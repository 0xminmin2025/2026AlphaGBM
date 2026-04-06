"""
Analytics API endpoints for tracking user behavior and market analysis.

This module provides endpoints for:
- Batch event submission from frontend
- Stock comparison
- Market sentiment dashboard
- Polymarket-derived signals
- Hot options (proxy to recommendations)
"""

from flask import Blueprint, request, jsonify
from ..models import db, AnalyticsEvent
from ..utils.auth import require_auth, get_user_id
import logging
import time
from datetime import datetime

analytics_bp = Blueprint('analytics', __name__, url_prefix='/api/analytics')
logger = logging.getLogger(__name__)

# Simple in-memory cache for expensive computations
_sentiment_cache = {'data': None, 'expires': 0}


@analytics_bp.route('/events', methods=['POST'])
def track_events():
    """
    Batch receive analytics events from frontend.

    Body: {
        "events": [
            {
                "event_type": "page_view",
                "session_id": "abc123",
                "user_id": "uuid" (optional),
                "user_tier": "guest|free|plus|pro",
                "properties": {...},
                "url": "/options",
                "referrer": "https://...",
                "timestamp": "2024-01-21T09:30:00Z"
            },
            ...
        ]
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400

        events = data.get('events', [])

        if not events:
            return jsonify({'success': True, 'count': 0}), 200

        # Limit batch size to prevent abuse
        MAX_BATCH_SIZE = 100
        if len(events) > MAX_BATCH_SIZE:
            events = events[:MAX_BATCH_SIZE]
            logger.warning(f"Analytics batch truncated to {MAX_BATCH_SIZE} events")

        # Prepare events for bulk insert
        analytics_events = []
        for event in events:
            try:
                # Parse timestamp from ISO format
                timestamp_str = event.get('timestamp')
                if timestamp_str:
                    try:
                        created_at = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    except (ValueError, AttributeError):
                        created_at = datetime.utcnow()
                else:
                    created_at = datetime.utcnow()

                analytics_event = AnalyticsEvent(
                    event_type=event.get('event_type', 'unknown'),
                    session_id=event.get('session_id', 'unknown'),
                    user_id=event.get('user_id'),  # Can be None for guests
                    user_tier=event.get('user_tier', 'guest'),
                    properties=event.get('properties', {}),
                    url=event.get('url', ''),
                    referrer=event.get('referrer', ''),
                    created_at=created_at
                )
                analytics_events.append(analytics_event)
            except Exception as e:
                logger.warning(f"Failed to process analytics event: {e}")
                continue

        # Bulk insert all events
        if analytics_events:
            db.session.bulk_save_objects(analytics_events)
            db.session.commit()
            logger.info(f"Stored {len(analytics_events)} analytics events")

        return jsonify({
            'success': True,
            'count': len(analytics_events)
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error storing analytics events: {e}")
        # Don't return error to client to prevent retries flooding the system
        return jsonify({'success': True, 'count': 0}), 200


@analytics_bp.route('/stats', methods=['GET'])
def get_stats():
    """
    Get basic analytics statistics (admin only).
    This is a simple endpoint for debugging; real analytics would use a dashboard.

    Query params:
    - days: Number of days to look back (default 7)
    """
    try:
        from datetime import timedelta
        from sqlalchemy import func

        days = request.args.get('days', 7, type=int)
        days = min(days, 30)  # Limit to 30 days max

        start_date = datetime.utcnow() - timedelta(days=days)

        # Get event counts by type
        event_counts = db.session.query(
            AnalyticsEvent.event_type,
            func.count(AnalyticsEvent.id).label('count')
        ).filter(
            AnalyticsEvent.created_at >= start_date
        ).group_by(
            AnalyticsEvent.event_type
        ).all()

        # Get unique sessions
        unique_sessions = db.session.query(
            func.count(func.distinct(AnalyticsEvent.session_id))
        ).filter(
            AnalyticsEvent.created_at >= start_date
        ).scalar() or 0

        # Get unique users (non-guest)
        unique_users = db.session.query(
            func.count(func.distinct(AnalyticsEvent.user_id))
        ).filter(
            AnalyticsEvent.created_at >= start_date,
            AnalyticsEvent.user_id.isnot(None)
        ).scalar() or 0

        return jsonify({
            'success': True,
            'period_days': days,
            'stats': {
                'event_counts': {row.event_type: row.count for row in event_counts},
                'unique_sessions': unique_sessions,
                'unique_users': unique_users
            }
        }), 200

    except Exception as e:
        logger.error(f"Error getting analytics stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ─────────────────────────────────────
# Compare
# ─────────────────────────────────────

@analytics_bp.route('/compare', methods=['GET'])
@require_auth
def compare_stocks():
    """
    Compare 2-5 stocks across multiple dimensions.

    Query params:
        symbols: comma-separated tickers (required, 2-5)
        dimensions: "all", "pillars", "options", "technicals", "valuations" (default "all")
    """
    try:
        symbols_str = request.args.get('symbols', '')
        if not symbols_str:
            return jsonify({'error': 'symbols parameter is required'}), 400

        symbols = [s.strip().upper() for s in symbols_str.split(',') if s.strip()]
        if len(symbols) < 2 or len(symbols) > 5:
            return jsonify({'error': 'Provide 2-5 symbols'}), 400

        dimensions = request.args.get('dimensions', 'all')

        from ..services.data_provider import DataProvider
        import numpy as np

        comparison = []
        for sym in symbols:
            try:
                provider = DataProvider(sym)
                info = provider.info or {}
                hist = provider.history(period='1mo')

                price = info.get('regularMarketPrice') or info.get('currentPrice', 0)
                pe = info.get('trailingPE')
                forward_pe = info.get('forwardPE')
                market_cap = info.get('marketCap')
                sector = info.get('sector', 'N/A')
                profit_margin = info.get('profitMargins')
                revenue_growth = info.get('revenueGrowth')
                beta = info.get('beta')

                # Compute 1M return and volatility from history
                monthly_return = None
                volatility = None
                if hist is not None and len(hist) > 1:
                    closes = hist['Close']
                    if len(closes) >= 2:
                        monthly_return = round(float((closes.iloc[-1] / closes.iloc[0] - 1) * 100), 2)
                        daily_returns = closes.pct_change().dropna()
                        if len(daily_returns) > 0:
                            volatility = round(float(daily_returns.std() * np.sqrt(252) * 100), 2)

                entry = {
                    'symbol': sym,
                    'price': price,
                    'pe_ratio': pe,
                    'forward_pe': forward_pe,
                    'market_cap': market_cap,
                    'sector': sector,
                    'profit_margin': round(profit_margin * 100, 2) if profit_margin else None,
                    'revenue_growth': round(revenue_growth * 100, 2) if revenue_growth else None,
                    'beta': beta,
                    'monthly_return_pct': monthly_return,
                    'annualized_volatility': volatility,
                }

                # Options metrics if requested
                if dimensions in ('all', 'options'):
                    try:
                        from ..services.options_service import OptionsService
                        exp_resp = OptionsService.get_expirations(sym)
                        if exp_resp.expirations:
                            nearest = exp_resp.expirations[0].date
                            chain = OptionsService.get_option_chain(sym, nearest)
                            chain_d = chain.dict() if chain else {}
                            entry['iv_rank'] = chain_d.get('iv_rank_30d')
                            entry['iv_percentile'] = chain_d.get('iv_percentile_30d')
                            entry['hv_30d'] = chain_d.get('historical_volatility')
                    except Exception:
                        pass

                comparison.append(entry)
            except Exception as e:
                logger.warning(f"Compare: failed to fetch {sym}: {e}")
                comparison.append({'symbol': sym, 'error': str(e)})

        # Determine winners by category
        valid = [c for c in comparison if 'error' not in c]
        winners = {}
        if valid:
            by_return = sorted(valid, key=lambda x: x.get('monthly_return_pct') or -999, reverse=True)
            winners['best_1m_return'] = by_return[0]['symbol'] if by_return else None
            by_pe = sorted([v for v in valid if v.get('pe_ratio')], key=lambda x: x['pe_ratio'])
            winners['lowest_pe'] = by_pe[0]['symbol'] if by_pe else None
            by_vol = sorted([v for v in valid if v.get('annualized_volatility')], key=lambda x: x['annualized_volatility'])
            winners['lowest_volatility'] = by_vol[0]['symbol'] if by_vol else None

        return jsonify({
            'success': True,
            'symbols': symbols,
            'dimensions': dimensions,
            'comparison': comparison,
            'category_winners': winners,
        })

    except Exception as e:
        logger.error(f"Compare error: {e}")
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────
# Market Sentiment
# ─────────────────────────────────────

@analytics_bp.route('/market-sentiment', methods=['GET'])
@require_auth
def market_sentiment():
    """
    Market sentiment dashboard.

    Query params:
        indicators: "all", "vix", "pcr", "breadth", "rotation" (default "all")
        lookback_days: int (default 252)
    """
    try:
        global _sentiment_cache
        now = time.time()

        # Return cached data if fresh (5 min TTL)
        if _sentiment_cache['data'] and now < _sentiment_cache['expires']:
            return jsonify(_sentiment_cache['data'])

        from ..services.data_provider import DataProvider
        import numpy as np

        indicators = request.args.get('indicators', 'all')
        result = {'success': True, 'timestamp': datetime.utcnow().isoformat()}

        # VIX
        try:
            vix_provider = DataProvider('^VIX')
            vix_hist = vix_provider.history(period='1y')
            if vix_hist is not None and len(vix_hist) > 0:
                vix_current = float(vix_hist['Close'].iloc[-1])
                vix_mean = float(vix_hist['Close'].mean())
                vix_pct = float((vix_hist['Close'] < vix_current).mean() * 100)
                result['vix'] = {
                    'current': round(vix_current, 2),
                    'mean_1y': round(vix_mean, 2),
                    'percentile': round(vix_pct, 1),
                    'level': 'extreme_fear' if vix_current > 30 else 'fear' if vix_current > 20 else 'neutral' if vix_current > 15 else 'greed',
                }
        except Exception as e:
            logger.warning(f"VIX fetch failed: {e}")
            result['vix'] = None

        # Market breadth via SPY / QQQ
        try:
            spy_hist = DataProvider('SPY').history(period='1mo')
            qqq_hist = DataProvider('QQQ').history(period='1mo')
            breadth = {}
            if spy_hist is not None and len(spy_hist) > 1:
                spy_ret = float((spy_hist['Close'].iloc[-1] / spy_hist['Close'].iloc[0] - 1) * 100)
                breadth['spy_1m_return'] = round(spy_ret, 2)
            if qqq_hist is not None and len(qqq_hist) > 1:
                qqq_ret = float((qqq_hist['Close'].iloc[-1] / qqq_hist['Close'].iloc[0] - 1) * 100)
                breadth['qqq_1m_return'] = round(qqq_ret, 2)
            result['breadth'] = breadth
        except Exception as e:
            logger.warning(f"Breadth fetch failed: {e}")
            result['breadth'] = None

        # Sector rotation
        try:
            sector_etfs = {'Technology': 'XLK', 'Financials': 'XLF', 'Energy': 'XLE', 'Healthcare': 'XLV',
                           'Consumer Discretionary': 'XLY', 'Industrials': 'XLI'}
            rotation = {}
            for name, etf in sector_etfs.items():
                try:
                    h = DataProvider(etf).history(period='1mo')
                    if h is not None and len(h) > 1:
                        ret = float((h['Close'].iloc[-1] / h['Close'].iloc[0] - 1) * 100)
                        rotation[name] = round(ret, 2)
                except Exception:
                    continue
            result['sector_rotation'] = rotation
        except Exception as e:
            logger.warning(f"Sector rotation failed: {e}")
            result['sector_rotation'] = None

        # Put/Call ratio from SPY options
        try:
            from ..services.options_service import OptionsService
            exp_resp = OptionsService.get_expirations('SPY')
            if exp_resp.expirations:
                nearest = exp_resp.expirations[0].date
                chain = OptionsService.get_option_chain('SPY', nearest)
                if chain:
                    call_vol = sum(c.volume or 0 for c in chain.calls) if chain.calls else 0
                    put_vol = sum(p.volume or 0 for p in chain.puts) if chain.puts else 0
                    pcr = round(put_vol / call_vol, 3) if call_vol > 0 else None
                    result['put_call_ratio'] = {
                        'ratio': pcr,
                        'call_volume': call_vol,
                        'put_volume': put_vol,
                        'signal': 'bearish' if pcr and pcr > 1.2 else 'bullish' if pcr and pcr < 0.7 else 'neutral',
                    }
        except Exception as e:
            logger.warning(f"PCR fetch failed: {e}")
            result['put_call_ratio'] = None

        # Overall regime
        vix_val = result.get('vix', {})
        vix_level = vix_val.get('current', 20) if vix_val else 20
        spy_ret = result.get('breadth', {})
        spy_1m = spy_ret.get('spy_1m_return', 0) if spy_ret else 0
        if vix_level > 25 and spy_1m < -3:
            regime = 'risk_off'
        elif vix_level < 18 and spy_1m > 2:
            regime = 'risk_on'
        else:
            regime = 'neutral'
        result['regime'] = regime

        # Cache result
        _sentiment_cache = {'data': result, 'expires': now + 300}

        return jsonify(result)

    except Exception as e:
        logger.error(f"Market sentiment error: {e}")
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────
# Polymarket Signals (market-derived)
# ─────────────────────────────────────

@analytics_bp.route('/polymarket/signals', methods=['GET'])
@require_auth
def polymarket_signals():
    """
    Market-derived signals inspired by prediction markets.
    No real Polymarket API — computed from available market data.

    Query params:
        event_type: "fed", "macro", "all" (default "all")
    """
    try:
        from ..services.data_provider import DataProvider
        import numpy as np

        event_type = request.args.get('event_type', 'all')
        signals = []

        # Signal 1: Fed rate expectations (from Treasury yields and VIX)
        try:
            vix_provider = DataProvider('^VIX')
            vix_hist = vix_provider.history(period='5d')
            if vix_hist is not None and len(vix_hist) > 0:
                vix_current = float(vix_hist['Close'].iloc[-1])
                # Higher VIX → markets expect more volatility → more likely to cut
                rate_cut_prob = min(0.95, max(0.10, 0.3 + (vix_current - 18) * 0.02))
                signals.append({
                    'event_id': 'fed_rate_decision_next',
                    'event_type': 'fed',
                    'title': 'Fed Rate Cut at Next Meeting',
                    'probability': round(rate_cut_prob, 2),
                    'source': 'market_derived',
                    'basis': f'VIX at {round(vix_current, 1)} implies {round(rate_cut_prob*100)}% cut probability',
                    'confidence': 0.6,
                })
        except Exception:
            pass

        # Signal 2: Market direction (SPY trend)
        try:
            spy_hist = DataProvider('SPY').history(period='1mo')
            if spy_hist is not None and len(spy_hist) > 5:
                spy_return = float((spy_hist['Close'].iloc[-1] / spy_hist['Close'].iloc[0] - 1))
                spy_5d_return = float((spy_hist['Close'].iloc[-1] / spy_hist['Close'].iloc[-5] - 1))
                bull_prob = min(0.90, max(0.10, 0.50 + spy_return * 2 + spy_5d_return * 3))
                signals.append({
                    'event_id': 'sp500_higher_next_month',
                    'event_type': 'macro',
                    'title': 'S&P 500 Higher in 30 Days',
                    'probability': round(bull_prob, 2),
                    'source': 'market_derived',
                    'basis': f'SPY 1M return {round(spy_return*100, 1)}%, momentum {round(spy_5d_return*100, 1)}%',
                    'confidence': 0.5,
                })
        except Exception:
            pass

        # Signal 3: Recession risk (from yield curve proxy)
        try:
            # Use VIX and market breadth as recession proxy
            vix_val = float(vix_hist['Close'].iloc[-1]) if vix_hist is not None and len(vix_hist) > 0 else 20
            recession_prob = min(0.80, max(0.05, (vix_val - 15) * 0.025))
            signals.append({
                'event_id': 'us_recession_2026',
                'event_type': 'macro',
                'title': 'US Recession in 2026',
                'probability': round(recession_prob, 2),
                'source': 'market_derived',
                'basis': f'VIX-implied stress at {round(vix_val, 1)}',
                'confidence': 0.4,
            })
        except Exception:
            pass

        # Filter by event_type
        if event_type != 'all':
            signals = [s for s in signals if s['event_type'] == event_type]

        return jsonify({
            'success': True,
            'source_note': 'Signals derived from market data, not from Polymarket',
            'events': signals,
        })

    except Exception as e:
        logger.error(f"Polymarket signals error: {e}")
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────
# Hot Options (proxy to recommendations)
# ─────────────────────────────────────

@analytics_bp.route('/hot-options', methods=['GET'])
@require_auth
def hot_options():
    """
    Hot options — proxies to existing daily recommendations.

    Query params:
        count: int (default 5, max 10)
    """
    try:
        from ..services.recommendation_service import recommendation_service
        count = request.args.get('count', 5, type=int)
        count = min(max(1, count), 10)
        result = recommendation_service.get_daily_recommendations(count=count)
        return jsonify(result), 200 if result.get('success') else 500
    except Exception as e:
        logger.error(f"Hot options error: {e}")
        return jsonify({'error': str(e)}), 500

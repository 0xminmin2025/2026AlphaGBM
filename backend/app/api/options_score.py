"""
Options Score API v1 — API Key 认证的期权评分端点

/api/v1/options/score  — 接收 ticker + strategy，返回期权推荐评分（Top 10）
"""

from flask import Blueprint, jsonify, request, g
from ..utils.auth import require_auth
from ..utils.decorators import check_quota
from ..utils.rate_limiter import rate_limit
from ..models import ServiceType
from ..services.options_service import OptionsService
from ..analysis.options_analysis.option_market_config import get_option_market_config
import logging

logger = logging.getLogger(__name__)

options_score_bp = Blueprint('options_score', __name__, url_prefix='/api/v1/options')


def _check_whitelist(symbol: str):
    """Check whitelist for HK/CN markets."""
    market_config = get_option_market_config(symbol)
    if market_config.whitelist_enforced and not market_config.is_symbol_allowed(symbol):
        return jsonify({
            'success': False,
            'error': f'Symbol {symbol} not in {market_config.market} whitelist',
            'allowed_symbols': market_config.get_allowed_symbols(),
        }), 400
    return None


@options_score_bp.route('/score', methods=['POST'])
@require_auth
@rate_limit(max_requests=60, window_seconds=60)
@check_quota(ServiceType.OPTION_ANALYSIS.value, amount=1)
def score_options():
    """
    期权推荐评分 API

    Request Body:
    {
        "ticker": "AAPL",
        "strategy": "sell_put",        // sell_put | sell_call | buy_call | buy_put | all
        "expiry_date": "2026-04-17",   // optional — auto-picks nearest monthly if omitted
        "top_n": 5                     // optional, default 5, max 10
    }

    Response:
    {
        "success": true,
        "ticker": "AAPL",
        "strategy": "sell_put",
        "current_price": 185.50,
        "expiry_date": "2026-04-17",
        "trend": {"direction": "downtrend", "strength": 0.67, "alignment_score": 100},
        "recommendations": [
            {
                "rank": 1,
                "strike": 170.0,
                "expiry": "2026-04-17",
                "days_to_expiry": 14,
                "mid_price": 2.65,
                "score": 78.5,
                "annualized_return_pct": 23.7,
                "safety_margin_pct": 5.82,
                "atr_safety": {"ratio": 1.25, "multiples": 2.5, "is_safe": true},
                "style": "balanced",
                "risk_level": "moderate",
                "win_probability": 0.72,
                "score_breakdown": {...}
            }
        ]
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Request body is required'}), 400

        ticker = data.get('ticker', '').upper()
        if not ticker:
            return jsonify({'success': False, 'error': 'ticker is required'}), 400

        strategy = data.get('strategy', 'all').lower().replace('-', '_')
        valid_strategies = ['sell_put', 'sell_call', 'buy_call', 'buy_put', 'all']
        if strategy not in valid_strategies:
            return jsonify({
                'success': False,
                'error': f'Invalid strategy. Must be one of: {", ".join(valid_strategies)}'
            }), 400

        top_n = min(max(1, data.get('top_n', 5)), 10)
        expiry_date = data.get('expiry_date')

        # Whitelist check
        wl_err = _check_whitelist(ticker)
        if wl_err:
            return wl_err

        # Auto-select nearest expiry if not provided
        if not expiry_date:
            try:
                exp_response = OptionsService.get_expirations(ticker)
                expirations = exp_response.expirations if hasattr(exp_response, 'expirations') else []
                if not expirations:
                    return jsonify({'success': False, 'error': f'No option expirations found for {ticker}'}), 404

                # Pick nearest monthly (≥ 14 DTE) or fallback to first
                from datetime import datetime as dt
                today = dt.now().date()
                for exp in expirations:
                    try:
                        exp_date = dt.strptime(exp, '%Y-%m-%d').date()
                        dte = (exp_date - today).days
                        if dte >= 14:
                            expiry_date = exp
                            break
                    except ValueError:
                        continue
                if not expiry_date:
                    expiry_date = expirations[0]
            except Exception as e:
                return jsonify({'success': False, 'error': f'Cannot determine expiry: {str(e)}'}), 400

        # Run analysis (sync)
        from .options import get_options_analysis_data
        result = get_options_analysis_data(ticker, enhanced=False, expiry_date=expiry_date)

        if 'error' in result:
            return jsonify({'success': False, 'error': result['error']}), 400

        # Extract relevant strategy data
        current_price = result.get('real_stock_price') or result.get('underlying_price') or 0

        # Build response for requested strategy(ies)
        strategies_to_return = valid_strategies[:-1] if strategy == 'all' else [strategy]
        output_strategies = {}

        for strat in strategies_to_return:
            recs = _extract_recommendations(result, strat, top_n)
            if recs is not None:
                output_strategies[strat] = recs

        # Get trend info
        trend_info = _extract_trend(result)

        response = {
            'success': True,
            'ticker': ticker,
            'strategy': strategy,
            'current_price': current_price,
            'expiry_date': expiry_date,
            'trend': trend_info,
        }

        if strategy == 'all':
            response['strategies'] = output_strategies
        else:
            response['recommendations'] = output_strategies.get(strategy, [])

        return jsonify(response), 200

    except Exception as e:
        logger.error(f"[options-score] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


def _extract_recommendations(result: dict, strategy: str, top_n: int) -> list:
    """Extract top-N scored recommendations for a strategy from chain result."""
    # The chain result has strategy_results keyed by strategy name
    strategy_map = {
        'sell_put': 'sell_put',
        'sell_call': 'sell_call',
        'buy_call': 'buy_call',
        'buy_put': 'buy_put',
    }
    key = strategy_map.get(strategy)
    if not key:
        return []

    # Try multiple possible result structures
    strat_data = None

    # Structure 1: result['strategy_results'][key]
    if 'strategy_results' in result:
        strat_data = result['strategy_results'].get(key, {})

    # Structure 2: result[key]
    if not strat_data and key in result:
        strat_data = result[key]

    # Structure 3: Look in 'data' wrapper
    if not strat_data and 'data' in result:
        data = result['data']
        if isinstance(data, dict):
            strat_data = data.get('strategy_results', {}).get(key, {})
            if not strat_data:
                strat_data = data.get(key, {})

    if not strat_data:
        return []

    # Get recommendations list
    recs = []
    if isinstance(strat_data, dict):
        recs = strat_data.get('recommendations', [])
        if not recs:
            recs = strat_data.get('options', [])
    elif isinstance(strat_data, list):
        recs = strat_data

    # Sort by score descending and take top N
    recs = sorted(recs, key=lambda r: r.get('score', 0), reverse=True)[:top_n]

    # Normalize output format
    output = []
    for rank, rec in enumerate(recs, 1):
        item = {
            'rank': rank,
            'strike': rec.get('strike'),
            'expiry': rec.get('expiry') or rec.get('expiry_date'),
            'days_to_expiry': rec.get('days_to_expiry') or rec.get('dte'),
            'mid_price': rec.get('mid_price') or rec.get('midPrice'),
            'bid': rec.get('bid'),
            'ask': rec.get('ask'),
            'score': round(rec.get('score', 0), 1),
            'annualized_return_pct': rec.get('annualized_return') or rec.get('annualized_return_pct'),
            'premium_yield_pct': rec.get('premium_yield'),
            'safety_margin_pct': rec.get('safety_margin'),
            'implied_volatility': rec.get('implied_volatility') or rec.get('iv'),
        }

        # ATR safety
        atr = rec.get('atr_safety', {})
        if atr:
            item['atr_safety'] = {
                'ratio': atr.get('safety_ratio'),
                'multiples': atr.get('atr_multiples'),
                'is_safe': atr.get('is_safe'),
            }

        # Risk-return profile
        profile = rec.get('risk_return_profile', {})
        if profile:
            item['style'] = profile.get('style')
            item['style_label'] = profile.get('style_label')
            item['risk_level'] = profile.get('risk_level')
            item['win_probability'] = profile.get('win_probability')

        # Score breakdown
        breakdown = rec.get('score_breakdown', {})
        if breakdown:
            item['score_breakdown'] = breakdown

        # Warnings
        if rec.get('trend_warning'):
            item['trend_warning'] = rec['trend_warning']
        item['is_ideal_trend'] = rec.get('is_ideal_trend', True)

        # Max profit / breakeven
        if rec.get('max_profit') is not None:
            item['max_profit'] = rec['max_profit']
        if rec.get('breakeven') is not None:
            item['breakeven'] = rec['breakeven']

        output.append(item)

    return output


def _extract_trend(result: dict) -> dict:
    """Extract trend info from chain result."""
    # Try multiple locations
    for path in [
        result.get('trend_info', {}),
        result.get('data', {}).get('trend_info', {}) if isinstance(result.get('data'), dict) else {},
        result.get('strategy_analysis', {}).get('trend_analysis', {}) if isinstance(result.get('strategy_analysis'), dict) else {},
    ]:
        if path and isinstance(path, dict) and path.get('trend'):
            return {
                'direction': path.get('trend'),
                'strength': path.get('trend_strength'),
                'alignment_score': path.get('trend_alignment_score'),
            }
    return {'direction': 'unknown', 'strength': None, 'alignment_score': None}

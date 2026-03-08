"""
Paper Trading Strategy Signal Generators

Wraps existing analysis engines to generate actionable trading signals
for the paper trading system.

Two strategies:
1. Momentum Stock - selects top stocks by 6-month momentum
2. Options Seller - sells puts on momentum holdings
"""

import logging
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Curated universe of liquid US stocks (SP500 subset)
STOCK_UNIVERSE = [
    # Mega-cap Tech
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'AVGO', 'ORCL', 'CRM',
    # Semiconductors
    'AMD', 'INTC', 'QCOM', 'MU', 'AMAT', 'LRCX', 'KLAC', 'MRVL', 'ON', 'NXPI',
    # Software & Cloud
    'ADBE', 'NOW', 'SNOW', 'PANW', 'CRWD', 'DDOG', 'ZS', 'NET', 'WDAY', 'TEAM',
    # Finance
    'JPM', 'BAC', 'GS', 'MS', 'BLK', 'SCHW', 'C', 'WFC', 'AXP', 'V',
    # Healthcare
    'UNH', 'JNJ', 'LLY', 'ABBV', 'MRK', 'PFE', 'TMO', 'ABT', 'AMGN', 'GILD',
    # Consumer
    'COST', 'WMT', 'HD', 'MCD', 'NKE', 'SBUX', 'TGT', 'LOW', 'TJX', 'LULU',
    # Industrial & Energy
    'CAT', 'DE', 'GE', 'HON', 'UNP', 'XOM', 'CVX', 'COP', 'SLB', 'EOG',
    # ETFs for broader exposure
    'SPY', 'QQQ', 'IWM', 'DIA', 'XLF', 'XLK', 'XLE', 'XLV', 'XLI', 'XLC',
]


def generate_momentum_signals(top_k: int = 15, capital: float = 100_000) -> List[Dict[str, Any]]:
    """
    Generate momentum stock buy signals.

    Strategy:
    1. Download 7-month history for universe
    2. Compute 6-month return (skip most recent month for mean reversion)
    3. Filter: above 200-day MA, vol < 80th percentile
    4. Select top K, equal-weight allocation
    5. ATR-based stop loss (2x ATR below entry)

    Returns list of signal dicts with ticker, action, quantity, price, stop_loss.
    """
    try:
        import yfinance as yf

        logger.info(f"Generating momentum signals for top {top_k} from {len(STOCK_UNIVERSE)} stocks...")

        # Batch download - 7 months of data
        tickers_str = ' '.join(STOCK_UNIVERSE)
        data = yf.download(tickers_str, period='7mo', group_by='ticker', threads=True, progress=False)

        if data is None or data.empty:
            logger.error("Failed to download stock data")
            return []

        scored = []
        for ticker in STOCK_UNIVERSE:
            try:
                # Extract ticker data
                if len(STOCK_UNIVERSE) > 1:
                    ticker_data = data[ticker] if ticker in data.columns.get_level_values(0) else None
                else:
                    ticker_data = data

                if ticker_data is None or ticker_data.empty:
                    continue

                close = ticker_data['Close'].dropna()
                if len(close) < 120:  # Need ~6 months of data
                    continue

                current_price = float(close.iloc[-1])

                # 6-month return (skip last 21 trading days for mean reversion filter)
                if len(close) > 21:
                    month_ago_price = float(close.iloc[-22])
                    six_month_start = float(close.iloc[0])
                    momentum_return = (month_ago_price / six_month_start - 1) * 100
                else:
                    continue

                # MA200 filter (use available data as proxy)
                ma = close.rolling(min(200, len(close))).mean().iloc[-1]
                if current_price < float(ma):
                    continue  # Below moving average - skip

                # Volatility filter
                daily_returns = close.pct_change().dropna()
                vol = float(daily_returns.std() * np.sqrt(252) * 100)

                # ATR for stop loss
                high = ticker_data['High'].dropna()
                low = ticker_data['Low'].dropna()
                if len(high) >= 14 and len(low) >= 14:
                    tr = np.maximum(
                        high.iloc[-14:].values - low.iloc[-14:].values,
                        np.abs(high.iloc[-14:].values - close.iloc[-15:-1].values)
                    )
                    atr = float(np.mean(tr))
                else:
                    atr = current_price * 0.02  # Fallback: 2%

                scored.append({
                    'ticker': ticker,
                    'momentum_return': momentum_return,
                    'current_price': current_price,
                    'volatility': vol,
                    'atr': atr,
                })

            except Exception as e:
                logger.debug(f"Skipping {ticker}: {e}")
                continue

        if not scored:
            logger.warning("No stocks passed momentum filters")
            return []

        # Filter out high-volatility stocks (top 20%)
        vols = [s['volatility'] for s in scored]
        vol_80th = np.percentile(vols, 80)
        scored = [s for s in scored if s['volatility'] <= vol_80th]

        # Sort by momentum return, take top K
        scored.sort(key=lambda x: x['momentum_return'], reverse=True)
        top_stocks = scored[:top_k]

        # Equal-weight allocation
        weight = 1.0 / len(top_stocks)
        allocation_per_stock = capital * weight * 0.9  # 90% invested, 10% cash reserve

        signals = []
        for stock in top_stocks:
            quantity = int(allocation_per_stock / stock['current_price'])
            if quantity <= 0:
                continue
            signals.append({
                'ticker': stock['ticker'],
                'action': 'BUY',
                'security_type': 'STOCK',
                'strategy': 'momentum',
                'quantity': quantity,
                'price': stock['current_price'],
                'stop_loss': round(stock['current_price'] - 2 * stock['atr'], 2),
                'notes': f"Momentum: {stock['momentum_return']:.1f}%, Vol: {stock['volatility']:.1f}%",
            })

        logger.info(f"Generated {len(signals)} momentum buy signals")
        return signals

    except Exception as e:
        logger.error(f"Momentum signal generation failed: {e}")
        return []


def generate_options_signals(momentum_tickers: List[str] = None,
                             max_signals: int = 5) -> List[Dict[str, Any]]:
    """
    Generate sell-put options signals on momentum holdings.

    Strategy:
    1. For each momentum holding, analyze options chain
    2. Use existing OptionsAnalysisEngine for scoring
    3. Filter: DTE 20-45, score > 70
    4. Return top opportunities

    Returns list of signal dicts for option trades.
    """
    try:
        from ..analysis.options_analysis.core.engine import OptionsAnalysisEngine

        if not momentum_tickers:
            # Get current momentum positions
            from ..models import PaperPosition
            positions = PaperPosition.query.filter_by(strategy='momentum', security_type='STOCK').all()
            momentum_tickers = [p.ticker for p in positions]

        if not momentum_tickers:
            logger.info("No momentum tickers for options scan")
            return []

        engine = OptionsAnalysisEngine()
        signals = []

        for ticker in momentum_tickers[:10]:  # Limit to 10 tickers to avoid API rate limits
            try:
                result = engine.analyze_options_chain(ticker, strategy='sell_put')
                if not result.get('success'):
                    continue

                sell_put_result = result.get('strategy_analysis', {}).get('sell_put', {})
                if not sell_put_result.get('success'):
                    continue

                recommendations = sell_put_result.get('recommendations', [])
                for rec in recommendations[:2]:  # Top 2 per ticker
                    score = rec.get('score', 0)
                    days_to_expiry = rec.get('days_to_expiry', 0)

                    # Filter: score > 70, DTE 20-45
                    if score < 70 or days_to_expiry < 20 or days_to_expiry > 45:
                        continue

                    mid_price = rec.get('mid_price') or rec.get('bid', 0)
                    if mid_price <= 0:
                        continue

                    signals.append({
                        'ticker': ticker,
                        'action': 'SELL',
                        'security_type': 'OPTION',
                        'strategy': 'options_seller',
                        'quantity': 1,  # 1 contract
                        'price': mid_price,
                        'expiry': rec.get('expiry'),
                        'strike': rec.get('strike'),
                        'option_right': 'PUT',
                        'notes': f"Score: {score:.0f}, DTE: {days_to_expiry}, "
                                 f"Yield: {rec.get('premium_yield', 0):.2f}%, "
                                 f"Safety: {rec.get('safety_margin', 0):.1f}%",
                    })

            except Exception as e:
                logger.warning(f"Options scan failed for {ticker}: {e}")
                continue

        # Sort by score (embedded in notes), take top N
        signals = signals[:max_signals]
        logger.info(f"Generated {len(signals)} options sell signals")
        return signals

    except Exception as e:
        logger.error(f"Options signal generation failed: {e}")
        return []


def run_momentum_rebalance():
    """
    Full momentum rebalance: close old positions, open new ones.
    Called by scheduler monthly.
    """
    from .paper_trading_service import paper_trading_service
    from ..models import PaperPosition

    logger.info("Starting monthly momentum rebalance...")

    # Get current momentum positions
    current_positions = PaperPosition.query.filter_by(
        strategy='momentum', security_type='STOCK'
    ).all()
    current_tickers = {p.ticker for p in current_positions}

    # Generate new signals
    cash = paper_trading_service.get_cash_balance()
    portfolio_value = paper_trading_service.get_portfolio_value()
    signals = generate_momentum_signals(top_k=15, capital=portfolio_value)
    new_tickers = {s['ticker'] for s in signals}

    # Close positions no longer in top K
    for pos in current_positions:
        if pos.ticker not in new_tickers and pos.current_price:
            paper_trading_service.execute_trade(
                ticker=pos.ticker, action='SELL', quantity=pos.quantity,
                price=pos.current_price, strategy='momentum',
                notes='Monthly rebalance: removed from top K'
            )

    # Open new positions
    for signal in signals:
        if signal['ticker'] not in current_tickers:
            paper_trading_service.execute_trade(**signal)

    logger.info(f"Momentum rebalance complete: {len(signals)} target positions")


def run_weekly_options_scan():
    """
    Weekly options scan: sell puts on momentum holdings.
    Called by scheduler weekly.
    """
    from .paper_trading_service import paper_trading_service

    logger.info("Starting weekly options scan...")
    signals = generate_options_signals()

    for signal in signals:
        paper_trading_service.execute_trade(**signal)

    logger.info(f"Options scan complete: executed {len(signals)} trades")

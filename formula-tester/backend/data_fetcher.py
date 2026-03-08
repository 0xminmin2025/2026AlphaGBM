"""
Data Fetcher - Raw data with yfinance-first, defeatbeta-api fallback
Used for testing formulas with real market data
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Import DataProvider from local module (with defeatbeta fallback)
DATA_PROVIDER_AVAILABLE = False
DataProvider = None

try:
    from data_provider import DataProvider as _DP
    DataProvider = _DP
    DATA_PROVIDER_AVAILABLE = True
    logger.info("DataProvider with defeatbeta fallback loaded successfully")
except ImportError as e:
    logger.warning(f"DataProvider not available ({e}), using yfinance directly")
    import yfinance as yf


def _get_ticker(symbol: str):
    """Get a ticker object - either DataProvider or yfinance."""
    if DATA_PROVIDER_AVAILABLE:
        return DataProvider(symbol)
    else:
        import yfinance as yf
        return yf.Ticker(symbol)


def fetch_stock_data(symbol: str) -> Dict[str, Any]:
    """
    Fetch comprehensive stock data for formula testing

    Returns:
    - Current price and change
    - Historical prices (OHLCV)
    - Fundamental data
    - Support/Resistance estimates
    """
    try:
        ticker = _get_ticker(symbol)

        # Get basic info
        info = ticker.info or {}

        # Get historical data (6 months for technical analysis)
        hist = ticker.history(period="6mo")

        if hist is None or hist.empty:
            return {
                'success': False,
                'error': f'No historical data for {symbol}'
            }

        current_price = float(hist['Close'].iloc[-1])
        prev_close = float(hist['Close'].iloc[-2]) if len(hist) > 1 else current_price
        change = current_price - prev_close
        change_percent = (change / prev_close) * 100 if prev_close > 0 else 0

        # Calculate technical levels
        high_52w = float(hist['High'].max())
        low_52w = float(hist['Low'].min())

        # Simple support/resistance from recent highs/lows
        recent_highs = hist['High'].tail(20)
        recent_lows = hist['Low'].tail(20)

        resistance_1 = float(recent_highs.nlargest(3).mean())
        resistance_2 = float(hist['High'].tail(60).nlargest(5).mean()) if len(hist) >= 60 else resistance_1 * 1.05
        support_1 = float(recent_lows.nsmallest(3).mean())
        support_2 = float(hist['Low'].tail(60).nsmallest(5).mean()) if len(hist) >= 60 else support_1 * 0.95

        # Moving averages
        ma_5 = float(hist['Close'].tail(5).mean())
        ma_20 = float(hist['Close'].tail(20).mean())
        ma_50 = float(hist['Close'].tail(50).mean()) if len(hist) >= 50 else None
        ma_200 = float(hist['Close'].tail(200).mean()) if len(hist) >= 200 else None

        # Volatility
        returns = hist['Close'].pct_change().dropna()
        daily_vol = float(returns.std())
        annualized_vol = daily_vol * np.sqrt(252)

        # Fundamental data - handle both yfinance and defeatbeta field names
        pe_ratio = info.get('trailingPE') or info.get('trailingPe')
        forward_pe = info.get('forwardPE') or info.get('forwardPe')
        peg_ratio = info.get('pegRatio')
        pb_ratio = info.get('priceToBook')
        dividend_yield = info.get('dividendYield', 0)
        market_cap = info.get('marketCap')
        debt_to_equity = info.get('debtToEquity')
        beta = info.get('beta')
        roe = info.get('returnOnEquity')
        gross_margin = info.get('grossMargins')
        revenue_growth = info.get('revenueGrowth')
        earnings_growth = info.get('earningsGrowth')

        return {
            'success': True,
            'symbol': symbol.upper(),
            'fetched_at': datetime.now().isoformat(),
            'data_source': 'defeatbeta' if (DATA_PROVIDER_AVAILABLE and hasattr(ticker, '_yf_failed') and ticker._yf_failed) else 'yfinance',
            'price_data': {
                'current_price': round(current_price, 2),
                'prev_close': round(prev_close, 2),
                'change': round(change, 2),
                'change_percent': round(change_percent, 2),
                'high_52w': round(high_52w, 2),
                'low_52w': round(low_52w, 2),
                'volume': int(hist['Volume'].iloc[-1]),
                'avg_volume_20d': int(hist['Volume'].tail(20).mean())
            },
            'technical_levels': {
                'resistance_1': round(resistance_1, 2),
                'resistance_2': round(resistance_2, 2),
                'support_1': round(support_1, 2),
                'support_2': round(support_2, 2),
                'ma_5': round(ma_5, 2),
                'ma_20': round(ma_20, 2),
                'ma_50': round(ma_50, 2) if ma_50 else None,
                'ma_200': round(ma_200, 2) if ma_200 else None
            },
            'volatility': {
                'daily_volatility': round(daily_vol * 100, 4),
                'annualized_volatility': round(annualized_vol * 100, 2),
                'beta': round(beta, 2) if beta else None
            },
            'fundamentals': {
                'pe_ratio': round(pe_ratio, 2) if pe_ratio else None,
                'forward_pe': round(forward_pe, 2) if forward_pe else None,
                'peg_ratio': round(peg_ratio, 2) if peg_ratio else None,
                'pb_ratio': round(pb_ratio, 2) if pb_ratio else None,
                'dividend_yield': round(dividend_yield * 100, 2) if dividend_yield else None,
                'market_cap': market_cap,
                'debt_to_equity': round(debt_to_equity, 1) if debt_to_equity else None,
                'roe': round(roe * 100, 2) if roe else None,
                'gross_margin': round(gross_margin * 100, 2) if gross_margin else None,
                'revenue_growth': round(revenue_growth * 100, 2) if revenue_growth else None,
                'earnings_growth': round(earnings_growth * 100, 2) if earnings_growth else None
            },
            'history': {
                'dates': hist.index.strftime('%Y-%m-%d').tolist()[-60:],
                'open': [round(float(x), 2) for x in hist['Open'].tolist()[-60:]],
                'high': [round(float(x), 2) for x in hist['High'].tolist()[-60:]],
                'low': [round(float(x), 2) for x in hist['Low'].tolist()[-60:]],
                'close': [round(float(x), 2) for x in hist['Close'].tolist()[-60:]],
                'volume': [int(x) for x in hist['Volume'].tolist()[-60:]]
            }
        }

    except Exception as e:
        logger.error(f"Error fetching stock data for {symbol}: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def fetch_options_data(symbol: str, expiry_filter: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetch options chain data for formula testing
    Note: Options data is only available from yfinance, not defeatbeta

    Returns:
    - Available expiration dates
    - Calls and Puts with greeks, IV, volume, OI
    """
    try:
        ticker = _get_ticker(symbol)

        # Get current price from history
        hist = ticker.history(period="5d")
        if hist is None or hist.empty:
            return {
                'success': False,
                'error': f'Cannot get current price for {symbol}'
            }
        current_price = float(hist['Close'].iloc[-1])

        # Get available expirations (yfinance only)
        expirations = ticker.options

        if not expirations:
            return {
                'success': False,
                'error': f'No options data available for {symbol}'
            }

        # Select expiration to fetch
        if expiry_filter and expiry_filter in expirations:
            selected_expiry = expiry_filter
        else:
            # Default: get nearest expiry 20-45 days out
            today = datetime.now().date()
            selected_expiry = None
            for exp in expirations:
                exp_date = datetime.strptime(exp, '%Y-%m-%d').date()
                days_to_exp = (exp_date - today).days
                if 20 <= days_to_exp <= 45:
                    selected_expiry = exp
                    break

            if not selected_expiry:
                selected_expiry = expirations[0]

        # Fetch options chain
        opt_chain = ticker.option_chain(selected_expiry)
        if opt_chain is None:
            return {
                'success': False,
                'error': f'Failed to fetch options chain for {symbol}'
            }

        calls_df = opt_chain.calls
        puts_df = opt_chain.puts

        # Calculate days to expiry
        exp_date = datetime.strptime(selected_expiry, '%Y-%m-%d').date()
        days_to_expiry = (exp_date - datetime.now().date()).days

        # Process calls
        calls = []
        for _, row in calls_df.iterrows():
            calls.append({
                'strike': float(row['strike']),
                'bid': float(row.get('bid', 0) or 0),
                'ask': float(row.get('ask', 0) or 0),
                'last': float(row.get('lastPrice', 0) or 0),
                'volume': int(row.get('volume', 0) or 0),
                'open_interest': int(row.get('openInterest', 0) or 0),
                'implied_volatility': round(float(row.get('impliedVolatility', 0) or 0) * 100, 2),
                'delta': row.get('delta'),
                'gamma': row.get('gamma'),
                'theta': row.get('theta'),
                'vega': row.get('vega'),
                'in_the_money': bool(row.get('inTheMoney', False))
            })

        # Process puts
        puts = []
        for _, row in puts_df.iterrows():
            puts.append({
                'strike': float(row['strike']),
                'bid': float(row.get('bid', 0) or 0),
                'ask': float(row.get('ask', 0) or 0),
                'last': float(row.get('lastPrice', 0) or 0),
                'volume': int(row.get('volume', 0) or 0),
                'open_interest': int(row.get('openInterest', 0) or 0),
                'implied_volatility': round(float(row.get('impliedVolatility', 0) or 0) * 100, 2),
                'delta': row.get('delta'),
                'gamma': row.get('gamma'),
                'theta': row.get('theta'),
                'vega': row.get('vega'),
                'in_the_money': bool(row.get('inTheMoney', False))
            })

        # Calculate weighted average IV
        all_options = calls + puts
        valid_ivs = [o['implied_volatility'] for o in all_options if o['implied_volatility'] > 0]
        valid_ois = [o['open_interest'] for o in all_options if o['implied_volatility'] > 0]

        if valid_ivs and valid_ois:
            weights = np.array(valid_ois) + 1  # Add 1 to avoid zero weights
            weighted_iv = float(np.average(valid_ivs, weights=weights))
        else:
            weighted_iv = float(np.mean(valid_ivs)) if valid_ivs else 0

        # Find ATM IV
        atm_iv = None
        min_diff = float('inf')
        for opt in all_options:
            diff = abs(opt['strike'] - current_price)
            if diff < min_diff and opt['implied_volatility'] > 0:
                min_diff = diff
                atm_iv = opt['implied_volatility']

        return {
            'success': True,
            'symbol': symbol.upper(),
            'fetched_at': datetime.now().isoformat(),
            'current_price': round(current_price, 2),
            'expiration': selected_expiry,
            'days_to_expiry': days_to_expiry,
            'available_expirations': list(expirations),
            'weighted_iv': round(weighted_iv, 2),
            'atm_iv': round(atm_iv, 2) if atm_iv else None,
            'calls': calls,
            'puts': puts,
            'summary': {
                'total_calls': len(calls),
                'total_puts': len(puts),
                'call_volume': sum(c['volume'] for c in calls),
                'put_volume': sum(p['volume'] for p in puts),
                'call_oi': sum(c['open_interest'] for c in calls),
                'put_oi': sum(p['open_interest'] for p in puts)
            }
        }

    except Exception as e:
        logger.error(f"Error fetching options data for {symbol}: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def fetch_history(
    symbol: str,
    period: str = "6mo",
    interval: str = "1d"
) -> Dict[str, Any]:
    """
    Fetch historical OHLCV data

    Period options: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
    Interval options: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
    """
    try:
        ticker = _get_ticker(symbol)
        hist = ticker.history(period=period)

        if hist is None or hist.empty:
            return {
                'success': False,
                'error': f'No historical data for {symbol}'
            }

        return {
            'success': True,
            'symbol': symbol.upper(),
            'period': period,
            'interval': interval,
            'data_points': len(hist),
            'data_source': 'defeatbeta' if (DATA_PROVIDER_AVAILABLE and hasattr(ticker, '_yf_failed') and ticker._yf_failed) else 'yfinance',
            'dates': hist.index.strftime('%Y-%m-%d').tolist(),
            'open': [round(float(x), 2) for x in hist['Open'].tolist()],
            'high': [round(float(x), 2) for x in hist['High'].tolist()],
            'low': [round(float(x), 2) for x in hist['Low'].tolist()],
            'close': [round(float(x), 2) for x in hist['Close'].tolist()],
            'volume': [int(x) for x in hist['Volume'].tolist()]
        }

    except Exception as e:
        logger.error(f"Error fetching history for {symbol}: {e}")
        return {
            'success': False,
            'error': str(e)
        }

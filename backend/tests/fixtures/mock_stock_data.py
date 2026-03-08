"""
Mock stock data fixtures for testing stock analysis components.

Provides realistic AAPL sample data including:
- Price and quote data (QuoteData)
- Fundamentals (FundamentalsData)
- Company info (CompanyInfo)
- Historical OHLCV DataFrame (HistoryData)
- Technical indicator helpers
"""
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta


# ---------------------------------------------------------------------------
# Raw price / quote data
# ---------------------------------------------------------------------------

AAPL_QUOTE = {
    'symbol': 'AAPL',
    'current_price': 189.84,
    'previous_close': 188.01,
    'open_price': 188.42,
    'day_high': 190.55,
    'day_low': 187.96,
    'volume': 47_520_301,
    'market_cap': 2_950_000_000_000,
    'timestamp': datetime(2026, 2, 7, 16, 0, 0),
    'source': 'test',
}

AAPL_QUOTE_DICT = {
    'currentPrice': 189.84,
    'regularMarketPrice': 189.84,
    'previousClose': 188.01,
    'open': 188.42,
    'dayHigh': 190.55,
    'dayLow': 187.96,
    'volume': 47_520_301,
    'marketCap': 2_950_000_000_000,
}


# ---------------------------------------------------------------------------
# Fundamental data
# ---------------------------------------------------------------------------

AAPL_FUNDAMENTALS = {
    'symbol': 'AAPL',
    # Valuation
    'pe_ratio': 31.2,
    'forward_pe': 28.5,
    'pb_ratio': 48.6,
    'ps_ratio': 8.1,
    'peg_ratio': 2.8,
    'ev_ebitda': 25.4,
    # Profitability
    'profit_margin': 0.264,
    'operating_margin': 0.302,
    'roe': 1.56,
    'roa': 0.286,
    # Growth
    'revenue_growth': 0.089,
    'earnings_growth': 0.112,
    # Other
    'beta': 1.24,
    'dividend_yield': 0.0052,
    'eps_trailing': 6.08,
    'eps_forward': 6.66,
    # Analyst
    'target_high': 240.0,
    'target_low': 155.0,
    'target_mean': 205.0,
    'recommendation': 'buy',
    'source': 'test',
}

AAPL_FUNDAMENTALS_DICT = {
    'trailingPE': 31.2,
    'forwardPE': 28.5,
    'priceToBook': 48.6,
    'priceToSalesTrailing12Months': 8.1,
    'pegRatio': 2.8,
    'enterpriseToEbitda': 25.4,
    'profitMargins': 0.264,
    'operatingMargins': 0.302,
    'returnOnEquity': 1.56,
    'returnOnAssets': 0.286,
    'revenueGrowth': 0.089,
    'earningsGrowth': 0.112,
    'beta': 1.24,
    'dividendYield': 0.0052,
    'trailingEps': 6.08,
    'forwardEps': 6.66,
    'targetHighPrice': 240.0,
    'targetLowPrice': 155.0,
    'targetMeanPrice': 205.0,
    'recommendationKey': 'buy',
}


# ---------------------------------------------------------------------------
# Company info
# ---------------------------------------------------------------------------

AAPL_INFO = {
    'symbol': 'AAPL',
    'name': 'Apple Inc.',
    'sector': 'Technology',
    'industry': 'Consumer Electronics',
    'country': 'United States',
    'description': 'Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories worldwide.',
    'employees': 161_000,
    'website': 'https://www.apple.com',
    'currency': 'USD',
    'exchange': 'NMS',
    'source': 'test',
}


# ---------------------------------------------------------------------------
# Historical OHLCV data (30 trading days)
# ---------------------------------------------------------------------------

def make_aapl_history_df(days: int = 30, end_date: date = None) -> pd.DataFrame:
    """
    Generate a realistic AAPL price history DataFrame.

    Args:
        days: Number of trading days to generate.
        end_date: Last trading day (default: 2026-02-07).

    Returns:
        pd.DataFrame with DatetimeIndex and Open/High/Low/Close/Volume columns.
    """
    if end_date is None:
        end_date = date(2026, 2, 7)

    # Build business day index going backwards
    dates = pd.bdate_range(end=end_date, periods=days)

    np.random.seed(42)
    base_price = 185.0
    returns = np.random.normal(loc=0.0005, scale=0.012, size=days)
    close_prices = base_price * np.cumprod(1 + returns)

    # Open is close of previous day with small noise
    open_prices = np.roll(close_prices, 1)
    open_prices[0] = base_price
    open_prices = open_prices * (1 + np.random.normal(0, 0.003, days))

    high_prices = np.maximum(open_prices, close_prices) * (1 + np.abs(np.random.normal(0, 0.005, days)))
    low_prices = np.minimum(open_prices, close_prices) * (1 - np.abs(np.random.normal(0, 0.005, days)))
    volumes = np.random.randint(35_000_000, 65_000_000, size=days)

    df = pd.DataFrame({
        'Open': np.round(open_prices, 2),
        'High': np.round(high_prices, 2),
        'Low': np.round(low_prices, 2),
        'Close': np.round(close_prices, 2),
        'Volume': volumes,
    }, index=dates)
    df.index.name = 'Date'
    return df


# Pre-built 30-day history for quick fixture access
AAPL_HISTORY_DF = make_aapl_history_df(30)


# ---------------------------------------------------------------------------
# Technical indicator snapshot (pre-computed values for tests)
# ---------------------------------------------------------------------------

AAPL_TECHNICAL_INDICATORS = {
    # Moving averages
    'sma_20': 188.45,
    'sma_50': 185.20,
    'sma_200': 178.90,
    'ema_12': 189.10,
    'ema_26': 187.30,

    # MACD
    'macd_line': 1.80,
    'macd_signal': 1.45,
    'macd_histogram': 0.35,

    # RSI
    'rsi_14': 58.7,

    # Bollinger Bands (20-day, 2 std)
    'bb_upper': 194.20,
    'bb_middle': 188.45,
    'bb_lower': 182.70,

    # ATR
    'atr_14': 3.25,

    # Stochastic
    'stoch_k': 68.2,
    'stoch_d': 64.5,

    # Volume
    'avg_volume_20': 48_500_000,
    'volume_ratio': 0.98,  # today's volume / avg

    # Trend
    'adx': 24.3,
    'trend_direction': 'bullish',
}


# ---------------------------------------------------------------------------
# Earnings data
# ---------------------------------------------------------------------------

AAPL_QUARTERLY_EARNINGS = [
    {'date': '2025-Q4', 'reported_eps': 2.40, 'estimated_eps': 2.35, 'surprise_pct': 2.1,
     'revenue': 124_300_000_000, 'estimated_revenue': 122_500_000_000},
    {'date': '2025-Q3', 'reported_eps': 1.64, 'estimated_eps': 1.60, 'surprise_pct': 2.5,
     'revenue': 94_930_000_000, 'estimated_revenue': 94_200_000_000},
    {'date': '2025-Q2', 'reported_eps': 1.40, 'estimated_eps': 1.35, 'surprise_pct': 3.7,
     'revenue': 85_780_000_000, 'estimated_revenue': 84_500_000_000},
    {'date': '2025-Q1', 'reported_eps': 1.53, 'estimated_eps': 1.50, 'surprise_pct': 2.0,
     'revenue': 90_750_000_000, 'estimated_revenue': 90_000_000_000},
]


# ---------------------------------------------------------------------------
# Full combined ticker data dict (backward-compatible with yf.Ticker().info)
# ---------------------------------------------------------------------------

AAPL_TICKER_DATA = {
    **AAPL_QUOTE_DICT,
    **AAPL_FUNDAMENTALS_DICT,
    'symbol': 'AAPL',
    'shortName': 'Apple Inc.',
    'longName': 'Apple Inc.',
    'sector': 'Technology',
    'industry': 'Consumer Electronics',
    'country': 'United States',
    'longBusinessSummary': AAPL_INFO['description'],
    'fullTimeEmployees': 161_000,
    'website': 'https://www.apple.com',
    'currency': 'USD',
    'exchange': 'NMS',
}


# ---------------------------------------------------------------------------
# Helper: build QuoteData / FundamentalsData / CompanyInfo / HistoryData
# ---------------------------------------------------------------------------

def make_quote_data():
    """Build a QuoteData dataclass instance from the AAPL fixtures."""
    from app.services.market_data.interfaces import QuoteData
    return QuoteData(**AAPL_QUOTE)


def make_fundamentals_data():
    """Build a FundamentalsData dataclass instance from the AAPL fixtures."""
    from app.services.market_data.interfaces import FundamentalsData
    return FundamentalsData(**AAPL_FUNDAMENTALS)


def make_company_info():
    """Build a CompanyInfo dataclass instance from the AAPL fixtures."""
    from app.services.market_data.interfaces import CompanyInfo
    return CompanyInfo(**AAPL_INFO)


def make_history_data(days: int = 30):
    """Build a HistoryData dataclass instance from the AAPL fixtures."""
    from app.services.market_data.interfaces import HistoryData
    df = make_aapl_history_df(days)
    return HistoryData(
        symbol='AAPL',
        df=df,
        period=f'{days}d',
        source='test',
    )

"""
Market Detection Module

Provides unified market detection logic for determining which market a symbol belongs to.
This is the single source of truth for market detection across the entire application.

Supported Markets:
- US: United States (default)
- CN: China A-shares (Shanghai & Shenzhen)
- HK: Hong Kong
"""

from typing import Tuple, Optional
from .interfaces import Market


# A-share stock code prefix rules (for 6-digit codes without suffix)
CN_STOCK_PREFIX_RULES = {
    '60': 'SS',    # Shanghai Main Board (上海主板)
    '68': 'SS',    # Shanghai STAR Market (科创板)
    '00': 'SZ',    # Shenzhen Main Board (深圳主板)
    '30': 'SZ',    # Shenzhen ChiNext (创业板)
}

# Ticker suffix to market mapping
TICKER_SUFFIX_TO_MARKET = {
    '.SS': Market.CN,   # Shanghai Stock Exchange
    '.SZ': Market.CN,   # Shenzhen Stock Exchange
    '.SH': Market.CN,   # Shanghai (alternative suffix)
    '.HK': Market.HK,   # Hong Kong Exchange
}


def detect_market(symbol: str) -> Market:
    """
    Detect which market a symbol belongs to.

    This is the primary market detection function and should be used throughout
    the application for consistent market identification.

    Detection Rules (in order of priority):
    1. Suffix-based: .HK → HK, .SS/.SZ/.SH → CN
    2. Prefix-based: 6-digit codes starting with 60/68/00/30 → CN
    3. Default: US market

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL", "0700.HK", "600519")

    Returns:
        Market enum (US, HK, or CN)

    Examples:
        >>> detect_market("AAPL")
        Market.US
        >>> detect_market("0700.HK")
        Market.HK
        >>> detect_market("600519")
        Market.CN
        >>> detect_market("000001")
        Market.CN
        >>> detect_market("600519.SS")
        Market.CN
        >>> detect_market("300750")
        Market.CN
    """
    symbol_upper = symbol.upper().strip()

    # 1. Check suffix first (most explicit)
    for suffix, market in TICKER_SUFFIX_TO_MARKET.items():
        if symbol_upper.endswith(suffix):
            return market

    # 2. Check if it's a 6-digit A-share code (without suffix)
    base_ticker = symbol_upper.split('.')[0]
    if base_ticker.isdigit() and len(base_ticker) == 6:
        prefix = base_ticker[:2]
        if prefix in CN_STOCK_PREFIX_RULES:
            return Market.CN

    # 3. Default to US market
    return Market.US


def detect_market_with_exchange(symbol: str) -> Tuple[Market, Optional[str]]:
    """
    Detect market and specific exchange for a symbol.

    Args:
        symbol: Stock ticker symbol

    Returns:
        Tuple of (Market, exchange_code) where exchange_code is:
        - 'SS' for Shanghai Stock Exchange
        - 'SZ' for Shenzhen Stock Exchange
        - 'HK' for Hong Kong Exchange
        - None for US stocks

    Examples:
        >>> detect_market_with_exchange("600519")
        (Market.CN, 'SS')
        >>> detect_market_with_exchange("000001")
        (Market.CN, 'SZ')
        >>> detect_market_with_exchange("0700.HK")
        (Market.HK, 'HK')
        >>> detect_market_with_exchange("AAPL")
        (Market.US, None)
    """
    symbol_upper = symbol.upper().strip()

    # Check suffix first
    if symbol_upper.endswith('.HK'):
        return Market.HK, 'HK'
    if symbol_upper.endswith('.SS') or symbol_upper.endswith('.SH'):
        return Market.CN, 'SS'
    if symbol_upper.endswith('.SZ'):
        return Market.CN, 'SZ'

    # Check 6-digit A-share codes
    base_ticker = symbol_upper.split('.')[0]
    if base_ticker.isdigit() and len(base_ticker) == 6:
        prefix = base_ticker[:2]
        exchange = CN_STOCK_PREFIX_RULES.get(prefix)
        if exchange:
            return Market.CN, exchange

    # Default to US
    return Market.US, None


def normalize_symbol(symbol: str) -> str:
    """
    Normalize a symbol to its canonical form with proper suffix.

    For A-share stocks without suffix, adds the appropriate exchange suffix.
    For HK stocks, strips leading zeros (Yahoo Finance format).
    For other markets, returns the symbol as-is (uppercase).

    Args:
        symbol: Stock ticker symbol

    Returns:
        Normalized symbol string

    Examples:
        >>> normalize_symbol("600519")
        '600519.SS'
        >>> normalize_symbol("000001")
        '000001.SZ'
        >>> normalize_symbol("AAPL")
        'AAPL'
        >>> normalize_symbol("0700.HK")
        '700.HK'
        >>> normalize_symbol("700")
        '700.HK'
    """
    symbol_upper = symbol.upper().strip()

    # Handle existing suffix
    if '.HK' in symbol_upper:
        # HK stocks: strip leading zeros (Yahoo Finance needs 179.HK not 0179.HK)
        base = symbol_upper.replace('.HK', '')
        if base.isdigit():
            stripped = base.lstrip('0') or '0'
            return f"{stripped}.HK"
        return symbol_upper

    # Check other known suffixes
    for suffix in TICKER_SUFFIX_TO_MARKET.keys():
        if symbol_upper.endswith(suffix):
            return symbol_upper

    # Check if it's a 6-digit A-share code without suffix
    base_ticker = symbol_upper.split('.')[0]
    if base_ticker.isdigit() and len(base_ticker) == 6:
        prefix = base_ticker[:2]
        exchange = CN_STOCK_PREFIX_RULES.get(prefix)
        if exchange:
            return f"{base_ticker}.{exchange}"

    # Check if it's a HK stock (1-5 digit number without suffix)
    if base_ticker.isdigit():
        stripped = base_ticker.lstrip('0') or '0'
        if len(stripped) <= 5:
            return f"{stripped}.HK"

    # Return as-is for US stocks
    return symbol_upper


def get_market_name(market: Market, language: str = 'en') -> str:
    """
    Get human-readable market name.

    Args:
        market: Market enum
        language: 'en' for English, 'zh' for Chinese

    Returns:
        Market name string
    """
    names = {
        Market.US: {'en': 'US Market', 'zh': '美股'},
        Market.CN: {'en': 'China A-Share', 'zh': 'A股'},
        Market.HK: {'en': 'Hong Kong', 'zh': '港股'},
    }
    return names.get(market, {}).get(language, str(market.value))


def is_a_share(symbol: str) -> bool:
    """Check if a symbol is a China A-share stock."""
    return detect_market(symbol) == Market.CN


def is_hk_stock(symbol: str) -> bool:
    """Check if a symbol is a Hong Kong stock."""
    return detect_market(symbol) == Market.HK


def is_us_stock(symbol: str) -> bool:
    """Check if a symbol is a US stock."""
    return detect_market(symbol) == Market.US

"""
Market Detection Module

Provides unified market detection logic for determining which market a symbol belongs to.
This is the single source of truth for market detection across the entire application.

Supported Markets:
- US: United States (default)
- CN: China A-shares (Shanghai & Shenzhen)
- HK: Hong Kong
- COMMODITY: 商品期货期权 (Au/Ag/Cu/Al/M)
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

# 商品期货期权品种代码白名单
COMMODITY_PRODUCT_CODES = {'au', 'ag', 'cu', 'al', 'm'}

# 期货交易所前缀
FUTURES_EXCHANGE_PREFIXES = {'shfe', 'dce', 'czce', 'ine'}


def is_commodity_symbol(symbol: str) -> bool:
    """
    Check if a symbol is a commodity futures option product.

    Recognizes formats: 'au', 'au2604', 'SHFE.au2604'

    Args:
        symbol: Symbol string

    Returns:
        True if symbol is a commodity product

    Examples:
        >>> is_commodity_symbol("au")
        True
        >>> is_commodity_symbol("au2604")
        True
        >>> is_commodity_symbol("SHFE.au2604")
        True
        >>> is_commodity_symbol("m2605")
        True
        >>> is_commodity_symbol("AAPL")
        False
    """
    s = symbol.lower().strip()
    # Strip exchange prefix: SHFE.au2506 -> au2506
    if '.' in s:
        parts = s.split('.')
        if parts[0] in FUTURES_EXCHANGE_PREFIXES:
            s = parts[1]
        else:
            return False  # Has a dot but not a futures exchange prefix
    # Extract alphabetic product code
    product = ''.join(c for c in s if c.isalpha())
    return product in COMMODITY_PRODUCT_CODES


def detect_market(symbol: str) -> Market:
    """
    Detect which market a symbol belongs to.

    This is the primary market detection function and should be used throughout
    the application for consistent market identification.

    Detection Rules (in order of priority):
    1. Suffix-based: .HK → HK, .SS/.SZ/.SH → CN
    2. Prefix-based: 6-digit codes starting with 60/68/00/30 → CN
    3. Commodity futures: au/ag/cu/al/m (with optional contract month)
    4. Default: US market

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL", "0700.HK", "600519", "au2604")

    Returns:
        Market enum (US, HK, CN, or COMMODITY)

    Examples:
        >>> detect_market("AAPL")
        Market.US
        >>> detect_market("0700.HK")
        Market.HK
        >>> detect_market("600519")
        Market.CN
        >>> detect_market("au")
        Market.COMMODITY
        >>> detect_market("au2604")
        Market.COMMODITY
        >>> detect_market("m2605")
        Market.COMMODITY
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

    # 3. Check commodity futures (before US default)
    if is_commodity_symbol(symbol):
        return Market.COMMODITY

    # 4. Default to US market
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
    For HK stocks, pads to 4 digits (Yahoo Finance format: 0179.HK, 0700.HK).
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
        '0700.HK'
        >>> normalize_symbol("700")
        '0700.HK'
        >>> normalize_symbol("179.HK")
        '0179.HK'
    """
    symbol_upper = symbol.upper().strip()

    # Handle existing suffix
    if '.HK' in symbol_upper:
        # HK stocks: pad to 4 digits (Yahoo Finance needs 0179.HK not 179.HK)
        base = symbol_upper.replace('.HK', '')
        if base.isdigit():
            normalized = base.lstrip('0').zfill(4)
            return f"{normalized}.HK"
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
            # Pad to 4 digits for Yahoo Finance format
            normalized = stripped.zfill(4)
            return f"{normalized}.HK"

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
        Market.COMMODITY: {'en': 'Commodity Futures', 'zh': '商品期货'},
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


def is_commodity(symbol: str) -> bool:
    """Check if a symbol is a commodity futures option."""
    return detect_market(symbol) == Market.COMMODITY

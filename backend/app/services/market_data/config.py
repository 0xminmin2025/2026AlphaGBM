"""
Market Data Configuration

Defines provider configurations, priorities, rate limits, and cache settings.
"""

from dataclasses import dataclass, field
from typing import List, Dict
from .interfaces import DataType, Market


@dataclass
class ProviderConfig:
    """Configuration for a single data provider."""
    name: str
    enabled: bool = True
    priority: int = 100  # Lower = higher priority

    # Rate limiting
    requests_per_minute: int = 60
    requests_per_day: int = 10000

    # Capabilities
    supported_data_types: List[DataType] = field(default_factory=list)
    supported_markets: List[Market] = field(default_factory=list)

    # Fallback behavior
    cooldown_on_error_seconds: int = 60  # Wait time before retrying after failure
    max_consecutive_failures: int = 3    # Failures before marking unhealthy
    auto_recover: bool = True            # Auto-recover after cooldown


@dataclass
class CacheConfig:
    """Cache configuration for market data."""
    # L1: In-memory cache (fast, per-process)
    memory_enabled: bool = True
    memory_ttl_quote: int = 60          # 1 minute for real-time quotes
    memory_ttl_history: int = 300       # 5 minutes for historical
    memory_ttl_fundamentals: int = 3600  # 1 hour for fundamentals
    memory_ttl_info: int = 86400        # 24 hours for company info
    memory_ttl_options: int = 120       # 2 minutes for options (volatile)
    memory_max_size: int = 1000         # Max entries before eviction

    # L2: Database cache (for daily analysis results)
    db_cache_enabled: bool = True
    db_cache_table: str = "market_data_cache"

    # Deduplication
    dedup_window_ms: int = 500  # Requests within this window share result


# Default provider configurations
PROVIDER_CONFIGS: Dict[str, ProviderConfig] = {
    "yfinance": ProviderConfig(
        name="yfinance",
        priority=10,  # Primary provider
        requests_per_minute=100,
        requests_per_day=2000,  # Conservative due to rate limits
        supported_data_types=[
            DataType.QUOTE,
            DataType.HISTORY,
            DataType.INFO,
            DataType.FUNDAMENTALS,
            DataType.OPTIONS_CHAIN,
            DataType.OPTIONS_EXPIRATIONS,
            DataType.EARNINGS,
            DataType.MACRO,
        ],
        supported_markets=[Market.US, Market.HK],
        cooldown_on_error_seconds=60,
        max_consecutive_failures=3,
    ),
    "defeatbeta": ProviderConfig(
        name="defeatbeta",
        priority=20,  # First fallback for stock data
        requests_per_minute=1000,  # Local DuckDB, no real limit
        requests_per_day=100000,
        supported_data_types=[
            DataType.QUOTE,
            DataType.HISTORY,
            DataType.INFO,
            DataType.FUNDAMENTALS,
            DataType.EARNINGS,
        ],
        supported_markets=[Market.US],  # Only US stocks
        cooldown_on_error_seconds=30,
        max_consecutive_failures=5,
    ),
    "tiger": ProviderConfig(
        name="tiger",
        priority=15,  # Preferred for options
        requests_per_minute=60,
        requests_per_day=5000,
        supported_data_types=[
            DataType.QUOTE,
            DataType.HISTORY,
            DataType.OPTIONS_CHAIN,
            DataType.OPTIONS_EXPIRATIONS,
        ],
        supported_markets=[Market.US, Market.HK, Market.CN],
        cooldown_on_error_seconds=60,
        max_consecutive_failures=3,
    ),
    "alpha_vantage": ProviderConfig(
        name="alpha_vantage",
        enabled=True,  # Enabled - will auto-disable if no API key
        priority=25,   # After defeatbeta, before other fallbacks
        requests_per_minute=5,  # Free tier limit
        requests_per_day=500,
        supported_data_types=[
            DataType.QUOTE,
            DataType.HISTORY,
            DataType.INFO,
            DataType.FUNDAMENTALS,
        ],
        supported_markets=[Market.US],
        cooldown_on_error_seconds=120,
        max_consecutive_failures=2,
    ),
}


# Symbols that are indices/futures/macro (special handling needed)
MACRO_TICKERS = {
    # US Indices
    "^GSPC", "^DJI", "^IXIC", "^RUT", "^VIX", "^TNX", "^TYX", "^FVX",
    # Currency/Commodities
    "DX-Y.NYB", "GC=F", "CL=F", "SI=F",
    # Other
    "^FTSE", "^N225", "^HSI",
}

# ETFs that behave like indices but are tradeable
INDEX_ETFS = {"SPY", "QQQ", "IWM", "DIA", "VOO", "VTI"}


def is_macro_ticker(symbol: str) -> bool:
    """Check if symbol is a macro/index ticker that may need special handling."""
    if symbol in MACRO_TICKERS:
        return True
    if symbol.startswith("^"):
        return True
    if symbol.endswith("=F") or symbol.endswith(".NYB"):
        return True
    return False


def is_index_etf(symbol: str) -> bool:
    """Check if symbol is an index ETF."""
    return symbol.upper() in INDEX_ETFS


def get_market_for_symbol(symbol: str) -> Market:
    """Determine market for a symbol based on suffix/pattern."""
    symbol_upper = symbol.upper()
    if symbol_upper.endswith(".HK"):
        return Market.HK
    elif symbol_upper.endswith(".SS") or symbol_upper.endswith(".SZ"):
        return Market.CN
    else:
        return Market.US


def get_timezone_for_market(market: Market) -> str:
    """Get timezone string for a market."""
    return {
        Market.US: "America/New_York",
        Market.HK: "Asia/Hong_Kong",
        Market.CN: "Asia/Shanghai",
    }.get(market, "America/New_York")

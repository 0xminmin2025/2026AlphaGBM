"""
Market Data Configuration

Defines provider configurations, priorities, rate limits, and cache settings.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from .interfaces import DataType, Market


@dataclass
class ProviderCacheTTL:
    """Per-provider cache TTL configuration (in seconds)."""
    quote: int = 60                  # Real-time quotes
    history: int = 300               # Historical data
    fundamentals: int = 3600         # PE, PB, ROE etc.
    info: int = 86400                # Company info
    options_chain: int = 120         # Options chain (volatile)
    options_expirations: int = 300   # Expiration dates
    earnings: int = 3600             # Earnings data
    macro: int = 60                  # VIX, indices

    def get_ttl(self, data_type: DataType) -> int:
        """Get TTL for a specific data type."""
        ttl_map = {
            DataType.QUOTE: self.quote,
            DataType.HISTORY: self.history,
            DataType.FUNDAMENTALS: self.fundamentals,
            DataType.INFO: self.info,
            DataType.OPTIONS_CHAIN: self.options_chain,
            DataType.OPTIONS_EXPIRATIONS: self.options_expirations,
            DataType.EARNINGS: self.earnings,
            DataType.MACRO: self.macro,
        }
        return ttl_map.get(data_type, 300)


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

    # Per-provider cache TTL (None uses global defaults)
    cache_ttl: Optional[ProviderCacheTTL] = None


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

    def get_default_ttl(self, data_type: DataType) -> int:
        """Get default TTL for a data type."""
        ttl_map = {
            DataType.QUOTE: self.memory_ttl_quote,
            DataType.HISTORY: self.memory_ttl_history,
            DataType.FUNDAMENTALS: self.memory_ttl_fundamentals,
            DataType.INFO: self.memory_ttl_info,
            DataType.OPTIONS_CHAIN: self.memory_ttl_options,
            DataType.OPTIONS_EXPIRATIONS: self.memory_ttl_options,
            DataType.EARNINGS: self.memory_ttl_fundamentals,
            DataType.MACRO: self.memory_ttl_quote,
        }
        return ttl_map.get(data_type, 300)


# Per-provider cache TTL configurations
# Each provider can have different TTLs based on their data freshness and reliability

YFINANCE_CACHE_TTL = ProviderCacheTTL(
    quote=60,                 # 1 minute - real-time quotes
    history=300,              # 5 minutes - historical data
    fundamentals=3600,        # 1 hour - PE, PB, ROE
    info=86400,               # 24 hours - company info
    options_chain=120,        # 2 minutes - options are volatile
    options_expirations=300,  # 5 minutes - expiry dates
    earnings=3600,            # 1 hour - earnings
    macro=60,                 # 1 minute - VIX, indices
)

DEFEATBETA_CACHE_TTL = ProviderCacheTTL(
    quote=120,                # 2 minutes - local DuckDB, data may be slightly delayed
    history=600,              # 10 minutes - local data, longer cache OK
    fundamentals=7200,        # 2 hours - stable data from local source
    info=172800,              # 48 hours - company info changes rarely
    options_chain=120,        # N/A - defeatbeta doesn't support options
    options_expirations=300,  # N/A
    earnings=7200,            # 2 hours - earnings data
    macro=120,                # N/A
)

TIGER_CACHE_TTL = ProviderCacheTTL(
    quote=60,                 # 1 minute - Tiger has real-time quotes
    history=300,              # 5 minutes - historical data
    fundamentals=3600,        # N/A - Tiger doesn't have fundamentals
    info=86400,               # N/A
    options_chain=90,         # 1.5 minutes - Tiger is priority for options, keep fresh
    options_expirations=180,  # 3 minutes - expiry dates
    earnings=3600,            # N/A
    macro=60,                 # 1 minute
)

ALPHA_VANTAGE_CACHE_TTL = ProviderCacheTTL(
    quote=300,                # 5 minutes - rate limited, cache longer
    history=900,              # 15 minutes - rate limited, cache longer
    fundamentals=7200,        # 2 hours - rate limited
    info=172800,              # 48 hours - rate limited, cache very long
    options_chain=300,        # N/A
    options_expirations=300,  # N/A
    earnings=7200,            # N/A
    macro=300,                # N/A
)

TUSHARE_CACHE_TTL = ProviderCacheTTL(
    quote=120,                # 2 minutes - Tushare daily data (not real-time)
    history=600,              # 10 minutes - historical data
    fundamentals=3600,        # 1 hour - PE, PB, ROE etc.
    info=86400,               # 24 hours - company info
    options_chain=300,        # N/A - no options
    options_expirations=300,  # N/A
    earnings=3600,            # 1 hour - earnings
    macro=120,                # 2 minutes - index data
)

AKSHARE_COMMODITY_CACHE_TTL = ProviderCacheTTL(
    quote=120,                # 2 minutes - Sina delayed ~15s
    history=600,              # 10 minutes - historical data
    fundamentals=3600,        # N/A
    info=86400,               # N/A
    options_chain=120,        # 2 minutes - options chain
    options_expirations=300,  # 5 minutes - contract list
    earnings=3600,            # N/A
    macro=120,                # N/A
)

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
        cache_ttl=YFINANCE_CACHE_TTL,
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
        cache_ttl=DEFEATBETA_CACHE_TTL,
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
        cache_ttl=TIGER_CACHE_TTL,
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
        cache_ttl=ALPHA_VANTAGE_CACHE_TTL,
    ),
    "tushare": ProviderConfig(
        name="tushare",
        enabled=True,  # Enabled - will auto-disable if no API token
        priority=10,   # Primary provider for A-shares
        requests_per_minute=200,  # Tushare Pro rate limit
        requests_per_day=10000,
        supported_data_types=[
            DataType.QUOTE,
            DataType.HISTORY,
            DataType.INFO,
            DataType.FUNDAMENTALS,
        ],
        supported_markets=[Market.CN],  # A-share only
        cooldown_on_error_seconds=60,
        max_consecutive_failures=3,
        cache_ttl=TUSHARE_CACHE_TTL,
    ),
    "akshare_commodity": ProviderConfig(
        name="akshare_commodity",
        enabled=True,
        priority=10,   # Primary (only) provider for commodity options
        requests_per_minute=30,  # Sina API conservative limit
        requests_per_day=5000,
        supported_data_types=[
            DataType.QUOTE,
            DataType.HISTORY,
            DataType.OPTIONS_CHAIN,
            DataType.OPTIONS_EXPIRATIONS,
        ],
        supported_markets=[Market.COMMODITY],
        cooldown_on_error_seconds=60,
        max_consecutive_failures=3,
        cache_ttl=AKSHARE_COMMODITY_CACHE_TTL,
    ),
}


def get_provider_cache_ttl(provider_name: str, data_type: DataType) -> int:
    """
    Get cache TTL for a provider and data type.

    Args:
        provider_name: Name of the provider
        data_type: Type of data

    Returns:
        TTL in seconds
    """
    config = PROVIDER_CONFIGS.get(provider_name)
    if config and config.cache_ttl:
        return config.cache_ttl.get_ttl(data_type)
    # Fall back to default CacheConfig TTLs
    default_config = CacheConfig()
    return default_config.get_default_ttl(data_type)


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
    """
    Determine market for a symbol based on suffix/pattern.

    Uses the canonical detect_market from market_detector module.

    Args:
        symbol: Stock ticker symbol

    Returns:
        Market enum (US, HK, CN, or COMMODITY)
    """
    from .market_detector import detect_market
    return detect_market(symbol)


def get_timezone_for_market(market: Market) -> str:
    """Get timezone string for a market."""
    return {
        Market.US: "America/New_York",
        Market.HK: "Asia/Hong_Kong",
        Market.CN: "Asia/Shanghai",
        Market.COMMODITY: "Asia/Shanghai",  # 国内商品期货
    }.get(market, "America/New_York")

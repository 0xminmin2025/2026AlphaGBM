"""
Market Data Service - Unified Data Provider Abstraction Layer

Provides a single entry point for all market data access with:
- Multi-provider support (yfinance, defeatbeta, Tiger API)
- Automatic failover on rate limits or errors
- Request deduplication (no duplicate API calls)
- Multi-level caching (memory -> database)
- Health monitoring per provider

Usage:
    from app.services.market_data import market_data_service

    # Get quote
    quote = market_data_service.get_quote("AAPL")

    # Get history
    history = market_data_service.get_history("AAPL", period="1mo")

    # Get fundamentals
    fundamentals = market_data_service.get_fundamentals("AAPL")

    # Get options chain
    chain = market_data_service.get_options_chain("AAPL", "2024-02-16")

    # Backward compatible dict (like yf.Ticker().info)
    data = market_data_service.get_ticker_data("AAPL")
"""

from .service import MarketDataService, market_data_service
from .interfaces import (
    DataType,
    Market,
    QuoteData,
    FundamentalsData,
    CompanyInfo,
    OptionsChainData,
    HistoryData,
    DataProviderAdapter,
    DataFetchResult,
)
from .config import ProviderConfig, CacheConfig, PROVIDER_CONFIGS

__all__ = [
    # Main service
    "MarketDataService",
    "market_data_service",
    # Interfaces
    "DataType",
    "Market",
    "QuoteData",
    "FundamentalsData",
    "CompanyInfo",
    "OptionsChainData",
    "HistoryData",
    "DataProviderAdapter",
    "DataFetchResult",
    # Config
    "ProviderConfig",
    "CacheConfig",
    "PROVIDER_CONFIGS",
]

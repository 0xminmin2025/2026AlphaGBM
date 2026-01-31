"""
Market Data Service - Central Entry Point

Provides a unified interface for all market data access with:
- Multi-provider support with automatic failover
- Request deduplication (no duplicate API calls)
- Multi-level caching
- Health monitoring per provider
"""

import logging
import time
from typing import Optional, List, Dict, Any
from datetime import date
from threading import Lock
import pandas as pd

from .interfaces import (
    DataProviderAdapter, DataType, Market, ProviderStatus,
    QuoteData, FundamentalsData, CompanyInfo, HistoryData,
    OptionsChainData, EarningsData, DataFetchResult
)
from .config import (
    PROVIDER_CONFIGS, ProviderConfig, CacheConfig,
    get_market_for_symbol
)
from .cache import MultiLevelCache
from .deduplicator import RequestDeduplicator

logger = logging.getLogger(__name__)


class MarketDataService:
    """
    Central service for all market data access.

    Features:
    - Multi-provider support with automatic failover
    - Request deduplication (no duplicate API calls)
    - Multi-level caching (memory -> database)
    - Health monitoring per provider

    Usage:
        from app.services.market_data import market_data_service

        # Get quote (uses cache, dedup, and failover automatically)
        quote = market_data_service.get_quote("AAPL")

        # Get history
        history = market_data_service.get_history("AAPL", period="1mo")

        # Backward compatible dict (like yf.Ticker().info)
        data = market_data_service.get_ticker_data("AAPL")
    """

    _instance = None
    _lock = Lock()

    def __new__(cls):
        """Singleton pattern to ensure single instance."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._adapters: Dict[str, DataProviderAdapter] = {}
        self._configs: Dict[str, ProviderConfig] = PROVIDER_CONFIGS.copy()
        self._cache = MultiLevelCache(CacheConfig())
        self._deduplicator = RequestDeduplicator(window_ms=500)

        self._register_default_adapters()
        self._initialized = True
        logger.info("[MarketData] Service initialized")

    def _register_default_adapters(self):
        """Register all available data provider adapters."""
        from .adapters import YFinanceAdapter, DefeatBetaAdapter, TigerAdapter, AlphaVantageAdapter

        self.register_adapter(YFinanceAdapter())
        self.register_adapter(DefeatBetaAdapter())
        self.register_adapter(TigerAdapter())
        self.register_adapter(AlphaVantageAdapter())

    def register_adapter(self, adapter: DataProviderAdapter):
        """Register a new data provider adapter."""
        self._adapters[adapter.name] = adapter
        logger.info(f"[MarketData] Registered provider: {adapter.name}")

    def _get_providers_for_data_type(
        self,
        data_type: DataType,
        market: Market = Market.US,
        symbol: Optional[str] = None
    ) -> List[DataProviderAdapter]:
        """
        Get list of providers that support this data type, sorted by priority.
        Excludes unhealthy/rate-limited providers.
        """
        providers = []

        for name, adapter in self._adapters.items():
            config = self._configs.get(name)
            if not config or not config.enabled:
                continue

            # Check if provider supports this data type and market
            if data_type not in adapter.supported_data_types:
                continue
            if market not in adapter.supported_markets:
                continue

            # Check if provider supports this specific symbol
            if symbol and not adapter.supports_symbol(symbol):
                continue

            # Check health (but don't exclude - we'll try anyway as fallback)
            priority = config.priority
            if adapter.is_rate_limited():
                priority += 1000  # Deprioritize but don't exclude

            providers.append((priority, adapter))

        # Sort by priority (lower = higher priority)
        providers.sort(key=lambda x: x[0])
        return [p[1] for p in providers]

    # ─────────────────────────────────────────────────────────────
    # Public API Methods
    # ─────────────────────────────────────────────────────────────

    def get_quote(
        self,
        symbol: str,
        market: Optional[Market] = None
    ) -> Optional[QuoteData]:
        """
        Get real-time quote for a symbol.
        Uses cache, deduplication, and automatic failover.
        """
        if market is None:
            market = get_market_for_symbol(symbol)

        cache_key = symbol.upper()

        # Check cache first
        cached = self._cache.get(cache_key, DataType.QUOTE)
        if cached is not None:
            return cached

        # Use deduplicator to prevent duplicate API calls
        def fetch():
            providers = self._get_providers_for_data_type(DataType.QUOTE, market, symbol)

            for adapter in providers:
                try:
                    start = time.time()
                    result = adapter.get_quote(symbol)
                    elapsed = (time.time() - start) * 1000

                    if result:
                        logger.debug(f"[MarketData] Quote {symbol}: {adapter.name} ({elapsed:.0f}ms)")
                        self._cache.set(cache_key, result, DataType.QUOTE, source=adapter.name)
                        return result
                except Exception as e:
                    logger.warning(f"[MarketData] {adapter.name} failed for quote {symbol}: {e}")
                    continue

            return None

        return self._deduplicator.execute(
            data_type="quote",
            symbol=symbol,
            fetch_fn=fetch
        )

    def get_history(
        self,
        symbol: str,
        period: Optional[str] = None,
        start: Optional[date] = None,
        end: Optional[date] = None,
        market: Optional[Market] = None
    ) -> Optional[HistoryData]:
        """
        Get historical OHLCV data.
        """
        if market is None:
            market = get_market_for_symbol(symbol)

        cache_key = f"{symbol.upper()}:{period}:{start}:{end}"

        cached = self._cache.get(cache_key, DataType.HISTORY)
        if cached is not None:
            return cached

        def fetch():
            providers = self._get_providers_for_data_type(DataType.HISTORY, market, symbol)

            for adapter in providers:
                try:
                    start_time = time.time()
                    result = adapter.get_history(symbol, period, start, end)
                    elapsed = (time.time() - start_time) * 1000

                    if result and not result.empty:
                        logger.debug(f"[MarketData] History {symbol}: {adapter.name} ({elapsed:.0f}ms, {len(result.df)} rows)")
                        self._cache.set(cache_key, result, DataType.HISTORY, source=adapter.name)
                        return result
                except Exception as e:
                    logger.warning(f"[MarketData] {adapter.name} failed for history {symbol}: {e}")
                    continue

            return None

        return self._deduplicator.execute(
            data_type="history",
            symbol=symbol,
            fetch_fn=fetch,
            period=period,
            start=str(start) if start else None,
            end=str(end) if end else None
        )

    def get_fundamentals(
        self,
        symbol: str,
        market: Optional[Market] = None
    ) -> Optional[FundamentalsData]:
        """Get fundamental metrics for a symbol."""
        if market is None:
            market = get_market_for_symbol(symbol)

        cache_key = symbol.upper()

        cached = self._cache.get(cache_key, DataType.FUNDAMENTALS)
        if cached is not None:
            return cached

        def fetch():
            providers = self._get_providers_for_data_type(DataType.FUNDAMENTALS, market, symbol)

            for adapter in providers:
                try:
                    start = time.time()
                    result = adapter.get_fundamentals(symbol)
                    elapsed = (time.time() - start) * 1000

                    if result:
                        logger.debug(f"[MarketData] Fundamentals {symbol}: {adapter.name} ({elapsed:.0f}ms)")
                        self._cache.set(cache_key, result, DataType.FUNDAMENTALS, source=adapter.name)
                        return result
                except Exception as e:
                    logger.warning(f"[MarketData] {adapter.name} failed for fundamentals {symbol}: {e}")
                    continue

            return None

        return self._deduplicator.execute(
            data_type="fundamentals",
            symbol=symbol,
            fetch_fn=fetch
        )

    def get_info(
        self,
        symbol: str,
        market: Optional[Market] = None
    ) -> Optional[CompanyInfo]:
        """Get company info for a symbol."""
        if market is None:
            market = get_market_for_symbol(symbol)

        cache_key = symbol.upper()

        cached = self._cache.get(cache_key, DataType.INFO)
        if cached is not None:
            return cached

        def fetch():
            providers = self._get_providers_for_data_type(DataType.INFO, market, symbol)

            for adapter in providers:
                try:
                    start = time.time()
                    result = adapter.get_info(symbol)
                    elapsed = (time.time() - start) * 1000

                    if result:
                        logger.debug(f"[MarketData] Info {symbol}: {adapter.name} ({elapsed:.0f}ms)")
                        self._cache.set(cache_key, result, DataType.INFO, source=adapter.name)
                        return result
                except Exception as e:
                    logger.warning(f"[MarketData] {adapter.name} failed for info {symbol}: {e}")
                    continue

            return None

        return self._deduplicator.execute(
            data_type="info",
            symbol=symbol,
            fetch_fn=fetch
        )

    def get_options_expirations(
        self,
        symbol: str,
        market: Optional[Market] = None
    ) -> Optional[List[str]]:
        """Get available option expiration dates."""
        if market is None:
            market = get_market_for_symbol(symbol)

        cache_key = symbol.upper()

        cached = self._cache.get(cache_key, DataType.OPTIONS_EXPIRATIONS)
        if cached is not None:
            return cached

        def fetch():
            providers = self._get_providers_for_data_type(DataType.OPTIONS_EXPIRATIONS, market, symbol)

            for adapter in providers:
                try:
                    start = time.time()
                    result = adapter.get_options_expirations(symbol)
                    elapsed = (time.time() - start) * 1000

                    if result:
                        logger.debug(f"[MarketData] Options expirations {symbol}: {adapter.name} ({elapsed:.0f}ms, {len(result)} dates)")
                        self._cache.set(cache_key, result, DataType.OPTIONS_EXPIRATIONS, source=adapter.name)
                        return result
                except Exception as e:
                    logger.warning(f"[MarketData] {adapter.name} failed for options expirations {symbol}: {e}")
                    continue

            return None

        return self._deduplicator.execute(
            data_type="options_expirations",
            symbol=symbol,
            fetch_fn=fetch
        )

    def get_options_chain(
        self,
        symbol: str,
        expiry: str,
        market: Optional[Market] = None
    ) -> Optional[OptionsChainData]:
        """Get options chain for a symbol and expiry."""
        if market is None:
            market = get_market_for_symbol(symbol)

        cache_key = f"{symbol.upper()}:{expiry}"

        cached = self._cache.get(cache_key, DataType.OPTIONS_CHAIN)
        if cached is not None:
            return cached

        def fetch():
            providers = self._get_providers_for_data_type(DataType.OPTIONS_CHAIN, market, symbol)

            for adapter in providers:
                try:
                    start = time.time()
                    result = adapter.get_options_chain(symbol, expiry)
                    elapsed = (time.time() - start) * 1000

                    if result and not result.empty:
                        calls_count = len(result.calls) if result.calls is not None else 0
                        puts_count = len(result.puts) if result.puts is not None else 0
                        logger.debug(f"[MarketData] Options chain {symbol} {expiry}: {adapter.name} ({elapsed:.0f}ms, {calls_count} calls, {puts_count} puts)")
                        self._cache.set(cache_key, result, DataType.OPTIONS_CHAIN, source=adapter.name)
                        return result
                except Exception as e:
                    logger.warning(f"[MarketData] {adapter.name} failed for options chain {symbol}: {e}")
                    continue

            return None

        return self._deduplicator.execute(
            data_type="options_chain",
            symbol=symbol,
            fetch_fn=fetch,
            expiry=expiry
        )

    def get_earnings(
        self,
        symbol: str,
        market: Optional[Market] = None
    ) -> Optional[EarningsData]:
        """Get quarterly earnings data."""
        if market is None:
            market = get_market_for_symbol(symbol)

        cache_key = symbol.upper()

        cached = self._cache.get(cache_key, DataType.EARNINGS)
        if cached is not None:
            return cached

        def fetch():
            providers = self._get_providers_for_data_type(DataType.EARNINGS, market, symbol)

            for adapter in providers:
                try:
                    start = time.time()
                    result = adapter.get_earnings(symbol)
                    elapsed = (time.time() - start) * 1000

                    if result and not result.empty:
                        logger.debug(f"[MarketData] Earnings {symbol}: {adapter.name} ({elapsed:.0f}ms)")
                        self._cache.set(cache_key, result, DataType.EARNINGS, source=adapter.name)
                        return result
                except Exception as e:
                    logger.warning(f"[MarketData] {adapter.name} failed for earnings {symbol}: {e}")
                    continue

            return None

        return self._deduplicator.execute(
            data_type="earnings",
            symbol=symbol,
            fetch_fn=fetch
        )

    # ─────────────────────────────────────────────────────────────
    # Backward Compatibility Methods
    # ─────────────────────────────────────────────────────────────

    def get_ticker_data(self, symbol: str) -> Dict[str, Any]:
        """
        Get comprehensive ticker data (quote + info + fundamentals).
        Backward compatible with code expecting dict like yf.Ticker().info.
        """
        result = {'symbol': symbol}

        quote = self.get_quote(symbol)
        info = self.get_info(symbol)
        fundamentals = self.get_fundamentals(symbol)

        if quote:
            result.update(quote.to_dict())
        if info:
            result.update(info.to_dict())
        if fundamentals:
            result.update(fundamentals.to_dict())

        return result

    def get_history_df(
        self,
        symbol: str,
        period: Optional[str] = None,
        start: Optional[date] = None,
        end: Optional[date] = None
    ) -> pd.DataFrame:
        """
        Get historical data as DataFrame.
        Backward compatible with yf.Ticker().history().
        """
        history = self.get_history(symbol, period, start, end)
        if history and not history.empty:
            return history.df
        return pd.DataFrame()

    # ─────────────────────────────────────────────────────────────
    # Utility Methods
    # ─────────────────────────────────────────────────────────────

    def clear_cache(self, symbol: Optional[str] = None) -> None:
        """Clear cache (all or for specific symbol)."""
        if symbol:
            self._cache.clear_for_symbol(symbol)
        else:
            self._cache.clear()

    def get_provider_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all registered providers."""
        status = {}
        for name, adapter in self._adapters.items():
            config = self._configs.get(name)
            health = adapter.health_check()
            status[name] = {
                'health': health.value,
                'enabled': config.enabled if config else False,
                'priority': config.priority if config else 999,
                'rate_limited': adapter.is_rate_limited(),
                'supported_data_types': [dt.value for dt in adapter.supported_data_types],
                'supported_markets': [m.value for m in adapter.supported_markets],
            }
        return status

    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        return {
            'cache': self._cache.stats,
            'deduplication': self._deduplicator.stats,
            'providers': self.get_provider_status(),
        }


# Singleton instance
market_data_service = MarketDataService()

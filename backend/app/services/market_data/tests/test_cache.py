"""
Unit tests for Market Data Cache module.

Tests the LRUCache, MultiLevelCache, and per-provider TTL configuration.
"""

import pytest
import time
from datetime import datetime
from unittest.mock import patch

from ..cache import LRUCache, MultiLevelCache, CacheEntry
from ..config import (
    CacheConfig,
    ProviderCacheTTL,
    get_provider_cache_ttl,
    PROVIDER_CONFIGS,
)
from ..interfaces import DataType


class TestCacheEntry:
    """Tests for CacheEntry dataclass."""

    def test_is_expired_false(self):
        """Test entry is not expired when within TTL."""
        entry = CacheEntry(
            key="test",
            value="data",
            created_at=datetime.now(),
            ttl_seconds=3600,
            data_type=DataType.QUOTE,
        )

        assert entry.is_expired is False

    def test_is_expired_true(self):
        """Test entry is expired when past TTL."""
        from datetime import timedelta

        entry = CacheEntry(
            key="test",
            value="data",
            created_at=datetime.now() - timedelta(seconds=3601),
            ttl_seconds=3600,
            data_type=DataType.QUOTE,
        )

        assert entry.is_expired is True

    def test_age_seconds(self):
        """Test age calculation."""
        from datetime import timedelta

        entry = CacheEntry(
            key="test",
            value="data",
            created_at=datetime.now() - timedelta(seconds=100),
            ttl_seconds=3600,
            data_type=DataType.QUOTE,
        )

        assert 99 <= entry.age_seconds <= 101


class TestLRUCache:
    """Tests for LRUCache."""

    def test_set_and_get(self):
        """Test basic set and get operations."""
        cache = LRUCache(max_size=100)

        cache.set("key1", "value1", ttl_seconds=3600, data_type=DataType.QUOTE)
        entry = cache.get("key1")

        assert entry is not None
        assert entry.value == "value1"

    def test_get_nonexistent(self):
        """Test getting nonexistent key returns None."""
        cache = LRUCache(max_size=100)

        entry = cache.get("nonexistent")

        assert entry is None

    def test_get_expired(self):
        """Test getting expired entry returns None."""
        cache = LRUCache(max_size=100)
        cache.set("key1", "value1", ttl_seconds=0, data_type=DataType.QUOTE)

        time.sleep(0.1)
        entry = cache.get("key1")

        assert entry is None

    def test_lru_eviction(self):
        """Test LRU eviction when at capacity."""
        cache = LRUCache(max_size=3)

        cache.set("key1", "value1", ttl_seconds=3600, data_type=DataType.QUOTE)
        cache.set("key2", "value2", ttl_seconds=3600, data_type=DataType.QUOTE)
        cache.set("key3", "value3", ttl_seconds=3600, data_type=DataType.QUOTE)

        # Access key1 to make it recently used
        cache.get("key1")

        # Add key4, should evict key2 (least recently used)
        cache.set("key4", "value4", ttl_seconds=3600, data_type=DataType.QUOTE)

        assert cache.get("key1") is not None  # Recently used, should exist
        assert cache.get("key2") is None  # LRU, should be evicted
        assert cache.get("key3") is not None
        assert cache.get("key4") is not None

    def test_stats(self):
        """Test cache statistics."""
        cache = LRUCache(max_size=100)

        cache.set("key1", "value1", ttl_seconds=3600, data_type=DataType.QUOTE)
        cache.get("key1")  # Hit
        cache.get("key2")  # Miss

        stats = cache.stats

        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["size"] == 1
        assert stats["max_size"] == 100

    def test_delete(self):
        """Test deleting an entry."""
        cache = LRUCache(max_size=100)

        cache.set("key1", "value1", ttl_seconds=3600, data_type=DataType.QUOTE)
        result = cache.delete("key1")

        assert result is True
        assert cache.get("key1") is None

    def test_delete_nonexistent(self):
        """Test deleting nonexistent key."""
        cache = LRUCache(max_size=100)

        result = cache.delete("nonexistent")

        assert result is False

    def test_clear(self):
        """Test clearing all entries."""
        cache = LRUCache(max_size=100)

        cache.set("key1", "value1", ttl_seconds=3600, data_type=DataType.QUOTE)
        cache.set("key2", "value2", ttl_seconds=3600, data_type=DataType.QUOTE)
        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_cleanup_expired(self):
        """Test removing expired entries."""
        cache = LRUCache(max_size=100)

        cache.set("key1", "value1", ttl_seconds=0, data_type=DataType.QUOTE)
        cache.set("key2", "value2", ttl_seconds=3600, data_type=DataType.QUOTE)

        time.sleep(0.1)
        removed = cache.cleanup_expired()

        assert removed == 1
        assert cache.get("key1") is None
        assert cache.get("key2") is not None


class TestMultiLevelCache:
    """Tests for MultiLevelCache."""

    def test_get_and_set(self):
        """Test basic get and set operations."""
        cache = MultiLevelCache(CacheConfig())

        cache.set("AAPL", "quote_data", DataType.QUOTE, source="yfinance")
        result = cache.get("AAPL", DataType.QUOTE)

        assert result == "quote_data"

    def test_get_with_different_data_types(self):
        """Test that different data types are stored separately."""
        cache = MultiLevelCache(CacheConfig())

        cache.set("AAPL", "quote_data", DataType.QUOTE, source="yfinance")
        cache.set("AAPL", "history_data", DataType.HISTORY, source="yfinance")

        assert cache.get("AAPL", DataType.QUOTE) == "quote_data"
        assert cache.get("AAPL", DataType.HISTORY) == "history_data"

    def test_per_provider_ttl(self):
        """Test that per-provider TTL is applied."""
        cache = MultiLevelCache(CacheConfig())

        # Tiger has shorter TTL for options (90s vs 120s for yfinance)
        tiger_ttl = get_provider_cache_ttl("tiger", DataType.OPTIONS_CHAIN)
        yfinance_ttl = get_provider_cache_ttl("yfinance", DataType.OPTIONS_CHAIN)

        assert tiger_ttl == 90
        assert yfinance_ttl == 120

    def test_ttl_override(self):
        """Test that TTL override works."""
        cache = MultiLevelCache(CacheConfig())

        cache.set("AAPL", "data", DataType.QUOTE, source="yfinance", ttl_override=10)

        # The data should still be accessible
        assert cache.get("AAPL", DataType.QUOTE) == "data"

    def test_disabled_cache(self):
        """Test that disabled cache returns None."""
        config = CacheConfig(memory_enabled=False)
        cache = MultiLevelCache(config)

        cache.set("AAPL", "data", DataType.QUOTE)
        result = cache.get("AAPL", DataType.QUOTE)

        assert result is None

    def test_stats(self):
        """Test cache statistics."""
        cache = MultiLevelCache(CacheConfig())

        cache.set("AAPL", "data", DataType.QUOTE, source="yfinance")
        cache.get("AAPL", DataType.QUOTE)  # Hit
        cache.get("MSFT", DataType.QUOTE)  # Miss

        stats = cache.stats

        assert stats["l1_hits"] == 1
        assert stats["l1_misses"] == 1
        assert 0 <= stats["l1_hit_rate"] <= 1

    def test_clear_for_symbol(self):
        """Test clearing cache for a specific symbol."""
        cache = MultiLevelCache(CacheConfig())

        cache.set("AAPL", "quote", DataType.QUOTE, source="yfinance")
        cache.set("AAPL", "history", DataType.HISTORY, source="yfinance")
        cache.set("MSFT", "quote", DataType.QUOTE, source="yfinance")

        cache.clear_for_symbol("AAPL")

        assert cache.get("AAPL", DataType.QUOTE) is None
        assert cache.get("AAPL", DataType.HISTORY) is None
        assert cache.get("MSFT", DataType.QUOTE) == "quote"


class TestProviderCacheTTL:
    """Tests for ProviderCacheTTL configuration."""

    def test_default_ttl_values(self):
        """Test default TTL values."""
        ttl = ProviderCacheTTL()

        assert ttl.quote == 60
        assert ttl.history == 300
        assert ttl.fundamentals == 3600
        assert ttl.info == 86400
        assert ttl.options_chain == 120
        assert ttl.options_expirations == 300
        assert ttl.earnings == 3600
        assert ttl.macro == 60

    def test_custom_ttl_values(self):
        """Test custom TTL values."""
        ttl = ProviderCacheTTL(
            quote=30,
            history=600,
        )

        assert ttl.quote == 30
        assert ttl.history == 600

    def test_get_ttl_for_data_type(self):
        """Test getting TTL for specific data type."""
        ttl = ProviderCacheTTL(quote=30)

        assert ttl.get_ttl(DataType.QUOTE) == 30
        assert ttl.get_ttl(DataType.HISTORY) == 300  # Default


class TestGetProviderCacheTTL:
    """Tests for get_provider_cache_ttl function."""

    def test_yfinance_ttl(self):
        """Test yfinance TTL values."""
        assert get_provider_cache_ttl("yfinance", DataType.QUOTE) == 60
        assert get_provider_cache_ttl("yfinance", DataType.OPTIONS_CHAIN) == 120

    def test_tiger_ttl(self):
        """Test Tiger TTL values (shorter for options)."""
        assert get_provider_cache_ttl("tiger", DataType.QUOTE) == 60
        assert get_provider_cache_ttl("tiger", DataType.OPTIONS_CHAIN) == 90

    def test_defeatbeta_ttl(self):
        """Test DefeatBeta TTL values (longer for local data)."""
        assert get_provider_cache_ttl("defeatbeta", DataType.QUOTE) == 120
        assert get_provider_cache_ttl("defeatbeta", DataType.HISTORY) == 600

    def test_alpha_vantage_ttl(self):
        """Test Alpha Vantage TTL values (longest due to rate limits)."""
        assert get_provider_cache_ttl("alpha_vantage", DataType.QUOTE) == 300
        assert get_provider_cache_ttl("alpha_vantage", DataType.HISTORY) == 900

    def test_unknown_provider_fallback(self):
        """Test fallback to default for unknown provider."""
        # Should fall back to CacheConfig defaults
        ttl = get_provider_cache_ttl("unknown_provider", DataType.QUOTE)
        assert ttl == 60  # Default from CacheConfig


class TestCacheConfig:
    """Tests for CacheConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = CacheConfig()

        assert config.memory_enabled is True
        assert config.memory_ttl_quote == 60
        assert config.memory_max_size == 1000
        assert config.dedup_window_ms == 500

    def test_get_default_ttl(self):
        """Test getting default TTL for data types."""
        config = CacheConfig()

        assert config.get_default_ttl(DataType.QUOTE) == 60
        assert config.get_default_ttl(DataType.INFO) == 86400


class TestCacheIntegration:
    """Integration tests for cache with service."""

    def test_thread_safety(self):
        """Test thread-safe cache operations."""
        import threading

        cache = LRUCache(max_size=1000)

        def write_operations():
            for i in range(100):
                cache.set(f"key{i}", f"value{i}", ttl_seconds=3600, data_type=DataType.QUOTE)

        def read_operations():
            for i in range(100):
                cache.get(f"key{i}")

        threads = []
        for _ in range(5):
            threads.append(threading.Thread(target=write_operations))
            threads.append(threading.Thread(target=read_operations))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should not raise any exceptions

    def test_high_concurrency(self):
        """Test cache under high concurrency."""
        import threading
        from concurrent.futures import ThreadPoolExecutor

        cache = MultiLevelCache(CacheConfig())

        def cache_operation(symbol):
            cache.set(symbol, f"data_{symbol}", DataType.QUOTE, source="yfinance")
            return cache.get(symbol, DataType.QUOTE)

        symbols = [f"STOCK{i}" for i in range(100)]

        with ThreadPoolExecutor(max_workers=20) as executor:
            results = list(executor.map(cache_operation, symbols))

        # All operations should succeed
        assert len(results) == 100
        assert all(r is not None for r in results)

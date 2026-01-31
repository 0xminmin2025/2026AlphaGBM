"""
Multi-Level Cache for Market Data

Provides a hierarchical caching system:
- L1: In-memory cache (fast, per-process, short TTL)
- L2: Database cache (persistent, longer TTL for daily analysis)

Cache is designed to minimize API calls while ensuring data freshness
appropriate for each data type.
"""

import threading
import logging
from typing import Any, Optional, Dict
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import OrderedDict

from .interfaces import DataType
from .config import CacheConfig

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """A single cache entry with metadata."""
    key: str
    value: Any
    created_at: datetime
    ttl_seconds: int
    data_type: DataType
    source: str = ""

    @property
    def is_expired(self) -> bool:
        """Check if this entry has expired."""
        age = (datetime.now() - self.created_at).total_seconds()
        return age > self.ttl_seconds

    @property
    def age_seconds(self) -> float:
        """Get age of this entry in seconds."""
        return (datetime.now() - self.created_at).total_seconds()


class LRUCache:
    """
    Thread-safe LRU cache with TTL support.

    Implements Least Recently Used eviction when max_size is reached.
    """

    def __init__(self, max_size: int = 1000):
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max_size = max_size
        self._lock = threading.Lock()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
        }

    @property
    def stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            **self._stats,
            "size": len(self._cache),
            "max_size": self._max_size,
        }

    def get(self, key: str) -> Optional[CacheEntry]:
        """
        Get entry from cache.

        Returns None if not found or expired.
        Moves accessed entry to end (most recently used).
        """
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._stats["misses"] += 1
                return None

            if entry.is_expired:
                # Remove expired entry
                del self._cache[key]
                self._stats["misses"] += 1
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self._stats["hits"] += 1
            return entry

    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int,
        data_type: DataType,
        source: str = ""
    ) -> None:
        """
        Set entry in cache.

        Evicts least recently used entry if at max capacity.
        """
        with self._lock:
            # Remove existing entry if present
            if key in self._cache:
                del self._cache[key]

            # Evict if at capacity
            while len(self._cache) >= self._max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                self._stats["evictions"] += 1

            # Add new entry
            self._cache[key] = CacheEntry(
                key=key,
                value=value,
                created_at=datetime.now(),
                ttl_seconds=ttl_seconds,
                data_type=data_type,
                source=source,
            )

    def delete(self, key: str) -> bool:
        """Delete entry from cache. Returns True if entry existed."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """Clear all entries from cache."""
        with self._lock:
            self._cache.clear()

    def cleanup_expired(self) -> int:
        """Remove all expired entries. Returns count of removed entries."""
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired
            ]
            for key in expired_keys:
                del self._cache[key]
            return len(expired_keys)


class MultiLevelCache:
    """
    Multi-level cache for market data.

    Provides a unified interface for caching with automatic TTL based on data type.
    """

    def __init__(self, config: Optional[CacheConfig] = None):
        self._config = config or CacheConfig()
        self._memory_cache = LRUCache(max_size=self._config.memory_max_size)
        self._stats = {
            "l1_hits": 0,
            "l1_misses": 0,
        }

    def _get_ttl(self, data_type: DataType) -> int:
        """Get TTL in seconds for a data type."""
        ttl_map = {
            DataType.QUOTE: self._config.memory_ttl_quote,
            DataType.HISTORY: self._config.memory_ttl_history,
            DataType.FUNDAMENTALS: self._config.memory_ttl_fundamentals,
            DataType.INFO: self._config.memory_ttl_info,
            DataType.OPTIONS_CHAIN: self._config.memory_ttl_options,
            DataType.OPTIONS_EXPIRATIONS: self._config.memory_ttl_options,
            DataType.EARNINGS: self._config.memory_ttl_fundamentals,
            DataType.MACRO: self._config.memory_ttl_quote,
        }
        return ttl_map.get(data_type, 300)  # Default 5 minutes

    def _make_key(self, cache_key: str, data_type: DataType) -> str:
        """Create internal cache key."""
        return f"{data_type.value}:{cache_key}"

    def get(self, cache_key: str, data_type: DataType) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            cache_key: Cache key (usually "symbol" or "symbol:params")
            data_type: Type of data being cached

        Returns:
            Cached value if found and not expired, None otherwise
        """
        if not self._config.memory_enabled:
            return None

        key = self._make_key(cache_key, data_type)
        entry = self._memory_cache.get(key)

        if entry is not None:
            self._stats["l1_hits"] += 1
            logger.debug(f"[Cache] HIT {data_type.value}:{cache_key} (age: {entry.age_seconds:.1f}s)")
            return entry.value

        self._stats["l1_misses"] += 1
        return None

    def set(
        self,
        cache_key: str,
        value: Any,
        data_type: DataType,
        source: str = "",
        ttl_override: Optional[int] = None
    ) -> None:
        """
        Set value in cache.

        Args:
            cache_key: Cache key (usually "symbol" or "symbol:params")
            value: Value to cache
            data_type: Type of data being cached
            source: Which provider returned this data
            ttl_override: Override default TTL for this data type
        """
        if not self._config.memory_enabled:
            return

        key = self._make_key(cache_key, data_type)
        ttl = ttl_override if ttl_override is not None else self._get_ttl(data_type)

        self._memory_cache.set(
            key=key,
            value=value,
            ttl_seconds=ttl,
            data_type=data_type,
            source=source,
        )
        logger.debug(f"[Cache] SET {data_type.value}:{cache_key} (ttl: {ttl}s, source: {source})")

    def delete(self, cache_key: str, data_type: DataType) -> bool:
        """Delete entry from cache."""
        key = self._make_key(cache_key, data_type)
        return self._memory_cache.delete(key)

    def clear(self) -> None:
        """Clear all cache entries."""
        self._memory_cache.clear()
        logger.info("[Cache] Cleared all entries")

    def clear_for_symbol(self, symbol: str) -> int:
        """Clear all cache entries for a specific symbol."""
        # This is a simple implementation - for better performance,
        # we'd need to track keys by symbol
        count = 0
        for data_type in DataType:
            if self.delete(symbol, data_type):
                count += 1
        return count

    def cleanup_expired(self) -> int:
        """Remove expired entries from cache."""
        return self._memory_cache.cleanup_expired()

    @property
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        memory_stats = self._memory_cache.stats
        return {
            "l1_hits": self._stats["l1_hits"],
            "l1_misses": self._stats["l1_misses"],
            "l1_hit_rate": (
                self._stats["l1_hits"] / (self._stats["l1_hits"] + self._stats["l1_misses"])
                if (self._stats["l1_hits"] + self._stats["l1_misses"]) > 0
                else 0
            ),
            "l1_size": memory_stats["size"],
            "l1_max_size": memory_stats["max_size"],
            "l1_evictions": memory_stats["evictions"],
        }

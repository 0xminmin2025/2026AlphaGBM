"""
Request Deduplicator

Prevents duplicate API calls for the same data within a short time window.
When multiple callers request the same data simultaneously:
1. First caller makes the actual API call
2. Subsequent callers wait for the first call to complete
3. All callers receive the same result

This prevents wasting API rate limits on duplicate requests.
"""

import threading
import hashlib
import logging
from typing import Any, Callable, Optional, Dict
from dataclasses import dataclass
from datetime import datetime
import time

logger = logging.getLogger(__name__)


@dataclass
class InFlightRequest:
    """Tracks an in-flight request."""
    key: str
    started_at: datetime
    event: threading.Event
    result: Any = None
    error: Optional[Exception] = None
    completed: bool = False


class RequestDeduplicator:
    """
    Prevents duplicate API calls for the same data.

    Thread-safe implementation that ensures only one request is made
    for the same (data_type, symbol, params) combination within
    the deduplication window.

    Usage:
        dedup = RequestDeduplicator(window_ms=500)

        def fetch_quote(symbol):
            return dedup.execute(
                data_type="quote",
                symbol=symbol,
                fetch_fn=lambda: api.get_quote(symbol)
            )

        # These two calls happen within 500ms - only one API call made
        quote1 = fetch_quote("AAPL")  # Makes API call
        quote2 = fetch_quote("AAPL")  # Waits for first, returns same result
    """

    def __init__(self, window_ms: int = 500):
        """
        Initialize deduplicator.

        Args:
            window_ms: Time window in milliseconds for deduplication
        """
        self._in_flight: Dict[str, InFlightRequest] = {}
        self._lock = threading.Lock()
        self._window_ms = window_ms
        self._stats = {
            "requests": 0,
            "deduplicated": 0,
            "api_calls": 0,
        }

    @property
    def stats(self) -> Dict[str, int]:
        """Get deduplication statistics."""
        return self._stats.copy()

    def _make_key(self, data_type: str, symbol: str, **kwargs) -> str:
        """
        Create a unique key for this request.

        The key is a hash of (data_type, symbol, sorted_kwargs).
        """
        # Sort kwargs for consistent key generation
        sorted_kwargs = sorted((k, str(v)) for k, v in kwargs.items() if v is not None)
        key_str = f"{data_type}:{symbol.upper()}:{sorted_kwargs}"
        return hashlib.md5(key_str.encode()).hexdigest()[:16]

    def execute(
        self,
        data_type: str,
        symbol: str,
        fetch_fn: Callable[[], Any],
        timeout: float = 30.0,
        **kwargs
    ) -> Any:
        """
        Execute a data fetch with deduplication.

        Args:
            data_type: Type of data being fetched (quote, history, etc.)
            symbol: Stock symbol
            fetch_fn: Function to call if this is the first request
            timeout: Max time to wait for in-flight request (seconds)
            **kwargs: Additional parameters that affect the cache key

        Returns:
            The fetched data (either from fetch_fn or from in-flight request)

        Raises:
            TimeoutError: If waiting for in-flight request times out
            Exception: Re-raises any exception from fetch_fn
        """
        self._stats["requests"] += 1
        key = self._make_key(data_type, symbol, **kwargs)

        with self._lock:
            # Check if there's already an in-flight request for this data
            existing = self._in_flight.get(key)
            if existing and not existing.completed:
                # Wait for the in-flight request
                in_flight = existing
                logger.debug(f"[Dedup] Waiting for in-flight request: {data_type}:{symbol}")
            else:
                # We're the first - create the in-flight entry
                in_flight = None
                self._in_flight[key] = InFlightRequest(
                    key=key,
                    started_at=datetime.now(),
                    event=threading.Event()
                )
                logger.debug(f"[Dedup] New request: {data_type}:{symbol}")

        if in_flight is not None:
            # Wait for the in-flight request to complete
            self._stats["deduplicated"] += 1
            if in_flight.event.wait(timeout=timeout):
                if in_flight.error:
                    raise in_flight.error
                return in_flight.result
            else:
                raise TimeoutError(f"Timed out waiting for {data_type}:{symbol}")

        # We're the first caller - do the actual fetch
        self._stats["api_calls"] += 1
        request = self._in_flight[key]

        try:
            result = fetch_fn()
            request.result = result
            request.completed = True
            request.event.set()
            return result
        except Exception as e:
            request.error = e
            request.completed = True
            request.event.set()
            raise
        finally:
            # Schedule cleanup after window expires
            self._schedule_cleanup(key)

    def _schedule_cleanup(self, key: str) -> None:
        """Schedule cleanup of completed request after window expires."""
        def cleanup():
            time.sleep(self._window_ms / 1000.0)
            with self._lock:
                if key in self._in_flight:
                    request = self._in_flight[key]
                    if request.completed:
                        del self._in_flight[key]

        thread = threading.Thread(target=cleanup, daemon=True)
        thread.start()

    def clear(self) -> None:
        """Clear all in-flight requests (for testing)."""
        with self._lock:
            self._in_flight.clear()

    def reset_stats(self) -> None:
        """Reset statistics counters."""
        self._stats = {
            "requests": 0,
            "deduplicated": 0,
            "api_calls": 0,
        }

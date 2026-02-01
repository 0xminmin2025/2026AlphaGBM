"""
Base Adapter with Common Utilities

Provides shared functionality for all data provider adapters:
- Rate limit detection and tracking
- Error classification
- Health tracking
- Concurrency control (semaphore-based)
- Circuit breaker pattern
- Common data transformations
"""

import logging
import json
import threading
from datetime import datetime, timedelta
from typing import Optional, Callable, TypeVar
from abc import ABC
from functools import wraps

from ..interfaces import ProviderStatus

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ConcurrencyLimiter:
    """
    Semaphore-based concurrency limiter for controlling max concurrent requests.

    Prevents a single provider from being overwhelmed with too many
    simultaneous requests, which can cause rate limiting or degraded performance.
    """

    def __init__(self, max_concurrent: int = 10):
        """
        Initialize concurrency limiter.

        Args:
            max_concurrent: Maximum number of concurrent requests allowed
        """
        self._semaphore = threading.Semaphore(max_concurrent)
        self._max_concurrent = max_concurrent
        self._current_count = 0
        self._lock = threading.Lock()

    def acquire(self, timeout: float = 30.0) -> bool:
        """
        Acquire a slot for a request.

        Args:
            timeout: Maximum time to wait for a slot (seconds)

        Returns:
            True if slot acquired, False if timeout
        """
        acquired = self._semaphore.acquire(timeout=timeout)
        if acquired:
            with self._lock:
                self._current_count += 1
        return acquired

    def release(self) -> None:
        """Release a slot after request completes."""
        with self._lock:
            self._current_count = max(0, self._current_count - 1)
        self._semaphore.release()

    @property
    def current_count(self) -> int:
        """Get current number of active requests."""
        with self._lock:
            return self._current_count

    @property
    def available_slots(self) -> int:
        """Get number of available slots."""
        return self._max_concurrent - self.current_count


class CircuitBreaker:
    """
    Circuit breaker pattern for automatic provider failure handling.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests are rejected
    - HALF_OPEN: Testing if provider has recovered
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 3,
        timeout_seconds: int = 60
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            success_threshold: Number of successes in half-open to close
            timeout_seconds: Time to wait before testing recovery
        """
        self._failure_threshold = failure_threshold
        self._success_threshold = success_threshold
        self._timeout_seconds = timeout_seconds

        self._state = self.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._lock = threading.Lock()

    @property
    def state(self) -> str:
        """Get current circuit state."""
        with self._lock:
            # Check if we should transition from OPEN to HALF_OPEN
            if self._state == self.OPEN and self._last_failure_time:
                elapsed = (datetime.now() - self._last_failure_time).total_seconds()
                if elapsed >= self._timeout_seconds:
                    self._state = self.HALF_OPEN
                    self._success_count = 0
                    logger.info("Circuit breaker transitioning to HALF_OPEN")
            return self._state

    def is_open(self) -> bool:
        """Check if circuit is open (requests should be rejected)."""
        return self.state == self.OPEN

    def record_success(self) -> None:
        """Record a successful request."""
        with self._lock:
            self._failure_count = 0

            if self._state == self.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self._success_threshold:
                    self._state = self.CLOSED
                    logger.info("Circuit breaker CLOSED - provider recovered")

    def record_failure(self) -> None:
        """Record a failed request."""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = datetime.now()

            if self._state == self.HALF_OPEN:
                # Single failure in half-open returns to open
                self._state = self.OPEN
                logger.warning("Circuit breaker OPEN - failure during recovery test")
            elif self._state == self.CLOSED:
                if self._failure_count >= self._failure_threshold:
                    self._state = self.OPEN
                    logger.warning(f"Circuit breaker OPEN - {self._failure_count} consecutive failures")

    def reset(self) -> None:
        """Reset circuit breaker to closed state."""
        with self._lock:
            self._state = self.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._last_failure_time = None


class RateLimitTracker:
    """Tracks rate limit status for a provider."""

    def __init__(self, cooldown_seconds: int = 60):
        self._is_limited = False
        self._limited_at: Optional[datetime] = None
        self._cooldown_seconds = cooldown_seconds
        self._consecutive_failures = 0
        self._lock = threading.Lock()

    @property
    def is_rate_limited(self) -> bool:
        """Check if currently rate limited."""
        with self._lock:
            if not self._is_limited:
                return False

            # Check if cooldown has passed
            if self._limited_at:
                elapsed = (datetime.now() - self._limited_at).total_seconds()
                if elapsed >= self._cooldown_seconds:
                    self._is_limited = False
                    self._consecutive_failures = 0
                    logger.info(f"Rate limit cooldown expired, resuming normal operation")
                    return False

            return True

    def mark_rate_limited(self) -> None:
        """Mark as rate limited."""
        with self._lock:
            self._is_limited = True
            self._limited_at = datetime.now()
            logger.warning(f"Rate limit triggered, cooling down for {self._cooldown_seconds}s")

    def mark_failure(self) -> None:
        """Record a failure (may trigger rate limit after threshold)."""
        with self._lock:
            self._consecutive_failures += 1

    def mark_success(self) -> None:
        """Record a success (resets failure counter)."""
        with self._lock:
            self._consecutive_failures = 0

    def reset(self) -> None:
        """Reset rate limit status."""
        with self._lock:
            self._is_limited = False
            self._limited_at = None
            self._consecutive_failures = 0

    @property
    def consecutive_failures(self) -> int:
        return self._consecutive_failures


def is_rate_limit_error(e: Exception) -> bool:
    """
    Check if an exception indicates a rate limit error.

    This covers various ways different APIs signal rate limiting:
    - HTTP 429 Too Many Requests
    - JSONDecodeError (empty response due to rate limit)
    - Explicit rate limit exceptions
    """
    error_msg = str(e).lower()
    error_type = type(e).__name__

    # Direct rate limit indicators
    rate_limit_indicators = [
        "too many requests",
        "rate limit",
        "429",
        "quota exceeded",
        "throttl",
    ]

    if any(indicator in error_msg for indicator in rate_limit_indicators):
        return True

    # JSONDecodeError often happens when API returns empty response due to rate limit
    if error_type == "JSONDecodeError" or isinstance(e, json.JSONDecodeError):
        if "expecting value" in error_msg:
            return True

    # Network errors that may indicate rate limiting
    if "max retries exceeded" in error_msg:
        return True

    return False


def is_network_error(e: Exception) -> bool:
    """Check if an exception indicates a network connectivity issue."""
    error_msg = str(e).lower()

    network_indicators = [
        "connection refused",
        "connection reset",
        "connection timeout",
        "network is unreachable",
        "name resolution",
        "ssl",
        "eof occurred",
        "remote end closed",
    ]

    return any(indicator in error_msg for indicator in network_indicators)


def is_invalid_symbol_error(e: Exception) -> bool:
    """Check if an exception indicates an invalid/unknown symbol."""
    error_msg = str(e).lower()

    invalid_indicators = [
        "no data found",
        "symbol not found",
        "invalid symbol",
        "unknown symbol",
        "delisted",
        "no price data",
    ]

    return any(indicator in error_msg for indicator in invalid_indicators)


def safe_float(value, default: Optional[float] = None) -> Optional[float]:
    """Safely convert a value to float."""
    if value is None:
        return default
    try:
        import pandas as pd
        import numpy as np
        if pd.isna(value) or (isinstance(value, float) and np.isnan(value)):
            return default
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value, default: Optional[int] = None) -> Optional[int]:
    """Safely convert a value to int."""
    if value is None:
        return default
    try:
        import pandas as pd
        import numpy as np
        if pd.isna(value) or (isinstance(value, float) and np.isnan(value)):
            return default
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_str(value, default: Optional[str] = None) -> Optional[str]:
    """Safely convert a value to string."""
    if value is None:
        return default
    try:
        return str(value)
    except (ValueError, TypeError):
        return default


class BaseAdapter(ABC):
    """
    Base class for data provider adapters.

    Provides common functionality:
    - Rate limit tracking
    - Error classification
    - Health status management
    - Concurrency control (semaphore-based)
    - Circuit breaker pattern

    Thread-safe for concurrent access.
    """

    def __init__(
        self,
        cooldown_seconds: int = 60,
        max_failures: int = 3,
        max_concurrent: int = 10,
        circuit_breaker_threshold: int = 5,
    ):
        """
        Initialize base adapter with protection mechanisms.

        Args:
            cooldown_seconds: Time to wait after rate limiting
            max_failures: Max consecutive failures before rate limiting
            max_concurrent: Max concurrent requests to this provider
            circuit_breaker_threshold: Failures before circuit opens
        """
        self._rate_limiter = RateLimitTracker(cooldown_seconds)
        self._max_failures = max_failures
        self._last_error: Optional[str] = None
        self._last_success: Optional[datetime] = None

        # Concurrency control
        self._concurrency_limiter = ConcurrencyLimiter(max_concurrent)

        # Circuit breaker
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=circuit_breaker_threshold,
            timeout_seconds=cooldown_seconds
        )

    def is_rate_limited(self) -> bool:
        """Check if provider is currently rate-limited."""
        return self._rate_limiter.is_rate_limited

    def is_circuit_open(self) -> bool:
        """Check if circuit breaker is open (requests should be skipped)."""
        return self._circuit_breaker.is_open()

    @property
    def active_requests(self) -> int:
        """Get number of currently active requests."""
        return self._concurrency_limiter.current_count

    def reset_rate_limit(self) -> None:
        """Reset rate limit status."""
        self._rate_limiter.reset()
        self._circuit_breaker.reset()

    def with_concurrency_limit(
        self,
        fetch_fn: Callable[[], T],
        timeout: float = 30.0
    ) -> Optional[T]:
        """
        Execute a function with concurrency limiting.

        Args:
            fetch_fn: Function to execute
            timeout: Max time to wait for a slot

        Returns:
            Result of fetch_fn, or None if timeout/circuit open
        """
        # Check circuit breaker first
        if self._circuit_breaker.is_open():
            logger.debug(f"[{self.name}] Circuit breaker open, skipping request")
            return None

        # Acquire concurrency slot
        if not self._concurrency_limiter.acquire(timeout=timeout):
            logger.warning(f"[{self.name}] Concurrency limit reached, request timed out")
            return None

        try:
            result = fetch_fn()
            self._circuit_breaker.record_success()
            return result
        except Exception as e:
            self._circuit_breaker.record_failure()
            raise
        finally:
            self._concurrency_limiter.release()

    def _handle_error(self, e: Exception, symbol: str) -> None:
        """Handle an error from the provider."""
        self._last_error = str(e)

        if is_rate_limit_error(e):
            self._rate_limiter.mark_rate_limited()
            self._circuit_breaker.record_failure()
            logger.warning(f"[{self.name}] Rate limited: {symbol}")
        elif is_network_error(e):
            self._rate_limiter.mark_failure()
            self._circuit_breaker.record_failure()
            logger.warning(f"[{self.name}] Network error for {symbol}: {e}")
        elif is_invalid_symbol_error(e):
            # Don't mark as failure for invalid symbols
            logger.debug(f"[{self.name}] Invalid symbol: {symbol}")
        else:
            self._rate_limiter.mark_failure()
            self._circuit_breaker.record_failure()
            logger.warning(f"[{self.name}] Error for {symbol}: {e}")

        # Check if too many failures
        if self._rate_limiter.consecutive_failures >= self._max_failures:
            self._rate_limiter.mark_rate_limited()
            logger.warning(f"[{self.name}] Too many failures, entering cooldown")

    def _handle_success(self) -> None:
        """Handle a successful request."""
        self._rate_limiter.mark_success()
        self._circuit_breaker.record_success()
        self._last_success = datetime.now()

    def health_check(self) -> ProviderStatus:
        """Check provider health status."""
        # Circuit breaker open is worse than rate limited
        if self._circuit_breaker.is_open():
            return ProviderStatus.UNAVAILABLE

        if self._rate_limiter.is_rate_limited:
            return ProviderStatus.RATE_LIMITED

        if self._rate_limiter.consecutive_failures > 0:
            return ProviderStatus.DEGRADED

        return ProviderStatus.HEALTHY

    def get_status_info(self) -> dict:
        """Get detailed status information for monitoring."""
        return {
            "health": self.health_check().value,
            "rate_limited": self.is_rate_limited(),
            "circuit_state": self._circuit_breaker.state,
            "active_requests": self.active_requests,
            "consecutive_failures": self._rate_limiter.consecutive_failures,
            "last_success": self._last_success.isoformat() if self._last_success else None,
            "last_error": self._last_error,
        }

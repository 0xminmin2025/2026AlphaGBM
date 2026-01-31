"""
Base Adapter with Common Utilities

Provides shared functionality for all data provider adapters:
- Rate limit detection
- Error classification
- Health tracking
- Common data transformations
"""

import logging
import json
import threading
from datetime import datetime, timedelta
from typing import Optional
from abc import ABC

from ..interfaces import ProviderStatus

logger = logging.getLogger(__name__)


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
    """

    def __init__(self, cooldown_seconds: int = 60, max_failures: int = 3):
        self._rate_limiter = RateLimitTracker(cooldown_seconds)
        self._max_failures = max_failures
        self._last_error: Optional[str] = None
        self._last_success: Optional[datetime] = None

    def is_rate_limited(self) -> bool:
        """Check if provider is currently rate-limited."""
        return self._rate_limiter.is_rate_limited

    def reset_rate_limit(self) -> None:
        """Reset rate limit status."""
        self._rate_limiter.reset()

    def _handle_error(self, e: Exception, symbol: str) -> None:
        """Handle an error from the provider."""
        self._last_error = str(e)

        if is_rate_limit_error(e):
            self._rate_limiter.mark_rate_limited()
            logger.warning(f"[{self.name}] Rate limited: {symbol}")
        elif is_network_error(e):
            self._rate_limiter.mark_failure()
            logger.warning(f"[{self.name}] Network error for {symbol}: {e}")
        elif is_invalid_symbol_error(e):
            # Don't mark as failure for invalid symbols
            logger.debug(f"[{self.name}] Invalid symbol: {symbol}")
        else:
            self._rate_limiter.mark_failure()
            logger.warning(f"[{self.name}] Error for {symbol}: {e}")

        # Check if too many failures
        if self._rate_limiter.consecutive_failures >= self._max_failures:
            self._rate_limiter.mark_rate_limited()
            logger.warning(f"[{self.name}] Too many failures, entering cooldown")

    def _handle_success(self) -> None:
        """Handle a successful request."""
        self._rate_limiter.mark_success()
        self._last_success = datetime.now()

    def health_check(self) -> ProviderStatus:
        """Check provider health status."""
        if self._rate_limiter.is_rate_limited:
            return ProviderStatus.RATE_LIMITED

        if self._rate_limiter.consecutive_failures > 0:
            return ProviderStatus.DEGRADED

        return ProviderStatus.HEALTHY

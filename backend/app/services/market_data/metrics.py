"""
Market Data Metrics - Statistics and Monitoring

Provides comprehensive statistics tracking for market data operations:
- Per-provider call tracking
- Success/failure rates
- Response time monitoring
- Cache hit rates
- Fallback usage statistics

Storage:
- In-memory ring buffer for recent calls (configurable size)
- Structured JSON logging for ops visibility
- API endpoint exposure via get_stats()
"""

import logging
import json
import time
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from threading import Lock
from typing import Optional, List, Dict, Any, Deque
from enum import Enum

from .interfaces import DataType

logger = logging.getLogger(__name__)


class CallResult(Enum):
    """Result of a data fetch call."""
    SUCCESS = "success"
    CACHE_HIT = "cache_hit"
    FALLBACK = "fallback"       # Succeeded with fallback provider
    FAILURE = "failure"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"


@dataclass
class CallRecord:
    """Record of a single data fetch operation."""
    timestamp: datetime
    data_type: DataType
    symbol: str
    providers_tried: List[str]     # List of providers attempted
    provider_used: Optional[str]   # Provider that returned data (None if failed)
    result: CallResult
    cache_hit: bool
    latency_ms: float
    fallback_used: bool
    error_type: Optional[str] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'data_type': self.data_type.value,
            'symbol': self.symbol,
            'providers_tried': self.providers_tried,
            'provider_used': self.provider_used,
            'result': self.result.value,
            'cache_hit': self.cache_hit,
            'latency_ms': round(self.latency_ms, 2),
            'fallback_used': self.fallback_used,
            'error_type': self.error_type,
            'error_message': self.error_message,
        }


@dataclass
class ProviderMetrics:
    """Aggregated metrics for a single provider."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    timeout_calls: int = 0
    rate_limited_calls: int = 0
    total_latency_ms: float = 0
    min_latency_ms: float = float('inf')
    max_latency_ms: float = 0
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_calls == 0:
            return 0.0
        return (self.successful_calls / self.total_calls) * 100

    @property
    def avg_latency_ms(self) -> float:
        """Calculate average latency in milliseconds."""
        if self.successful_calls == 0:
            return 0.0
        return self.total_latency_ms / self.successful_calls

    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_calls': self.total_calls,
            'successful_calls': self.successful_calls,
            'failed_calls': self.failed_calls,
            'timeout_calls': self.timeout_calls,
            'rate_limited_calls': self.rate_limited_calls,
            'success_rate': round(self.success_rate, 2),
            'avg_latency_ms': round(self.avg_latency_ms, 2),
            'min_latency_ms': round(self.min_latency_ms, 2) if self.min_latency_ms != float('inf') else None,
            'max_latency_ms': round(self.max_latency_ms, 2),
            'last_error': self.last_error,
            'last_error_time': self.last_error_time.isoformat() if self.last_error_time else None,
            'last_success_time': self.last_success_time.isoformat() if self.last_success_time else None,
        }


@dataclass
class DataTypeMetrics:
    """Aggregated metrics for a single data type."""
    total_calls: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    fallback_used: int = 0
    failures: int = 0

    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate as percentage."""
        if self.total_calls == 0:
            return 0.0
        return (self.cache_hits / self.total_calls) * 100

    @property
    def fallback_rate(self) -> float:
        """Calculate fallback rate as percentage."""
        if self.total_calls == 0:
            return 0.0
        return (self.fallback_used / self.total_calls) * 100

    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_calls': self.total_calls,
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'cache_hit_rate': round(self.cache_hit_rate, 2),
            'fallback_used': self.fallback_used,
            'fallback_rate': round(self.fallback_rate, 2),
            'failures': self.failures,
        }


class MetricsCollector:
    """
    Collects and aggregates metrics for market data operations.

    Features:
    - Thread-safe metrics collection
    - In-memory ring buffer for recent call records
    - Per-provider statistics
    - Per-data-type statistics
    - Structured JSON logging for ops visibility

    Usage:
        from app.services.market_data.metrics import metrics_collector

        # Record a successful call
        metrics_collector.record_call(
            data_type=DataType.QUOTE,
            symbol="AAPL",
            providers_tried=["yfinance"],
            provider_used="yfinance",
            latency_ms=150.5,
            cache_hit=False,
            success=True
        )

        # Get statistics
        stats = metrics_collector.get_stats()
    """

    _instance = None
    _lock = Lock()

    # Configuration
    MAX_RECORDS = 10000            # Max records in ring buffer
    LOG_INTERVAL_SECONDS = 300    # Log summary every 5 minutes
    LOG_TO_JSON = True            # Whether to log structured JSON

    def __new__(cls):
        """Singleton pattern."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if getattr(self, '_initialized', False):
            return

        self._records: Deque[CallRecord] = deque(maxlen=self.MAX_RECORDS)
        self._provider_metrics: Dict[str, ProviderMetrics] = {}
        self._data_type_metrics: Dict[DataType, DataTypeMetrics] = {}
        self._last_summary_log: datetime = datetime.now()
        self._start_time: datetime = datetime.now()
        self._lock = Lock()

        # Initialize metrics for all data types
        for dt in DataType:
            self._data_type_metrics[dt] = DataTypeMetrics()

        self._initialized = True
        logger.info("[Metrics] MetricsCollector initialized")

    def record_call(
        self,
        data_type: DataType,
        symbol: str,
        providers_tried: List[str],
        provider_used: Optional[str],
        latency_ms: float,
        cache_hit: bool = False,
        success: bool = True,
        fallback_used: bool = False,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
        timeout: bool = False,
        rate_limited: bool = False,
    ) -> None:
        """
        Record a data fetch operation.

        Args:
            data_type: Type of data requested
            symbol: Stock symbol
            providers_tried: List of providers attempted
            provider_used: Provider that returned data (None if failed)
            latency_ms: Total response time
            cache_hit: Whether result was from cache
            success: Whether operation succeeded
            fallback_used: Whether fallback provider was used
            error_type: Type of error if failed
            error_message: Error message if failed
            timeout: Whether operation timed out
            rate_limited: Whether rate limited
        """
        # DEBUG: Log every call to confirm metrics are being recorded
        logger.info(f"[Metrics] record_call: {data_type.value} {symbol} provider={provider_used} cache_hit={cache_hit} success={success}")

        # Determine result
        if cache_hit:
            result = CallResult.CACHE_HIT
        elif timeout:
            result = CallResult.TIMEOUT
        elif rate_limited:
            result = CallResult.RATE_LIMITED
        elif not success:
            result = CallResult.FAILURE
        elif fallback_used:
            result = CallResult.FALLBACK
        else:
            result = CallResult.SUCCESS

        record = CallRecord(
            timestamp=datetime.now(),
            data_type=data_type,
            symbol=symbol,
            providers_tried=providers_tried,
            provider_used=provider_used,
            result=result,
            cache_hit=cache_hit,
            latency_ms=latency_ms,
            fallback_used=fallback_used,
            error_type=error_type,
            error_message=error_message,
        )

        with self._lock:
            # Add to ring buffer
            self._records.append(record)

            # Update data type metrics
            dt_metrics = self._data_type_metrics[data_type]
            dt_metrics.total_calls += 1
            if cache_hit:
                dt_metrics.cache_hits += 1
            else:
                dt_metrics.cache_misses += 1
            if fallback_used:
                dt_metrics.fallback_used += 1
            if not success:
                dt_metrics.failures += 1

            # Update provider metrics
            for provider in providers_tried:
                if provider not in self._provider_metrics:
                    self._provider_metrics[provider] = ProviderMetrics()

                pm = self._provider_metrics[provider]
                pm.total_calls += 1

                # Only count as success if this was the provider that returned data
                if provider == provider_used and success:
                    pm.successful_calls += 1
                    pm.total_latency_ms += latency_ms
                    pm.min_latency_ms = min(pm.min_latency_ms, latency_ms)
                    pm.max_latency_ms = max(pm.max_latency_ms, latency_ms)
                    pm.last_success_time = datetime.now()
                elif provider != provider_used:
                    # This provider failed before fallback
                    pm.failed_calls += 1
                    if timeout:
                        pm.timeout_calls += 1
                    if rate_limited:
                        pm.rate_limited_calls += 1
                    pm.last_error = error_type or 'unknown'
                    pm.last_error_time = datetime.now()

        # Log structured JSON for ops visibility
        if self.LOG_TO_JSON:
            self._log_record(record)

        # DEBUG: Log current totals after each call
        total_calls = sum(dt.total_calls for dt in self._data_type_metrics.values())
        total_failures = sum(dt.failures for dt in self._data_type_metrics.values())
        logger.info(f"[Metrics] Current totals: calls={total_calls} failures={total_failures} buffer_size={len(self._records)}")

        # Periodic summary logging
        self._maybe_log_summary()

    def _log_record(self, record: CallRecord) -> None:
        """Log a single record as structured JSON."""
        log_data = {
            'event': 'market_data_call',
            **record.to_dict()
        }

        # Use info level for failures, debug for success
        if record.result in (CallResult.FAILURE, CallResult.TIMEOUT):
            logger.info(f"[Metrics] {json.dumps(log_data)}")
        else:
            logger.debug(f"[Metrics] {json.dumps(log_data)}")

    def _maybe_log_summary(self) -> None:
        """Log summary statistics periodically."""
        now = datetime.now()
        if (now - self._last_summary_log).total_seconds() >= self.LOG_INTERVAL_SECONDS:
            self._last_summary_log = now
            summary = self._get_summary_stats()
            logger.info(f"[Metrics] Summary: {json.dumps(summary)}")

    def _get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics for logging."""
        with self._lock:
            total_calls = sum(dt.total_calls for dt in self._data_type_metrics.values())
            total_cache_hits = sum(dt.cache_hits for dt in self._data_type_metrics.values())
            total_failures = sum(dt.failures for dt in self._data_type_metrics.values())

            provider_summary = {}
            for name, pm in self._provider_metrics.items():
                provider_summary[name] = {
                    'success_rate': round(pm.success_rate, 1),
                    'avg_latency_ms': round(pm.avg_latency_ms, 1),
                }

            return {
                'uptime_hours': round((datetime.now() - self._start_time).total_seconds() / 3600, 2),
                'total_calls': total_calls,
                'cache_hit_rate': round(total_cache_hits / total_calls * 100, 1) if total_calls > 0 else 0,
                'failure_rate': round(total_failures / total_calls * 100, 1) if total_calls > 0 else 0,
                'providers': provider_summary,
            }

    def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics.

        Returns:
            Dict containing:
            - uptime: Service uptime
            - totals: Overall statistics
            - by_provider: Per-provider metrics
            - by_data_type: Per-data-type metrics
            - recent_errors: Recent error records
        """
        with self._lock:
            # Calculate totals
            total_calls = sum(dt.total_calls for dt in self._data_type_metrics.values())
            total_cache_hits = sum(dt.cache_hits for dt in self._data_type_metrics.values())
            total_failures = sum(dt.failures for dt in self._data_type_metrics.values())
            total_fallbacks = sum(dt.fallback_used for dt in self._data_type_metrics.values())

            # Get recent errors (last 50)
            recent_errors = [
                r.to_dict() for r in self._records
                if r.result in (CallResult.FAILURE, CallResult.TIMEOUT)
            ][-50:]

            return {
                'uptime': {
                    'start_time': self._start_time.isoformat(),
                    'uptime_seconds': (datetime.now() - self._start_time).total_seconds(),
                },
                'totals': {
                    'total_calls': total_calls,
                    'cache_hits': total_cache_hits,
                    'cache_hit_rate': round(total_cache_hits / total_calls * 100, 2) if total_calls > 0 else 0,
                    'failures': total_failures,
                    'failure_rate': round(total_failures / total_calls * 100, 2) if total_calls > 0 else 0,
                    'fallback_used': total_fallbacks,
                    'fallback_rate': round(total_fallbacks / total_calls * 100, 2) if total_calls > 0 else 0,
                },
                'by_provider': {
                    name: pm.to_dict() for name, pm in self._provider_metrics.items()
                },
                'by_data_type': {
                    dt.value: dtm.to_dict() for dt, dtm in self._data_type_metrics.items()
                },
                'recent_errors': recent_errors,
                'buffer_size': len(self._records),
            }

    def get_provider_health(self, provider_name: str) -> Dict[str, Any]:
        """
        Get health status for a specific provider.

        Args:
            provider_name: Name of the provider

        Returns:
            Health status including success rate, latency, and recent errors
        """
        with self._lock:
            if provider_name not in self._provider_metrics:
                return {'status': 'unknown', 'message': 'No data for this provider'}

            pm = self._provider_metrics[provider_name]

            # Determine health status
            if pm.total_calls == 0:
                status = 'unknown'
            elif pm.success_rate >= 95:
                status = 'healthy'
            elif pm.success_rate >= 80:
                status = 'degraded'
            else:
                status = 'unhealthy'

            # Get recent errors for this provider
            recent_errors = [
                r.to_dict() for r in self._records
                if provider_name in r.providers_tried and r.result in (CallResult.FAILURE, CallResult.TIMEOUT)
            ][-10:]

            return {
                'status': status,
                'metrics': pm.to_dict(),
                'recent_errors': recent_errors,
            }

    def get_recent_calls(
        self,
        limit: int = 100,
        data_type: Optional[DataType] = None,
        provider: Optional[str] = None,
        symbol: Optional[str] = None,
        errors_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Get recent call records with optional filtering.

        Args:
            limit: Maximum number of records to return
            data_type: Filter by data type
            provider: Filter by provider
            symbol: Filter by symbol
            errors_only: Only return error records

        Returns:
            List of call records as dictionaries
        """
        with self._lock:
            records = list(self._records)

        # Apply filters
        if data_type:
            records = [r for r in records if r.data_type == data_type]
        if provider:
            records = [r for r in records if provider in r.providers_tried]
        if symbol:
            records = [r for r in records if r.symbol == symbol.upper()]
        if errors_only:
            records = [r for r in records if r.result in (CallResult.FAILURE, CallResult.TIMEOUT)]

        # Return most recent
        return [r.to_dict() for r in records[-limit:]]

    def get_latency_percentiles(
        self,
        provider: Optional[str] = None,
        data_type: Optional[DataType] = None,
    ) -> Dict[str, float]:
        """
        Calculate latency percentiles.

        Args:
            provider: Filter by provider
            data_type: Filter by data type

        Returns:
            Dict with p50, p90, p95, p99 latencies in ms
        """
        with self._lock:
            records = [r for r in self._records if r.result == CallResult.SUCCESS]

        if provider:
            records = [r for r in records if r.provider_used == provider]
        if data_type:
            records = [r for r in records if r.data_type == data_type]

        if not records:
            return {'p50': 0, 'p90': 0, 'p95': 0, 'p99': 0}

        latencies = sorted([r.latency_ms for r in records])
        n = len(latencies)

        return {
            'p50': round(latencies[int(n * 0.50)], 2),
            'p90': round(latencies[int(n * 0.90)], 2),
            'p95': round(latencies[int(n * 0.95)], 2),
            'p99': round(latencies[min(int(n * 0.99), n - 1)], 2),
        }

    def reset(self) -> None:
        """Reset all metrics (useful for testing)."""
        with self._lock:
            self._records.clear()
            self._provider_metrics.clear()
            for dt in DataType:
                self._data_type_metrics[dt] = DataTypeMetrics()
            self._start_time = datetime.now()
            logger.info("[Metrics] Metrics reset")


# Singleton instance
metrics_collector = MetricsCollector()


# Convenience function for integration
def record_call(
    data_type: DataType,
    symbol: str,
    providers_tried: List[str],
    provider_used: Optional[str],
    latency_ms: float,
    **kwargs
) -> None:
    """Convenience wrapper for metrics_collector.record_call()."""
    metrics_collector.record_call(
        data_type=data_type,
        symbol=symbol,
        providers_tried=providers_tried,
        provider_used=provider_used,
        latency_ms=latency_ms,
        **kwargs
    )

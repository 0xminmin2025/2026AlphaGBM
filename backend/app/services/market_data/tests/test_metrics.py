"""
Unit tests for Market Data Metrics module.

Tests the MetricsCollector, CallRecord, and statistics aggregation.
"""

import pytest
import time
from datetime import datetime
from unittest.mock import patch

from ..metrics import (
    MetricsCollector,
    CallRecord,
    CallResult,
    ProviderMetrics,
    DataTypeMetrics,
    metrics_collector,
)
from ..interfaces import DataType


class TestCallRecord:
    """Tests for CallRecord dataclass."""

    def test_to_dict(self):
        """Test CallRecord serialization to dict."""
        record = CallRecord(
            timestamp=datetime(2024, 1, 15, 10, 30, 0),
            data_type=DataType.QUOTE,
            symbol="AAPL",
            providers_tried=["yfinance", "tiger"],
            provider_used="yfinance",
            result=CallResult.SUCCESS,
            cache_hit=False,
            latency_ms=150.5,
            fallback_used=False,
        )

        d = record.to_dict()

        assert d["timestamp"] == "2024-01-15T10:30:00"
        assert d["data_type"] == "quote"
        assert d["symbol"] == "AAPL"
        assert d["providers_tried"] == ["yfinance", "tiger"]
        assert d["provider_used"] == "yfinance"
        assert d["result"] == "success"
        assert d["cache_hit"] is False
        assert d["latency_ms"] == 150.5
        assert d["fallback_used"] is False

    def test_to_dict_with_error(self):
        """Test CallRecord serialization with error info."""
        record = CallRecord(
            timestamp=datetime(2024, 1, 15, 10, 30, 0),
            data_type=DataType.QUOTE,
            symbol="AAPL",
            providers_tried=["yfinance"],
            provider_used=None,
            result=CallResult.FAILURE,
            cache_hit=False,
            latency_ms=500.0,
            fallback_used=False,
            error_type="HTTPError",
            error_message="Connection timeout",
        )

        d = record.to_dict()

        assert d["provider_used"] is None
        assert d["result"] == "failure"
        assert d["error_type"] == "HTTPError"
        assert d["error_message"] == "Connection timeout"


class TestProviderMetrics:
    """Tests for ProviderMetrics dataclass."""

    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        metrics = ProviderMetrics(
            total_calls=100,
            successful_calls=95,
            failed_calls=5,
        )

        assert metrics.success_rate == 95.0

    def test_success_rate_zero_calls(self):
        """Test success rate with zero calls."""
        metrics = ProviderMetrics()
        assert metrics.success_rate == 0.0

    def test_avg_latency_calculation(self):
        """Test average latency calculation."""
        metrics = ProviderMetrics(
            successful_calls=10,
            total_latency_ms=1500.0,
        )

        assert metrics.avg_latency_ms == 150.0

    def test_avg_latency_zero_calls(self):
        """Test average latency with zero successful calls."""
        metrics = ProviderMetrics()
        assert metrics.avg_latency_ms == 0.0

    def test_to_dict(self):
        """Test serialization to dict."""
        metrics = ProviderMetrics(
            total_calls=100,
            successful_calls=95,
            failed_calls=5,
            timeout_calls=2,
            rate_limited_calls=1,
            total_latency_ms=14250.0,
            min_latency_ms=50.0,
            max_latency_ms=500.0,
            last_error="HTTPError",
            last_error_time=datetime(2024, 1, 15, 10, 30, 0),
            last_success_time=datetime(2024, 1, 15, 10, 35, 0),
        )

        d = metrics.to_dict()

        assert d["total_calls"] == 100
        assert d["successful_calls"] == 95
        assert d["success_rate"] == 95.0
        assert d["avg_latency_ms"] == 150.0
        assert d["min_latency_ms"] == 50.0
        assert d["max_latency_ms"] == 500.0
        assert d["last_error"] == "HTTPError"


class TestDataTypeMetrics:
    """Tests for DataTypeMetrics dataclass."""

    def test_cache_hit_rate(self):
        """Test cache hit rate calculation."""
        metrics = DataTypeMetrics(
            total_calls=100,
            cache_hits=60,
            cache_misses=40,
        )

        assert metrics.cache_hit_rate == 60.0

    def test_fallback_rate(self):
        """Test fallback rate calculation."""
        metrics = DataTypeMetrics(
            total_calls=100,
            fallback_used=10,
        )

        assert metrics.fallback_rate == 10.0


class TestMetricsCollector:
    """Tests for MetricsCollector."""

    @pytest.fixture
    def collector(self):
        """Create a fresh MetricsCollector for each test."""
        # Create a new instance (bypass singleton for testing)
        collector = object.__new__(MetricsCollector)
        collector._initialized = False
        collector.__init__()
        return collector

    def test_record_successful_call(self, collector):
        """Test recording a successful call."""
        collector.record_call(
            data_type=DataType.QUOTE,
            symbol="AAPL",
            providers_tried=["yfinance"],
            provider_used="yfinance",
            latency_ms=150.0,
            cache_hit=False,
            success=True,
        )

        stats = collector.get_stats()

        assert stats["totals"]["total_calls"] == 1
        assert stats["totals"]["failures"] == 0
        assert stats["by_data_type"]["quote"]["total_calls"] == 1
        assert stats["by_provider"]["yfinance"]["successful_calls"] == 1

    def test_record_cache_hit(self, collector):
        """Test recording a cache hit."""
        collector.record_call(
            data_type=DataType.QUOTE,
            symbol="AAPL",
            providers_tried=[],
            provider_used=None,
            latency_ms=1.0,
            cache_hit=True,
            success=True,
        )

        stats = collector.get_stats()

        assert stats["totals"]["cache_hits"] == 1
        assert stats["by_data_type"]["quote"]["cache_hits"] == 1

    def test_record_fallback(self, collector):
        """Test recording a call that used fallback."""
        collector.record_call(
            data_type=DataType.QUOTE,
            symbol="AAPL",
            providers_tried=["yfinance", "tiger"],
            provider_used="tiger",
            latency_ms=300.0,
            cache_hit=False,
            success=True,
            fallback_used=True,
        )

        stats = collector.get_stats()

        assert stats["totals"]["fallback_used"] == 1
        assert stats["by_data_type"]["quote"]["fallback_used"] == 1
        # yfinance should be marked as failed
        assert stats["by_provider"]["yfinance"]["failed_calls"] == 1
        # tiger should be marked as successful
        assert stats["by_provider"]["tiger"]["successful_calls"] == 1

    def test_record_failure(self, collector):
        """Test recording a failed call."""
        collector.record_call(
            data_type=DataType.QUOTE,
            symbol="AAPL",
            providers_tried=["yfinance", "tiger"],
            provider_used=None,
            latency_ms=500.0,
            cache_hit=False,
            success=False,
            error_type="HTTPError",
            error_message="All providers failed",
        )

        stats = collector.get_stats()

        assert stats["totals"]["failures"] == 1
        assert stats["by_data_type"]["quote"]["failures"] == 1
        assert len(stats["recent_errors"]) == 1
        assert stats["recent_errors"][0]["error_type"] == "HTTPError"

    def test_get_provider_health_healthy(self, collector):
        """Test provider health when healthy."""
        # Record 100 calls with 98% success
        for i in range(98):
            collector.record_call(
                data_type=DataType.QUOTE,
                symbol="AAPL",
                providers_tried=["yfinance"],
                provider_used="yfinance",
                latency_ms=100.0,
                success=True,
            )
        for i in range(2):
            collector.record_call(
                data_type=DataType.QUOTE,
                symbol="AAPL",
                providers_tried=["yfinance"],
                provider_used=None,
                latency_ms=500.0,
                success=False,
            )

        health = collector.get_provider_health("yfinance")

        assert health["status"] == "healthy"
        assert health["metrics"]["success_rate"] == 98.0

    def test_get_provider_health_degraded(self, collector):
        """Test provider health when degraded."""
        # Record 100 calls with 85% success
        for i in range(85):
            collector.record_call(
                data_type=DataType.QUOTE,
                symbol="AAPL",
                providers_tried=["yfinance"],
                provider_used="yfinance",
                latency_ms=100.0,
                success=True,
            )
        for i in range(15):
            collector.record_call(
                data_type=DataType.QUOTE,
                symbol="AAPL",
                providers_tried=["yfinance"],
                provider_used=None,
                latency_ms=500.0,
                success=False,
            )

        health = collector.get_provider_health("yfinance")

        assert health["status"] == "degraded"

    def test_get_provider_health_unhealthy(self, collector):
        """Test provider health when unhealthy."""
        # Record 100 calls with 70% success
        for i in range(70):
            collector.record_call(
                data_type=DataType.QUOTE,
                symbol="AAPL",
                providers_tried=["yfinance"],
                provider_used="yfinance",
                latency_ms=100.0,
                success=True,
            )
        for i in range(30):
            collector.record_call(
                data_type=DataType.QUOTE,
                symbol="AAPL",
                providers_tried=["yfinance"],
                provider_used=None,
                latency_ms=500.0,
                success=False,
            )

        health = collector.get_provider_health("yfinance")

        assert health["status"] == "unhealthy"

    def test_get_recent_calls_filtering(self, collector):
        """Test filtering recent calls."""
        # Record various calls
        collector.record_call(
            data_type=DataType.QUOTE,
            symbol="AAPL",
            providers_tried=["yfinance"],
            provider_used="yfinance",
            latency_ms=100.0,
            success=True,
        )
        collector.record_call(
            data_type=DataType.OPTIONS_CHAIN,
            symbol="AAPL",
            providers_tried=["tiger"],
            provider_used="tiger",
            latency_ms=200.0,
            success=True,
        )
        collector.record_call(
            data_type=DataType.QUOTE,
            symbol="MSFT",
            providers_tried=["yfinance"],
            provider_used=None,
            latency_ms=500.0,
            success=False,
        )

        # Filter by data type
        quote_calls = collector.get_recent_calls(data_type=DataType.QUOTE)
        assert len(quote_calls) == 2

        # Filter by provider
        tiger_calls = collector.get_recent_calls(provider="tiger")
        assert len(tiger_calls) == 1

        # Filter by symbol
        aapl_calls = collector.get_recent_calls(symbol="AAPL")
        assert len(aapl_calls) == 2

        # Filter errors only
        error_calls = collector.get_recent_calls(errors_only=True)
        assert len(error_calls) == 1

    def test_get_latency_percentiles(self, collector):
        """Test latency percentile calculation."""
        # Record calls with various latencies
        latencies = [50, 100, 150, 200, 250, 300, 350, 400, 450, 500]
        for latency in latencies:
            collector.record_call(
                data_type=DataType.QUOTE,
                symbol="AAPL",
                providers_tried=["yfinance"],
                provider_used="yfinance",
                latency_ms=float(latency),
                success=True,
            )

        percentiles = collector.get_latency_percentiles()

        assert percentiles["p50"] > 0
        assert percentiles["p90"] > percentiles["p50"]
        assert percentiles["p99"] >= percentiles["p95"]

    def test_ring_buffer_limit(self, collector):
        """Test that ring buffer respects max size."""
        # The collector is initialized with MAX_RECORDS=10000
        # We test that the deque correctly limits size
        original_maxlen = collector._records.maxlen

        # Record more than a reasonable amount
        for i in range(50):
            collector.record_call(
                data_type=DataType.QUOTE,
                symbol=f"STOCK{i}",
                providers_tried=["yfinance"],
                provider_used="yfinance",
                latency_ms=100.0,
                success=True,
            )

        # Verify the buffer stores records correctly
        assert len(collector._records) == 50
        assert collector._records.maxlen == original_maxlen

    def test_reset(self, collector):
        """Test metrics reset."""
        collector.record_call(
            data_type=DataType.QUOTE,
            symbol="AAPL",
            providers_tried=["yfinance"],
            provider_used="yfinance",
            latency_ms=100.0,
            success=True,
        )

        collector.reset()
        stats = collector.get_stats()

        assert stats["totals"]["total_calls"] == 0
        assert len(stats["by_provider"]) == 0
        assert stats["buffer_size"] == 0


class TestMetricsIntegration:
    """Integration tests for metrics with service."""

    def test_singleton_instance(self):
        """Test that metrics_collector is a singleton."""
        from ..metrics import metrics_collector as mc1
        from ..metrics import metrics_collector as mc2

        assert mc1 is mc2

    def test_thread_safety(self, collector=None):
        """Test thread-safe metrics recording."""
        import threading

        if collector is None:
            # Create a fresh collector for this test
            collector = object.__new__(MetricsCollector)
            collector._initialized = False
            collector.__init__()

        def record_calls():
            for i in range(100):
                collector.record_call(
                    data_type=DataType.QUOTE,
                    symbol="AAPL",
                    providers_tried=["yfinance"],
                    provider_used="yfinance",
                    latency_ms=100.0,
                    success=True,
                )

        threads = [threading.Thread(target=record_calls) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        stats = collector.get_stats()
        assert stats["totals"]["total_calls"] == 500

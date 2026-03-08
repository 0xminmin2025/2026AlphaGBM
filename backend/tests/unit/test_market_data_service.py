"""
Unit tests for MarketDataService.

Tests the singleton pattern and market detection logic for US, CN, and HK
symbols. All adapters and external services are mocked out.
"""

import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Fixtures: Isolate the singleton so tests do not interfere with each other
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_singleton():
    """Reset MarketDataService singleton state before and after each test
    so that tests are independent."""
    with patch('app.services.market_data.service.MarketDataService._register_default_adapters'):
        yield
    # Clean up singleton for next test
    from app.services.market_data.service import MarketDataService
    MarketDataService._instance = None


# ---------------------------------------------------------------------------
# Tests: Singleton pattern
# ---------------------------------------------------------------------------

class TestSingletonPattern:

    def test_singleton_pattern(self):
        """MarketDataService() should always return the same instance."""
        from app.services.market_data.service import MarketDataService
        # Reset to ensure a clean state
        MarketDataService._instance = None

        with patch.object(MarketDataService, '_register_default_adapters'):
            svc_a = MarketDataService()
            svc_b = MarketDataService()

        assert svc_a is svc_b


# ---------------------------------------------------------------------------
# Tests: Market detection via get_market_for_symbol
# ---------------------------------------------------------------------------

class TestMarketDetection:
    """Test the get_market_for_symbol helper which determines market type
    based on the ticker symbol string."""

    def test_market_detection_us(self):
        """'AAPL' (no suffix) should be detected as US market."""
        from app.services.market_data.config import get_market_for_symbol
        from app.services.market_data.interfaces import Market

        result = get_market_for_symbol('AAPL')
        assert result == Market.US

    def test_market_detection_cn_ss(self):
        """'600519.SS' (Shanghai suffix) should be detected as CN market."""
        from app.services.market_data.config import get_market_for_symbol
        from app.services.market_data.interfaces import Market

        result = get_market_for_symbol('600519.SS')
        assert result == Market.CN

    def test_market_detection_cn_sz(self):
        """'000001.SZ' (Shenzhen suffix) should be detected as CN market."""
        from app.services.market_data.config import get_market_for_symbol
        from app.services.market_data.interfaces import Market

        result = get_market_for_symbol('000001.SZ')
        assert result == Market.CN

    def test_market_detection_hk(self):
        """'0700.HK' should be detected as HK market."""
        from app.services.market_data.config import get_market_for_symbol
        from app.services.market_data.interfaces import Market

        result = get_market_for_symbol('0700.HK')
        assert result == Market.HK

    def test_market_detection_us_etf(self):
        """'SPY' (common US ETF) should be detected as US market."""
        from app.services.market_data.config import get_market_for_symbol
        from app.services.market_data.interfaces import Market

        result = get_market_for_symbol('SPY')
        assert result == Market.US

"""
Unit tests for DataProvider facade.

DataProvider is a drop-in replacement for yf.Ticker that delegates to
MarketDataService. These tests verify the facade interface without
hitting any real network or database.
"""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock
import pandas as pd
import numpy as np


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _patch_market_data_service():
    """Patch the market_data_service singleton used by DataProvider."""
    mock_mds = MagicMock()
    with patch('app.services.data_provider.market_data_service', mock_mds):
        yield mock_mds


def _make_provider(symbol='AAPL'):
    from app.services.data_provider import DataProvider
    return DataProvider(symbol)


# ---------------------------------------------------------------------------
# Tests: creation
# ---------------------------------------------------------------------------

class TestCreateTicker:

    def test_create_ticker(self, _patch_market_data_service):
        """DataProvider(symbol) should return a ticker-like object
        with the symbol stored on it."""
        provider = _make_provider('MSFT')

        assert provider.ticker == 'MSFT'
        assert hasattr(provider, 'info')
        assert callable(getattr(provider, 'history', None))


# ---------------------------------------------------------------------------
# Tests: .info property
# ---------------------------------------------------------------------------

class TestInfoProperty:

    def test_info_property(self, _patch_market_data_service):
        """The .info property should return a dict obtained from
        market_data_service.get_ticker_data()."""
        mock_mds = _patch_market_data_service
        mock_mds.get_ticker_data.return_value = {
            'symbol': 'AAPL',
            'regularMarketPrice': 185.50,
            'currentPrice': 185.50,
            'shortName': 'Apple Inc.',
        }

        provider = _make_provider('AAPL')
        info = provider.info

        assert isinstance(info, dict)
        assert info['regularMarketPrice'] == 185.50
        assert info['symbol'] == 'AAPL'
        mock_mds.get_ticker_data.assert_called_once_with('AAPL')

    def test_info_caches_result(self, _patch_market_data_service):
        """Repeated access to .info should use the cached value."""
        mock_mds = _patch_market_data_service
        mock_mds.get_ticker_data.return_value = {
            'symbol': 'AAPL',
            'regularMarketPrice': 185.0,
        }

        provider = _make_provider('AAPL')
        _ = provider.info
        _ = provider.info  # second access

        # Should only call the service once due to caching
        assert mock_mds.get_ticker_data.call_count == 1

    def test_info_fallback_on_failure(self, _patch_market_data_service):
        """When market_data_service raises, .info returns a minimal dict
        with just the symbol."""
        mock_mds = _patch_market_data_service
        mock_mds.get_ticker_data.side_effect = Exception('network error')

        provider = _make_provider('FAIL')
        info = provider.info

        assert isinstance(info, dict)
        assert info['symbol'] == 'FAIL'


# ---------------------------------------------------------------------------
# Tests: .history() method
# ---------------------------------------------------------------------------

class TestHistoryMethod:

    def test_history_method(self, _patch_market_data_service):
        """The .history() method should return a DataFrame from
        market_data_service.get_history_df()."""
        mock_mds = _patch_market_data_service
        expected_df = pd.DataFrame({
            'Open': [180.0, 181.0],
            'High': [185.0, 186.0],
            'Low': [179.0, 180.0],
            'Close': [184.0, 185.0],
            'Volume': [1000000, 1100000],
        })
        mock_mds.get_history_df.return_value = expected_df

        provider = _make_provider('AAPL')
        result = provider.history(period='5d')

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert 'Close' in result.columns
        mock_mds.get_history_df.assert_called_once()

    def test_history_returns_empty_on_failure(self, _patch_market_data_service):
        """When the underlying service fails, .history() should return
        an empty DataFrame rather than raising."""
        mock_mds = _patch_market_data_service
        mock_mds.get_history_df.side_effect = Exception('timeout')

        provider = _make_provider('AAPL')
        result = provider.history(period='1mo')

        assert isinstance(result, pd.DataFrame)
        assert result.empty

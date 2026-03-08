"""
Unit tests for the scheduler module.

Tests get_exchange_rates (success and fallback), convert_to_usd for
HKD/CNY/USD, and get_current_stock_price with mocked DataProvider.
"""

import pytest
from unittest.mock import patch, MagicMock

from app.scheduler import (
    get_exchange_rates,
    convert_to_usd,
    get_current_stock_price,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reset_exchange_rate_cache():
    """Reset the module-level cache so each test starts fresh."""
    import app.scheduler as sched
    sched.exchange_rates_cache = {}
    sched.cache_timestamp = None


# ===================================================================
# test_get_exchange_rates_success
# ===================================================================

class TestGetExchangeRatesSuccess:
    """Successful API call should return a rates dict."""

    @patch('app.scheduler.requests.get')
    def test_returns_rates_dict(self, mock_get):
        _reset_exchange_rate_cache()

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            'rates': {
                'HKD': 7.82,
                'CNY': 7.25,
            }
        }
        mock_get.return_value = mock_resp

        rates = get_exchange_rates()

        assert 'USD_TO_HKD' in rates
        assert 'USD_TO_CNY' in rates
        assert 'HKD_TO_USD' in rates
        assert 'CNY_TO_USD' in rates
        assert abs(rates['USD_TO_HKD'] - 7.82) < 1e-6
        assert abs(rates['HKD_TO_USD'] - 1 / 7.82) < 1e-6


# ===================================================================
# test_get_exchange_rates_fallback
# ===================================================================

class TestGetExchangeRatesFallback:
    """When the API fails, fallback rates (7.8 HKD, 7.2 CNY) are used."""

    @patch('app.scheduler.requests.get', side_effect=Exception('Network error'))
    def test_fallback_on_error(self, mock_get):
        _reset_exchange_rate_cache()

        rates = get_exchange_rates()

        assert rates['USD_TO_HKD'] == 7.8
        assert rates['USD_TO_CNY'] == 7.2
        assert abs(rates['HKD_TO_USD'] - 0.128) < 1e-6
        assert abs(rates['CNY_TO_USD'] - 0.139) < 1e-6


# ===================================================================
# test_convert_to_usd_hkd
# ===================================================================

class TestConvertToUsdHkd:
    """HKD conversion uses HKD_TO_USD rate."""

    def test_hkd_conversion(self):
        rates = {'HKD_TO_USD': 0.128, 'CNY_TO_USD': 0.139}
        result = convert_to_usd(1000, 'HKD', rates)
        assert abs(result - 128.0) < 1e-6

    def test_hkd_zero(self):
        rates = {'HKD_TO_USD': 0.128, 'CNY_TO_USD': 0.139}
        result = convert_to_usd(0, 'HKD', rates)
        assert result == 0.0


# ===================================================================
# test_convert_to_usd_cny
# ===================================================================

class TestConvertToUsdCny:
    """CNY conversion uses CNY_TO_USD rate."""

    def test_cny_conversion(self):
        rates = {'HKD_TO_USD': 0.128, 'CNY_TO_USD': 0.139}
        result = convert_to_usd(1000, 'CNY', rates)
        assert abs(result - 139.0) < 1e-6


# ===================================================================
# test_convert_to_usd_usd
# ===================================================================

class TestConvertToUsdUsd:
    """USD to USD should return the same amount (no conversion)."""

    def test_usd_no_conversion(self):
        rates = {'HKD_TO_USD': 0.128, 'CNY_TO_USD': 0.139}
        result = convert_to_usd(250.50, 'USD', rates)
        assert result == 250.50

    def test_unknown_currency_treated_as_usd(self):
        rates = {'HKD_TO_USD': 0.128, 'CNY_TO_USD': 0.139}
        result = convert_to_usd(100.0, 'EUR', rates)
        assert result == 100.0


# ===================================================================
# test_get_current_stock_price
# ===================================================================

class TestGetCurrentStockPrice:
    """get_current_stock_price should use DataProvider and return a float."""

    @patch('app.scheduler.DataProvider')
    def test_returns_current_price(self, MockDP):
        mock_instance = MagicMock()
        mock_instance.info = {'currentPrice': 185.50}
        MockDP.return_value = mock_instance

        price = get_current_stock_price('AAPL')

        MockDP.assert_called_once_with('AAPL')
        assert price == 185.50

    @patch('app.scheduler.DataProvider')
    def test_falls_back_to_regular_market_price(self, MockDP):
        mock_instance = MagicMock()
        mock_instance.info = {'currentPrice': None, 'regularMarketPrice': 180.0}
        MockDP.return_value = mock_instance

        price = get_current_stock_price('AAPL')
        assert price == 180.0

    @patch('app.scheduler.DataProvider')
    def test_returns_none_on_no_data(self, MockDP):
        mock_instance = MagicMock()
        mock_instance.info = {}
        MockDP.return_value = mock_instance

        price = get_current_stock_price('FAKE')
        assert price is None

    @patch('app.scheduler.DataProvider')
    def test_returns_none_on_exception(self, MockDP):
        MockDP.side_effect = Exception('API down')

        price = get_current_stock_price('AAPL')
        assert price is None

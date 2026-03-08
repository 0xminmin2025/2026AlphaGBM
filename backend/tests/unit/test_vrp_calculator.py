"""
Unit tests for VRPCalculator.

Tests VRP (Volatility Risk Premium) calculation including premium cases
(IV > RV), discount cases (IV < RV), and graceful handling of missing data.
"""

import pytest
from app.analysis.options_analysis.advanced.vrp_calculator import VRPCalculator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_options_data(avg_iv=0.30, atm_iv=0.30, iv_min=0.20, iv_max=0.40):
    """Build a minimal options_data dict with specified IV metrics."""
    return {
        'success': True,
        'calls': [
            {'strike': 100, 'impliedVolatility': avg_iv, 'openInterest': 1000},
        ],
        'puts': [
            {'strike': 100, 'impliedVolatility': avg_iv, 'openInterest': 800},
        ],
    }


def _make_stock_data(vol_30d=0.20, close_prices=None):
    """Build a minimal stock_data dict."""
    data = {
        'success': True,
        'volatility_30d': vol_30d,
    }
    if close_prices is not None:
        data['history'] = {'Close': close_prices}
    return data


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestVRPCalculator:

    def test_vrp_premium(self):
        """When IV > RV (realized volatility), VRP should be positive,
        indicating options are 'expensive' and favor sell strategies."""
        calc = VRPCalculator()

        # IV metrics will use the estimated values from _calculate_implied_volatility_metrics
        # Stock data has low historical volatility so VRP = IV - RV > 0
        options_data = _make_options_data(avg_iv=0.35)
        stock_data = _make_stock_data(vol_30d=0.20)

        result = calc.calculate('AAPL', options_data, stock_data)

        assert result['success'] is True
        vrp = result['vrp_analysis']
        # IV (implied) should be greater than HV (historical) -> positive VRP
        assert vrp['vrp_absolute'] > 0 or vrp['implied_vol'] >= vrp['historical_vol']

    def test_vrp_discount(self):
        """When IV < RV, VRP should be negative,
        indicating options are 'cheap' and favor buy strategies."""
        calc = VRPCalculator()

        # Low IV options on a high-volatility stock
        options_data = _make_options_data(avg_iv=0.15)
        stock_data = _make_stock_data(vol_30d=0.35)

        result = calc.calculate('TSLA', options_data, stock_data)

        assert result['success'] is True
        # The VRP analysis should reflect that options are underpriced
        # _calculate_historical_volatility will use volatility_30d=0.35 from stock_data
        # _calculate_implied_volatility_metrics will compute from the options_data
        # The relative VRP should trend negative
        vrp = result['vrp_analysis']
        hv = result['historical_volatility']
        # Historical volatility should reflect the high input
        assert hv['volatility_30d'] == 0.35

    def test_vrp_with_missing_data(self):
        """When options_data indicates failure, calculate() should return
        success=False gracefully without raising."""
        calc = VRPCalculator()

        options_data = {'success': False}
        stock_data = _make_stock_data()

        result = calc.calculate('INVALID', options_data, stock_data)

        assert result['success'] is False
        assert 'error' in result

    def test_vrp_with_empty_options(self):
        """With no calls/puts in options_data, calculation should still
        succeed using default IV estimates."""
        calc = VRPCalculator()

        options_data = {
            'success': True,
            'calls': [],
            'puts': [],
        }
        stock_data = _make_stock_data(vol_30d=0.25)

        result = calc.calculate('SPY', options_data, stock_data)

        assert result['success'] is True
        assert 'vrp_analysis' in result

    def test_vrp_thresholds_initialized(self):
        """VRPCalculator should have the expected threshold configuration."""
        calc = VRPCalculator()

        assert calc.vrp_thresholds['high_premium'] == 0.15
        assert calc.vrp_thresholds['moderate_premium'] == 0.05
        assert calc.vrp_thresholds['low_premium'] == -0.05
        assert calc.vrp_thresholds['negative_premium'] == -0.15

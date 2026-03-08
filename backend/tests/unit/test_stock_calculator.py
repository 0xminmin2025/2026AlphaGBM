"""
Unit tests for StockCalculator.
Tests liquidity checking, ATR calculation, and ATR-based stop-loss logic.
"""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch


# ---------------------------------------------------------------------------
# We patch the constants import so we control threshold values.
# ---------------------------------------------------------------------------

@pytest.fixture()
def calculator():
    """Return a fresh StockCalculator with known defaults."""
    with patch.dict('sys.modules', {}):
        # Re-import with controlled constants
        import importlib
        try:
            from app.analysis.stock_analysis.core.calculator import StockCalculator
        except Exception:
            # If constants import fails the module uses its own defaults
            from app.analysis.stock_analysis.core.calculator import StockCalculator
        calc = StockCalculator()
        # Ensure known thresholds regardless of constants file
        calc.min_daily_volume_usd = 5_000_000
        calc.atr_multiplier_base = 2.5
        return calc


# ---------------------------------------------------------------------------
# Sample data helpers
# ---------------------------------------------------------------------------

def _make_history_data(price=100.0, volume=200_000, days=30):
    """Return a market data dict with uniform price/volume history."""
    return {
        'history_prices': [price] * days,
        'history_volumes': [volume] * days,
    }


def _make_ohlc_dataframe(rows=20, base_price=100.0):
    """Return a DataFrame with Open/High/Low/Close columns suitable for ATR."""
    np.random.seed(42)
    dates = pd.date_range('2025-01-01', periods=rows, freq='B')
    close = base_price + np.cumsum(np.random.randn(rows) * 0.5)
    high = close + np.abs(np.random.randn(rows)) * 1.0
    low = close - np.abs(np.random.randn(rows)) * 1.0
    return pd.DataFrame({
        'Open': close + np.random.randn(rows) * 0.3,
        'High': high,
        'Low': low,
        'Close': close,
    }, index=dates)


# ---------------------------------------------------------------------------
# Liquidity tests
# ---------------------------------------------------------------------------

class TestCheckLiquidity:

    def test_check_liquidity_sufficient(self, calculator):
        """avg_volume * price > $5M  -->  is_liquid = True."""
        # price=100, volume=200_000 => daily_volume_usd = 20M
        data = _make_history_data(price=100.0, volume=200_000)
        is_liquid, info = calculator.check_liquidity(data)

        assert bool(is_liquid) is True
        assert info['avg_daily_volume_usd'] >= calculator.min_daily_volume_usd

    def test_check_liquidity_insufficient(self, calculator):
        """avg_volume * price < $5M  -->  is_liquid = False."""
        # price=1.0, volume=1000 => daily_volume_usd = 1000
        data = _make_history_data(price=1.0, volume=1000)
        is_liquid, info = calculator.check_liquidity(data)

        assert bool(is_liquid) is False
        assert info['avg_daily_volume_usd'] < calculator.min_daily_volume_usd

    def test_check_liquidity_empty_history(self, calculator):
        """No history data at all  -->  is_liquid = False."""
        data = {'info': {}}
        is_liquid, info = calculator.check_liquidity(data)

        assert is_liquid is False

    def test_check_liquidity_from_info_fallback(self, calculator):
        """Uses info.averageVolume * currentPrice when history is absent."""
        data = {
            'info': {
                'averageVolume': 1_000_000,
                'regularMarketPrice': 50.0,
            }
        }
        is_liquid, info = calculator.check_liquidity(data)

        # 1M * 50 = 50M > 5M
        assert is_liquid is True
        assert info['source'] == 'yfinance_info'

    def test_check_liquidity_mismatched_lengths(self, calculator):
        """Mismatched history_prices / history_volumes  -->  False."""
        data = {
            'history_prices': [100.0, 101.0],
            'history_volumes': [50_000],
        }
        is_liquid, info = calculator.check_liquidity(data)

        assert is_liquid is False


# ---------------------------------------------------------------------------
# ATR tests
# ---------------------------------------------------------------------------

class TestCalculateATR:

    def test_calculate_atr_positive(self, calculator):
        """ATR on valid OHLC data produces a positive float."""
        df = _make_ohlc_dataframe(rows=30, base_price=100.0)
        atr = calculator.calculate_atr(df, period=14)

        assert isinstance(atr, float)
        assert atr > 0

    def test_calculate_atr_insufficient_data(self, calculator):
        """Fewer rows than the ATR period  -->  0.0."""
        df = _make_ohlc_dataframe(rows=5, base_price=100.0)
        atr = calculator.calculate_atr(df, period=14)

        assert atr == 0.0

    def test_calculate_atr_empty_dataframe(self, calculator):
        """Empty DataFrame  -->  0.0."""
        df = pd.DataFrame(columns=['Open', 'High', 'Low', 'Close'])
        atr = calculator.calculate_atr(df)

        assert atr == 0.0


# ---------------------------------------------------------------------------
# ATR stop-loss tests
# ---------------------------------------------------------------------------

class TestCalculateATRStopLoss:

    def test_atr_stop_loss_basic(self, calculator):
        """Positive ATR  -->  stop_loss_price < buy_price."""
        df = _make_ohlc_dataframe(rows=30, base_price=100.0)
        result = calculator.calculate_atr_stop_loss(buy_price=100.0, hist_data=df)

        assert result['stop_loss_price'] < 100.0
        assert result['stop_loss_pct'] > 0
        assert result['atr'] > 0

    def test_atr_stop_loss_uses_multiplier(self, calculator):
        """ATR * multiplier determines the distance from buy price."""
        df = _make_ohlc_dataframe(rows=30, base_price=100.0)
        result = calculator.calculate_atr_stop_loss(
            buy_price=100.0, hist_data=df, atr_multiplier=3.0
        )
        # The suggested stop should reflect multiplier=3.0
        expected_suggested = 100.0 - (result['atr'] * 3.0)
        assert abs(result.get('atr_suggested_price', result['stop_loss_price']) - expected_suggested) < 0.01

    def test_atr_stop_loss_beta_adjustment_high(self, calculator):
        """High beta (>1.5)  -->  wider stop (multiplier *= 1.2)."""
        df = _make_ohlc_dataframe(rows=30, base_price=100.0)
        result_normal = calculator.calculate_atr_stop_loss(
            buy_price=100.0, hist_data=df
        )
        result_high_beta = calculator.calculate_atr_stop_loss(
            buy_price=100.0, hist_data=df, beta=2.0
        )
        # High beta should have a wider stop (lower stop price or higher multiplier)
        assert result_high_beta['atr_multiplier'] > result_normal['atr_multiplier']

    def test_atr_stop_loss_beta_adjustment_low(self, calculator):
        """Low beta (<0.8)  -->  tighter stop (multiplier *= 0.8)."""
        df = _make_ohlc_dataframe(rows=30, base_price=100.0)
        result_normal = calculator.calculate_atr_stop_loss(
            buy_price=100.0, hist_data=df
        )
        result_low_beta = calculator.calculate_atr_stop_loss(
            buy_price=100.0, hist_data=df, beta=0.5
        )
        assert result_low_beta['atr_multiplier'] < result_normal['atr_multiplier']

    def test_atr_fallback_fixed_15pct(self, calculator):
        """When ATR = 0 (insufficient data), fall back to 15% fixed stop."""
        df = _make_ohlc_dataframe(rows=3, base_price=100.0)  # too few for ATR
        result = calculator.calculate_atr_stop_loss(buy_price=100.0, hist_data=df)

        assert result['method'] == 'fixed_percentage'
        assert result['atr'] == 0
        # 15% stop from 100 => 85
        assert abs(result['stop_loss_price'] - 85.0) < 0.01
        assert abs(result['stop_loss_pct'] - 0.15) < 0.001

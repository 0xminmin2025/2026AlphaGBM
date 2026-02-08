"""
Unit tests for SellPutScorer.
Tests scoring logic, liquidity handling, score boundaries, and 0DTE capping.
"""
import pytest
from unittest.mock import patch, MagicMock
import numpy as np


@pytest.fixture()
def scorer():
    """Return a SellPutScorer with mocked trend/ATR sub-components."""
    with patch(
        'app.analysis.options_analysis.scoring.sell_put.TrendAnalyzer'
    ) as MockTrend, patch(
        'app.analysis.options_analysis.scoring.sell_put.ATRCalculator'
    ) as MockATR:
        from app.analysis.options_analysis.scoring.sell_put import SellPutScorer

        s = SellPutScorer()
        # Default trend: sideways, neutral
        s.trend_analyzer.analyze_trend_for_strategy.return_value = {
            'trend': 'sideways',
            'trend_strength': 0.5,
            'trend_alignment_score': 70,
            'is_ideal_trend': True,
            'display_info': {
                'trend_name_cn': 'test',
                'is_ideal_trend': True,
                'warning': None,
            },
        }
        s.atr_calculator.calculate_atr.return_value = 2.5
        s.atr_calculator.calculate_atr_based_safety.return_value = {
            'safety_ratio': 1.5,
            'atr_multiples': 3.0,
            'is_safe': True,
        }
        yield s


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def _stock_data(price=180.0):
    return {
        'current_price': price,
        'change_percent': 0.5,
        'volatility_30d': 0.25,
        'price_history': [price - 2 + i * 0.3 for i in range(10)],
        'atr_14': 3.0,
        'support_resistance': {
            'support_1': price * 0.95,
            'support_2': price * 0.90,
            'low_52w': price * 0.70,
        },
        'ma_50': price * 0.97,
        'ma_200': price * 0.92,
    }


def _options_data(symbol='AAPL', puts=None):
    if puts is None:
        puts = [_put_option()]
    return {
        'success': True,
        'symbol': symbol,
        'puts': puts,
        'calls': [],
    }


def _put_option(strike=170.0, bid=2.50, ask=3.00, volume=500,
                open_interest=2000, iv=0.30, dte=30, expiry='2025-03-21'):
    return {
        'strike': strike,
        'bid': bid,
        'ask': ask,
        'volume': volume,
        'open_interest': open_interest,
        'implied_volatility': iv,
        'days_to_expiry': dte,
        'expiry': expiry,
        'symbol': f'AAPL250321P{int(strike*1000):08d}',
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestScoreIdealPut:

    def test_score_ideal_put(self, scorer):
        """Good premium, safe distance, decent liquidity  -->  high score."""
        stock = _stock_data(price=180.0)
        opts = _options_data(puts=[
            _put_option(strike=170.0, bid=3.0, ask=3.50, volume=800,
                        open_interest=5000, iv=0.28, dte=30),
        ])

        result = scorer.score_options(opts, stock)

        assert result['success'] is True
        assert result['strategy'] == 'sell_put'
        assert len(result['recommendations']) > 0
        top = result['recommendations'][0]
        assert top['score'] > 40  # reasonable quality
        assert top['strike'] == 170.0

    def test_score_returns_all_expected_fields(self, scorer):
        """Each recommendation has the full set of result keys."""
        stock = _stock_data()
        opts = _options_data()

        result = scorer.score_options(opts, stock)

        if result['recommendations']:
            rec = result['recommendations'][0]
            expected_keys = {
                'strike', 'expiry', 'days_to_expiry', 'bid', 'ask',
                'mid_price', 'score', 'score_breakdown', 'safety_margin',
            }
            assert expected_keys.issubset(set(rec.keys()))


class TestScoreZeroLiquidity:

    def test_score_zero_open_interest(self, scorer):
        """OI = 0, volume = 0  -->  low liquidity score component."""
        stock = _stock_data(price=180.0)
        opts = _options_data(puts=[
            _put_option(strike=170.0, bid=2.0, ask=2.50, volume=0,
                        open_interest=0, dte=30),
        ])

        result = scorer.score_options(opts, stock)

        # Should still produce a result (score may be low but not necessarily 0
        # because other components contribute)
        assert result['success'] is True
        if result['recommendations']:
            rec = result['recommendations'][0]
            # Liquidity score sub-component should be 0 or very low
            liq_score = rec['score_breakdown'].get('liquidity', 0)
            # bid/ask > 0 so spread_score contributes something, but volume & OI are 0
            assert liq_score < 25

    def test_no_bid_returns_none(self, scorer):
        """bid=0 makes the option unattractive; filtered out."""
        stock = _stock_data(price=180.0)
        opts = _options_data(puts=[
            _put_option(strike=170.0, bid=0, ask=2.50, volume=100,
                        open_interest=500, dte=30),
        ])

        result = scorer.score_options(opts, stock)
        # Filtered out because bid=0 fails the guard
        assert result['success'] is True
        assert len(result['recommendations']) == 0


class TestScoreBoundary:

    def test_score_boundary_0_100(self, scorer):
        """Total score is always clamped to [0, 100]."""
        stock = _stock_data(price=180.0)

        # Test with various strike/premium combos
        test_puts = [
            _put_option(strike=170, bid=1, ask=1.5, dte=30, volume=100, open_interest=200),
            _put_option(strike=175, bid=5, ask=6, dte=45, volume=1000, open_interest=5000),
            _put_option(strike=160, bid=0.5, ask=0.8, dte=7, volume=50, open_interest=100),
            _put_option(strike=178, bid=8, ask=9, dte=60, volume=2000, open_interest=10000),
        ]
        opts = _options_data(puts=test_puts)

        result = scorer.score_options(opts, stock)

        for rec in result.get('recommendations', []):
            assert 0 <= rec['score'] <= 100, (
                f"Score {rec['score']} out of [0,100] for strike={rec['strike']}"
            )


class TestDailyOptionCap:

    def test_0dte_time_decay_score_capped(self, scorer):
        """0DTE (days_to_expiry near 0) produces a low time_decay score."""
        stock = _stock_data(price=180.0)
        opts = _options_data(puts=[
            _put_option(strike=170.0, bid=1.0, ask=1.50, volume=200,
                        open_interest=500, dte=1),
        ])

        result = scorer.score_options(opts, stock)

        if result['recommendations']:
            rec = result['recommendations'][0]
            # _score_time_decay(1) = max(10, 70 - (10-1)*6) = max(10, 16) = 16
            td_score = rec['score_breakdown'].get('time_decay', 0)
            assert td_score <= 30, f"0DTE time_decay should be capped low, got {td_score}"


class TestScoreOptionsEdgeCases:

    def test_no_puts_returns_error(self, scorer):
        opts = {'success': True, 'symbol': 'AAPL', 'puts': []}
        stock = _stock_data()

        result = scorer.score_options(opts, stock)

        assert result['success'] is False

    def test_invalid_options_data(self, scorer):
        opts = {'success': False}
        stock = _stock_data()

        result = scorer.score_options(opts, stock)

        assert result['success'] is False

    def test_no_current_price(self, scorer):
        opts = _options_data()
        stock = {'current_price': 0}

        result = scorer.score_options(opts, stock)

        assert result['success'] is False

    def test_itm_put_filtered_out(self, scorer):
        """In-the-money put (strike > price * 1.02) is filtered."""
        stock = _stock_data(price=180.0)
        opts = _options_data(puts=[
            _put_option(strike=200.0, bid=22.0, ask=23.0, dte=30),
        ])

        result = scorer.score_options(opts, stock)

        assert result['success'] is True
        assert len(result['recommendations']) == 0

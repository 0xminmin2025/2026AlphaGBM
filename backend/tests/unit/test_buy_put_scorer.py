"""
Unit tests for BuyPutScorer.
Tests scoring logic, liquidity handling, score boundaries, and edge cases.
"""
import pytest
from unittest.mock import patch, MagicMock
import numpy as np


@pytest.fixture()
def scorer():
    """Return a BuyPutScorer instance."""
    try:
        from app.analysis.options_analysis.scoring.buy_put import BuyPutScorer
    except ImportError:
        pytest.skip("BuyPutScorer not importable")
    return BuyPutScorer()


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def _stock_data(price=180.0, change_pct=-1.5):
    return {
        'current_price': price,
        'change_percent': change_pct,
        'volatility_30d': 0.25,
        'price_history': [price + 2 - i * 0.3 for i in range(10)],
        'support_resistance': {
            'support_1': price * 0.95,
            'support_2': price * 0.90,
            'low_52w': price * 0.70,
            'high_52w': price * 1.20,
        },
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


def _put_option(strike=175.0, bid=3.00, ask=3.50, volume=500,
                open_interest=2000, iv=0.30, dte=30, delta=-0.40,
                expiry='2025-03-21'):
    return {
        'strike': strike,
        'bid': bid,
        'ask': ask,
        'volume': volume,
        'open_interest': open_interest,
        'implied_volatility': iv,
        'days_to_expiry': dte,
        'delta': delta,
        'expiry': expiry,
        'symbol': f'AAPL250321P{int(strike*1000):08d}',
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestScoreIdealBuyPut:

    def test_score_ideal_buy_put(self, scorer):
        """Good bearish momentum, reasonable IV, decent liquidity  -->  positive score."""
        stock = _stock_data(price=180.0, change_pct=-2.5)
        opts = _options_data(puts=[
            _put_option(strike=175.0, bid=3.0, ask=3.50, volume=800,
                        open_interest=5000, iv=0.25, dte=30, delta=-0.40),
        ])

        result = scorer.score_options(opts, stock)

        assert result['success'] is True
        assert result['strategy'] == 'buy_put'
        assert len(result['recommendations']) > 0
        top = result['recommendations'][0]
        assert top['score'] > 30
        assert top['strike'] == 175.0

    def test_score_returns_expected_fields(self, scorer):
        """Each recommendation has breakeven, max_loss, etc."""
        stock = _stock_data()
        opts = _options_data()

        result = scorer.score_options(opts, stock)

        if result['recommendations']:
            rec = result['recommendations'][0]
            assert 'breakeven' in rec
            assert 'max_loss' in rec
            assert 'profit_potential' in rec


class TestScoreZeroLiquidity:

    def test_score_zero_open_interest(self, scorer):
        """OI = 0, volume = 0  -->  low liquidity score component."""
        stock = _stock_data(price=180.0)
        opts = _options_data(puts=[
            _put_option(strike=175.0, bid=2.0, ask=2.50, volume=0,
                        open_interest=0, dte=30),
        ])

        result = scorer.score_options(opts, stock)

        assert result['success'] is True
        if result['recommendations']:
            rec = result['recommendations'][0]
            liq_score = rec['score_breakdown'].get('liquidity', 0)
            assert liq_score < 25

    def test_no_ask_returns_none(self, scorer):
        """ask=0 means the option is invalid; filtered out."""
        stock = _stock_data(price=180.0)
        opts = _options_data(puts=[
            _put_option(strike=175.0, bid=0, ask=0, volume=100,
                        open_interest=500, dte=30),
        ])

        result = scorer.score_options(opts, stock)
        assert result['success'] is True
        assert len(result['recommendations']) == 0


class TestScoreBoundary:

    def test_score_boundary_0_100(self, scorer):
        """Total score is always in [0, 100]."""
        stock = _stock_data(price=180.0)

        test_puts = [
            _put_option(strike=180, bid=5, ask=6, dte=30, volume=100, open_interest=200, delta=-0.50),
            _put_option(strike=170, bid=2, ask=2.5, dte=45, volume=1000, open_interest=5000, delta=-0.30),
            _put_option(strike=190, bid=12, ask=13, dte=7, volume=50, open_interest=100, delta=-0.70),
            _put_option(strike=160, bid=0.5, ask=0.8, dte=60, volume=2000, open_interest=10000, delta=-0.15),
        ]
        opts = _options_data(puts=test_puts)

        result = scorer.score_options(opts, stock)

        for rec in result.get('recommendations', []):
            assert 0 <= rec['score'] <= 100, (
                f"Score {rec['score']} out of [0,100] for strike={rec['strike']}"
            )


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

    def test_bearish_momentum_strong_decline(self, scorer):
        """change_percent <= -3  -->  momentum_score close to 100."""
        stock = _stock_data(price=180.0, change_pct=-4.0)
        opts = _options_data(puts=[
            _put_option(strike=175.0, bid=5.0, ask=5.50, dte=30, delta=-0.45),
        ])

        result = scorer.score_options(opts, stock)

        if result['recommendations']:
            rec = result['recommendations'][0]
            momentum = rec['score_breakdown'].get('bearish_momentum', 0)
            assert momentum >= 80, f"Expected high bearish momentum, got {momentum}"

    def test_bullish_market_reduces_momentum(self, scorer):
        """change_percent > 1  -->  low bearish momentum score."""
        stock = _stock_data(price=180.0, change_pct=2.0)
        opts = _options_data(puts=[
            _put_option(strike=175.0, bid=2.0, ask=2.50, dte=30, delta=-0.35),
        ])

        result = scorer.score_options(opts, stock)

        if result['recommendations']:
            rec = result['recommendations'][0]
            momentum = rec['score_breakdown'].get('bearish_momentum', 0)
            assert momentum < 50, f"Expected low bearish momentum for bullish day, got {momentum}"

    def test_multiple_puts_sorted_by_score(self, scorer):
        """Multiple puts are returned sorted by score descending."""
        stock = _stock_data(price=180.0, change_pct=-2.0)
        opts = _options_data(puts=[
            _put_option(strike=175, bid=3, ask=3.5, dte=30, volume=1000, open_interest=5000, delta=-0.40),
            _put_option(strike=170, bid=2, ask=2.5, dte=30, volume=500, open_interest=2000, delta=-0.30),
            _put_option(strike=180, bid=6, ask=6.5, dte=30, volume=800, open_interest=4000, delta=-0.50),
        ])

        result = scorer.score_options(opts, stock)

        if len(result['recommendations']) >= 2:
            scores = [r['score'] for r in result['recommendations']]
            assert scores == sorted(scores, reverse=True), "Recommendations should be sorted by score descending"

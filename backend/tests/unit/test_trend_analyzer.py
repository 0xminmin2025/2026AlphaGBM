"""
Unit tests for TrendAnalyzer.

Tests intraday trend detection (uptrend, downtrend, sideways) and
the trend-strategy alignment scoring system.
"""

import pytest
import numpy as np
import pandas as pd
from app.analysis.options_analysis.scoring.trend_analyzer import TrendAnalyzer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rising_prices(start=100.0, count=7, step=2.0):
    """Generate a series of steadily rising prices."""
    return pd.Series([start + i * step for i in range(count)])


def _falling_prices(start=100.0, count=7, step=2.0):
    """Generate a series of steadily falling prices."""
    return pd.Series([start - i * step for i in range(count)])


def _flat_prices(base=100.0, count=7, noise=0.05):
    """Generate a series of approximately flat prices with tiny noise."""
    return pd.Series([base + (i % 2) * noise for i in range(count)])


# ---------------------------------------------------------------------------
# Tests: determine_intraday_trend
# ---------------------------------------------------------------------------

class TestUptrendDetection:

    def test_uptrend_detection(self):
        """Steadily rising prices should be classified as 'uptrend'."""
        analyzer = TrendAnalyzer()
        # Prices: 100, 102, 104, 106, 108, 110, 112
        prices = _rising_prices(start=100.0, count=7, step=2.0)
        current_price = 115.0  # well above MA5 and previous close

        trend, strength = analyzer.determine_intraday_trend(prices, current_price)

        assert trend == 'uptrend'
        assert strength > 0.5

    def test_uptrend_alignment_score(self):
        """Sell_call in an uptrend should receive a high alignment score."""
        analyzer = TrendAnalyzer()

        score = analyzer.calculate_trend_alignment_score(
            strategy='sell_call',
            trend='uptrend',
            trend_strength=0.8
        )

        # Base score for sell_call + uptrend is 100; with strength 0.8: 100*(1+0.8*0.2)=116
        assert score >= 100


class TestDowntrendDetection:

    def test_downtrend_detection(self):
        """Steadily falling prices should be classified as 'downtrend'."""
        analyzer = TrendAnalyzer()
        # Prices: 100, 98, 96, 94, 92, 90, 88
        prices = _falling_prices(start=100.0, count=7, step=2.0)
        current_price = 85.0  # well below MA5 and previous close

        trend, strength = analyzer.determine_intraday_trend(prices, current_price)

        assert trend == 'downtrend'
        assert strength > 0.5

    def test_downtrend_alignment_score(self):
        """Sell_put in a downtrend should receive a high alignment score."""
        analyzer = TrendAnalyzer()

        score = analyzer.calculate_trend_alignment_score(
            strategy='sell_put',
            trend='downtrend',
            trend_strength=0.8
        )

        # Base score for sell_put + downtrend is 100
        assert score >= 100


class TestSideways:

    def test_sideways(self):
        """Flat/stable prices should be classified as 'sideways'."""
        analyzer = TrendAnalyzer()
        # Very flat prices with tiny noise
        prices = _flat_prices(base=100.0, count=7, noise=0.01)
        current_price = 100.02  # almost exactly at the mean

        trend, strength = analyzer.determine_intraday_trend(prices, current_price)

        assert trend == 'sideways'
        assert strength == 0.5

    def test_sideways_alignment_score(self):
        """Sell strategies in sideways markets should get a moderate score."""
        analyzer = TrendAnalyzer()

        score_sell_put = analyzer.calculate_trend_alignment_score(
            strategy='sell_put',
            trend='sideways',
            trend_strength=0.5
        )
        score_sell_call = analyzer.calculate_trend_alignment_score(
            strategy='sell_call',
            trend='sideways',
            trend_strength=0.5
        )

        # Base for sideways sell strategies is 60
        assert 30 <= score_sell_put <= 80
        assert 30 <= score_sell_call <= 80


# ---------------------------------------------------------------------------
# Tests: Edge cases
# ---------------------------------------------------------------------------

class TestTrendEdgeCases:

    def test_insufficient_data(self):
        """With fewer than 6 data points, trend should default to 'sideways'."""
        analyzer = TrendAnalyzer()
        short_prices = pd.Series([100.0, 101.0, 102.0])  # only 3 points
        current_price = 103.0

        trend, strength = analyzer.determine_intraday_trend(short_prices, current_price)

        assert trend == 'sideways'
        assert strength == 0.5

    def test_mismatched_trend_strategy_lowers_score(self):
        """A sell_call in a downtrend should get a much lower score
        than a sell_call in an uptrend."""
        analyzer = TrendAnalyzer()

        score_matching = analyzer.calculate_trend_alignment_score(
            strategy='sell_call', trend='uptrend', trend_strength=0.8
        )
        score_mismatch = analyzer.calculate_trend_alignment_score(
            strategy='sell_call', trend='downtrend', trend_strength=0.8
        )

        assert score_matching > score_mismatch
        # Matching should be >= 100 while mismatch should be well below
        assert score_mismatch < 50

    def test_trend_display_info(self):
        """get_trend_display_info should return a dict with trend metadata."""
        analyzer = TrendAnalyzer()

        info = analyzer.get_trend_display_info(
            trend='uptrend',
            trend_strength=0.8,
            strategy='sell_call'
        )

        assert isinstance(info, dict)
        # Should contain keys describing the trend to the user
        assert 'trend' in info or 'trend_name' in info or len(info) > 0

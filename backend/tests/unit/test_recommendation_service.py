"""
Unit tests for RecommendationService.

Tests symbol quality scoring, price trend detection, timing bonus,
strategy diversity enforcement, and daily recommendation caching.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, date, timedelta
import pandas as pd
import numpy as np


# ---------------------------------------------------------------------------
# Helpers to import the service without triggering heavy side-effects
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _patch_imports():
    """Patch DB model and DataProvider so the module can be imported
    without a running Flask app or database."""
    mock_db = MagicMock()
    mock_daily_rec = MagicMock()

    with patch.dict('sys.modules', {
        'app.models': MagicMock(db=mock_db, DailyRecommendation=mock_daily_rec),
    }):
        with patch('app.services.recommendation_service.DataProvider'):
            with patch('app.services.recommendation_service.OptionScorer'):
                with patch('app.services.recommendation_service.db', mock_db):
                    with patch('app.services.recommendation_service.DailyRecommendation', mock_daily_rec):
                        yield


def _make_service():
    """Create a fresh RecommendationService instance with mocked deps."""
    from app.services.recommendation_service import RecommendationService
    svc = RecommendationService()
    return svc


# ---------------------------------------------------------------------------
# Tests: get_symbol_quality_score
# ---------------------------------------------------------------------------

class TestGetSymbolQualityScore:

    def test_get_symbol_quality_score_tier1(self):
        """SPY should be tier 1 with a quality score between 85 and 95."""
        svc = _make_service()
        result = svc.get_symbol_quality_score('SPY')

        assert result['tier'] == 1
        assert 85 <= result['quality'] <= 95

    def test_get_symbol_quality_score_unknown(self):
        """An unknown/random ticker should default to tier 5."""
        svc = _make_service()
        result = svc.get_symbol_quality_score('ZZZZXYZ')

        assert result['tier'] == 5
        assert result['quality'] == 50
        assert result['description'] == '未评级标的'


# ---------------------------------------------------------------------------
# Tests: get_price_trend
# ---------------------------------------------------------------------------

class TestGetPriceTrend:

    def test_get_price_trend_up(self):
        """Rising prices (>3% gain) should yield trend='up'."""
        svc = _make_service()

        # Create a mock DataFrame with rising prices
        mock_hist = pd.DataFrame({
            'Close': [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0]
        })

        mock_ticker = MagicMock()
        mock_ticker.history.return_value = mock_hist

        with patch('app.services.recommendation_service.DataProvider', return_value=mock_ticker):
            result = svc.get_price_trend('AAPL', days=5)

        assert result['trend'] == 'up'
        assert result['change_pct'] > 3
        assert result['is_good_timing_for_put'] is False


# ---------------------------------------------------------------------------
# Tests: calculate_timing_bonus
# ---------------------------------------------------------------------------

class TestCalculateTimingBonus:

    def test_calculate_timing_bonus_sell_put_down(self):
        """Downtrend combined with sell_put strategy should produce a positive bonus."""
        svc = _make_service()
        trend = {'trend': 'down', 'change_pct': -5.0, 'is_good_timing_for_put': True}
        bonus = svc.calculate_timing_bonus(trend, 'sell_put')

        assert bonus > 0
        # With change_pct of -5, expected bonus = min(10, 5*2) = 10
        assert bonus == 10

    def test_timing_bonus_sell_call_up(self):
        """Uptrend combined with sell_call should produce a positive bonus."""
        svc = _make_service()
        trend = {'trend': 'up', 'change_pct': 4.0}
        bonus = svc.calculate_timing_bonus(trend, 'sell_call')

        assert bonus > 0
        assert bonus == min(10, 4.0 * 2)

    def test_timing_bonus_sideways_sell(self):
        """Sideways trend for sell strategies should give a small bonus of 3."""
        svc = _make_service()
        trend = {'trend': 'sideways', 'change_pct': 1.0}
        bonus = svc.calculate_timing_bonus(trend, 'sell_put')

        assert bonus == 3

    def test_timing_bonus_no_match(self):
        """When trend and strategy do not match, bonus should be 0."""
        svc = _make_service()
        trend = {'trend': 'up', 'change_pct': 5.0}
        bonus = svc.calculate_timing_bonus(trend, 'sell_put')

        assert bonus == 0


# ---------------------------------------------------------------------------
# Tests: _ensure_diversity
# ---------------------------------------------------------------------------

class TestEnsureDiversity:

    def test_ensure_diversity(self):
        """No more than 2 recommendations per strategy should be selected."""
        svc = _make_service()

        # Create 5 recommendations all with the same strategy
        recs = [
            {'strategy': 'sell_put', 'score': 90 - i, 'symbol': f'SYM{i}'}
            for i in range(5)
        ]
        # Add 2 of another strategy
        recs.extend([
            {'strategy': 'sell_call', 'score': 80, 'symbol': 'CALL1'},
            {'strategy': 'sell_call', 'score': 75, 'symbol': 'CALL2'},
            {'strategy': 'sell_call', 'score': 70, 'symbol': 'CALL3'},
        ])

        result = svc._ensure_diversity(recs, count=6)

        # Count per strategy
        strategy_counts = {}
        for r in result:
            s = r['strategy']
            strategy_counts[s] = strategy_counts.get(s, 0) + 1

        for strategy, cnt in strategy_counts.items():
            assert cnt <= 2, f"Strategy {strategy} has {cnt} recs, expected max 2"

        assert len(result) <= 6


# ---------------------------------------------------------------------------
# Tests: get_daily_recommendations (cached path)
# ---------------------------------------------------------------------------

class TestGetDailyRecommendationsCached:

    def test_get_daily_recommendations_cached(self):
        """When a cached recommendation exists for today, it should be returned."""
        svc = _make_service()

        # Build a mock cached record
        mock_cached = MagicMock()
        mock_cached.recommendations = [
            {'symbol': 'SPY', 'strategy': 'sell_put', 'score': 85},
            {'symbol': 'AAPL', 'strategy': 'sell_call', 'score': 78},
        ]
        mock_cached.market_summary = 'Test summary'
        mock_cached.updated_at = datetime(2026, 1, 15, 10, 0, 0)

        # Patch the DB query
        with patch('app.services.recommendation_service.DailyRecommendation') as MockDR:
            MockDR.query.filter_by.return_value.first.return_value = mock_cached
            result = svc.get_daily_recommendations(count=2, force_refresh=False)

        assert result['success'] is True
        assert result['from_cache'] is True
        assert len(result['recommendations']) == 2
        assert result['market_summary'] == 'Test summary'

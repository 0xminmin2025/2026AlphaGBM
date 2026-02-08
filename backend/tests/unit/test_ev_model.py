"""
Unit tests for EV (Expected Value) model service.

Tests calculate_ev_score, generate_extended_recommendation,
and calculate_ev_model_extended fallback behaviour.
"""

import pytest
from unittest.mock import patch, MagicMock
from app.services.ev_model import (
    calculate_ev_score,
    generate_extended_recommendation,
    calculate_ev_model_extended,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _make_risk_result(score=2, level='low', flags=None, suggested_position=50):
    return {
        'score': score,
        'level': level,
        'flags': flags or [],
        'suggested_position': suggested_position,
    }


def _make_market_data(**overrides):
    """Return minimal market data dict accepted by calculate_ev_model."""
    base = {
        'symbol': 'TEST',
        'name': 'Test Corp',
        'price': 100.0,
        'target_price': 120.0,
        'week52_high': 130.0,
        'week52_low': 80.0,
        'pe': 20.0,
        'peg': 1.2,
        'growth': 0.15,
        'margin': 0.12,
        'ma50': 98.0,
        'ma200': 95.0,
        'market_sentiment': 6.0,
        'history_prices': [95 + i * 0.1 for i in range(60)],
        'currency_symbol': '$',
    }
    base.update(overrides)
    return base


# ===================================================================
# test_calculate_ev_score_positive
# ===================================================================

class TestCalculateEvScorePositive:
    """Positive EV should produce a score above the midpoint (5.0)."""

    def test_positive_ev_high_score(self):
        ev_weighted = 0.10  # +10 %
        risk = _make_risk_result(score=1)
        score = calculate_ev_score(ev_weighted, risk)
        # 5.0 + 0.10*25 = 7.5, minus risk penalty 1*0.3 = 7.2
        assert score > 5.0, f"Expected score > 5.0, got {score}"

    def test_large_positive_ev(self):
        ev_weighted = 0.20  # +20 %
        risk = _make_risk_result(score=0)
        score = calculate_ev_score(ev_weighted, risk)
        assert score == 10.0


# ===================================================================
# test_calculate_ev_score_negative
# ===================================================================

class TestCalculateEvScoreNegative:
    """Negative EV should produce a score below the midpoint (5.0)."""

    def test_negative_ev_low_score(self):
        ev_weighted = -0.10  # -10 %
        risk = _make_risk_result(score=1)
        score = calculate_ev_score(ev_weighted, risk)
        # 5.0 + (-0.10)*25 = 2.5, minus 0.3 = 2.2
        assert score < 5.0, f"Expected score < 5.0, got {score}"

    def test_very_negative_ev(self):
        ev_weighted = -0.20
        risk = _make_risk_result(score=2)
        score = calculate_ev_score(ev_weighted, risk)
        assert score == 0.0


# ===================================================================
# test_recommendation_strong_buy
# ===================================================================

class TestRecommendationStrongBuy:
    """EV > 10% should yield STRONG_BUY from the extended recommendation."""

    def test_strong_buy_when_ev_above_10pct(self):
        rec = generate_extended_recommendation(
            ev_extended=0.12,
            ev_base=0.08,
            sector_analysis=None,
            capital_analysis=None,
            base_recommendation={'action': 'BUY'},
        )
        assert rec['action'] == 'STRONG_BUY'
        assert rec['confidence'] == 'high'


# ===================================================================
# test_recommendation_avoid
# ===================================================================

class TestRecommendationAvoid:
    """EV < -3% (and > -8%) should yield AVOID."""

    def test_avoid_when_ev_below_neg3pct(self):
        rec = generate_extended_recommendation(
            ev_extended=-0.05,
            ev_base=-0.02,
            sector_analysis=None,
            capital_analysis=None,
            base_recommendation={'action': 'HOLD'},
        )
        assert rec['action'] == 'AVOID'

    def test_strong_avoid_when_ev_very_negative(self):
        rec = generate_extended_recommendation(
            ev_extended=-0.10,
            ev_base=-0.06,
            sector_analysis=None,
            capital_analysis=None,
            base_recommendation={'action': 'HOLD'},
        )
        assert rec['action'] == 'STRONG_AVOID'


# ===================================================================
# test_extended_ev_with_sector
# ===================================================================

class TestExtendedEvWithSector:
    """When sector_analysis is provided, sector_rotation_premium is added."""

    @patch('app.services.ev_model.calculate_ev_model')
    @patch('app.services.ev_model.calculate_ev_score')
    @patch('app.services.ev_model.generate_extended_recommendation')
    def test_sector_premium_added(self, mock_rec, mock_score, mock_base):
        mock_base.return_value = {
            'ev_weighted': 0.05,
            'ev_weighted_pct': 5.0,
            'recommendation': {'action': 'BUY'},
        }
        mock_score.return_value = 7.0
        mock_rec.return_value = {
            'action': 'STRONG_BUY',
            'reason': 'test',
            'confidence': 'high',
        }

        data = _make_market_data()
        risk = _make_risk_result()
        sector = {
            'sector_rotation_premium': 0.03,
            'sector': 'Technology',
            'sector_zh': '',
            'sector_strength': 80,
            'alignment_score': 75,
            'is_sector_leader': True,
            'sector_trend': 'bullish',
        }

        result = calculate_ev_model_extended(data, risk, 'growth', sector_analysis=sector)

        assert result['sector_rotation_premium'] == 0.03
        # ev_extended = ev_base (0.05) + sector_premium (0.03) + capital (0)
        assert abs(result['ev_extended'] - 0.08) < 1e-9
        assert result['model_version'] == 'extended_v1'


# ===================================================================
# test_extended_ev_fallback
# ===================================================================

class TestExtendedEvFallback:
    """When sector_analysis causes an error, the code falls back to base EV."""

    @patch('app.services.ev_model.calculate_ev_model')
    def test_fallback_on_sector_error(self, mock_base):
        """If the extended path raises, we should get base_v1_fallback."""
        mock_base.return_value = {
            'ev_weighted': 0.04,
            'ev_weighted_pct': 4.0,
            'recommendation': {'action': 'BUY'},
        }

        data = _make_market_data()
        risk = _make_risk_result()

        # Provide a sector_analysis whose get() call raises an exception
        bad_sector = MagicMock()
        bad_sector.get.side_effect = TypeError("boom")

        result = calculate_ev_model_extended(data, risk, 'growth', sector_analysis=bad_sector)

        assert result['model_version'] == 'base_v1_fallback'
        assert result['sector_rotation_premium'] == 0.0
        assert result['capital_structure_factor'] == 0.0

"""
Unit tests for the AI service (fallback analysis and recommendation logic).

Tests get_fallback_analysis and _compute_alphagbm_recommendation from
app.services.ai_service.
"""

import pytest
from unittest.mock import patch


# Patch the genai import and analysis_engine import before importing the module
with patch.dict('os.environ', {'GOOGLE_API_KEY': ''}):
    with patch('app.services.ai_service.genai', None):
        pass

from app.services.ai_service import get_fallback_analysis, _compute_alphagbm_recommendation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_data(**overrides):
    """Minimal market data dict for get_fallback_analysis."""
    base = {
        'name': 'Apple Inc',
        'price': 180.0,
        'target_price': 210.0,
        'week52_high': 220.0,
        'week52_low': 140.0,
        'pe': 28.0,
        'peg': 1.5,
        'growth': 0.12,
        'margin': 0.25,
        'ma50': 175.0,
        'ma200': 165.0,
        'currency_symbol': '$',
        'stop_loss_price': 153.0,
        'stop_loss_method': 'ATR',
    }
    base.update(overrides)
    return base


def _make_risk(score=3, level='medium', flags=None, suggested_position=40):
    return {
        'score': score,
        'level': level,
        'flags': flags or ['Moderate volatility'],
        'suggested_position': suggested_position,
    }


# ===================================================================
# test_get_fallback_analysis
# ===================================================================

class TestGetFallbackAnalysis:
    """get_fallback_analysis returns a markdown string."""

    def test_returns_string(self):
        data = _make_data()
        risk = _make_risk()
        result = get_fallback_analysis('AAPL', 'quality', data, risk)
        assert isinstance(result, str)
        assert len(result) > 100

    def test_contains_ticker(self):
        data = _make_data()
        risk = _make_risk()
        result = get_fallback_analysis('AAPL', 'quality', data, risk)
        assert 'AAPL' in result

    def test_contains_company_name(self):
        data = _make_data()
        risk = _make_risk()
        result = get_fallback_analysis('AAPL', 'quality', data, risk)
        assert 'Apple Inc' in result


# ===================================================================
# test_fallback_contains_sections
# ===================================================================

class TestFallbackContainsSections:
    """The fallback analysis should contain all 7 major sections."""

    EXPECTED_SECTIONS = [
        'ALPHAGBM',
        'AlphaG',
        'G (收益',
        'B (基本面',
        'M (动量',
        '风险控制',
        '交易策略',
    ]

    def test_all_sections_present(self):
        data = _make_data()
        risk = _make_risk()
        result = get_fallback_analysis('AAPL', 'quality', data, risk)

        missing = [s for s in self.EXPECTED_SECTIONS if s not in result]
        assert not missing, f"Missing sections: {missing}"


# ===================================================================
# test_compute_recommendation_bullish
# ===================================================================

class TestComputeRecommendationBullish:
    """Positive data with large upside should produce a buy-type recommendation."""

    def test_buy_recommendation(self):
        data = _make_data(
            price=100.0,
            target_price=130.0,  # 30% upside
            ma50=98.0,
            ma200=90.0,
            ev_model={'recommendation': {'action': 'BUY', 'reason': 'EV positive'}},
        )
        risk = _make_risk(score=2, suggested_position=50)

        rec = _compute_alphagbm_recommendation(data, risk, 'growth')

        assert rec['action'] in ('买入', '分批建仓')
        assert rec['upside_pct'] > 10
        assert rec['position_pct'] == 50

    def test_trend_direction_bullish(self):
        data = _make_data(
            price=100.0,
            target_price=125.0,
            ma50=98.0,
            ma200=90.0,
            ev_model={},
        )
        risk = _make_risk(score=1, suggested_position=60)

        rec = _compute_alphagbm_recommendation(data, risk, 'momentum')
        assert rec['trend_direction'] == '上涨趋势'


# ===================================================================
# test_compute_recommendation_bearish
# ===================================================================

class TestComputeRecommendationBearish:
    """Negative data (zero position, high risk) should produce hold/sell."""

    def test_hold_when_position_zero(self):
        data = _make_data(
            price=100.0,
            target_price=110.0,
            ev_model={},
        )
        risk = _make_risk(score=8, suggested_position=0)

        rec = _compute_alphagbm_recommendation(data, risk, 'value')

        assert rec['action'] == '观望'
        assert rec['position_pct'] == 0
        assert rec['upside_pct'] == 0

    def test_sell_when_price_far_above_target(self):
        data = _make_data(
            price=200.0,
            target_price=140.0,  # price far above target -> sell
            ma50=195.0,
            ma200=180.0,
            ev_model={},
        )
        risk = _make_risk(score=2, suggested_position=40)

        rec = _compute_alphagbm_recommendation(data, risk, 'value')
        assert rec['action'] in ('减仓', '卖出')

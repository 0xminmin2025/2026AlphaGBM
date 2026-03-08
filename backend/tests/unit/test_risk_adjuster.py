"""
Unit tests for RiskAdjuster.

Tests risk score adjustment, portfolio risk analysis, position sizing,
and tail-risk / extreme scenario handling.
"""

import pytest
from app.analysis.options_analysis.advanced.risk_adjuster import RiskAdjuster


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_strategy_analysis(strategies=None):
    """Build a minimal strategy_analysis dict."""
    if strategies is None:
        strategies = {
            'sell_put': {
                'success': True,
                'recommendations': [
                    {'strike': 95, 'premium': 2.0, 'expiry': '2026-03-21',
                     'impliedVolatility': 0.25, 'openInterest': 500}
                ]
            }
        }
    return strategies


def _make_stock_data(volatility_30d=0.20, change_percent=0):
    """Build a minimal stock_data dict."""
    return {
        'volatility_30d': volatility_30d,
        'change_percent': change_percent,
    }


# ---------------------------------------------------------------------------
# Tests: Risk score adjustment
# ---------------------------------------------------------------------------

class TestAdjustScore:

    def test_adjust_score(self):
        """analyze_portfolio_risk should return a combined risk score
        that modifies the base score using market and option-specific risk."""
        adjuster = RiskAdjuster()

        strategy_analysis = _make_strategy_analysis()
        stock_data = _make_stock_data(volatility_30d=0.20, change_percent=1.0)

        result = adjuster.analyze_portfolio_risk(strategy_analysis, stock_data)

        assert result['success'] is True
        assert 'strategy_risks' in result
        assert 'portfolio_risk' in result
        assert 'risk_assessment' in result

        # Each strategy should have a combined risk score
        for strategy, risk in result['strategy_risks'].items():
            assert 'combined_risk_score' in risk
            score = risk['combined_risk_score']
            assert 0 <= score <= 100

    def test_combine_risk_scores(self):
        """_combine_risk_scores should apply the weighted formula:
        40% base + 40% market + 20% option."""
        adjuster = RiskAdjuster()

        combined = adjuster._combine_risk_scores(60, 50, 70)
        expected = 60 * 0.4 + 50 * 0.4 + 70 * 0.2  # 24 + 20 + 14 = 58
        assert abs(combined - expected) < 0.01

    def test_position_sizing_moderate(self):
        """Position sizing with moderate risk tolerance should produce
        reasonable capital allocation."""
        adjuster = RiskAdjuster()

        strategy_analysis = _make_strategy_analysis()
        result = adjuster.calculate_position_sizing(
            strategy_analysis,
            portfolio_value=100000.0,
            risk_tolerance='moderate'
        )

        assert result['success'] is True
        assert result['risk_tolerance'] == 'moderate'
        assert result['portfolio_value'] == 100000.0

    def test_invalid_risk_tolerance_defaults(self):
        """An invalid risk_tolerance string should fall back to 'moderate'."""
        adjuster = RiskAdjuster()

        strategy_analysis = _make_strategy_analysis()
        result = adjuster.calculate_position_sizing(
            strategy_analysis,
            portfolio_value=50000.0,
            risk_tolerance='yolo'  # not a valid tier
        )

        assert result['success'] is True
        assert result['risk_tolerance'] == 'moderate'


# ---------------------------------------------------------------------------
# Tests: Tail risk / extreme scenarios
# ---------------------------------------------------------------------------

class TestTailRisk:

    def test_tail_risk_high_volatility(self):
        """In an extreme high-volatility scenario, the risk score should
        be elevated compared to normal conditions."""
        adjuster = RiskAdjuster()

        strategy_analysis = _make_strategy_analysis()
        stock_data_normal = _make_stock_data(volatility_30d=0.15, change_percent=0.5)
        stock_data_extreme = _make_stock_data(volatility_30d=0.80, change_percent=15.0)

        result_normal = adjuster.analyze_portfolio_risk(strategy_analysis, stock_data_normal)
        result_extreme = adjuster.analyze_portfolio_risk(strategy_analysis, stock_data_extreme)

        assert result_normal['success'] is True
        assert result_extreme['success'] is True

        # Extract combined risk scores for the sell_put strategy
        normal_risk = result_normal['strategy_risks']['sell_put']['combined_risk_score']
        extreme_risk = result_extreme['strategy_risks']['sell_put']['combined_risk_score']

        # Extreme scenario should produce a higher risk score
        assert extreme_risk > normal_risk

    def test_empty_strategy_analysis(self):
        """Passing an empty strategy_analysis dict should return success=False
        with a descriptive error, since there are no strategies to analyze."""
        adjuster = RiskAdjuster()

        result = adjuster.analyze_portfolio_risk({}, _make_stock_data())

        assert result['success'] is False
        assert 'error' in result

    def test_no_strategy_analysis_returns_failure(self):
        """Passing None should return success=False."""
        adjuster = RiskAdjuster()

        result = adjuster.analyze_portfolio_risk(None, _make_stock_data())

        assert result['success'] is False
        assert 'error' in result

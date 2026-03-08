"""
Unit tests for OptionsAnalysisEngine.
All external dependencies (data fetcher, scorers, VRP, risk adjuster) are mocked.
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime


@pytest.fixture()
def engine():
    """Return an OptionsAnalysisEngine with every dependency mocked."""
    with patch(
        'app.analysis.options_analysis.core.engine.OptionsDataFetcher'
    ) as MockFetcher, patch(
        'app.analysis.options_analysis.core.engine.SellPutScorer'
    ), patch(
        'app.analysis.options_analysis.core.engine.SellCallScorer'
    ), patch(
        'app.analysis.options_analysis.core.engine.BuyPutScorer'
    ), patch(
        'app.analysis.options_analysis.core.engine.BuyCallScorer'
    ), patch(
        'app.analysis.options_analysis.core.engine.VRPCalculator'
    ), patch(
        'app.analysis.options_analysis.core.engine.RiskAdjuster'
    ), patch(
        'app.analysis.options_analysis.core.engine.add_profiles_to_options',
        side_effect=lambda recs, *a, **kw: recs,
    ):
        from app.analysis.options_analysis.core.engine import OptionsAnalysisEngine

        eng = OptionsAnalysisEngine()

        # Pre-wire successful scorer responses
        for name, scorer in eng.scorers.items():
            scorer.score_options.return_value = {
                'success': True,
                'strategy': name,
                'recommendations': [
                    {
                        'strike': 180,
                        'expiry': '2025-03-21',
                        'score': 82,
                        'risk_return_profile': {
                            'style': 'balanced',
                            'style_label': 'Balanced',
                            'risk_level': 'medium',
                            'risk_color': 'yellow',
                            'win_probability': 0.72,
                            'max_profit_pct': 3.5,
                            'max_loss_pct': 10.0,
                            'summary_cn': 'test summary',
                        },
                    }
                ],
                'trend_info': {'trend': 'up'},
            }

        # VRP
        eng.vrp_calculator.calculate.return_value = {
            'level': 'normal',
            'vrp_value': 0.05,
        }

        # Risk adjuster
        eng.risk_adjuster.analyze_portfolio_risk.return_value = {
            'overall_risk': 'medium',
        }

        # Data fetcher
        eng.data_fetcher.get_options_chain.return_value = {
            'success': True,
            'symbol': 'AAPL',
            'puts': [{'strike': 170}],
            'calls': [{'strike': 190}],
        }
        eng.data_fetcher.get_underlying_stock_data.return_value = {
            'current_price': 185.0,
            'change_percent': 0.5,
        }

        yield eng


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestAnalyzeOptionsChainSuccess:

    def test_analyze_options_chain_success(self, engine):
        """Successful chain analysis returns expected structure."""
        result = engine.analyze_options_chain('AAPL')

        assert result['success'] is True
        assert result['symbol'] == 'AAPL'
        assert 'strategy_analysis' in result
        assert 'vrp_analysis' in result
        assert 'risk_analysis' in result
        assert 'summary' in result

    def test_returns_error_when_data_fetch_fails(self, engine):
        engine.data_fetcher.get_options_chain.return_value = {
            'success': False,
            'error': 'API timeout',
        }

        result = engine.analyze_options_chain('AAPL')

        assert result['success'] is False
        assert 'error' in result


class TestAnalyzeAllStrategies:

    def test_analyze_all_strategies(self, engine):
        """strategy='all' scores all four strategy types."""
        result = engine.analyze_options_chain('AAPL', strategy='all')

        assert result['success'] is True
        analysis = result['strategy_analysis']
        assert set(analysis.keys()) == {'sell_put', 'sell_call', 'buy_put', 'buy_call'}

    def test_analyze_single_strategy(self, engine):
        """Specifying a single strategy only runs that scorer."""
        result = engine.analyze_options_chain('AAPL', strategy='sell_put')

        assert result['success'] is True
        assert 'sell_put' in result['strategy_analysis']
        assert 'sell_call' not in result['strategy_analysis']

    def test_unsupported_strategy_returns_error(self, engine):
        result = engine.analyze_options_chain('AAPL', strategy='iron_condor')

        assert result['success'] is False
        assert 'error' in result


class TestGroupByStyle:

    def test_group_by_style(self, engine):
        """_group_by_style organises recommendations into style buckets."""
        strategy_analysis = {}
        for name in ('sell_put', 'sell_call', 'buy_put', 'buy_call'):
            strategy_analysis[name] = {
                'success': True,
                'recommendations': [
                    {
                        'strike': 180,
                        'expiry': '2025-03-21',
                        'score': 80,
                        'risk_return_profile': {
                            'style': 'steady_income',
                            'style_label': 'Steady Income',
                            'risk_level': 'low',
                            'risk_color': 'green',
                            'win_probability': 0.85,
                            'max_profit_pct': 2.0,
                            'max_loss_pct': 5.0,
                            'summary_cn': 'stable',
                        },
                    },
                    {
                        'strike': 200,
                        'expiry': '2025-04-18',
                        'score': 70,
                        'risk_return_profile': {
                            'style': 'high_risk_high_reward',
                            'style_label': 'High Risk',
                            'risk_level': 'high',
                            'risk_color': 'red',
                            'win_probability': 0.40,
                            'max_profit_pct': 20.0,
                            'max_loss_pct': 50.0,
                            'summary_cn': 'aggressive',
                        },
                    },
                ],
            }

        grouped = engine._group_by_style(strategy_analysis)

        assert 'steady_income' in grouped
        assert 'high_risk_high_reward' in grouped
        assert 'balanced' in grouped
        assert 'hedge' in grouped
        # At least some entries in steady_income
        assert len(grouped['steady_income']) > 0


class TestOverallRecommendation:

    def test_overall_recommendation_strong_buy(self, engine):
        """Score > 85 with low/medium risk  -->  strong_buy."""
        best_strategies = [
            {'strategy': 'sell_put', 'score': 90, 'option': {}},
        ]
        vrp = {'level': 'normal'}
        risk = {'overall_risk': 'low'}

        rec = engine._get_overall_recommendation(best_strategies, vrp, risk)

        assert rec['action'] == 'strong_buy'
        assert rec['confidence'] == 'high'

    def test_overall_recommendation_buy(self, engine):
        """Score > 70 with normal VRP  -->  buy."""
        best_strategies = [
            {'strategy': 'sell_call', 'score': 75, 'option': {}},
        ]
        vrp = {'level': 'normal'}
        risk = {'overall_risk': 'medium'}

        rec = engine._get_overall_recommendation(best_strategies, vrp, risk)

        assert rec['action'] == 'buy'

    def test_overall_recommendation_wait(self, engine):
        """No best strategies  -->  wait."""
        rec = engine._get_overall_recommendation([], {}, {})

        assert rec['action'] == 'wait'
        assert rec['confidence'] == 'low'

    def test_overall_recommendation_cautious(self, engine):
        """Moderate score with high VRP  -->  cautious."""
        best_strategies = [
            {'strategy': 'buy_call', 'score': 72, 'option': {}},
        ]
        vrp = {'level': 'high'}
        risk = {'overall_risk': 'high'}

        rec = engine._get_overall_recommendation(best_strategies, vrp, risk)

        assert rec['action'] == 'cautious'

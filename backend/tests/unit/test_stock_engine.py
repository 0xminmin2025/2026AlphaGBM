"""
Unit tests for StockAnalysisEngine.
Tests the main orchestrator with mocked sub-components.
"""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock


# ---------------------------------------------------------------------------
# Module-level patches so we never touch real imports of data_fetcher, etc.
# ---------------------------------------------------------------------------

@pytest.fixture()
def engine():
    """Return a StockAnalysisEngine with every dependency mocked out."""
    with patch(
        'app.analysis.stock_analysis.core.engine.StockDataFetcher'
    ) as MockFetcher, patch(
        'app.analysis.stock_analysis.core.engine.StockCalculator'
    ) as MockCalc, patch(
        'app.analysis.stock_analysis.core.engine.BasicAnalysisStrategy'
    ) as MockStrategy:
        from app.analysis.stock_analysis.core.engine import StockAnalysisEngine

        eng = StockAnalysisEngine()
        # Expose the mock instances for per-test configuration
        eng._mock_fetcher = eng.data_fetcher
        eng._mock_calculator = eng.calculator
        eng._mock_strategy = eng.basic_strategy
        yield eng


# ---------------------------------------------------------------------------
# Helper data factories
# ---------------------------------------------------------------------------

def _market_data(ticker='AAPL'):
    """Minimal valid market data dict."""
    return {
        'ticker': ticker,
        'info': {
            'regularMarketPrice': 180.0,
            'marketCap': 2_800_000_000_000,
            'sector': 'Technology',
        },
        'history_prices': [170 + i * 0.5 for i in range(30)],
        'history_volumes': [50_000_000] * 30,
    }


def _liquidity_info(is_liquid=True):
    return {
        'daily_volume_usd': 9_000_000_000,
        'avg_daily_volume_usd': 9_000_000_000,
        'min_requirement': 5_000_000,
    }


def _analysis_result():
    return {
        'success': True,
        'analysis_style': 'growth',
        'company_classification': {'cap_category': 'mega_cap'},
        'risk_analysis': {'risk_level': 'low'},
        'recommendation': {'action': 'buy'},
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestAnalyzeStockSuccess:
    """analyze_stock with valid data returns a successful analysis dict."""

    def test_analyze_stock_success(self, engine):
        md = _market_data()
        engine._mock_fetcher.get_market_data.return_value = md
        engine._mock_calculator.check_liquidity.return_value = (True, _liquidity_info())
        engine._mock_strategy.analyze.return_value = _analysis_result()

        result = engine.analyze_stock('AAPL', style='growth')

        assert result['success'] is True
        assert result['ticker'] == 'AAPL'
        assert result['analysis_style'] == 'growth'
        assert 'liquidity_analysis' in result
        assert result['liquidity_analysis']['is_liquid'] is True
        engine._mock_fetcher.get_market_data.assert_called_once()


class TestAnalyzeStockInvalidTicker:
    """analyze_stock handles bad / missing data gracefully."""

    def test_returns_error_when_market_data_is_none(self, engine):
        engine._mock_fetcher.get_market_data.return_value = None

        result = engine.analyze_stock('INVALID')

        assert result['success'] is False
        assert 'error' in result

    def test_returns_error_when_market_data_has_error_key(self, engine):
        engine._mock_fetcher.get_market_data.return_value = {'error': 'not found'}

        result = engine.analyze_stock('ZZZZ')

        assert result['success'] is False

    def test_returns_error_on_exception(self, engine):
        engine._mock_fetcher.get_market_data.side_effect = RuntimeError('boom')

        result = engine.analyze_stock('BOOM')

        assert result['success'] is False
        assert 'ticker' in result


class TestGetQuickQuote:
    """get_quick_quote delegates to data_fetcher.get_ticker_price."""

    def test_get_quick_quote(self, engine):
        expected = {
            'success': True,
            'price': 182.50,
            'change': 1.25,
            'change_percent': 0.69,
        }
        engine._mock_fetcher.get_ticker_price.return_value = expected

        result = engine.get_quick_quote('AAPL')

        assert result['price'] == 182.50
        engine._mock_fetcher.get_ticker_price.assert_called_once_with('AAPL')

    def test_get_quick_quote_error(self, engine):
        engine._mock_fetcher.get_ticker_price.side_effect = RuntimeError('timeout')

        result = engine.get_quick_quote('AAPL')

        assert result['success'] is False
        assert 'error' in result


class TestCheckStockLiquidity:
    """check_stock_liquidity returns (bool, dict)."""

    def test_check_stock_liquidity_pass(self, engine):
        md = _market_data()
        engine._mock_fetcher.get_market_data.return_value = md
        engine._mock_calculator.check_liquidity.return_value = (True, _liquidity_info(True))

        is_liquid, info = engine.check_stock_liquidity('AAPL')

        assert is_liquid is True
        assert info['avg_daily_volume_usd'] >= 5_000_000

    def test_check_stock_liquidity_fail(self, engine):
        md = _market_data()
        engine._mock_fetcher.get_market_data.return_value = md
        low_liq = {
            'daily_volume_usd': 100_000,
            'avg_daily_volume_usd': 100_000,
            'min_requirement': 5_000_000,
        }
        engine._mock_calculator.check_liquidity.return_value = (False, low_liq)

        is_liquid, info = engine.check_stock_liquidity('PENNY')

        assert is_liquid is False
        assert info['avg_daily_volume_usd'] < info['min_requirement']

    def test_check_stock_liquidity_no_data(self, engine):
        engine._mock_fetcher.get_market_data.return_value = None

        is_liquid, info = engine.check_stock_liquidity('NODATA')

        assert is_liquid is False
        assert 'error' in info

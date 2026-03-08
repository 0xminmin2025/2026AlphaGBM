"""
Unit tests for BasicAnalysisStrategy.
Tests company classification, growth/value detection, and risk analysis.
"""
import pytest
import numpy as np
from unittest.mock import patch, MagicMock


@pytest.fixture()
def strategy():
    """Return a BasicAnalysisStrategy instance."""
    try:
        from app.analysis.stock_analysis.strategies.basic import BasicAnalysisStrategy
    except ImportError:
        pytest.skip("BasicAnalysisStrategy not importable")
    return BasicAnalysisStrategy()


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def _make_data(market_cap=10_000_000_000, pe=20, revenue_growth=0.12,
               sector='Technology', industry='Software', quote_type='EQUITY',
               short_name='Test Corp', history_len=60, price=150.0,
               debt_to_equity=50, beta=1.0):
    """Build a market-data dict suitable for BasicAnalysisStrategy."""
    prices = [price + np.sin(i / 5) * 2 for i in range(history_len)]
    return {
        'ticker': 'TEST',
        'info': {
            'marketCap': market_cap,
            'trailingPE': pe,
            'revenueGrowth': revenue_growth,
            'sector': sector,
            'industry': industry,
            'quoteType': quote_type,
            'shortName': short_name,
            'longName': short_name,
            'debtToEquity': debt_to_equity,
            'regularMarketPrice': price,
            'currentPrice': price,
            'beta': beta,
            'pegRatio': pe / max(revenue_growth * 100, 1) if revenue_growth else 0,
            'earningsGrowth': revenue_growth * 0.8,
        },
        'history_prices': prices,
        'history_volumes': [500_000] * history_len,
    }


# ---------------------------------------------------------------------------
# Company classification – market cap
# ---------------------------------------------------------------------------

class TestClassifyCompanyMarketCap:

    def test_classify_company_mega_cap(self, strategy):
        """market_cap >= 200B  -->  mega_cap."""
        data = _make_data(market_cap=250_000_000_000)
        result = strategy.classify_company(data)

        assert result['cap_category'] == 'mega_cap'

    def test_classify_company_large_cap(self, strategy):
        """10B <= market_cap < 200B  -->  large_cap."""
        data = _make_data(market_cap=50_000_000_000)
        result = strategy.classify_company(data)

        assert result['cap_category'] == 'large_cap'

    def test_classify_company_mid_cap(self, strategy):
        """2B <= market_cap < 10B  -->  mid_cap."""
        data = _make_data(market_cap=5_000_000_000)
        result = strategy.classify_company(data)

        assert result['cap_category'] == 'mid_cap'

    def test_classify_company_small_cap(self, strategy):
        """300M <= market_cap < 2B  -->  small_cap."""
        data = _make_data(market_cap=1_000_000_000)
        result = strategy.classify_company(data)

        assert result['cap_category'] == 'small_cap'

    def test_classify_company_micro_cap(self, strategy):
        """market_cap < 300M  -->  micro_cap."""
        data = _make_data(market_cap=100_000_000)
        result = strategy.classify_company(data)

        assert result['cap_category'] == 'micro_cap'


# ---------------------------------------------------------------------------
# Company classification – growth vs value
# ---------------------------------------------------------------------------

class TestClassifyGrowthValue:

    def test_classify_growth(self, strategy):
        """PE > 25 and revenueGrowth > 15%  -->  growth."""
        data = _make_data(pe=30, revenue_growth=0.20)
        result = strategy.classify_company(data)

        assert result['growth_vs_value'] == 'growth'

    def test_classify_value(self, strategy):
        """PE < 15 and revenueGrowth < 10%  -->  value."""
        data = _make_data(pe=12, revenue_growth=0.05)
        result = strategy.classify_company(data)

        assert result['growth_vs_value'] == 'value'

    def test_classify_blend(self, strategy):
        """PE and growth in between  -->  blend."""
        data = _make_data(pe=20, revenue_growth=0.12)
        result = strategy.classify_company(data)

        assert result['growth_vs_value'] == 'blend'


# ---------------------------------------------------------------------------
# analyze() returns a valid structure
# ---------------------------------------------------------------------------

class TestAnalyzeReturnsDict:

    def test_analyze_returns_dict(self, strategy):
        """analyze() with valid data returns a dict with expected keys."""
        data = _make_data()
        liquidity_info = {'avg_daily_volume_usd': 50_000_000}

        result = strategy.analyze(data=data, style='growth', liquidity_info=liquidity_info)

        assert isinstance(result, dict)
        assert result.get('success') is True
        assert 'company_classification' in result
        assert 'risk_analysis' in result
        assert 'recommendation' in result

    def test_analyze_missing_info_key(self, strategy):
        """analyze() without 'info' key returns error."""
        result = strategy.analyze(data={'ticker': 'X'}, style='growth', liquidity_info={})

        assert result.get('success') is False

    def test_analyze_all_styles(self, strategy):
        """analyze() works for every supported style."""
        data = _make_data()
        liq = {'avg_daily_volume_usd': 50_000_000}

        for style in ('growth', 'value', 'balanced', 'quality', 'momentum'):
            result = strategy.analyze(data=data, style=style, liquidity_info=liq)
            assert result.get('success') is True, f"Failed for style={style}"


# ---------------------------------------------------------------------------
# Risk and position analysis
# ---------------------------------------------------------------------------

class TestAnalyzeRiskAndPosition:

    def test_returns_risk_dict(self, strategy):
        """analyze_risk_and_position returns dict with expected keys."""
        data = _make_data()
        result = strategy.analyze_risk_and_position(style='growth', data=data)

        assert 'risk_score' in result
        assert 'risk_level' in result
        assert result['risk_level'] in ('low', 'medium', 'high')
        assert 'position_size_pct' in result

    def test_low_risk_for_stable_stock(self, strategy):
        """Large-cap, low-debt, low-vol should be low/medium risk."""
        data = _make_data(
            market_cap=500_000_000_000,
            debt_to_equity=30,
            sector='Consumer Defensive',
            history_len=60,
        )
        result = strategy.analyze_risk_and_position(style='value', data=data)

        assert result['risk_level'] in ('low', 'medium')

    def test_high_risk_for_volatile_small_cap(self, strategy):
        """Small-cap, high-debt, high-vol sector should be medium/high risk."""
        # Build high-volatility price history
        prices = [50 + ((-1)**i) * 5 for i in range(60)]
        data = _make_data(
            market_cap=500_000_000,
            debt_to_equity=250,
            sector='Technology',
        )
        data['history_prices'] = prices

        result = strategy.analyze_risk_and_position(style='growth', data=data)

        assert result['risk_level'] in ('medium', 'high')

    def test_missing_data_returns_valid_risk(self, strategy):
        """Minimal data returns a valid risk result without crashing."""
        result = strategy.analyze_risk_and_position(style='growth', data={})

        assert result['risk_level'] in ('low', 'medium', 'high')
        assert 'risk_score' in result

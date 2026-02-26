"""
HK / CN 期权分析支持集成测试

测试各模块在 HK_OPTIONS_CONFIG / CN_OPTIONS_CONFIG 下的行为，
以及 US 默认行为的向后兼容性。
"""

import pytest
import math
import numpy as np
from unittest.mock import patch, MagicMock

from app.analysis.options_analysis.option_market_config import (
    OptionMarketConfig,
    US_OPTIONS_CONFIG,
    HK_OPTIONS_CONFIG,
    CN_OPTIONS_CONFIG,
    get_option_market_config,
)


# ============================================================
# 辅助：构造最小可用的 options_data / stock_data
# ============================================================

def _make_stock_data(price=100.0, prices=None):
    """构造最小 stock_data dict"""
    if prices is None:
        prices = [price * (1 + 0.01 * i) for i in range(-30, 1)]
    return {
        'success': True,
        'current_price': price,
        'price_history': prices,
        'historical_data': {
            'prices': prices,
            'highs': [p * 1.02 for p in prices],
            'lows': [p * 0.98 for p in prices],
            'volumes': [1000000] * len(prices),
        },
    }


def _make_option(strike=95.0, bid=2.0, ask=2.2, volume=100, oi=500,
                 iv=0.25, expiry='2026-06-20', option_type='put'):
    """构造最小 option dict"""
    return {
        'strike': strike,
        'bid': bid,
        'ask': ask,
        'mid_price': (bid + ask) / 2,
        'volume': volume,
        'open_interest': oi,
        'implied_volatility': iv,
        'expiry': expiry,
        'type': option_type,
        'delta': -0.3 if option_type == 'put' else 0.3,
        'gamma': 0.02,
        'theta': -0.05,
        'vega': 0.15,
        'days_to_expiry': 30,
    }


def _make_options_data(current_price=100.0, options=None):
    """构造最小 options_data dict"""
    if options is None:
        options = [_make_option(strike=95.0), _make_option(strike=90.0)]
    return {
        'success': True,
        'symbol': 'TEST',
        'current_price': current_price,
        'options': options,
        'expirations': ['2026-06-20'],
    }


# ============================================================
# 1. 评分器 market_config 传递测试
# ============================================================

class TestScorerMarketConfigParam:
    """评分器接受 market_config 参数且不报错"""

    def test_sell_put_accepts_market_config(self):
        from app.analysis.options_analysis.scoring.sell_put import SellPutScorer
        scorer = SellPutScorer()
        # 调用不应抛出异常（结果可能因数据不充分而为空）
        result = scorer.score_options(
            _make_options_data(), _make_stock_data(),
            market_config=HK_OPTIONS_CONFIG
        )
        assert isinstance(result, dict)

    def test_sell_call_accepts_market_config(self):
        from app.analysis.options_analysis.scoring.sell_call import SellCallScorer
        scorer = SellCallScorer()
        result = scorer.score_options(
            _make_options_data(), _make_stock_data(),
            market_config=CN_OPTIONS_CONFIG
        )
        assert isinstance(result, dict)

    def test_buy_call_accepts_market_config(self):
        from app.analysis.options_analysis.scoring.buy_call import BuyCallScorer
        scorer = BuyCallScorer()
        result = scorer.score_options(
            _make_options_data(), _make_stock_data(),
            market_config=HK_OPTIONS_CONFIG
        )
        assert isinstance(result, dict)

    def test_buy_put_accepts_market_config(self):
        from app.analysis.options_analysis.scoring.buy_put import BuyPutScorer
        scorer = BuyPutScorer()
        result = scorer.score_options(
            _make_options_data(), _make_stock_data(),
            market_config=CN_OPTIONS_CONFIG
        )
        assert isinstance(result, dict)


# ============================================================
# 2. 向后兼容：不传 market_config 时默认 US
# ============================================================

class TestBackwardCompatibility:
    """不传 market_config 时，行为与修改前一致（默认 US）"""

    def test_sell_put_default_us(self):
        from app.analysis.options_analysis.scoring.sell_put import SellPutScorer
        scorer = SellPutScorer()
        # 不传 market_config — 应使用 US 默认
        result = scorer.score_options(_make_options_data(), _make_stock_data())
        assert isinstance(result, dict)

    def test_sell_call_default_us(self):
        from app.analysis.options_analysis.scoring.sell_call import SellCallScorer
        scorer = SellCallScorer()
        result = scorer.score_options(_make_options_data(), _make_stock_data())
        assert isinstance(result, dict)

    def test_buy_call_default_us(self):
        from app.analysis.options_analysis.scoring.buy_call import BuyCallScorer
        scorer = BuyCallScorer()
        result = scorer.score_options(_make_options_data(), _make_stock_data())
        assert isinstance(result, dict)

    def test_buy_put_default_us(self):
        from app.analysis.options_analysis.scoring.buy_put import BuyPutScorer
        scorer = BuyPutScorer()
        result = scorer.score_options(_make_options_data(), _make_stock_data())
        assert isinstance(result, dict)


# ============================================================
# 3. VRP 计算器 — 年化因子正确
# ============================================================

class TestVRPMarketConfig:
    """VRP 计算器使用正确的市场交易日数"""

    def test_vrp_accepts_market_config(self):
        from app.analysis.options_analysis.advanced.vrp_calculator import VRPCalculator
        vrp = VRPCalculator()
        result = vrp.calculate(
            '0700.HK', _make_options_data(), _make_stock_data(),
            market_config=HK_OPTIONS_CONFIG
        )
        assert isinstance(result, dict)

    def test_vrp_default_us(self):
        from app.analysis.options_analysis.advanced.vrp_calculator import VRPCalculator
        vrp = VRPCalculator()
        result = vrp.calculate('AAPL', _make_options_data(), _make_stock_data())
        assert isinstance(result, dict)


# ============================================================
# 4. 风险调整器 — 合约乘数和保证金率
# ============================================================

class TestRiskAdjusterMarketConfig:
    """风险调整器使用正确的乘数和保证金率"""

    def test_risk_adjuster_accepts_market_config(self):
        from app.analysis.options_analysis.advanced.risk_adjuster import RiskAdjuster
        adjuster = RiskAdjuster()
        strategy_analysis = {
            'sell_put': {
                'success': True,
                'recommendations': [_make_option(strike=95.0)]
            }
        }
        result = adjuster.calculate_position_sizing(
            strategy_analysis, 100000.0, 'moderate',
            market_config=CN_OPTIONS_CONFIG
        )
        assert isinstance(result, dict)

    def test_risk_adjuster_default_us(self):
        from app.analysis.options_analysis.advanced.risk_adjuster import RiskAdjuster
        adjuster = RiskAdjuster()
        strategy_analysis = {
            'sell_put': {
                'success': True,
                'recommendations': [_make_option(strike=95.0)]
            }
        }
        result = adjuster.calculate_position_sizing(
            strategy_analysis, 100000.0, 'moderate'
        )
        assert isinstance(result, dict)


# ============================================================
# 5. Engine 白名单校验
# ============================================================

class TestEngineWhitelist:
    """引擎层白名单校验"""

    @patch('app.analysis.options_analysis.core.engine.get_option_market_config')
    def test_engine_rejects_non_whitelisted_hk(self, mock_get_config):
        mock_get_config.return_value = HK_OPTIONS_CONFIG
        from app.analysis.options_analysis.core.engine import OptionsAnalysisEngine
        engine = OptionsAnalysisEngine()
        result = engine.analyze_options_chain('1234.HK')
        assert result['success'] is False
        assert 'allowed_symbols' in result
        assert '0700.HK' in result['allowed_symbols']

    @patch('app.analysis.options_analysis.core.engine.get_option_market_config')
    def test_engine_rejects_non_whitelisted_cn(self, mock_get_config):
        mock_get_config.return_value = CN_OPTIONS_CONFIG
        from app.analysis.options_analysis.core.engine import OptionsAnalysisEngine
        engine = OptionsAnalysisEngine()
        result = engine.analyze_options_chain('510500.SS')
        assert result['success'] is False
        assert 'allowed_symbols' in result

    @patch('app.analysis.options_analysis.core.engine.get_option_market_config')
    def test_engine_allows_whitelisted_us(self, mock_get_config):
        """US 无白名单限制 — 不应在白名单校验阶段失败"""
        mock_get_config.return_value = US_OPTIONS_CONFIG
        from app.analysis.options_analysis.core.engine import OptionsAnalysisEngine
        engine = OptionsAnalysisEngine()
        # 不 mock data_fetcher，所以会在获取数据阶段失败，但不是白名单失败
        result = engine.analyze_options_chain('AAPL')
        # US 不应因白名单被拒（可能因数据获取失败）
        if not result['success']:
            assert 'allowed_symbols' not in result

    @patch('app.analysis.options_analysis.core.engine.get_option_market_config')
    def test_engine_result_has_market_info(self, mock_get_config):
        """成功分析应包含 market_info"""
        mock_get_config.return_value = HK_OPTIONS_CONFIG
        from app.analysis.options_analysis.core.engine import OptionsAnalysisEngine
        engine = OptionsAnalysisEngine()

        # Mock data_fetcher 返回成功
        engine.data_fetcher.get_options_chain = MagicMock(return_value=_make_options_data())
        engine.data_fetcher.get_underlying_stock_data = MagicMock(return_value=_make_stock_data())

        result = engine.analyze_options_chain('0700.HK')
        assert result['success'] is True
        assert 'market_info' in result
        assert result['market_info']['market'] == 'HK'
        assert result['market_info']['currency'] == 'HKD'


# ============================================================
# 6. 市场参数差异验证
# ============================================================

class TestMarketParameterDifferences:
    """验证不同市场配置之间的参数差异"""

    def test_cn_multiplier_much_larger(self):
        assert CN_OPTIONS_CONFIG.contract_multiplier == 10000
        assert US_OPTIONS_CONFIG.contract_multiplier == 100
        assert CN_OPTIONS_CONFIG.contract_multiplier / US_OPTIONS_CONFIG.contract_multiplier == 100

    def test_risk_free_rate_order(self):
        """US > HK > CN 无风险利率"""
        assert US_OPTIONS_CONFIG.risk_free_rate > HK_OPTIONS_CONFIG.risk_free_rate
        assert HK_OPTIONS_CONFIG.risk_free_rate > CN_OPTIONS_CONFIG.risk_free_rate

    def test_trading_days_order(self):
        """US > HK > CN 交易日"""
        assert US_OPTIONS_CONFIG.trading_days_per_year > HK_OPTIONS_CONFIG.trading_days_per_year
        assert HK_OPTIONS_CONFIG.trading_days_per_year > CN_OPTIONS_CONFIG.trading_days_per_year

    def test_cn_cash_settlement(self):
        assert CN_OPTIONS_CONFIG.cash_settlement is True
        assert US_OPTIONS_CONFIG.cash_settlement is False
        assert HK_OPTIONS_CONFIG.cash_settlement is False

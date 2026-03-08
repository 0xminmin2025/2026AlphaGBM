"""
期权市场参数配置模块 单元测试
"""

import pytest
from unittest.mock import patch, MagicMock
from app.analysis.options_analysis.option_market_config import (
    OptionMarketConfig,
    US_OPTIONS_CONFIG,
    HK_OPTIONS_CONFIG,
    CN_OPTIONS_CONFIG,
    get_option_market_config,
)


class TestOptionMarketConfigInstances:
    """测试三个市场配置实例的参数正确性"""

    def test_us_config_basic_params(self):
        cfg = US_OPTIONS_CONFIG
        assert cfg.market == 'US'
        assert cfg.currency == 'USD'
        assert cfg.contract_multiplier == 100
        assert cfg.risk_free_rate == 0.05
        assert cfg.trading_days_per_year == 252
        assert cfg.default_margin_rate == 0.20
        assert cfg.monthly_expiry_rule == 'third_friday'
        assert cfg.whitelist_enforced is False
        assert cfg.cash_settlement is False

    def test_hk_config_basic_params(self):
        cfg = HK_OPTIONS_CONFIG
        assert cfg.market == 'HK'
        assert cfg.currency == 'HKD'
        assert cfg.contract_multiplier == 100
        assert cfg.risk_free_rate == 0.025
        assert cfg.trading_days_per_year == 242
        assert cfg.default_margin_rate == 0.15
        assert cfg.monthly_expiry_rule == 'fourth_wednesday'
        assert cfg.whitelist_enforced is True
        assert cfg.cash_settlement is False

    def test_cn_config_basic_params(self):
        cfg = CN_OPTIONS_CONFIG
        assert cfg.market == 'CN'
        assert cfg.currency == 'CNY'
        assert cfg.contract_multiplier == 10000
        assert cfg.risk_free_rate == 0.018
        assert cfg.trading_days_per_year == 240
        assert cfg.default_margin_rate == 0.12
        assert cfg.monthly_expiry_rule == 'fourth_wednesday'
        assert cfg.whitelist_enforced is True
        assert cfg.cash_settlement is True

    def test_hk_liquidity_thresholds(self):
        cfg = HK_OPTIONS_CONFIG
        assert cfg.min_volume == 5
        assert cfg.min_open_interest == 20
        assert cfg.max_bid_ask_spread_pct == 0.20

    def test_cn_liquidity_thresholds(self):
        cfg = CN_OPTIONS_CONFIG
        assert cfg.min_volume == 50
        assert cfg.min_open_interest == 100
        assert cfg.max_bid_ask_spread_pct == 0.08


class TestMultiplierOverride:
    """测试个股合约乘数覆盖"""

    def test_hk_default_multiplier(self):
        assert HK_OPTIONS_CONFIG.get_multiplier('9999.HK') == 100

    def test_hk_tencent_multiplier(self):
        assert HK_OPTIONS_CONFIG.get_multiplier('0700.HK') == 100

    def test_hk_meituan_multiplier(self):
        assert HK_OPTIONS_CONFIG.get_multiplier('3690.HK') == 100

    def test_cn_etf_multiplier(self):
        assert CN_OPTIONS_CONFIG.get_multiplier('510050.SS') == 10000

    def test_us_multiplier_always_100(self):
        assert US_OPTIONS_CONFIG.get_multiplier('AAPL') == 100
        assert US_OPTIONS_CONFIG.get_multiplier('TSLA') == 100


class TestWhitelist:
    """测试白名单逻辑"""

    def test_us_no_whitelist(self):
        assert US_OPTIONS_CONFIG.is_symbol_allowed('AAPL') is True
        assert US_OPTIONS_CONFIG.is_symbol_allowed('ANY_SYMBOL') is True

    def test_hk_whitelist_enforced(self):
        assert HK_OPTIONS_CONFIG.is_symbol_allowed('0700.HK') is True
        assert HK_OPTIONS_CONFIG.is_symbol_allowed('9988.HK') is True
        assert HK_OPTIONS_CONFIG.is_symbol_allowed('3690.HK') is True
        assert HK_OPTIONS_CONFIG.is_symbol_allowed('1234.HK') is False

    def test_cn_whitelist_enforced(self):
        assert CN_OPTIONS_CONFIG.is_symbol_allowed('510050.SS') is True
        assert CN_OPTIONS_CONFIG.is_symbol_allowed('510300.SS') is True
        assert CN_OPTIONS_CONFIG.is_symbol_allowed('510500.SS') is False

    def test_hk_get_allowed_symbols(self):
        allowed = HK_OPTIONS_CONFIG.get_allowed_symbols()
        assert '0700.HK' in allowed
        assert '9988.HK' in allowed
        assert '3690.HK' in allowed
        assert len(allowed) == 3

    def test_cn_get_allowed_symbols(self):
        allowed = CN_OPTIONS_CONFIG.get_allowed_symbols()
        assert '510050.SS' in allowed
        assert '510300.SS' in allowed
        assert len(allowed) == 2


class TestFrozenDataclass:
    """测试 frozen 不可变性"""

    def test_cannot_modify_market(self):
        with pytest.raises(AttributeError):
            US_OPTIONS_CONFIG.market = 'CN'

    def test_cannot_modify_risk_free_rate(self):
        with pytest.raises(AttributeError):
            HK_OPTIONS_CONFIG.risk_free_rate = 0.99

    def test_cannot_modify_multiplier(self):
        with pytest.raises(AttributeError):
            CN_OPTIONS_CONFIG.contract_multiplier = 999


class TestGetOptionMarketConfig:
    """测试 get_option_market_config() 自动市场检测"""

    @patch('app.services.market_data.market_detector.detect_market')
    def test_us_symbol(self, mock_detect):
        mock_market = MagicMock()
        mock_market.value = 'US'
        mock_detect.return_value = mock_market

        cfg = get_option_market_config('AAPL')
        assert cfg.market == 'US'
        assert cfg.contract_multiplier == 100

    @patch('app.services.market_data.market_detector.detect_market')
    def test_hk_symbol(self, mock_detect):
        mock_market = MagicMock()
        mock_market.value = 'HK'
        mock_detect.return_value = mock_market

        cfg = get_option_market_config('0700.HK')
        assert cfg.market == 'HK'
        assert cfg.risk_free_rate == 0.025

    @patch('app.services.market_data.market_detector.detect_market')
    def test_cn_symbol(self, mock_detect):
        mock_market = MagicMock()
        mock_market.value = 'CN'
        mock_detect.return_value = mock_market

        cfg = get_option_market_config('510050.SS')
        assert cfg.market == 'CN'
        assert cfg.contract_multiplier == 10000

    @patch('app.services.market_data.market_detector.detect_market')
    def test_fallback_to_us_on_error(self, mock_detect):
        mock_detect.side_effect = Exception("detection failed")

        cfg = get_option_market_config('UNKNOWN')
        assert cfg.market == 'US'

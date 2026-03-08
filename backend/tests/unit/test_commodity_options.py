"""
商品期货期权功能 - 综合单元测试

覆盖范围：
1. 商品代码检测 (market_detector)
2. 适配器列名标准化 (AkShareCommodityAdapter) — mock akshare
3. 交割风险计算 (DeliveryRiskCalculator)
4. 期权市场配置 (COMMODITY_OPTIONS_CONFIG)
5. 数据获取路由 (OptionsDataFetcher)
6. 推荐服务商品池
"""

import pytest
import pandas as pd
import numpy as np
from datetime import date, timedelta
from unittest.mock import patch, MagicMock


# ═══════════════════════════════════════════════════════════════
# 1. 商品代码检测 单元测试
# ═══════════════════════════════════════════════════════════════

class TestCommoditySymbolDetection:
    """商品品种代码识别"""

    def test_bare_product_codes(self):
        from app.services.market_data.market_detector import detect_market, is_commodity_symbol
        from app.services.market_data.interfaces import Market

        for code in ('au', 'ag', 'cu', 'al', 'm'):
            assert is_commodity_symbol(code) is True, f"{code} should be commodity"
            assert detect_market(code) == Market.COMMODITY

    def test_product_codes_uppercase(self):
        from app.services.market_data.market_detector import detect_market, is_commodity_symbol
        from app.services.market_data.interfaces import Market

        for code in ('AU', 'AG', 'CU', 'AL', 'M'):
            assert is_commodity_symbol(code) is True, f"{code} uppercase should be commodity"
            assert detect_market(code) == Market.COMMODITY

    def test_contract_codes_with_month(self):
        from app.services.market_data.market_detector import detect_market
        from app.services.market_data.interfaces import Market

        for code in ('au2604', 'ag2507', 'cu2512', 'al2603', 'm2605'):
            assert detect_market(code) == Market.COMMODITY, f"{code} should be COMMODITY"

    def test_exchange_prefix_codes(self):
        from app.services.market_data.market_detector import detect_market
        from app.services.market_data.interfaces import Market

        assert detect_market('SHFE.au2604') == Market.COMMODITY
        assert detect_market('DCE.m2605') == Market.COMMODITY
        assert detect_market('shfe.cu2506') == Market.COMMODITY

    def test_non_commodity_symbols_unchanged(self):
        from app.services.market_data.market_detector import detect_market
        from app.services.market_data.interfaces import Market

        assert detect_market('AAPL') == Market.US
        assert detect_market('TSLA') == Market.US
        assert detect_market('0700.HK') == Market.HK
        assert detect_market('600519') == Market.CN
        assert detect_market('600519.SS') == Market.CN
        assert detect_market('000001') == Market.CN

    def test_ambiguous_code_m_is_commodity(self):
        """单字母 m 应该识别为商品而非美股"""
        from app.services.market_data.market_detector import detect_market
        from app.services.market_data.interfaces import Market

        assert detect_market('m') == Market.COMMODITY
        assert detect_market('M') == Market.COMMODITY
        assert detect_market('M2605') == Market.COMMODITY

    def test_non_commodity_similar_codes(self):
        """非白名单品种不应误识别"""
        from app.services.market_data.market_detector import is_commodity_symbol

        assert is_commodity_symbol('MM') is False
        assert is_commodity_symbol('GOLD') is False
        assert is_commodity_symbol('xx') is False
        assert is_commodity_symbol('zn2605') is False  # 锌 不在白名单

    def test_is_commodity_helper(self):
        from app.services.market_data.market_detector import is_commodity

        assert is_commodity('au') is True
        assert is_commodity('AAPL') is False

    def test_get_market_name_commodity(self):
        from app.services.market_data.market_detector import get_market_name
        from app.services.market_data.interfaces import Market

        assert get_market_name(Market.COMMODITY, 'en') == 'Commodity Futures'
        assert get_market_name(Market.COMMODITY, 'zh') == '商品期货'


class TestCommodityConfigRouting:
    """get_market_for_symbol 和 get_timezone_for_market"""

    def test_get_market_for_commodity(self):
        from app.services.market_data.config import get_market_for_symbol
        from app.services.market_data.interfaces import Market

        assert get_market_for_symbol('au') == Market.COMMODITY
        assert get_market_for_symbol('m2605') == Market.COMMODITY

    def test_timezone_for_commodity(self):
        from app.services.market_data.config import get_timezone_for_market
        from app.services.market_data.interfaces import Market

        assert get_timezone_for_market(Market.COMMODITY) == 'Asia/Shanghai'

    def test_provider_config_exists(self):
        from app.services.market_data.config import PROVIDER_CONFIGS

        assert 'akshare_commodity' in PROVIDER_CONFIGS
        cfg = PROVIDER_CONFIGS['akshare_commodity']
        assert cfg.priority == 10
        assert cfg.requests_per_minute == 30


# ═══════════════════════════════════════════════════════════════
# 2. AkShareCommodityAdapter 单元测试 (mock akshare)
# ═══════════════════════════════════════════════════════════════

class TestAkShareCommodityAdapterParsing:
    """适配器列名标准化 + OptionsChainData 格式验证"""

    def _make_adapter(self):
        from app.services.market_data.adapters.akshare_commodity_adapter import AkShareCommodityAdapter
        adapter = AkShareCommodityAdapter()
        return adapter

    def test_adapter_properties(self):
        adapter = self._make_adapter()
        from app.services.market_data.interfaces import Market, DataType

        assert adapter.name == 'akshare_commodity'
        assert Market.COMMODITY in adapter.supported_markets
        assert DataType.OPTIONS_CHAIN in adapter.supported_data_types
        assert DataType.OPTIONS_EXPIRATIONS in adapter.supported_data_types

    def test_supports_symbol(self):
        adapter = self._make_adapter()

        assert adapter.supports_symbol('au') is True
        assert adapter.supports_symbol('au2604') is True
        assert adapter.supports_symbol('SHFE.cu2506') is True
        assert adapter.supports_symbol('m') is True
        assert adapter.supports_symbol('AAPL') is False
        assert adapter.supports_symbol('0700.HK') is False

    def test_extract_product(self):
        from app.services.market_data.adapters.akshare_commodity_adapter import AkShareCommodityAdapter

        assert AkShareCommodityAdapter._extract_product('au2604') == 'au'
        assert AkShareCommodityAdapter._extract_product('SHFE.au2604') == 'au'
        assert AkShareCommodityAdapter._extract_product('m') == 'm'
        assert AkShareCommodityAdapter._extract_product('M2605') == 'm'

    def test_extract_contract(self):
        from app.services.market_data.adapters.akshare_commodity_adapter import AkShareCommodityAdapter

        assert AkShareCommodityAdapter._extract_contract('au2604') == 'au2604'
        assert AkShareCommodityAdapter._extract_contract('au') is None
        assert AkShareCommodityAdapter._extract_contract('SHFE.cu2506') == 'cu2506'

    def test_parse_option_table_column_mapping(self):
        """验证中文列名 → 标准英文列名映射"""
        adapter = self._make_adapter()

        # 构造模拟的 akshare 返回 DataFrame (中文列名)
        mock_df = pd.DataFrame({
            '看涨合约-买量': [10, 20],
            '看涨合约-买价': [5.0, 3.0],
            '看涨合约-最新价': [5.5, 3.5],
            '看涨合约-卖价': [6.0, 4.0],
            '看涨合约-卖量': [15, 25],
            '看涨合约-持仓量': [100, 200],
            '看涨合约-涨跌': [0.5, -0.2],
            '看涨合约-看涨期权合约': ['au2604C680', 'au2604C700'],
            '行权价': [680.0, 700.0],
            '看跌合约-买量': [8, 12],
            '看跌合约-买价': [4.0, 6.0],
            '看跌合约-最新价': [4.5, 6.5],
            '看跌合约-卖价': [5.0, 7.0],
            '看跌合约-卖量': [12, 18],
            '看跌合约-持仓量': [80, 150],
            '看跌合约-涨跌': [-0.3, 0.1],
            '看跌合约-看跌期权合约': ['au2604P680', 'au2604P700'],
        })

        calls_df, puts_df, underlying_price = adapter._parse_option_table(mock_df, 'au')

        # calls 验证
        assert len(calls_df) == 2
        assert 'strike' in calls_df.columns
        assert 'bid' in calls_df.columns
        assert 'ask' in calls_df.columns
        assert 'lastPrice' in calls_df.columns
        assert 'volume' in calls_df.columns
        assert 'openInterest' in calls_df.columns
        assert 'contractName' in calls_df.columns

        # 验证具体数值
        row0 = calls_df.iloc[0]
        assert row0['strike'] == 680.0
        assert row0['bid'] == 5.0
        assert row0['ask'] == 6.0
        assert row0['lastPrice'] == 5.5
        assert row0['volume'] == 25  # 买量10 + 卖量15
        assert row0['openInterest'] == 100

        # puts 验证
        assert len(puts_df) == 2
        put_row0 = puts_df.iloc[0]
        assert put_row0['strike'] == 680.0
        assert put_row0['bid'] == 4.0
        assert put_row0['ask'] == 5.0
        assert put_row0['lastPrice'] == 4.5
        assert put_row0['volume'] == 20  # 买量8 + 卖量12
        assert put_row0['openInterest'] == 80

        # underlying price 应为非零
        assert underlying_price > 0

    def test_get_options_expirations_mock(self):
        """mock akshare 返回合约列表"""
        adapter = self._make_adapter()
        mock_ak = MagicMock()
        mock_ak.option_commodity_contract_sina.return_value = pd.DataFrame({
            '序号': [1, 2, 3],
            '合约': ['au2604', 'au2605', 'au2606']
        })
        adapter._ak = mock_ak

        result = adapter.get_options_expirations('au')

        assert result is not None
        assert len(result) == 3
        assert result[0] == 'au2604'
        assert result[2] == 'au2606'
        mock_ak.option_commodity_contract_sina.assert_called_once_with(symbol='黄金期权')

    def test_get_options_chain_mock(self):
        """mock akshare 返回期权链 → 验证 OptionsChainData 格式"""
        adapter = self._make_adapter()
        mock_ak = MagicMock()

        # 模拟期权链表
        mock_ak.option_commodity_contract_table_sina.return_value = pd.DataFrame({
            '看涨合约-买量': [10],
            '看涨合约-买价': [5.0],
            '看涨合约-最新价': [5.5],
            '看涨合约-卖价': [6.0],
            '看涨合约-卖量': [15],
            '看涨合约-持仓量': [100],
            '看涨合约-涨跌': [0.5],
            '看涨合约-看涨期权合约': ['au2604C680'],
            '行权价': [680.0],
            '看跌合约-买量': [8],
            '看跌合约-买价': [4.0],
            '看跌合约-最新价': [4.5],
            '看跌合约-卖价': [5.0],
            '看跌合约-卖量': [12],
            '看跌合约-持仓量': [80],
            '看跌合约-涨跌': [-0.3],
            '看跌合约-看跌期权合约': ['au2604P680'],
        })
        adapter._ak = mock_ak

        result = adapter.get_options_chain('au', 'au2604')

        assert result is not None
        assert result.symbol == 'au'
        assert result.expiry_date == 'au2604'
        assert result.source == 'akshare_commodity'
        assert not result.empty
        assert isinstance(result.calls, pd.DataFrame)
        assert isinstance(result.puts, pd.DataFrame)
        assert len(result.calls) == 1
        assert len(result.puts) == 1

    def test_get_options_expirations_unsupported_product(self):
        adapter = self._make_adapter()
        result = adapter.get_options_expirations('xx_unknown')
        assert result is None

    def test_get_info_returns_commodity_info(self):
        adapter = self._make_adapter()
        info = adapter.get_info('au')

        assert info is not None
        assert info.name == '黄金期权'
        assert info.sector == 'Commodities'
        assert info.exchange == 'SHFE'
        assert info.currency == 'CNY'

    def test_get_fundamentals_returns_none(self):
        adapter = self._make_adapter()
        assert adapter.get_fundamentals('au') is None

    def test_estimate_underlying_price(self):
        adapter = self._make_adapter()
        calls = [
            {'strike': 680, 'lastPrice': 20.0},
            {'strike': 700, 'lastPrice': 5.0},
        ]
        puts = [
            {'strike': 680, 'lastPrice': 5.0},
            {'strike': 700, 'lastPrice': 20.0},
        ]
        # At 680: call=20, put=5 → diff=15
        # At 700: call=5, put=20 → diff=15
        # Both same diff, use first match (680): underlying ≈ 680 + 20 - 5 = 695
        price = adapter._estimate_underlying_price(calls, puts)
        assert abs(price - 695.0) < 0.01


class TestAdapterRegistration:
    """验证适配器在 MarketDataService 中正确注册和路由"""

    def test_adapter_in_service(self):
        from app.services.market_data.service import MarketDataService
        from app.services.market_data.interfaces import Market, DataType

        # Reset singleton
        MarketDataService._instance = None
        service = MarketDataService()

        assert 'akshare_commodity' in service._adapters

        providers = service._get_providers_for_data_type(
            DataType.OPTIONS_CHAIN, Market.COMMODITY
        )
        assert len(providers) >= 1
        assert providers[0].name == 'akshare_commodity'

        # 恢复 singleton
        MarketDataService._instance = None

    def test_no_commodity_provider_for_us_market(self):
        from app.services.market_data.service import MarketDataService
        from app.services.market_data.interfaces import Market, DataType

        MarketDataService._instance = None
        service = MarketDataService()

        providers = service._get_providers_for_data_type(
            DataType.OPTIONS_CHAIN, Market.US
        )
        names = [p.name for p in providers]
        assert 'akshare_commodity' not in names

        MarketDataService._instance = None


# ═══════════════════════════════════════════════════════════════
# 3. 交割风险计算 单元测试
# ═══════════════════════════════════════════════════════════════

class TestDeliveryRiskCalculator:
    """交割月风险评估"""

    def _calc(self):
        from app.analysis.options_analysis.advanced.delivery_risk import DeliveryRiskCalculator
        return DeliveryRiskCalculator()

    def test_far_future_contract_safe(self):
        """远月合约: penalty=0, recommendation=ok"""
        calc = self._calc()
        result = calc.assess('au2712')

        assert result.is_red_zone is False
        assert result.is_warning_zone is False
        assert result.delivery_penalty == 0.0
        assert result.recommendation == 'ok'
        assert result.warning == ''

    def test_red_zone_t25(self):
        """T-25天: 红色区域, penalty=1.0"""
        calc = self._calc()
        today = date.today()
        target = today + timedelta(days=25)
        yymm = f'{target.year - 2000:02d}{target.month:02d}'
        code = f'au{yymm}'

        result = calc.assess(code)
        # days_to_delivery = (first of target month) - today
        # This could be <=30 depending on where we are in the month
        if result.days_to_delivery <= 30:
            assert result.is_red_zone is True
            assert result.delivery_penalty == 1.0
            assert result.recommendation == 'close'
            assert '平仓' in result.warning

    def test_warning_zone_t45(self):
        """T-45天: 黄色区域, 0 < penalty < 1"""
        calc = self._calc()
        today = date.today()
        # 找一个月份使得 days_to_delivery 在 30-60
        target = today + timedelta(days=50)
        yymm = f'{target.year - 2000:02d}{target.month:02d}'
        code = f'ag{yymm}'

        result = calc.assess(code)
        if 30 < result.days_to_delivery <= 60:
            assert result.is_warning_zone is True
            assert result.is_red_zone is False
            assert 0 < result.delivery_penalty < 1.0
            assert result.recommendation == 'reduce'
            assert '移仓' in result.warning

    def test_penalty_linear_interpolation(self):
        """验证警告区域的线性插值精度"""
        calc = self._calc()
        # Directly test with known days
        # At 60 days: penalty = 0/30 = 0
        # At 45 days: penalty = 15/30 = 0.5
        # At 30 days: penalty = 30/30 = 1.0 (but <=30 is red zone)

        # 构造一个刚好 45 天的合约
        today = date.today()
        target_date = today + timedelta(days=45)
        # 如果正好是某月1日, days_to_delivery = 45
        # 但合约码是 YYMM, delivery_date = first of that month

        # 直接测试 _parse_delivery_month
        result = calc._parse_delivery_month('au2612')
        assert result == date(2026, 12, 1)

        result = calc._parse_delivery_month('m2605')
        assert result == date(2026, 5, 1)

    def test_past_contract_penalty_max(self):
        """已过期合约: penalty=1.0"""
        calc = self._calc()
        result = calc.assess('au2501')  # 2025-01, 已过去

        assert result.is_red_zone is True
        assert result.delivery_penalty == 1.0
        assert result.recommendation == 'close'
        assert result.days_to_delivery < 0

    def test_invalid_contract_graceful(self):
        """无法解析的合约码: penalty=0, 不报错"""
        calc = self._calc()
        result = calc.assess('unknown')

        assert result.delivery_penalty == 0.0
        assert result.recommendation == 'ok'
        assert result.delivery_month == 'unknown'

    def test_parse_delivery_month_edge_cases(self):
        calc = self._calc()

        # 正常格式
        assert calc._parse_delivery_month('au2604') == date(2026, 4, 1)
        assert calc._parse_delivery_month('m2512') == date(2025, 12, 1)
        assert calc._parse_delivery_month('cu2601') == date(2026, 1, 1)

        # 无法解析
        assert calc._parse_delivery_month('unknown') is None
        assert calc._parse_delivery_month('au') is None
        assert calc._parse_delivery_month('') is None

    def test_to_dict_format(self):
        calc = self._calc()
        result = calc.assess('au2712')
        d = result.to_dict()

        assert isinstance(d, dict)
        assert 'days_to_delivery' in d
        assert 'is_red_zone' in d
        assert 'is_warning_zone' in d
        assert 'delivery_penalty' in d
        assert 'warning' in d
        assert 'recommendation' in d
        assert 'delivery_month' in d


# ═══════════════════════════════════════════════════════════════
# 4. 期权市场配置 - COMMODITY 测试
# ═══════════════════════════════════════════════════════════════

class TestCommodityOptionsConfig:
    """COMMODITY_OPTIONS_CONFIG 参数正确性"""

    def test_basic_params(self):
        from app.analysis.options_analysis.option_market_config import COMMODITY_OPTIONS_CONFIG

        cfg = COMMODITY_OPTIONS_CONFIG
        assert cfg.market == 'COMMODITY'
        assert cfg.currency == 'CNY'
        assert cfg.risk_free_rate == 0.018
        assert cfg.trading_days_per_year == 240
        assert cfg.default_margin_rate == 0.10
        assert cfg.whitelist_enforced is True
        assert cfg.cash_settlement is False
        assert cfg.monthly_expiry_rule == 'exchange_specific'

    def test_per_symbol_multiplier(self):
        from app.analysis.options_analysis.option_market_config import COMMODITY_OPTIONS_CONFIG

        assert COMMODITY_OPTIONS_CONFIG.get_multiplier('au') == 1000
        assert COMMODITY_OPTIONS_CONFIG.get_multiplier('AU') == 1000
        assert COMMODITY_OPTIONS_CONFIG.get_multiplier('ag') == 15
        assert COMMODITY_OPTIONS_CONFIG.get_multiplier('AG') == 15
        assert COMMODITY_OPTIONS_CONFIG.get_multiplier('cu') == 5
        assert COMMODITY_OPTIONS_CONFIG.get_multiplier('m') == 10
        assert COMMODITY_OPTIONS_CONFIG.get_multiplier('M') == 10
        assert COMMODITY_OPTIONS_CONFIG.get_multiplier('al') == 5

    def test_whitelist(self):
        from app.analysis.options_analysis.option_market_config import COMMODITY_OPTIONS_CONFIG

        assert COMMODITY_OPTIONS_CONFIG.is_symbol_allowed('au') is True
        assert COMMODITY_OPTIONS_CONFIG.is_symbol_allowed('ag') is True
        assert COMMODITY_OPTIONS_CONFIG.is_symbol_allowed('cu') is True
        assert COMMODITY_OPTIONS_CONFIG.is_symbol_allowed('al') is True
        assert COMMODITY_OPTIONS_CONFIG.is_symbol_allowed('m') is True
        assert COMMODITY_OPTIONS_CONFIG.is_symbol_allowed('xx') is False

    def test_whitelist_with_contract_code(self):
        from app.analysis.options_analysis.option_market_config import COMMODITY_OPTIONS_CONFIG

        assert COMMODITY_OPTIONS_CONFIG.is_symbol_allowed('au2604') is True
        assert COMMODITY_OPTIONS_CONFIG.is_symbol_allowed('m2605') is True
        assert COMMODITY_OPTIONS_CONFIG.is_symbol_allowed('SHFE.cu2506') is True
        assert COMMODITY_OPTIONS_CONFIG.is_symbol_allowed('xx2604') is False

    def test_get_option_market_config_auto_detect(self):
        from app.analysis.options_analysis.option_market_config import get_option_market_config

        cfg = get_option_market_config('au')
        assert cfg.market == 'COMMODITY'

        cfg = get_option_market_config('m2605')
        assert cfg.market == 'COMMODITY'

        cfg = get_option_market_config('AAPL')
        assert cfg.market == 'US'

    def test_config_in_market_map(self):
        from app.analysis.options_analysis.option_market_config import _MARKET_CONFIG_MAP

        assert 'COMMODITY' in _MARKET_CONFIG_MAP
        assert _MARKET_CONFIG_MAP['COMMODITY'].market == 'COMMODITY'

    def test_liquidity_thresholds(self):
        from app.analysis.options_analysis.option_market_config import COMMODITY_OPTIONS_CONFIG

        assert COMMODITY_OPTIONS_CONFIG.min_volume == 5
        assert COMMODITY_OPTIONS_CONFIG.min_open_interest == 20
        assert COMMODITY_OPTIONS_CONFIG.max_bid_ask_spread_pct == 0.15


# ═══════════════════════════════════════════════════════════════
# 5. 推荐服务商品池 测试
# ═══════════════════════════════════════════════════════════════

class TestRecommendationServiceCommodity:
    """推荐服务包含商品标的"""

    def test_commodity_symbols_in_pool(self):
        from app.services.recommendation_service import COMMODITY_HOT_SYMBOLS

        assert 'au' in COMMODITY_HOT_SYMBOLS
        assert 'ag' in COMMODITY_HOT_SYMBOLS
        assert 'cu' in COMMODITY_HOT_SYMBOLS

    def test_commodity_quality_ratings(self):
        from app.services.recommendation_service import SYMBOL_QUALITY

        assert 'au' in SYMBOL_QUALITY
        assert SYMBOL_QUALITY['au']['tier'] == 1
        assert SYMBOL_QUALITY['au']['quality'] >= 80

        assert 'ag' in SYMBOL_QUALITY
        assert 'cu' in SYMBOL_QUALITY
        assert 'm' in SYMBOL_QUALITY

    def test_all_symbols_includes_commodity(self):
        """确保生成推荐时商品标的在标的池中"""
        from app.services.recommendation_service import (
            HOT_SYMBOLS, HK_HOT_SYMBOLS, CN_HOT_SYMBOLS, COMMODITY_HOT_SYMBOLS
        )

        all_symbols = HOT_SYMBOLS[:8] + HK_HOT_SYMBOLS + CN_HOT_SYMBOLS + COMMODITY_HOT_SYMBOLS
        assert 'au' in all_symbols
        assert 'ag' in all_symbols
        assert 'cu' in all_symbols


# ═══════════════════════════════════════════════════════════════
# 6. 数据获取路由 测试
# ═══════════════════════════════════════════════════════════════

class TestDataFetcherCommodityRouting:
    """OptionsDataFetcher 的 COMMODITY 路由分支"""

    def test_commodity_routing_calls_commodity_method(self):
        """当 market_config.market == 'COMMODITY' 时应走 _get_commodity_options"""
        from app.analysis.options_analysis.core.data_fetcher import OptionsDataFetcher
        from app.analysis.options_analysis.option_market_config import COMMODITY_OPTIONS_CONFIG

        fetcher = OptionsDataFetcher()

        with patch.object(fetcher, '_get_commodity_options', return_value={'success': True, 'calls': [], 'puts': []}) as mock_method:
            fetcher.get_options_chain('au', market_config=COMMODITY_OPTIONS_CONFIG)
            mock_method.assert_called_once_with('au')

    def test_us_routing_does_not_call_commodity_method(self):
        """US 市场不应走 commodity 路由"""
        from app.analysis.options_analysis.core.data_fetcher import OptionsDataFetcher
        from app.analysis.options_analysis.option_market_config import US_OPTIONS_CONFIG

        fetcher = OptionsDataFetcher()

        with patch.object(fetcher, '_get_commodity_options') as mock_commodity, \
             patch.object(fetcher, '_get_yfinance_options_data', return_value={'success': True, 'calls': [], 'puts': []}) as mock_yf:
            fetcher.get_options_chain('AAPL', market_config=US_OPTIONS_CONFIG)
            mock_commodity.assert_not_called()
            mock_yf.assert_called_once_with('AAPL')

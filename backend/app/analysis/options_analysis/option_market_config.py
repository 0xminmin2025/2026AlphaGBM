"""
期权市场参数配置模块

为 US / HK / CN 三个市场提供期权分析所需的市场特定参数。
所有评分器、VRP计算器、风险调整器从此处读取参数，实现"参数化，不复制"。

核心设计：
- frozen dataclass 保证不可变
- get_option_market_config(symbol) 自动匹配市场
- 不传 config 时默认 US，100% 向后兼容
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Set
import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OptionMarketConfig:
    """期权市场参数配置（不可变）"""

    market: str                          # 'US', 'HK', 'CN'
    currency: str                        # 'USD', 'HKD', 'CNY'
    contract_multiplier: int             # 默认合约乘数
    risk_free_rate: float                # 无风险利率
    trading_days_per_year: int           # 年化交易日数
    default_margin_rate: float           # 默认保证金率
    min_volume: int                      # 最小成交量（流动性筛选）
    min_open_interest: int               # 最小持仓量
    max_bid_ask_spread_pct: float        # 最大买卖价差（百分比）
    monthly_expiry_rule: str             # 月到期规则：'third_friday' | 'fourth_wednesday'
    whitelist_enforced: bool             # 是否强制白名单
    whitelist: frozenset                 # 白名单标的（frozenset 保证 frozen）
    cash_settlement: bool                # 是否现金交割
    per_symbol_multiplier: Dict[str, int] = field(default_factory=dict)  # 个股乘数覆盖

    def get_multiplier(self, symbol: str) -> int:
        """获取指定标的的合约乘数（先查个股覆盖，再用默认值）"""
        clean_symbol = symbol.upper().split('.')[0]
        return self.per_symbol_multiplier.get(clean_symbol, self.contract_multiplier)

    def is_symbol_allowed(self, symbol: str) -> bool:
        """检查标的是否在白名单内（白名单未启用时始终返回 True）"""
        if not self.whitelist_enforced:
            return True
        normalized = symbol.upper()
        # 商品期权：提取品种代码进行匹配 (au2604 → AU, SHFE.au2604 → AU)
        if self.market == 'COMMODITY':
            s = symbol.lower().strip()
            if '.' in s:
                parts = s.split('.')
                if parts[0] in ('shfe', 'dce', 'czce', 'ine'):
                    s = parts[1]
            product = ''.join(c for c in s if c.isalpha())
            return product in self.whitelist
        return normalized in self.whitelist

    def get_allowed_symbols(self) -> frozenset:
        """返回白名单标的集合"""
        return self.whitelist


# ========================
# US 期权配置
# ========================
US_OPTIONS_CONFIG = OptionMarketConfig(
    market='US',
    currency='USD',
    contract_multiplier=100,
    risk_free_rate=0.05,
    trading_days_per_year=252,
    default_margin_rate=0.20,
    min_volume=10,
    min_open_interest=50,
    max_bid_ask_spread_pct=0.10,
    monthly_expiry_rule='third_friday',
    whitelist_enforced=False,
    whitelist=frozenset(),
    cash_settlement=False,
)

# ========================
# HK 期权配置
# ========================
HK_OPTIONS_CONFIG = OptionMarketConfig(
    market='HK',
    currency='HKD',
    contract_multiplier=100,
    risk_free_rate=0.025,
    trading_days_per_year=242,
    default_margin_rate=0.15,
    min_volume=5,
    min_open_interest=20,
    max_bid_ask_spread_pct=0.20,
    monthly_expiry_rule='fourth_wednesday',
    whitelist_enforced=True,
    whitelist=frozenset({'0700.HK', '9988.HK', '3690.HK'}),
    cash_settlement=False,
    per_symbol_multiplier={
        '0700': 100,   # 腾讯
        '9988': 100,   # 阿里
        '3690': 100,   # 美团
    },
)

# ========================
# CN (A股ETF) 期权配置
# ========================
CN_OPTIONS_CONFIG = OptionMarketConfig(
    market='CN',
    currency='CNY',
    contract_multiplier=10000,
    risk_free_rate=0.018,
    trading_days_per_year=240,
    default_margin_rate=0.12,
    min_volume=50,
    min_open_interest=100,
    max_bid_ask_spread_pct=0.08,
    monthly_expiry_rule='fourth_wednesday',
    whitelist_enforced=True,
    whitelist=frozenset({'510050.SS', '510300.SS'}),
    cash_settlement=True,
)

# ========================
# COMMODITY (商品期货) 期权配置
# ========================
COMMODITY_OPTIONS_CONFIG = OptionMarketConfig(
    market='COMMODITY',
    currency='CNY',
    contract_multiplier=1000,       # 默认值(黄金)，其他品种用 per_symbol_multiplier
    risk_free_rate=0.018,
    trading_days_per_year=240,
    default_margin_rate=0.10,
    min_volume=5,                   # 商品期权流动性较低
    min_open_interest=20,
    max_bid_ask_spread_pct=0.15,
    monthly_expiry_rule='exchange_specific',
    whitelist_enforced=True,
    whitelist=frozenset({'au', 'ag', 'cu', 'al', 'm'}),
    cash_settlement=False,          # 实物交割
    per_symbol_multiplier={'AU': 1000, 'AG': 15, 'CU': 5, 'AL': 5, 'M': 10},
)


# 市场配置映射
_MARKET_CONFIG_MAP: Dict[str, OptionMarketConfig] = {
    'US': US_OPTIONS_CONFIG,
    'HK': HK_OPTIONS_CONFIG,
    'CN': CN_OPTIONS_CONFIG,
    'COMMODITY': COMMODITY_OPTIONS_CONFIG,
}


def get_option_market_config(symbol: str) -> OptionMarketConfig:
    """
    根据股票代码自动解析市场，返回对应的期权参数配置。

    使用现有的 market_detector 进行市场检测，
    检测失败时默认返回 US 配置。

    Args:
        symbol: 股票代码（如 'AAPL', '0700.HK', '510050.SS', 'au', 'au2604'）

    Returns:
        OptionMarketConfig 实例
    """
    try:
        from ...services.market_data.market_detector import detect_market
        market = detect_market(symbol)
        market_key = market.value if hasattr(market, 'value') else str(market)
        config = _MARKET_CONFIG_MAP.get(market_key.upper(), US_OPTIONS_CONFIG)
        logger.debug(f"期权市场配置: {symbol} → {config.market}")
        return config
    except Exception as e:
        logger.warning(f"市场检测失败 ({symbol}), 默认使用 US 配置: {e}")
        return US_OPTIONS_CONFIG

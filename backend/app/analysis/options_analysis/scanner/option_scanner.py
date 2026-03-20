"""
期权机会扫描器

功能：
- 批量扫描多个标的的期权机会
- 按策略类型筛选（Covered Call, Cash Secured Put, Bull Spread, Wheel 等）
- 支持 IV Percentile、最低收益率、到期范围等过滤条件
- 结合现有 GBM 评分系统输出综合评分
- 结果排序和分页
"""

import logging
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime, timedelta
import math

logger = logging.getLogger(__name__)

# 默认扫描标的池
DEFAULT_SCAN_UNIVERSE = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'AMD',
    'SPY', 'QQQ', 'IWM', 'DIA',
    'JPM', 'BAC', 'GS', 'V', 'MA',
    'XOM', 'CVX', 'PFE', 'JNJ', 'UNH',
    'NFLX', 'DIS', 'COIN', 'SQ', 'PYPL',
]

# 策略对应的扫描逻辑
SCAN_STRATEGIES = {
    'covered_call': {
        'name_cn': '备兑看涨',
        'option_type': 'call',
        'action': 'sell',
        'target_delta': 0.30,    # 30 delta OTM call
        'min_premium_yield': 0.5,  # 最低年化收益率 %
    },
    'cash_secured_put': {
        'name_cn': '现金担保看跌',
        'option_type': 'put',
        'action': 'sell',
        'target_delta': -0.25,
        'min_premium_yield': 0.5,
    },
    'bull_call_spread': {
        'name_cn': '牛市看涨价差',
        'option_type': 'call',
        'action': 'buy',
        'multi_leg': True,
    },
    'wheel': {
        'name_cn': 'Wheel 策略',
        'option_type': 'put',
        'action': 'sell',
        'target_delta': -0.30,
        'min_premium_yield': 1.0,
    },
}


@dataclass
class ScanFilter:
    """扫描筛选条件"""
    strategies: List[str] = field(default_factory=lambda: ['covered_call'])
    tickers: Optional[List[str]] = None       # None = 使用默认池
    market_cap: Optional[str] = None          # 'large', 'mid', 'small'
    iv_percentile_min: float = 0              # IV 百分位下限 (0-100)
    iv_percentile_max: float = 100            # IV 百分位上限
    min_yield_pct: float = 0                  # 最低年化收益率 %
    expiry_range: str = 'monthly'             # 'weekly', 'monthly', '30-60d'
    min_volume: int = 10                      # 最低成交量
    min_open_interest: int = 100              # 最低持仓量
    max_results: int = 50                     # 最大返回数量


@dataclass
class ScanResult:
    """单条扫描结果"""
    ticker: str
    strategy: str
    strategy_cn: str
    strike: float
    expiry: str
    expiry_days: int
    premium: float              # 权利金
    yield_pct: float            # 年化收益率 %
    iv_rank: Optional[float]    # IV Rank (0-100)
    delta: Optional[float]
    prob_otm: Optional[float]   # 到期 OTM 概率 %
    gbm_score: int              # GBM 综合评分 (0-100)
    underlying_price: float
    volume: int
    open_interest: int

    # 附加信息
    bid: Optional[float] = None
    ask: Optional[float] = None
    mid: Optional[float] = None
    spread_pct: Optional[float] = None  # 买卖价差百分比

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class OptionScanner:
    """期权机会扫描器"""

    def __init__(self):
        pass

    def scan(
        self,
        scan_filter: ScanFilter,
        chain_data_provider=None,
    ) -> Dict[str, Any]:
        """
        执行扫描

        Args:
            scan_filter: 筛选条件
            chain_data_provider: 期权链数据提供函数
                signature: (ticker: str) -> Dict[str, Any]
                返回: {'underlying_price': float, 'chains': [{...}]}

        Returns:
            {
                'results': [ScanResult],
                'total_matches': int,
                'scan_time_ms': int,
                'filters_applied': {...}
            }
        """
        import time
        start = time.time()

        tickers = scan_filter.tickers or DEFAULT_SCAN_UNIVERSE
        all_results = []

        for ticker in tickers:
            try:
                if chain_data_provider:
                    data = chain_data_provider(ticker)
                else:
                    # 无数据源时返回空
                    continue

                if not data:
                    continue

                underlying_price = data.get('underlying_price', 0)
                if underlying_price <= 0:
                    continue

                chains = data.get('chains', [])

                for strategy in scan_filter.strategies:
                    results = self._scan_single(
                        ticker, strategy, underlying_price,
                        chains, scan_filter
                    )
                    all_results.extend(results)

            except Exception as e:
                logger.warning(f"扫描 {ticker} 失败: {e}")
                continue

        # 按 GBM Score 排序
        all_results.sort(key=lambda r: r.gbm_score, reverse=True)

        # 限制结果数量
        total = len(all_results)
        all_results = all_results[:scan_filter.max_results]

        elapsed_ms = int((time.time() - start) * 1000)

        return {
            'results': [r.to_dict() for r in all_results],
            'total_matches': total,
            'scan_time_ms': elapsed_ms,
            'filters_applied': asdict(scan_filter),
        }

    def _scan_single(
        self,
        ticker: str,
        strategy: str,
        underlying_price: float,
        chains: List[Dict[str, Any]],
        scan_filter: ScanFilter,
    ) -> List[ScanResult]:
        """扫描单个标的的单个策略"""
        strategy_config = SCAN_STRATEGIES.get(strategy)
        if not strategy_config:
            return []

        results = []

        for chain in chains:
            expiry = chain.get('expiry', '')
            expiry_days = chain.get('expiry_days', 0)

            # 到期范围过滤
            if not self._check_expiry_range(expiry_days, scan_filter.expiry_range):
                continue

            options = chain.get('calls', []) if strategy_config['option_type'] == 'call' \
                else chain.get('puts', [])

            for opt in options:
                result = self._evaluate_option(
                    ticker, strategy, strategy_config,
                    underlying_price, opt, expiry, expiry_days,
                    scan_filter
                )
                if result:
                    results.append(result)

        return results

    def _evaluate_option(
        self,
        ticker: str,
        strategy: str,
        config: Dict,
        underlying_price: float,
        opt: Dict[str, Any],
        expiry: str,
        expiry_days: int,
        scan_filter: ScanFilter,
    ) -> Optional[ScanResult]:
        """评估单个期权是否符合条件"""

        strike = opt.get('strike', 0)
        if strike <= 0:
            return None

        # 基础数据
        bid = self._safe_float(opt.get('bid', 0))
        ask = self._safe_float(opt.get('ask', 0))
        volume = int(opt.get('volume', 0) or 0)
        oi = int(opt.get('openInterest', 0) or 0)
        delta = self._safe_float(opt.get('delta'))
        iv = self._safe_float(opt.get('impliedVolatility', opt.get('iv', 0)))

        # 流动性过滤
        if volume < scan_filter.min_volume:
            return None
        if oi < scan_filter.min_open_interest:
            return None

        # 中间价
        mid = (bid + ask) / 2 if bid and ask and bid > 0 and ask > 0 else \
            self._safe_float(opt.get('lastPrice', 0))
        if not mid or mid <= 0:
            return None

        # 收益率计算
        if config['action'] == 'sell' and expiry_days > 0:
            # 卖方收益率：年化 premium yield
            if config['option_type'] == 'put':
                capital = strike  # 需要的现金担保
            else:
                capital = underlying_price  # 持有标的

            yield_pct = (mid / capital) * (365 / expiry_days) * 100
        else:
            yield_pct = 0

        # 收益率过滤
        if yield_pct < scan_filter.min_yield_pct:
            return None

        # IV 过滤（简化版：用 IV 值近似 percentile）
        iv_rank = None
        if iv:
            # 粗略估计：IV rank 基于该股票的典型 IV 范围
            iv_rank = min(100, max(0, iv * 100 * 2))  # 简化近似

        if iv_rank is not None:
            if iv_rank < scan_filter.iv_percentile_min or iv_rank > scan_filter.iv_percentile_max:
                return None

        # OTM 概率估算
        prob_otm = None
        if delta is not None:
            prob_otm = round(abs(1 - abs(delta)) * 100, 1)

        # GBM Score 计算（综合评分）
        gbm_score = self._calculate_gbm_score(
            yield_pct=yield_pct,
            iv_rank=iv_rank,
            prob_otm=prob_otm,
            volume=volume,
            oi=oi,
            bid=bid,
            ask=ask,
            strategy=strategy,
        )

        # 买卖价差
        spread_pct = None
        if bid and ask and mid > 0:
            spread_pct = round((ask - bid) / mid * 100, 2)

        return ScanResult(
            ticker=ticker,
            strategy=strategy,
            strategy_cn=config['name_cn'],
            strike=strike,
            expiry=expiry,
            expiry_days=expiry_days,
            premium=round(mid, 2),
            yield_pct=round(yield_pct, 1),
            iv_rank=round(iv_rank, 1) if iv_rank else None,
            delta=round(delta, 3) if delta else None,
            prob_otm=prob_otm,
            gbm_score=gbm_score,
            underlying_price=round(underlying_price, 2),
            volume=volume,
            open_interest=oi,
            bid=round(bid, 2) if bid else None,
            ask=round(ask, 2) if ask else None,
            mid=round(mid, 2),
            spread_pct=spread_pct,
        )

    def _calculate_gbm_score(
        self,
        yield_pct: float,
        iv_rank: Optional[float],
        prob_otm: Optional[float],
        volume: int,
        oi: int,
        bid: Optional[float],
        ask: Optional[float],
        strategy: str,
    ) -> int:
        """计算 GBM 综合评分 (0-100)"""
        score = 0.0

        # 收益率得分 (30%)
        yield_score = min(100, yield_pct * 5)  # 20% 年化 = 满分
        score += yield_score * 0.30

        # IV Rank 得分 (20%) - 卖方策略偏好高 IV
        if iv_rank is not None:
            if strategy in ('covered_call', 'cash_secured_put', 'wheel'):
                iv_score = iv_rank  # 高 IV 对卖方有利
            else:
                iv_score = 100 - iv_rank  # 低 IV 对买方有利
            score += iv_score * 0.20

        # OTM 概率得分 (20%)
        if prob_otm is not None:
            prob_score = min(100, prob_otm * 1.3)  # 77% OTM = 满分
            score += prob_score * 0.20

        # 流动性得分 (15%)
        vol_score = min(100, math.log10(max(volume, 1)) / 4 * 100)
        oi_score = min(100, math.log10(max(oi, 1)) / 5 * 100)
        liq_score = (vol_score + oi_score) / 2
        score += liq_score * 0.15

        # 买卖价差得分 (15%)
        if bid and ask and ask > 0:
            spread = (ask - bid) / ((bid + ask) / 2) * 100
            spread_score = max(0, 100 - spread * 10)  # 10% 价差 = 0 分
            score += spread_score * 0.15

        return min(100, max(0, int(round(score))))

    def _check_expiry_range(self, expiry_days: int, range_type: str) -> bool:
        """检查到期日是否在指定范围内"""
        if range_type == 'weekly':
            return 1 <= expiry_days <= 7
        elif range_type == 'monthly':
            return 20 <= expiry_days <= 45
        elif range_type == '30-60d':
            return 30 <= expiry_days <= 60
        return True  # 默认不过滤

    def _safe_float(self, val) -> float:
        """安全转 float"""
        try:
            return float(val) if val is not None else 0.0
        except (ValueError, TypeError):
            return 0.0

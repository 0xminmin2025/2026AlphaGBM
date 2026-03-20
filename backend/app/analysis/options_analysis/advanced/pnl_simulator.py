"""
P/L 场景模拟引擎

功能：
- 多维度 P/L 模拟（价格 × 时间 × IV）
- Bull/Base/Bear 三场景对比
- 概率分析（基于对数正态分布）
- 期望收益计算
- Greeks 热力图数据
"""

import math
import logging
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional
import numpy as np
from scipy.stats import norm, lognorm

from ..core.greeks_calculator import BlackScholesCalculator, OptionLeg

logger = logging.getLogger(__name__)

CALENDAR_DAYS_PER_YEAR = 365


@dataclass
class ScenarioResult:
    """单个场景的结果"""
    name: str               # 'bull', 'base', 'bear'
    name_cn: str             # '看涨', '基准', '看跌'
    price_change_pct: float  # 价格变动百分比
    target_price: float      # 目标价格
    pnl: float               # 盈亏金额
    pnl_pct: float           # 盈亏百分比（相对于净成本）
    probability: float       # 发生概率

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SimulationResult:
    """P/L 模拟完整结果"""
    # 基础信息
    symbol: str
    spot: float
    total_days: int          # 距到期总天数

    # P/L 曲线
    prices: List[float] = field(default_factory=list)
    pnl_at_expiry: List[float] = field(default_factory=list)
    pnl_today: List[float] = field(default_factory=list)
    pnl_future: Optional[List[float]] = None
    future_day: Optional[int] = None

    # 盈亏平衡
    breakevens: List[float] = field(default_factory=list)
    max_profit: float = 0.0
    max_loss: float = 0.0
    net_cost: float = 0.0

    # 场景分析
    scenarios: List[ScenarioResult] = field(default_factory=list)

    # 概率指标
    probability_of_profit: float = 0.0
    expected_value: float = 0.0
    risk_reward_ratio: float = 0.0
    implied_move: float = 0.0   # 隐含波动幅度

    # Greeks 热力图（价格 × IV）
    greeks_heatmap: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PnLSimulator:
    """P/L 场景模拟器"""

    def __init__(self, risk_free_rate: float = 0.05):
        self.bs = BlackScholesCalculator(risk_free_rate=risk_free_rate)
        self.r = risk_free_rate

    def simulate(
        self,
        legs: List[OptionLeg],
        spot: float,
        symbol: str = '',
        future_day: Optional[int] = None,
        iv_shift: float = 0.0,
        price_range_pct: float = 0.20,
        num_points: int = 100,
        scenarios: Optional[List[Dict[str, float]]] = None,
    ) -> SimulationResult:
        """
        运行完整的 P/L 模拟

        Args:
            legs: 期权腿
            spot: 当前标的价格
            symbol: 标的代码
            future_day: 未来某天（0 = 今天，None = 到期日）
            iv_shift: IV 整体偏移
            price_range_pct: 价格范围百分比（默认 ±20%）
            num_points: 价格点数
            scenarios: 自定义场景 [{'name': 'bull', 'pct': 0.10}, ...]

        Returns:
            SimulationResult
        """
        if not legs:
            raise ValueError("至少需要一个期权腿")

        total_days = max(leg.expiry_days for leg in legs)

        # 基础 P/L 曲线
        price_range = (spot * (1 - price_range_pct), spot * (1 + price_range_pct))
        pnl_data = self.bs.calculate_pnl_curve(
            legs, spot,
            price_range=price_range,
            num_points=num_points,
            future_days=future_day,
            iv_shift=iv_shift
        )

        result = SimulationResult(
            symbol=symbol,
            spot=spot,
            total_days=total_days,
            prices=pnl_data['prices'],
            pnl_at_expiry=pnl_data['pnl_at_expiry'],
            pnl_today=pnl_data['pnl_current'],
            pnl_future=pnl_data['pnl_future'],
            future_day=future_day,
            breakevens=pnl_data['breakevens'],
            max_profit=pnl_data['max_profit'],
            max_loss=pnl_data['max_loss'],
            net_cost=pnl_data['net_cost'],
        )

        # 隐含波动幅度
        avg_iv = self._avg_iv(legs)
        result.implied_move = round(
            spot * avg_iv * math.sqrt(total_days / CALENDAR_DAYS_PER_YEAR), 2
        )

        # 场景分析
        if scenarios is None:
            scenarios = [
                {'name': 'bull', 'name_cn': '看涨', 'pct': 0.10},
                {'name': 'base', 'name_cn': '基准', 'pct': 0.00},
                {'name': 'bear', 'name_cn': '看跌', 'pct': -0.10},
            ]

        result.scenarios = self._run_scenarios(legs, spot, total_days, avg_iv, scenarios)

        # 概率分析
        prob_data = self._calculate_probabilities(
            legs, spot, total_days, avg_iv, pnl_data
        )
        result.probability_of_profit = prob_data['prob_profit']
        result.expected_value = prob_data['expected_value']
        result.risk_reward_ratio = prob_data['risk_reward']

        return result

    def generate_greeks_heatmap(
        self,
        legs: List[OptionLeg],
        spot: float,
        price_steps: int = 11,
        iv_steps: int = 7,
        price_range_pct: float = 0.10,
        iv_range: float = 0.10,
    ) -> Dict[str, Any]:
        """
        生成 Greeks 热力图数据（价格 × IV 维度）

        Returns:
            {
                'prices': [...],
                'ivs': [...],
                'delta_grid': [[...]],
                'gamma_grid': [[...]],
                'theta_grid': [[...]],
                'pnl_grid': [[...]],
            }
        """
        prices = np.linspace(
            spot * (1 - price_range_pct),
            spot * (1 + price_range_pct),
            price_steps
        )

        base_iv = self._avg_iv(legs)
        ivs = np.linspace(
            max(0.01, base_iv - iv_range),
            base_iv + iv_range,
            iv_steps
        )

        delta_grid = []
        theta_grid = []
        pnl_grid = []

        for iv_val in ivs:
            delta_row = []
            theta_row = []
            pnl_row = []

            for price in prices:
                total_delta = 0.0
                total_theta = 0.0
                total_pnl = 0.0

                for leg in legs:
                    T = leg.expiry_days / CALENDAR_DAYS_PER_YEAR
                    sign = 1 if leg.action == 'buy' else -1
                    qty = leg.quantity * leg.multiplier

                    d = self.bs.delta(price, leg.strike, T, iv_val, leg.option_type)
                    t = self.bs.theta(price, leg.strike, T, iv_val, leg.option_type)
                    current_p = self.bs.bs_price(price, leg.strike, T, iv_val, leg.option_type)

                    entry_iv = leg.iv or 0.25
                    entry_p = leg.premium or self.bs.bs_price(
                        spot, leg.strike, T, entry_iv, leg.option_type
                    )

                    total_delta += d * sign * qty
                    total_theta += t * sign * qty
                    total_pnl += (current_p - entry_p) * sign * qty

                delta_row.append(round(float(total_delta), 2))
                theta_row.append(round(float(total_theta), 2))
                pnl_row.append(round(float(total_pnl), 2))

            delta_grid.append(delta_row)
            theta_grid.append(theta_row)
            pnl_grid.append(pnl_row)

        return {
            'prices': [round(float(p), 2) for p in prices],
            'ivs': [round(float(iv) * 100, 1) for iv in ivs],
            'delta_grid': delta_grid,
            'theta_grid': theta_grid,
            'pnl_grid': pnl_grid,
        }

    # ─────────────────────────────────────
    # 内部方法
    # ─────────────────────────────────────

    def _avg_iv(self, legs: List[OptionLeg]) -> float:
        """计算加权平均 IV"""
        ivs = [leg.iv for leg in legs if leg.iv]
        return sum(ivs) / len(ivs) if ivs else 0.25

    def _run_scenarios(
        self,
        legs: List[OptionLeg],
        spot: float,
        total_days: int,
        avg_iv: float,
        scenarios: List[Dict],
    ) -> List[ScenarioResult]:
        """运行场景分析"""
        results = []

        for sc in scenarios:
            pct = sc['pct']
            target = spot * (1 + pct)

            # 到期日 P/L
            pnl = 0.0
            cost = 0.0
            for leg in legs:
                sign = 1 if leg.action == 'buy' else -1
                iv = leg.iv or 0.25

                entry = leg.premium or self.bs.bs_price(
                    spot, leg.strike,
                    leg.expiry_days / CALENDAR_DAYS_PER_YEAR,
                    iv, leg.option_type
                )

                if leg.option_type == 'call':
                    payoff = max(target - leg.strike, 0)
                else:
                    payoff = max(leg.strike - target, 0)

                pnl += (payoff - entry) * sign * leg.quantity * leg.multiplier
                cost += entry * abs(sign) * leg.quantity * leg.multiplier

            # 概率（对数正态分布）
            T = total_days / CALENDAR_DAYS_PER_YEAR
            if T > 0 and avg_iv > 0:
                d = (math.log(target / spot) - (self.r - 0.5 * avg_iv**2) * T) / (avg_iv * math.sqrt(T))
                # P(S > target) 的概率
                prob = float(norm.cdf(-d)) if pct > 0 else float(norm.cdf(d))
            else:
                prob = 0.5

            pnl_pct = (pnl / abs(cost) * 100) if cost != 0 else 0

            results.append(ScenarioResult(
                name=sc['name'],
                name_cn=sc.get('name_cn', sc['name']),
                price_change_pct=round(pct * 100, 1),
                target_price=round(target, 2),
                pnl=round(pnl, 2),
                pnl_pct=round(pnl_pct, 1),
                probability=round(prob * 100, 1),
            ))

        return results

    def _calculate_probabilities(
        self,
        legs: List[OptionLeg],
        spot: float,
        total_days: int,
        avg_iv: float,
        pnl_data: Dict[str, Any],
    ) -> Dict[str, float]:
        """计算概率指标"""
        T = total_days / CALENDAR_DAYS_PER_YEAR

        if T <= 0 or avg_iv <= 0:
            return {'prob_profit': 50.0, 'expected_value': 0.0, 'risk_reward': 1.0}

        # 蒙特卡洛概率（轻量版，1000 路径）
        np.random.seed(42)
        num_paths = 1000
        z = np.random.standard_normal(num_paths)
        future_prices = spot * np.exp(
            (self.r - 0.5 * avg_iv**2) * T + avg_iv * math.sqrt(T) * z
        )

        pnls = []
        for fp in future_prices:
            pnl = 0.0
            for leg in legs:
                sign = 1 if leg.action == 'buy' else -1
                iv = leg.iv or 0.25
                entry = leg.premium or self.bs.bs_price(
                    spot, leg.strike,
                    leg.expiry_days / CALENDAR_DAYS_PER_YEAR,
                    iv, leg.option_type
                )
                if leg.option_type == 'call':
                    payoff = max(fp - leg.strike, 0)
                else:
                    payoff = max(leg.strike - fp, 0)
                pnl += (payoff - entry) * sign * leg.quantity * leg.multiplier
            pnls.append(pnl)

        pnls = np.array(pnls)
        prob_profit = float(np.mean(pnls > 0) * 100)
        expected_value = float(np.mean(pnls))

        max_p = pnl_data.get('max_profit', 1)
        max_l = abs(pnl_data.get('max_loss', -1))
        risk_reward = round(max_l / max_p, 1) if max_p > 0 else 99.9

        return {
            'prob_profit': round(prob_profit, 1),
            'expected_value': round(expected_value, 2),
            'risk_reward': risk_reward,
        }

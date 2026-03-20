"""
Black-Scholes 期权定价与 Greeks 计算引擎

提供完整的期权分析基础设施：
- BS 公式定价（欧式期权）
- 全套 Greeks 解析解（Delta, Gamma, Theta, Vega, Rho）
- 隐含波动率反求（Newton-Raphson + Bisection 混合）
- 多腿组合 Greeks 聚合
- P/L 曲线计算
"""

import math
import logging
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional, Literal
from scipy.stats import norm
import numpy as np

logger = logging.getLogger(__name__)

# 常量
TRADING_DAYS_PER_YEAR = 252
CALENDAR_DAYS_PER_YEAR = 365
DEFAULT_RISK_FREE_RATE = 0.05  # 5% 美国无风险利率
IV_PRECISION = 1e-6
IV_MAX_ITERATIONS = 100
IV_UPPER_BOUND = 5.0  # 500% IV 上限
IV_LOWER_BOUND = 0.001  # 0.1% IV 下限


@dataclass
class GreeksResult:
    """单个期权的 Greeks 计算结果"""
    # 定价
    price: float              # 理论价格
    intrinsic: float          # 内在价值
    time_value: float         # 时间价值

    # Greeks
    delta: float              # Delta: 价格敏感度 (-1 ~ 1)
    gamma: float              # Gamma: Delta 变化率
    theta: float              # Theta: 每日时间衰减 (负值)
    vega: float               # Vega: 波动率敏感度 (每1%变动)
    rho: float                # Rho: 利率敏感度 (每1%变动)

    # 元数据
    option_type: str           # 'call' 或 'put'
    spot: float               # 标的价格
    strike: float             # 行权价
    expiry_days: int          # 到期天数
    iv: float                 # 隐含波动率
    risk_free_rate: float     # 无风险利率

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class OptionLeg:
    """期权腿定义"""
    option_type: Literal['call', 'put']
    strike: float
    expiry_days: int
    action: Literal['buy', 'sell']
    quantity: int = 1
    iv: Optional[float] = None           # 隐含波动率，None 则使用市场数据
    premium: Optional[float] = None      # 实际市场价格
    multiplier: int = 100                # 合约乘数


@dataclass
class StrategyGreeks:
    """多腿策略的聚合 Greeks"""
    # 聚合 Greeks
    delta: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0          # 每日
    vega: float = 0.0           # 每1% IV变动
    rho: float = 0.0

    # 策略概要
    net_cost: float = 0.0       # 净成本（正=借方，负=贷方）
    max_profit: float = 0.0
    max_loss: float = 0.0
    breakevens: List[float] = field(default_factory=list)

    # 各腿明细
    legs: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BlackScholesCalculator:
    """
    Black-Scholes 期权定价与 Greeks 计算器

    所有 Greeks 使用解析解（closed-form），计算效率高。
    支持欧式期权（美式期权用欧式近似，对无分红标的足够准确）。
    """

    def __init__(self, risk_free_rate: float = DEFAULT_RISK_FREE_RATE):
        self.r = risk_free_rate

    # ─────────────────────────────────────
    # 核心 BS 公式
    # ─────────────────────────────────────

    @staticmethod
    def _d1(S: float, K: float, T: float, r: float, sigma: float) -> float:
        """计算 d1 参数"""
        if T <= 0 or sigma <= 0:
            return 0.0
        return (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))

    @staticmethod
    def _d2(S: float, K: float, T: float, r: float, sigma: float) -> float:
        """计算 d2 参数"""
        if T <= 0 or sigma <= 0:
            return 0.0
        return BlackScholesCalculator._d1(S, K, T, r, sigma) - sigma * math.sqrt(T)

    def bs_price(self, S: float, K: float, T: float, sigma: float,
                 option_type: str = 'call') -> float:
        """
        Black-Scholes 期权理论价格

        Args:
            S: 标的资产价格
            K: 行权价
            T: 到期时间（年化，如 30天 = 30/365）
            sigma: 隐含波动率（如 0.25 = 25%）
            option_type: 'call' 或 'put'

        Returns:
            期权理论价格
        """
        if T <= 0:
            # 已到期
            if option_type == 'call':
                return max(S - K, 0)
            else:
                return max(K - S, 0)

        d1 = self._d1(S, K, T, self.r, sigma)
        d2 = self._d2(S, K, T, self.r, sigma)

        if option_type == 'call':
            return S * norm.cdf(d1) - K * math.exp(-self.r * T) * norm.cdf(d2)
        else:
            return K * math.exp(-self.r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)

    # ─────────────────────────────────────
    # Greeks 解析解
    # ─────────────────────────────────────

    def delta(self, S: float, K: float, T: float, sigma: float,
              option_type: str = 'call') -> float:
        """Delta: 标的价格变动 $1 时期权价格的变动量"""
        if T <= 0:
            if option_type == 'call':
                return 1.0 if S > K else 0.0
            else:
                return -1.0 if S < K else 0.0

        d1 = self._d1(S, K, T, self.r, sigma)
        if option_type == 'call':
            return norm.cdf(d1)
        else:
            return norm.cdf(d1) - 1.0

    def gamma(self, S: float, K: float, T: float, sigma: float) -> float:
        """Gamma: Delta 对标的价格的变化率（Call 和 Put 相同）"""
        if T <= 0 or sigma <= 0 or S <= 0:
            return 0.0

        d1 = self._d1(S, K, T, self.r, sigma)
        return norm.pdf(d1) / (S * sigma * math.sqrt(T))

    def theta(self, S: float, K: float, T: float, sigma: float,
              option_type: str = 'call') -> float:
        """
        Theta: 每日时间衰减（负值表示每天亏损的时间价值）

        返回值为每 *日历日* 的衰减量
        """
        if T <= 0:
            return 0.0

        d1 = self._d1(S, K, T, self.r, sigma)
        d2 = self._d2(S, K, T, self.r, sigma)
        sqrt_T = math.sqrt(T)

        # 第一项：波动率衰减（Call/Put 相同）
        term1 = -(S * norm.pdf(d1) * sigma) / (2 * sqrt_T)

        if option_type == 'call':
            term2 = -self.r * K * math.exp(-self.r * T) * norm.cdf(d2)
        else:
            term2 = self.r * K * math.exp(-self.r * T) * norm.cdf(-d2)

        # 返回每日历日
        return (term1 + term2) / CALENDAR_DAYS_PER_YEAR

    def vega(self, S: float, K: float, T: float, sigma: float) -> float:
        """
        Vega: IV 变动 1 个百分点时期权价格的变动量

        例如 IV 从 25% 变到 26%，期权价格变动 vega 的值
        Call 和 Put 的 Vega 相同
        """
        if T <= 0:
            return 0.0

        d1 = self._d1(S, K, T, self.r, sigma)
        # 除以 100 使结果表示 "每1个百分点" 的变动
        return S * norm.pdf(d1) * math.sqrt(T) / 100

    def rho(self, S: float, K: float, T: float, sigma: float,
            option_type: str = 'call') -> float:
        """
        Rho: 无风险利率变动 1 个百分点时期权价格的变动量
        """
        if T <= 0:
            return 0.0

        d2 = self._d2(S, K, T, self.r, sigma)

        if option_type == 'call':
            return K * T * math.exp(-self.r * T) * norm.cdf(d2) / 100
        else:
            return -K * T * math.exp(-self.r * T) * norm.cdf(-d2) / 100

    # ─────────────────────────────────────
    # 综合计算
    # ─────────────────────────────────────

    def calculate(self, S: float, K: float, expiry_days: int, sigma: float,
                  option_type: str = 'call') -> GreeksResult:
        """
        一次性计算期权价格 + 全套 Greeks

        Args:
            S: 标的价格
            K: 行权价
            expiry_days: 到期天数
            sigma: 隐含波动率
            option_type: 'call' 或 'put'

        Returns:
            GreeksResult 包含价格和全套 Greeks
        """
        T = expiry_days / CALENDAR_DAYS_PER_YEAR

        price = self.bs_price(S, K, T, sigma, option_type)

        # 内在价值
        if option_type == 'call':
            intrinsic = max(S - K, 0)
        else:
            intrinsic = max(K - S, 0)

        return GreeksResult(
            price=round(price, 4),
            intrinsic=round(intrinsic, 4),
            time_value=round(price - intrinsic, 4),
            delta=round(self.delta(S, K, T, sigma, option_type), 4),
            gamma=round(self.gamma(S, K, T, sigma), 6),
            theta=round(self.theta(S, K, T, sigma, option_type), 4),
            vega=round(self.vega(S, K, T, sigma), 4),
            rho=round(self.rho(S, K, T, sigma, option_type), 4),
            option_type=option_type,
            spot=S,
            strike=K,
            expiry_days=expiry_days,
            iv=round(sigma, 4),
            risk_free_rate=self.r
        )

    # ─────────────────────────────────────
    # 隐含波动率反求
    # ─────────────────────────────────────

    def implied_volatility(self, market_price: float, S: float, K: float,
                           expiry_days: int, option_type: str = 'call') -> Optional[float]:
        """
        从市场价格反求隐含波动率（Newton-Raphson + Bisection 混合法）

        Args:
            market_price: 期权市场价格
            S: 标的价格
            K: 行权价
            expiry_days: 到期天数
            option_type: 'call' 或 'put'

        Returns:
            隐含波动率，或 None（无法收敛）
        """
        T = expiry_days / CALENDAR_DAYS_PER_YEAR

        if T <= 0:
            return None

        # 边界检查
        if option_type == 'call':
            intrinsic = max(S - K * math.exp(-self.r * T), 0)
        else:
            intrinsic = max(K * math.exp(-self.r * T) - S, 0)

        if market_price < intrinsic:
            return None  # 价格低于内在价值，无解

        # 初始猜测：使用 Brenner-Subrahmanyam 近似
        sigma = math.sqrt(2 * math.pi / T) * market_price / S

        # 限制初始猜测范围
        sigma = max(IV_LOWER_BOUND, min(sigma, IV_UPPER_BOUND))

        # Newton-Raphson 迭代
        for i in range(IV_MAX_ITERATIONS):
            price = self.bs_price(S, K, T, sigma, option_type)
            diff = price - market_price

            if abs(diff) < IV_PRECISION:
                return round(sigma, 6)

            # Vega（未归一化的，用于 Newton 步长）
            d1 = self._d1(S, K, T, self.r, sigma)
            vega_raw = S * norm.pdf(d1) * math.sqrt(T)

            if vega_raw < 1e-12:
                break  # Vega 太小，Newton 法不稳定，切换 bisection

            sigma -= diff / vega_raw
            sigma = max(IV_LOWER_BOUND, min(sigma, IV_UPPER_BOUND))

        # Newton 未收敛，使用 Bisection 兜底
        lo, hi = IV_LOWER_BOUND, IV_UPPER_BOUND
        for _ in range(IV_MAX_ITERATIONS):
            mid = (lo + hi) / 2
            price = self.bs_price(S, K, T, mid, option_type)
            diff = price - market_price

            if abs(diff) < IV_PRECISION:
                return round(mid, 6)

            if diff > 0:
                hi = mid
            else:
                lo = mid

        logger.warning(
            f"IV 未收敛: S={S}, K={K}, T={T:.4f}, price={market_price}, type={option_type}"
        )
        return round((lo + hi) / 2, 6)

    # ─────────────────────────────────────
    # P/L 曲线计算
    # ─────────────────────────────────────

    def calculate_pnl_curve(
        self,
        legs: List[OptionLeg],
        spot: float,
        price_range: Optional[tuple] = None,
        num_points: int = 100,
        future_days: Optional[int] = None,
        iv_shift: float = 0.0
    ) -> Dict[str, Any]:
        """
        计算多腿策略在不同标的价格下的 P/L 曲线

        Args:
            legs: 期权腿列表
            spot: 当前标的价格
            price_range: (min_price, max_price)，默认 spot ± 20%
            num_points: 价格点数量
            future_days: 未来某一天的 P/L（None = 到期日）
            iv_shift: IV 整体偏移（如 +0.05 = IV 上升5个百分点）

        Returns:
            {
                'prices': [...],           # 标的价格序列
                'pnl_at_expiry': [...],     # 到期日 P/L
                'pnl_current': [...],       # 当前 P/L（含时间价值）
                'pnl_future': [...],        # 未来某天 P/L
                'breakevens': [...],        # 盈亏平衡点
                'max_profit': float,
                'max_loss': float,
                'net_cost': float
            }
        """
        if not price_range:
            price_range = (spot * 0.8, spot * 1.2)

        prices = np.linspace(price_range[0], price_range[1], num_points)

        # 计算各腿的入场成本
        net_cost = 0.0
        leg_entries = []

        for leg in legs:
            T_entry = leg.expiry_days / CALENDAR_DAYS_PER_YEAR
            iv = leg.iv if leg.iv else 0.25  # 默认 25% IV

            if leg.premium is not None:
                entry_price = leg.premium
            else:
                entry_price = self.bs_price(spot, leg.strike, T_entry, iv, leg.option_type)

            sign = 1 if leg.action == 'buy' else -1
            net_cost += sign * entry_price * leg.quantity * leg.multiplier

            leg_entries.append({
                'leg': leg,
                'entry_price': entry_price,
                'iv': iv,
                'sign': sign
            })

        # 到期日 P/L
        pnl_expiry = np.zeros(num_points)
        for entry in leg_entries:
            leg = entry['leg']
            sign = entry['sign']
            ep = entry['entry_price']

            for i, p in enumerate(prices):
                if leg.option_type == 'call':
                    payoff = max(p - leg.strike, 0)
                else:
                    payoff = max(leg.strike - p, 0)

                pnl_expiry[i] += (payoff - ep) * sign * leg.quantity * leg.multiplier

        # 当前 P/L（当前时间点，含时间价值）
        pnl_current = np.zeros(num_points)
        for entry in leg_entries:
            leg = entry['leg']
            sign = entry['sign']
            ep = entry['entry_price']
            iv = entry['iv'] + iv_shift
            T = leg.expiry_days / CALENDAR_DAYS_PER_YEAR

            for i, p in enumerate(prices):
                current_price = self.bs_price(p, leg.strike, T, max(iv, 0.001), leg.option_type)
                pnl_current[i] += (current_price - ep) * sign * leg.quantity * leg.multiplier

        # 未来某天 P/L
        pnl_future = None
        if future_days is not None:
            pnl_future = np.zeros(num_points)
            for entry in leg_entries:
                leg = entry['leg']
                sign = entry['sign']
                ep = entry['entry_price']
                iv = entry['iv'] + iv_shift
                remaining = max(leg.expiry_days - future_days, 0)
                T_future = remaining / CALENDAR_DAYS_PER_YEAR

                for i, p in enumerate(prices):
                    if remaining <= 0:
                        if leg.option_type == 'call':
                            future_price = max(p - leg.strike, 0)
                        else:
                            future_price = max(leg.strike - p, 0)
                    else:
                        future_price = self.bs_price(
                            p, leg.strike, T_future, max(iv, 0.001), leg.option_type
                        )
                    pnl_future[i] += (future_price - ep) * sign * leg.quantity * leg.multiplier

        # 找盈亏平衡点
        breakevens = []
        for i in range(len(prices) - 1):
            if pnl_expiry[i] * pnl_expiry[i + 1] < 0:
                # 线性插值
                ratio = abs(pnl_expiry[i]) / (abs(pnl_expiry[i]) + abs(pnl_expiry[i + 1]))
                be = prices[i] + ratio * (prices[i + 1] - prices[i])
                breakevens.append(round(float(be), 2))

        return {
            'prices': [round(float(p), 2) for p in prices],
            'pnl_at_expiry': [round(float(p), 2) for p in pnl_expiry],
            'pnl_current': [round(float(p), 2) for p in pnl_current],
            'pnl_future': [round(float(p), 2) for p in pnl_future] if pnl_future is not None else None,
            'breakevens': breakevens,
            'max_profit': round(float(np.max(pnl_expiry)), 2),
            'max_loss': round(float(np.min(pnl_expiry)), 2),
            'net_cost': round(net_cost, 2),
        }

    # ─────────────────────────────────────
    # 多腿 Greeks 聚合
    # ─────────────────────────────────────

    def calculate_strategy_greeks(
        self, legs: List[OptionLeg], spot: float
    ) -> StrategyGreeks:
        """
        计算多腿策略的聚合 Greeks

        Args:
            legs: 期权腿列表
            spot: 当前标的价格

        Returns:
            StrategyGreeks 包含聚合 Greeks 和各腿明细
        """
        result = StrategyGreeks()
        net_cost = 0.0

        for leg in legs:
            iv = leg.iv if leg.iv else 0.25
            greeks = self.calculate(spot, leg.strike, leg.expiry_days, iv, leg.option_type)

            sign = 1 if leg.action == 'buy' else -1
            qty = leg.quantity

            # 入场成本
            price = leg.premium if leg.premium else greeks.price
            net_cost += sign * price * qty * leg.multiplier

            # 聚合 Greeks（按合约乘数和数量缩放）
            result.delta += greeks.delta * sign * qty * leg.multiplier
            result.gamma += greeks.gamma * sign * qty * leg.multiplier
            result.theta += greeks.theta * sign * qty * leg.multiplier
            result.vega += greeks.vega * sign * qty * leg.multiplier
            result.rho += greeks.rho * sign * qty * leg.multiplier

            # 记录各腿明细
            result.legs.append({
                'action': leg.action,
                'option_type': leg.option_type,
                'strike': leg.strike,
                'expiry_days': leg.expiry_days,
                'quantity': qty,
                'entry_price': round(price, 4),
                'delta': round(greeks.delta * sign, 4),
                'gamma': round(greeks.gamma * sign, 6),
                'theta': round(greeks.theta * sign, 4),
                'vega': round(greeks.vega * sign, 4),
                'rho': round(greeks.rho * sign, 4),
                'iv': round(iv, 4),
            })

        result.delta = round(result.delta, 2)
        result.gamma = round(result.gamma, 4)
        result.theta = round(result.theta, 2)
        result.vega = round(result.vega, 2)
        result.rho = round(result.rho, 2)
        result.net_cost = round(net_cost, 2)

        # 计算 P/L 边界来填充 max_profit, max_loss, breakevens
        pnl = self.calculate_pnl_curve(legs, spot)
        result.max_profit = pnl['max_profit']
        result.max_loss = pnl['max_loss']
        result.breakevens = pnl['breakevens']

        return result

    # ─────────────────────────────────────
    # 批量计算（期权链）
    # ─────────────────────────────────────

    def calculate_chain_greeks(
        self,
        spot: float,
        chain_data: List[Dict[str, Any]],
        expiry_days: int
    ) -> List[Dict[str, Any]]:
        """
        为整条期权链计算 Greeks（用于波动率微笑等可视化）

        Args:
            spot: 标的价格
            chain_data: [{'strike': 150, 'call_iv': 0.25, 'put_iv': 0.22, ...}, ...]
            expiry_days: 到期天数

        Returns:
            补充了 Greeks 的 chain_data
        """
        results = []
        for row in chain_data:
            strike = row['strike']
            entry = {'strike': strike}

            # Call Greeks
            call_iv = row.get('call_iv')
            if call_iv and call_iv > 0:
                call_greeks = self.calculate(spot, strike, expiry_days, call_iv, 'call')
                entry['call'] = call_greeks.to_dict()
            else:
                entry['call'] = None

            # Put Greeks
            put_iv = row.get('put_iv')
            if put_iv and put_iv > 0:
                put_greeks = self.calculate(spot, strike, expiry_days, put_iv, 'put')
                entry['put'] = put_greeks.to_dict()
            else:
                entry['put'] = None

            results.append(entry)

        return results

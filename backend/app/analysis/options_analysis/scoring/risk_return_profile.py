"""
期权风险收益风格标签系统
为每个期权提供一目了然的风格分类和关键指标
"""

import logging
import math
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class RiskReturnProfile:
    """风险收益风格标签"""
    # 核心标签
    style: str                    # 'steady_income', 'high_risk_high_reward', 'balanced', 'hedge'
    style_label: str              # 中英双语标签
    style_label_cn: str           # 纯中文标签
    style_label_en: str           # 纯英文标签

    # 风险等级
    risk_level: str               # 'low', 'moderate', 'high', 'very_high'
    risk_color: str               # 前端显示颜色: 'green', 'yellow', 'orange', 'red'

    # 关键指标
    max_loss_pct: float           # 最大亏损百分比
    max_profit_pct: float         # 最大收益百分比
    win_probability: float        # 胜率估算 (0-1)
    risk_reward_ratio: float      # 风险收益比 (收益/风险)

    # 摘要
    summary: str                  # 一句话总结
    summary_cn: str               # 中文总结

    # 额外信息
    strategy_type: str            # 'buyer' or 'seller'
    time_decay_impact: str        # 'positive', 'negative', 'neutral'
    volatility_impact: str        # 'positive', 'negative', 'neutral'

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


# 风格定义常量
STYLE_DEFINITIONS = {
    'steady_income': {
        'label': '稳健收益 / STEADY INCOME',
        'label_cn': '稳健收益',
        'label_en': 'STEADY INCOME',
        'description': '高胜率，收益有限但稳定',
        'typical_win_rate': (0.65, 0.80),
        'typical_return': (0.01, 0.05),  # 月收益1-5%
    },
    'high_risk_high_reward': {
        'label': '高风险高收益 / HIGH RISK HIGH REWARD',
        'label_cn': '高风险高收益',
        'label_en': 'HIGH RISK HIGH REWARD',
        'description': '低胜率，但潜在收益巨大',
        'typical_win_rate': (0.20, 0.40),
        'typical_return': (2.0, 10.0),  # 2-10倍收益
    },
    'balanced': {
        'label': '稳中求进 / BALANCED',
        'label_cn': '稳中求进',
        'label_en': 'BALANCED',
        'description': '风险收益均衡',
        'typical_win_rate': (0.40, 0.55),
        'typical_return': (0.5, 2.0),  # 50%-200%收益
    },
    'hedge': {
        'label': '保护对冲 / HEDGE',
        'label_cn': '保护对冲',
        'label_en': 'HEDGE',
        'description': '保险性质，下跌保护',
        'typical_win_rate': (0.30, 0.50),
        'typical_return': (0.0, 1.0),  # 对冲收益
    }
}

# 风险等级颜色映射
RISK_COLORS = {
    'low': 'green',
    'moderate': 'yellow',
    'high': 'orange',
    'very_high': 'red'
}


def calculate_risk_return_profile(
    option: Dict[str, Any],
    stock_data: Dict[str, Any],
    strategy: str,
    vrp_analysis: Optional[Dict[str, Any]] = None
) -> RiskReturnProfile:
    """
    计算期权的风险收益风格标签

    Args:
        option: 期权数据 (strike, bid, ask, days_to_expiry, implied_volatility等)
        stock_data: 标的股票数据 (current_price, volatility_30d等)
        strategy: 策略类型 ('sell_put', 'sell_call', 'buy_call', 'buy_put')
        vrp_analysis: VRP分析数据 (可选)

    Returns:
        RiskReturnProfile: 风险收益风格标签
    """
    try:
        # 提取关键数据
        strike = option.get('strike', 0)
        bid = option.get('bid', option.get('bid_price', 0))
        ask = option.get('ask', option.get('ask_price', 0))
        mid_price = (bid + ask) / 2 if bid and ask else option.get('mid_price', 0)
        days_to_expiry = option.get('days_to_expiry', 30)
        implied_vol = option.get('implied_volatility', option.get('impliedVolatility', 0.25))

        current_price = stock_data.get('current_price', 0)

        if not all([strike, current_price, mid_price > 0]):
            return _create_default_profile(strategy)

        # 根据策略类型计算风格
        if strategy == 'sell_put':
            return _calculate_sell_put_profile(
                strike, mid_price, current_price, days_to_expiry, implied_vol, vrp_analysis
            )
        elif strategy == 'sell_call':
            return _calculate_sell_call_profile(
                strike, mid_price, current_price, days_to_expiry, implied_vol, vrp_analysis
            )
        elif strategy == 'buy_call':
            return _calculate_buy_call_profile(
                strike, mid_price, current_price, days_to_expiry, implied_vol, vrp_analysis
            )
        elif strategy == 'buy_put':
            return _calculate_buy_put_profile(
                strike, mid_price, current_price, days_to_expiry, implied_vol, vrp_analysis
            )
        else:
            return _create_default_profile(strategy)

    except Exception as e:
        logger.error(f"计算风险收益风格失败: {e}")
        return _create_default_profile(strategy)


def _calculate_sell_put_profile(
    strike: float,
    premium: float,
    current_price: float,
    days_to_expiry: int,
    implied_vol: float,
    vrp_analysis: Optional[Dict] = None
) -> RiskReturnProfile:
    """计算 Sell Put 策略的风格标签"""

    # 计算关键指标
    safety_margin_pct = (current_price - strike) / current_price * 100
    max_profit_pct = (premium / strike) * 100  # 收取的权利金占执行价的比例
    max_loss_pct = ((strike - premium) / strike) * 100  # 最大亏损（被指派）
    annualized_return = (max_profit_pct / days_to_expiry) * 365

    # 基础胜率估算
    base_win_prob = _estimate_sell_put_win_probability(
        current_price, strike, implied_vol, days_to_expiry
    )

    # VRP调整胜率
    if vrp_analysis:
        vrp_level = vrp_analysis.get('vrp_level', 'normal')
        if vrp_level == 'very_high':
            base_win_prob = min(0.90, base_win_prob + 0.05)
        elif vrp_level == 'high':
            base_win_prob = min(0.85, base_win_prob + 0.03)

    # 风格判定
    if safety_margin_pct >= 10 and annualized_return <= 25:
        # 大安全边际 + 适中收益 = 稳健收益
        style = 'steady_income'
        risk_level = 'low'
    elif safety_margin_pct >= 5 and annualized_return <= 40:
        # 中等安全边际 = 稳中求进
        style = 'balanced'
        risk_level = 'moderate'
    elif safety_margin_pct < 3 or annualized_return > 50:
        # 小安全边际 或 高收益 = 高风险高收益
        style = 'high_risk_high_reward'
        risk_level = 'high' if safety_margin_pct >= 0 else 'very_high'
    else:
        style = 'balanced'
        risk_level = 'moderate'

    # 风险收益比
    risk_reward_ratio = max_profit_pct / max_loss_pct if max_loss_pct > 0 else 0

    # 生成摘要
    summary_cn = _generate_sell_put_summary_cn(
        style, base_win_prob, max_profit_pct, safety_margin_pct, days_to_expiry
    )
    summary_en = _generate_sell_put_summary_en(
        style, base_win_prob, max_profit_pct, safety_margin_pct, days_to_expiry
    )

    style_def = STYLE_DEFINITIONS[style]

    return RiskReturnProfile(
        style=style,
        style_label=style_def['label'],
        style_label_cn=style_def['label_cn'],
        style_label_en=style_def['label_en'],
        risk_level=risk_level,
        risk_color=RISK_COLORS[risk_level],
        max_loss_pct=round(max_loss_pct, 2),
        max_profit_pct=round(max_profit_pct, 2),
        win_probability=round(base_win_prob, 2),
        risk_reward_ratio=round(risk_reward_ratio, 3),
        summary=f"{summary_cn} | {summary_en}",
        summary_cn=summary_cn,
        strategy_type='seller',
        time_decay_impact='positive',
        volatility_impact='negative'
    )


def _calculate_sell_call_profile(
    strike: float,
    premium: float,
    current_price: float,
    days_to_expiry: int,
    implied_vol: float,
    vrp_analysis: Optional[Dict] = None
) -> RiskReturnProfile:
    """计算 Sell Call 策略的风格标签"""

    # 计算关键指标
    distance_pct = (strike - current_price) / current_price * 100
    max_profit_pct = (premium / current_price) * 100
    # Sell Call 的最大亏损理论上无限，这里用一个合理估算
    max_loss_pct = 100  # 简化为100%
    annualized_return = (max_profit_pct / days_to_expiry) * 365

    # 基础胜率估算
    base_win_prob = _estimate_sell_call_win_probability(
        current_price, strike, implied_vol, days_to_expiry
    )

    # VRP调整
    if vrp_analysis:
        vrp_level = vrp_analysis.get('vrp_level', 'normal')
        if vrp_level == 'very_high':
            base_win_prob = min(0.85, base_win_prob + 0.05)

    # 风格判定 - Sell Call 通常风险更高
    if distance_pct >= 15 and annualized_return <= 20:
        style = 'steady_income'
        risk_level = 'moderate'  # Sell Call 即使安全边际大也至少是moderate
    elif distance_pct >= 8:
        style = 'balanced'
        risk_level = 'moderate'
    else:
        style = 'high_risk_high_reward'
        risk_level = 'high'

    risk_reward_ratio = max_profit_pct / max_loss_pct if max_loss_pct > 0 else 0

    summary_cn = f"胜率约{base_win_prob:.0%}，年化收益{annualized_return:.0f}%，虚值{distance_pct:.1f}%"
    summary_en = f"Win rate ~{base_win_prob:.0%}, {annualized_return:.0f}% annualized, {distance_pct:.1f}% OTM"

    style_def = STYLE_DEFINITIONS[style]

    return RiskReturnProfile(
        style=style,
        style_label=style_def['label'],
        style_label_cn=style_def['label_cn'],
        style_label_en=style_def['label_en'],
        risk_level=risk_level,
        risk_color=RISK_COLORS[risk_level],
        max_loss_pct=round(max_loss_pct, 2),
        max_profit_pct=round(max_profit_pct, 2),
        win_probability=round(base_win_prob, 2),
        risk_reward_ratio=round(risk_reward_ratio, 3),
        summary=f"{summary_cn} | {summary_en}",
        summary_cn=summary_cn,
        strategy_type='seller',
        time_decay_impact='positive',
        volatility_impact='negative'
    )


def _calculate_buy_call_profile(
    strike: float,
    premium: float,
    current_price: float,
    days_to_expiry: int,
    implied_vol: float,
    vrp_analysis: Optional[Dict] = None
) -> RiskReturnProfile:
    """计算 Buy Call 策略的风格标签"""

    # 计算关键指标
    distance_pct = (strike - current_price) / current_price * 100  # 虚值程度
    max_loss_pct = 100  # 最多亏损全部权利金
    breakeven_move_pct = ((strike + premium - current_price) / current_price) * 100

    # 潜在收益估算（基于波动率）
    expected_move = current_price * implied_vol * math.sqrt(days_to_expiry / 365)
    potential_profit_at_1std = max(0, current_price + expected_move - strike - premium)
    max_profit_pct = (potential_profit_at_1std / premium) * 100 if premium > 0 else 0

    # 基础胜率估算
    base_win_prob = _estimate_buy_call_win_probability(
        current_price, strike, premium, implied_vol, days_to_expiry
    )

    # VRP调整 - 低VRP对买方有利
    if vrp_analysis:
        vrp_level = vrp_analysis.get('vrp_level', 'normal')
        if vrp_level == 'very_low':
            base_win_prob = min(0.60, base_win_prob + 0.05)
        elif vrp_level == 'low':
            base_win_prob = min(0.55, base_win_prob + 0.03)

    # 风格判定
    if distance_pct > 20:
        # 深度虚值 = 高风险高收益
        style = 'high_risk_high_reward'
        risk_level = 'very_high'
        max_profit_pct = 500  # 深度虚值潜在5倍+收益
    elif distance_pct > 10:
        # 中度虚值
        style = 'high_risk_high_reward'
        risk_level = 'high'
        max_profit_pct = min(300, max_profit_pct)
    elif distance_pct > 3:
        # 轻度虚值
        style = 'balanced'
        risk_level = 'high'
        max_profit_pct = min(200, max_profit_pct)
    else:
        # 平值或轻度实值
        style = 'balanced'
        risk_level = 'moderate'
        max_profit_pct = min(150, max_profit_pct)

    risk_reward_ratio = max_profit_pct / max_loss_pct if max_loss_pct > 0 else 0

    summary_cn = _generate_buy_call_summary_cn(
        style, base_win_prob, distance_pct, breakeven_move_pct, days_to_expiry
    )
    summary_en = _generate_buy_call_summary_en(
        style, base_win_prob, distance_pct, breakeven_move_pct, days_to_expiry
    )

    style_def = STYLE_DEFINITIONS[style]

    return RiskReturnProfile(
        style=style,
        style_label=style_def['label'],
        style_label_cn=style_def['label_cn'],
        style_label_en=style_def['label_en'],
        risk_level=risk_level,
        risk_color=RISK_COLORS[risk_level],
        max_loss_pct=round(max_loss_pct, 2),
        max_profit_pct=round(max_profit_pct, 2),
        win_probability=round(base_win_prob, 2),
        risk_reward_ratio=round(risk_reward_ratio, 3),
        summary=f"{summary_cn} | {summary_en}",
        summary_cn=summary_cn,
        strategy_type='buyer',
        time_decay_impact='negative',
        volatility_impact='positive'
    )


def _calculate_buy_put_profile(
    strike: float,
    premium: float,
    current_price: float,
    days_to_expiry: int,
    implied_vol: float,
    vrp_analysis: Optional[Dict] = None
) -> RiskReturnProfile:
    """计算 Buy Put 策略的风格标签"""

    # 计算关键指标
    distance_pct = (current_price - strike) / current_price * 100  # 虚值程度
    max_loss_pct = 100  # 最多亏损全部权利金
    breakeven_price = strike - premium
    breakeven_drop_pct = (current_price - breakeven_price) / current_price * 100

    # 保护性成本
    hedge_cost_pct = (premium / current_price) * 100

    # 潜在收益估算
    expected_move = current_price * implied_vol * math.sqrt(days_to_expiry / 365)
    potential_profit_at_1std = max(0, strike - (current_price - expected_move) - premium)
    max_profit_pct = (potential_profit_at_1std / premium) * 100 if premium > 0 else 0

    # 基础胜率估算
    base_win_prob = _estimate_buy_put_win_probability(
        current_price, strike, premium, implied_vol, days_to_expiry
    )

    # 判断是保护性还是投机性
    is_protective = distance_pct <= 5  # 平值或轻度虚值可能是保护性

    # 风格判定
    if is_protective and hedge_cost_pct <= 5:
        # 保护对冲
        style = 'hedge'
        risk_level = 'low'
        max_profit_pct = 100  # 对冲收益有限
    elif distance_pct > 15:
        # 深度虚值 = 高风险高收益
        style = 'high_risk_high_reward'
        risk_level = 'very_high'
        max_profit_pct = 400
    elif distance_pct > 8:
        style = 'high_risk_high_reward'
        risk_level = 'high'
        max_profit_pct = min(250, max_profit_pct)
    else:
        style = 'balanced'
        risk_level = 'moderate'

    risk_reward_ratio = max_profit_pct / max_loss_pct if max_loss_pct > 0 else 0

    if style == 'hedge':
        summary_cn = f"保护成本{hedge_cost_pct:.1f}%，下跌超过{breakeven_drop_pct:.1f}%开始获利"
        summary_en = f"Hedge cost {hedge_cost_pct:.1f}%, profit if down >{breakeven_drop_pct:.1f}%"
    else:
        summary_cn = f"胜率约{base_win_prob:.0%}，需下跌{breakeven_drop_pct:.1f}%才能获利"
        summary_en = f"Win rate ~{base_win_prob:.0%}, needs {breakeven_drop_pct:.1f}% drop to profit"

    style_def = STYLE_DEFINITIONS[style]

    return RiskReturnProfile(
        style=style,
        style_label=style_def['label'],
        style_label_cn=style_def['label_cn'],
        style_label_en=style_def['label_en'],
        risk_level=risk_level,
        risk_color=RISK_COLORS[risk_level],
        max_loss_pct=round(max_loss_pct, 2),
        max_profit_pct=round(max_profit_pct, 2),
        win_probability=round(base_win_prob, 2),
        risk_reward_ratio=round(risk_reward_ratio, 3),
        summary=f"{summary_cn} | {summary_en}",
        summary_cn=summary_cn,
        strategy_type='buyer',
        time_decay_impact='negative',
        volatility_impact='positive'
    )


# ==================== 辅助函数 ====================

def _estimate_sell_put_win_probability(
    current_price: float,
    strike: float,
    implied_vol: float,
    days_to_expiry: int
) -> float:
    """估算 Sell Put 的胜率"""
    try:
        from scipy.stats import norm

        if implied_vol <= 0 or days_to_expiry <= 0:
            return 0.60

        t = days_to_expiry / 365
        # 使用简化的 Black-Scholes 概率
        d1 = (math.log(current_price / strike) + (0.05 + 0.5 * implied_vol ** 2) * t) / (implied_vol * math.sqrt(t))
        # 股价在到期时高于执行价的概率
        prob_above_strike = norm.cdf(d1)

        return min(0.95, max(0.30, prob_above_strike))

    except Exception:
        # 简化计算
        distance_pct = (current_price - strike) / current_price * 100
        if distance_pct >= 15:
            return 0.85
        elif distance_pct >= 10:
            return 0.78
        elif distance_pct >= 5:
            return 0.70
        elif distance_pct >= 0:
            return 0.60
        else:
            return max(0.35, 0.60 + distance_pct * 0.02)


def _estimate_sell_call_win_probability(
    current_price: float,
    strike: float,
    implied_vol: float,
    days_to_expiry: int
) -> float:
    """估算 Sell Call 的胜率"""
    try:
        from scipy.stats import norm

        if implied_vol <= 0 or days_to_expiry <= 0:
            return 0.55

        t = days_to_expiry / 365
        d1 = (math.log(current_price / strike) + (0.05 + 0.5 * implied_vol ** 2) * t) / (implied_vol * math.sqrt(t))
        # 股价在到期时低于执行价的概率
        prob_below_strike = norm.cdf(-d1)

        return min(0.90, max(0.30, prob_below_strike))

    except Exception:
        distance_pct = (strike - current_price) / current_price * 100
        if distance_pct >= 15:
            return 0.80
        elif distance_pct >= 10:
            return 0.72
        elif distance_pct >= 5:
            return 0.62
        elif distance_pct >= 0:
            return 0.50
        else:
            return max(0.30, 0.50 + distance_pct * 0.02)


def _estimate_buy_call_win_probability(
    current_price: float,
    strike: float,
    premium: float,
    implied_vol: float,
    days_to_expiry: int
) -> float:
    """估算 Buy Call 的胜率（达到盈亏平衡的概率）"""
    try:
        from scipy.stats import norm

        if implied_vol <= 0 or days_to_expiry <= 0:
            return 0.35

        breakeven = strike + premium
        t = days_to_expiry / 365
        d1 = (math.log(current_price / breakeven) + (0.05 + 0.5 * implied_vol ** 2) * t) / (implied_vol * math.sqrt(t))
        prob_above_breakeven = norm.cdf(d1)

        return min(0.65, max(0.15, prob_above_breakeven))

    except Exception:
        distance_pct = (strike - current_price) / current_price * 100
        if distance_pct <= 0:
            return 0.50
        elif distance_pct <= 5:
            return 0.42
        elif distance_pct <= 10:
            return 0.35
        elif distance_pct <= 20:
            return 0.25
        else:
            return 0.15


def _estimate_buy_put_win_probability(
    current_price: float,
    strike: float,
    premium: float,
    implied_vol: float,
    days_to_expiry: int
) -> float:
    """估算 Buy Put 的胜率"""
    try:
        from scipy.stats import norm

        if implied_vol <= 0 or days_to_expiry <= 0:
            return 0.35

        breakeven = strike - premium
        t = days_to_expiry / 365
        d1 = (math.log(current_price / breakeven) + (0.05 + 0.5 * implied_vol ** 2) * t) / (implied_vol * math.sqrt(t))
        prob_below_breakeven = norm.cdf(-d1)

        return min(0.60, max(0.15, prob_below_breakeven))

    except Exception:
        distance_pct = (current_price - strike) / current_price * 100
        if distance_pct <= 0:
            return 0.45
        elif distance_pct <= 5:
            return 0.38
        elif distance_pct <= 10:
            return 0.30
        else:
            return 0.20


def _generate_sell_put_summary_cn(
    style: str,
    win_prob: float,
    profit_pct: float,
    safety_margin: float,
    days: int
) -> str:
    """生成 Sell Put 中文摘要"""
    if style == 'steady_income':
        return f"胜率{win_prob:.0%}，月收益约{profit_pct:.1f}%，安全边际{safety_margin:.1f}%，适合稳健投资者"
    elif style == 'high_risk_high_reward':
        return f"胜率{win_prob:.0%}，收益{profit_pct:.1f}%，安全边际仅{safety_margin:.1f}%，需谨慎"
    else:
        return f"胜率{win_prob:.0%}，收益{profit_pct:.1f}%，{days}天到期，风险收益均衡"


def _generate_sell_put_summary_en(
    style: str,
    win_prob: float,
    profit_pct: float,
    safety_margin: float,
    days: int
) -> str:
    """生成 Sell Put 英文摘要"""
    if style == 'steady_income':
        return f"{win_prob:.0%} win rate, ~{profit_pct:.1f}% return, {safety_margin:.1f}% cushion"
    elif style == 'high_risk_high_reward':
        return f"{win_prob:.0%} win rate, {profit_pct:.1f}% return, only {safety_margin:.1f}% cushion"
    else:
        return f"{win_prob:.0%} win rate, {profit_pct:.1f}% return, {days}d expiry"


def _generate_buy_call_summary_cn(
    style: str,
    win_prob: float,
    distance_pct: float,
    breakeven_pct: float,
    days: int
) -> str:
    """生成 Buy Call 中文摘要"""
    if style == 'high_risk_high_reward':
        return f"胜率约{win_prob:.0%}，需上涨{breakeven_pct:.1f}%才能获利，潜在收益巨大"
    else:
        return f"胜率约{win_prob:.0%}，{days}天到期，需上涨{breakeven_pct:.1f}%达到盈亏平衡"


def _generate_buy_call_summary_en(
    style: str,
    win_prob: float,
    distance_pct: float,
    breakeven_pct: float,
    days: int
) -> str:
    """生成 Buy Call 英文摘要"""
    if style == 'high_risk_high_reward':
        return f"~{win_prob:.0%} win rate, needs +{breakeven_pct:.1f}% to profit, high upside"
    else:
        return f"~{win_prob:.0%} win rate, {days}d expiry, +{breakeven_pct:.1f}% breakeven"


def _create_default_profile(strategy: str) -> RiskReturnProfile:
    """创建默认的风格标签"""
    if strategy in ['sell_put', 'sell_call']:
        return RiskReturnProfile(
            style='balanced',
            style_label='稳中求进 / BALANCED',
            style_label_cn='稳中求进',
            style_label_en='BALANCED',
            risk_level='moderate',
            risk_color='yellow',
            max_loss_pct=0,
            max_profit_pct=0,
            win_probability=0.50,
            risk_reward_ratio=0,
            summary='数据不足，无法评估 | Insufficient data',
            summary_cn='数据不足，无法评估',
            strategy_type='seller',
            time_decay_impact='positive',
            volatility_impact='negative'
        )
    else:
        return RiskReturnProfile(
            style='balanced',
            style_label='稳中求进 / BALANCED',
            style_label_cn='稳中求进',
            style_label_en='BALANCED',
            risk_level='moderate',
            risk_color='yellow',
            max_loss_pct=100,
            max_profit_pct=0,
            win_probability=0.35,
            risk_reward_ratio=0,
            summary='数据不足，无法评估 | Insufficient data',
            summary_cn='数据不足，无法评估',
            strategy_type='buyer',
            time_decay_impact='negative',
            volatility_impact='positive'
        )


# ==================== 批量处理函数 ====================

def add_profiles_to_options(
    options: list,
    stock_data: Dict[str, Any],
    strategy: str,
    vrp_analysis: Optional[Dict[str, Any]] = None
) -> list:
    """
    为期权列表批量添加风格标签

    Args:
        options: 期权列表
        stock_data: 标的股票数据
        strategy: 策略类型
        vrp_analysis: VRP分析数据

    Returns:
        添加了风格标签的期权列表
    """
    result = []
    for option in options:
        profile = calculate_risk_return_profile(option, stock_data, strategy, vrp_analysis)
        option_with_profile = {
            **option,
            'risk_return_profile': profile.to_dict()
        }
        result.append(option_with_profile)

    return result


# ==================== 测试代码 ====================

if __name__ == "__main__":
    print("🧪 风险收益风格标签系统测试")
    print("=" * 60)

    # 测试数据
    stock_data = {
        'current_price': 180.0,
        'volatility_30d': 0.25
    }

    # 测试 Sell Put
    print("\n📊 Sell Put 测试:")
    sell_put_option = {
        'strike': 170,
        'bid': 2.5,
        'ask': 2.8,
        'days_to_expiry': 30,
        'implied_volatility': 0.28
    }
    profile = calculate_risk_return_profile(sell_put_option, stock_data, 'sell_put')
    print(f"  风格: {profile.style_label}")
    print(f"  风险等级: {profile.risk_level} ({profile.risk_color})")
    print(f"  胜率: {profile.win_probability:.0%}")
    print(f"  最大收益: {profile.max_profit_pct:.2f}%")
    print(f"  摘要: {profile.summary_cn}")

    # 测试 Buy Call
    print("\n📊 Buy Call 测试:")
    buy_call_option = {
        'strike': 200,
        'bid': 1.5,
        'ask': 1.8,
        'days_to_expiry': 30,
        'implied_volatility': 0.30
    }
    profile = calculate_risk_return_profile(buy_call_option, stock_data, 'buy_call')
    print(f"  风格: {profile.style_label}")
    print(f"  风险等级: {profile.risk_level} ({profile.risk_color})")
    print(f"  胜率: {profile.win_probability:.0%}")
    print(f"  潜在收益: {profile.max_profit_pct:.0f}%")
    print(f"  摘要: {profile.summary_cn}")

    # 测试 Buy Put (对冲)
    print("\n📊 Buy Put (保护性) 测试:")
    buy_put_option = {
        'strike': 175,
        'bid': 3.0,
        'ask': 3.3,
        'days_to_expiry': 45,
        'implied_volatility': 0.25
    }
    profile = calculate_risk_return_profile(buy_put_option, stock_data, 'buy_put')
    print(f"  风格: {profile.style_label}")
    print(f"  风险等级: {profile.risk_level} ({profile.risk_color})")
    print(f"  摘要: {profile.summary_cn}")

    print("\n🎉 测试完成!")

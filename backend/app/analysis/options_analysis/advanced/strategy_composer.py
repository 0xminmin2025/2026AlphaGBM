"""
多腿期权策略组合器

功能：
- 预设策略模板（Covered Call, Bull/Bear Spread, Iron Condor, Straddle, etc.）
- 自定义多腿组合
- 聚合 Greeks 计算
- P/L 曲线生成
- 策略特征分析
"""

import logging
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional, Literal
from ..core.greeks_calculator import BlackScholesCalculator, OptionLeg, StrategyGreeks

logger = logging.getLogger(__name__)


# ─────────────────────────────────────
# 策略模板定义
# ─────────────────────────────────────

STRATEGY_TEMPLATES = {
    'covered_call': {
        'name_cn': '备兑看涨',
        'name_en': 'Covered Call',
        'description_cn': '持有股票 + 卖出看涨期权，赚取权利金收入',
        'category': 'income',
        'direction': 'neutral_bullish',
        'legs_template': [
            {'action': 'sell', 'option_type': 'call', 'strike_offset': 'otm_1'}
        ],
        'requires_stock': True,  # 需要持有标的
    },
    'cash_secured_put': {
        'name_cn': '现金担保看跌',
        'name_en': 'Cash Secured Put',
        'description_cn': '卖出看跌期权，愿意在低价接盘',
        'category': 'income',
        'direction': 'bullish',
        'legs_template': [
            {'action': 'sell', 'option_type': 'put', 'strike_offset': 'otm_1'}
        ],
    },
    'bull_call_spread': {
        'name_cn': '牛市看涨价差',
        'name_en': 'Bull Call Spread',
        'description_cn': '买入低行权价 Call + 卖出高行权价 Call，限定风险看涨',
        'category': 'directional',
        'direction': 'bullish',
        'legs_template': [
            {'action': 'buy', 'option_type': 'call', 'strike_offset': 'atm'},
            {'action': 'sell', 'option_type': 'call', 'strike_offset': 'otm_1'}
        ],
    },
    'bear_put_spread': {
        'name_cn': '熊市看跌价差',
        'name_en': 'Bear Put Spread',
        'description_cn': '买入高行权价 Put + 卖出低行权价 Put，限定风险看跌',
        'category': 'directional',
        'direction': 'bearish',
        'legs_template': [
            {'action': 'buy', 'option_type': 'put', 'strike_offset': 'atm'},
            {'action': 'sell', 'option_type': 'put', 'strike_offset': 'otm_1'}
        ],
    },
    'iron_condor': {
        'name_cn': '铁鹰',
        'name_en': 'Iron Condor',
        'description_cn': '同时卖出 OTM Put 和 OTM Call 价差，赚取时间价值',
        'category': 'income',
        'direction': 'neutral',
        'legs_template': [
            {'action': 'buy', 'option_type': 'put', 'strike_offset': 'otm_2'},
            {'action': 'sell', 'option_type': 'put', 'strike_offset': 'otm_1'},
            {'action': 'sell', 'option_type': 'call', 'strike_offset': 'otm_1'},
            {'action': 'buy', 'option_type': 'call', 'strike_offset': 'otm_2'},
        ],
    },
    'iron_butterfly': {
        'name_cn': '铁蝶',
        'name_en': 'Iron Butterfly',
        'description_cn': '在 ATM 同时卖出 Call 和 Put，两侧买入保护',
        'category': 'income',
        'direction': 'neutral',
        'legs_template': [
            {'action': 'buy', 'option_type': 'put', 'strike_offset': 'otm_1'},
            {'action': 'sell', 'option_type': 'put', 'strike_offset': 'atm'},
            {'action': 'sell', 'option_type': 'call', 'strike_offset': 'atm'},
            {'action': 'buy', 'option_type': 'call', 'strike_offset': 'otm_1'},
        ],
    },
    'straddle': {
        'name_cn': '跨式',
        'name_en': 'Straddle',
        'description_cn': '同时买入 ATM Call 和 Put，赌大幅波动',
        'category': 'volatility',
        'direction': 'neutral',
        'legs_template': [
            {'action': 'buy', 'option_type': 'call', 'strike_offset': 'atm'},
            {'action': 'buy', 'option_type': 'put', 'strike_offset': 'atm'},
        ],
    },
    'strangle': {
        'name_cn': '宽跨式',
        'name_en': 'Strangle',
        'description_cn': '买入 OTM Call 和 OTM Put，成本更低的波动率策略',
        'category': 'volatility',
        'direction': 'neutral',
        'legs_template': [
            {'action': 'buy', 'option_type': 'call', 'strike_offset': 'otm_1'},
            {'action': 'buy', 'option_type': 'put', 'strike_offset': 'otm_1'},
        ],
    },
    'protective_put': {
        'name_cn': '保护性看跌',
        'name_en': 'Protective Put',
        'description_cn': '持有股票 + 买入看跌期权对冲下行风险',
        'category': 'hedge',
        'direction': 'bullish',
        'legs_template': [
            {'action': 'buy', 'option_type': 'put', 'strike_offset': 'otm_1'}
        ],
        'requires_stock': True,
    },
    'collar': {
        'name_cn': '领口策略',
        'name_en': 'Collar',
        'description_cn': '持有股票 + 买 Put 保护 + 卖 Call 降低成本',
        'category': 'hedge',
        'direction': 'neutral',
        'legs_template': [
            {'action': 'buy', 'option_type': 'put', 'strike_offset': 'otm_1'},
            {'action': 'sell', 'option_type': 'call', 'strike_offset': 'otm_1'},
        ],
        'requires_stock': True,
    },
}


class StrategyComposer:
    """策略组合器"""

    def __init__(self, risk_free_rate: float = 0.05):
        self.bs = BlackScholesCalculator(risk_free_rate=risk_free_rate)

    def get_templates(self) -> List[Dict[str, Any]]:
        """获取所有策略模板列表"""
        templates = []
        for key, tmpl in STRATEGY_TEMPLATES.items():
            templates.append({
                'id': key,
                'name_cn': tmpl['name_cn'],
                'name_en': tmpl['name_en'],
                'description_cn': tmpl['description_cn'],
                'category': tmpl['category'],
                'direction': tmpl['direction'],
                'num_legs': len(tmpl['legs_template']),
                'requires_stock': tmpl.get('requires_stock', False),
            })
        return templates

    def build_from_template(
        self,
        template_id: str,
        spot: float,
        expiry_days: int,
        strikes: List[float],
        ivs: Optional[Dict[float, float]] = None,
        quantity: int = 1,
        multiplier: int = 100,
    ) -> Dict[str, Any]:
        """
        从模板构建策略

        Args:
            template_id: 策略模板 ID
            spot: 标的价格
            expiry_days: 到期天数
            strikes: 可用行权价列表（已排序）
            ivs: {strike: iv} 映射，可选
            quantity: 每腿数量
            multiplier: 合约乘数

        Returns:
            {'template': ..., 'legs': [...], 'greeks': ..., 'pnl': ...}
        """
        template = STRATEGY_TEMPLATES.get(template_id)
        if not template:
            raise ValueError(f"未知策略模板: {template_id}")

        # 解析行权价偏移
        legs = []
        for leg_tmpl in template['legs_template']:
            strike = self._resolve_strike(
                leg_tmpl['strike_offset'],
                leg_tmpl['option_type'],
                spot, strikes
            )

            iv = 0.25  # 默认
            if ivs and strike in ivs:
                iv = ivs[strike]

            legs.append(OptionLeg(
                option_type=leg_tmpl['option_type'],
                strike=strike,
                expiry_days=expiry_days,
                action=leg_tmpl['action'],
                quantity=quantity,
                iv=iv,
                multiplier=multiplier,
            ))

        return self.analyze_strategy(legs, spot, template_info=template)

    def analyze_strategy(
        self,
        legs: List[OptionLeg],
        spot: float,
        template_info: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        分析自定义策略组合

        Args:
            legs: 期权腿列表
            spot: 标的价格
            template_info: 策略模板信息（可选）

        Returns:
            完整的策略分析结果
        """
        # 计算聚合 Greeks
        greeks = self.bs.calculate_strategy_greeks(legs, spot)

        # 计算 P/L 曲线
        pnl = self.bs.calculate_pnl_curve(legs, spot)

        # 策略特征分析
        characteristics = self._analyze_characteristics(greeks, pnl, legs)

        result = {
            'legs': [self._leg_to_dict(leg) for leg in legs],
            'greeks': greeks.to_dict(),
            'pnl': pnl,
            'characteristics': characteristics,
        }

        if template_info:
            result['template'] = {
                'name_cn': template_info['name_cn'],
                'name_en': template_info['name_en'],
                'description_cn': template_info['description_cn'],
                'category': template_info['category'],
                'direction': template_info['direction'],
            }

        return result

    def _resolve_strike(
        self,
        offset: str,
        option_type: str,
        spot: float,
        strikes: List[float]
    ) -> float:
        """
        解析行权价偏移

        offset 可以是:
        - 'atm': 最接近现价
        - 'otm_1': 第1个虚值档位
        - 'otm_2': 第2个虚值档位
        - 'itm_1': 第1个实值档位
        """
        if not strikes:
            return spot

        atm_idx = min(range(len(strikes)), key=lambda i: abs(strikes[i] - spot))

        if offset == 'atm':
            return strikes[atm_idx]

        # OTM 方向：Call 往上，Put 往下
        n = int(offset.split('_')[1]) if '_' in offset else 1

        if 'otm' in offset:
            if option_type == 'call':
                idx = min(atm_idx + n, len(strikes) - 1)
            else:
                idx = max(atm_idx - n, 0)
        elif 'itm' in offset:
            if option_type == 'call':
                idx = max(atm_idx - n, 0)
            else:
                idx = min(atm_idx + n, len(strikes) - 1)
        else:
            idx = atm_idx

        return strikes[idx]

    def _leg_to_dict(self, leg: OptionLeg) -> Dict[str, Any]:
        """腿转字典"""
        return {
            'action': leg.action,
            'option_type': leg.option_type,
            'strike': leg.strike,
            'expiry_days': leg.expiry_days,
            'quantity': leg.quantity,
            'iv': leg.iv,
            'premium': leg.premium,
            'multiplier': leg.multiplier,
        }

    def _analyze_characteristics(
        self,
        greeks: StrategyGreeks,
        pnl: Dict[str, Any],
        legs: List[OptionLeg]
    ) -> Dict[str, Any]:
        """分析策略特征"""
        chars = {}

        # 方向性
        if abs(greeks.delta) < 10:
            chars['direction_cn'] = '中性'
            chars['direction'] = 'neutral'
        elif greeks.delta > 0:
            chars['direction_cn'] = '看涨'
            chars['direction'] = 'bullish'
        else:
            chars['direction_cn'] = '看跌'
            chars['direction'] = 'bearish'

        # 时间价值影响
        if greeks.theta > 0:
            chars['time_decay_cn'] = '有利（赚取时间价值）'
            chars['time_decay'] = 'positive'
        elif greeks.theta < 0:
            chars['time_decay_cn'] = '不利（损失时间价值）'
            chars['time_decay'] = 'negative'
        else:
            chars['time_decay_cn'] = '中性'
            chars['time_decay'] = 'neutral'

        # 波动率影响
        if greeks.vega > 0:
            chars['vol_impact_cn'] = '波动率上升有利'
            chars['vol_impact'] = 'long_vol'
        elif greeks.vega < 0:
            chars['vol_impact_cn'] = '波动率下降有利'
            chars['vol_impact'] = 'short_vol'
        else:
            chars['vol_impact_cn'] = '中性'
            chars['vol_impact'] = 'neutral'

        # 风险/收益类型
        max_p = pnl.get('max_profit', 0)
        max_l = pnl.get('max_loss', 0)

        if max_l != 0:
            rr_ratio = abs(max_p / max_l)
            chars['risk_reward_ratio'] = round(rr_ratio, 2)
        else:
            chars['risk_reward_ratio'] = float('inf')

        # 是否风险有限
        all_strikes = [leg.strike for leg in legs]
        num_buys = sum(1 for leg in legs if leg.action == 'buy')
        num_sells = sum(1 for leg in legs if leg.action == 'sell')

        chars['limited_risk'] = bool(num_buys >= num_sells)
        chars['limited_profit'] = bool(num_sells > 0)
        chars['is_debit'] = bool(pnl.get('net_cost', 0) > 0)
        chars['is_credit'] = bool(pnl.get('net_cost', 0) < 0)

        return chars

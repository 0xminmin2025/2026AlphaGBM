"""
宏观事件日历模块
检测 NFP(非农)、CPI、FOMC 等重大宏观事件，用于期权打分时的风险调整。

核心逻辑：
- 买方策略(Buy Call/Put)：短期期权(<=7天)在事件日前到期时额外降分 20-30%
- 卖方策略(Sell Call/Put)：0DTE/当周到期时加风险警告标签
- 到期日与事件日重叠时在 strategy_notes 中提示 IV Crush 风险
"""

import logging
from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

# 2025-2026 年宏观事件日历（硬编码，每年初更新一次即可）
# 格式: (日期, 事件类型, 事件名称)
MACRO_EVENTS = [
    # ---- 2025 NFP (非农就业数据，每月第一个周五，盘前8:30AM) ----
    (date(2025, 1, 10), 'NFP', '非农就业数据'),
    (date(2025, 2, 7), 'NFP', '非农就业数据'),
    (date(2025, 3, 7), 'NFP', '非农就业数据'),
    (date(2025, 4, 4), 'NFP', '非农就业数据'),
    (date(2025, 5, 2), 'NFP', '非农就业数据'),
    (date(2025, 6, 6), 'NFP', '非农就业数据'),
    (date(2025, 7, 3), 'NFP', '非农就业数据'),
    (date(2025, 8, 1), 'NFP', '非农就业数据'),
    (date(2025, 9, 5), 'NFP', '非农就业数据'),
    (date(2025, 10, 3), 'NFP', '非农就业数据'),
    (date(2025, 11, 7), 'NFP', '非农就业数据'),
    (date(2025, 12, 5), 'NFP', '非农就业数据'),
    # ---- 2026 NFP ----
    (date(2026, 1, 9), 'NFP', '非农就业数据'),
    (date(2026, 2, 6), 'NFP', '非农就业数据'),
    (date(2026, 3, 6), 'NFP', '非农就业数据'),
    (date(2026, 4, 3), 'NFP', '非农就业数据'),
    (date(2026, 5, 8), 'NFP', '非农就业数据'),
    (date(2026, 6, 5), 'NFP', '非农就业数据'),
    (date(2026, 7, 2), 'NFP', '非农就业数据'),
    (date(2026, 8, 7), 'NFP', '非农就业数据'),
    (date(2026, 9, 4), 'NFP', '非农就业数据'),
    (date(2026, 10, 2), 'NFP', '非农就业数据'),
    (date(2026, 11, 6), 'NFP', '非农就业数据'),
    (date(2026, 12, 4), 'NFP', '非农就业数据'),

    # ---- 2025 CPI (消费者物价指数，通常每月10-14日) ----
    (date(2025, 1, 15), 'CPI', 'CPI消费者物价指数'),
    (date(2025, 2, 12), 'CPI', 'CPI消费者物价指数'),
    (date(2025, 3, 12), 'CPI', 'CPI消费者物价指数'),
    (date(2025, 4, 10), 'CPI', 'CPI消费者物价指数'),
    (date(2025, 5, 13), 'CPI', 'CPI消费者物价指数'),
    (date(2025, 6, 11), 'CPI', 'CPI消费者物价指数'),
    (date(2025, 7, 15), 'CPI', 'CPI消费者物价指数'),
    (date(2025, 8, 12), 'CPI', 'CPI消费者物价指数'),
    (date(2025, 9, 10), 'CPI', 'CPI消费者物价指数'),
    (date(2025, 10, 14), 'CPI', 'CPI消费者物价指数'),
    (date(2025, 11, 12), 'CPI', 'CPI消费者物价指数'),
    (date(2025, 12, 10), 'CPI', 'CPI消费者物价指数'),
    # ---- 2026 CPI ----
    (date(2026, 1, 13), 'CPI', 'CPI消费者物价指数'),
    (date(2026, 2, 11), 'CPI', 'CPI消费者物价指数'),
    (date(2026, 3, 11), 'CPI', 'CPI消费者物价指数'),
    (date(2026, 4, 14), 'CPI', 'CPI消费者物价指数'),
    (date(2026, 5, 12), 'CPI', 'CPI消费者物价指数'),
    (date(2026, 6, 10), 'CPI', 'CPI消费者物价指数'),
    (date(2026, 7, 14), 'CPI', 'CPI消费者物价指数'),
    (date(2026, 8, 12), 'CPI', 'CPI消费者物价指数'),
    (date(2026, 9, 15), 'CPI', 'CPI消费者物价指数'),
    (date(2026, 10, 13), 'CPI', 'CPI消费者物价指数'),
    (date(2026, 11, 10), 'CPI', 'CPI消费者物价指数'),
    (date(2026, 12, 9), 'CPI', 'CPI消费者物价指数'),

    # ---- 2025 FOMC (利率决议，每年8次) ----
    (date(2025, 1, 29), 'FOMC', 'FOMC利率决议'),
    (date(2025, 3, 19), 'FOMC', 'FOMC利率决议'),
    (date(2025, 5, 7), 'FOMC', 'FOMC利率决议'),
    (date(2025, 6, 18), 'FOMC', 'FOMC利率决议'),
    (date(2025, 7, 30), 'FOMC', 'FOMC利率决议'),
    (date(2025, 9, 17), 'FOMC', 'FOMC利率决议'),
    (date(2025, 11, 5), 'FOMC', 'FOMC利率决议'),
    (date(2025, 12, 17), 'FOMC', 'FOMC利率决议'),
    # ---- 2026 FOMC ----
    (date(2026, 1, 28), 'FOMC', 'FOMC利率决议'),
    (date(2026, 3, 18), 'FOMC', 'FOMC利率决议'),
    (date(2026, 4, 29), 'FOMC', 'FOMC利率决议'),
    (date(2026, 6, 17), 'FOMC', 'FOMC利率决议'),
    (date(2026, 7, 29), 'FOMC', 'FOMC利率决议'),
    (date(2026, 9, 16), 'FOMC', 'FOMC利率决议'),
    (date(2026, 10, 28), 'FOMC', 'FOMC利率决议'),
    (date(2026, 12, 16), 'FOMC', 'FOMC利率决议'),
]

# 事件对 IV 的影响权重（NFP 最猛因为撞上周五到期日）
EVENT_IV_IMPACT = {
    'NFP': 1.0,   # 非农：最高影响（周五 + 0DTE 双杀）
    'FOMC': 0.8,  # FOMC：高影响（但周三发布，有2天缓冲）
    'CPI': 0.7,   # CPI：中高影响（周中发布）
}


def get_upcoming_events(days_ahead: int = 7, from_date: date = None) -> List[Dict[str, Any]]:
    """
    获取未来 N 天内的宏观事件。

    Args:
        days_ahead: 向前看多少天
        from_date: 起始日期，默认今天

    Returns:
        事件列表，按日期排序
    """
    if from_date is None:
        from_date = date.today()

    end_date = from_date + timedelta(days=days_ahead)

    events = []
    for event_date, event_type, event_name in MACRO_EVENTS:
        if from_date <= event_date <= end_date:
            events.append({
                'date': event_date,
                'type': event_type,
                'name': event_name,
                'days_until': (event_date - from_date).days,
                'iv_impact': EVENT_IV_IMPACT.get(event_type, 0.5),
            })

    events.sort(key=lambda x: x['date'])
    return events


def check_expiry_event_overlap(expiry_str: str, days_ahead: int = 7) -> Dict[str, Any]:
    """
    检查期权到期日是否与宏观事件重叠或临近。

    Args:
        expiry_str: 到期日字符串 (YYYY-MM-DD)
        days_ahead: 事件日前多少天算"临近"

    Returns:
        重叠检测结果
    """
    try:
        expiry_date = _parse_date(expiry_str)
        if expiry_date is None:
            return {'has_overlap': False, 'events': []}

        today = date.today()
        overlapping_events = []

        for event_date, event_type, event_name in MACRO_EVENTS:
            # 事件在今天之后、且在到期日前后1天内
            if event_date < today:
                continue

            days_diff = (event_date - expiry_date).days

            # 到期日 == 事件日（最危险：0DTE + 事件）
            if days_diff == 0:
                overlapping_events.append({
                    'date': event_date,
                    'type': event_type,
                    'name': event_name,
                    'overlap_type': 'same_day',
                    'risk_level': 'critical',
                    'iv_impact': EVENT_IV_IMPACT.get(event_type, 0.5),
                })
            # 事件在到期日之前1-2天（IV已被抬高，到期前会crush）
            elif -2 <= days_diff < 0:
                overlapping_events.append({
                    'date': event_date,
                    'type': event_type,
                    'name': event_name,
                    'overlap_type': 'before_expiry',
                    'risk_level': 'high',
                    'iv_impact': EVENT_IV_IMPACT.get(event_type, 0.5) * 0.7,
                })
            # 事件在到期日之后1天（期权在事件前到期，IV可能已经提前抬升）
            elif 0 < days_diff <= 1:
                overlapping_events.append({
                    'date': event_date,
                    'type': event_type,
                    'name': event_name,
                    'overlap_type': 'after_expiry',
                    'risk_level': 'medium',
                    'iv_impact': EVENT_IV_IMPACT.get(event_type, 0.5) * 0.4,
                })

        return {
            'has_overlap': len(overlapping_events) > 0,
            'events': overlapping_events,
            'max_risk_level': _get_max_risk_level(overlapping_events),
        }

    except Exception as e:
        logger.error(f"到期日事件重叠检测失败: {e}")
        return {'has_overlap': False, 'events': []}


def calculate_event_penalty(expiry_str: str, days_to_expiry: int,
                            strategy_type: str) -> Dict[str, Any]:
    """
    计算宏观事件对期权评分的惩罚。

    Args:
        expiry_str: 到期日字符串
        days_to_expiry: 距到期天数
        strategy_type: 策略类型 ('buy_call', 'buy_put', 'sell_call', 'sell_put')

    Returns:
        惩罚信息：
        - penalty_factor: 0.0-1.0 的乘数（1.0=无惩罚）
        - warnings: 警告文字列表
        - event_info: 事件详情
    """
    result = {
        'penalty_factor': 1.0,
        'warnings': [],
        'event_info': None,
        'has_event_risk': False,
    }

    overlap = check_expiry_event_overlap(expiry_str)
    if not overlap['has_overlap']:
        return result

    result['has_event_risk'] = True
    result['event_info'] = overlap

    is_buyer = strategy_type in ('buy_call', 'buy_put')
    is_seller = strategy_type in ('sell_call', 'sell_put')

    for event in overlap['events']:
        event_name = event['name']
        event_type = event['type']
        overlap_type = event['overlap_type']
        iv_impact = event['iv_impact']

        if is_buyer:
            # 买方策略：短期期权在事件日前到期时降分
            if days_to_expiry <= 7:
                # 同一天到期 = 最危险（IV Crush + Theta双杀）
                if overlap_type == 'same_day':
                    penalty = 0.70 * iv_impact  # 最多降30%
                    result['penalty_factor'] = min(result['penalty_factor'], 1.0 - penalty)
                    result['warnings'].append(
                        f"此期权在{event_name}当天到期，IV Crush风险极高，"
                        f"建议选择下周或更远到期的期权"
                    )
                elif overlap_type == 'before_expiry':
                    penalty = 0.50 * iv_impact
                    result['penalty_factor'] = min(result['penalty_factor'], 1.0 - penalty)
                    result['warnings'].append(
                        f"{event_name}在到期日前发布，IV已被抬高，"
                        f"到期前可能遭遇IV Crush"
                    )
            elif days_to_expiry <= 14:
                # 中短期期权：轻度警告
                if overlap_type in ('same_day', 'before_expiry'):
                    penalty = 0.15 * iv_impact
                    result['penalty_factor'] = min(result['penalty_factor'], 1.0 - penalty)
                    result['warnings'].append(
                        f"到期日临近{event_name}({event['date'].strftime('%m/%d')})，"
                        f"注意IV变动风险"
                    )

        elif is_seller:
            # 卖方策略：不降分，但加警告标签
            if overlap_type == 'same_day':
                if days_to_expiry <= 5:
                    # 0DTE / 当周到期 + 事件日 = 最高风险
                    result['warnings'].append(
                        f"[高风险] 此期权在{event_name}当天到期(0DTE)，"
                        f"VIX可能暴涨20%+，卖方策略亏损风险极大"
                    )
                else:
                    result['warnings'].append(
                        f"到期日恰逢{event_name}({event['date'].strftime('%m/%d')})，"
                        f"注意事件日波动率可能异常放大"
                    )
            elif overlap_type == 'before_expiry':
                result['warnings'].append(
                    f"{event_name}在到期前发布({event['date'].strftime('%m/%d')})，"
                    f"事件可能导致标的大幅波动"
                )

            # VIX > 25 时卖方策略额外惩罚（在调用侧处理）

    return result


def generate_event_notes(expiry_str: str, days_to_expiry: int) -> List[str]:
    """
    生成到期日相关的宏观事件提示，用于 strategy_notes。

    Args:
        expiry_str: 到期日字符串
        days_to_expiry: 距到期天数

    Returns:
        提示文字列表
    """
    notes = []
    overlap = check_expiry_event_overlap(expiry_str)

    if not overlap['has_overlap']:
        return notes

    for event in overlap['events']:
        event_name = event['name']
        event_date_str = event['date'].strftime('%m/%d')

        if event['overlap_type'] == 'same_day':
            notes.append(
                f"此期权在{event_name}当天到期({event_date_str})，"
                f"IV Crush风险较高"
            )
            if event['type'] == 'NFP':
                notes.append(
                    "非农恰逢周五到期日，0DTE期权可能遭遇"
                    "IV+Theta双杀，历史数据显示波动率可达普通周五的1.8倍"
                )
        elif event['overlap_type'] == 'before_expiry':
            notes.append(
                f"{event_name}将在到期前发布({event_date_str})，"
                f"期权IV可能提前抬升"
            )

    return notes


def get_vix_penalty_for_seller(vix_level: float) -> Dict[str, Any]:
    """
    基于VIX水平对卖方策略的惩罚。

    研究发现：VIX > 25 时卖跨式策略期望值为负，
    因为VIX暴涨的幅度(平均+19%)远大于IV Crush的幅度(平均-4.7%)。

    Args:
        vix_level: 当前VIX水平

    Returns:
        惩罚信息
    """
    if vix_level <= 0:
        return {'penalty_factor': 1.0, 'warning': None, 'vix_zone': 'unknown'}

    if vix_level >= 30:
        return {
            'penalty_factor': 0.75,
            'warning': (
                f"VIX={vix_level:.1f}，市场恐慌情绪高涨，"
                f"卖方策略亏损风险极大，建议暂停或大幅缩减仓位"
            ),
            'vix_zone': 'danger',
        }
    elif vix_level >= 25:
        return {
            'penalty_factor': 0.85,
            'warning': (
                f"VIX={vix_level:.1f}，高波动环境，"
                f"卖方策略的VIX暴涨风险大于IV Crush收益，建议谨慎"
            ),
            'vix_zone': 'warning',
        }
    elif vix_level >= 20:
        return {
            'penalty_factor': 0.95,
            'warning': None,
            'vix_zone': 'elevated',
        }
    else:
        return {
            'penalty_factor': 1.0,
            'warning': None,
            'vix_zone': 'normal',
        }


def _parse_date(date_str: str) -> Optional[date]:
    """解析日期字符串"""
    if not date_str:
        return None

    for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%m/%d/%Y'):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None


def _get_max_risk_level(events: List[Dict]) -> str:
    """获取事件列表中最高的风险等级"""
    if not events:
        return 'none'

    risk_order = {'critical': 3, 'high': 2, 'medium': 1}
    max_risk = max(events, key=lambda e: risk_order.get(e.get('risk_level', ''), 0))
    return max_risk.get('risk_level', 'none')

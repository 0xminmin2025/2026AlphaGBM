"""
商品期权交割月风险计算模块

商品期权与股票期权的核心差异：临近交割月的合约有强平风险。
本模块提供交割风险评估，用于评分系统惩罚临期合约。

规则：
- ≤30天（红色区域）：必须平仓，penalty=1.0
- 30-60天（黄色区域）：注意移仓，penalty 线性插值
- >60天（绿色区域）：正常交易，penalty=0.0
"""

import re
import logging
from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class DeliveryRiskAssessment:
    """交割风险评估结果"""
    days_to_delivery: int
    is_red_zone: bool        # ≤30天：必须平仓
    is_warning_zone: bool    # 30-60天：注意移仓
    delivery_penalty: float  # 评分惩罚 0.0~1.0
    warning: str             # 风险提示文案
    recommendation: str      # 'ok' | 'reduce' | 'close'
    delivery_month: str      # 交割月份 e.g. '2025-06'

    def to_dict(self):
        return {
            'days_to_delivery': self.days_to_delivery,
            'is_red_zone': self.is_red_zone,
            'is_warning_zone': self.is_warning_zone,
            'delivery_penalty': round(self.delivery_penalty, 3),
            'warning': self.warning,
            'recommendation': self.recommendation,
            'delivery_month': self.delivery_month,
        }


class DeliveryRiskCalculator:
    """商品期权交割月风险计算器"""

    RED_ZONE_DAYS = 30
    WARNING_ZONE_DAYS = 60

    def assess(self, contract_code: str) -> DeliveryRiskAssessment:
        """
        评估合约交割风险。

        Args:
            contract_code: 合约代码，如 'au2506', 'm2605'

        Returns:
            DeliveryRiskAssessment 实例
        """
        delivery_month = self._parse_delivery_month(contract_code)
        if not delivery_month:
            return DeliveryRiskAssessment(
                days_to_delivery=999,
                is_red_zone=False,
                is_warning_zone=False,
                delivery_penalty=0.0,
                warning='',
                recommendation='ok',
                delivery_month='unknown',
            )

        # Calculate days to first day of delivery month
        today = date.today()
        delivery_date = date(delivery_month.year, delivery_month.month, 1)
        days_to_delivery = (delivery_date - today).days

        if days_to_delivery <= 0:
            return DeliveryRiskAssessment(
                days_to_delivery=days_to_delivery,
                is_red_zone=True,
                is_warning_zone=False,
                delivery_penalty=1.0,
                warning=f'合约已进入交割月，必须立即平仓！',
                recommendation='close',
                delivery_month=delivery_month.strftime('%Y-%m'),
            )

        if days_to_delivery <= self.RED_ZONE_DAYS:
            return DeliveryRiskAssessment(
                days_to_delivery=days_to_delivery,
                is_red_zone=True,
                is_warning_zone=False,
                delivery_penalty=1.0,
                warning=f'距交割仅{days_to_delivery}天，建议立即平仓',
                recommendation='close',
                delivery_month=delivery_month.strftime('%Y-%m'),
            )

        if days_to_delivery <= self.WARNING_ZONE_DAYS:
            # Linear interpolation: 60d→0.0, 30d→1.0
            penalty = (self.WARNING_ZONE_DAYS - days_to_delivery) / (self.WARNING_ZONE_DAYS - self.RED_ZONE_DAYS)
            return DeliveryRiskAssessment(
                days_to_delivery=days_to_delivery,
                is_red_zone=False,
                is_warning_zone=True,
                delivery_penalty=round(penalty, 3),
                warning=f'距交割{days_to_delivery}天，建议关注移仓',
                recommendation='reduce',
                delivery_month=delivery_month.strftime('%Y-%m'),
            )

        # Safe zone
        return DeliveryRiskAssessment(
            days_to_delivery=days_to_delivery,
            is_red_zone=False,
            is_warning_zone=False,
            delivery_penalty=0.0,
            warning='',
            recommendation='ok',
            delivery_month=delivery_month.strftime('%Y-%m'),
        )

    @staticmethod
    def _parse_delivery_month(contract_code: str) -> Optional[date]:
        """
        Parse delivery month from contract code.

        Formats:
        - au2506 → 2025-06
        - m2605 → 2026-05
        - au2604 → 2026-04

        The 4-digit suffix is YYMM.
        """
        s = contract_code.lower().strip()
        # Extract trailing digits
        match = re.search(r'(\d{4})$', s)
        if not match:
            return None

        yymm = match.group(1)
        try:
            year = 2000 + int(yymm[:2])
            month = int(yymm[2:])
            if 1 <= month <= 12:
                return date(year, month, 1)
        except (ValueError, IndexError):
            pass

        return None

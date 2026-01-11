# phase1_modules/risk_adjuster.py

from typing import Optional, Dict, List
from dataclasses import dataclass
from enum import Enum

class RiskLevel(str, Enum):
    """风险等级枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"

@dataclass
class RiskAnalysis:
    """风险分析结果数据类"""
    expected_value: float            # 期望值
    risk_adjusted_expectancy: float  # 风险调整后期望值 (RAE)
    max_loss: float                  # 最大潜在亏损
    tail_risk_var: float             # 尾部风险 (VaR proxy)
    win_rate: float                  # 胜率 (0-100)
    risk_level: RiskLevel            # 风险等级
    tail_risk_warning: str           # 风险警告信息

class RiskAdjuster:
    """
    风险调整器：用于计算期望值、尾部风险及风险评级
    """
    
    def __init__(self, risk_free_rate: float = 0.05):
        self.risk_free_rate = risk_free_rate
    
    def calculate_expected_value(
        self,
        win_prob: float,
        avg_profit: float,
        avg_loss: float
    ) -> float:
        """
        计算数学期望值 (EV)
        EV = (胜率 * 平均盈利) - (败率 * 平均亏损)
        """
        loss_prob = 1.0 - win_prob
        expected_value = (win_prob * avg_profit) - (loss_prob * avg_loss)
        return expected_value
    
    def calculate_risk_adjusted_expectancy(
        self,
        expected_value: float,
        max_loss: float
    ) -> float:
        """
        计算风险调整后期望值 (RAE)
        RAE = EV / Max Loss
        """
        if max_loss <= 0:
            # 如果最大亏损为0或负（异常情况），返回0
            return 0.0
        return expected_value / max_loss
    
    def calculate_tail_risk(
        self,
        option_data: Dict,
        stock_price: float,
        confidence_level: float = 0.99
    ) -> float:
        """
        计算尾部风险 (VaR - 简化版)
        基于期权类型和保证金计算极端情况下的亏损
        """
        strike = option_data.get('strike', 0.0)
        premium = option_data.get('premium', 0.0)
        margin = option_data.get('margin', 0.0)
        option_type = option_data.get('type', 'call').lower()
        
        # 计算理论上的最大潜在亏损
        if option_type == 'put':
            # 卖出 Put：股票归零时的亏损
            # (行权价 - 权利金) * 100
            max_loss_theoretical = (strike - premium) * 100
        else:
            # 卖出 Call：理论无限，实际取保证金作为风险敞口参考
            max_loss_theoretical = margin
        
        # 极端事件乘数 (Phase 1 简化逻辑)
        # 假设极端行情下亏损可能扩大到理论值的 1.5 倍 (如跳空缺口、无法平仓)
        extreme_multiplier = 1.5
        
        # 简化实现：直接取最大亏损的1.5倍作为"极端风险值"
        # 这代表在极端市场条件下（如黑天鹅事件）可能面临的额外风险
        tail_risk = max_loss_theoretical * extreme_multiplier
        
        return tail_risk

    def analyze_risk(
        self,
        win_prob: float,
        avg_profit: float,
        avg_loss: float,
        max_loss: float,
        option_data: Optional[Dict] = None,
        stock_price: Optional[float] = None
    ) -> RiskAnalysis:
        """
        执行完整的风险分析
        """
        # 1. 计算期望值
        expected_value = self.calculate_expected_value(win_prob, avg_profit, avg_loss)
        
        # 2. 计算 RAE
        risk_adjusted_expectancy = self.calculate_risk_adjusted_expectancy(
            expected_value, max_loss
        )
        
        # 3. 计算尾部风险
        if option_data and stock_price:
            tail_risk_var = self.calculate_tail_risk(option_data, stock_price)
        else:
            # 默认假设尾部风险为最大亏损的 1.5 倍
            tail_risk_var = max_loss * 1.5
            
        # 4. 确定风险等级
        if max_loss <= 0:
            risk_level = RiskLevel.LOW
        elif risk_adjusted_expectancy > 0.5:
            risk_level = RiskLevel.LOW
        elif risk_adjusted_expectancy > 0.2:
            risk_level = RiskLevel.MEDIUM
        elif risk_adjusted_expectancy > 0:
            risk_level = RiskLevel.HIGH
        else:
            risk_level = RiskLevel.EXTREME
            
        # 5. 生成警告
        warning = ""
        if tail_risk_var > max_loss * 1.5:
            warning = f"警告：尾部风险预估为 ${tail_risk_var:.2f}，严重超出常规风控范围"
        elif win_prob > 0.9 and max_loss > avg_profit * 10:
            warning = "警告：胜率虽高，但盈亏比极差（黑天鹅风险）"
        elif risk_adjusted_expectancy < 0:
            warning = "警告：期望值为负，数学上不建议交易"
            
        return RiskAnalysis(
            expected_value=expected_value,
            risk_adjusted_expectancy=risk_adjusted_expectancy,
            max_loss=max_loss,
            tail_risk_var=tail_risk_var,
            win_rate=win_prob * 100,
            risk_level=risk_level,
            tail_risk_warning=warning
        )

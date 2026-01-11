# phase1_modules/vrp_calculator.py

import math
import bisect
import numpy as np
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class VRPResult:
    """VRP计算结果数据类"""
    vrp: float                    # VRP值（IV - RV）
    iv: float                     # 当前隐含波动率
    rv_forecast: float            # 预测的已实现波动率
    iv_rank: float                # IV Rank (0-100)
    iv_percentile: float          # IV Percentile (0-100)
    recommendation: str           # "sell", "buy", or "neutral"

class VRPCalculator:
    """
    波动率风险溢价（VRP）计算器
    """
    
    def __init__(self, risk_free_rate: float = 0.05):
        self.risk_free_rate = risk_free_rate
    
    def calculate_vrp(self, iv: float, rv_forecast: float) -> float:
        """
        计算VRP = 隐含波动率(IV) - 预测已实现波动率(RV)
        """
        return iv - rv_forecast
    
    def calculate_iv_rank(self, current_iv: float, iv_history: List[float]) -> float:
        """
        计算 IV Rank (0-100)
        如果是历史最高，返回100；历史最低，返回0。
        """
        if not iv_history or len(iv_history) < 10:
            return 50.0  # 数据不足时返回中性值
        
        sorted_iv = sorted(iv_history)
        # 找到当前IV在历史数据中的插入位置
        rank = bisect.bisect_left(sorted_iv, current_iv)
        iv_rank = (rank / len(sorted_iv)) * 100.0
        
        return min(100.0, max(0.0, iv_rank))
    
    def calculate_iv_percentile(self, current_iv: float, iv_history: List[float]) -> float:
        """
        计算 IV Percentile (0-100)
        计算有多少百分比的历史IV低于当前IV。
        """
        if not iv_history or len(iv_history) < 10:
            return 50.0
        
        below_count = sum(1 for iv in iv_history if iv < current_iv)
        percentile = (below_count / len(iv_history)) * 100.0
        
        return min(100.0, max(0.0, percentile))
    
    def forecast_realized_volatility(self, price_history: List[float], method: str = "garch") -> float:
        """
        预测已实现波动率 (RV)
        
        支持方法:
        - "garch": 使用 GARCH(1,1) 模型 (需要 arch 库)
        - "ewma": 指数加权移动平均 (RiskMetrics 标准)
        """
        if not price_history or len(price_history) < 30:
            # 数据不足，返回一个保守的估计值或抛出特定错误
            # 这里为了系统稳定，我们假设无法计算时返回0，上层需处理
            raise ValueError("需要至少30个历史价格数据点来预测波动率")
        
        # 1. 计算对数收益率
        # log_return = ln(Pt / Pt-1)
        returns = []
        for i in range(1, len(price_history)):
            if price_history[i-1] > 0:
                val = price_history[i] / price_history[i-1]
                if val > 0:
                    returns.append(math.log(val))
                else:
                    returns.append(0.0)
            else:
                returns.append(0.0)
                
        returns_array = np.array(returns)

        # 2. 尝试 GARCH 模型
        if method == "garch":
            try:
                from arch import arch_model
                # arch_model 通常对数值放大的数据表现更好 (x100)
                model = arch_model(returns_array * 100, vol='Garch', p=1, q=1)
                res = model.fit(disp='off')
                forecast = res.forecast(horizon=1)
                # 获取方差并还原比例 (/10000)
                variance = forecast.variance.values[-1, 0] / 10000
                return math.sqrt(variance * 252)
            except (ImportError, Exception):
                # 如果失败，自动降级到 EWMA
                return self.forecast_realized_volatility(price_history, method="ewma")

        # 3. EWMA 模型 (RiskMetrics)
        # Lambda = 0.94 是日度数据的行业标准
        lambda_factor = 0.94
        n = len(returns_array)
        
        # 生成权重: (1-lambda) * lambda^(n-1-i)
        weights = (1 - lambda_factor) * (lambda_factor ** np.arange(n)[::-1])
        # 归一化权重
        weights /= weights.sum()
        
        # 加权方差
        variance = np.sum(weights * (returns_array ** 2))
        
        # 年化波动率 = sqrt(日方差 * 252)
        return math.sqrt(variance * 252)

    def calculate_vrp_result(
        self,
        current_iv: float,
        price_history: List[float],
        iv_history: Optional[List[float]] = None
    ) -> VRPResult:
        """
        计算完整的 VRP 分析结果
        """
        # 1. 预测 RV
        try:
            rv_forecast = self.forecast_realized_volatility(price_history)
        except ValueError:
            # 如果历史价格不足，暂时使用当前IV作为RV的替代（即VRP=0），避免崩溃
            rv_forecast = current_iv
            
        # 2. 计算 VRP
        vrp = self.calculate_vrp(current_iv, rv_forecast)
        
        # 3. 计算 Rank/Percentile
        iv_rank = 50.0
        iv_percentile = 50.0
        if iv_history:
            iv_rank = self.calculate_iv_rank(current_iv, iv_history)
            iv_percentile = self.calculate_iv_percentile(current_iv, iv_history)
        
        # 4. 生成建议
        if vrp > 0.05:
            recommendation = "sell"  # IV 显著高于 RV，卖出波动率有利
        elif vrp < -0.05:
            recommendation = "buy"   # IV 显著低于 RV，买入波动率有利
        else:
            recommendation = "neutral"
            
        return VRPResult(
            vrp=vrp,
            iv=current_iv,
            rv_forecast=rv_forecast,
            iv_rank=iv_rank,
            iv_percentile=iv_percentile,
            recommendation=recommendation
        )

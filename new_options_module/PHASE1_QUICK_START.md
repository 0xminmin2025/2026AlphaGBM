# Phase 1 快速入门指南

## 概述

这是Phase 1外部开发的快速入门指南。详细文档请参考 `PHASE1_DEVELOPMENT_GUIDE.md`。

---

## 一、需要开发的两个模块

### 1. VRP计算器（VRP Calculator）
**文件**：`vrp_calculator.py`

**核心功能**：
- 计算VRP = IV - RV（波动率风险溢价）
- 计算IV Rank和IV Percentile
- 预测已实现波动率（RV）

**关键函数**：
```python
calculate_vrp(iv, rv_forecast) -> float
calculate_iv_rank(current_iv, iv_history) -> float
forecast_realized_volatility(price_history, method="garch") -> float
calculate_vrp_result(current_iv, price_history, iv_history) -> VRPResult
```

### 2. 风险调整器（Risk Adjuster）
**文件**：`risk_adjuster.py`

**核心功能**：
- 计算期望值（Expected Value）
- 计算风险调整后期望值（Risk-Adjusted Expectancy）
- 计算尾部风险（Tail Risk / VaR）

**关键函数**：
```python
calculate_expected_value(win_prob, avg_profit, avg_loss) -> float
calculate_risk_adjusted_expectancy(expected_value, max_loss) -> float
analyze_risk(win_prob, avg_profit, avg_loss, max_loss) -> RiskAnalysis
```

---

## 二、最小实现示例

### VRP计算器最小实现

```python
# vrp_calculator.py

import math
import bisect
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class VRPResult:
    vrp: float
    iv: float
    rv_forecast: float
    iv_rank: float
    iv_percentile: float
    recommendation: str

class VRPCalculator:
    def __init__(self, risk_free_rate: float = 0.05):
        self.risk_free_rate = risk_free_rate
    
    def calculate_vrp(self, iv: float, rv_forecast: float) -> float:
        """计算VRP = IV - RV"""
        return iv - rv_forecast
    
    def calculate_iv_rank(self, current_iv: float, iv_history: List[float]) -> float:
        """计算IV Rank (0-100)"""
        if not iv_history or len(iv_history) < 10:
            return 50.0
        sorted_iv = sorted(iv_history)
        rank = bisect.bisect_left(sorted_iv, current_iv)
        return (rank / len(sorted_iv)) * 100.0
    
    def forecast_realized_volatility(self, price_history: List[float], method: str = "ewma") -> float:
        """预测已实现波动率（简化版：使用EWMA）"""
        if len(price_history) < 30:
            raise ValueError("需要至少30个历史价格数据点")
        
        # 计算对数收益率
        import numpy as np
        returns = [math.log(price_history[i] / price_history[i-1]) 
                   for i in range(1, len(price_history)) if price_history[i-1] > 0]
        
        # EWMA方法（简化版）
        lambda_factor = 0.94
        window = min(30, len(returns))
        variance = np.var(returns[-window:])
        rv = math.sqrt(variance * 252)  # 年化
        
        return rv
    
    def calculate_vrp_result(self, current_iv: float, price_history: List[float], 
                            iv_history: Optional[List[float]] = None) -> VRPResult:
        """计算完整的VRP结果"""
        rv_forecast = self.forecast_realized_volatility(price_history)
        vrp = self.calculate_vrp(current_iv, rv_forecast)
        
        iv_rank = self.calculate_iv_rank(current_iv, iv_history) if iv_history else 50.0
        iv_percentile = iv_rank  # 简化版：使用IV Rank作为IV Percentile
        
        recommendation = "sell" if vrp > 0.05 else ("buy" if vrp < -0.05 else "neutral")
        
        return VRPResult(
            vrp=vrp,
            iv=current_iv,
            rv_forecast=rv_forecast,
            iv_rank=iv_rank,
            iv_percentile=iv_rank,
            recommendation=recommendation
        )
```

### 风险调整器最小实现

```python
# risk_adjuster.py

from typing import Optional, Dict
from dataclasses import dataclass
from enum import Enum

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"

@dataclass
class RiskAnalysis:
    expected_value: float
    risk_adjusted_expectancy: float
    max_loss: float
    tail_risk_var: float
    win_rate: float
    risk_level: RiskLevel
    tail_risk_warning: str

class RiskAdjuster:
    def __init__(self, risk_free_rate: float = 0.05):
        self.risk_free_rate = risk_free_rate
    
    def calculate_expected_value(self, win_prob: float, avg_profit: float, avg_loss: float) -> float:
        """计算期望值"""
        loss_prob = 1.0 - win_prob
        return (win_prob * avg_profit) - (loss_prob * avg_loss)
    
    def calculate_risk_adjusted_expectancy(self, expected_value: float, max_loss: float) -> float:
        """计算风险调整后期望值"""
        if max_loss <= 0:
            return 0.0
        return expected_value / max_loss
    
    def analyze_risk(self, win_prob: float, avg_profit: float, avg_loss: float, 
                    max_loss: float) -> RiskAnalysis:
        """完整的风险分析"""
        expected_value = self.calculate_expected_value(win_prob, avg_profit, avg_loss)
        risk_adjusted_expectancy = self.calculate_risk_adjusted_expectancy(expected_value, max_loss)
        
        # 简化版尾部风险
        tail_risk_var = max_loss * 1.5  # 假设极端情况下损失增加50%
        
        # 确定风险等级
        if risk_adjusted_expectancy > 0.5:
            risk_level = RiskLevel.LOW
        elif risk_adjusted_expectancy > 0.2:
            risk_level = RiskLevel.MEDIUM
        elif risk_adjusted_expectancy > 0:
            risk_level = RiskLevel.HIGH
        else:
            risk_level = RiskLevel.EXTREME
        
        # 生成警告
        warning = ""
        if win_prob > 0.9 and max_loss > avg_profit * 10:
            warning = "警告：虽然胜率很高，但一旦亏损，损失可能是盈利的10倍以上"
        elif risk_adjusted_expectancy < 0:
            warning = "警告：期望值为负，不建议进行此交易"
        
        return RiskAnalysis(
            expected_value=expected_value,
            risk_adjusted_expectancy=risk_adjusted_expectancy,
            max_loss=max_loss,
            tail_risk_var=tail_risk_var,
            win_rate=win_prob * 100,
            risk_level=risk_level,
            tail_risk_warning=warning
        )
```

---

## 三、测试代码模板

```python
# test_phase1.py

from vrp_calculator import VRPCalculator, VRPResult
from risk_adjuster import RiskAdjuster, RiskAnalysis

def test_vrp():
    """测试VRP计算"""
    calculator = VRPCalculator()
    
    # 测试基本VRP计算
    vrp = calculator.calculate_vrp(0.30, 0.25)  # IV=30%, RV=25%
    assert abs(vrp - 0.05) < 0.001, f"VRP计算错误: {vrp}"
    
    # 测试IV Rank
    iv_history = [0.20, 0.25, 0.30, 0.35, 0.40]
    iv_rank = calculator.calculate_iv_rank(0.30, iv_history)
    assert 40 <= iv_rank <= 60, f"IV Rank计算错误: {iv_rank}"
    
    print("✅ VRP计算器测试通过")

def test_risk():
    """测试风险调整器"""
    adjuster = RiskAdjuster()
    
    # 测试期望值
    ev = adjuster.calculate_expected_value(0.8, 100, 500)  # 80%胜率
    assert ev == (0.8 * 100) - (0.2 * 500), f"期望值计算错误: {ev}"
    
    # 测试风险调整后期望值
    rae = adjuster.calculate_risk_adjusted_expectancy(100, 5000)
    assert abs(rae - 0.02) < 0.001, f"风险调整后期望值计算错误: {rae}"
    
    print("✅ 风险调整器测试通过")

if __name__ == "__main__":
    test_vrp()
    test_risk()
    print("\n🎉 所有测试通过！")
```

---

## 四、数据格式说明

### 输入数据格式

**价格历史**（List[float]）：
```python
price_history = [100.0, 102.5, 101.8, 103.2, 105.0, ...]
# 从旧到新的时间序列
```

**IV历史**（List[float]，可选）：
```python
iv_history = [0.20, 0.25, 0.28, 0.30, ...]
# 小数形式（0.20表示20%）
```

**期权数据**（Dict）：
```python
option_data = {
    "strike": 150.0,
    "premium": 2.5,
    "implied_vol": 0.30,  # 30%
    "type": "call",  # or "put"
    "margin": 5000
}
```

### 输出数据格式

**VRP结果**：
```python
VRPResult(
    vrp=0.05,              # VRP值（5%）
    iv=0.30,               # 当前IV（30%）
    rv_forecast=0.25,      # 预测RV（25%）
    iv_rank=75.0,          # IV Rank（75%）
    iv_percentile=75.0,    # IV Percentile（75%）
    recommendation="sell"  # 推荐：卖出
)
```

**风险分析结果**：
```python
RiskAnalysis(
    expected_value=50.0,                # 期望值$50
    risk_adjusted_expectancy=0.005,     # 风险调整后期望值0.5%
    max_loss=10000.0,                   # 最大亏损$10000
    tail_risk_var=15000.0,              # 尾部风险$15000
    win_rate=85.0,                      # 胜率85%
    risk_level=RiskLevel.HIGH,          # 风险等级：高
    tail_risk_warning="警告：..."       # 风险警告
)
```

---

## 五、交付清单

开发完成后，请提供：

1. ✅ **源代码文件**：
   - `vrp_calculator.py`
   - `risk_adjuster.py`
   - `__init__.py`（如果作为包）

2. ✅ **测试代码**：
   - `test_vrp.py`
   - `test_risk.py`

3. ✅ **依赖列表**：
   - `requirements.txt`

4. ✅ **使用示例**：
   - `example_usage.py`（可选但推荐）

5. ✅ **README**：
   - 简要说明如何使用

---

## 六、常见问题

### Q: 如果历史数据不足怎么办？
**A**: 返回合理的默认值（如IV Rank返回50.0），不要抛出异常。

### Q: GARCH模型必须实现吗？
**A**: 不必须。可以先实现EWMA方法，GARCH作为可选项。

### Q: 需要处理哪些边界情况？
**A**: 
- 数据为空或不足
- 除零错误
- 负数或异常值
- 所有函数都要有合理的默认值和错误处理

---

## 七、下一步

开发完成后：
1. 将代码文件发给我
2. 我会集成到现有系统中
3. 我们测试集成后的功能
4. 根据测试结果进行调整

---

**文档版本**：v1.0  
**分支**：feature/commercial-optimization

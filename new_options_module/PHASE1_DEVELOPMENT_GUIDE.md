# Phase 1 开发指南

## 概述

本文档详细说明如何在外部开发 Phase 1 的核心功能，包括VRP计算模块、风险调整后期望值和波动率偏斜校正。完成后，这些模块将集成到现有的 Alpha GBM 系统中。

---

## 一、开发环境准备

### 1.1 技术栈要求

**必需依赖**：
- Python 3.8+
- NumPy
- SciPy
- Pandas
- 可选：Arch（GARCH模型）

**可选依赖（高级功能）**：
- statsmodels（GARCH模型）
- scikit-learn（机器学习辅助）

### 1.2 项目结构

建议的独立开发结构：
```
phase1_modules/
├── __init__.py
├── vrp_calculator.py          # VRP计算模块
├── risk_adjuster.py           # 风险调整模块
├── volatility_surface.py      # 波动率曲面模块（可选，Phase 1.3）
├── test/
│   ├── test_vrp.py
│   ├── test_risk.py
│   └── test_volatility.py
└── requirements.txt
```

---

## 二、模块1：VRP计算器（VRP Calculator）

### 2.1 功能说明

**VRP（Volatility Risk Premium）** = 隐含波动率（IV）- 已实现波动率（RV）

这是期权市场的核心Alpha来源。当IV > RV时，卖出期权更有利；当IV < RV时，买入期权更有利。

### 2.2 接口定义

```python
# vrp_calculator.py

from typing import List, Optional, Dict
from dataclasses import dataclass

@dataclass
class VRPResult:
    """VRP计算结果"""
    vrp: float                    # VRP值（IV - RV）
    iv: float                     # 当前隐含波动率
    rv_forecast: float            # 预测的已实现波动率
    iv_rank: float                # IV Rank (0-100)
    iv_percentile: float          # IV Percentile (0-100)
    recommendation: str           # "sell" or "buy" or "neutral"


class VRPCalculator:
    """
    波动率风险溢价（VRP）计算器
    
    核心功能：
    1. 计算VRP（IV - RV）
    2. 计算IV Rank和IV Percentile
    3. 预测已实现波动率（RV）
    4. 生成交易建议
    """
    
    def __init__(self, risk_free_rate: float = 0.05):
        """
        初始化VRP计算器
        
        Args:
            risk_free_rate: 无风险利率，默认5%
        """
        self.risk_free_rate = risk_free_rate
    
    def calculate_vrp(self, iv: float, rv_forecast: float) -> float:
        """
        计算VRP
        
        Args:
            iv: 隐含波动率（小数形式，如0.20表示20%）
            rv_forecast: 预测的已实现波动率（小数形式）
        
        Returns:
            VRP值（小数形式），正数表示IV高于RV，负数表示IV低于RV
        """
        return iv - rv_forecast
    
    def calculate_iv_rank(
        self, 
        current_iv: float, 
        iv_history: List[float]
    ) -> float:
        """
        计算IV Rank（0-100）
        
        IV Rank = (当前IV在历史IV中的排名) / 历史总数 × 100
        
        Args:
            current_iv: 当前隐含波动率
            iv_history: 历史隐含波动率列表（至少需要30个数据点）
        
        Returns:
            IV Rank (0-100)，值越高表示IV越处于历史高位
        """
        if not iv_history or len(iv_history) < 10:
            # 如果历史数据不足，返回估算值
            return 50.0
        
        sorted_iv = sorted(iv_history)
        rank = bisect.bisect_left(sorted_iv, current_iv)
        iv_rank = (rank / len(sorted_iv)) * 100.0
        
        return min(100.0, max(0.0, iv_rank))
    
    def calculate_iv_percentile(
        self, 
        current_iv: float, 
        iv_history: List[float]
    ) -> float:
        """
        计算IV Percentile（0-100）
        
        IV Percentile和IV Rank类似，但计算方法略有不同
        
        Args:
            current_iv: 当前隐含波动率
            iv_history: 历史隐含波动率列表
        
        Returns:
            IV Percentile (0-100)
        """
        if not iv_history or len(iv_history) < 10:
            return 50.0
        
        # 计算有多少百分比的历史IV低于当前IV
        below_count = sum(1 for iv in iv_history if iv < current_iv)
        percentile = (below_count / len(iv_history)) * 100.0
        
        return min(100.0, max(0.0, percentile))
    
    def forecast_realized_volatility(
        self, 
        price_history: List[float],
        method: str = "garch"
    ) -> float:
        """
        预测已实现波动率（RV）
        
        可以使用多种方法：
        1. 简单移动平均（Simple Moving Average）
        2. EWMA（指数加权移动平均）
        3. GARCH模型（推荐）
        
        Args:
            price_history: 历史价格列表（至少需要60个数据点）
            method: 预测方法，"sma", "ewma", 或 "garch"
        
        Returns:
            预测的已实现波动率（小数形式）
        """
        if not price_history or len(price_history) < 30:
            raise ValueError("需要至少30个历史价格数据点")
        
        # 计算对数收益率
        returns = []
        for i in range(1, len(price_history)):
            if price_history[i-1] > 0:
                log_return = math.log(price_history[i] / price_history[i-1])
                returns.append(log_return)
        
        if method == "sma":
            # 简单移动平均
            window = min(30, len(returns))
            variance = np.var(returns[-window:])
            rv = math.sqrt(variance * 252)  # 年化
        
        elif method == "ewma":
            # 指数加权移动平均（EWMA）
            lambda_factor = 0.94  # RiskMetrics标准
            weights = []
            for i in range(len(returns)):
                weights.append((1 - lambda_factor) * (lambda_factor ** (len(returns) - 1 - i)))
            weights = np.array(weights) / np.sum(weights)
            variance = np.average(np.array(returns) ** 2, weights=weights)
            rv = math.sqrt(variance * 252)  # 年化
        
        elif method == "garch":
            # GARCH(1,1)模型（推荐）
            try:
                from arch import arch_model
                returns_array = np.array(returns) * 100  # GARCH模型需要百分比形式
                model = arch_model(returns_array, vol='Garch', p=1, q=1)
                fitted_model = model.fit(disp='off')
                forecast = fitted_model.forecast(horizon=1)
                variance = forecast.variance.values[-1, 0] / 10000  # 转换回小数形式
                rv = math.sqrt(variance * 252)  # 年化
            except ImportError:
                # 如果没有arch库，降级到EWMA
                return self.forecast_realized_volatility(price_history, method="ewma")
            except Exception:
                # 如果GARCH拟合失败，降级到EWMA
                return self.forecast_realized_volatility(price_history, method="ewma")
        
        else:
            raise ValueError(f"未知的预测方法: {method}")
        
        return rv
    
    def calculate_vrp_result(
        self,
        current_iv: float,
        price_history: List[float],
        iv_history: Optional[List[float]] = None
    ) -> VRPResult:
        """
        计算完整的VRP分析结果
        
        Args:
            current_iv: 当前隐含波动率
            price_history: 历史价格列表
            iv_history: 历史IV列表（可选，如果提供可以计算IV Rank）
        
        Returns:
            VRPResult对象，包含所有计算结果
        """
        # 预测已实现波动率
        rv_forecast = self.forecast_realized_volatility(price_history)
        
        # 计算VRP
        vrp = self.calculate_vrp(current_iv, rv_forecast)
        
        # 计算IV Rank和IV Percentile
        iv_rank = 50.0  # 默认值
        iv_percentile = 50.0  # 默认值
        
        if iv_history and len(iv_history) >= 10:
            iv_rank = self.calculate_iv_rank(current_iv, iv_history)
            iv_percentile = self.calculate_iv_percentile(current_iv, iv_history)
        
        # 生成交易建议
        if vrp > 0.05:  # VRP > 5%
            recommendation = "sell"  # 推荐卖出（做空波动率）
        elif vrp < -0.05:  # VRP < -5%
            recommendation = "buy"  # 推荐买入（做多波动率）
        else:
            recommendation = "neutral"  # 中性
        
        return VRPResult(
            vrp=vrp,
            iv=current_iv,
            rv_forecast=rv_forecast,
            iv_rank=iv_rank,
            iv_percentile=iv_percentile,
            recommendation=recommendation
        )
```

### 2.3 使用示例

```python
from vrp_calculator import VRPCalculator

# 初始化计算器
calculator = VRPCalculator()

# 示例数据
current_iv = 0.30  # 30%的隐含波动率
price_history = [100, 102, 101, 103, 105, ...]  # 历史价格列表
iv_history = [0.20, 0.25, 0.28, 0.30, ...]  # 历史IV列表（可选）

# 计算VRP结果
result = calculator.calculate_vrp_result(
    current_iv=current_iv,
    price_history=price_history,
    iv_history=iv_history
)

print(f"VRP: {result.vrp:.4f}")
print(f"IV Rank: {result.iv_rank:.2f}%")
print(f"推荐: {result.recommendation}")
```

### 2.4 注意事项

1. **历史数据要求**：
   - 价格历史：至少30个数据点，推荐60+（约3个月）
   - IV历史：至少10个数据点，推荐30+（约1个月）

2. **数据格式**：
   - 所有波动率使用小数形式（0.20表示20%）
   - 价格历史应该是时间序列（从旧到新）

3. **性能考虑**：
   - GARCH模型计算较慢，可以先用EWMA
   - IV Rank计算需要排序，时间复杂度O(n log n)

---

## 三、模块2：风险调整器（Risk Adjuster）

### 3.1 功能说明

**风险调整后期望值** = 期望值 / 最大潜在亏损

包含尾部风险惩罚，避免用户因高胜率而忽略极端风险。

### 3.2 接口定义

```python
# risk_adjuster.py

from typing import Optional, Dict
from dataclasses import dataclass
from enum import Enum

class RiskLevel(str, Enum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


@dataclass
class RiskAnalysis:
    """风险分析结果"""
    expected_value: float            # 期望值
    risk_adjusted_expectancy: float  # 风险调整后期望值
    max_loss: float                  # 最大潜在亏损
    tail_risk_var: float             # 尾部风险（99% VaR）
    win_rate: float                  # 胜率（0-100）
    risk_level: RiskLevel            # 风险等级
    tail_risk_warning: str           # 尾部风险警告


class RiskAdjuster:
    """
    风险调整器
    
    核心功能：
    1. 计算期望值（Expected Value）
    2. 计算风险调整后期望值（Risk-Adjusted Expectancy）
    3. 计算尾部风险（Tail Risk / VaR）
    4. 生成风险警告
    """
    
    def __init__(self, risk_free_rate: float = 0.05):
        """
        初始化风险调整器
        
        Args:
            risk_free_rate: 无风险利率，默认5%
        """
        self.risk_free_rate = risk_free_rate
    
    def calculate_expected_value(
        self,
        win_prob: float,
        avg_profit: float,
        avg_loss: float
    ) -> float:
        """
        计算期望值（Expected Value）
        
        EV = (Win Prob × Avg Profit) - (Loss Prob × Avg Loss)
        
        Args:
            win_prob: 盈利概率（0-1，如0.75表示75%）
            avg_profit: 平均盈利金额
            avg_loss: 平均亏损金额（正数）
        
        Returns:
            期望值（美元）
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
        计算风险调整后期望值
        
        RAE = EV / Max Loss
        
        Args:
            expected_value: 期望值
            max_loss: 最大潜在亏损
        
        Returns:
            风险调整后期望值（比率），值越高越好
        """
        if max_loss <= 0:
            return 0.0
        return expected_value / max_loss
    
    def calculate_tail_risk(
        self,
        option_data: Dict,  # 包含strike, premium, margin等信息
        stock_price: float,
        price_history: Optional[List[float]] = None,
        confidence_level: float = 0.99
    ) -> float:
        """
        计算尾部风险（VaR - Value at Risk）
        
        使用历史极端事件数据或Monte Carlo模拟
        
        Args:
            option_data: 期权数据字典
            stock_price: 当前股票价格
            price_history: 历史价格（用于计算波动率）
            confidence_level: 置信水平，默认99%
        
        Returns:
            尾部风险值（美元），表示在(1-confidence_level)概率下的最大亏损
        """
        # 简化实现：基于历史波动率和极端事件
        # 在完整实现中，应该使用Monte Carlo模拟或历史极端事件数据
        
        strike = option_data.get('strike', 0)
        premium = option_data.get('premium', 0)
        margin = option_data.get('margin', 0)
        option_type = option_data.get('type', 'call')  # 'call' or 'put'
        
        # 计算最大潜在亏损
        if option_type == 'put':
            # 卖出看跌：最大亏损 = 行权价 - 0（股票归零）
            max_loss = strike * 100 - premium * 100  # 假设每张合约100股
        else:
            # 卖出看涨：最大亏损 = 无限（理论上）
            # 实际使用保证金作为最大亏损
            max_loss = margin
        
        # 基于历史极端事件调整（简化版）
        # 实际应该使用历史崩盘数据（如2020年3月、2022年等）
        extreme_multiplier = 1.5  # 极端事件中损失可能是理论最大损失的1.5倍
        
        tail_risk = max_loss * extreme_multiplier * (1 - confidence_level)
        
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
        完整的风险分析
        
        Args:
            win_prob: 盈利概率（0-1）
            avg_profit: 平均盈利
            avg_loss: 平均亏损
            max_loss: 最大潜在亏损
            option_data: 期权数据（可选，用于计算尾部风险）
            stock_price: 股票价格（可选，用于计算尾部风险）
        
        Returns:
            RiskAnalysis对象
        """
        # 计算期望值
        expected_value = self.calculate_expected_value(win_prob, avg_profit, avg_loss)
        
        # 计算风险调整后期望值
        risk_adjusted_expectancy = self.calculate_risk_adjusted_expectancy(
            expected_value, max_loss
        )
        
        # 计算尾部风险
        tail_risk_var = max_loss  # 默认值
        if option_data and stock_price:
            tail_risk_var = self.calculate_tail_risk(
                option_data, stock_price, confidence_level=0.99
            )
        
        # 确定风险等级
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
        
        # 生成风险警告
        warning = ""
        if tail_risk_var > max_loss * 1.5:
            warning = f"警告：尾部风险（99% VaR）为${tail_risk_var:.2f}，可能超过最大理论亏损"
        elif win_prob > 0.9 and max_loss > avg_profit * 10:
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

### 3.3 使用示例

```python
from risk_adjuster import RiskAdjuster

# 初始化风险调整器
adjuster = RiskAdjuster()

# 示例数据
win_prob = 0.85  # 85%胜率
avg_profit = 100  # 平均盈利$100
avg_loss = 5000  # 平均亏损$5000
max_loss = 10000  # 最大潜在亏损$10000

# 风险分析
analysis = adjuster.analyze_risk(
    win_prob=win_prob,
    avg_profit=avg_profit,
    avg_loss=avg_loss,
    max_loss=max_loss
)

print(f"期望值: ${analysis.expected_value:.2f}")
print(f"风险调整后期望值: {analysis.risk_adjusted_expectancy:.4f}")
print(f"风险等级: {analysis.risk_level}")
print(f"警告: {analysis.tail_risk_warning}")
```

---

## 四、集成说明

### 4.1 数据输入格式

**期权数据（OptionData）**：
```python
{
    "strike": 150.0,              # 行权价
    "premium": 2.5,               # 权利金
    "implied_vol": 0.30,          # 隐含波动率（30%）
    "type": "call",               # "call" or "put"
    "bid_price": 2.4,
    "ask_price": 2.6,
    "margin": 5000,               # 保证金（卖出策略）
    "expiry_date": "2025-02-21"
}
```

**股票数据（StockData）**：
```python
{
    "symbol": "AAPL",
    "current_price": 180.0,
    "price_history": [175.0, 178.0, 180.0, ...],  # 历史价格列表
    "iv_history": [0.25, 0.28, 0.30, ...]          # 历史IV列表（可选）
}
```

### 4.2 输出格式

**VRP结果**：
```python
{
    "vrp": 0.05,                  # VRP值（5%）
    "iv": 0.30,                   # 当前IV（30%）
    "rv_forecast": 0.25,          # 预测RV（25%）
    "iv_rank": 75.0,              # IV Rank（75%）
    "iv_percentile": 78.0,        # IV Percentile（78%）
    "recommendation": "sell"      # 推荐：卖出
}
```

**风险分析结果**：
```python
{
    "expected_value": 50.0,       # 期望值$50
    "risk_adjusted_expectancy": 0.005,  # 风险调整后期望值0.5%
    "max_loss": 10000.0,          # 最大亏损$10000
    "tail_risk_var": 15000.0,     # 尾部风险$15000
    "win_rate": 85.0,             # 胜率85%
    "risk_level": "high",         # 风险等级：高
    "tail_risk_warning": "警告：尾部风险可能超过最大理论亏损"
}
```

### 4.3 集成到现有系统

**后端集成（Python）**：
```python
# 在 option_service.py 中

from phase1_modules.vrp_calculator import VRPCalculator
from phase1_modules.risk_adjuster import RiskAdjuster

# 初始化
vrp_calculator = VRPCalculator()
risk_adjuster = RiskAdjuster()

# 在计算推荐值时使用
def calculate_enhanced_recommendation(option, scores, stock_price, price_history):
    # 1. 计算VRP
    vrp_result = vrp_calculator.calculate_vrp_result(
        current_iv=option.implied_vol,
        price_history=price_history
    )
    
    # 2. 计算风险分析
    risk_analysis = risk_adjuster.analyze_risk(
        win_prob=scores.win_rate / 100,
        avg_profit=scores.premium_income,
        avg_loss=scores.margin_requirement,
        max_loss=scores.margin_requirement
    )
    
    # 3. 在推荐值中加入VRP和风险调整因子
    # ... 整合逻辑
    
    return enhanced_recommendation
```

**前端集成（JavaScript）**：
```javascript
// 在 frontend.html 中

// 调用后端API获取VRP和风险分析
async function getEnhancedAnalysis(option, scores, stockPrice) {
    const response = await fetch(`/api/enhanced-analysis/${symbol}/${strike}`);
    const data = await response.json();
    
    // data.vrp_result - VRP计算结果
    // data.risk_analysis - 风险分析结果
    
    return data;
}

// 在推荐值计算中使用
function calculateRecommendation(option, scores, stockPrice) {
    // 获取VRP和风险分析
    const enhanced = await getEnhancedAnalysis(option, scores, stockPrice);
    
    // 在评分中加入VRP因子
    if (enhanced.vrp_result.vrp > 0.05) {
        score += 10;  // VRP优势加分
    }
    
    // 在评分中加入风险调整因子
    if (enhanced.risk_analysis.risk_adjusted_expectancy > 0.5) {
        score += 5;  // 风险调整后期望值高加分
    }
    
    return { value: score, ... };
}
```

---

## 五、测试要求

### 5.1 单元测试

**VRP计算器测试**：
```python
# test/test_vrp.py

def test_calculate_vrp():
    """测试VRP计算"""
    calculator = VRPCalculator()
    vrp = calculator.calculate_vrp(0.30, 0.25)  # IV=30%, RV=25%
    assert vrp == 0.05  # VRP应该为5%

def test_iv_rank():
    """测试IV Rank计算"""
    calculator = VRPCalculator()
    iv_history = [0.20, 0.25, 0.30, 0.35, 0.40]
    iv_rank = calculator.calculate_iv_rank(0.30, iv_history)
    assert 40 <= iv_rank <= 60  # 30%应该在中间位置

def test_forecast_rv():
    """测试RV预测"""
    calculator = VRPCalculator()
    price_history = [100 + i*0.5 + random.random() for i in range(60)]
    rv = calculator.forecast_realized_volatility(price_history)
    assert 0 < rv < 1  # RV应该在合理范围内
```

**风险调整器测试**：
```python
# test/test_risk.py

def test_expected_value():
    """测试期望值计算"""
    adjuster = RiskAdjuster()
    ev = adjuster.calculate_expected_value(0.8, 100, 500)  # 80%胜率
    assert ev > 0  # 期望值应该为正

def test_risk_adjusted_expectancy():
    """测试风险调整后期望值"""
    adjuster = RiskAdjuster()
    ev = 100
    max_loss = 5000
    rae = adjuster.calculate_risk_adjusted_expectancy(ev, max_loss)
    assert rae == 0.02  # 100/5000 = 0.02
```

### 5.2 集成测试

测试与现有系统的集成：
- 测试数据格式兼容性
- 测试API接口
- 测试前端显示

---

## 六、交付要求

### 6.1 代码要求

1. **代码格式**：
   - 遵循PEP 8规范
   - 添加类型提示（Type Hints）
   - 添加完整的文档字符串（Docstrings）

2. **代码质量**：
   - 通过所有单元测试
   - 代码覆盖率 > 80%
   - 通过Linter检查（flake8或pylint）

3. **文档要求**：
   - 每个函数有清晰的文档说明
   - 包含使用示例
   - 说明参数和返回值

### 6.2 交付文件

1. **源代码**：
   - `vrp_calculator.py`
   - `risk_adjuster.py`
   - `__init__.py`

2. **测试代码**：
   - `test_vrp.py`
   - `test_risk.py`

3. **文档**：
   - `README.md`（使用说明）
   - `API_DOC.md`（API文档）

4. **配置文件**：
   - `requirements.txt`（依赖列表）
   - `setup.py`（可选，用于打包）

### 6.3 示例数据

提供测试用的示例数据：
- 示例价格历史（CSV格式）
- 示例IV历史（CSV格式）
- 示例期权数据（JSON格式）

---

## 七、常见问题（FAQ）

### Q1: 如果没有历史IV数据怎么办？
**A**: IV Rank和IV Percentile可以返回默认值（50），或者使用简化的估算方法。

### Q2: GARCH模型计算太慢怎么办？
**A**: 可以先实现EWMA方法，GARCH作为可选项。在实际使用中，EWMA已经足够好。

### Q3: 如何处理数据不足的情况？
**A**: 所有函数都应该有合理的默认值和错误处理。如果数据不足，返回默认值或抛出明确的错误。

### Q4: 尾部风险如何精确计算？
**A**: Phase 1可以使用简化版本（基于历史波动率）。完整的尾部风险分析需要Monte Carlo模拟，可以在Phase 2实现。

---

## 八、联系方式

如果在开发过程中遇到问题，可以：
1. 查看 `COMMERCIAL_OPTIMIZATION_PLAN.md` 了解整体方案
2. 查看 `OPTION_SELECTION_LOGIC.md` 了解现有逻辑
3. 查看现有代码 `scoring/option_scorer.py` 了解代码风格

---

**文档版本**：v1.0  
**创建日期**：2025年1月  
**分支**：feature/commercial-optimization

# 期权分析算法标准文档

本文档定义了期权分析系统的算法标准、评分方法和参数配置。

## 📋 目录

- [算法概述](#算法概述)
- [期权数据获取](#期权数据获取)
- [流动性评分算法](#流动性评分算法)
- [IV 排名与百分位](#iv-排名与百分位)
- [期权评分系统](#期权评分系统)
- [VRP 波动率风险溢价](#vrp-波动率风险溢价)
- [风险调整算法](#风险调整算法)
- [策略推荐算法](#策略推荐算法)
- [参数配置](#参数配置)

## 🎯 算法概述

期权分析系统提供实时的期权链数据分析和量化评分，帮助投资者：

- 评估期权流动性
- 分析隐含波动率（IV）
- 计算波动率风险溢价（VRP）
- 提供策略推荐（买入/卖出看涨/看跌）

## 📊 期权数据获取

### 数据源

- **主要数据源**：Tiger OpenAPI
- **备用方案**：Mock 数据（测试环境）

### 数据字段

```python
class OptionData:
    identifier: str          # 期权标识符
    symbol: str             # 标的股票代码
    strike: float            # 行权价
    put_call: str            # CALL 或 PUT
    expiry_date: str         # 到期日
    latest_price: float      # 最新价
    bid_price: float         # 买价
    ask_price: float         # 卖价
    volume: int              # 成交量
    open_interest: int       # 持仓量（OI）
    implied_vol: float       # 隐含波动率
    delta: float             # Delta
    gamma: float              # Gamma
    theta: float              # Theta
    vega: float              # Vega
```

## 💧 流动性评分算法

### 流动性因子计算

流动性因子范围：**0.0 - 1.0**，分数越高流动性越好。

### 一票否决规则

```python
# OI < 10 直接返回 0.0（流动性不足）
if open_interest < 10:
    return 0.0
```

### 价差评分（Spread Score，权重：40%）

```python
mid_price = (bid_price + ask_price) / 2
spread_ratio = (ask_price - bid_price) / mid_price

if spread_ratio <= 0.01:      # < 1%
    spread_score = 1.0
elif spread_ratio <= 0.03:   # 1-3%
    spread_score = 0.8 + (0.03 - spread_ratio) / 0.02 * 0.2
elif spread_ratio <= 0.05:   # 3-5%
    spread_score = 0.5 + (0.05 - spread_ratio) / 0.02 * 0.3
elif spread_ratio <= 0.10:   # 5-10%
    spread_score = 0.2 + (0.10 - spread_ratio) / 0.05 * 0.3
else:                         # > 10%
    spread_score = 0.0
```

### 持仓量评分（OI Score，权重：60%）

```python
if open_interest >= 500:
    oi_score = 1.0
elif open_interest >= 200:
    oi_score = 0.8 + (open_interest - 200) / 300 * 0.15
elif open_interest >= 50:
    oi_score = 0.6 + (open_interest - 50) / 150 * 0.2
elif open_interest >= 10:
    oi_score = 0.3 + (open_interest - 10) / 40 * 0.3
else:
    oi_score = 0.0
```

### 综合流动性因子

```python
liquidity_factor = 0.4 * spread_score + 0.6 * oi_score
```

## 📈 IV 排名与百分位

### IV 排名（IV Rank）

IV Rank 表示当前 IV 在历史 IV 范围中的位置。

**简化计算**（基于当前 IV 值估算）：

```python
def calculate_iv_rank(implied_vol: float) -> float:
    if implied_vol < 0.15:      # 低 IV
        return 20.0
    elif implied_vol < 0.25:    # 中等 IV
        return 40.0
    elif implied_vol < 0.35:    # 偏高 IV
        return 60.0
    elif implied_vol < 0.50:    # 高 IV
        return 80.0
    else:                        # 极高 IV
        return 95.0
```

**完整计算**（需要历史 IV 数据）：

```python
iv_rank = (current_iv - min_iv) / (max_iv - min_iv) * 100
```

### IV 百分位（IV Percentile）

IV Percentile 表示历史上有多少比例的 IV 值低于当前 IV。

```python
iv_percentile = min(99.0, iv_rank + 5.0)  # 通常略高于 IV Rank
```

### IV 评估标准

| IV Rank | IV Percentile | 评估 | 策略建议 |
|---------|---------------|------|---------|
| 0-20    | 0-25          | 低 IV | 适合买入期权 |
| 20-40   | 25-45         | 中等偏低 | 谨慎买入 |
| 40-60   | 45-65         | 中等 | 中性 |
| 60-80   | 65-85         | 中等偏高 | 适合卖出期权 |
| 80-100  | 85-100        | 高 IV | 强烈建议卖出 |

## 🎯 期权评分系统

### 综合评分计算

期权综合评分由多个维度加权计算：

```python
total_score = (
    liquidity_score * 0.30 +      # 流动性（30%）
    iv_score * 0.25 +              # IV 排名（25%）
    moneyness_score * 0.20 +       # 虚实值程度（20%）
    time_score * 0.15 +            # 时间价值（15%）
    greeks_score * 0.10            # Greeks 指标（10%）
)
```

### 各维度评分

#### 1. 流动性评分（30%）

直接使用流动性因子：

```python
liquidity_score = liquidity_factor  # 0.0 - 1.0
```

#### 2. IV 评分（25%）

基于 IV Rank：

```python
if iv_rank < 20:
    iv_score = 1.0      # 低 IV，适合买入
elif iv_rank < 40:
    iv_score = 0.8
elif iv_rank < 60:
    iv_score = 0.5      # 中等 IV
elif iv_rank < 80:
    iv_score = 0.3      # 高 IV，适合卖出
else:
    iv_score = 0.1      # 极高 IV
```

#### 3. 虚实值评分（20%）

基于 Delta 值：

```python
# 对于买入看涨期权
if delta > 0.7:
    moneyness_score = 0.9  # 实值，高 Delta
elif delta > 0.5:
    moneyness_score = 0.7  # 平值附近
elif delta > 0.3:
    moneyness_score = 0.5  # 虚值
else:
    moneyness_score = 0.3  # 深度虚值
```

#### 4. 时间价值评分（15%）

基于到期时间：

```python
days_to_expiry = calculate_days_to_expiry(expiry_date)

if days_to_expiry < 7:
    time_score = 0.3      # 时间价值快速衰减
elif days_to_expiry < 30:
    time_score = 0.5      # 短期期权
elif days_to_expiry < 60:
    time_score = 0.7      # 中期期权
else:
    time_score = 0.9      # 长期期权，时间价值充足
```

#### 5. Greeks 评分（10%）

综合评估 Greeks 指标：

```python
# Delta 合理性
delta_score = abs(delta - 0.5) * 2  # 接近 0.5 更好

# Theta 衰减（买入期权时越小越好）
theta_score = 1.0 - min(1.0, abs(theta) / 0.1)

# Vega 敏感性（高 IV 时买入期权，Vega 越大越好）
vega_score = min(1.0, vega / 0.2)

greeks_score = (delta_score + theta_score + vega_score) / 3
```

## 📊 VRP 波动率风险溢价

### VRP 定义

VRP (Volatility Risk Premium) 表示隐含波动率与预期实际波动率之间的差异。

```
VRP = 隐含波动率 (IV) - 预期实际波动率 (RV)
```

### VRP 计算

```python
# 1. 获取隐含波动率
implied_vol = option.implied_vol

# 2. 计算预期实际波动率（基于历史波动率）
historical_vol = calculate_historical_volatility(stock_prices, period=30)

# 3. 计算 VRP
vrp = implied_vol - historical_vol

# 4. VRP 百分比
vrp_percent = (vrp / historical_vol) * 100 if historical_vol > 0 else 0
```

### VRP 评估

| VRP 范围 | 评估 | 策略建议 |
|---------|------|---------|
| VRP > 5% | 高溢价 | 适合卖出期权（收取溢价） |
| 2% < VRP ≤ 5% | 中等溢价 | 谨慎卖出 |
| -2% ≤ VRP ≤ 2% | 合理范围 | 中性 |
| -5% < VRP < -2% | 低溢价 | 谨慎买入 |
| VRP ≤ -5% | 负溢价 | 适合买入期权（便宜） |

## ⚠️ 风险调整算法

### 风险等级

```python
class RiskLevel(Enum):
    LOW = "low"           # 低风险
    MEDIUM = "medium"     # 中等风险
    HIGH = "high"         # 高风险
    VERY_HIGH = "very_high"  # 极高风险
```

### 风险因子

#### 1. 流动性风险

```python
if liquidity_factor < 0.3:
    risk_level = RiskLevel.HIGH
elif liquidity_factor < 0.5:
    risk_level = RiskLevel.MEDIUM
else:
    risk_level = RiskLevel.LOW
```

#### 2. IV 风险

```python
if iv_rank > 80:
    risk_level = RiskLevel.HIGH  # 高 IV，卖出风险高
elif iv_rank < 20:
    risk_level = RiskLevel.LOW   # 低 IV，买入风险低
```

#### 3. 时间风险

```python
if days_to_expiry < 7:
    risk_level = RiskLevel.VERY_HIGH  # 时间价值快速衰减
elif days_to_expiry < 30:
    risk_level = RiskLevel.HIGH
```

#### 4. 虚实值风险

```python
# 深度虚值期权风险高
if abs(delta) < 0.2:
    risk_level = RiskLevel.HIGH
```

### 风险调整评分

```python
# 根据风险等级调整最终评分
risk_adjustment = {
    RiskLevel.LOW: 1.0,
    RiskLevel.MEDIUM: 0.8,
    RiskLevel.HIGH: 0.5,
    RiskLevel.VERY_HIGH: 0.2
}

adjusted_score = total_score * risk_adjustment[risk_level]
```

## 🎲 策略推荐算法

### 策略类型

1. **买入看涨 (Buy Call)**
2. **买入看跌 (Buy Put)**
3. **卖出看涨 (Sell Call)**
4. **卖出看跌 (Sell Put)**

### 买入看涨策略评分

```python
def score_buy_call(option: OptionData, stock_price: float) -> float:
    score = 0.0
    
    # 流动性（必须）
    if option.liquidity_factor < 0.3:
        return 0.0
    
    # IV 低（适合买入）
    if iv_rank < 40:
        score += 0.3
    elif iv_rank > 60:
        score -= 0.2
    
    # Delta 合理（0.3-0.7）
    if 0.3 <= abs(option.delta) <= 0.7:
        score += 0.2
    
    # 时间充足（> 30天）
    if days_to_expiry > 30:
        score += 0.2
    
    # VRP 负（便宜）
    if vrp < -2:
        score += 0.3
    
    return min(1.0, max(0.0, score))
```

### 卖出看涨策略评分

```python
def score_sell_call(option: OptionData, stock_price: float) -> float:
    score = 0.0
    
    # 流动性（必须）
    if option.liquidity_factor < 0.5:
        return 0.0
    
    # IV 高（适合卖出）
    if iv_rank > 60:
        score += 0.4
    elif iv_rank < 40:
        score -= 0.2
    
    # VRP 正（收取溢价）
    if vrp > 2:
        score += 0.3
    
    # 时间衰减（Theta 大）
    if abs(option.theta) > 0.05:
        score += 0.2
    
    # 实值或平值（Delta > 0.5）
    if option.delta > 0.5:
        score += 0.1
    
    return min(1.0, max(0.0, score))
```

### 买入看跌策略评分

```python
def score_buy_put(option: OptionData, stock_price: float) -> float:
    score = 0.0
    
    # 流动性（必须）
    if option.liquidity_factor < 0.3:
        return 0.0
    
    # IV 低（适合买入）
    if iv_rank < 40:
        score += 0.3
    
    # Delta 合理（-0.7 到 -0.3）
    if -0.7 <= option.delta <= -0.3:
        score += 0.2
    
    # VRP 负（便宜）
    if vrp < -2:
        score += 0.3
    
    # 时间充足
    if days_to_expiry > 30:
        score += 0.2
    
    return min(1.0, max(0.0, score))
```

### 卖出看跌策略评分

```python
def score_sell_put(option: OptionData, stock_price: float) -> float:
    score = 0.0
    
    # 流动性（必须）
    if option.liquidity_factor < 0.5:
        return 0.0
    
    # IV 高（适合卖出）
    if iv_rank > 60:
        score += 0.4
    
    # VRP 正（收取溢价）
    if vrp > 2:
        score += 0.3
    
    # 虚值（Delta < -0.3）
    if option.delta < -0.3:
        score += 0.2
    
    # 时间衰减
    if abs(option.theta) > 0.05:
        score += 0.1
    
    return min(1.0, max(0.0, score))
```

## ⚙️ 参数配置

### 流动性参数

```python
MIN_OPEN_INTEREST = 10           # 最小持仓量（一票否决）
SPREAD_THRESHOLD_EXCELLENT = 0.01  # 优秀价差（< 1%）
SPREAD_THRESHOLD_GOOD = 0.03    # 良好价差（< 3%）
SPREAD_THRESHOLD_POOR = 0.10    # 差价差（> 10%）
OI_THRESHOLD_EXCELLENT = 500    # 优秀持仓量
OI_THRESHOLD_GOOD = 200        # 良好持仓量
OI_THRESHOLD_MIN = 50          # 最小持仓量
```

### IV 参数

```python
IV_LOW_THRESHOLD = 0.15         # 低 IV 阈值
IV_MEDIUM_THRESHOLD = 0.25      # 中等 IV 阈值
IV_HIGH_THRESHOLD = 0.35        # 高 IV 阈值
IV_VERY_HIGH_THRESHOLD = 0.50   # 极高 IV 阈值
```

### VRP 参数

```python
VRP_HIGH_THRESHOLD = 0.05       # 高 VRP 阈值（5%）
VRP_MEDIUM_THRESHOLD = 0.02     # 中等 VRP 阈值（2%）
VRP_LOW_THRESHOLD = -0.02       # 低 VRP 阈值（-2%）
VRP_VERY_LOW_THRESHOLD = -0.05  # 极低 VRP 阈值（-5%）
```

### 时间参数

```python
DAYS_TO_EXPIRY_SHORT = 7        # 短期期权（< 7天）
DAYS_TO_EXPIRY_MEDIUM = 30      # 中期期权（< 30天）
DAYS_TO_EXPIRY_LONG = 60        # 长期期权（> 60天）
```

### Delta 参数

```python
DELTA_DEEP_ITM = 0.7            # 深度实值 Delta
DELTA_ATM = 0.5                 # 平值 Delta
DELTA_DEEP_OTM = 0.2            # 深度虚值 Delta
```

## 🔄 算法流程

### 完整期权分析流程

```
1. 获取期权链数据
   ├── 通过 Tiger OpenAPI 获取实时数据
   └── 解析期权链（Calls 和 Puts）

2. 计算流动性评分
   ├── 价差评分（40%）
   └── 持仓量评分（60%）

3. 计算 IV 排名和百分位
   ├── IV Rank
   └── IV Percentile

4. 计算 VRP
   ├── 隐含波动率
   └── 预期实际波动率

5. 计算综合评分
   ├── 流动性（30%）
   ├── IV（25%）
   ├── 虚实值（20%）
   ├── 时间价值（15%）
   └── Greeks（10%）

6. 风险调整
   ├── 流动性风险
   ├── IV 风险
   ├── 时间风险
   └── 虚实值风险

7. 策略推荐
   ├── 买入看涨评分
   ├── 买入看跌评分
   ├── 卖出看涨评分
   └── 卖出看跌评分
```

## 📝 注意事项

1. **数据质量**：确保期权数据的实时性和准确性
2. **流动性优先**：流动性不足的期权不建议交易
3. **IV 评估**：结合历史 IV 数据更准确评估 IV Rank
4. **风险控制**：深度虚值期权风险高，需谨慎
5. **时间衰减**：短期期权时间价值衰减快
6. **VRP 利用**：利用 VRP 溢价进行策略选择

---

**最后更新**: 2026-01-16

# 股票分析算法标准文档

本文档定义了股票分析系统的算法标准、计算方法和参数配置。

## 📋 目录

- [算法概述](#算法概述)
- [AlphaG 模型](#alphag-模型)
- [风险评分算法](#风险评分算法)
- [目标价格计算](#目标价格计算)
- [EV 期望值模型](#ev-期望值模型)
- [止损价格计算](#止损价格计算)
- [市场情绪计算](#市场情绪计算)
- [参数配置](#参数配置)

## 🎯 算法概述

股票分析系统基于 **AlphaG (G=B+M) 模型**，将股票收益分解为：

- **G (收益 Gain)** = **B (基本面 Basics)** + **M (动量 Momentum)**

系统提供多维度的量化分析，包括风险评分、目标价格、期望值计算等。

## 📊 AlphaG 模型

### 模型公式

```
收益(G) = 基本面(B) + 动量(M)
```

### 基本面 (B) 评估

**评估维度**：

1. **财务健康度**
   - 营收增长率
   - 利润率
   - 债务水平
   - ROE/ROA

2. **估值水平**
   - PE 比率及分位点
   - PEG 比率（动态调整）
   - PB 比率

3. **增长潜力**
   - 营收增长率
   - 盈利增长率
   - 增长率折现系数

### 动量 (M) 评估

**评估维度**：

1. **技术面**
   - 价格位置（52周区间）
   - 均线关系
   - 成交量异常

2. **市场情绪**
   - VIX 恐慌指数
   - Put/Call 比率
   - 美债收益率

3. **期权市场**
   - 隐含波动率
   - 期权链数据

## ⚠️ 风险评分算法

### 评分范围

风险评分范围：**0-10 分**，分数越高风险越大。

### 评分等级

| 分数 | 风险等级 | 建议仓位调整 |
|------|---------|------------|
| 0-2  | 低风险   | 100% 基础仓位 |
| 2-4  | 中低风险 | 70% 基础仓位 |
| 4-6  | 中高风险 | 40% 基础仓位 |
| 6-8  | 高风险   | 10% 基础仓位 |
| 8-10 | 极高风险 | 0% (不建议建仓) |

### 评分因子

#### 1. PE 估值风险

```python
if pe > 60:
    risk_score += 3.0  # 极高估值
elif pe > 40:
    risk_score += 2.0  # 高估值
elif pe > 30:
    risk_score += 1.0  # 中等偏高估值
```

#### 2. PEG 估值风险

```python
# 动态 PEG 阈值（根据美债收益率调整）
treasury_yield = get_treasury_yield()
if treasury_yield > 4.0:
    peg_threshold = PEG_THRESHOLD_BASE * 0.8  # 高息环境降低阈值
else:
    peg_threshold = PEG_THRESHOLD_BASE

if peg > 2.0:
    risk_score += 2.0
elif peg > peg_threshold:
    risk_score += 1.0
```

#### 3. 增长率风险

```python
if growth_rate < -0.10:  # 负增长超过10%
    risk_score += 2.5
elif growth_rate < 0:
    risk_score += 1.5
```

#### 4. 流动性风险

```python
daily_volume_usd = avg_volume * current_price
if daily_volume_usd < MIN_DAILY_VOLUME_USD:  # 500万美元
    risk_score += 1.5
```

#### 5. 市场情绪风险

```python
if vix > 30:
    risk_score += 2.0
elif vix > 25:
    risk_score += 1.0

if put_call_ratio > 1.5:
    risk_score += 1.5
elif put_call_ratio > 1.2:
    risk_score += 0.5
```

### 风险标志 (Risk Flags)

系统会标识具体的风险点：

- `high_pe`: PE 过高
- `high_peg`: PEG 过高
- `negative_growth`: 负增长
- `low_liquidity`: 流动性不足
- `high_vix`: 市场恐慌
- `high_put_call`: 看跌情绪浓厚

## 💰 目标价格计算

### 多维度估值模型

目标价格由以下三个维度加权计算：

#### 1. PE/PEG 估值（权重：40%）

```python
# PE 估值
pe_target = current_price * (fair_pe / current_pe)

# PEG 估值（考虑增长率）
peg_target = current_price * (1 + growth_rate * GROWTH_DISCOUNT_FACTOR)

# 综合估值
valuation_target = (pe_target + peg_target) / 2
```

#### 2. 增长率折现（权重：30%）

```python
# 增长率折现
growth_multiplier = 1 + (growth_rate * GROWTH_DISCOUNT_FACTOR)
growth_target = current_price * growth_multiplier
```

#### 3. 技术面分析（权重：30%）

```python
# 基于52周区间和技术指标
if price_position < 0.3:  # 低位
    technical_target = week52_high * 0.9  # 目标接近52周高点
elif price_position > 0.8:  # 高位
    technical_target = current_price * 1.05  # 小幅上涨
else:
    technical_target = (week52_high + current_price) / 2
```

### 最终目标价格

```python
target_price = (
    valuation_target * 0.40 +
    growth_target * 0.30 +
    technical_target * 0.30
)
```

### 投资风格调整

不同投资风格对目标价格有不同影响：

- **质量 (Quality)**：更重视 PE/PEG 估值
- **价值 (Value)**：更重视低估值
- **成长 (Growth)**：更重视增长率
- **趋势 (Momentum)**：更重视技术面

## 📈 EV 期望值模型

### 核心公式

```
EV = (上涨概率 × 上涨幅度) + (下跌概率 × 下跌幅度)
```

### 多时间视界加权

```python
综合EV = 一周EV × 50% + 一月EV × 30% + 三月EV × 20%
```

### 概率计算

基于以下特征计算上涨/下跌概率：

1. **价格位置**（权重：25%）
   ```python
   price_position = (price - week52_low) / (week52_high - week52_low)
   if price_position < 0.3:
       prob_up += 0.10  # 低位反弹概率高
   elif price_position > 0.8:
       prob_up -= 0.10  # 高位回调概率高
   ```

2. **技术面**（权重：25%）
   - 均线关系
   - 成交量异常
   - 技术指标

3. **基本面**（权重：25%）
   - PE/PEG 估值
   - 增长率
   - 财务健康度

4. **风险评分**（权重：15%）
   ```python
   if risk_score < 3:
       prob_up += 0.05
   elif risk_score > 7:
       prob_up -= 0.10
   ```

5. **市场情绪**（权重：10%）
   - VIX 指数
   - Put/Call 比率

### 涨跌幅度估算

优先使用期权隐含波动率，备用历史波动率：

```python
# 优先使用期权 IV
if implied_vol:
    expected_move = price * implied_vol * sqrt(days_to_expiry / 365)
else:
    # 备用：历史波动率
    historical_vol = calculate_historical_volatility(hist_prices)
    expected_move = price * historical_vol * sqrt(days_to_expiry / 365)
```

### EV 评分与推荐

| EV 范围 | 评分 | 推荐动作 | 置信度 |
|---------|------|---------|--------|
| EV > 8% | 9-10 | 强烈买入 | 高 |
| 3% < EV ≤ 8% | 6-8 | 买入 | 中高 |
| -3% ≤ EV ≤ 3% | 4-6 | 观望 | 中 |
| -8% ≤ EV < -3% | 2-4 | 回避 | 中低 |
| EV < -8% | 0-2 | 强烈回避 | 高 |

## 🛑 止损价格计算

### ATR 止损（动态止损）

```python
# 计算 ATR (Average True Range)
atr = calculate_atr(hist_prices, period=ATR_PERIOD)  # 默认14天

# 基础 ATR 倍数
atr_multiplier = ATR_MULTIPLIER_BASE  # 2.5

# Beta 调整
if beta > BETA_HIGH_THRESHOLD:  # > 1.5
    atr_multiplier *= BETA_HIGH_MULTIPLIER  # × 1.2
elif beta < BETA_LOW_THRESHOLD:  # < 0.8
    atr_multiplier *= BETA_LOW_MULTIPLIER  # × 0.8

# 止损价格
stop_loss = current_price - (atr * atr_multiplier)
```

### 固定止损（备用）

如果无法计算 ATR，使用固定百分比：

```python
stop_loss = current_price * (1 - FIXED_STOP_LOSS_PCT)  # 15%
```

### 止损预警点

```python
warning_price = current_price * (1 - FIXED_STOP_LOSS_PCT * 0.5)  # 7.5%
```

## 📊 市场情绪计算

### 情绪评分范围

市场情绪评分：**0-10 分**，分数越高情绪越乐观。

### 情绪因子

#### 1. VIX 恐慌指数

```python
if vix < 15:
    sentiment += 2.0  # 低波动，情绪乐观
elif vix < 20:
    sentiment += 1.0
elif vix > 30:
    sentiment -= 2.0  # 高波动，情绪恐慌
elif vix > 25:
    sentiment -= 1.0
```

#### 2. Put/Call 比率

```python
if put_call_ratio < 0.8:
    sentiment += 1.5  # 看涨情绪浓厚
elif put_call_ratio > 1.5:
    sentiment -= 1.5  # 看跌情绪浓厚
```

#### 3. 美债收益率

```python
if treasury_yield > TREASURY_YIELD_VERY_HIGH:  # > 5.0%
    sentiment -= 1.0  # 高利率环境
elif treasury_yield < 2.0:
    sentiment += 0.5  # 低利率环境
```

#### 4. PE 分位点

```python
pe_percentile = calculate_pe_percentile(current_pe, hist_data)

if pe_percentile < 20:
    sentiment += 1.0  # 低估值，情绪乐观
elif pe_percentile > 80:
    sentiment -= 1.0  # 高估值，情绪谨慎
```

## ⚙️ 参数配置

所有算法参数定义在 `backend/app/constants.py`：

### 估值参数

```python
GROWTH_DISCOUNT_FACTOR = 0.6      # 增长率折现系数
TECHNICAL_SENTIMENT_BOOST = 0.10  # 技术面情绪加成
PEG_THRESHOLD_BASE = 1.5          # PEG 基础阈值
```

### 止损参数

```python
ATR_PERIOD = 14                   # ATR 计算周期
ATR_MULTIPLIER_BASE = 2.5         # ATR 倍数基础值
ATR_MULTIPLIER_MIN = 1.5          # ATR 倍数最小值
ATR_MULTIPLIER_MAX = 4.0          # ATR 倍数最大值
FIXED_STOP_LOSS_PCT = 0.15        # 固定止损百分比（15%）
```

### 流动性参数

```python
MIN_DAILY_VOLUME_USD = 5_000_000  # 最小日均成交额（500万美元）
VOLUME_ANOMALY_HIGH = 2.0          # 成交量异常高阈值
VOLUME_ANOMALY_LOW = 0.3           # 成交量异常低阈值
```

### 风险评分参数

```python
PE_HIGH_THRESHOLD = 40             # PE 高风险阈值
PE_VERY_HIGH_THRESHOLD = 60        # PE 极高风险阈值
PEG_HIGH_THRESHOLD = 2.0           # PEG 高风险阈值
GROWTH_NEGATIVE_THRESHOLD = -0.10  # 负增长风险阈值
```

### 市场情绪参数

```python
VIX_HIGH = 30.0                    # VIX 高风险阈值
VIX_MEDIUM = 25.0                  # VIX 中等风险阈值
PUT_CALL_HIGH = 1.5                # Put/Call 高风险阈值
TREASURY_YIELD_VERY_HIGH = 5.0    # 美债收益率极高阈值
```

## 🔄 算法流程

### 完整分析流程

```
1. 获取市场数据
   ├── 价格数据（当前价、52周高低点）
   ├── 财务数据（PE、PEG、增长率）
   └── 历史数据（价格历史、成交量）

2. 计算风险评分
   ├── PE/PEG 估值风险
   ├── 增长率风险
   ├── 流动性风险
   └── 市场情绪风险

3. 计算目标价格
   ├── PE/PEG 估值
   ├── 增长率折现
   └── 技术面分析

4. 计算 EV 期望值
   ├── 上涨/下跌概率
   ├── 涨跌幅度估算
   └── 多时间视界加权

5. 计算止损价格
   ├── ATR 动态止损
   └── 固定止损（备用）

6. 生成 AI 分析报告
   └── 整合所有分析结果
```

## 📝 注意事项

1. **数据质量**：确保数据源的准确性和及时性
2. **参数调优**：根据市场情况定期调整参数
3. **异常处理**：对缺失数据提供合理的默认值
4. **性能优化**：缓存计算结果，避免重复计算
5. **可追溯性**：记录所有计算参数和中间结果

---

**最后更新**: 2026-01-16

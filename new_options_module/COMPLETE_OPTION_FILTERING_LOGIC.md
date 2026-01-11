# Alpha GBM 期权筛选、概率、流动性与推荐值完整逻辑文档

## 概述

本文档完整说明 Alpha GBM 期权分析平台的核心逻辑，包括：
1. **期权筛选机制**：如何从期权链中筛选出符合条件的期权
2. **行权概率计算**：基于 Black-Scholes 模型的科学计算方法
3. **流动性判断**：如何评估期权的交易活跃度
4. **推荐值算法**：基于 Alpha GBM 五大支柱的量化评分系统

---

## 第一部分：期权筛选机制

### 1.1 基础筛选（用户输入）

#### 筛选维度

1. **股票代码（Symbol）**
   - 格式：大写字母（如：AAPL, TSLA, NVDA）
   - 验证：必须输入有效的股票代码

2. **到期日期（Expiry Date）**
   - 格式：YYYY-MM-DD（如：2024-02-16）
   - 来源：从 Tiger API 获取该股票的所有可用到期日期
   - 限制：只能选择系统提供的到期日期

3. **交易类型（Trade Type）**
   - 选项：
     - `sell_put`：卖出看跌（现金担保看跌）
     - `sell_call`：卖出看涨（备兑看涨）
     - `buy_call`：买入看涨
     - `buy_put`：买入看跌
     - `all`：全部（默认显示卖出策略）

#### 筛选流程

```
用户输入股票代码
    ↓
系统获取该股票的所有到期日期
    ↓
用户选择到期日期和交易类型
    ↓
用户点击"查询期权"按钮
    ↓
系统获取该股票在该到期日的完整期权链
    ↓
根据交易类型筛选 Call 或 Put 期权
    ↓
应用高级筛选（可选）
    ↓
计算每个期权的评分指标
    ↓
应用一票否决机制
    ↓
计算推荐值
    ↓
按推荐值排序并显示
```

### 1.2 高级筛选（可选）

用户可以通过"高级选项"面板设置额外的筛选条件：

#### 筛选条件

1. **年化收益范围**
   - 最小值：默认 0%
   - 最大值：默认 100%
   - 逻辑：`minAnnualReturn ≤ 年化收益 ≤ maxAnnualReturn`

2. **权利金范围**
   - 最小值：默认 $0
   - 最大值：默认 $10000
   - 逻辑：`minPremium ≤ 权利金 ≤ maxPremium`

3. **买卖价差上限**
   - 最大值：默认 $10
   - 逻辑：`价差 ≤ maxSpread`

#### 代码实现

```javascript
function filterOptions(options, minAnnualReturn, maxAnnualReturn, minPremium, maxPremium, maxSpread) {
    return options.filter(option => {
        const scores = option.scores || {};
        
        // 年化收益率筛选
        const annualReturn = parseFloat(scores.annualized_return) || 0;
        const passAnnualReturn = annualReturn >= minAnnualReturn && annualReturn <= maxAnnualReturn;
        
        // 权利金筛选
        const premium = parseFloat(scores.premium_income) || 0;
        const passPremium = premium >= minPremium && premium <= maxPremium;
        
        // 买卖价差筛选
        const bidPrice = parseFloat(option.bid_price) || 0;
        const askPrice = parseFloat(option.ask_price) || 0;
        const spread = Math.abs(askPrice - bidPrice);
        const passSpread = spread <= maxSpread;
        
        return passAnnualReturn && passPremium && passSpread;
    });
}
```

---

## 第二部分：行权概率计算（Assignment Probability）

### 2.1 理论基础

行权概率是指期权到期时变为实值（ITM）的概率，即期权被行权的概率。

**重要区别**：
- **Delta ($N(d_1)$)**：期权价格对股价变动的敏感度，包含幅度加权
- **行权概率 ($N(d_2)$)**：股价落在行权价之外的可能性，纯粹的概率

对于虚值期权（OTM），$N(d_2)$ 通常略小于 Delta。使用 $N(d_2)$ 更精准。

### 2.2 Black-Scholes N(d2) 公式

#### 核心公式

$$P(\text{Assignment}) = N(d_2) = N\left( \frac{\ln(S/K) + (r - \frac{\sigma^2}{2})T}{\sigma\sqrt{T}} \right)$$

#### 变量说明

| 变量 | 符号 | 说明 | 单位 |
|------|------|------|------|
| 当前股价 | $S$ | Stock Price | 美元 |
| 行权价 | $K$ | Strike Price | 美元 |
| 无风险利率 | $r$ | Risk-free Rate | 年化（默认 5%） |
| 隐含波动率 | $\sigma$ | Implied Volatility | 年化（如 0.25 表示 25%） |
| 到期时间 | $T$ | Time to Expiration | 年（天数/365） |
| 标准正态分布 | $N(\cdot)$ | Cumulative Distribution Function | - |

#### 计算步骤

1. **计算到期时间（T）**
   ```python
   dte_days = (expiry_date - today).days
   T = dte_days / 365.0
   ```

2. **计算 d2 参数**
   ```python
   ln_s_k = math.log(S / K)
   sqrt_t = math.sqrt(T)
   d2 = (ln_s_k + (r - 0.5 * sigma**2) * T) / (sigma * sqrt_t)
   ```

3. **计算概率**
   ```python
   prob_itm = norm.cdf(d2)  # N(d2)
   ```

4. **根据期权类型调整**
   ```python
   if option_type == "PUT":
       # 看跌期权：股价 < 行权价时被行权
       assignment_prob = (1.0 - prob_itm) * 100.0
   else:  # CALL
       # 看涨期权：股价 > 行权价时被行权
       assignment_prob = prob_itm * 100.0
   ```

### 2.3 完整代码实现（Python）

```python
from scipy.stats import norm
import math

def calculate_assignment_probability(option, stock_price, risk_free_rate=0.05):
    """
    计算行权概率（基于 Black-Scholes N(d2)）
    
    Args:
        option: 期权数据对象，包含：
            - implied_vol: 隐含波动率
            - strike: 行权价
            - expiry_date: 到期日期
            - put_call: 期权类型（"PUT" 或 "CALL"）
        stock_price: 当前股价
        risk_free_rate: 无风险利率（默认 5%）
    
    Returns:
        行权概率（0-100%），如果数据不足返回 None
    """
    # 数据验证
    if (not option.implied_vol or not option.strike or
        option.implied_vol <= 0 or option.strike <= 0 or stock_price <= 0):
        return None
    
    # 计算到期时间（年）
    dte_days = calculate_days_to_expiry(option.expiry_date)
    T = dte_days / 365.0
    
    if T <= 0:
        # 已到期期权：如果实值则100%行权，否则0%
        if option.put_call == "PUT":
            return 100.0 if stock_price < option.strike else 0.0
        else:  # CALL
            return 100.0 if stock_price > option.strike else 0.0
    
    # Black-Scholes 参数
    S = stock_price
    K = option.strike
    r = risk_free_rate
    sigma = option.implied_vol
    
    try:
        # 计算 d2
        ln_s_k = math.log(S / K)
        sqrt_t = math.sqrt(T)
        d2 = (ln_s_k + (r - 0.5 * sigma**2) * T) / (sigma * sqrt_t)
        
        # N(d2) = 标准正态分布累积分布函数
        prob_itm = norm.cdf(d2)
        
        # 根据期权类型调整
        if option.put_call == "PUT":
            # 看跌期权：P(S < K) = 1 - N(d2)
            assignment_prob = (1.0 - prob_itm) * 100.0
        else:  # CALL
            # 看涨期权：P(S > K) = N(d2)
            assignment_prob = prob_itm * 100.0
        
        # 确保结果在有效范围内
        return max(0.0, min(100.0, assignment_prob))
    
    except (ValueError, ZeroDivisionError):
        return None  # 计算错误，返回 None
```

### 2.4 特殊情况处理

1. **数据缺失**
   - 如果缺少 IV、行权价或股价，返回 `None`
   - 前端显示为 `-%`

2. **已到期期权**
   - 如果到期时间 ≤ 0：
     - 看跌期权：股价 < 行权价 → 100%，否则 0%
     - 看涨期权：股价 > 行权价 → 100%，否则 0%

3. **计算错误**
   - 如果出现除零或对数错误，返回 `None`
   - 避免显示误导性数据

### 2.5 显示格式

- **正常值**：保留1位小数，如 `15.5%`
- **零值**：显示 `0.0%`
- **缺失值**：显示 `-%`

---

## 第三部分：流动性判断（Liquidity Assessment）

### 3.1 流动性因子计算（v2.0 优化版）

流动性因子是一个 0-1 之间的数值，反映期权的交易活跃度和平仓便利性。

**新逻辑（v2.0）**：复合流动性因子 = 40% 价差得分 + 60% 未平仓量（OI）得分

#### 核心改进

1. **引入未平仓量（Open Interest, OI）**
   - OI 是判断流动性深度的"金标准"
   - 特别是在盘前或交易清淡时，成交量可能为 0，但 OI 能证明盘口有对手方存在
   - OI 反映市场深度和流动性储备

2. **价差率（Spread Ratio）**
   - 旧逻辑：固定金额（如 < $10）
   - 新逻辑：价差率 = (Ask - Bid) / MidPrice
   - 理由：$100 的期权价差 $0.5 和 $1 的期权价差 $0.5 完全不同，比例更能反映交易磨损成本

3. **一票否决机制**
   - 如果 OI < 10 张，直接过滤，无论价差多小
   - 防止做市商钓鱼单（Fishing Orders）

#### 计算公式

```
复合流动性因子 = 40% × 价差得分 + 60% × OI得分

其中：
价差率 = (Ask - Bid) / MidPrice
中间价 = (买价 + 卖价) / 2
```

#### 价差得分计算（40% 权重）

| 价差率范围 | 价差得分 | 说明 |
|-----------|---------|------|
| ≤ 1% | 1.0 | 价差极小，交易成本低 |
| 1% - 3% | 0.8 - 1.0（线性插值） | 价差较小 |
| 3% - 5% | 0.5 - 0.8（线性插值） | 价差适中 |
| 5% - 10% | 0.2 - 0.5（线性插值） | 价差较大 |
| > 10% | 0.0 | 价差过大 |

#### OI 得分计算（60% 权重）

| OI 范围 | OI 得分 | 说明 |
|--------|---------|------|
| ≥ 500 | 1.0 | 流动性极佳 |
| 200 - 500 | 0.8 - 0.95（线性插值） | 流动性良好 |
| 50 - 200 | 0.6 - 0.8（线性插值） | 流动性中等 |
| 10 - 50 | 0.3 - 0.6（线性插值） | 流动性较低 |
| < 10 | 0.0（一票否决） | 流动性不足，过滤 |

#### 判断标准

| 复合流动性因子 | 等级 | 说明 |
|--------------|------|------|
| ≥ 0.8 | **良好** | 流动性优秀 |
| 0.4 - 0.8 | **中等** | 流动性一般 |
| < 0.4 | **较低** | 流动性较差 |

### 3.2 完整代码实现（Python v2.0）

```python
def calculate_liquidity_factor(bid_price, ask_price, open_interest=None, latest_price=None):
    """
    计算复合流动性因子（v2.0）
    
    Args:
        bid_price: 买价
        ask_price: 卖价
        open_interest: 未平仓量（OI）
        latest_price: 最新价格（备用）
    
    Returns:
        流动性因子（0-1之间，标准化评分）
    """
    # ========== 一票否决：OI < 10 ==========
    if open_interest is not None and open_interest < 10:
        return 0.0  # Veto: insufficient OI depth
    
    # ========== Spread Score (40% weight) ==========
    spread_score = 0.5  # Default poor liquidity
    if bid_price and ask_price and bid_price > 0 and ask_price > 0:
        mid_price = (bid_price + ask_price) / 2
        if mid_price > 0:
            # Spread Ratio: (Ask - Bid) / MidPrice
            spread_ratio = (ask_price - bid_price) / mid_price
            
            # Score: <1% = 1.0, 1-3% = 0.8-1.0, 3-5% = 0.5-0.8, 5-10% = 0.2-0.5, >10% = 0.0
            if spread_ratio <= 0.01:  # <1%
                spread_score = 1.0
            elif spread_ratio <= 0.03:  # 1-3%
                spread_score = 0.8 + (0.03 - spread_ratio) / 0.02 * 0.2  # Linear: 0.8-1.0
            elif spread_ratio <= 0.05:  # 3-5%
                spread_score = 0.5 + (0.05 - spread_ratio) / 0.02 * 0.3  # Linear: 0.5-0.8
            elif spread_ratio <= 0.10:  # 5-10%
                spread_score = 0.2 + (0.10 - spread_ratio) / 0.05 * 0.3  # Linear: 0.2-0.5
            else:  # >10%
                spread_score = 0.0
    
    # ========== OI Score (60% weight) ==========
    oi_score = 0.0  # Default no liquidity
    if open_interest is not None and open_interest >= 10:
        # Score: 10-50 = 0.3-0.6, 50-200 = 0.6-0.8, 200-500 = 0.8-0.95, >500 = 1.0
        if open_interest >= 500:
            oi_score = 1.0
        elif open_interest >= 200:
            oi_score = 0.8 + (open_interest - 200) / 300 * 0.15  # Linear: 0.8-0.95
        elif open_interest >= 50:
            oi_score = 0.6 + (open_interest - 50) / 150 * 0.2  # Linear: 0.6-0.8
        elif open_interest >= 10:
            oi_score = 0.3 + (open_interest - 10) / 40 * 0.3  # Linear: 0.3-0.6
    elif open_interest is None:
        # If OI data is missing, use a conservative default (0.3)
        oi_score = 0.3
    
    # ========== Composite Factor = 40% Spread + 60% OI ==========
    composite_factor = 0.4 * spread_score + 0.6 * oi_score
    
    # Ensure result is in valid range [0.0, 1.0]
    return max(0.0, min(1.0, composite_factor))
```

### 3.3 显示格式

流动性以**文字等级**显示，不显示具体数值：

| 流动性因子 | 显示文字 | 说明 |
|-----------|---------|------|
| ≥ 0.8 | **良好** | 流动性优秀 |
| 0.4 - 0.8 | **中等** | 流动性一般 |
| < 0.4 | **较低** | 流动性较差 |

#### 代码实现

```javascript
function formatLiquidity(liquidity) {
    if (!liquidity || liquidity === 0) return '-';
    const value = parseFloat(liquidity);
    
    if (value >= 0.8) {
        return '良好';
    } else if (value >= 0.4) {
        return '中等';
    } else {
        return '较低';
    }
}
```

### 3.4 流动性在推荐值中的作用

- **一票否决**：流动性 < 0.3 的期权直接得 0 分
- **评分权重**：流动性占推荐值总分的 25%（最高 25 分）

---

## 第四部分：推荐值算法（Recommendation Score）

### 4.1 设计理念

推荐值算法基于 **Alpha GBM 五大支柱**：

1. **量化决策**：用数据说话，减少情绪干扰
2. **事前验尸**：假设投资失败，提前识别风险点
3. **严格风控**：硬数据计算，设置仓位上限和止损
4. **怀疑主义**：始终质疑，寻找不买入的理由
5. **风格纪律**：严格遵守投资风格，不偏离策略

### 4.2 一票否决机制（Disqualification Rules）

以下任一条件不满足，期权直接得 **0分**，不予推荐：

| 条件 | 阈值 | 原因 |
|------|------|------|
| **流动性过低** | < 0.3 | 无法平仓，风险不可控 |
| **收益过低** | 年化收益 < 3% | 不值得承担期权风险 |
| **风险过高** | 行权概率 > 80% | 风险太大，不适合卖出策略 |
| **交易成本过高** | 买卖价差 > 期权价格的10% | 交易成本侵蚀利润 |

#### 代码实现

```javascript
// 一票否决检查
if (liquidity < 0.3) {
    return { value: 0, text: '0.00', class: 'score-low', highlight: false, reason: '流动性太低' };
}
if (annualReturnPercent < 3) {
    return { value: 0, text: '0.00', class: 'score-low', highlight: false, reason: '收益太低' };
}
if (assignmentProb > 80) {
    return { value: 0, text: '0.00', class: 'score-low', highlight: false, reason: '风险太高' };
}
if (spreadPercent > 10) {
    return { value: 0, text: '0.00', class: 'score-low', highlight: false, reason: '交易成本太高' };
}
```

### 4.3 评分标准（总分80分）

推荐值算法采用**线性插值**计算，确保分数连续平滑，避免阶梯式评分的不连续性。

#### 1. 量化决策 - 年化收益（权重 25%，最高25分）

**计算公式**：
```
年化收益 = (权利金收入 / 资金占用) × (365 / 到期天数) × 100%

其中：
- **卖出看跌（Sell Put）**：
  - 如果API提供保证金率：资金占用 = 行权价 × 100 × 保证金率
  - 否则使用Reg-T规则：资金占用 = max(20% × 行权价 × 100 - OTM, 10% × 行权价 × 100) + 权利金
    - OTM = max(0, 行权价 - 股价) × 100
- **卖出看涨（Sell Call）**：
  - 如果API提供保证金率：资金占用 = 股价 × 100 × 保证金率
  - 否则假设备兑看涨：资金占用 = 股价 × 100（假设已持有股票）

**保证金计算优化（v2.0）**：
- 系统会尝试从 Tiger API 获取股票的融资融券保证金率
- 如果API提供保证金率，使用该比例计算（更准确）
- 如果API不提供，使用标准 Reg-T 规则（向后兼容）
```

**线性插值规则**：

| 年化收益范围 | 分数范围 | 插值公式 |
|------------|---------|---------|
| ≥ 15% | 25分（满分） | - |
| 12% - 15% | 20-25分 | `20 + (年化收益 - 12) / (15 - 12) × 5` |
| 8% - 12% | 15-20分 | `15 + (年化收益 - 8) / (12 - 8) × 5` |
| 5% - 8% | 10-15分 | `10 + (年化收益 - 5) / (8 - 5) × 5` |
| 3% - 5% | 5-10分 | `5 + (年化收益 - 3) / (5 - 3) × 5` |
| < 3% | 0分（一票否决） | - |

**代码实现**：
```javascript
if (annualReturnPercent >= 15) {
    score += 25;
} else if (annualReturnPercent >= 12) {
    const ratio = (annualReturnPercent - 12) / (15 - 12);
    score += 20 + ratio * 5;
} else if (annualReturnPercent >= 8) {
    const ratio = (annualReturnPercent - 8) / (12 - 8);
    score += 15 + ratio * 5;
} else if (annualReturnPercent >= 5) {
    const ratio = (annualReturnPercent - 5) / (8 - 5);
    score += 10 + ratio * 5;
} else if (annualReturnPercent >= 3) {
    const ratio = (annualReturnPercent - 3) / (5 - 3);
    score += 5 + ratio * 5;
}
```

#### 2. 事前验尸 - 行权概率（权重 25%，最高25分，越低越好）

**线性插值规则**：

| 行权概率范围 | 分数范围 | 插值公式 |
|------------|---------|---------|
| < 15% | 25分（满分） | - |
| 15% - 25% | 20-25分 | `20 + (25 - 行权概率) / (25 - 15) × 5` |
| 25% - 35% | 15-20分 | `15 + (35 - 行权概率) / (35 - 25) × 5` |
| 35% - 50% | 10-15分 | `10 + (50 - 行权概率) / (50 - 35) × 5` |
| 50% - 70% | 5-10分 | `5 + (70 - 行权概率) / (70 - 50) × 5` |
| ≥ 70% | 0分 | - |
| > 75% | 0分（一票否决） | - |

**风险阈值收紧（v2.0）**：
- 旧逻辑：行权概率 > 80% 一票否决
- 新逻辑：行权概率 > 75% 即视为过度风险，触发一票否决
- 理由：实盘中，一旦概率超过 75%，Gamma 风险急剧上升，且此时往往已深度实值，流动性枯竭，难以通过滚单（Roll）自救

**代码实现**：
```javascript
if (assignmentProb < 15) {
    score += 25;
} else if (assignmentProb < 25) {
    const ratio = (25 - assignmentProb) / (25 - 15);
    score += 20 + ratio * 5;
} else if (assignmentProb < 35) {
    const ratio = (35 - assignmentProb) / (35 - 25);
    score += 15 + ratio * 5;
} else if (assignmentProb < 50) {
    const ratio = (50 - assignmentProb) / (50 - 35);
    score += 10 + ratio * 5;
} else if (assignmentProb < 70) {
    const ratio = (70 - assignmentProb) / (70 - 50);
    score += 5 + ratio * 5;
}
```

#### 3. 严格风控 - 流动性（权重 25%，最高25分）

**流动性因子计算（v2.0）**：
- 复合因子 = 40% 价差得分 + 60% OI 得分
- OI 是判断流动性深度的"金标准"，特别是在盘前或交易清淡时
- 如果 OI < 10 张，直接过滤（一票否决）

**线性插值规则**：

| 流动性因子范围 | 分数范围 | 插值公式 |
|--------------|---------|---------|
| ≥ 0.8 | 25分（满分） | - |
| 0.6 - 0.8 | 20-25分 | `20 + (流动性 - 0.6) / (0.8 - 0.6) × 5` |
| 0.4 - 0.6 | 15-20分 | `15 + (流动性 - 0.4) / (0.6 - 0.4) × 5` |
| 0.3 - 0.4 | 10-15分 | `10 + (流动性 - 0.3) / (0.4 - 0.3) × 5` |
| < 0.3 | 0分（一票否决） | - |

**代码实现**：
```javascript
if (liquidity >= 0.8) {
    score += 25;
} else if (liquidity >= 0.6) {
    const ratio = (liquidity - 0.6) / (0.8 - 0.6);
    score += 20 + ratio * 5;
} else if (liquidity >= 0.4) {
    const ratio = (liquidity - 0.4) / (0.6 - 0.4);
    score += 15 + ratio * 5;
} else if (liquidity >= 0.3) {
    const ratio = (liquidity - 0.3) / (0.4 - 0.3);
    score += 10 + ratio * 5;
}
```

#### 4. 怀疑主义 - 买卖价差率（权重 15%，最高15分，越小越好）

**计算公式（v2.0）**：
```
价差率（Spread Ratio）= (Ask - Bid) / MidPrice
中间价（MidPrice）= (买价 + 卖价) / 2
价差百分比 = 价差率 × 100%
```

**改进说明**：
- 旧逻辑：固定金额（如 < $10）
- 新逻辑：价差率（比例）
- 理由：$100 的期权价差 $0.5 和 $1 的期权价差 $0.5 完全不同，比例更能反映交易磨损成本

**线性插值规则**：

| 价差百分比范围 | 分数范围 | 插值公式 |
|--------------|---------|---------|
| < 1% | 15分（满分） | - |
| 1% - 3% | 12-15分 | `12 + (3 - 价差) / (3 - 1) × 3` |
| 3% - 5% | 8-12分 | `8 + (5 - 价差) / (5 - 3) × 4` |
| 5% - 10% | 4-8分 | `4 + (10 - 价差) / (10 - 5) × 4` |
| ≥ 10% | 0分（一票否决） | - |

**代码实现**：
```javascript
if (spreadPercent < 1) {
    score += 15;
} else if (spreadPercent < 3) {
    const ratio = (3 - spreadPercent) / (3 - 1);
    score += 12 + ratio * 3;
} else if (spreadPercent < 5) {
    const ratio = (5 - spreadPercent) / (5 - 3);
    score += 8 + ratio * 4;
} else if (spreadPercent < 10) {
    const ratio = (10 - spreadPercent) / (10 - 5);
    score += 4 + ratio * 4;
}
```

### 4.4 推荐等级划分（基于80分总分）

| 总分 | 等级 | 显示格式 | 高亮 | 说明 |
|------|------|---------|------|------|
| ≥ 60分 | **特别推荐** | `72.50分` | ✅ 是（绿色背景+品牌色分数框） | 75%以上，优质机会 |
| 52-59分 | **推荐** | `55.25分` | ❌ 否（黄色） | 65-74%，可考虑 |
| 40-51分 | **一般** | `45.00分` | ❌ 否（灰色） | 50-64%，需谨慎 |
| < 40分 | **不推荐** | `35.50分` | ❌ 否（红色） | <50%，不推荐 |

**阈值说明**：
- **≥ 60分**（75%）：特别推荐，高亮显示
- **≥ 52分**（65%）：推荐级别
- **≥ 40分**（50%）：一般级别
- **< 40分**（<50%）：不推荐

### 4.5 完整推荐值计算代码

```javascript
function calculateRecommendation(option, scores, stockPrice, optionType = 'call', tradeType = 'sell') {
    if (!scores) return { value: 0, text: '0.00', class: '', highlight: false };
    
    // 提取数据
    const annualReturn = parseFloat(scores.annualized_return) || 0;
    const annualReturnPercent = annualReturn; // 后端返回的已经是百分比格式
    const assignmentProb = parseFloat(scores.assignment_probability) || 0;
    const liquidity = parseFloat(scores.liquidity_factor) || 0;
    const bidPrice = parseFloat(option.bid_price) || 0;
    const askPrice = parseFloat(option.ask_price) || 0;
    // ========== 价差率计算（Spread Ratio） ==========
    // 新逻辑：价差率 = (Ask - Bid) / MidPrice
    // 理由：$100的期权价差$0.5和$1的期权价差$0.5完全不同，比例更能反映交易磨损成本
    const midPrice = (bidPrice + askPrice) / 2 || option.latest_price || 0;
    const spreadRatio = midPrice > 0 ? (askPrice - bidPrice) / midPrice : 0;
    const spreadPercent = spreadRatio * 100; // 转换为百分比用于显示
    
    // ========== 一票否决机制（v2.0 优化） ==========
    if (liquidity < 0.3) {
        return { value: 0, text: '0.00', class: 'score-low', highlight: false, reason: '流动性太低' };
    }
    if (annualReturnPercent < 3) {
        return { value: 0, text: '0.00', class: 'score-low', highlight: false, reason: '收益太低' };
    }
    // 风险阈值收紧：行权概率 > 75% 即视为过度风险（旧逻辑：>80%）
    // 理由：实盘中，一旦概率超过75%，Gamma风险急剧上升，且此时往往已深度实值，流动性枯竭
    if (assignmentProb > 75) {
        return { value: 0, text: '0.00', class: 'score-low', highlight: false, reason: '风险太高' };
    }
    // OI一票否决：如果 OI < 10张，直接过滤，无论价差多小（防止做市商钓鱼单）
    const openInterest = parseInt(option.open_interest) || 0;
    if (openInterest > 0 && openInterest < 10) {
        return { value: 0, text: '0.00', class: 'score-low', highlight: false, reason: '未平仓量不足' };
    }
    // 价差率 > 10% 一票否决
    if (spreadPercent > 10) {
        return { value: 0, text: '0.00', class: 'score-low', highlight: false, reason: '交易成本太高' };
    }
    
    // ========== 评分计算（使用线性插值，更精准） ==========
    let score = 0;
    
    // 1. 年化收益（25分）- 线性插值
    if (annualReturnPercent >= 15) {
        score += 25;
    } else if (annualReturnPercent >= 12) {
        const ratio = (annualReturnPercent - 12) / (15 - 12);
        score += 20 + ratio * 5;
    } else if (annualReturnPercent >= 8) {
        const ratio = (annualReturnPercent - 8) / (12 - 8);
        score += 15 + ratio * 5;
    } else if (annualReturnPercent >= 5) {
        const ratio = (annualReturnPercent - 5) / (8 - 5);
        score += 10 + ratio * 5;
    } else if (annualReturnPercent >= 3) {
        const ratio = (annualReturnPercent - 3) / (5 - 3);
        score += 5 + ratio * 5;
    }
    
    // 2. 行权概率（25分）- 线性插值
    if (assignmentProb < 15) {
        score += 25;
    } else if (assignmentProb < 25) {
        const ratio = (25 - assignmentProb) / (25 - 15);
        score += 20 + ratio * 5;
    } else if (assignmentProb < 35) {
        const ratio = (35 - assignmentProb) / (35 - 25);
        score += 15 + ratio * 5;
    } else if (assignmentProb < 50) {
        const ratio = (50 - assignmentProb) / (50 - 35);
        score += 10 + ratio * 5;
    } else if (assignmentProb < 70) {
        const ratio = (70 - assignmentProb) / (70 - 50);
        score += 5 + ratio * 5;
    }
    
    // 3. 流动性（25分）- 线性插值
    if (liquidity >= 0.8) {
        score += 25;
    } else if (liquidity >= 0.6) {
        const ratio = (liquidity - 0.6) / (0.8 - 0.6);
        score += 20 + ratio * 5;
    } else if (liquidity >= 0.4) {
        const ratio = (liquidity - 0.4) / (0.6 - 0.4);
        score += 15 + ratio * 5;
    } else if (liquidity >= 0.3) {
        const ratio = (liquidity - 0.3) / (0.4 - 0.3);
        score += 10 + ratio * 5;
    }
    
    // 4. 买卖价差（15分）- 线性插值
    if (spreadPercent < 1) {
        score += 15;
    } else if (spreadPercent < 3) {
        const ratio = (3 - spreadPercent) / (3 - 1);
        score += 12 + ratio * 3;
    } else if (spreadPercent < 5) {
        const ratio = (5 - spreadPercent) / (5 - 3);
        score += 8 + ratio * 4;
    } else if (spreadPercent < 10) {
        const ratio = (10 - spreadPercent) / (10 - 5);
        score += 4 + ratio * 4;
    }
    
    // ========== 确定推荐等级和显示 ==========
    // 总分现在是80分（年化收益25分 + 行权概率25分 + 流动性25分 + 买卖价差15分）
    let scoreClass, highlight;
    
    if (score >= 60) {  // 60/80 = 75%
        scoreClass = 'score-high';
        highlight = true;  // 特别推荐，高亮显示
    } else if (score >= 52) {  // 52/80 = 65%
        scoreClass = 'score-medium';
        highlight = false;
    } else if (score >= 40) {  // 40/80 = 50%
        scoreClass = 'score-medium';
        highlight = false;
    } else {
        scoreClass = 'score-low';
        highlight = false;
    }
    
    // 显示分数（保留2位小数）
    return { 
        value: score, 
        text: score.toFixed(2), 
        class: scoreClass, 
        highlight: highlight 
    };
}
```

---

## 第五部分：完整筛选流程

### 5.1 端到端流程

```
┌─────────────────────────────────────────────────────────────┐
│ 第一步：用户输入                                              │
│ - 股票代码（Symbol）                                          │
│ - 到期日期（Expiry Date）                                    │
│ - 交易类型（Trade Type）                                     │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 第二步：获取期权链                                            │
│ - 调用 Tiger API 获取完整期权链                              │
│ - 包含所有 Call 和 Put 期权                                   │
│ - 获取 Greeks、Bid/Ask、Volume、OI 等数据                     │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 第三步：基础筛选                                              │
│ - 根据交易类型筛选 Call 或 Put                                │
│ - 过滤无效数据（价格为0、缺失关键字段等）                      │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 第四步：计算核心指标（后端）                                   │
│ 对每个期权计算：                                              │
│ 1. 行权概率（Black-Scholes N(d2)）                           │
│ 2. 流动性因子（基于买卖价差）                                 │
│ 3. 年化收益（权利金/资金占用 × 365/DTE）                      │
│ 4. 权利金收入（期权价格 × 100）                               │
│ 5. 保证金要求（使用API保证金率或Reg-T规则）                   │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 第五步：高级筛选（可选，前端）                                 │
│ - 年化收益范围筛选                                            │
│ - 权利金范围筛选                                              │
│ - 买卖价差上限筛选                                            │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 第六步：一票否决（前端）                                       │
│ 不符合以下任一条件，直接排除：                                 │
│ - 流动性 < 0.3                                               │
│ - 年化收益 < 3%                                               │
│ - 行权概率 > 80%                                              │
│ - 买卖价差 > 10%                                              │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 第七步：计算推荐值（前端）                                     │
│ 对通过筛选的期权：                                            │
│ 1. 年化收益评分（25分，线性插值）                             │
│ 2. 行权概率评分（25分，线性插值）                             │
│ 3. 流动性评分（25分，线性插值）                               │
│ 4. 买卖价差评分（15分，线性插值）                             │
│ 总分 = 各项分数之和（最高80分）                               │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 第八步：排序和显示                                            │
│ - 按推荐值从高到低排序                                        │
│ - ≥60分的期权高亮显示（绿色背景）                              │
│ - 显示所有关键指标                                            │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 数据流向

```
Tiger API
    ↓
option_service.py (后端)
    ↓
计算行权概率、流动性、年化收益等
    ↓
返回 OptionChainResponse (JSON)
    ↓
frontend.html (前端)
    ↓
应用高级筛选
    ↓
应用一票否决
    ↓
计算推荐值
    ↓
排序并显示
```

---

## 第六部分：关键计算公式汇总

### 6.1 行权概率

$$P(\text{Assignment}) = \begin{cases}
1 - N(d_2) & \text{看跌期权 (PUT)} \\
N(d_2) & \text{看涨期权 (CALL)}
\end{cases}$$

$$d_2 = \frac{\ln(S/K) + (r - \frac{\sigma^2}{2})T}{\sigma\sqrt{T}}$$

### 6.2 流动性因子

$$L_{liq} = \begin{cases}
1.0 & \text{如果 } \frac{Ask - Bid}{Mid} \leq 5\% \\
0.5 + 0.5 \times \frac{10\% - Spread}{10\% - 5\%} & \text{如果 } 5\% < Spread < 10\% \\
0.5 & \text{如果 } Spread \geq 10\%
\end{cases}$$

其中：$Mid = \frac{Bid + Ask}{2}$

### 6.3 年化收益

$$Annualized\ Return = \frac{Premium}{Capital} \times \frac{365}{DTE} \times 100\%$$

其中：
- **卖出看跌（Sell Put）**：
  - 如果API提供保证金率：$Capital = Strike \times 100 \times MarginRate$
  - 否则使用Reg-T：$Capital = \max(0.20 \times Strike \times 100 - OTM, 0.10 \times Strike \times 100) + Premium$
    - 其中 $OTM = \max(0, Strike - StockPrice) \times 100$
- **卖出看涨（Sell Call）**：
  - 如果API提供保证金率：$Capital = StockPrice \times 100 \times MarginRate$
  - 否则假设备兑：$Capital = StockPrice \times 100$
- $Premium = Option\ Price \times 100$

### 6.4 推荐值总分

$$Score_{total} = Score_{return} + Score_{prob} + Score_{liquidity} + Score_{spread}$$

其中：
- $Score_{return} \in [0, 25]$（年化收益）
- $Score_{prob} \in [0, 25]$（行权概率）
- $Score_{liquidity} \in [0, 25]$（流动性）
- $Score_{spread} \in [0, 15]$（买卖价差）

总分范围：$[0, 80]$

---

## 第七部分：算法特点

### 7.1 严格性
- **一票否决机制**：确保只有基本合格的期权才能参与评分
- **高门槛**：≥60分才能获得特别推荐，避免推荐过多
- **精选原则**：只有真正优质的期权才会被高亮

### 7.2 精准性
- **线性插值**：使用线性插值计算，确保分数连续平滑
- **2位小数**：推荐值显示为2位小数，更专业
- **科学计算**：行权概率基于 Black-Scholes 模型，而非简单估算

### 7.3 全面性
- **四维评分**：综合考虑收益、风险、流动性、成本
- **五大支柱**：基于 Alpha GBM 投资理念
- **完整流程**：从筛选到评分，全流程覆盖

### 7.4 实用性
- **直观显示**：分数而非文字，更直观
- **高亮标记**：特别推荐的期权一目了然
- **清晰标准**：每个指标都有明确的判断标准

---

## 第八部分：使用建议

### 8.1 对于普通用户

1. **优先关注高亮推荐**
   - 优先查看 ≥60分的高亮推荐期权
   - 这些期权已经通过了严格筛选

2. **查看关键指标**
   - **流动性**：确保可以平仓（至少"中等"）
   - **年化收益**：了解预期回报
   - **行权概率**：了解风险水平（越低越好）
   - **买卖价差**：了解交易成本

3. **理解推荐值**
   - 推荐值越高，综合质量越好
   - 但也要结合自己的风险承受能力

### 8.2 对于专业用户

1. **深入分析**
   - 可以查看所有分数的期权，自行判断
   - 结合年化收益和行权概率进行风险评估

2. **理解算法**
   - 理解线性插值的计算方式
   - 了解一票否决的严格标准

3. **综合判断**
   - 推荐值仅供参考
   - 建议结合市场趋势、个股基本面等综合判断

---

## 第九部分：注意事项

1. **数据准确性**
   - 所有计算基于实时市场数据
   - 数据准确性依赖于 Tiger API

2. **风险提示**
   - 所有数据分析由AI生成，不构成投资建议
   - 期权交易有风险，入市需谨慎

3. **动态调整**
   - 市场情况变化时，推荐值会相应调整
   - 建议定期查看最新数据

4. **综合判断**
   - 推荐值只是参考工具
   - 建议结合其他因素（如市场趋势、个股基本面等）综合判断

---

## 附录：变量说明

| 变量名 | 类型 | 说明 | 单位/格式 |
|--------|------|------|----------|
| `stockPrice` | Number | 股票当前价格 | 美元 |
| `strike` | Number | 期权行权价 | 美元 |
| `premium` | Number | 权利金（单份合约） | 美元 |
| `premium_income` | Number | 权利金收入（100股） | 美元 |
| `assignmentProb` | Number | 行权概率 | 0-100% |
| `liquidity` | Number | 流动性因子 | 0-1 |
| `annualReturn` | Number | 年化收益 | 百分比（如12.5表示12.5%） |
| `bidPrice` | Number | 买价 | 美元 |
| `askPrice` | Number | 卖价 | 美元 |
| `spread` | Number | 买卖价差（绝对值） | 美元 |
| `spreadPercent` | Number | 买卖价差百分比 | 百分比 |
| `implied_vol` | Number | 隐含波动率 | 年化（如0.25表示25%） |
| `dte` | Number | 到期天数 | 天 |
| `optionType` | String | 期权类型 | 'call' 或 'put' |
| `tradeType` | String | 交易类型 | 'buy' 或 'sell' |
| `score` | Number | 推荐值分数 | 0-80 |

---

## 附录：代码文件位置

### 后端代码
- **行权概率计算**：`scoring/option_scorer.py` → `calculate_assignment_probability()`
- **流动性计算**：`scoring/option_scorer.py` → `calculate_liquidity_factor()`
- **年化收益计算**：`scoring/option_scorer.py` → `calculate_premium_and_margin()`
- **期权评分**：`scoring/option_scorer.py` → `score_option()`

### 前端代码
- **推荐值计算**：`frontend.html` → `calculateRecommendation()`
- **高级筛选**：`frontend.html` → `filterOptions()`
- **流动性显示**：`frontend.html` → `formatLiquidity()`
- **行权概率显示**：`frontend.html` → `formatAssignmentPercent()`

---

**文档版本**：v1.0  
**最后更新**：2025年1月  
**维护者**：Alpha GBM 团队

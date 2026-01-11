# Alpha GBM 期权选择逻辑文档

## 概述

本文档详细说明了 Alpha GBM 期权分析工具的完整选择逻辑，包括价差计算、胜率计算、流动性判断、推荐值算法等核心功能。

---

## 一、价差计算（Price Difference）

### 定义
价差是指**股票当前价格**与**期权行权价**之间的差值，用于判断期权的实值/虚值状态。

### 计算公式

#### 看涨期权（Call）
```
价差 = 股票当前价格 - 行权价
```
- **正数**：实值期权（In-the-Money）
- **负数**：虚值期权（Out-of-the-Money）
- **零**：平值期权（At-the-Money）

#### 看跌期权（Put）
```
价差 = 行权价 - 股票当前价格
```
- **正数**：实值期权（In-the-Money）
- **负数**：虚值期权（Out-of-the-Money）
- **零**：平值期权（At-the-Money）

### 代码实现
```javascript
function calculatePriceDiff(stockPrice, strike, optionType = 'call') {
    if (!stockPrice || !strike) return '-';
    const diff = parseFloat(stockPrice) - parseFloat(strike);
    if (optionType === 'put') {
        return formatNumber(parseFloat(strike) - parseFloat(stockPrice));
    }
    return formatNumber(diff);
}
```

---

## 二、胜率计算（Win Rate / Probability of Profit）

### 定义
胜率是指期权交易盈利的概率，根据交易类型（买入/卖出）和期权类型（看涨/看跌）采用不同的计算方法。

### 计算方法

#### 卖出期权（Sell Options）
对于卖出期权策略，胜率计算相对简单：
```
胜率 = (1 - 行权概率) × 100%
```
- **逻辑**：如果股价不触及行权价，期权不会被行权，卖方获得权利金，交易盈利
- **适用场景**：卖出看涨（Sell Call）、卖出看跌（Sell Put）

#### 买入期权（Buy Options）
对于买入期权策略，需要计算股价达到盈亏平衡点的概率：

**买入看涨（Buy Call）**
```
盈亏平衡点 = 行权价 + 权利金
胜率计算：
- 如果当前价格 ≥ 盈亏平衡点：胜率 = 60% + (当前价格 - 盈亏平衡点) / 行权价 × 20%
- 如果当前价格 < 盈亏平衡点：胜率 = 60% - (盈亏平衡点 - 当前价格) / 当前价格 × 100%
```

**买入看跌（Buy Put）**
```
盈亏平衡点 = 行权价 - 权利金
胜率计算：
- 如果当前价格 ≤ 盈亏平衡点：胜率 = 60% + (盈亏平衡点 - 当前价格) / 行权价 × 20%
- 如果当前价格 > 盈亏平衡点：胜率 = 60% - (当前价格 - 盈亏平衡点) / 当前价格 × 100%
```

### 代码实现
```javascript
function calculateWinRate(option, scores, stockPrice, optionType = 'call', tradeType = 'sell') {
    const strike = parseFloat(option.strike) || 0;
    const premium = parseFloat(scores.premium_income) || 0;
    const assignmentProb = parseFloat(scores.assignment_probability) || 0;
    const currentPrice = parseFloat(stockPrice) || 0;
    
    if (tradeType === 'sell') {
        // 卖出期权：胜率 = 1 - 行权概率
        return Math.max(0, Math.min(100, (1 - assignmentProb / 100) * 100));
    } else {
        // 买入期权：基于盈亏平衡点计算
        if (optionType === 'call') {
            const breakEven = strike + premium;
            if (currentPrice >= breakEven) {
                return Math.max(60, Math.min(100, 60 + (currentPrice - breakEven) / strike * 20));
            } else {
                const distance = (breakEven - currentPrice) / currentPrice;
                return Math.max(0, Math.min(60, 60 - distance * 100));
            }
        } else {
            const breakEven = strike - premium;
            if (currentPrice <= breakEven) {
                return Math.max(60, Math.min(100, 60 + (breakEven - currentPrice) / strike * 20));
            } else {
                const distance = (currentPrice - breakEven) / currentPrice;
                return Math.max(0, Math.min(60, 60 - distance * 100));
            }
        }
    }
}
```

---

## 三、流动性判断标准（Liquidity Assessment）

### 定义
流动性因子（Liquidity Factor）是一个0-1之间的数值，反映期权的交易活跃度和平仓便利性。

### 判断标准

| 流动性值 | 等级 | 描述 | 特征 |
|---------|------|------|------|
| ≥ 0.8 | 高 | 成交量充足，买卖价差小 | 容易平仓，交易成本低 |
| 0.6 - 0.8 | 中 | 成交量一般，价差适中 | 可以平仓，交易成本适中 |
| 0.4 - 0.6 | 低 | 成交量较少，价差较大 | 平仓困难，交易成本较高 |
| < 0.4 | 很低 | 成交量稀少，价差很大 | 很难平仓，交易成本很高 |

### 显示格式
流动性以百分比形式显示，并标注等级：
- `100% (高)` - 流动性值 ≥ 0.8
- `70% (中)` - 流动性值 0.6-0.8
- `50% (低)` - 流动性值 0.4-0.6
- `30% (很低)` - 流动性值 < 0.4

### 代码实现
```javascript
function formatLiquidity(liquidity) {
    if (!liquidity || liquidity === 0) return '-';
    const value = parseFloat(liquidity);
    const percent = (value * 100).toFixed(0);
    
    let level = '';
    if (value >= 0.8) level = '高';
    else if (value >= 0.6) level = '中';
    else if (value >= 0.4) level = '低';
    else level = '很低';
    
    return `${percent}% (${level})`;
}
```

---

## 四、推荐值算法（Recommendation Score）

### 设计理念
推荐值算法基于 **Alpha GBM 五大支柱**：
1. **量化决策**：用数据说话，减少情绪干扰
2. **事前验尸**：假设投资失败，提前识别风险点
3. **严格风控**：硬数据计算，设置仓位上限和止损
4. **怀疑主义**：始终质疑，寻找不买入的理由
5. **风格纪律**：严格遵守投资风格，不偏离策略

### 一票否决机制（Disqualification Rules）

以下任一条件不满足，期权直接得 **0分**，不予推荐：

1. **流动性过低**
   - 条件：流动性 < 0.3
   - 原因：流动性太低，无法平仓，风险不可控

2. **收益过低**
   - 条件：年化收益 < 3%
   - 原因：收益太低，不值得承担期权风险

3. **风险过高**
   - 条件：行权概率 > 80%
   - 原因：行权概率过高，风险太大

4. **交易成本过高**
   - 条件：买卖价差 > 期权价格的10%
   - 原因：交易成本太高，侵蚀利润

### 评分标准（总分100分）

#### 1. 量化决策 - 年化收益（权重 25%，最高25分）

| 年化收益 | 得分 |
|---------|------|
| ≥ 15% | 25分 |
| ≥ 12% | 20分 |
| ≥ 8% | 15分 |
| ≥ 5% | 10分 |
| ≥ 3% | 5分 |
| < 3% | 0分（一票否决） |

**逻辑**：年化收益越高，期权价值越大。但必须 ≥ 3% 才能通过一票否决。

#### 2. 事前验尸 - 行权概率（权重 25%，最高25分）

| 行权概率 | 得分 | 说明 |
|---------|------|------|
| < 15% | 25分 | 风险极低 |
| < 25% | 20分 | 风险低 |
| < 35% | 15分 | 风险中等 |
| < 50% | 10分 | 风险偏高 |
| < 70% | 5分 | 风险高 |
| ≥ 70% | 0分 | 风险极高 |
| > 80% | 0分（一票否决） | 风险不可接受 |

**逻辑**：行权概率越低，风险越小。对于卖出期权策略，行权概率越低越好。

#### 3. 严格风控 - 流动性（权重 20%，最高20分）

| 流动性值 | 得分 |
|---------|------|
| ≥ 0.8 | 20分 |
| ≥ 0.6 | 15分 |
| ≥ 0.4 | 10分 |
| ≥ 0.3 | 5分 |
| < 0.3 | 0分（一票否决） |

**逻辑**：流动性越高，越容易平仓，风险控制能力越强。

#### 4. 胜率（权重 20%，最高20分）

| 胜率 | 得分 |
|------|------|
| ≥ 75% | 20分 |
| ≥ 65% | 15分 |
| ≥ 55% | 10分 |
| ≥ 45% | 5分 |
| < 45% | 0分 |

**逻辑**：胜率越高，盈利概率越大。这是量化决策的重要指标。

#### 5. 怀疑主义 - 买卖价差（权重 10%，最高10分）

买卖价差以**期权价格的百分比**计算：
```
价差百分比 = (卖价 - 买价) / 期权价格 × 100%
```

| 价差百分比 | 得分 |
|----------|------|
| < 1% | 10分 |
| < 3% | 7分 |
| < 5% | 4分 |
| < 10% | 2分 |
| ≥ 10% | 0分（一票否决） |

**逻辑**：价差越小，交易成本越低，这是怀疑主义（寻找不买入理由）的体现。

### 推荐等级划分

| 总分 | 等级 | 显示 | 高亮 |
|------|------|------|------|
| ≥ 75分 | 特别推荐 | 显示分数（如：75分） | ✅ 是（绿色背景+品牌色分数框） |
| 65-74分 | 推荐 | 显示分数（如：68分） | ❌ 否（黄色） |
| 50-64分 | 一般 | 显示分数（如：55分） | ❌ 否（灰色） |
| < 50分 | 不推荐 | 显示分数（如：35分） | ❌ 否（红色） |

### 代码实现
```javascript
function calculateRecommendation(option, scores, stockPrice, optionType = 'call', tradeType = 'sell') {
    // 一票否决检查
    if (liquidity < 0.3) return { value: 0, text: '0', class: 'score-low', highlight: false };
    if (annualReturnPercent < 3) return { value: 0, text: '0', class: 'score-low', highlight: false };
    if (assignmentProb > 80) return { value: 0, text: '0', class: 'score-low', highlight: false };
    if (spreadPercent > 10) return { value: 0, text: '0', class: 'score-low', highlight: false };
    
    // 评分计算
    let score = 0;
    
    // 1. 年化收益（25分）
    if (annualReturnPercent >= 15) score += 25;
    else if (annualReturnPercent >= 12) score += 20;
    else if (annualReturnPercent >= 8) score += 15;
    else if (annualReturnPercent >= 5) score += 10;
    else if (annualReturnPercent >= 3) score += 5;
    
    // 2. 行权概率（25分）
    if (assignmentProb < 15) score += 25;
    else if (assignmentProb < 25) score += 20;
    else if (assignmentProb < 35) score += 15;
    else if (assignmentProb < 50) score += 10;
    else if (assignmentProb < 70) score += 5;
    
    // 3. 流动性（20分）
    if (liquidity >= 0.8) score += 20;
    else if (liquidity >= 0.6) score += 15;
    else if (liquidity >= 0.4) score += 10;
    else if (liquidity >= 0.3) score += 5;
    
    // 4. 胜率（20分）
    const winRate = calculateWinRate(option, scores, stockPrice, optionType, tradeType);
    if (winRate >= 75) score += 20;
    else if (winRate >= 65) score += 15;
    else if (winRate >= 55) score += 10;
    else if (winRate >= 45) score += 5;
    
    // 5. 买卖价差（10分）
    if (spreadPercent < 1) score += 10;
    else if (spreadPercent < 3) score += 7;
    else if (spreadPercent < 5) score += 4;
    else if (spreadPercent < 10) score += 2;
    
    // 确定推荐等级
    let scoreClass, highlight;
    if (score >= 75) {
        scoreClass = 'score-high';
        highlight = true; // 特别推荐，高亮显示
    } else if (score >= 65) {
        scoreClass = 'score-medium';
        highlight = false;
    } else if (score >= 50) {
        scoreClass = 'score-medium';
        highlight = false;
    } else {
        scoreClass = 'score-low';
        highlight = false;
    }
    
    return { 
        value: score, 
        text: score.toString(), 
        class: scoreClass, 
        highlight: highlight 
    };
}
```

---

## 五、交易类型判断

### 交易类型映射

根据用户选择的交易类型，系统会自动判断是买入还是卖出策略：

| 用户选择 | 交易类型 | 说明 |
|---------|---------|------|
| 卖出看跌 (Sell Put) | `sell` | Value风格：现金担保看跌 |
| 卖出看涨 (Sell Call) | `sell` | Quality风格：备兑看涨 |
| 买入看涨 (Buy Call) | `buy` | Growth/Momentum风格：看涨价差 |
| 买入看跌 (Buy Put) | `buy` | 看跌策略 |
| 全部 | `sell` | 默认推荐卖出策略（更安全） |

### 代码实现
```javascript
// 对于看涨期权
let callTradeType = 'sell'; // 默认卖出（更安全）
if (tradeType === 'buy_call') {
    callTradeType = 'buy';
} else if (tradeType === 'sell_call' || tradeType === 'all') {
    callTradeType = 'sell';
}

// 对于看跌期权
let putTradeType = 'sell'; // 默认卖出（更安全）
if (tradeType === 'buy_put') {
    putTradeType = 'buy';
} else if (tradeType === 'sell_put' || tradeType === 'all') {
    putTradeType = 'sell';
}
```

---

## 六、显示规则

### 推荐值显示

1. **显示格式**：显示分数 + "分"字（如：`75分`）
2. **颜色编码**：
   - **特别推荐（≥75分）**：绿色背景 + 品牌色分数框高亮
   - **推荐（65-74分）**：黄色背景
   - **一般（50-64分）**：灰色背景
   - **不推荐（<50分）**：红色背景

3. **高亮规则**：
   - 只有 **≥75分** 的期权才会高亮显示
   - 高亮效果：整行绿色背景 + 分数框品牌色高亮 + 阴影效果

### 其他指标显示

- **价差**：显示为美元金额（如：`$5.50`）
- **行权概率**：显示为百分比（如：`15.5%`）
- **年化收益**：显示为百分比（如：`12.3%`）
- **流动性**：显示为百分比 + 等级（如：`80% (高)`）
- **胜率**：显示为百分比（如：`75%`）

---

## 七、筛选流程

### 完整筛选流程

1. **基础筛选**：根据交易类型筛选期权（Call/Put）
2. **高级筛选**（可选）：
   - 年化收益范围
   - 权利金范围
   - 买卖价差上限
3. **一票否决**：不符合基本条件的期权直接排除
4. **评分计算**：对通过筛选的期权进行评分
5. **排序显示**：按推荐值从高到低排序
6. **高亮标记**：≥75分的期权高亮显示

---

## 八、算法特点

### 1. 严格性
- 一票否决机制确保只有基本合格的期权才能参与评分
- 高门槛（≥75分）才能获得特别推荐，避免推荐过多

### 2. 全面性
- 综合考虑收益、风险、流动性、胜率、成本五个维度
- 基于 Alpha GBM 五大支柱，体现完整的投资理念

### 3. 实用性
- 显示分数而非文字，更直观
- 高亮显示特别推荐的期权，便于快速识别
- 流动性判断标准清晰，帮助用户理解风险

### 4. 精选性
- 只有真正优质的期权才会被高亮推荐
- 避免推荐过多，保持精选原则

---

## 九、使用建议

### 对于普通用户
1. 优先关注 **≥75分** 的高亮推荐期权
2. 查看 **流动性** 等级，确保可以平仓
3. 关注 **胜率**，了解盈利概率
4. 查看 **价差**，了解交易成本

### 对于专业用户
1. 可以查看所有分数的期权，自行判断
2. 结合 **年化收益** 和 **行权概率** 进行风险评估
3. 根据 **流动性** 判断平仓便利性
4. 参考 **买卖价差** 评估交易成本

---

## 十、注意事项

1. **推荐值仅供参考**：所有数据分析由AI生成，不构成投资建议
2. **风险提示**：期权交易有风险，入市需谨慎
3. **动态调整**：市场情况变化时，推荐值会相应调整
4. **综合判断**：建议结合其他因素（如市场趋势、个股基本面等）综合判断

---

## 附录：变量说明

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `stockPrice` | Number | 股票当前价格 |
| `strike` | Number | 期权行权价 |
| `premium` | Number | 权利金 |
| `assignmentProb` | Number | 行权概率（0-100） |
| `liquidity` | Number | 流动性因子（0-1） |
| `annualReturn` | Number | 年化收益（小数形式，如0.12表示12%） |
| `bidPrice` | Number | 买价 |
| `askPrice` | Number | 卖价 |
| `spread` | Number | 买卖价差（绝对值） |
| `spreadPercent` | Number | 买卖价差百分比 |
| `winRate` | Number | 胜率（0-100） |
| `optionType` | String | 期权类型：'call' 或 'put' |
| `tradeType` | String | 交易类型：'buy' 或 'sell' |

---

**文档版本**：v1.0  
**最后更新**：2025年1月  
**维护者**：Alpha GBM 团队

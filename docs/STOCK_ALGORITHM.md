# 股票分析算法详解

本文档详细说明 AlphaGBM 股票分析系统的核心算法。

> **2026年1月更新**：新增PE历史分位点计算、动态ATR止损（VIX调整）、DCF估值法、EV信心度评分、市场相关性风险检测等重要优化。

---

## 目录

1. [系统架构概览](#一系统架构概览)
2. [核心模型：G = B + M](#二核心模型g--b--m)
3. [分析流程（7步）](#三分析流程7步)
4. [市场数据获取](#四市场数据获取)
5. [风险分析模块](#五风险分析模块)
6. [市场情绪计算](#六市场情绪计算)
7. [目标价格计算](#七目标价格计算)
8. [ATR动态止损](#八atr动态止损)
9. [EV期望值模型](#九ev期望值模型)
10. [AI分析报告](#十ai分析报告)
11. [市场差异化处理](#十一市场差异化处理)

---

## 一、系统架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                     股票分析系统架构                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│   │ 市场数据获取  │ -> │ 风险分析     │ -> │ 市场情绪计算  │     │
│   │ (yfinance)   │    │ (五大支柱)   │    │ (G=B+M)      │     │
│   └──────────────┘    └──────────────┘    └──────────────┘     │
│         │                   │                    │              │
│         v                   v                    v              │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│   │ 目标价计算    │    │ ATR动态止损  │    │ EV期望值模型 │     │
│   │ (5种方法)    │    │ (VIX调整)    │    │ (多时间视界) │     │
│   └──────────────┘    └──────────────┘    └──────────────┘     │
│         │                   │                    │              │
│         └───────────────────┼────────────────────┘              │
│                             v                                    │
│                    ┌──────────────┐                             │
│                    │ AI分析报告   │                             │
│                    │ (Gemini)     │                             │
│                    └──────────────┘                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**核心文件**：
- `backend/app/services/analysis_engine.py` - 核心分析引擎
- `backend/app/services/ev_model.py` - EV期望值模型
- `backend/app/services/ai_service.py` - AI分析服务
- `backend/app/constants.py` - 配置参数
- `backend/app/api/stock.py` - API接口

---

## 二、核心模型：G = B + M

### 2.1 模型理念

**AlphaGBM 核心公式**：`收益 = 基本面 + 情绪`

```
G = B + M

G (Gain)     = 预期收益
B (Basics)   = 基本面价值（财务数据、行业趋势）
M (Momentum) = 市场情绪（技术趋势、资金流向、估值情绪）
```

### 2.2 权重配置

| 维度 | 正常权重 | 财报滞后期权重 | 说明 |
|------|----------|----------------|------|
| 基本面 (B) | 40% | 20% | 财报刚发布时数据可能滞后 |
| 技术面 | 30% | 45% | 财报期技术面更可靠 |
| 情绪面 (M) | 30% | 35% | 市场情绪反应更快 |

---

## 三、分析流程（7步）

```python
def get_stock_analysis_data(ticker, style):
    """完整的股票分析流程"""

    # 1. 获取市场数据
    market_data = get_market_data(ticker)

    # 2. 风险分析（五大支柱）
    risk_result = analyze_risk_and_position(style, market_data)

    # 3. 市场情绪计算
    market_sentiment = calculate_market_sentiment(market_data)

    # 4. 目标价格计算（5种方法加权）
    target_price = calculate_target_price(market_data, risk_result, style)

    # 5. ATR动态止损（VIX调整）
    stop_loss = calculate_atr_stop_loss(price, hist, beta, vix)

    # 6. EV期望值模型（多时间视界）
    ev_result = calculate_ev_model(market_data, risk_result, style)

    # 7. AI分析报告（Gemini）
    ai_report = get_gemini_analysis(ticker, style, market_data, risk_result)

    return combined_result
```

---

## 四、市场数据获取

### 4.1 数据来源

| 数据类型 | 来源 | 备用 |
|----------|------|------|
| 股票行情 | Yahoo Finance | Alpha Vantage |
| 期权数据 | Yahoo Finance | - |
| VIX指数 | Yahoo Finance (^VIX) | - |
| 宏观数据 | Yahoo Finance (^TNX, DX-Y.NYB) | - |

### 4.2 获取的关键数据

```python
market_data = {
    # 价格数据
    'price': float,           # 当前价格
    'week52_high': float,     # 52周最高
    'week52_low': float,      # 52周最低
    'ma50': float,            # 50日均线
    'ma200': float,           # 200日均线

    # 基本面数据
    'pe': float,              # 市盈率
    'peg': float,             # PEG比率
    'growth': float,          # 营收增长率
    'margin': float,          # 利润率
    'beta': float,            # Beta值
    'free_cash_flow': float,  # 自由现金流（新增）
    'shares_outstanding': int, # 流通股数（新增）

    # 期权市场数据
    'options_data': {
        'vix': float,         # VIX恐慌指数
        'vix_change': float,  # VIX变化率
        'put_call_ratio': float  # Put/Call比率
    },

    # 宏观经济数据
    'macro_data': {
        'treasury_10y': float,  # 10年美债收益率
        'dxy': float,           # 美元指数
        'gold': float,          # 黄金价格
        'oil': float            # 原油价格
    },

    # 相关性数据（新增）
    'market_correlation': {
        'current_correlation': float,  # 与SPY的当前相关性
        'beta_estimate': float,        # 估算Beta
        'high_correlation_warning': bool
    }
}
```

---

## 五、风险分析模块

### 5.1 五大支柱框架

| 支柱 | 检测内容 | 风险权重 |
|------|----------|----------|
| **估值风险** | PE分位点、PEG合理性 | 30% |
| **技术风险** | 均线位置、价格位置 | 20% |
| **流动性风险** | 日均成交额 | 15% |
| **事件风险** | 财报日期、解禁期 | 20% |
| **市场风险** | VIX、宏观环境 | 15% |

### 5.2 流动性检查（市场差异化）

```python
# constants.py 中的市场配置
MARKET_CONFIG = {
    'US': {
        'min_daily_volume_usd': 5_000_000,    # 美股 $500万
        'liquidity_coefficient': 1.0,
    },
    'HK': {
        'min_daily_volume_usd': 2_000_000,    # 港股 $200万
        'liquidity_coefficient': 0.6,
    },
    'CN': {
        'min_daily_volume_usd': 1_000_000,    # A股（换算后）
        'liquidity_coefficient': 0.5,
    }
}

def check_liquidity(data, ticker):
    """市场差异化流动性检查"""
    market = detect_market_from_ticker(ticker)
    config = get_market_config(market)
    threshold = config['min_daily_volume_usd'] * config['liquidity_coefficient']

    # 检查日均成交额是否达标
    is_liquid = estimated_daily_volume >= threshold
    return is_liquid, liquidity_info
```

### 5.3 PE历史分位点计算（新增）

```python
def calculate_pe_percentile(current_pe, ticker):
    """
    计算当前PE在5年历史中的分位点

    数据来源：yfinance季度盈利数据
    计算方法：
    1. 获取5年历史价格
    2. 获取季度EPS数据
    3. 计算每季度的历史PE
    4. 用scipy.stats.percentileofscore计算分位点
    """
    # 获取历史盈利数据
    earnings = stock.quarterly_earnings

    # 计算历史PE序列
    for date, row in earnings.iterrows():
        eps = row['Earnings']
        price_at_date = get_price_at(date)
        pe = price_at_date / (eps * 4)  # 年化
        historical_pe_list.append(pe)

    # 计算分位点
    percentile = stats.percentileofscore(historical_pe_list, current_pe)

    return percentile, z_score, historical_pe_list
```

**PE分位点情绪评分映射**：

| 分位点 | 情绪评分 | 含义 |
|--------|----------|------|
| 0-20% | 3.0 | 历史低估，极度悲观 |
| 20-40% | 4.5 | 偏低估 |
| 40-60% | 5.5 | 中性 |
| 60-80% | 6.5 | 偏高估 |
| 80-90% | 8.0 | 历史高位 |
| 90-100% | 9.0 | 极度高估 |

### 5.4 风险等级与建议仓位

| 风险评分 | 等级 | 建议最大仓位 |
|----------|------|--------------|
| 0-2 | 极低 | 25% |
| 2-4 | 低 | 20% |
| 4-6 | 中等 | 15% |
| 6-8 | 高 | 5% |
| 8-10 | 极高 | 0% (不建议) |

---

## 六、市场情绪计算

### 6.1 情绪评分组成（0-10分）

| 指标 | 权重 | 说明 |
|------|------|------|
| 技术面情绪 | 10% | 均线位置、价格趋势 |
| VIX恐慌指数 | 12% | 市场波动率 |
| Put/Call比率 | 8% | 期权市场情绪 |
| 宏观经济 | 10% | 利率、美元、商品 |
| PE分位点 | 15% | 估值历史位置 |
| 成交量异常 | 5% | 资金流入流出 |
| 中国市场情绪 | 40%* | *仅A股/港股 |

### 6.2 VIX情绪评分

```python
def calculate_vix_sentiment(vix, vix_change):
    """VIX恐慌指数对情绪的影响"""

    if vix < 15:
        vix_sentiment = 8.0   # 低波动，市场平静
    elif vix < 20:
        vix_sentiment = 6.5   # 正常波动
    elif vix < 25:
        vix_sentiment = 5.0   # 中等偏高
    elif vix < 30:
        vix_sentiment = 3.5   # 高波动，情绪偏悲观
    elif vix < 40:
        vix_sentiment = 2.0   # 很高波动，恐慌
    else:
        vix_sentiment = 1.0   # 极高波动，极度恐慌

    # VIX快速上升进一步降低情绪
    if vix_change > 10:
        vix_sentiment -= 1.5
    elif vix_change > 5:
        vix_sentiment -= 0.8

    return vix_sentiment
```

### 6.3 相关性风险检测（新增）

```python
def calculate_market_correlation(ticker, benchmark='SPY'):
    """
    计算个股与大盘的相关性
    用于检测风险聚集
    """
    # 计算60日滚动相关性
    rolling_corr = stock_returns.rolling(60).corr(benchmark_returns)

    # 高相关性警告
    if current_corr > 0.85:
        high_correlation_warning = True
        # 高相关+高Beta = 市场下跌时损失更大
        if beta > 1.2:
            sentiment_adjustment = -0.3

    return {
        'current_correlation': current_corr,
        'avg_correlation': avg_corr,
        'beta_estimate': beta,
        'high_correlation_warning': warning
    }
```

---

## 七、目标价格计算

### 7.1 五种估值方法

| 方法 | 适用场景 | 权重范围 |
|------|----------|----------|
| **PE估值** | 有盈利的公司 | 20-45% |
| **PEG估值** | 成长股 | 10-25% |
| **增长率折现** | 高增长公司 | 15-25% |
| **DCF估值** | 稳定现金流公司 | 10-30% |
| **技术面分析** | 所有公司 | 10-15% |

### 7.2 行业权重配置

```python
# 根据行业类别分配不同权重
industry_weights = {
    'technology': {
        'PE估值': 0.20, 'PEG估值': 0.25,
        '增长率折现': 0.25, 'DCF估值': 0.20, '技术面分析': 0.10
    },
    'financial': {
        'PE估值': 0.45, 'PEG估值': 0.15,
        '增长率折现': 0.15, 'DCF估值': 0.10, '技术面分析': 0.15
    },
    'energy': {
        'PE估值': 0.30, 'PEG估值': 0.10,
        '增长率折现': 0.15, 'DCF估值': 0.30, '技术面分析': 0.15
    },
    'consumer': {
        'PE估值': 0.25, 'PEG估值': 0.20,
        '增长率折现': 0.20, 'DCF估值': 0.25, '技术面分析': 0.10
    }
}
```

### 7.3 DCF估值法（新增）

```python
def calculate_dcf_target(data, risk_result):
    """
    简化DCF模型

    公式：企业价值 = Σ(FCF_t / (1+r)^t) + 终值
    """
    fcf = data['free_cash_flow']
    shares = data['shares_outstanding']
    growth = data['growth']

    # 折现率 = 无风险利率 + 风险溢价
    risk_free_rate = 0.04  # 美债收益率
    risk_premium = 0.03 + (risk_score / 100)
    discount_rate = risk_free_rate + risk_premium

    # 5年预测（增长率逐年递减）
    fcf_projections = []
    for year in range(1, 6):
        year_growth = growth * (0.9 ** (year - 1))
        projected_fcf = current_fcf * (1 + year_growth)
        discounted = projected_fcf / ((1 + discount_rate) ** year)
        fcf_projections.append(discounted)

    # 永续价值（Gordon Growth Model）
    terminal_growth = min(growth * 0.3, 0.025)  # 不超过2.5%
    terminal_value = fcf_projections[-1] * (1 + terminal_growth) / (discount_rate - terminal_growth)

    # 股权价值
    enterprise_value = sum(fcf_projections) + terminal_value
    target_price = enterprise_value / shares

    return target_price
```

### 7.4 风险调整

```python
# 根据风险评分调整目标价
if risk_score >= 6:
    risk_adjustment = 0.85  # 高风险下调15%
elif risk_score >= 4:
    risk_adjustment = 0.95  # 中等风险下调5%
else:
    risk_adjustment = 1.0   # 低风险不调整

# 根据投资风格调整
style_adjustments = {
    'value': 0.95,     # 价值风格更保守
    'growth': 1.05,    # 成长风格稍乐观
    'momentum': 1.08,  # 趋势风格更乐观
    'quality': 1.0     # 质量风格中性
}

target_price = avg_price * risk_adjustment * style_adjustments[style]
```

---

## 八、ATR动态止损

### 8.1 基本公式

```python
# True Range
TR = max(High - Low, |High - PrevClose|, |Low - PrevClose|)

# ATR(14) = 14日TR简单移动平均
ATR = SMA(TR, 14)

# 止损价格
stop_loss = buy_price - (ATR × multiplier)
```

### 8.2 VIX动态调整（新增）

```python
def calculate_atr_stop_loss(buy_price, hist_data, beta, vix):
    """
    基于ATR计算止损，并根据VIX动态调整
    """
    base_multiplier = 2.5  # 基础ATR倍数

    # VIX调整（VIX > 20时扩大止损空间）
    if vix > 20:
        vix_adjustment = min(1.0, ((vix - 20) / 10) * 0.3)
        # VIX每上升10点，ATR倍数+0.3
    elif vix < 15:
        vix_adjustment = -0.2  # 低VIX时收紧止损
    else:
        vix_adjustment = 0

    # Beta调整
    if beta > 1.5:
        beta_multiplier = 1.2  # 高Beta扩大止损
    elif beta < 0.8:
        beta_multiplier = 0.8  # 低Beta收紧止损
    else:
        beta_multiplier = 1.0

    # 最终倍数（限制在1.5-4.0）
    final_multiplier = (base_multiplier + vix_adjustment) * beta_multiplier
    final_multiplier = max(1.5, min(4.0, final_multiplier))

    stop_loss_price = buy_price - (ATR * final_multiplier)

    return {
        'stop_loss_price': stop_loss_price,
        'atr_multiplier': final_multiplier,
        'adjustments': [...],
        'vix': vix,
        'beta': beta
    }
```

### 8.3 调整示例

| 场景 | VIX | Beta | 基础倍数 | 最终倍数 |
|------|-----|------|----------|----------|
| 平静市场 | 15 | 1.0 | 2.5 | 2.3 |
| 正常市场 | 20 | 1.0 | 2.5 | 2.5 |
| 高波动 | 30 | 1.0 | 2.5 | 2.8 |
| 高波动+高Beta | 30 | 1.8 | 2.5 | 3.4 |
| 恐慌市场 | 40 | 1.5 | 2.5 | 3.8 |

---

## 九、EV期望值模型

### 9.1 核心公式

```
EV = (上涨概率 × 上涨幅度) + (下跌概率 × 下跌幅度)
```

### 9.2 多时间视界

| 时间视界 | 权重 | 说明 |
|----------|------|------|
| 1周 | 50% | 短期预测准确性最高 |
| 1月 | 30% | 中期趋势 |
| 3月 | 20% | 长期方向 |

```python
ev_weighted = (
    ev_1week * 0.50 +
    ev_1month * 0.30 +
    ev_3months * 0.20
)
```

### 9.3 EV信心度评分（新增）

```python
def calculate_ev_confidence(ev_1week, ev_1month, ev_3months, data):
    """
    评估EV预测的可信度

    因素：
    1. 时间一致性（40%）：三个时间维度方向是否一致
    2. 信号强度（30%）：EV绝对值是否足够大
    3. 数据质量（20%）：历史数据是否充足
    4. 波动率稳定性（10%）：近期波动率是否稳定
    """
    score = 50  # 基础分

    # 1. 时间一致性
    directions = [get_direction(ev_1week), get_direction(ev_1month), get_direction(ev_3months)]
    if all_same_direction(directions):
        score += 40  # 方向完全一致
    elif partial_consistent(directions):
        score += 25  # 部分一致
    else:
        score -= 15  # 方向分歧

    # 2. 信号强度
    avg_abs_ev = average([abs(ev_1week), abs(ev_1month), abs(ev_3months)])
    if avg_abs_ev > 0.10:
        score += 30  # 强信号
    elif avg_abs_ev > 0.05:
        score += 20  # 中等信号
    elif avg_abs_ev < 0.02:
        score -= 10  # 弱信号

    # 确定等级
    if score >= 70:
        level = 'HIGH'
    elif score >= 40:
        level = 'MEDIUM'
    else:
        level = 'LOW'

    return {
        'level': level,
        'score': score,
        'factors': [...],
        'description': '...'
    }
```

### 9.4 EV推荐映射

| EV值 | 推荐 | 信心度 |
|------|------|--------|
| > 8% | STRONG_BUY | high |
| 3%-8% | BUY | medium |
| -3%-3% | HOLD | medium |
| -8%--3% | AVOID | medium |
| < -8% | STRONG_AVOID | high |

---

## 十、AI分析报告

### 10.1 Gemini分析流程

```
1. 构建Prompt（包含所有数据）
   ↓
2. 调用Gemini API
   ↓
3. 解析返回的分析报告
   ↓
4. 如果失败，使用备用分析（Fallback）
```

### 10.2 报告结构

```markdown
## 第一部分：公司概况
- 公司名称、行业、市值

## 第二部分：基本面分析 (B)
- 营收增长、利润率、PE/PEG分析

## 第三部分：情绪/趋势分析 (M)
- 技术面、市场情绪、VIX影响

## 第四部分：风险评估
- 主要风险点、风险等级

## 第五部分：估值分析
- 目标价格、估值方法说明

## 第六部分：交易策略
- 操作建议、建议仓位、止损价格
```

### 10.3 投资风格约束

| 风格 | 核心原则 | 最大仓位 |
|------|----------|----------|
| 质量 (Quality) | 财务稳健、护城河深 | 20% |
| 价值 (Value) | 低估值、安全边际 | 10% |
| 成长 (Growth) | 高增长、容忍高估值 | 15% |
| 趋势 (Momentum) | 跟随趋势、快进快出 | 5% |

---

## 十一、市场差异化处理

### 11.1 市场识别规则

```python
def detect_market_from_ticker(ticker):
    """根据股票代码识别市场"""

    suffix_map = {
        '.SS': 'CN',  # 上海
        '.SZ': 'CN',  # 深圳
        '.HK': 'HK',  # 香港
    }

    # 检查后缀
    for suffix, market in suffix_map.items():
        if ticker.endswith(suffix):
            return market

    # 检查纯数字（A股）
    if ticker[:2] in ['60', '68', '00', '30']:
        return 'CN'

    return 'US'  # 默认美股
```

### 11.2 市场特定参数

| 参数 | 美股 | 港股 | A股 |
|------|------|------|------|
| 流动性门槛 | $500万 | $200万 | ¥2000万 |
| 流动性系数 | 1.0 | 0.6 | 0.5 |
| 风险溢价 | 1.0 | 1.15 | 1.3 |
| PE高风险阈值 | 40 | 35 | 50 |
| 波动率调整 | 1.0 | 1.1 | 1.2 |

### 11.3 中国市场情绪因子

| 因子 | 权重 | 说明 |
|------|------|------|
| 政策面 | 40% | 政策是A股最大驱动因素 |
| 北向资金 | 20% | 外资流入流出 |
| 融资融券 | 15% | 杠杆资金情绪 |
| 大宗商品 | 10% | 周期股影响 |
| 技术面 | 15% | 均线、趋势 |

---

## 十二、关键算法总结

| 算法 | 输入 | 输出 | 核心逻辑 |
|------|------|------|----------|
| PE分位点 | 当前PE, 历史数据 | 0-100% | scipy.percentileofscore |
| 动态ATR止损 | 价格, ATR, VIX, Beta | 止损价格 | ATR × 动态倍数 |
| DCF估值 | FCF, 增长率, 风险 | 目标价格 | 5年预测 + 终值 |
| EV模型 | 概率, 幅度 | -20% ~ +20% | 多时间加权 |
| EV信心度 | 三维EV, 数据质量 | HIGH/MEDIUM/LOW | 多因子评分 |
| 相关性检测 | 股票收益, 基准收益 | 相关系数, Beta | 60日滚动相关 |

---

## 十三、设计亮点

1. **G=B+M模型**：简洁直观的投资框架，基本面+情绪双维度
2. **五种估值方法加权**：根据行业特点自动分配权重，避免单一方法偏差
3. **VIX动态止损**：高波动环境自动扩大止损空间，避免被震出
4. **PE历史分位点**：相对估值比绝对PE更有参考意义
5. **EV信心度**：减少弱信号误导，提高决策质量
6. **市场差异化**：美股、港股、A股使用不同参数，适应各市场特点
7. **相关性风险检测**：识别与大盘高度相关的股票，提示分散化不足

---

## 十四、配置参数速查

```python
# constants.py 关键配置

# ATR止损
ATR_PERIOD = 14
ATR_MULTIPLIER_BASE = 2.5
ATR_MULTIPLIER_MIN = 1.5
ATR_MULTIPLIER_MAX = 4.0

# Beta调整
BETA_HIGH_THRESHOLD = 1.5
BETA_LOW_THRESHOLD = 0.8

# VIX阈值
VIX_HIGH = 30.0
VIX_MEDIUM = 25.0

# PE分位点
PE_HISTORY_WINDOW_YEARS = 5
PE_MIN_DATA_POINTS = 20

# 流动性
MIN_DAILY_VOLUME_USD = 5_000_000
```

---

*文档版本: 2026.01 | 最后更新: 2026-01-22*

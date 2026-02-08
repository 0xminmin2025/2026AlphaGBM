# 期权分析模块 (Options Analysis Module)

## 1. 模块概述

期权分析模块是系统的核心交易分析引擎，为用户提供基于量化模型的期权交易建议。

**支持 4 种策略:**

| 策略 | 方向 | 评分指标 | 适用场景 |
|------|------|----------|----------|
| Sell Put | 卖出看跌 | SPRV (0-100) | 看涨/中性，收取权利金 |
| Sell Call | 卖出看涨 | SCRV (0-100) | 看跌/中性，收取权利金 |
| Buy Call | 买入看涨 | BCRV (0-100) | 看涨，方向性杠杆 |
| Buy Put | 买入看跌 | BPRV (0-100) | 看跌，对冲/投机 |

**评分系统:** 所有策略统一 0-100 分制，按分数降序排列推荐期权合约。


## 2. OptionsAnalysisEngine -- 分析引擎主类

**文件:** `app/analysis/options_analysis/core/engine.py` (341 行)

引擎负责编排整个分析流程，组合以下子模块:

```
OptionsAnalysisEngine
  |-- OptionsDataFetcher          # 数据获取
  |-- SellPutScorer               # Sell Put 计分
  |-- SellCallScorer              # Sell Call 计分
  |-- BuyPutScorer                # Buy Put 计分
  |-- BuyCallScorer               # Buy Call 计分
  |-- VRPCalculator               # 波动率风险溢价
  |-- RiskAdjuster                # 风险调整
```

### 2.1 核心方法

**`analyze_options_chain(symbol, strategy='all') -> Dict`**

主入口方法，执行完整的期权链分析。流程:
1. `OptionsDataFetcher.get_options_chain(symbol)` 获取期权数据
2. `get_underlying_stock_data(symbol)` 获取股票基础数据
3. `VRPCalculator.calculate()` 计算波动率风险溢价
4. 循环 `_analyze_strategy()` 对各策略评分 + 附加风险收益标签
5. `RiskAdjuster.analyze_portfolio_risk()` 计算风险指标
6. 生成分析摘要 (`summary`) 和总体建议

返回: `{success, symbol, options_data, stock_data, strategy_analysis, vrp_analysis, risk_analysis, summary, trend_info}`

**`get_options_quotes(symbols: List[str]) -> Dict`** -- 获取多个期权合约的实时报价。

**`calculate_position_sizing(strategy_analysis, portfolio_value, risk_tolerance) -> Dict`** -- 基于风险容忍度 (`conservative`/`moderate`/`aggressive`) 计算建议仓位，委托 `RiskAdjuster`。

### 2.2 风格分组

**`_group_by_style(strategy_analysis) -> Dict`** 将推荐结果按风格分为 4 组:

| 风格 Key | 中文名 | 说明 |
|----------|--------|------|
| `steady_income` | 稳健收益 | 高胜率，有限但稳定的收益 |
| `high_risk_high_reward` | 高风险高收益 | 低胜率，潜在收益巨大 |
| `balanced` | 稳中求进 | 风险收益均衡 |
| `hedge` | 保护对冲 | 保险性质，下跌保护 |

每组按分数排序，取前 3 个推荐。

### 2.3 Overall Recommendation 逻辑

```
score > 85 且 risk_level in [low, medium]  --> Strong Buy  (confidence: high)
score > 70 且 vrp_level in [low, normal]   --> Buy         (confidence: medium)
其他情况                                     --> Cautious    (confidence: low)
无推荐                                       --> Wait        (confidence: low)
```


## 3. OptionsDataFetcher -- 数据获取器

**文件:** `app/analysis/options_analysis/core/data_fetcher.py` (819 行)

### 3.1 缓存机制

- 缓存有效期: **5 分钟** (`cache_duration = 300`)
- 缓存粒度: 按 `{type}_{symbol}_{params}` 作为 cache key
- 内存缓存，进程重启后失效

### 3.2 核心方法

**`get_options_chain(symbol, expiry_days=45) -> Dict`**

获取期权链数据，取前 3 个到期日的 calls 和 puts。通过 yfinance (DataProvider) 获取，包含 strike, expiry, bid/ask, lastPrice, volume, openInterest, impliedVolatility, Greeks。数据获取后自动丰富: Put/Call Ratio, Max Pain, 流动性分析。

**`get_underlying_stock_data(symbol) -> Dict`**

获取标的股票 3 个月历史数据，计算: 当前价格/涨跌幅、ATR(14)、MA20/MA50、30 日年化波动率、多方法支撑阻力位 (Pivot Points + MA + Swing Highs/Lows + Fibonacci)。

### 3.3 波动率计算

```
volatility = std(daily_returns) * sqrt(252)
```

实际代码使用 `pct_change()` 计算日收益率，年化因子 252 为美股年交易日数。


## 4. OptionScorer -- 量化评分核心

**文件:** `app/services/option_scorer.py` (818 行)

### 4.1 SPRV -- Sell Put Recommendation Value

| 因子 | 满分 | 计算逻辑 |
|------|------|----------|
| 收益率 | 30 | `annual_return / 0.50 * 30`，年化 50% 得满分 |
| 胜率 | 25 | `(1 - abs(delta)) * 25` |
| IV 溢价 | 15 | IV Rank 30-100 映射到 0-15 |
| 流动性 | 15 | `liquidity_factor * 15` |
| Theta | +10 | `abs(theta) / 0.10 * 10` |
| Gamma 惩罚 | -5 | `(gamma - 0.02) / 0.08 * 5` |

额外规则: 实值 (strike > stock*1.02) 返回 0; 深度价外 (moneyness<0.7) 线性降分; 日权上限 30 分。

### 4.2 SCRV -- Sell Call Recommendation Value

| 因子 | 满分 | 计算逻辑 |
|------|------|----------|
| 收益率 | 30 | `annual_return / 0.50 * 30` |
| 胜率 | 25 | `(1 - delta) * 25` |
| IV 百分位 | 15 | IV Percentile 30-100 映射到 0-15 |
| 流动性 | 15 | `liquidity_factor * 15` |
| Theta | +10 | `abs(theta) / 0.10 * 10` |
| 上涨空间奖励 | +5 | `upside_space / 0.15 * 5` |
| Gamma 惩罚 | -5 | `(gamma - 0.02) / 0.08 * 5` |

额外规则: 实值 (strike < stock*0.98) 返回 0; 深度价外 (moneyness>1.3) 线性降分; 日权上限 30 分。

### 4.3 BCRV -- Buy Call Recommendation Value

| 因子 | 满分 | 计算逻辑 |
|------|------|----------|
| Delta 方向性 | 30 | `delta * 30` |
| Gamma/Theta 效率 | 25 | `(gamma/abs(theta)) / 2.0 * 25` |
| 低 IV 加分 | 15 | `(60 - iv_rank) / 60 * 15` |
| 流动性 | 15 | `liquidity_factor * 15` |
| Gamma 杠杆 | +5 | `gamma / 0.10 * 5` |
| Theta 惩罚 | -10 | `abs(theta) / 0.15 * 10` |

额外规则: 深度实值 (strike < stock*0.8) 返回 0。

### 4.4 BPRV -- Buy Put Recommendation Value

| 因子 | 满分 | 计算逻辑 |
|------|------|----------|
| Delta 对冲杠杆 | 30 | `abs(delta) * 30` |
| 性价比 | 25 | `(delta_abs/premium) / 1.0 * 25` |
| 低 IV 加分 | 15 | `(60 - iv_rank) / 60 * 15` |
| 流动性 | 15 | `liquidity_factor * 15` |
| Gamma 杠杆 | +5 | `gamma / 0.10 * 5` |
| Theta 惩罚 | -10 | `abs(theta) / 0.15 * 10` |
| 距离 ATM 惩罚 | -5 | `distance_from_atm / 0.20 * 5` |

额外规则: 深度实值 (strike > stock*1.2) 返回 0。


## 5. 流动性因子 (Liquidity Factor)

**计算位置:** `OptionScorer.calculate_liquidity_factor()`

### 一票否决

`open_interest < 10` --> 直接返回 0.0，否决该期权。

### Spread Score (权重 40%)

| Spread Ratio | Score |
|-------------|-------|
| <= 1% | 1.0 |
| 1-3% | 0.8-1.0 |
| 3-5% | 0.5-0.8 |
| 5-10% | 0.2-0.5 |
| > 10% | 0.0 |

### OI Score (权重 60%)

| Open Interest | Score |
|--------------|-------|
| >= 500 | 1.0 |
| 200-500 | 0.80-0.95 |
| 50-200 | 0.60-0.80 |
| 10-50 | 0.30-0.60 |
| < 10 | 0.0 (否决) |

**最终:** `composite = 0.4 * spread_score + 0.6 * oi_score`


## 6. IV Rank 估算

**方法:** `OptionScorer.calculate_iv_rank(implied_vol)`

由于缺少长期 IV 历史数据，采用简化估算:

| Implied Volatility | IV Rank |
|-------------------|---------|
| < 15% | 20 |
| 15-25% | 40 |
| 25-35% | 60 |
| 35-50% | 80 |
| > 50% | 95 |

IV Percentile = IV Rank + 5 (上限 99)。


## 7. 行权概率计算 (Black-Scholes N(d2))

**方法:** `OptionScorer.calculate_assignment_probability()`

```
d2 = [ln(S/K) + (r - 0.5 * sigma^2) * T] / (sigma * sqrt(T))

S = 标的价格, K = 执行价, r = 0.05, sigma = IV, T = DTE/365
```

- **PUT:** `assignment_prob = N(-d2) * 100%`
- **CALL:** `assignment_prob = N(d2) * 100%`

胜率估算同样基于 N(d2): Sell Put = N(d2), Sell Call = N(-d2), Buy 策略以 breakeven 价格代替 K。


## 8. 到期风险惩罚 (Expiry Risk Penalty)

**方法:** `OptionScorer.calculate_expiry_risk_penalty(dte, moneyness_ratio)`

基于用户实战经验: 临期接近行权价需提前平仓，避免夜盘震荡导致意外接股。

| DTE | 距 ATM 距离 | Penalty Factor |
|-----|-------------|---------------|
| 0 DTE | < 3% | 0.30 |
| 0 DTE | 3-5% | 0.50 |
| 0 DTE | > 5% | 0.70 |
| 1-3 DTE | < 3% | 0.60 |
| 1-3 DTE | 3-5% | 0.80 |
| 1-3 DTE | > 5% | 0.95 |
| 4-7 DTE | < 2% | 0.90 |
| 7+ DTE | 任意 | 1.00 (无惩罚) |

**日权评分上限:** DTE <= 1 判定为日权，所有策略评分 **封顶 30 分**。


## 9. 风险收益标签 (Risk-Return Profile)

**文件:** `app/analysis/options_analysis/scoring/risk_return_profile.py` (788 行)

### 9.1 风格定义

| 风格 | 标签 | 典型胜率 | 典型收益 |
|------|------|---------|---------|
| `steady_income` | 稳健收益 / STEADY INCOME | 65-80% | 月 1-5% |
| `balanced` | 稳中求进 / BALANCED | 40-55% | 50-200% |
| `high_risk_high_reward` | 高风险高收益 / HIGH RISK HIGH REWARD | 20-40% | 2-10x |
| `hedge` | 保护对冲 / HEDGE | 30-50% | 对冲收益 |

### 9.2 风格判定规则

**Sell Put** -- 基于安全边际 `(current_price - strike) / current_price * 100`:
- Steady Income: >= 8%
- Balanced: 3-8%
- High Risk: < 3%

**Sell Call** -- 基于虚值程度 `(strike - current_price) / current_price * 100`:
- Steady Income: >= 10%
- Balanced: 3-10%
- High Risk: < 3%

**Buy Call** -- 基于虚值距离: >20% high_risk/very_high, 10-20% high_risk/high, 3-10% balanced/high, <3% balanced/moderate。

**Buy Put** -- 虚值 <=5% 且成本 <=5% 为 `hedge`; >15% 为 high_risk; 8-15% 为 high_risk/high。

### 9.3 VRP 调整

- 卖方策略: 高 VRP 时胜率 +3% ~ +5%
- 买方策略: 低 VRP 时胜率 +3% ~ +5%


## 10. VRP 计算 (Volatility Risk Premium)

**文件:** `app/analysis/options_analysis/advanced/vrp_calculator.py` (594 行)

### 10.1 核心公式

```
VRP = IV - RV
VRP_relative = (IV - RV) / RV
```

VRP > 0 期权偏贵 (卖方有利); VRP < 0 期权偏便宜 (买方有利)。

### 10.2 VRP 等级与策略建议

| VRP Relative | 等级 | 建议 |
|-------------|------|------|
| >= 15% | `very_high` | 强烈卖方 (Iron Condor) |
| 5-15% | `high` | 偏向卖方 |
| -5% ~ 5% | `normal` | 中性，关注方向 |
| -15% ~ -5% | `low` | 偏向买方 |
| <= -15% | `very_low` | 强烈买方 (Long Straddle) |

### 10.3 市场状态识别

同时识别: 波动率状态 (high/elevated/normal/below_average/low)、期权定价状态 (overpriced/fairly_priced/underpriced)、市场压力水平 (high/moderate/normal/low stress)。


## 11. 风险调整 (Risk Adjuster)

**文件:** `app/analysis/options_analysis/advanced/risk_adjuster.py` (722 行)

### 11.1 风险容忍度配置

| 参数 | Conservative | Moderate | Aggressive |
|------|-------------|----------|------------|
| 组合最大风险 | 2% | 5% | 10% |
| 单笔最大风险 | 1% | 2.5% | 5% |
| 最大相关性 | 0.6 | 0.8 | 1.0 |
| 波动率乘数 | 0.8 | 1.0 | 1.3 |

### 11.2 风险评估

`analyze_portfolio_risk()` 流程:
1. 各策略风险 = 基础风险(40%) + 市场风险(40%) + 期权特定风险(20%)
2. 组合风险 = `avg_risk - diversification_benefit + concentration_risk + correlation_risk`
3. 等级: low(<=30) / moderate(30-50) / high(50-70) / very_high(>70)

### 11.3 仓位计算

- 买方: `portfolio_value * max_single_position / (mid_price * 100)`
- 卖方: 额外考虑保证金 (strike * 100 * 20% - 权利金)
- 波动率乘数调整 + 组合级别缩放

### 11.4 策略基础风险

| 策略 | 基础分 | 最大亏损 | Time Decay | Vol Impact |
|------|--------|---------|------------|------------|
| Sell Put | 60 | high | positive | negative |
| Sell Call | 70 | unlimited | positive | negative |
| Buy Put | 50 | limited | negative | positive |
| Buy Call | 55 | limited | negative | positive |


## 12. 趋势分析 (Trend Analyzer)

**文件:** `app/analysis/options_analysis/scoring/trend_analyzer.py` (497 行)

### 12.1 TrendAnalyzer

基于真实交易者决策逻辑:
- **Sell Call 只在上涨时做** (满分 100，下跌降至 30)
- **Sell Put 只在下跌时做** (满分 100，上涨降至 30)
- 不匹配趋势时 **显示但降分**，不完全过滤

`determine_intraday_trend()` 用 3 个信号综合判断:
1. 当日涨跌幅 (> 0.5% bullish / < -0.5% bearish)
2. 相对 MA5 位置 (> 1% bullish / < -1% bearish)
3. 近 5 日动量 (> 2% bullish / < -2% bearish)

2/3 以上信号一致 --> uptrend/downtrend，否则 sideways。

### 12.2 ATRCalculator

基于 ATR 的动态安全边际:

```
safety_ratio = actual_buffer / (ATR * atr_ratio)
```

`safety_ratio >= 1.0` 视为安全。评分: 2.0+ 得 100 分，<0.5 按比例降分。

`SellPutScorer` 和 `SellCallScorer` 均集成趋势分析和 ATR 安全边际。


## 13. 文件路径清单

```
backend/
  app/
    analysis/
      options_analysis/
        __init__.py
        core/
          __init__.py
          engine.py              # 341行  分析引擎主类
          data_fetcher.py        # 819行  期权数据获取
        scoring/
          __init__.py
          sell_put.py            # 744行  Sell Put 策略计分
          sell_call.py           # 843行  Sell Call 策略计分
          buy_call.py            # 679行  Buy Call 策略计分
          buy_put.py             # 637行  Buy Put 策略计分
          risk_return_profile.py # 788行  风险收益标签
          trend_analyzer.py      # 497行  趋势分析 + ATR
        advanced/
          vrp_calculator.py      # 594行  VRP 波动率溢价
          risk_adjuster.py       # 722行  风险调整器
    services/
      option_scorer.py           # 818行  量化评分核心算法
```

**模块总计:** 约 7,482 行 Python 代码。

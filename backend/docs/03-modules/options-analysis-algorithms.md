# 期权分析算法 (Options Analysis Algorithms)

AlphaGBM 期权推荐系统核心算法。迁移自 `docs/OPTIONS_ALGORITHM.md`。

---

## 1. 四种策略概览

| 策略 | 中文 | 最大收益 | 最大亏损 | 理想趋势 |
|------|------|----------|----------|----------|
| **Sell Put** | 卖出看跌 | 权利金 | 行权价-权利金 | 下跌 |
| **Sell Call** | 卖出看涨 | 权利金 | 理论无限 | 上涨 |
| **Buy Call** | 买入看涨 | 理论无限 | 权利金 | 上涨 |
| **Buy Put** | 买入看跌 | 行权价-权利金 | 权利金 | 下跌 |

交易者经验：Sell Put 只在下跌时做（接货更划算）；Sell Call 只在上涨时做（锁定收益）。

---

## 2. 趋势分析系统（3-Signal）

**文件**: `scoring/trend_analyzer.py`

三信号综合判断，2/3 同向即确认趋势：

| 信号 | Bullish | Bearish |
|------|---------|---------|
| 当日涨跌幅 | > +0.5% | < -0.5% |
| 相对 MA5 位置 | > +1.0% | < -1.0% |
| 5 日动量 | > +2.0% | < -2.0% |

趋势-策略匹配矩阵（"显示但降分"策略）：

| 策略 | 上涨 | 横盘 | 下跌 |
|------|------|------|------|
| Sell Call / Buy Call | 100 | 60/50 | 30/20 |
| Sell Put / Buy Put | 30/20 | 60/50 | 100 |

强度调整：匹配趋势 → `score * (1 + strength * 0.2)`; 不匹配 → `score * (1 - strength * 0.3)`

---

## 3. ATR 动态安全边际

```python
required_buffer = ATR(14) * 2.0       # 2 倍 ATR 缓冲
actual_buffer = abs(price - strike)
safety_ratio = actual_buffer / required_buffer    # >= 1.0 安全
```

| safety_ratio | 得分 | 额外调整 |
|-------------|------|----------|
| >= 2.0 | 100 | atr_multiples >= 3: +10 |
| 1.5-2.0 | 90-100 | atr_multiples >= 2: +5 |
| 1.0-1.5 | 70-90 | |
| 0.5-1.0 | 40-70 | |
| < 0.5 | 0-40 | atr_multiples < 1: -10 |

---

## 4. Sell Put 计分器

**文件**: `scoring/sell_put.py` | 筛选: `strike <= price * 1.02`, `time_value > 0`

| 指标 | 权重 | 评分要点 |
|------|------|----------|
| `premium_yield` | 20% | 年化 >= 20%: 100; 15-20%: 80+; 10-15%: 60+; 5-10%: 40+ |
| `support_strength` | 20% | S1(25), S2(20), MA50(20), MA200(25), 52w_low(10)，距离越近分越高 |
| `safety_margin` | 15% | 基础（百分比安全边际）+ ATR 调整（ratio >= 1.5: +15; >= 1.0: +5; < 0.5: -20） |
| `trend_alignment` | 15% | 下跌趋势 100 / 横盘 60 / 上涨 30 |
| `probability_profit` | 15% | Black-Scholes: `norm.cdf(-d1)` x 100; 或简化版按安全边际查表 |
| `liquidity` | 10% | volume/10(max 50) + OI/50(max 30) + spread 评分(max 20) |
| `time_decay` | 5% | 20-45 天: 100; 10-20: 70+; 45-90: 递减; < 10: 高 Gamma 风险 |

---

## 5. Sell Call 计分器

**文件**: `scoring/sell_call.py` | 筛选: `strike >= price * 0.98`

| 指标 | 权重 | 评分要点 |
|------|------|----------|
| `premium_yield` | 20% | 同 Sell Put |
| `resistance_strength` | 20% | R1(25), R2(20), 52w_high(25), MA50+5%(15), MA200+8%(15) |
| `trend_alignment` | 15% | 上涨 100 / 横盘 60 / 下跌 30 |
| `upside_buffer` | 15% | 百分比缓冲 + ATR 调整（同 safety_margin） |
| `liquidity` | 10% | 同 Sell Put |
| `is_covered` | 10% | 持股 100 / 裸卖 50 |
| `time_decay` | 5% | 15-30 天: 100; 7-15: 90; 偏好更短期限 |
| `overvaluation` | 5% | 距 R1 <= 2%: 90; 距 52w_high <= 3%: 85; 当日涨 >= 3%: 80 |

---

## 6. Buy Call 计分器

**文件**: `scoring/buy_call.py`

| 指标 | 权重 | 评分要点 |
|------|------|----------|
| `bullish_momentum` | 25% | 当日涨幅 >= 3%: 100; 52 周位置 >= 70%: +20 |
| `breakout_potential` | 20% | 距 R1 <= 3%: +25; 执行价 >= R1*1.02: +20; 距 52w_high <= 5%: +15 |
| `value_efficiency` | 20% | delta/mid_price; 平值(-5%~5%): +10; 深度虚值(< -15%): -15 |
| `volatility_timing` | 15% | 偏好低 IV: IV/HV <= 0.85: +25; IV pctl <= 30: +20 |
| `liquidity` | 10% | 同上 |
| `time_optimization` | 10% | 时间价值比 0.2-0.6 理想; 到期 30-60 天最佳 |

---

## 7. Buy Put 计分器

**文件**: `scoring/buy_put.py`

| 指标 | 权重 | 评分要点 |
|------|------|----------|
| `bearish_momentum` | 25% | 当日跌幅 >= 3%: 100; 52 周位置 <= 20%: +15 |
| `support_break` | 20% | 距 S1 <= 3%: +30; 执行价 <= S1: +20; 跌幅 >= 2%+接近 S1: +25 |
| `value_efficiency` | 20% | 同 Buy Call 逻辑 |
| `volatility_expansion` | 15% | 偏好低 IV: IV/HV <= 0.8: +30; IV pctl <= 20: +25 |
| `liquidity` | 10% | 同上 |
| `time_value` | 10% | 时间价值比 0.3-0.7 理想; 到期 30-60 天最佳 |

---

## 8. VRP 计算系统

**文件**: `advanced/vrp_calculator.py`

```python
vrp_absolute = implied_vol - historical_vol
vrp_relative = (IV - HV) / HV
```

| VRP 相对值 | 等级 | 卖方 | 买方 |
|-----------|------|------|------|
| >= 15% | very_high | 非常有利 | 不利 |
| 5%-15% | high | 有利 | 略不利 |
| -5%-5% | normal | 中性 | 中性 |
| -15%~-5% | low | 不利 | 有利 |
| < -15% | very_low | 非常不利 | 非常有利 |

**策略建议**: 高 VRP → sell_put/sell_call (high confidence); 低 VRP → buy_call/buy_put (high confidence)

**胜率调整**: very_high VRP → Sell Put prob + 5%(cap 90%); very_low VRP → Buy Call prob + 5%(cap 60%)

---

## 9. 风险收益风格标签

**文件**: `scoring/risk_return_profile.py`

### 四种风格

| 风格 | 典型胜率 | 典型收益 | 风险等级颜色 |
|------|----------|----------|-------------|
| `steady_income`（稳健收益） | 65-80% | 1-5%/月 | green (low) |
| `balanced`（稳中求进） | 40-55% | 50-200% | yellow (moderate) |
| `high_risk_high_reward` | 20-40% | 2-10 倍 | orange/red (high/very_high) |
| `hedge`（保护对冲） | 30-50% | 0-1 倍 | green (low) |

### 判定规则摘要

| 策略 | steady_income 条件 | high_risk 条件 |
|------|-------------------|---------------|
| Sell Put | 安全边际 >= 10% 且年化 <= 25% | 安全边际 < 3% 或年化 > 50% |
| Sell Call | 距离 >= 15% 且年化 <= 20% | 距离 < 8% |
| Buy Call | -- | 虚值 > 10%（距离越大风险越高） |
| Buy Put | hedge: 距离 <= 5% 且成本 <= 5% | 虚值 > 8% |

---

## 10. 推荐排序与输出

### 筛选条件

| 条件 | 阈值 |
|------|------|
| Open Interest | >= 10 |
| Bid-Ask Spread | <= 10% |
| Time Value | > 0 |

### 输出流程

筛选 → 添加风格标签 → 按 score 降序 → 返回 **Top 10**

每条推荐包含：基础信息（strike, expiry, bid/ask）、综合得分 + 明细 breakdown、ATR 安全指标、风格标签（style, risk_level, win_probability, summary_cn）、趋势警告。

---

## 11. 算法总结

| 策略 | 核心权重 | 理想趋势 | 关键指标 |
|------|----------|----------|----------|
| Sell Put | support 20% + premium 20% | 下跌 | 支撑位、安全边际、ATR |
| Sell Call | resistance 20% + premium 20% | 上涨 | 阻力位、上涨缓冲、Covered |
| Buy Call | momentum 25% + breakout 20% | 上涨 | 动量、突破潜力、Delta 效率 |
| Buy Put | momentum 25% + support_break 20% | 下跌 | 动量、支撑突破、波动率 |

---

## 12. 核心文件

| 文件 | 职责 |
|------|------|
| `backend/app/analysis/options_analysis/scoring/sell_put.py` | Sell Put 计分器 |
| `backend/app/analysis/options_analysis/scoring/sell_call.py` | Sell Call 计分器 |
| `backend/app/analysis/options_analysis/scoring/buy_call.py` | Buy Call 计分器 |
| `backend/app/analysis/options_analysis/scoring/buy_put.py` | Buy Put 计分器 |
| `backend/app/analysis/options_analysis/scoring/trend_analyzer.py` | 趋势分析 + ATR |
| `backend/app/analysis/options_analysis/scoring/risk_return_profile.py` | 风格标签 |
| `backend/app/analysis/options_analysis/advanced/vrp_calculator.py` | VRP 计算器 |

---

*文档版本: 2026.02 | 迁移自 docs/OPTIONS_ALGORITHM.md 并结构化重写*

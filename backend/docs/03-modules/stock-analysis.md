# 股票分析模块 (Stock Analysis Module)

## 1. 模块概述

股票分析模块是 AlphaGBM 系统的核心量化引擎，实现了 **AlphaGBM 模型**：

```
G = B (Business Fundamentals) + M (Market Sentiment)
```

- **G (Gain)**: 预期收益，由基本面和市场情绪共同决定
- **B (Basics)**: 营收增长率、利润率、ROE、自由现金流等基本面指标
- **M (Momentum)**: PE/PEG 估值、技术面动量、VIX 恐慌指数等市场情绪指标

系统支持 4 种投资风格（Investment Style），每种风格对 B 和 M 维度赋予不同权重：

| 风格 | 关键词 | 核心关注点 |
|------|--------|-----------|
| `quality` | 质量 | ROE、毛利率、自由现金流、低负债 |
| `value` | 价值 | 低 PE、低 PB、高股息率、安全边际 |
| `growth` | 成长 | 营收增长率、利润增长率、PEG < 1.5 |
| `momentum` | 趋势 | 价格动量、均线排列、RSI、成交量 |

---

## 2. StockAnalysisEngine -- 分析引擎主类

**文件**: `app/analysis/stock_analysis/core/engine.py` (194 行)

引擎采用**组合模式 (Composition)**，将职责委托给三个专用组件：

```python
class StockAnalysisEngine:
    def __init__(self):
        self.data_fetcher = StockDataFetcher()      # 数据获取
        self.calculator = StockCalculator()           # 指标计算
        self.basic_strategy = BasicAnalysisStrategy() # 策略分析
```

### 核心方法

| 方法 | 签名 | 功能 |
|------|------|------|
| `analyze_stock` | `(ticker, style, **kwargs) -> Dict` | 完整分析流水线：获取数据 -> 流动性检查 -> 策略分析 -> 整合结果 |
| `get_quick_quote` | `(ticker) -> Dict` | 委托 DataFetcher 获取实时报价 |
| `check_stock_liquidity` | `(ticker) -> Tuple[bool, Dict]` | 获取历史数据后检查流动性 |
| `calculate_target_price` | `(ticker, style) -> Dict` | 先做风险分析，再计算目标价格 |

**工厂函数**: `create_stock_engine()` 提供向后兼容的实例化入口。

### analyze_stock 流程

`get_market_data` -> `check_liquidity` -> `basic_strategy.analyze` -> 整合返回。

---

## 3. StockDataFetcher -- 数据获取器

**文件**: `app/analysis/stock_analysis/core/data_fetcher.py` (408 行)

### 股票代码规范化

`normalize_ticker()` 将用户输入统一转换为 Yahoo Finance 格式：

| 输入格式 | 前缀匹配 | 输出格式 | 交易所 |
|----------|----------|---------|--------|
| `600519` | `60`, `68` | `600519.SS` | 上海证券交易所 |
| `000001` | `00`, `30` | `000001.SZ` | 深圳证券交易所 |
| `AAPL` | 非数字 | `AAPL` | 美股直接返回 |

### 数据获取策略

**get_ticker_price()**: 最大 **3 次重试**，间隔 **2 秒**，捕获 `YFRateLimitError` 时双倍等待。
返回 `current_price`, `previous_close`, `change_percent`, `market_cap` 等字段。

**get_market_data()**: 通过 `DataProvider` adapter 访问数据源，默认 **2 年历史周期**。
`onlyHistoryData=True` 跳过实时价格。自动计算 `avg_volume_30d`、`price_52w_high/low`。

**get_macro_market_data()**: 拉取 S&P 500、NASDAQ、Russell 2000、VIX 指数，
10 年期美债收益率 (`^TNX`)，回退值 4.5%。

---

## 4. StockCalculator -- 指标计算器

**文件**: `app/analysis/stock_analysis/core/calculator.py` (516 行)

### 流动性检查

`check_liquidity(data, currency_symbol)` 判断标准：

```
avg_daily_volume_usd = mean(近30日每日成交额)
is_liquid = avg_daily_volume_usd >= MIN_DAILY_VOLUME_USD
```

数据优先级：`history_prices * history_volumes` > `info.averageVolume * regularMarketPrice`

### ATR 计算

`calculate_atr(hist_data, period=14)` -- 14 期 Average True Range：

```python
True Range = max(High - Low, |High - PrevClose|, |Low - PrevClose|)
ATR = rolling_mean(True Range, window=14)
```

### ATR 动态止损

`calculate_atr_stop_loss(buy_price, hist_data, beta=None)`:

```
止损价格 = buy_price - (ATR * multiplier)
```

**Beta 调整规则**：
- `beta > 1.5`: multiplier *= **1.2** (高波动 -> 放宽止损)
- `beta < 0.8`: multiplier *= **0.8** (低波动 -> 收紧止损)

**回退机制**: ATR 计算失败时使用固定 **15% 止损** (`FIXED_STOP_LOSS_PCT = 0.15`)

### 市场情绪

`calculate_market_sentiment(data)`: 综合评分 -100~+100，基于价格动量、成交量趋势、
年化波动率、SMA20/SMA50 位置。等级：`bullish`(>30) / `neutral` / `bearish`(<-30)。

---

## 5. BasicAnalysisStrategy -- 基础分析策略

**文件**: `app/analysis/stock_analysis/strategies/basic.py` (1044 行)

### analyze() 主流程

`detect_market` -> `get_market_config` -> `classify_company` -> `analyze_risk_and_position`
-> `_analyze_{style}_style` -> 应用 `MARKET_STYLE_WEIGHTS` -> `_generate_recommendation`。

### 公司分类 classify_company()

**市值分类**:

| 类别 | 市值阈值 | 中文名称 |
|------|---------|---------|
| `mega_cap` | >= $200B | 超大盘股 |
| `large_cap` | >= $10B | 大盘股 |
| `mid_cap` | >= $2B | 中盘股 |
| `small_cap` | >= $300M | 小盘股 |
| `micro_cap` | < $300M | 微盘股 |

**增长 vs 价值检测**:
- `PE > 25 && RevenueGrowth > 15%` -> **Growth**
- `PE < 15 && RevenueGrowth < 10%` -> **Value**
- 其余 -> **Blend**

**ETF 检测**: 通过 `quoteType` 字段和名称关键词 (`etf`, `fund`, `ishares`, `vanguard` 等) 识别。

### 四种风格差异化分析

**Growth 风格** (`_analyze_growth_style`):
- 收入增长 > 25% -> +30 分，> 15% -> +20 分
- 利润增长 > 30% -> +25 分
- PEG < 1.0 -> +15 分

**Value 风格** (`_analyze_value_style`):
- PE < 10 -> +25 分，< 15 -> +20 分
- PB < 1.0 (破净) -> +20 分
- 股息率 > 4% -> +15 分

**Quality 风格** (`_analyze_quality_style`):
- ROE > 25% -> +30 分 (权重 30%)
- 毛利率 > 50% -> +20 分 (权重 25%)
- FCF/NI > 1.0 -> +20 分 (权重 25%)
- D/E < 30% -> +15 分 (权重 20%)

**Momentum 风格** (`_analyze_momentum_style`):
- 5 日涨幅、MA20 vs MA50 趋势、RSI(14)、成交量量比、52 周位置

---

## 6. 风险分析五大支柱

`analyze_risk_and_position()` 构建综合风险评分（0-100），覆盖以下维度：

### (1) ATR 动态止损
基于 14 期 ATR 计算止损价格，Beta 调整 multiplier（+20%/-20%），
ATR 不可用时回退到固定 15% 止损。

### (2) Beta 调整
- `beta > 1.5`: 高 beta，风险评分 +25
- 波动率 > 50%: 风险评分 +25
- 波动率 > 30%: 风险评分 +15

### (3) VIX 预警
通过宏观数据集成 VIX 值：
- `VIX > 30`: 高波动风险
- AI 报告中标注 Vanna crush 和负 Gamma 风险

### (4) 流动性检查
按市场差异化最低日均成交额阈值：

| 市场 | 最低日均成交额 |
|------|--------------|
| US (美股) | $5,000,000 |
| CN (A股) | $1,000,000 (CNY 折算) |
| HK (港股) | $2,000,000 |

### (5) 盈利事件预警
财报日期距离分级：
- **< 7 天** (高危): 强烈建议减仓 30-50% 或全部避险
- **7-14 天** (中危): 建议提前规划
- **> 14 天** (低危): 正常持有

### 风险等级与仓位建议

| 风险评分 | 等级 | 建议仓位 |
|---------|------|---------|
| >= 60 | `high` | 2% |
| >= 35 | `medium` | 3% |
| < 35 | `low` | 5% |

风格调整：Growth 仓位 * 1.2 (最大 8%)，Value 仓位 * 1.1 (最大 6%)。

---

## 7. EV 期望值模型

**文件**: `app/services/ev_model.py` (896 行)

### 核心公式

```
EV = P(up) * Upside + P(down) * Downside
```

### 概率估算 -- calculate_probability_from_features()

基于特征工程的概率调整（基础 50%），约束范围 [20%, 80%]：

| 特征 | 调整幅度 |
|------|---------|
| 52 周低位 (< 30%) | +10% |
| 52 周高位 (> 80%) | -10% |
| 多头排列 (Price > MA50 > MA200) | +12% |
| 空头排列 (Price < MA50 < MA200) | -12% |
| PEG < 1.0 | +8% |
| 负增长 | -8% |
| 高风险评分 (>= 4) | -15% |

### 幅度估算 -- calculate_expected_move()

```
expected_move = implied_vol * sqrt(time_horizon_days / 252)
```

优先使用期权隐含波动率，回退到历史波动率。结合 52 周高低点做保守修正。

### 多时间框架加权

```python
ev_weighted = ev_1week * 0.50 + ev_1month * 0.30 + ev_3months * 0.20
```

短期权重更高，因为预测准确性随时间递减。

### Extended EV -- calculate_ev_model_extended()

```
EV_extended = EV_base + sector_rotation_premium + capital_structure_factor
```

整合板块轮动溢价和资金结构因子，生成扩展推荐。

### 推荐阈值

| EV 范围 | 推荐 Action |
|---------|------------|
| > +10% | `STRONG_BUY` |
| +5% ~ +10% | `BUY` |
| 0% ~ +5% | `CAUTIOUS_BUY` |
| -3% ~ 0% | `HOLD` |
| -8% ~ -3% | `AVOID` |
| < -8% | `STRONG_AVOID` |

安全阀：目标价低于当前价时，`BUY` / `STRONG_BUY` 强制降级为 `HOLD`。

---

## 8. AI 报告生成

**文件**: `app/services/ai_service.py` (953 行)

### Gemini 集成

- 模型: **Gemini 2.5-flash** (`models/gemini-2.5-flash`)
- API Key 来源: `GOOGLE_API_KEY` 环境变量
- 超时记录: `elapsed = time.time() - start_time`

### 7 章节 Markdown 报告结构

| 章节 | 内容 |
|------|------|
| 第一部分 | 投资风格与原则重申 |
| 第二部分 | 公司概况（业务介绍 + 最新动态） |
| 第三部分 | AlphaGBM 深度解构 (B + M + G) |
| 第四部分 | 五大支柱检查（怀疑主义 + 事前验尸） |
| 第五部分 | 风险控制评估（风险评分 + EV 短期波动） |
| 第六部分 | 估值分析与交易策略（含宏观背景） |
| 第七部分 | 卖出策略（止盈 / 止损 / 分阶段 / 特殊情况） |

### ETF 特殊处理

检测到 ETF 时：
- 跳过公司财务指标（PE、营收等）
- 改为分析跟踪标的指数、管理费率、跟踪误差
- 杠杆 ETF 额外标注时间衰减风险

### 宏观数据集成

Prompt 中动态注入以下宏观信息：
- 10 年期美债收益率 (`^TNX`)、美元指数 (`DXY`)、黄金、原油
- VIX 恐慌指数及变化率
- CPI 数据发布日期、美联储利率决议 (FOMC) 日期
- 期权到期日（含四重到期日）
- 地缘政治风险指数

### AlphaGBM 系统研判注入

`_compute_alphagbm_recommendation()` 预计算操作建议，注入 Prompt 中作为强制约束，
确保 AI 输出不与量化系统的方向矛盾。

### 回退机制

`get_fallback_analysis()`: 当 Gemini 不可用（`genai is None` 或无 API Key）时，
生成纯 Markdown 格式的结构化报告，包含完整的 AlphaGBM 分析、风险评估和交易建议。

---

## 9. 市场差异化

**文件**: `app/params/market.py` (165 行)

### 三市场参数对比

| 参数 | US (美股) | CN (A股) | HK (港股) |
|------|----------|---------|----------|
| `min_daily_volume_usd` | $5M | $1M | $2M |
| `risk_premium` | 1.0 (基线) | 1.3 (政策风险) | 1.15 |
| `growth_discount` | 0.6 | 0.7 (偏好成长) | 0.65 |
| `pe_high_threshold` | 40 | 50 (A股 PE 普遍较高) | 35 |
| `volatility_adjustment` | 1.0 | 1.2 (波动率更高) | 1.1 |
| `policy_risk_factor` | -- | 1.2 | -- |
| `discount_factor` | -- | -- | 0.95 (A/H 折价) |

### 风格权重差异

| 风格 | US | CN | HK |
|------|-----|-----|-----|
| `quality` | 1.0 | 0.8 | **1.2** |
| `value` | 1.0 | 0.7 | **1.3** |
| `growth` | 1.0 | **1.3** | 0.9 |
| `momentum` | 1.0 | **1.2** | 0.8 |

A股偏好成长和趋势，港股偏好价值和质量，美股各风格均衡。

### 市场识别规则

Ticker 后缀映射: `.SS` / `.SZ` -> CN, `.HK` -> HK, 其余 -> US

A股代码前缀: `60` / `68` -> 上交所 (`.SS`), `00` / `30` -> 深交所 (`.SZ`)

---

## 10. 文件路径清单

```
backend/app/analysis/stock_analysis/
  core/
    engine.py            # StockAnalysisEngine (194 行)
    data_fetcher.py      # StockDataFetcher (408 行)
    calculator.py        # StockCalculator (516 行)
  strategies/
    basic.py             # BasicAnalysisStrategy (1044 行)

backend/app/services/
  ev_model.py            # EV 期望值模型 (896 行)
  ai_service.py          # Gemini AI 报告生成 (953 行)
  data_provider.py       # DataProvider adapter (统一数据源)

backend/app/params/
  market.py              # 市场差异化配置 (165 行)
  valuation.py           # 估值参数 (PEG, PE, Growth)
  risk_management.py     # 风险参数 (ATR, Beta, VIX)
  sector_rotation.py     # 板块轮动配置
  capital_structure.py   # 资金结构配置

backend/app/
  constants.py           # 向后兼容参数导出 (192 行)
```

# AI Services 模块

## 1. Gemini 分析报告服务

**文件**: `app/services/ai_service.py` (~952 lines)

### 1.1 模型配置

| 配置项 | 值 |
|--------|---|
| Model | `gemini-2.5-flash` |
| Temperature | 0.7 |
| Max Output Tokens | 8192 |
| API Provider | Google Generative AI |

### 1.2 七章节报告结构

每次股票分析生成一份包含 7 个章节的完整 AI 报告：

| 章节 | 内容 |
|------|------|
| 1. 投资风格原则 (Investment Style Principles) | 根据 style 参数生成分析框架，定下基调 |
| 2. 公司概述与新闻 (Company Overview & News) | 基本面概述、最新新闻影响、关键事件 |
| 3. AlphaGBM 深度分析 (AlphaGBM Deep Dive) | G=B+M 框架评分及行业百分位排名 |
| 4. 五大支柱检查 (Five Pillar Check) | 盈利/增长/财务/估值/技术 Pass/Caution/Fail |
| 5. 风控评估 (Risk Assessment) | 波动率/回撤/流动性/系统性/地缘风险 |
| 6. 估值与策略 (Valuation & Strategy) | DCF/相对估值/入场价位/仓位/期权配合 |
| 7. 退出策略 (Exit Strategy) | 止盈/止损/技术退出信号/持有时间 |

### 1.3 AlphaGBM 框架: G = B + M

| 分量 | 含义 | 分析维度 |
|------|------|---------|
| **G** (Growth) | 综合增长评分 | 最终复合评分 |
| **B** (Base) | 基础面评分 | 营收、利润、现金流增长率 |
| **M** (Momentum) | 动量评分 | 价格动量、资金流向、技术指标 |

### 1.4 五大支柱检查

| 支柱 | 检查内容 |
|------|---------|
| Profitability | ROE, ROA, Net Margin |
| Growth Driver | Revenue/EPS Growth, TAM |
| Financial Health | Debt/Equity, Current Ratio, FCF |
| Valuation | P/E, P/B, PEG, EV/EBITDA |
| Technical Trend | MA, RSI, MACD, Volume |

### 1.5 ETF 特殊处理

当分析标的为 ETF 时 (如 SPY, QQQ, XLK)：

- **排除指标**: P/E ratio, PEG ratio (ETF 这些指标无意义)
- **替代分析**: 费用比率 (Expense Ratio)、跟踪误差 (Tracking Error)、持仓集中度
- **行业暴露**: 分析 ETF 的行业分布及权重

### 1.6 宏观数据注入

AI 报告生成时注入以下宏观经济数据作为上下文：

| 数据项 | 来源 |
|--------|------|
| 美国国债收益率 Treasury Yield (10Y) | DataProvider |
| 美元指数 DXY (Dollar Index) | DataProvider |
| 黄金 Gold (XAU/USD) / 原油 Oil (WTI) | DataProvider |
| CPI (Consumer Price Index) | DataProvider |
| FOMC 会议日程 (Fed Meeting Schedule) | 硬编码/API |

### 1.7 盈利日期预警

- 检查目标公司下一个 Earnings Date
- 距盈利日 **<= 7 天** 时标记为 **高风险 (High Risk)**
- 期权策略会考虑盈利日 IV Crush 风险

### 1.8 中国特殊分析

针对 A 股 (`.SS`, `.SZ`) 和港股 (`.HK`) 标的额外分析：政策新闻、主力资金流向、龙虎榜机构席位。

### 1.9 一致性要求

**AlphaGBM 推荐不可矛盾**: AI 报告各章节结论必须与 AlphaGBM 框架评分方向一致。
Prompt 约束: `"Ensure your recommendations are consistent with the AlphaGBM score"`

### 1.10 Fallback 机制

**get_fallback_analysis()**: Gemini API 不可用时生成 Markdown 基础报告。纯数据驱动，标注 `[Fallback Report - AI Service Unavailable]`。

---

## 2. 叙事投资服务 (Narrative Investment)

**文件**: `app/services/narrative_service.py` (~584 lines)

### 2.1 概述

基于"投资叙事"(Investment Narrative) 理论，提供热门主题的针对性分析和策略推荐。

### 2.2 10 个预设叙事

**5 大人物叙事 (Character Narratives)**:

| Key | 名称 | 风格 |
|-----|------|------|
| `musk` | Elon Musk | 颠覆性创新、高风险高回报 |
| `buffett` | Warren Buffett | 价值投资、护城河、安全边际 |
| `ark` | Cathie Wood / ARK | 破坏性创新、5 年期、高成长 |
| `dalio` | Ray Dalio | 全天候策略、风险平价 |
| `burry` | Michael Burry | 逆向投资、深度价值 |

**5 大主题叙事 (Theme Narratives)**:

| Key | 名称 | 描述 |
|-----|------|------|
| `ai_chips` | AI 芯片革命 | GPU 供应链、算力需求 |
| `glp1` | GLP-1 减肥药浪潮 | 肥胖症药物、医疗器械 |
| `quantum` | 量子计算 | 量子优越性、商业化路径 |
| `robotics` | 机器人与自动化 | 人形机器人、工业自动化 |
| `ev_battery` | 电动车与电池 | 锂电/固态电池、充电基础设施 |

### 2.3 核心方法: analyze_narrative(concept, market, narrative_key, lang)

| 参数 | 说明 |
|------|------|
| `concept` | 用户输入的投资概念/股票 |
| `market` | 市场: `us` / `hk` / `cn` |
| `narrative_key` | 叙事 key (上述 10 个之一) |
| `lang` | 语言: `zh` / `en` |

输出：叙事框架投资逻辑、相关标的推荐 (3-5 只)、风险识别、入场时机、策略推荐。

### 2.4 策略推荐

| 策略 | 适用场景 |
|------|---------|
| ZEBRA (Zero Extrinsic Back Ratio) | 长期看涨替代持股 |
| LEAPS (Long-Term Equity Anticipation Securities) | 长期期权杠杆策略 |

根据叙事时间跨度选到期日，根据确定性选 Delta，输出具体 strike price 建议。

### 2.5 多语言与 Fallback

- 支持 `zh` (中文报告，术语保留英文) 和 `en` (全英文报告)
- `FALLBACK_DATA`: 每个叙事预设约 500-800 字离线分析，API 不可用时返回

---

## 3. 图像识别服务 (Image Recognition)

**文件**: `app/services/image_recognition_service.py` (~217 lines)

### 3.1 模型配置

使用 `gemini-1.5-flash` (Vision) 对期权交易截图进行 OCR 与结构化提取。

### 3.2 提取字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `symbol` | str | 标的股票代码 (e.g. `AAPL`) |
| `option_type` | str | 期权类型: `call` / `put` |
| `strike` | float | 行权价 |
| `expiry` | str | 到期日 (YYYY-MM-DD) |
| `price` | float | 期权价格 (premium) |
| `IV` | float | 隐含波动率 (Implied Volatility) |

### 3.3 处理流程

接收图片 (PNG/JPG/JPEG) -> Base64 编码 -> Gemini Vision Prompt -> API 调用 -> JSON 解析 -> 字段验证 -> Confidence 评估 -> 返回结构化结果

### 3.4 Confidence 评估

| 置信度 | 范围 | 含义 |
|--------|------|------|
| `high` | >= 0.9 | 字段清晰可读 |
| `medium` | 0.7-0.9 | 可能存在模糊 |
| `low` | < 0.7 | 建议用户确认 |

整体置信度取所有字段中的最低值。

### 3.5 JSON 容错

三级 fallback 解析：直接 `json.loads()` -> 提取 `` ```json ``` `` 代码块 -> 提取 `{...}` 片段。全部失败时抛出 ValueError。

---

## 4. 文件路径清单

| 文件路径 | 说明 | 大致行数 |
|---------|------|---------|
| `app/services/ai_service.py` | Gemini 分析报告核心服务 | ~952 |
| `app/services/narrative_service.py` | 叙事投资分析服务 | ~584 |
| `app/services/image_recognition_service.py` | 图像识别服务 | ~217 |
| `app/routes/analysis_routes.py` | 分析相关 API 路由 | ~200 |
| `app/routes/narrative_routes.py` | 叙事投资 API 路由 | ~80 |

---

## 5. 注意事项

- Gemini API key 通过环境变量 `GOOGLE_API_KEY` 配置
- AI 报告生成耗时约 15-30 秒，通过 Task Queue 异步处理
- Fallback 报告质量远低于 AI 报告，应监控 API 可用率
- 图像识别仅支持英文 broker 界面截图，中文界面尚未适配
- 叙事投资的 FALLBACK_DATA 需定期更新以保持时效性
- 所有 AI 服务调用均有 retry 机制 (最多 3 次，指数退避)

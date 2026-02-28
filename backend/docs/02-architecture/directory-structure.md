# AlphaGBM Backend 目录结构

> 本文档描述 `backend/` 的完整目录结构，每个文件附带一行中文说明。
> 技术术语保留英文原文。

---

## 顶层文件

```
backend/
├── run.py                    # 应用入口，启动 Flask dev server (port 5002)
├── requirements.txt          # Python 依赖清单
├── Dockerfile                # Docker 容器构建配置
├── .env                      # 环境变量配置（不入版本控制）
├── .env.example              # 环境变量模板（入版本控制，供新开发者参考）
```

`run.py` 是本地开发的唯一入口，调用 `create_app()` 工厂函数后以 debug 模式监听 5002 端口。
生产环境通过 Dockerfile 构建镜像，由 Gunicorn 等 WSGI server 启动。

---

## app/ -- 应用主包

```
app/
├── __init__.py               # 应用工厂 create_app()，蓝图注册，DB 初始化
├── config.py                 # 配置类（DB URL、Stripe key、SMTP、Gemini key）
├── constants.py              # 向后兼容的常量导出（代理到 params/）
├── models.py                 # 全部 SQLAlchemy 模型（18 个模型 + 7 个枚举）
├── scheduler.py              # APScheduler 定时任务（每日 P&L、飞书日报）
```

`__init__.py` 中的 `create_app()` 是整个后端的组装点：加载配置、初始化数据库、
注册全部 Blueprint、启动 Scheduler。`models.py` 集中定义所有 ORM 模型，
包括 User、Stock、Option、Portfolio、Payment 等 18 张表及 7 个枚举类型。

---

## app/api/ -- 路由层（12 个 Blueprint）

```
app/api/
├── auth.py                   # /api/auth/*     认证：注册、登录、JWT 刷新
├── user.py                   # /api/user/*     用户信息、偏好配置
├── stock.py                  # /api/stock/*    股票分析、搜索、历史数据
├── options.py                # /api/options/*  期权分析、期权链、增强分析
├── payment.py                # /api/payment/*  支付、订阅、额度管理
├── portfolio.py              # /api/portfolio/* 投资组合、P&L 损益
├── sector.py                 # /api/sector/*   行业分析、轮动策略
├── narrative_routes.py       # /api/narrative/* AI 叙事投资
├── tasks.py                  # /api/tasks/*    异步任务状态查询
├── analytics.py              # /api/analytics/* 事件追踪、使用统计
├── metrics.py                # /api/metrics/*  系统监控指标
└── feedback.py               # /api/feedback/* 用户反馈收集
```

路由层只负责 HTTP 请求/响应的解析与序列化，不包含业务逻辑。
每个文件对应一个 Flask Blueprint，在 `create_app()` 中统一注册。
认证相关路由（`auth.py`）处理 JWT 签发与刷新；业务路由通过
`@require_auth` 装饰器进行鉴权后，委托 `services/` 层执行具体逻辑。

---

## app/services/ -- 业务逻辑层

```
app/services/
├── analysis_engine.py          # 分析引擎入口（调度 stock/options 分析）
├── data_provider.py            # DataProvider 门面（封装 MarketDataService）
├── payment_service.py          # PaymentService（Stripe 集成、额度扣减、订阅管理）
├── options_service.py          # 期权业务服务
├── option_scorer.py            # 期权评分算法（SPRV / SCRV / BCRV / BPRV）
├── option_models.py            # 期权数据模型（Pydantic dataclass）
├── recommendation_service.py   # 每日推荐生成（热门标的 + 评分排序）
├── sector_rotation_service.py  # 行业轮动服务
├── capital_structure_service.py # 资本结构分析服务
├── ai_service.py               # Gemini AI 分析报告生成
├── narrative_service.py        # AI 叙事投资（预设主题 + 自定义主题）
├── image_recognition_service.py # Gemini Vision 图像识别（期权截图解析）
├── ev_model.py                 # EV 期望值模型
├── task_queue.py               # 异步任务队列（ThreadPoolExecutor）
└── feishu_bot.py               # 飞书机器人（每日运营数据推送）
```

`services/` 是核心业务逻辑的聚集地。`analysis_engine.py` 作为统一入口，
根据请求类型分发到股票分析或期权分析流程。`payment_service.py` 封装了
Stripe 支付全流程，包括订阅创建、Webhook 处理和查询额度扣减。
`ai_service.py` 和 `narrative_service.py` 负责调用 Gemini API 生成
自然语言分析报告。`task_queue.py` 使用线程池处理耗时任务，
前端通过 `/api/tasks/*` 轮询获取结果。

---

### app/services/market_data/ -- 市场数据子系统

```
app/services/market_data/
├── service.py                # MarketDataService 单例（路由 + 缓存 + failover）
├── cache.py                  # 多级缓存（内存 L1 + DB L2）
├── config.py                 # 数据服务配置（超时、重试、缓存 TTL）
├── interfaces.py             # 抽象接口定义（DataAdapter Protocol）
├── metrics.py                # 性能指标收集（命中率、延迟、错误率）
├── market_detector.py        # 市场检测器（ticker -> US / CN / HK / COMMODITY 市场识别）
├── deduplicator.py           # 请求去重（500ms 窗口内合并相同请求）
│
└── adapters/                 # 数据源适配器
    ├── base.py               # 适配器抽象基类
    ├── yfinance_adapter.py   # Yahoo Finance 适配器（美股/港股主力源）
    ├── defeatbeta_adapter.py # DefeatBeta 适配器
    ├── tiger_adapter.py      # Tiger Securities 适配器（老虎证券）
    ├── alphavantage_adapter.py # Alpha Vantage 适配器
    ├── tushare_adapter.py    # Tushare 适配器（A 股数据）
    └── akshare_commodity_adapter.py # AkShare 适配器（商品期货期权）
```

市场数据子系统采用 Adapter 模式，将多个第三方数据源统一为相同接口。
`MarketDataService` 作为单例对外暴露，内部实现了智能路由（根据 ticker 所属市场
选择最优数据源）、多级缓存（内存 -> 数据库）和 failover（主源失败自动切换备源）。
`deduplicator.py` 在 500ms 窗口内合并重复请求，避免高并发下对上游 API 的冗余调用。

---

## app/analysis/ -- 量化分析引擎

### 股票分析

```
app/analysis/stock_analysis/
├── core/
│   ├── engine.py             # StockAnalysisEngine 主引擎
│   ├── data_fetcher.py       # StockDataFetcher 数据获取
│   ├── calculator.py         # StockCalculator 指标计算（技术面 + 基本面）
│   ├── capital_structure.py  # 资本结构分析（负债率、利息覆盖）
│   └── sector_rotation.py    # 行业轮动因子计算
├── strategies/
│   └── basic.py              # 4 种投资风格评分策略
└── data/
    └── sector_mappings.py    # 行业分类映射表（GICS -> 自定义分类）
```

### 期权分析

```
app/analysis/options_analysis/
├── option_market_config.py   # 多市场参数配置（US/HK/CN/COMMODITY）
├── core/
│   ├── engine.py             # OptionsAnalysisEngine 主引擎
│   └── data_fetcher.py       # OptionsDataFetcher 期权链数据获取（含商品期权）
├── scoring/
│   ├── sell_put.py           # Sell Put 评分器（SPRV 策略）
│   ├── sell_call.py          # Sell Call 评分器（SCRV 策略）
│   ├── buy_call.py           # Buy Call 评分器（BCRV 策略）
│   ├── buy_put.py            # Buy Put 评分器（BPRV 策略）
│   ├── trend_analyzer.py     # 趋势分析（多时间框架）
│   └── risk_return_profile.py # 风险收益标签（保守/平衡/激进）
└── advanced/
    ├── vrp_calculator.py     # VRP 波动率风险溢价计算
    ├── risk_adjuster.py      # 风险调整因子（VIX、行业 Beta）
    └── delivery_risk.py      # 商品期权交割风险评估（T-30/T-60 风控）
```

`analysis/` 是 AlphaGBM 的量化核心。股票分析引擎计算技术指标、基本面评分、
资本结构健康度和行业轮动因子，输出综合评分和多维度标签。期权分析引擎对
四种主要期权策略（Sell Put / Sell Call / Buy Call / Buy Put）分别评分，
结合 VRP 波动率溢价和趋势分析生成推荐。`scoring/` 下的四个评分器
是系统的核心定价逻辑，各自独立维护评分权重和阈值。

---

## app/params/ -- 参数配置（按域模块化）

```
app/params/
├── valuation.py              # 估值参数（权重、PEG 阈值、收益滞后天数）
├── risk_management.py        # 风险参数（ATR 系数、Beta 阈值、VIX 区间）
├── market.py                 # 市场参数（US / CN / HK 差异化交易日历与规则）
├── sector_rotation.py        # 行业轮动参数（动量窗口、均值回归系数）
└── capital_structure.py      # 资本结构参数（负债率阈值、利息覆盖倍数）
```

`params/` 将原来散落在各处的魔法数字和阈值统一收归为按业务域划分的配置文件。
修改评分权重或风险阈值时只需编辑对应的参数文件，无需触碰引擎代码。
`constants.py` 中的旧常量名通过代理导入保持向后兼容。

---

## app/utils/ -- 工具类

```
app/utils/
├── auth.py                   # @require_auth 装饰器，JWT token 缓存（5min TTL），用户同步
├── decorators.py             # @check_quota（额度检查），@db_retry（3 次重试 + 指数退避）
└── serialization.py          # numpy / pandas 类型 -> Python 原生类型转换（JSON 序列化）
```

工具层提供横切关注点的复用逻辑。`@require_auth` 在每次请求中验证 JWT 并缓存
解码结果以减少重复解析开销。`@db_retry` 用于应对 SQLite 并发写锁场景下的瞬时失败。

---

## app/docs/ -- API 文档

```
app/docs/
└── openapi.yaml              # OpenAPI 3.0 规范（API 契约定义）
```

---

## 顶层辅助目录

```
backend/
├── tests/                    # 测试文件（单元测试 + 集成测试）
├── scripts/                  # 辅助脚本（数据迁移、批量导入等）
├── data/                     # 数据存储（SQLite 数据库文件）
└── logs/                     # 应用日志（backend.log，按日期轮转）
```

`tests/` 包含基于 pytest 的测试用例。`scripts/` 存放一次性或周期性的运维脚本，
如数据库 schema 迁移、历史数据导入等。`data/` 目录在本地开发时存放 SQLite 文件，
生产环境中可切换为 PostgreSQL。`logs/` 存放运行日志，默认使用 RotatingFileHandler。

---

## 依赖关系概览

```
API 路由层 (api/)
    ↓ 调用
业务逻辑层 (services/)
    ↓ 调用
量化分析引擎 (analysis/)  +  市场数据子系统 (services/market_data/)
    ↓ 读取                        ↓ 请求
参数配置 (params/)           外部数据源 (Yahoo / Tushare / Tiger / ...)
```

整体架构遵循分层设计：路由层只做请求解析和响应格式化，业务逻辑层编排具体流程，
量化引擎执行计算，市场数据层负责外部数据获取与缓存。各层之间通过明确的接口通信，
保持单向依赖。

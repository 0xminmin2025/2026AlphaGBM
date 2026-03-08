# AlphaGBM 后端技术文档

> **版本:** 1.0
> **最后更新:** 2026-02-08
> **项目:** AlphaGBM -- 多市场股票/期权智能分析平台

---

## 文档导航

本文档库为 AlphaGBM 后端系统的完整技术文档，涵盖系统概览、架构设计、模块详解、API 参考、业务流程、测试规范及附录。所有文档按主题分目录组织，便于快速定位。

---

### 01 - 系统概览

系统级介绍，帮助读者快速了解 AlphaGBM 的定位、功能范围和核心术语。

| 文档 | 说明 |
|------|------|
| [系统概览](01-overview/system-overview.md) | 平台定位、技术栈、支持的市场（美股/港股/A股）、核心能力概述 |
| [功能清单](01-overview/feature-checklist.md) | 按模块列出的完整功能列表及当前实现状态 |
| [术语表](01-overview/glossary.md) | 项目中使用的业务术语与技术术语定义（如 GBM、IV、VRP、EV Model 等） |

---

### 02 - 架构设计

从全局视角描述系统的技术架构、代码组织、数据层设计、配置管理及工程规范。

| 文档 | 说明 |
|------|------|
| [整体架构](02-architecture/overall-architecture.md) | 分层架构图、组件关系、请求处理流程、缓存策略及第三方服务集成 |
| [目录结构](02-architecture/directory-structure.md) | 后端代码目录树详解，各目录/文件职责说明 |
| [数据库设计](02-architecture/database-design.md) | PostgreSQL (Supabase) 与 MySQL 双数据库设计、ER 图、表结构与索引说明 |
| [配置与环境变量](02-architecture/config-and-env.md) | 环境变量清单、配置文件说明、多环境（开发/测试/生产）切换方式 |
| [设计标准](02-architecture/design-standards.md) | 编码规范、命名约定、错误处理策略、日志规范及 Code Review 标准 |

---

### 03 - 模块详解

每个核心业务模块的独立设计文档，包含模块职责、类图、核心算法、数据流及依赖关系。

| 文档 | 说明 |
|------|------|
| [认证与用户管理](03-modules/auth-and-user.md) | Supabase Auth 集成、JWT 验证、用户注册/登录、角色与权限、额度管理 |
| [股票分析](03-modules/stock-analysis.md) | 股票分析引擎架构、多市场适配器、数据获取与分析报告生成流程 |
| [股票分析算法](03-modules/stock-analysis-algorithms.md) | GBM 模型、技术指标计算、评分公式、策略信号生成等核心算法详解 |
| [期权分析](03-modules/options-analysis.md) | 期权分析引擎架构、Options Chain 获取、四大策略（Sell Put/Call, Buy Call/Put）分析流程 |
| [期权分析算法](03-modules/options-analysis-algorithms.md) | IV/HV 计算、VRP (Volatility Risk Premium)、EV Model、Greeks 分析、期权评分算法 |
| [支付系统](03-modules/payment-system.md) | Stripe 集成、订阅计划管理、Webhook 处理、额度充值与消费逻辑 |
| [市场数据服务](03-modules/market-data-service.md) | 多数据源适配（YFinance, Tiger API, Alpha Vantage, Tushare, DefeatBeta）、数据标准化与缓存策略 |
| [投资组合管理](03-modules/portfolio-management.md) | 用户持仓跟踪、组合分析、每日盈亏计算、止盈/止损监控 |
| [行业轮动](03-modules/sector-rotation.md) | 行业 ETF 数据获取、行业强度排名、轮动分析与可视化 |
| [任务队列](03-modules/task-queue.md) | 异步任务管理、任务状态机、并发控制、超时处理与重试机制 |
| [调度器](03-modules/scheduler.md) | APScheduler 配置、定时任务注册、每日自动分析与数据刷新调度 |
| [AI 服务](03-modules/ai-services.md) | Google Generative AI 集成、Prompt 模板管理、AI 叙事报告与图像识别 |
| [推荐服务](03-modules/recommendation-service.md) | 基于分析结果的智能推荐、推荐策略配置、推送机制 |
| [飞书机器人](03-modules/feishu-bot.md) | 飞书 Webhook 集成、每日运营数据推送、消息模板与告警通知 |
| [分析与监控](03-modules/analytics-metrics.md) | 用户行为分析、API 调用统计、系统性能指标采集与上报 |

---

### 04 - API 参考

RESTful API 完整参考文档，包含请求/响应格式、参数说明、错误码及调用示例。

| 文档 | 说明 |
|------|------|
| [API 概览](04-api-reference/README.md) | API 设计规范、Base URL、认证方式、通用响应格式、错误码体系及速率限制 |
| [认证 API](04-api-reference/auth-api.md) | 登录、注册、Token 刷新、密码重置等认证相关接口 |
| [用户 API](04-api-reference/user-api.md) | 用户信息查询与更新、额度查询、使用记录等接口 |
| [股票 API](04-api-reference/stock-api.md) | 股票分析请求、分析结果查询、反向评分查询等接口 |
| [期权 API](04-api-reference/options-api.md) | 期权分析请求、Options Chain 查询、策略推荐等接口 |
| [支付 API](04-api-reference/payment-api.md) | 订阅创建、Stripe Checkout、Webhook 回调、订阅状态查询等接口 |
| [投资组合 API](04-api-reference/portfolio-api.md) | 持仓管理、组合分析、每日快照等接口 |
| [行业轮动 API](04-api-reference/sector-api.md) | 行业数据查询、轮动分析、行业排名等接口 |
| [任务 API](04-api-reference/task-api.md) | 异步任务提交、状态轮询、结果获取等接口 |
| [叙事 API](04-api-reference/narrative-api.md) | AI 叙事报告生成、报告查询等接口 |
| [统计分析 API](04-api-reference/analytics-api.md) | 用户行为统计、使用量分析等接口 |
| [监控 API](04-api-reference/metrics-api.md) | 系统健康检查、性能指标、运行状态等接口 |
| [反馈 API](04-api-reference/feedback-api.md) | 用户反馈提交与查询等接口 |

---

### 05 - 业务流程

核心业务场景的端到端流程描述，包含时序图、状态变迁及异常处理路径。

| 文档 | 说明 |
|------|------|
| [用户注册与认证流程](05-business-flows/user-registration-flow.md) | 注册 -> 邮箱验证 -> 登录 -> Token 管理的完整生命周期 |
| [股票分析流程](05-business-flows/stock-analysis-flow.md) | 用户请求 -> 额度检查 -> 数据获取 -> 算法分析 -> 报告生成 -> 缓存的完整链路 |
| [期权分析流程](05-business-flows/options-analysis-flow.md) | 期权分析请求 -> Chain 获取 -> 策略筛选 -> 评分排序 -> 结果返回的完整链路 |
| [支付与订阅流程](05-business-flows/payment-subscription-flow.md) | 计划选择 -> Stripe Checkout -> Webhook 确认 -> 额度发放 -> 订阅续期的完整链路 |
| [额度消费流程](05-business-flows/credit-quota-flow.md) | 额度检查 -> 预扣 -> 分析执行 -> 确认扣除/回退的事务流程 |
| [投资组合每日流程](05-business-flows/portfolio-daily-flow.md) | 调度触发 -> 持仓刷新 -> 盈亏计算 -> 止盈止损检测 -> 通知推送 |
| [数据获取流程](05-business-flows/data-fetching-flow.md) | 多数据源选择 -> 请求 -> 失败降级 -> 数据标准化 -> 缓存写入的容错流程 |

---

### 06 - 测试规范

测试策略、用例管理及测试环境的配置指南。

| 文档 | 说明 |
|------|------|
| [测试策略](06-testing/testing-strategy.md) | 测试金字塔、单元/集成/端到端测试划分、覆盖率目标及 CI 集成方案 |
| [测试用例清单](06-testing/test-cases.md) | 按模块组织的测试用例矩阵，包含正向/异常/边界场景 |
| [测试环境配置](06-testing/test-environment-setup.md) | pytest 配置、Mock 策略、测试数据库搭建及 Fixtures 使用指南 |

---

### 07 - 附录

补充参考资料，包含第三方 API 文档、配置详情、研究记录及项目变更历史。

| 文档 | 说明 |
|------|------|
| [数据源 API 参考](07-appendix/data-source-api.md) | YFinance, Tiger API, Alpha Vantage, Tushare, DefeatBeta 等数据源的接口规格与限制 |
| [订阅计划配置](07-appendix/subscription-config.md) | Free/Basic/Pro/Premium 各套餐的功能权限、额度配置与 Stripe Price ID 映射 |
| [期权池筛选研究](07-appendix/options-pool-research.md) | 期权筛选策略的研究笔记、回测结果及参数调优记录 |
| [变更日志](07-appendix/changelog.md) | 版本发布记录、重大变更说明及迁移指南 |
| [已知问题](07-appendix/known-issues.md) | 当前已识别但尚未修复的问题清单及临时解决方案 |

---

## 其他参考文档

| 文档 | 说明 |
|------|------|
| [架构分析文档 (Legacy)](ARCHITECTURE.md) | 早期生成的单体架构分析文档，包含完整的架构图和组件详解 |
| [工作进度跟踪](progress.md) | 文档编写、代码审查与测试建设的总体进度追踪 |

---

## 快速开始

1. **新成员入职** -- 建议按顺序阅读: 系统概览 -> 术语表 -> 整体架构 -> 目录结构
2. **功能开发** -- 查阅对应模块文档 + API 参考 + 相关业务流程
3. **Bug 修复** -- 查阅相关模块文档 + 已知问题 + 测试用例清单
4. **运维排查** -- 查阅配置说明 + 监控 API + 数据源 API 参考

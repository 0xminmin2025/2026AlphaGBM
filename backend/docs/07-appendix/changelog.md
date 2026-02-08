# 变更日志

> AlphaGBM Backend 项目变更记录

---

## 2026-02-08

### 文档体系建设 (51 documents)
- 完成全部 51 份技术文档
- 文档结构覆盖 7 大类：
  - `01-overview/` — 系统概览、功能清单、术语表 (3 docs)
  - `02-architecture/` — 整体架构、目录结构、数据库、配置、设计标准 (5 docs)
  - `03-modules/` — 15 个核心模块详解 (15 docs)
  - `04-api-reference/` — 13 个 REST API 完整规范 (13 docs)
  - `05-business-flows/` — 7 个端到端业务流程 (7 docs)
  - `06-testing/` — 测试策略、用例清单、环境配置 (3 docs)
  - `07-appendix/` — 数据源、订阅配置、研究记录等 (5 docs)

### 代码审查与问题修复
- 系统性代码审查完成，发现 10 个问题
- **4 Critical/High 已修复**:
  - `app/__init__.py`: Admin endpoints 添加 ADMIN_SECRET_KEY 认证
  - `app/scheduler.py:30`: `.seconds` → `.total_seconds()` 缓存计算 bug
  - `app/services/payment_service.py:163`: bare `except:` → `except Exception:`
  - 测试修复: SPRV 阈值调整 + db_session.refresh 脱离会话修复
- **6 Medium/Low 已记录**:
  - auth/decorators 代码重复、token cache 无上限、check_quota 未用缓存、dead code、线程安全

### 测试体系建设
- **384 tests passing**, 0 failures
- 覆盖: 30 unit test files + 9 integration test files + 3 fixture files
- 测试基础设施: SQLite in-memory DB, Supabase/Stripe/AI mock
- 模块覆盖: Models, Auth, Decorators, Payment, TaskQueue, MarketData, Stock/Options engines, All 4 scorers, VRP, EV, AI, Scheduler, Feishu

---

## 2026-02-04

### 期权池扩展研究
- 完成港股期权、A股ETF期权、商品期权可行性研究
- 制定三阶段实施计划

---

## 2026-01-28

### 数据源文档
- 编写完整数据源与 API 参考文档
- 覆盖 50 个数据需求点、13 个章节

---

## 2026-01-25

### 订阅系统
- 编写订阅系统配置指南
- 包含 Stripe 配置、定价方案、Webhook 设置

---

*本文件在每次重要变更时更新*

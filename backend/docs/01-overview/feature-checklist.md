# AlphaGBM 功能清单 (Feature Checklist)

> 最后更新: 2026-02-27
>
> 本文档列出 AlphaGBM 股票/期权分析平台后端的全部功能模块、API 端点及核心服务引用。

---

## 1. 用户认证 (Authentication)

| # | 功能名称 | 功能描述 | 入口端点 | 核心服务类/方法 | 当前状态 |
|---|---------|---------|----------|----------------|---------|
| 1.1 | 用户注册 | 通过 Supabase Auth 创建新用户账号 | `POST /api/auth/signup` | `auth_bp` / Supabase Auth SDK | ✅ 已实现 |
| 1.2 | 用户登录 | 通过邮箱密码获取 JWT Token | `POST /api/auth/login` | `auth_bp` / Supabase Auth SDK | ✅ 已实现 |
| 1.3 | Token 刷新 | 刷新过期的 JWT Access Token | `POST /api/auth/refresh` | `auth_bp` / Supabase Auth SDK | ✅ 已实现 |
| 1.4 | 获取当前用户 | 返回当前登录用户的基本信息 | `GET /api/user/me` | `user_bp` / `get_current_user_info()` | ✅ 已实现 |
| 1.5 | 获取用户档案 | 返回用户的详细 Profile 信息 | `GET /api/user/profile` | `user_bp.get_profile()` / `require_auth` decorator | ✅ 已实现 |

---

## 2. 股票分析 (Stock Analysis)

| # | 功能名称 | 功能描述 | 入口端点 | 核心服务类/方法 | 当前状态 |
|---|---------|---------|----------|----------------|---------|
| 2.1 | 搜索股票 | 通过 Yahoo Finance 模糊搜索股票，支持 US/HK/CN 多市场格式 | `GET /api/stock/search?q=QUERY&limit=8` | `stock_bp.search_stocks()` / `TTLCache`, `_normalize_search_queries()` | ✅ 已实现 |
| 2.2 | 同步分析 | 提交股票分析请求，自动使用异步任务队列+每日缓存 | `POST /api/stock/analyze` | `stock_bp.analyze_stock()` / `get_stock_analysis_data()`, `analysis_engine`, `ev_model`, `ai_service` | ✅ 已实现 |
| 2.3 | 异步分析 | 创建异步股票分析任务，支持缓存命中/等待/全量三种模式 | `POST /api/stock/analyze-async` | `stock_bp.analyze_stock_async()` / `TaskQueue.create_analysis_task()` | ✅ 已实现 |
| 2.4 | 历史查询 | 分页查询用户的股票分析历史记录 | `GET /api/stock/history` | `stock_bp.get_analysis_history()` / `StockAnalysisHistory` model | ✅ 已实现 |
| 2.5 | 分析摘要 | 获取指定股票的分析摘要，首次免费，支持期权页面联动 | `GET /api/stock/summary/<ticker>` | `stock_bp.get_stock_summary()` / `get_stock_analysis_data()` | ✅ 已实现 |

---

## 3. 期权分析 (Options Analysis)

| # | 功能名称 | 功能描述 | 入口端点 | 核心服务类/方法 | 当前状态 |
|---|---------|---------|----------|----------------|---------|
| 3.1 | 到期日查询 | 获取指定股票的期权到期日列表 | `GET /api/options/expirations/<symbol>` | `options_bp.get_expirations()` / `OptionsService.get_expirations()` | ✅ 已实现 |
| 3.2 | 期权链分析 | 获取指定到期日的期权链及评分数据 | `GET /api/options/chain/<symbol>/<expiry_date>` | `options_bp.get_option_chain()` / `OptionsService.get_option_chain()`, `OptionScorer` | ✅ 已实现 |
| 3.3 | 增强分析 | 获取单个期权合约的 VRP/风险增强分析 | `GET\|POST /api/options/enhanced-analysis/<symbol>/<option_identifier>` | `options_bp.get_enhanced_analysis()` / `OptionsService.get_enhanced_analysis()`, `VRPCalculator`, `RiskAdjuster` | ✅ 已实现 |
| 3.4 | 图像识别 | 通过 Gemini Vision API 识别期权截图并提取参数 | `POST /api/options/recognize-image` | `options_bp.recognize_option_image()` / `ImageRecognitionService.recognize_option_from_image()` | ✅ 已实现 |
| 3.5 | 反向评分 | 根据用户输入的期权参数（symbol/strike/expiry 等）反向计算评分 | `POST /api/options/reverse-score` | `options_bp.reverse_score_option()` / `OptionsService.reverse_score_option()` | ✅ 已实现 |
| 3.6 | 批量分析 | 批量创建多 symbol x 多 expiry 的期权链分析异步任务 | `POST /api/options/chain/batch` | `options_bp.get_option_chain_batch()` / `TaskQueue.create_analysis_task()` | ✅ 已实现 |
| 3.7 | 商品期货合约查询 | 查询商品期货期权可用合约列表及主力合约 (au/ag/cu/al/m) | `GET /api/options/commodity/contracts/<product>` | `options_bp` / `AkShareCommodityAdapter` | ✅ 已实现 |
| 3.8 | 多市场白名单校验 | HK/CN/COMMODITY 市场标的白名单校验，不在名单内返回 400 | 所有期权链端点 | `_check_option_whitelist()` / `OptionMarketConfig` | ✅ 已实现 |
| 3.9 | 交割风险评估 | 商品期权交割月风控 (T-30 红区/T-60 警告区) | 商品期权评分流程内部 | `DeliveryRiskCalculator.assess()` | ✅ 已实现 |

---

## 4. 每日推荐 (Daily Recommendations)

| # | 功能名称 | 功能描述 | 入口端点 | 核心服务类/方法 | 当前状态 |
|---|---------|---------|----------|----------------|---------|
| 4.1 | 推荐列表 + 市场摘要 | 获取每日热门期权推荐及市场概况（US/HK/CN/Commodity 四市场），支持缓存与强制刷新 | `GET /api/options/recommendations?count=5&refresh=false` | `options_bp.get_recommendations()` / `RecommendationService.get_daily_recommendations()` | ✅ 已实现 |

---

## 5. 支付系统 (Payment System)

| # | 功能名称 | 功能描述 | 入口端点 | 核心服务类/方法 | 当前状态 |
|---|---------|---------|----------|----------------|---------|
| 5.1 | 创建 Checkout Session | 创建 Stripe Checkout 支付会话 | `POST /api/payment/create-checkout-session` | `payment_bp.create_checkout_session()` / `PaymentService.create_checkout_session()` | ✅ 已实现 |
| 5.2 | Stripe Webhook | 处理 Stripe 回调事件（支付完成、续费、取消等） | `POST /api/payment/webhook` | `payment_bp.webhook()` / `PaymentService.handle_checkout_completed()`, `handle_subscription_renewal()` | ✅ 已实现 |
| 5.3 | 额度查询 | 获取用户总额度、订阅信息及每日免费额度使用情况 | `GET /api/payment/credits` | `payment_bp.get_credits()` / `PaymentService.get_total_credits()`, `get_user_subscription_info()` | ✅ 已实现 |
| 5.4 | 额度预检 | 检查额度是否足够（不扣减），用于前端确认弹窗 | `POST /api/payment/check-quota` | `payment_bp.check_quota()` / `PaymentService.get_daily_free_quota_info()` | ✅ 已实现 |
| 5.5 | 升级订阅 | 升级用户的订阅计划（Plus/Pro） | `POST /api/payment/upgrade` | `payment_bp.upgrade_subscription()` / `PaymentService.upgrade_subscription()` | ✅ 已实现 |
| 5.6 | 取消订阅 | 取消当前订阅（周期结束后生效） | `POST /api/payment/cancel` | `payment_bp.cancel_subscription()` / `PaymentService.cancel_subscription()` | ✅ 已实现 |
| 5.7 | 客户门户 | 创建 Stripe Billing Portal 会话供用户自助管理 | `POST /api/payment/customer-portal` | `payment_bp.create_customer_portal_session()` / `stripe.billing_portal.Session.create()` | ✅ 已实现 |
| 5.8 | 定价信息 | 返回平台定价套餐详情（Free/Plus/Pro/Enterprise） | `GET /api/payment/pricing` | `payment_bp.get_pricing()` | ✅ 已实现 |
| 5.9 | 交易历史 | 分页查询用户的付费交易记录 | `GET /api/payment/transactions` | `payment_bp.get_transactions()` / `Transaction` model | ✅ 已实现 |
| 5.10 | 使用历史 | 分页查询用户的额度使用日志 | `GET /api/payment/usage-history` | `payment_bp.get_usage_history()` / `UsageLog` model | ✅ 已实现 |
| 5.11 | 升级选项 | 获取当前用户可用的升级选项列表 | `GET /api/payment/upgrade-options` | `payment_bp.get_upgrade_options()` / `PaymentService.get_upgrade_options()` | ✅ 已实现 |

---

## 6. 投资组合 (Portfolio)

| # | 功能名称 | 功能描述 | 入口端点 | 核心服务类/方法 | 当前状态 |
|---|---------|---------|----------|----------------|---------|
| 6.1 | 持仓列表 | 获取按风格分组的投资组合持仓及实时市值/收益 | `GET /api/portfolio/holdings` | `portfolio_bp.get_portfolio_holdings()` / `PortfolioHolding` model, `DataProvider` | ✅ 已实现 |
| 6.2 | 每日 P&L | 获取最新的组合级每日盈亏统计 | `GET /api/portfolio/daily-stats` | `portfolio_bp.get_daily_portfolio_stats()` / `DailyProfitLoss` model | ✅ 已实现 |
| 6.3 | P&L 历史曲线 | 获取指定天数的盈亏历史数据（按风格拆分） | `GET /api/portfolio/profit-loss/history?days=30` | `portfolio_bp.get_profit_loss_history()` / `DailyProfitLoss`, `StyleProfit` models | ✅ 已实现 |
| 6.4 | 再平衡历史 | 获取投资组合的再平衡操作记录 | `GET /api/portfolio/rebalance-history` | `portfolio_bp.get_rebalance_history()` / `PortfolioRebalance` model | ✅ 已实现 |

---

## 7. 行业分析 (Sector Analysis)

| # | 功能名称 | 功能描述 | 入口端点 | 核心服务类/方法 | 当前状态 |
|---|---------|---------|----------|----------------|---------|
| 7.1 | 轮动概览 | 获取全市场板块轮动概览及板块强度排名 | `GET /api/sector/rotation/overview?market=US` | `sector_bp.get_rotation_overview()` / `SectorRotationService.get_rotation_overview()` | ✅ 已实现 |
| 7.2 | 行业详情 | 获取单一板块的详细分析数据 | `GET /api/sector/rotation/sector/<sector_name>` | `sector_bp.get_sector_detail()` / `SectorRotationService.get_sector_detail()` | ✅ 已实现 |
| 7.3 | 热力图 | 获取板块热力图数据 | `GET /api/sector/heatmap?market=US` | `sector_bp.get_heatmap()` / `SectorRotationService.get_heatmap_data()` | ✅ 已实现 |
| 7.4 | 资金结构分析 | 分析个股的资金集中度和情绪传导阶段 | `GET /api/sector/capital/analysis/<ticker>` | `sector_bp.analyze_capital_structure()` / `CapitalStructureService.analyze_stock_capital()` | ✅ 已实现 |
| 7.5 | 强势板块排行 | 获取当前最强板块 top-N 列表 | `GET /api/sector/top-sectors?market=US&limit=5` | `sector_bp.get_top_sectors()` / `SectorRotationService.get_top_sectors()` | ✅ 已实现 |
| 7.6 | 弱势板块排行 | 获取当前最弱板块 top-N 列表 | `GET /api/sector/bottom-sectors?market=US&limit=5` | `sector_bp.get_bottom_sectors()` / `SectorRotationService.get_bottom_sectors()` | ✅ 已实现 |
| 7.7 | 个股板块关联 | 分析个股与板块的同步度/领先性 | `GET /api/sector/stock/<ticker>/sector-analysis` | `sector_bp.analyze_stock_sector()` / `SectorRotationService.analyze_stock_sector()` | ✅ 已实现 |
| 7.8 | 资金因子 | 获取指定股票的资金因子值（快速接口） | `GET /api/sector/capital/factor/<ticker>` | `sector_bp.get_capital_factor()` / `CapitalStructureService.get_capital_factor()` | ✅ 已实现 |
| 7.9 | 情绪传导阶段 | 获取指定股票的情绪传导阶段 | `GET /api/sector/capital/stage/<ticker>` | `sector_bp.get_propagation_stage()` / `CapitalStructureService.get_propagation_stage()` | ✅ 已实现 |
| 7.10 | 资金集中度信号 | 获取指定股票的资金集中度信号列表 | `GET /api/sector/capital/signals/<ticker>` | `sector_bp.get_capital_signals()` / `CapitalStructureService.get_concentration_signals()` | ✅ 已实现 |

---

## 8. AI 叙事雷达 (Narrative Radar)

| # | 功能名称 | 功能描述 | 入口端点 | 核心服务类/方法 | 当前状态 |
|---|---------|---------|----------|----------------|---------|
| 8.1 | 预设叙事列表 | 获取所有预设叙事（人物/机构/主题），按类型分组返回 | `GET /api/narrative/presets` | `narrative_bp.get_presets()` / `get_preset_narratives()` | ✅ 已实现 |
| 8.2 | 自定义概念分析 | 通过 Gemini AI 分析用户输入的概念或预设叙事，返回关联股票及期权策略 | `POST /api/narrative/analyze` | `narrative_bp.analyze()` / `analyze_narrative()` | ✅ 已实现 |

---

## 9. 异步任务 (Async Task Queue)

| # | 功能名称 | 功能描述 | 入口端点 | 核心服务类/方法 | 当前状态 |
|---|---------|---------|----------|----------------|---------|
| 9.1 | 创建任务 | 创建新的异步分析任务（股票/期权/增强期权） | `POST /api/tasks/create` | `tasks_bp.create_task()` / `TaskQueue.create_analysis_task()` | ✅ 已实现 |
| 9.2 | 任务状态 | 查询任务进度、当前步骤、完成百分比 | `GET /api/tasks/<task_id>/status` | `tasks_bp.get_task_status_endpoint()` / `get_task_status()` | ✅ 已实现 |
| 9.3 | 任务结果 | 获取已完成任务的分析结果数据 | `GET /api/tasks/<task_id>/result` | `tasks_bp.get_task_result()` / `get_task_status()` | ✅ 已实现 |
| 9.4 | 用户任务列表 | 获取当前用户的任务列表，支持状态过滤 | `GET /api/tasks/user?limit=10&status=completed` | `tasks_bp.get_user_tasks_endpoint()` / `get_user_tasks()` | ✅ 已实现 |
| 9.5 | 任务统计 | 获取用户的任务统计（成功率、各状态数量） | `GET /api/tasks/stats` | `tasks_bp.get_task_stats()` / `get_user_tasks()` | ✅ 已实现 |

---

## 10. 分析统计 (Analytics)

| # | 功能名称 | 功能描述 | 入口端点 | 核心服务类/方法 | 当前状态 |
|---|---------|---------|----------|----------------|---------|
| 10.1 | 事件追踪 | 批量接收前端 Analytics 事件（page_view, click 等） | `POST /api/analytics/events` | `analytics_bp.track_events()` / `AnalyticsEvent` model | ✅ 已实现 |
| 10.2 | 统计数据 | 获取基础分析统计（事件计数、独立会话、独立用户） | `GET /api/analytics/stats?days=7` | `analytics_bp.get_stats()` / `AnalyticsEvent` aggregate queries | ✅ 已实现 |

---

## 11. 系统监控 (System Metrics)

| # | 功能名称 | 功能描述 | 入口端点 | 核心服务类/方法 | 当前状态 |
|---|---------|---------|----------|----------------|---------|
| 11.1 | 综合指标 | 获取全量 Market Data 操作指标（调用量、缓存命中率、失败率等） | `GET /api/metrics/` | `metrics_bp.get_all_metrics()` / `MarketDataService.get_stats()` | ✅ 已实现 |
| 11.2 | 供应商状态 | 获取所有已注册数据供应商的健康状态及能力 | `GET /api/metrics/providers` | `metrics_bp.get_provider_status()` / `MarketDataService.get_provider_status()` | ✅ 已实现 |
| 11.3 | 供应商健康 | 获取特定数据供应商的详细健康信息（成功率、延迟、近期错误） | `GET /api/metrics/providers/<provider_name>` | `metrics_bp.get_provider_health()` / `MarketDataService.get_provider_health()` | ✅ 已实现 |
| 11.4 | 延迟分位 | 获取延迟分位数（p50/p90/p95/p99），支持按供应商和数据类型过滤 | `GET /api/metrics/latency` | `metrics_bp.get_latency_percentiles()` / `MarketDataService.get_latency_percentiles()` | ✅ 已实现 |
| 11.5 | 最近请求 | 获取最近调用记录，支持按供应商/股票/错误过滤 | `GET /api/metrics/recent` | `metrics_bp.get_recent_calls()` / `MarketDataService.get_recent_calls()` | ✅ 已实现 |
| 11.6 | 仪表板 | 渲染可视化 HTML Metrics Dashboard 页面 | `GET /api/metrics/dashboard` | `metrics_bp.dashboard()` / `render_template_string(DASHBOARD_HTML)` | ✅ 已实现 |

---

## 12. 用户反馈 (User Feedback)

| # | 功能名称 | 功能描述 | 入口端点 | 核心服务类/方法 | 当前状态 |
|---|---------|---------|----------|----------------|---------|
| 12.1 | 提交反馈 | 用户提交 Bug/建议/问题反馈 | `POST /api/feedback` | `feedback_bp.submit_feedback()` / `Feedback` model | ✅ 已实现 |

---

## 13. 定时任务 (Scheduled Jobs)

> 以下为 APScheduler 后台定时任务，非 HTTP API 端点。

| # | 功能名称 | 功能描述 | 触发时间 | 核心服务类/方法 | 当前状态 |
|---|---------|---------|----------|----------------|---------|
| 13.1 | 每日 P&L 计算 | 遍历所有持仓，获取实时价格并计算当日盈亏，按风格写入 DB | 每日 18:12 (服务器本地时间) | `scheduler.calculate_daily_profit_loss()` / `DataProvider`, `DailyProfitLoss`, `StyleProfit` models | ✅ 已实现 |
| 13.2 | 飞书日报推送 | 查询当日运营数据并通过飞书 Webhook 推送到运营群 | 每日 20:00 (服务器本地时间) | `scheduler._send_feishu_report()` / `feishu_bot.send_daily_report()`, `get_daily_stats()` | ✅ 已实现 |

---

## 附录: 核心服务模块索引

| 服务文件 | 核心类/函数 | 职责 |
|---------|-----------|------|
| `app/services/analysis_engine.py` | `get_market_data()`, `analyze_risk_and_position()`, `calculate_target_price()`, `calculate_atr_stop_loss()` | 股票核心分析引擎 |
| `app/services/ai_service.py` | `get_gemini_analysis()`, `get_fallback_analysis()` | Gemini AI 报告生成 |
| `app/services/ev_model.py` | `calculate_ev_model()`, `calculate_ev_model_extended()` | EV 期望值模型 |
| `app/services/options_service.py` | `OptionsService` (class) | 期权数据获取与分析 |
| `app/services/option_scorer.py` | `OptionScorer` (class) | 期权评分（Buy/Sell Call/Put） |
| `app/services/payment_service.py` | `PaymentService` (class) | Stripe 支付与额度管理 |
| `app/services/recommendation_service.py` | `RecommendationService` (class) | 每日期权推荐 |
| `app/services/narrative_service.py` | `analyze_narrative()`, `get_preset_narratives()` | AI 叙事雷达 |
| `app/services/task_queue.py` | `TaskQueue` (class), `create_analysis_task()`, `get_task_status()` | 异步任务队列 |
| `app/services/image_recognition_service.py` | `ImageRecognitionService` (class) | 期权截图识别 (Gemini Vision) |
| `app/services/sector_rotation_service.py` | `SectorRotationService` (class) | 板块轮动分析 |
| `app/services/capital_structure_service.py` | `CapitalStructureService` (class) | 资金结构分析 |
| `app/services/market_data/service.py` | `MarketDataService` (class) | 多源市场数据统一接入层 |
| `app/services/data_provider.py` | `DataProvider` (class) | 统一数据访问代理（含 metrics） |
| `app/services/feishu_bot.py` | `send_daily_report()`, `get_daily_stats()` | 飞书机器人日报推送 |
| `app/scheduler.py` | `init_scheduler()`, `calculate_daily_profit_loss()` | APScheduler 定时任务调度 |

---

## 统计

- **功能模块总数**: 13
- **API 端点总数**: 49
- **已实现**: 49 / 49 (100%)

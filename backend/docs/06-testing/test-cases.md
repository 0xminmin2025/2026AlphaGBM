# 测试用例清单

> 按模块组织的完整测试用例 Checklist

---

## 1. test_models.py — 数据模型测试

### 1.1 User Model

| # | 测试用例 | 类型 | 说明 |
|---|---------|------|------|
| M01 | `test_model_user_create_with_required_fields` | unit | 创建 User 只需 id, email |
| M02 | `test_model_user_display_name_default_none` | unit | display_name 默认 None |
| M03 | `test_model_user_created_at_auto_set` | unit | created_at 自动填充当前时间 |

### 1.2 Subscription Model

| # | 测试用例 | 类型 | 说明 |
|---|---------|------|------|
| M04 | `test_model_subscription_create_valid` | unit | 创建 Subscription 包含所有字段 |
| M05 | `test_model_subscription_user_relationship` | unit | subscription.user 关联正确 |
| M06 | `test_model_subscription_status_default` | unit | status 默认 'active' |
| M07 | `test_model_subscription_cancel_at_period_end_default_false` | unit | cancel_at_period_end 默认 False |

### 1.3 CreditLedger Model

| # | 测试用例 | 类型 | 说明 |
|---|---------|------|------|
| M08 | `test_model_credit_ledger_create_valid` | unit | 创建 CreditLedger 记录 |
| M09 | `test_model_credit_ledger_expires_at_nullable` | unit | expires_at 可为 None（订阅额度） |
| M10 | `test_model_credit_ledger_source_types` | unit | source 支持 'subscription' / 'topup' |

### 1.4 DailyQueryCount Model

| # | 测试用例 | 类型 | 说明 |
|---|---------|------|------|
| M11 | `test_model_daily_query_count_create` | unit | 创建每日计数记录 |
| M12 | `test_model_daily_query_count_default_zero` | unit | query_count 默认 0 |
| M13 | `test_model_daily_query_unique_user_date` | unit | 同用户同日期唯一约束 |

### 1.5 TaskQueue Model

| # | 测试用例 | 类型 | 说明 |
|---|---------|------|------|
| M14 | `test_model_task_queue_create_pending` | unit | 新任务 status='pending' |
| M15 | `test_model_task_queue_result_nullable` | unit | result 字段可为 None |

### 1.6 其他 Model

| # | 测试用例 | 类型 | 说明 |
|---|---------|------|------|
| M16 | `test_model_stock_analysis_record_create` | unit | 股票分析记录创建 |
| M17 | `test_model_option_analysis_record_create` | unit | 期权分析记录创建 |
| M18 | `test_model_recommendation_record_create` | unit | 推荐记录创建 |

---

## 2. test_auth.py — 认证模块测试

| # | 测试用例 | 类型 | 说明 |
|---|---------|------|------|
| A01 | `test_auth_valid_token_returns_user_object` | unit | 有效 Bearer token 解析出用户信息 |
| A02 | `test_auth_invalid_token_returns_401` | unit | 无效 token 返回 401 Unauthorized |
| A03 | `test_auth_expired_token_returns_401` | unit | 过期 token 返回 401 |
| A04 | `test_auth_missing_header_returns_401` | unit | 无 Authorization header 返回 401 |
| A05 | `test_auth_malformed_bearer_returns_401` | unit | 格式错误（无 Bearer 前缀）返回 401 |
| A06 | `test_auth_cache_hit_skips_supabase_call` | unit | 缓存命中时不调用 Supabase |
| A07 | `test_auth_cache_miss_calls_supabase` | unit | 缓存未命中时调用 Supabase |
| A08 | `test_auth_user_auto_create_on_first_login` | unit | 首次登录自动创建 User 记录 |
| A09 | `test_auth_existing_user_not_duplicated` | unit | 已存在用户不重复创建 |
| A10 | `test_auth_supabase_error_retry_3_times` | unit | Supabase 异常时重试 3 次 |
| A11 | `test_auth_supabase_timeout_returns_503` | unit | Supabase 超时返回 503 |
| A12 | `test_auth_cache_expiry_refreshes_token` | unit | 缓存过期后重新验证 |

---

## 3. test_decorators.py — 装饰器测试

### 3.1 check_quota Decorator

| # | 测试用例 | 类型 | 说明 |
|---|---------|------|------|
| D01 | `test_decorator_check_quota_free_user_within_limit_passes` | unit | 免费用户未达上限，放行 |
| D02 | `test_decorator_check_quota_free_user_exceeded_returns_429` | unit | 免费用户超限，返回 429 |
| D03 | `test_decorator_check_quota_paid_user_has_credits_passes` | unit | 付费用户有额度，放行 |
| D04 | `test_decorator_check_quota_paid_user_no_credits_returns_402` | unit | 付费用户额度耗尽，返回 402 |
| D05 | `test_decorator_check_quota_deducts_credit_after_success` | unit | 请求成功后扣减 1 次额度 |
| D06 | `test_decorator_check_quota_no_deduct_on_failure` | unit | 请求失败不扣减额度 |
| D07 | `test_decorator_check_quota_expired_credits_skipped` | unit | 过期额度不计入可用额度 |

### 3.2 db_retry Decorator

| # | 测试用例 | 类型 | 说明 |
|---|---------|------|------|
| D08 | `test_decorator_db_retry_success_on_first_attempt` | unit | 首次成功不重试 |
| D09 | `test_decorator_db_retry_success_on_second_attempt` | unit | 首次失败，第二次成功 |
| D10 | `test_decorator_db_retry_exhausted_raises_exception` | unit | 重试耗尽后抛出异常 |
| D11 | `test_decorator_db_retry_only_retries_db_errors` | unit | 仅对数据库错误重试 |

---

## 4. test_payment_service.py — 支付服务测试

### 4.1 Checkout Session

| # | 测试用例 | 类型 | 说明 |
|---|---------|------|------|
| P01 | `test_payment_create_checkout_plus_monthly_returns_url` | unit | Plus 月付创建 checkout session |
| P02 | `test_payment_create_checkout_pro_yearly_returns_url` | unit | Pro 年付创建 checkout session |
| P03 | `test_payment_create_checkout_topup_returns_url` | unit | 加油包创建 checkout session |
| P04 | `test_payment_create_checkout_invalid_plan_returns_400` | unit | 无效计划返回 400 |
| P05 | `test_payment_create_checkout_already_subscribed_returns_409` | unit | 已订阅用户重复订阅返回 409 |

### 4.2 Credit Deduction (FIFO)

| # | 测试用例 | 类型 | 说明 |
|---|---------|------|------|
| P06 | `test_payment_deduct_credit_fifo_oldest_first` | unit | FIFO 先扣最早的额度 |
| P07 | `test_payment_deduct_credit_skip_expired` | unit | 跳过已过期额度 |
| P08 | `test_payment_deduct_credit_insufficient_raises_error` | unit | 额度不足抛出异常 |
| P09 | `test_payment_deduct_credit_cross_ledger_entries` | unit | 跨多条 ledger 记录扣减 |

### 4.3 Webhook — Idempotency

| # | 测试用例 | 类型 | 说明 |
|---|---------|------|------|
| P10 | `test_payment_webhook_checkout_completed_creates_subscription` | unit | checkout.session.completed 创建订阅 |
| P11 | `test_payment_webhook_invoice_succeeded_grants_credits` | unit | invoice.payment_succeeded 发放额度 |
| P12 | `test_payment_webhook_duplicate_event_idempotent` | unit | 重复 event 不重复发放额度 |
| P13 | `test_payment_webhook_invalid_signature_returns_400` | unit | 签名验证失败返回 400 |

### 4.4 Upgrade

| # | 测试用例 | 类型 | 说明 |
|---|---------|------|------|
| P14 | `test_payment_upgrade_plus_to_pro_calls_stripe_modify` | unit | Plus→Pro 调用 Stripe modify |
| P15 | `test_payment_upgrade_monthly_to_yearly_proration` | unit | 月付→年付 proration 正确 |
| P16 | `test_payment_upgrade_no_subscription_returns_404` | unit | 无订阅用户升级返回 404 |
| P17 | `test_payment_upgrade_same_plan_returns_400` | unit | 相同计划升级返回 400 |

### 4.5 Cancel

| # | 测试用例 | 类型 | 说明 |
|---|---------|------|------|
| P18 | `test_payment_cancel_sets_cancel_at_period_end` | unit | 取消设置 period_end 标志 |
| P19 | `test_payment_cancel_no_subscription_returns_404` | unit | 无订阅取消返回 404 |

### 4.6 Credit Query

| # | 测试用例 | 类型 | 说明 |
|---|---------|------|------|
| P20 | `test_payment_get_credits_returns_total_available` | unit | 返回可用额度总数 |
| P21 | `test_payment_get_credits_excludes_expired` | unit | 排除过期额度 |

---

## 5. test_option_scorer.py — 期权评分测试

### 5.1 SPRV (Sell Put Risk-Value)

| # | 测试用例 | 类型 | 说明 |
|---|---------|------|------|
| O01 | `test_scorer_sprv_high_iv_high_score` | unit | 高 IV 下 Sell Put 得分高 |
| O02 | `test_scorer_sprv_low_iv_low_score` | unit | 低 IV 下 Sell Put 得分低 |
| O03 | `test_scorer_sprv_deep_otm_lower_risk` | unit | 深度虚值降低风险评分 |
| O04 | `test_scorer_sprv_near_earnings_penalized` | unit | 临近财报日惩罚评分 |

### 5.2 SCRV (Sell Call Risk-Value)

| # | 测试用例 | 类型 | 说明 |
|---|---------|------|------|
| O05 | `test_scorer_scrv_covered_call_scenario` | unit | 备兑场景评分 |
| O06 | `test_scorer_scrv_naked_call_high_risk` | unit | 裸卖 Call 高风险惩罚 |

### 5.3 BCRV (Buy Call Risk-Value)

| # | 测试用例 | 类型 | 说明 |
|---|---------|------|------|
| O07 | `test_scorer_bcrv_bullish_trend_high_score` | unit | 看涨趋势下 Buy Call 高分 |
| O08 | `test_scorer_bcrv_bearish_trend_low_score` | unit | 看跌趋势下 Buy Call 低分 |

### 5.4 BPRV (Buy Put Risk-Value)

| # | 测试用例 | 类型 | 说明 |
|---|---------|------|------|
| O09 | `test_scorer_bprv_bearish_trend_high_score` | unit | 看跌趋势下 Buy Put 高分 |
| O10 | `test_scorer_bprv_bullish_trend_low_score` | unit | 看涨趋势下 Buy Put 低分 |

### 5.5 Liquidity Scoring

| # | 测试用例 | 类型 | 说明 |
|---|---------|------|------|
| O11 | `test_scorer_liquidity_high_volume_high_score` | unit | 高成交量高流动性分 |
| O12 | `test_scorer_liquidity_wide_spread_penalized` | unit | 宽 bid-ask spread 惩罚 |
| O13 | `test_scorer_liquidity_zero_oi_minimum_score` | unit | 零 OI 给最低分 |

### 5.6 Assignment Probability

| # | 测试用例 | 类型 | 说明 |
|---|---------|------|------|
| O14 | `test_scorer_assignment_itm_high_probability` | unit | ITM 高指派概率 |
| O15 | `test_scorer_assignment_deep_otm_low_probability` | unit | 深度 OTM 低指派概率 |

### 5.7 Expiry Penalty

| # | 测试用例 | 类型 | 说明 |
|---|---------|------|------|
| O16 | `test_scorer_expiry_less_than_7_days_heavy_penalty` | unit | < 7 天重度惩罚 |
| O17 | `test_scorer_expiry_30_to_60_days_optimal` | unit | 30-60 天最佳区间 |
| O18 | `test_scorer_expiry_over_180_days_slight_penalty` | unit | > 180 天轻度惩罚 |

---

## 6. test_ev_model.py — 期望值模型测试

### 6.1 Multi-Horizon EV

| # | 测试用例 | 类型 | 说明 |
|---|---------|------|------|
| E01 | `test_ev_model_single_horizon_calculation` | unit | 单个时间窗口 EV 计算 |
| E02 | `test_ev_model_multi_horizon_aggregation` | unit | 多时间窗口加权聚合 |
| E03 | `test_ev_model_positive_ev_bullish_scenario` | unit | 看涨场景 EV 为正 |
| E04 | `test_ev_model_negative_ev_bearish_scenario` | unit | 看跌场景 EV 为负 |
| E05 | `test_ev_model_zero_ev_neutral_scenario` | unit | 中性场景 EV 接近零 |

### 6.2 Recommendations

| # | 测试用例 | 类型 | 说明 |
|---|---------|------|------|
| E06 | `test_ev_model_recommend_buy_on_high_positive_ev` | unit | 高正 EV 推荐买入 |
| E07 | `test_ev_model_recommend_sell_on_high_negative_ev` | unit | 高负 EV 推荐卖出 |
| E08 | `test_ev_model_recommend_hold_on_neutral_ev` | unit | 中性 EV 推荐持有 |
| E09 | `test_ev_model_risk_adjusted_ev_considers_volatility` | unit | 风险调整考虑波动率 |
| E10 | `test_ev_model_confidence_interval_bounds` | unit | 置信区间边界正确 |

---

## 7. test_task_queue.py — 任务队列测试

| # | 测试用例 | 类型 | 说明 |
|---|---------|------|------|
| T01 | `test_task_queue_create_task_returns_task_id` | unit | 创建任务返回唯一 task_id |
| T02 | `test_task_queue_create_task_status_pending` | unit | 新任务状态为 pending |
| T03 | `test_task_queue_process_task_status_processing` | unit | 处理中状态变更为 processing |
| T04 | `test_task_queue_complete_task_stores_result` | unit | 完成后存储结果 |
| T05 | `test_task_queue_get_status_returns_correct_state` | unit | 查询状态返回正确值 |
| T06 | `test_task_queue_timeout_marks_failed` | unit | 超时任务标记为 failed |
| T07 | `test_task_queue_duplicate_process_idempotent` | unit | 重复处理幂等 |
| T08 | `test_task_queue_nonexistent_task_returns_404` | unit | 不存在的 task_id 返回 404 |

---

## 8. test_recommendation_service.py — 推荐服务测试

| # | 测试用例 | 类型 | 说明 |
|---|---------|------|------|
| R01 | `test_recommendation_generate_returns_top_n` | unit | 生成前 N 个推荐 |
| R02 | `test_recommendation_quality_scoring_weights` | unit | 质量评分权重正确 |
| R03 | `test_recommendation_diversity_different_sectors` | unit | 推荐覆盖不同行业 |
| R04 | `test_recommendation_filter_low_liquidity` | unit | 过滤低流动性标的 |
| R05 | `test_recommendation_cache_hit_returns_cached` | unit | 缓存命中返回缓存结果 |
| R06 | `test_recommendation_empty_pool_returns_empty` | unit | 空候选池返回空列表 |
| R07 | `test_recommendation_respects_market_filter` | unit | 遵守市场过滤条件 |

---

## 9. test_ai_service.py — AI 服务测试

| # | 测试用例 | 类型 | 说明 |
|---|---------|------|------|
| AI01 | `test_ai_service_generate_report_returns_markdown` | unit | 生成报告为 Markdown 格式 |
| AI02 | `test_ai_service_generate_report_includes_sections` | unit | 报告包含必需章节 |
| AI03 | `test_ai_service_api_error_returns_fallback` | unit | API 错误时返回 fallback 报告 |
| AI04 | `test_ai_service_timeout_returns_fallback` | unit | 超时返回 fallback 报告 |
| AI05 | `test_ai_service_rate_limit_retries` | unit | 速率限制时重试 |
| AI06 | `test_ai_service_empty_data_graceful_handling` | unit | 空数据输入优雅处理 |

---

## 10. test_narrative_service.py — 叙述服务测试

| # | 测试用例 | 类型 | 说明 |
|---|---------|------|------|
| N01 | `test_narrative_presets_all_registered` | unit | 所有预设模板已注册 |
| N02 | `test_narrative_analyze_bullish_generates_text` | unit | 看涨场景生成叙述文本 |
| N03 | `test_narrative_analyze_bearish_generates_text` | unit | 看跌场景生成叙述文本 |
| N04 | `test_narrative_analyze_neutral_generates_text` | unit | 中性场景生成叙述文本 |
| N05 | `test_narrative_fallback_on_missing_data` | unit | 缺失数据时使用 fallback |
| N06 | `test_narrative_custom_preset_applied` | unit | 自定义 preset 正确应用 |

---

## 11. test_stock_engine.py — 股票分析引擎测试

| # | 测试用例 | 类型 | 说明 |
|---|---------|------|------|
| S01 | `test_stock_engine_full_analysis_returns_all_sections` | unit | 完整分析包含所有章节 |
| S02 | `test_stock_engine_valuation_scoring` | unit | 估值评分逻辑正确 |
| S03 | `test_stock_engine_technical_indicators_calculated` | unit | 技术指标（RSI, MACD, Bollinger）计算 |
| S04 | `test_stock_engine_growth_scoring` | unit | 成长性评分 |
| S05 | `test_stock_engine_profitability_scoring` | unit | 盈利能力评分 |
| S06 | `test_stock_engine_risk_scoring` | unit | 风险评分 |
| S07 | `test_stock_engine_market_warnings_included` | unit | 市场预警信息包含 |
| S08 | `test_stock_engine_a_share_lockup_analysis` | unit | A 股限售解禁分析 |
| S09 | `test_stock_engine_missing_data_graceful` | unit | 缺失数据不崩溃 |
| S10 | `test_stock_engine_us_stock_full_pipeline` | unit | 美股完整流水线 |
| S11 | `test_stock_engine_hk_stock_full_pipeline` | unit | 港股完整流水线 |

---

## 12. test_options_engine.py — 期权分析引擎测试

| # | 测试用例 | 类型 | 说明 |
|---|---------|------|------|
| OE01 | `test_options_engine_chain_analysis_returns_scored_options` | unit | 期权链分析返回评分列表 |
| OE02 | `test_options_engine_multi_strategy_all_four_scored` | unit | 四种策略全部评分 |
| OE03 | `test_options_engine_tiger_data_preferred` | unit | 优先使用 Tiger 数据 |
| OE04 | `test_options_engine_fallback_to_yfinance` | unit | Tiger 失败 fallback 到 yfinance |
| OE05 | `test_options_engine_fallback_to_mock` | unit | yfinance 也失败时使用 Mock 数据 |
| OE06 | `test_options_engine_greeks_calculation` | unit | Greeks 计算正确 |
| OE07 | `test_options_engine_vrp_analysis` | unit | VRP（波动率风险溢价）分析 |
| OE08 | `test_options_engine_risk_profile_classification` | unit | 风险画像分类正确 |
| OE09 | `test_options_engine_expiry_filter_applied` | unit | 到期日过滤生效 |
| OE10 | `test_options_engine_empty_chain_returns_empty` | unit | 空期权链返回空结果 |

---

## 13. Integration Tests — 集成测试

### 13.1 test_api_stock.py — 股票 API 集成测试

| # | 测试用例 | 类型 | 说明 |
|---|---------|------|------|
| IS01 | `test_api_stock_analyze_valid_symbol_200` | integration | 有效 symbol 返回 200 |
| IS02 | `test_api_stock_analyze_invalid_symbol_400` | integration | 无效 symbol 返回 400 |
| IS03 | `test_api_stock_analyze_no_auth_401` | integration | 无认证返回 401 |
| IS04 | `test_api_stock_analyze_free_user_within_limit` | integration | 免费用户额度内正常 |
| IS05 | `test_api_stock_analyze_free_user_exceeded_429` | integration | 免费用户超限返回 429 |
| IS06 | `test_api_stock_analyze_paid_user_deducts_credit` | integration | 付费用户扣减额度 |
| IS07 | `test_api_stock_analyze_response_schema` | integration | 响应 JSON schema 验证 |
| IS08 | `test_api_stock_analyze_async_returns_task_id` | integration | 异步模式返回 task_id |

### 13.2 test_api_options.py — 期权 API 集成测试

| # | 测试用例 | 类型 | 说明 |
|---|---------|------|------|
| IO01 | `test_api_options_analyze_valid_symbol_200` | integration | 有效 symbol 返回 200 |
| IO02 | `test_api_options_analyze_with_expiry_filter` | integration | 指定到期日过滤 |
| IO03 | `test_api_options_analyze_no_auth_401` | integration | 无认证返回 401 |
| IO04 | `test_api_options_reverse_score_valid_params` | integration | 反向查分有效参数 |
| IO05 | `test_api_options_reverse_score_missing_params_400` | integration | 缺参数返回 400 |
| IO06 | `test_api_options_image_recognition_valid_image` | integration | 图片识别有效图片 |
| IO07 | `test_api_options_multi_symbol_counts_correctly` | integration | 多 symbol 额度计数正确 |

### 13.3 test_api_payment.py — 支付 API 集成测试

| # | 测试用例 | 类型 | 说明 |
|---|---------|------|------|
| IP01 | `test_api_payment_pricing_returns_all_plans` | integration | 定价接口返回所有计划 |
| IP02 | `test_api_payment_create_checkout_session_flow` | integration | 创建 checkout 完整流程 |
| IP03 | `test_api_payment_webhook_checkout_completed_flow` | integration | webhook checkout 完整流程 |
| IP04 | `test_api_payment_webhook_invoice_succeeded_flow` | integration | webhook invoice 完整流程 |
| IP05 | `test_api_payment_credits_returns_correct_balance` | integration | 额度查询返回正确余额 |
| IP06 | `test_api_payment_upgrade_full_flow` | integration | 升级完整流程 |
| IP07 | `test_api_payment_cancel_full_flow` | integration | 取消完整流程 |
| IP08 | `test_api_payment_transactions_history` | integration | 交易历史查询 |
| IP09 | `test_api_payment_customer_portal_redirect` | integration | 客户门户重定向 |

### 13.4 test_api_auth.py — 认证 API 集成测试

| # | 测试用例 | 类型 | 说明 |
|---|---------|------|------|
| IA01 | `test_api_auth_protected_route_valid_token` | integration | 有效 token 访问受保护路由 |
| IA02 | `test_api_auth_protected_route_no_token` | integration | 无 token 被拒绝 |
| IA03 | `test_api_auth_user_info_endpoint` | integration | 用户信息接口 |

---

## 14. 测试用例统计

| 模块 | 用例数 | 类型 |
|------|--------|------|
| test_models.py | 18 | unit |
| test_auth.py | 12 | unit |
| test_decorators.py | 11 | unit |
| test_payment_service.py | 21 | unit |
| test_option_scorer.py | 18 | unit |
| test_ev_model.py | 10 | unit |
| test_task_queue.py | 8 | unit |
| test_recommendation_service.py | 7 | unit |
| test_ai_service.py | 6 | unit |
| test_narrative_service.py | 6 | unit |
| test_stock_engine.py | 11 | unit |
| test_options_engine.py | 10 | unit |
| test_api_stock.py | 8 | integration |
| test_api_options.py | 7 | integration |
| test_api_payment.py | 9 | integration |
| test_api_auth.py | 3 | integration |
| **合计** | **165** | - |

---

*最后更新: 2026-02-08*

# 分析统计与系统监控 (Analytics & Metrics)

本模块包含两个子系统：**用户行为分析**（Analytics）和 **数据源性能监控**（Metrics）。

---

## 1. 用户行为分析 (Analytics)

**文件**: `app/api/analytics.py` (158 行)

### 1.1 POST `/api/analytics/events` -- 批量事件提交

| 参数 | 说明 |
|------|------|
| 请求体 | `{"events": [...]}` |
| 最大批量 | **100 条**（超出截断不报错） |
| 存储 | `AnalyticsEvent` 模型，bulk insert |
| 错误策略 | 失败也返回 `{"success": true}`，防止客户端重试洪泛 |

**事件属性**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `event_type` | str | 是 | page_view, click, analysis_request 等 |
| `session_id` | str | 是 | 会话标识 |
| `user_id` | str | 否 | UUID，游客为 null |
| `user_tier` | str | 否 | guest / free / plus / pro |
| `properties` | JSON | 否 | 自定义 key-value |
| `url` | str | 否 | 当前页面 URL |
| `referrer` | str | 否 | 来源页面 |
| `timestamp` | ISO str | 否 | 支持 `Z` 后缀，默认服务端时间 |

### 1.2 GET `/api/analytics/stats` -- 基础统计

| 查询参数 | 默认 | 范围 |
|----------|------|------|
| `days` | 7 | 1-30 |

返回: `event_counts`（按 event_type 分组 COUNT）、`unique_sessions`（DISTINCT session_id）、`unique_users`（DISTINCT user_id, NOT NULL）

---

## 2. 系统监控 API (Metrics API)

**文件**: `app/api/metrics.py` (451 行)

### 2.1 端点一览

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/api/metrics/` | 综合指标：uptime, totals, by_provider, by_data_type, recent_errors |
| GET | `/api/metrics/providers` | 所有数据源状态和能力 |
| GET | `/api/metrics/providers/{name}` | 单个数据源健康（healthy/degraded/unhealthy） |
| GET | `/api/metrics/latency` | 延迟百分位 p50/p90/p95/p99，可按 provider/data_type 过滤 |
| GET | `/api/metrics/recent` | 最近请求（max 500），支持 provider/symbol/data_type/errors_only 过滤 |
| GET | `/api/metrics/dashboard` | HTML 可视化仪表板 |

### 2.2 健康状态判定

| 成功率 | 状态 |
|--------|------|
| >= 95% | `healthy` |
| >= 80% | `degraded` |
| < 80% | `unhealthy` |
| 无数据 | `unknown` |

### 2.3 HTML Dashboard

- 深色主题，CSS Variables 驱动
- 四宫格：Total Calls / Success Rate / Cache Hit Rate / P50 Latency
- Provider Status：名称 + Badge + Calls + Avg Latency
- Recent Errors 滚动列表 + Data Type Breakdown 网格
- **30 秒**自动刷新（`setInterval(loadData, 30000)`）

---

## 3. 指标收集器 (MetricsCollector)

**文件**: `app/services/market_data/metrics.py` (569 行)

Singleton 模式 + `threading.Lock` 线程安全。

### 3.1 数据结构

| 类 | 用途 |
|----|------|
| `CallResult` (Enum) | SUCCESS, CACHE_HIT, FALLBACK, FAILURE, TIMEOUT, RATE_LIMITED |
| `CallRecord` (dataclass) | 单次调用记录：timestamp, data_type, symbol, providers_tried, latency_ms, result |
| `ProviderMetrics` (dataclass) | 按 provider 聚合：total_calls, success_rate, avg_latency_ms, min/max |
| `DataTypeMetrics` (dataclass) | 按数据类型聚合：total_calls, cache_hit_rate, fallback_rate, failures |

### 3.2 存储架构

- `_records`: `Deque[CallRecord]`，ring buffer，**maxlen=10,000**
- `_provider_metrics`: `Dict[str, ProviderMetrics]`，按 provider 聚合
- `_data_type_metrics`: `Dict[DataType, DataTypeMetrics]`，按类型聚合

### 3.3 核心方法

| 方法 | 功能 |
|------|------|
| `record_call(data_type, symbol, ...)` | 记录一次调用：更新 ring buffer + provider/type 聚合 + JSON 日志 |
| `get_stats()` | 综合统计（供 API `/api/metrics/`） |
| `get_provider_health(name)` | 单 provider 健康 + 最近 10 条错误 |
| `get_recent_calls(limit, ...)` | 带过滤的最近记录 |
| `get_latency_percentiles(...)` | p50/p90/p95/p99，基于 SUCCESS 记录排序取百分位 |
| `reset()` | 重置所有指标（测试用） |

### 3.4 `record_call()` 流程

```
1. 确定 CallResult（优先级：cache_hit > timeout > rate_limited > failure > fallback > success）
2. 创建 CallRecord，Lock 内追加到 ring buffer
3. 更新 DataTypeMetrics（+total, +cache/miss, +failure）
4. 更新 ProviderMetrics（per provider: +total, +success/fail, latency min/max/sum）
5. 结构化 JSON 日志（failure=INFO, success=DEBUG）
6. 每 300 秒输出汇总日志
```

### 3.5 配置

| 参数 | 值 |
|------|-----|
| `MAX_RECORDS` | 10,000（ring buffer 容量） |
| `LOG_INTERVAL_SECONDS` | 300（汇总日志间隔） |
| `LOG_TO_JSON` | True |

---

## 4. 文件路径

| 文件 | 行数 | 职责 |
|------|------|------|
| `backend/app/api/analytics.py` | 158 | 用户行为分析 API |
| `backend/app/api/metrics.py` | 451 | 系统监控 API + HTML Dashboard |
| `backend/app/services/market_data/metrics.py` | 569 | 底层指标收集器（Singleton） |
| `backend/app/services/market_data/interfaces.py` | -- | DataType enum 定义 |
| `backend/app/models.py` | -- | AnalyticsEvent 模型 |

---

*文档版本: 2026.02 | 基于 analytics.py, metrics.py, market_data/metrics.py 实际代码编写*

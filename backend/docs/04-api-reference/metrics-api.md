# Metrics API -- 市场数据指标监控接口

**Blueprint 前缀**: `/api/metrics` | **源文件**: `app/api/metrics.py` | **Auth**: 全部无需认证

监控数据提供商 (Data Provider) 健康状态和性能，包括延迟分位数、调用记录和可视化 Dashboard。

---

## 1. GET /api/metrics/

获取所有市场数据操作的综合指标。

**Response:**
```json
{
  "success": true,
  "data": {
    "uptime": {"uptime_seconds": 86400, "started_at": "..."},
    "totals": {
      "total_calls": 10000, "cache_hits": 5000,
      "cache_hit_rate": 50.0, "failures": 100, "failure_rate": 1.0
    },
    "by_provider": {
      "yfinance": {"total_calls": 6000, "success_rate": 98.5, "avg_latency_ms": 320}
    },
    "by_data_type": {
      "quote": {"total_calls": 3000, "cache_hit_rate": 60.0}
    },
    "recent_errors": [
      {"timestamp": "...", "symbol": "INVALID", "data_type": "quote", "error_type": "TickerNotFound"}
    ]
  }
}
```

---

## 2. GET /api/metrics/providers

获取所有已注册提供商的状态（启用状态、健康度、能力）。

**Response:**
```json
{
  "success": true,
  "providers": {
    "yfinance": {"enabled": true, "healthy": true, "capabilities": ["quote", "history", "options"]}
  }
}
```

---

## 3. GET /api/metrics/providers/{name}

获取指定提供商的详细健康状态。Path param `name` 为提供商名称（如 `yfinance`、`tiger`）。

**Response:**
```json
{
  "success": true,
  "provider": "yfinance",
  "health": {"success_rate": 98.5, "avg_latency_ms": 320, "total_calls": 6000, "recent_errors": []}
}
```

---

## 4. GET /api/metrics/latency

获取延迟分位数 (p50/p90/p95/p99)。

| Query Param | 类型 | 必填 | 说明 |
|-------------|------|------|------|
| `provider` | string | 否 | 按提供商过滤 |
| `data_type` | string | 否 | 按数据类型过滤（须为合法 DataType 枚举值） |

**Response:** `{"success": true, "percentiles": {"p50": 280, "p90": 520, "p95": 750, "p99": 1200}}`

**Error (400):** data_type 值不合法时返回 `{"success": false, "error": "Invalid data_type: ..."}`

---

## 5. GET /api/metrics/recent

获取近期调用记录，支持多维过滤。

| Query Param | 类型 | 默认 | 约束 | 说明 |
|-------------|------|------|------|------|
| `limit` | int | 100 | max 500 | 返回数量 |
| `provider` | string | -- | -- | 按提供商过滤 |
| `symbol` | string | -- | -- | 按股票代码过滤 |
| `data_type` | string | -- | -- | 按数据类型过滤 |
| `errors_only` | string | `"false"` | `"true"`/`"false"` | 仅返回错误记录 |

**Response:**
```json
{
  "success": true, "count": 50,
  "records": [
    {"timestamp": "...", "provider": "yfinance", "symbol": "AAPL",
     "data_type": "quote", "latency_ms": 310, "success": true, "error": null}
  ]
}
```

---

## 6. GET /api/metrics/dashboard

渲染可视化 Dashboard HTML 页面（返回 `text/html`）。

- 自动调用 `/api/metrics/` 和 `/api/metrics/latency` 获取数据
- 每 30 秒自动刷新
- 展示 Total Calls、Success Rate、Cache Hit Rate、P50 Latency、Provider Status、Recent Errors
- 浏览器直接访问 `/api/metrics/dashboard` 即可查看

---

## 通用错误响应 (500)

```json
{"success": false, "error": "错误描述"}
```

# Analytics API -- 用户行为分析接口

**Blueprint 前缀**: `/api/analytics` | **源文件**: `app/api/analytics.py` | **Auth**: 全部无需认证

收集前端用户行为事件并存入数据库。采用"静默容错"策略 -- 存储失败仍返回 200，避免重试风暴。

---

## 1. POST /api/analytics/events

批量提交用户行为事件。

**Request Body:**
```json
{
  "events": [
    {
      "event_type": "page_view",
      "session_id": "abc123",
      "user_id": "uuid-or-null",
      "user_tier": "free",
      "properties": {"page": "stock_analysis"},
      "url": "/options",
      "referrer": "https://google.com",
      "timestamp": "2026-02-07T09:30:00Z"
    }
  ]
}
```

| 字段 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `events` | array | 是 | -- | 事件数组，最大 100 条 |

**单个 event 字段：**

| 字段 | 默认 | 说明 |
|------|------|------|
| `event_type` | `"unknown"` | 事件类型 |
| `session_id` | `"unknown"` | 会话 ID |
| `user_id` | `null` | 用户 UUID（游客为 null） |
| `user_tier` | `"guest"` | `guest`/`free`/`plus`/`pro` |
| `properties` | `{}` | 自定义属性 |
| `url` | `""` | 页面 URL |
| `referrer` | `""` | 来源 URL |
| `timestamp` | 当前时间 | ISO 8601 格式 |

**Response (200):** `{"success": true, "count": 5}`

即使内部错误也返回 200，`count` 为 0。

---

## 2. GET /api/analytics/stats

获取基础统计（事件计数、独立会话、独立用户）。

| Query Param | 类型 | 默认 | 约束 | 说明 |
|-------------|------|------|------|------|
| `days` | int | 7 | max 30 | 回溯天数 |

**Response:**
```json
{
  "success": true,
  "period_days": 7,
  "stats": {
    "event_counts": {"page_view": 1523, "click": 892},
    "unique_sessions": 456,
    "unique_users": 128
  }
}
```

`unique_users` 不含游客（user_id 为 null 的记录）。

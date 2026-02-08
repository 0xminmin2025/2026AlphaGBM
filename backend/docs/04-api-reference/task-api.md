# Task API -- 异步任务管理接口

**Blueprint 前缀**: `/api/tasks` | **源文件**: `app/api/tasks.py` | **Auth**: 全部需要 `@require_auth`

---

## 1. POST /api/tasks/create

创建异步分析任务。

**Request Body:**
```json
{
  "task_type": "stock_analysis",
  "input_params": {"ticker": "AAPL", "style": "quality"},
  "priority": 100
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `task_type` | string | 是 | `stock_analysis` / `option_analysis` / `enhanced_option_analysis` |
| `input_params` | object | 是 | 任务参数 |
| `priority` | int | 否 | 默认 100，数值越小优先级越高 |

**input_params 必填字段：**
- `stock_analysis`: `ticker`
- `option_analysis`: `symbol`
- `enhanced_option_analysis`: `symbol` + `option_identifier`

**Response (201):** `{"task_id": "uuid-string", "message": "Task created successfully"}`

**Errors:** 400 (参数校验失败) / 401 (未认证) / 500

---

## 2. GET /api/tasks/{id}/status

查询任务状态和进度。仅可查询当前用户拥有的任务。

**Response:**
```json
{
  "id": "uuid", "task_type": "stock_analysis",
  "status": "processing", "progress_percent": 75,
  "current_step": "Running AI analysis...",
  "input_params": {}, "result_data": null,
  "error_message": null,
  "created_at": "...", "started_at": "...", "completed_at": null,
  "related_history_id": null, "related_history_type": null
}
```

| status 值 | 说明 |
|-----------|------|
| `pending` | 等待处理 |
| `processing` | 正在分析 |
| `completed` | 完成（result_data 包含结果） |
| `failed` | 失败（error_message 包含原因） |

**Errors:** 401 / 403 (非本人任务) / 404

---

## 3. GET /api/tasks/{id}/result

获取已完成任务的结果。仅当 status 为 `completed` 时可用。

**Response:**
```json
{
  "task_id": "uuid", "status": "completed",
  "result_data": {"ticker": "AAPL", "score": 85},
  "related_history_id": 123, "related_history_type": "stock",
  "completed_at": "2026-02-07T12:02:15"
}
```

**Errors:** 400 (任务未完成，返回 current_status 和 progress_percent) / 403 / 404

---

## 4. GET /api/tasks/user

获取当前用户任务列表。

| Query Param | 类型 | 默认 | 约束 | 说明 |
|-------------|------|------|------|------|
| `limit` | int | 10 | max 50 | 返回数量 |
| `status` | string | -- | pending/processing/completed/failed | 过滤状态 |

**Response:**
```json
{
  "tasks": [{"id": "uuid", "task_type": "...", "status": "...", ...}],
  "total": 25, "limit": 10, "status_filter": null
}
```

---

## 5. GET /api/tasks/stats

获取当前用户任务统计。

**Response:**
```json
{
  "total_tasks": 25, "pending": 2, "processing": 1,
  "completed": 20, "failed": 2, "success_rate": 0.91
}
```

`success_rate` = completed / (completed + failed)，无已结束任务时为 0。

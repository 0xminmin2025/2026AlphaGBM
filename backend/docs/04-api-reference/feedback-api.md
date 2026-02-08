# Feedback API -- 用户反馈接口

## 概述

用户反馈模块提供单一的反馈提交 endpoint，允许已认证用户提交 bug 报告、功能建议或问题咨询。反馈记录包含用户 ID、IP 地址和可选的关联股票代码。

**Blueprint 前缀**: `/api/feedback`

**源文件**: `app/api/feedback.py`

**数据模型**: `Feedback`

---

## POST /api/feedback

提交用户反馈。

| 属性 | 说明 |
|------|------|
| Method | `POST` |
| Auth | `@require_auth` (JWT Bearer Token) |
| Content-Type | `application/json` |

### Request Body

```json
{
  "type": "bug",
  "content": "股票分析页面在分析港股时出现加载超时",
  "ticker": "0700.HK"
}
```

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `type` | string | 否 | `"general"` | 反馈类型：`bug` / `suggestion` / `question` / `general` |
| `content` | string | 是 | -- | 反馈内容（不能为空或仅含空格） |
| `ticker` | string | 否 | `null` | 关联的股票代码 |

若 `type` 值不在合法范围内，自动修正为 `general`。

### 服务端自动记录的字段

| 字段 | 来源 |
|------|------|
| `user_id` | 从 JWT Token 解析，通过 `g.user_id` 获取 |
| `ip_address` | 优先取 `X-Forwarded-For` 请求头，否则取 `request.remote_addr` |
| `submitted_at` | 服务端 UTC 时间 |

### Response (200)

```json
{
  "success": true,
  "message": "Feedback submitted successfully",
  "feedback_id": 42
}
```

### 错误响应

| Status | 响应 | 场景 |
|--------|------|------|
| 400 | `{"success": false, "error": "No data provided"}` | 请求体为空 |
| 400 | `{"success": false, "error": "Feedback content is required"}` | content 字段为空 |
| 401 | `{"success": false, "error": "User not authenticated"}` | 未认证或 Token 无效 |
| 500 | `{"success": false, "error": "..."}` | 数据库写入失败 |

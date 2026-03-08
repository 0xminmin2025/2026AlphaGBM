# API Reference 总览

## Base URL

所有 API 端点基于统一前缀：

```
/api
```

生产环境完整 URL 示例：`https://your-domain.com/api/stock/search?q=AAPL`

---

## 认证方式 (Authentication)

API 使用 **Bearer Token** 认证，Token 为 Supabase 签发的 JWT。

```
Authorization: Bearer <supabase_jwt_token>
```

- 部分端点无需认证（标注为 `no auth`），如搜索、定价查询等
- 需要认证的端点使用 `@require_auth` 装饰器，验证 JWT 并从中提取 `user_id`
- 额度检查端点使用 `@check_quota` 装饰器，同时处理认证和额度扣减

---

## 请求格式 (Request Format)

- **Content-Type**: `application/json`（除文件上传外）
- **文件上传**: `multipart/form-data`
- 所有 JSON body 字段使用 `snake_case` 命名

---

## 响应格式 (Response Format)

### 成功响应

```json
{
  "success": true,
  "data": { ... }
}
```

### 错误响应

```json
{
  "error": "错误描述信息",
  "code": "ERROR_CODE"
}
```

部分端点在错误时也会返回 `"success": false`：

```json
{
  "success": false,
  "error": "具体错误信息"
}
```

---

## 通用 HTTP 状态码 (Common HTTP Status Codes)

| 状态码 | 含义 | 说明 |
|--------|------|------|
| `200` | OK | 请求成功 |
| `201` | Created | 异步任务创建成功 |
| `400` | Bad Request | 请求参数缺失或无效 |
| `401` | Unauthorized | 未提供 Token 或 Token 无效/过期 |
| `402` | Insufficient Credits | 额度不足，需购买额度包或升级订阅 |
| `403` | Forbidden | 无权限访问该资源（如强制刷新需额度但额度不足） |
| `404` | Not Found | 资源不存在（如历史记录 ID 无效） |
| `429` | Rate Limited | 请求频率过高，请稍后重试 |
| `500` | Server Error | 服务器内部错误 |

---

## 额度系统 (Quota System)

### 免费额度

| 用户类型 | 每日免费次数 | 适用服务 |
|----------|-------------|---------|
| 所有用户 | 2 次/天 | `stock_analysis`、`option_analysis` 共享 |
| 所有用户 | 0 次/天 | `deep_report` 无免费额度 |

### 额度消耗

| 服务类型 (service_type) | 每次消耗 | 说明 |
|------------------------|---------|------|
| `stock_analysis` | 1 credit | 股票分析（同步/异步） |
| `option_analysis` | 1 credit | 期权链分析 / 增强分析 / 反向查分 |
| `deep_report` | 1 credit | 深度研报 |

### 额度优先级

1. 优先使用当日免费额度
2. 免费额度用完后扣减付费额度
3. 额度不足时返回 `402` 错误

---

## API 模块索引

| 模块 | 前缀 | 文档 |
|------|------|------|
| 认证 (Auth) | `/api/auth` | [auth-api.md](./auth-api.md) |
| 用户 (User) | `/api/user` | [user-api.md](./user-api.md) |
| 股票 (Stock) | `/api/stock` | [stock-api.md](./stock-api.md) |
| 期权 (Options) | `/api/options` | [options-api.md](./options-api.md) |
| 支付 (Payment) | `/api/payment` | [payment-api.md](./payment-api.md) |

---

## 异步任务模式 (Async Task Pattern)

部分分析端点采用异步任务队列模式：

1. 客户端发起 POST 请求 -> 返回 `task_id`
2. 客户端轮询 `GET /api/tasks/{task_id}` 获取进度
3. 任务完成后返回完整分析结果

异步端点会利用每日缓存 (DailyAnalysisCache)：
- **Cache HIT**: 立即返回缓存数据（模拟进度动画）
- **In-progress**: 复用已有任务，避免重复计算
- **Cache MISS**: 创建新的分析任务

---

## 装饰器说明 (Decorators)

| 装饰器 | 作用 |
|--------|------|
| `@require_auth` | 验证 JWT Token，提取 `user_id` 到 `g.user_id` |
| `@check_quota(service_type, amount)` | 认证 + 额度检查 + 自动扣减 |
| `@db_retry(max_retries, retry_delay)` | 数据库操作自动重试（处理 Supabase SSL 瞬断） |

# Auth API -- 认证接口

> Blueprint 前缀: `/api/auth`
> 源码文件: `backend/app/api/auth.py`

---

## GET /api/auth/status

健康检查端点，用于验证后端服务是否正常运行。

### 认证

无需认证 (no auth)

### Parameters

无

### 请求示例

```http
GET /api/auth/status HTTP/1.1
Host: your-domain.com
```

### 成功响应

**Status: `200 OK`**

```json
{
  "status": "ok"
}
```

### 错误码

| 状态码 | 说明 |
|--------|------|
| `500` | 服务器内部错误，服务不可用 |

### 使用场景

- 前端启动时检测后端是否在线
- 负载均衡器 / 容器编排的 health check
- 监控系统定期探活

### 备注

此端点不涉及数据库查询或外部服务调用，响应速度极快，适合高频探活。

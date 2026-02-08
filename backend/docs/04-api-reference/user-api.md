# User API -- 用户接口

> Blueprint 前缀: `/api/user`
> 源码文件: `backend/app/api/user.py`

---

## GET /api/user/profile

获取当前登录用户的个人信息。

### 认证

需要认证 (`@require_auth`)

```
Authorization: Bearer <supabase_jwt_token>
```

### Parameters

无

### 请求示例

```http
GET /api/user/profile HTTP/1.1
Host: your-domain.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

### 成功响应

**Status: `200 OK`**

```json
{
  "message": "User Profile Endpoint"
}
```

> **注意**: 当前此端点返回占位响应，后续将扩展为完整的用户 profile 数据，包括：
> - `user_id` -- 用户唯一标识
> - `email` -- 注册邮箱
> - `subscription` -- 订阅信息
> - `created_at` -- 注册时间

### 错误码

| 状态码 | 说明 |
|--------|------|
| `401` | 未提供 Token 或 Token 无效/过期 |
| `500` | 服务器内部错误 |

### 使用场景

- 用户登录后加载个人信息
- Dashboard 页面展示用户状态
- 前端路由守卫中验证用户身份

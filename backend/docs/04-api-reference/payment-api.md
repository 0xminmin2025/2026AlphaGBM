# Payment API -- 支付与额度接口

> Blueprint 前缀: `/api/payment`
> 源码文件: `backend/app/api/payment.py`

---

## 端点列表

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| POST | `/api/payment/create-checkout-session` | `@require_auth` | 创建 Stripe 支付会话 |
| POST | `/api/payment/webhook` | Stripe Signature | Stripe Webhook 回调 |
| POST | `/api/payment/check-quota` | `@require_auth` | 检查额度是否足够 |
| GET | `/api/payment/credits` | `@require_auth` | 获取用户额度信息 |
| GET | `/api/payment/transactions` | `@require_auth` | 获取交易历史 |
| GET | `/api/payment/usage-history` | `@require_auth` | 获取额度使用历史 |
| GET | `/api/payment/pricing` | 无 | 获取定价信息 |
| POST | `/api/payment/upgrade` | `@require_auth` | 升级订阅 |
| POST | `/api/payment/cancel` | `@require_auth` | 取消订阅 |
| GET | `/api/payment/upgrade-options` | `@require_auth` | 获取可升级选项 |
| POST | `/api/payment/customer-portal` | `@require_auth` | 创建 Stripe 客户门户会话 |

---

## POST /api/payment/create-checkout-session

创建 Stripe Checkout Session，用于引导用户完成支付。

### 认证

`@require_auth`

### Request Body (JSON)

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `price_key` | string | 是 | - | 价格键，必须在 `PaymentService.PRICES` 中定义 |
| `success_url` | string | 否 | `{FRONTEND_URL}/dashboard?success=true` | 支付成功跳转 URL |
| `cancel_url` | string | 否 | `{FRONTEND_URL}/pricing?canceled=true` | 取消支付跳转 URL |

### 请求示例

```http
POST /api/payment/create-checkout-session HTTP/1.1
Content-Type: application/json
Authorization: Bearer <token>

{
  "price_key": "plus_monthly",
  "success_url": "https://app.example.com/dashboard?success=true",
  "cancel_url": "https://app.example.com/pricing?canceled=true"
}
```

### 成功响应

**Status: `200 OK`**

```json
{
  "session_id": "cs_test_xxxxx",
  "checkout_url": "https://checkout.stripe.com/c/pay/cs_test_xxxxx"
}
```

### 错误码

| 状态码 | 错误描述 | 说明 |
|--------|---------|------|
| `400` | `No data provided` | 请求体为空 |
| `400` | `无效的价格键` | `price_key` 不在可用列表中 |
| `400` | Stripe 错误信息 | Stripe API 返回错误 |
| `401` | - | 未登录 |

---

## POST /api/payment/webhook

Stripe Webhook 回调端点，接收并处理 Stripe 事件通知。

### 认证

无需 JWT 认证。使用 **Stripe Signature** 验证请求真实性（通过 `Stripe-Signature` header 和 `STRIPE_WEBHOOK_SECRET` 环境变量）。

### 处理的事件类型

| 事件类型 | 处理逻辑 |
|----------|---------|
| `checkout.session.completed` | 支付完成，激活订阅/充值额度 |
| `invoice.payment_succeeded` | 发票支付成功（含续费） |
| `invoice.paid` | 发票已支付 |
| `customer.subscription.deleted` | 订阅已取消，更新状态为 `canceled` |
| `customer.subscription.created` | 记录日志（实际处理在 checkout 阶段） |
| `customer.subscription.updated` | 记录日志 |

### 请求格式

由 Stripe 自动发送，payload 为 raw body，需通过 `stripe.Webhook.construct_event()` 验证。

### 成功响应

**Status: `200 OK`**

```json
{
  "status": "success"
}
```

### 错误码

| 状态码 | 错误描述 | 说明 |
|--------|---------|------|
| `400` | `Invalid payload` | 请求体格式错误 |
| `400` | `Invalid signature` | Stripe 签名验证失败 |
| `500` | `Webhook密钥未配置` | 未设置 `STRIPE_WEBHOOK_SECRET` 环境变量 |
| `500` | 处理错误信息 | 事件处理过程中出错 |

---

## POST /api/payment/check-quota

检查用户额度是否足够（不扣减额度），用于前端在分析前展示确认弹窗。

### 认证

`@require_auth`

### Request Body (JSON)

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `service_type` | string | 否 | `"stock_analysis"` | 服务类型：`stock_analysis` / `option_analysis` / `deep_report` |
| `amount` | integer | 否 | `1` | 需要消耗的额度数量 |

### 请求示例

```http
POST /api/payment/check-quota HTTP/1.1
Content-Type: application/json
Authorization: Bearer <token>

{
  "service_type": "option_analysis",
  "amount": 3
}
```

### 成功响应

**Status: `200 OK`**

```json
{
  "has_enough": true,
  "will_use_free": false,
  "free_quota": 2,
  "free_used": 2,
  "free_remaining": 0,
  "paid_credits": 150,
  "amount_needed": 3,
  "message": "额度充足"
}
```

### 响应字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `has_enough` | boolean | 是否有足够额度 |
| `will_use_free` | boolean | 是否将使用免费额度 |
| `free_quota` | integer | 每日免费总额度 |
| `free_used` | integer | 今日已使用免费额度 |
| `free_remaining` | integer | 今日剩余免费额度 |
| `paid_credits` | integer | 付费额度余额 |
| `amount_needed` | integer | 本次需要的额度数量 |
| `message` | string | 人类可读的状态描述 |

### 错误码

| 状态码 | 说明 |
|--------|------|
| `401` | 未登录 |

---

## GET /api/payment/credits

获取用户的额度详细信息，包含订阅状态和每日免费额度使用情况。

### 认证

`@require_auth`

### Query Parameters

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `service_type` | string | 否 | `"stock_analysis"` | 查询的服务类型 |

### 请求示例

```http
GET /api/payment/credits?service_type=option_analysis HTTP/1.1
Authorization: Bearer <token>
```

### 成功响应

**Status: `200 OK`**

```json
{
  "total_credits": 850,
  "subscription": {
    "plan": "plus",
    "status": "active",
    "current_period_end": "2025-02-15T00:00:00"
  },
  "daily_free": {
    "quota": 2,
    "used": 1,
    "remaining": 1
  }
}
```

### 错误码

| 状态码 | 说明 |
|--------|------|
| `401` | 未登录 |

---

## GET /api/payment/transactions

获取用户的交易（支付）历史，支持分页。

### 认证

`@require_auth`

### Query Parameters

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `page` | integer | 否 | `1` | 页码 |
| `per_page` | integer | 否 | `20` | 每页条数 |

### 请求示例

```http
GET /api/payment/transactions?page=1&per_page=10 HTTP/1.1
Authorization: Bearer <token>
```

### 成功响应

**Status: `200 OK`**

```json
{
  "transactions": [
    {
      "period_start": "",
      "date": "2025-01-10T14:30:00",
      "description": "Plus会员月度订阅",
      "amount": 58.80,
      "currency": "usd",
      "status": "succeeded",
      "invoice_pdf": ""
    }
  ],
  "total": 5,
  "pages": 1,
  "current_page": 1
}
```

### 备注

- `amount` 字段已从 Stripe 的最小货币单位（美分）转换为标准单位（美元），即原始值除以 100

### 错误码

| 状态码 | 说明 |
|--------|------|
| `401` | 未登录 |

---

## GET /api/payment/usage-history

获取用户的额度使用（消耗）历史，支持分页。

### 认证

`@require_auth`

### Query Parameters

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `page` | integer | 否 | `1` | 页码 |
| `per_page` | integer | 否 | `10` | 每页条数 |

### 请求示例

```http
GET /api/payment/usage-history?page=1 HTTP/1.1
Authorization: Bearer <token>
```

### 成功响应

**Status: `200 OK`**

```json
{
  "usage_logs": [
    {
      "id": 201,
      "service_type": "stock_analysis",
      "amount_used": 1,
      "created_at": "2025-01-15T10:30:00"
    },
    {
      "id": 200,
      "service_type": "option_analysis",
      "amount_used": 1,
      "created_at": "2025-01-15T09:15:00"
    }
  ],
  "total": 42,
  "pages": 5,
  "current_page": 1,
  "per_page": 10
}
```

### 错误码

| 状态码 | 说明 |
|--------|------|
| `401` | 未登录 |

---

## GET /api/payment/pricing

获取产品定价信息，无需登录。所有价格以 USD 计价。

### 认证

无需认证 (no auth)

### 请求示例

```http
GET /api/payment/pricing HTTP/1.1
```

### 成功响应

**Status: `200 OK`**

```json
{
  "plans": {
    "free": {
      "name": "免费版",
      "price": 0,
      "credits": "每天2次查询",
      "features": ["每日2次", "期权分析", "股票分析"]
    },
    "plus": {
      "name": "Plus会员",
      "monthly": {
        "price": 58.8,
        "currency": "usd",
        "credits": 1000,
        "period": "month"
      },
      "yearly": {
        "price": 588,
        "currency": "usd",
        "credits": 12000,
        "period": "year",
        "savings": "节省17%"
      },
      "features": ["1000次查询/月", "期权分析", "反向查分", "股票分析"]
    },
    "pro": {
      "name": "Pro会员",
      "monthly": {
        "price": 99.8,
        "currency": "usd",
        "credits": 5000,
        "period": "month"
      },
      "yearly": {
        "price": 998,
        "currency": "usd",
        "credits": 60000,
        "period": "year",
        "savings": "节省17%"
      },
      "features": ["5000次查询/月", "期权分析", "反向查分", "股票分析", "投资回顾"]
    },
    "enterprise": {
      "name": "企业客户",
      "price": null,
      "credits": "定制化",
      "features": ["API接入", "批量期权分析", "定制化策略", "专属客服"]
    }
  },
  "topups": {
    "100": {
      "name": "额度加油包（100次）",
      "price": 4.99,
      "currency": "usd",
      "credits": 100,
      "validity": "3个月有效"
    }
  }
}
```

### 错误码

无特定错误（该端点始终返回 `200`）。

---

## POST /api/payment/upgrade

升级当前订阅到更高级别的套餐。

### 认证

`@require_auth`

### Request Body (JSON)

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `price_key` | string | 是 | 目标套餐的价格键 |

### 请求示例

```http
POST /api/payment/upgrade HTTP/1.1
Content-Type: application/json
Authorization: Bearer <token>

{
  "price_key": "pro_monthly"
}
```

### 成功响应

**Status: `200 OK`**

返回升级结果信息（具体字段由 `PaymentService.upgrade_subscription` 决定）。

### 错误码

| 状态码 | 错误描述 | 说明 |
|--------|---------|------|
| `400` | `请指定升级的套餐` | 未提供 `price_key` |
| `400` | Stripe/业务逻辑错误 | 升级不可用或已是最高级别 |
| `401` | - | 未登录 |

---

## POST /api/payment/cancel

取消当前订阅，在当前计费周期结束后生效。

### 认证

`@require_auth`

### Request Body

无需请求体。

### 请求示例

```http
POST /api/payment/cancel HTTP/1.1
Authorization: Bearer <token>
```

### 成功响应

**Status: `200 OK`**

返回取消结果信息（具体字段由 `PaymentService.cancel_subscription` 决定）。

### 错误码

| 状态码 | 说明 |
|--------|------|
| `400` | 无有效订阅可取消，或 Stripe 操作失败 |
| `401` | 未登录 |

---

## GET /api/payment/upgrade-options

获取当前用户可以升级到的套餐选项。

### 认证

`@require_auth`

### 请求示例

```http
GET /api/payment/upgrade-options HTTP/1.1
Authorization: Bearer <token>
```

### 成功响应

**Status: `200 OK`**

返回可用的升级选项列表（具体结构由 `PaymentService.get_upgrade_options` 决定）。

### 错误码

| 状态码 | 说明 |
|--------|------|
| `401` | 未登录 |

---

## POST /api/payment/customer-portal

创建 Stripe Customer Portal 会话，允许用户自助管理订阅、支付方式和发票。

### 认证

`@require_auth`

### Request Body (JSON)

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `return_url` | string | 否 | `{FRONTEND_URL}/profile` | 从 Portal 返回后的跳转 URL |

### 请求示例

```http
POST /api/payment/customer-portal HTTP/1.1
Content-Type: application/json
Authorization: Bearer <token>

{
  "return_url": "https://app.example.com/profile"
}
```

### 成功响应

**Status: `200 OK`**

```json
{
  "portal_url": "https://billing.stripe.com/p/session/xxxxx"
}
```

### 错误码

| 状态码 | 错误描述 | 说明 |
|--------|---------|------|
| `400` | `未找到客户信息，请先创建订阅` | 用户没有 `stripe_customer_id` |
| `400` | `未找到有效订阅` | 用户没有 `active` 状态的订阅 |
| `400` | `Stripe错误: ...` | Stripe API 返回错误 |
| `401` | - | 未登录 |
| `404` | `用户不存在` | User 记录不存在 |
| `500` | `创建客户门户失败: ...` | 服务器内部错误 |

# Payment System 模块

## 1. 模块概述

支付系统模块处理所有与付费相关的业务逻辑，包括 Stripe 集成、额度管理和配额控制。

**核心架构决策：**

- 支付网关使用 **Stripe**，支持 subscription（订阅）和 one-time payment（加油包）两种模式
- 免费用户每日 **2 次共享配额**（所有服务类型合并计算，`FREE_USER_DAILY_QUOTA = 2`）
- 付费额度通过 **CreditLedger** 以 FIFO 策略消费，支持过期时间
- 额度发放的**唯一入口**是 `invoice.payment_succeeded` webhook（订阅类型）
- 所有 PaymentService 方法均为 `@classmethod`，无实例状态

**额度消费决策流程：**

```
API 请求进入
  │
  ├─ @check_quota 装饰器
  │     ├─ 验证 JWT token (同 @require_auth 逻辑)
  │     └─ 调用 check_and_deduct_credits()
  │
  ├─ 1. 检查每日免费额度
  │     ├─ DailyQueryCount.query_count < FREE_USER_DAILY_QUOTA(2)
  │     │     └─ 扣减免费额度 → 记录 UsageLog → 返回成功
  │     └─ 已用完 → 进入步骤 2
  │
  ├─ 2. 查找付费额度 (CreditLedger FIFO)
  │     ├─ 找到未过期且 amount_remaining > 0 的记录
  │     │     └─ with_for_update() 行级锁 → 扣减 → 记录 UsageLog → 返回成功
  │     └─ 无可用额度 → 返回 402 INSUFFICIENT_CREDITS
  │
  └─ 视图函数执行
```

---

## 2. PaymentService 类

文件：`app/services/payment_service.py`，947 行

全部 14 个方法均为 `@classmethod`，无需实例化。按职责分为四组：

### 2.1 Checkout 与支付

| 方法 | 签名 | 返回值 | 说明 |
|------|------|--------|------|
| `create_checkout_session` | `(user_id, price_key, success_url, cancel_url, email=None)` | `(session, error)` | 创建 Stripe Checkout Session；订阅检查已有活跃订阅；支持 lazy user creation |
| `handle_checkout_completed` | `(session)` | `(bool, message)` | 处理 `checkout.session.completed` webhook |
| `handle_invoice_payment_succeeded` | `(invoice)` | `(bool, message)` | **额度发放唯一入口**，处理 `invoice.payment_succeeded` webhook |

**`create_checkout_session` 核心逻辑：**

```python
# 1. 订阅类型 → 检查是否已有活跃订阅（有则拒绝，引导使用升级功能）
# 2. 用户不存在 + 提供 email → lazy creation（Supabase 同步场景）
# 3. 获取或创建 Stripe Customer（绑定 user.stripe_customer_id）
# 4. mode = 'payment' if 'topup' else 'subscription'
# 5. metadata 携带 user_id, price_key, type
# 6. locale='zh'
```

**`handle_checkout_completed` 分支处理：**

- **订阅类型**（`topup` 不在 `price_key` 中）：仅创建 Subscription 记录，**不发放额度**（额度在 `invoice.payment_succeeded` 中处理）
- **Top-up 类型**：直接创建 Transaction + 发放 100 额度（`days_valid=90`），因为 top-up 不触发 `invoice.payment_succeeded`

**`handle_invoice_payment_succeeded` 核心逻辑：**

```python
# 1. 非订阅 invoice → 跳过
# 2. billing_reason == 'subscription_update' → 跳过（由 upgrade_subscription 处理）
# 3. 幂等性检查：Transaction.query.filter_by(stripe_invoice_id=invoice_id)
# 4. Subscription 记录不存在 → 从 Stripe API 获取信息创建
# 5. 根据 period_days > 60 判断年付/月付
# 6. 创建 Transaction 记录（先 flush，确保幂等性）
# 7. 发放额度：add_credits(credits, source=SUBSCRIPTION, days_valid)
# 8. 首次订阅 + 有 referrer → 发放推荐奖励 100 额度 (90天有效)
```

### 2.2 额度管理

| 方法 | 签名 | 返回值 | 说明 |
|------|------|--------|------|
| `add_credits` | `(user_id, amount, source, service_type, days_valid=None, subscription_id=None)` | `CreditLedger` | 通用额度发放，创建 CreditLedger 记录 |
| `check_and_deduct_credits` | `(user_id, service_type, amount, ticker=None)` | `(bool, message, remaining, extra)` | FIFO 扣减，先免费后付费 |
| `check_daily_free_quota` | `(user_id, service_type, amount=1)` | `bool` | 检查免费额度是否足够 |
| `get_daily_free_quota_info` | `(user_id, service_type)` | `dict{quota, used, remaining}` | 获取免费额度详情 |
| `get_total_credits` | `(user_id, service_type)` | `int` | 查询所有未过期付费额度总和 |

**`check_and_deduct_credits` 流程（第 425-562 行）：**

1. 检查免费额度 → `DailyQueryCount.with_for_update()` 行级锁更新 `query_count` → 记录 UsageLog（无 `credit_ledger_id`）
2. 查找付费额度 → `CreditLedger.query.filter(amount_remaining > 0, 未过期).order_by(expires_at.asc().nullslast()).with_for_update().first()` → FIFO 扣减
3. 无可用额度 → 返回 `(False, "额度不足")`

> **关键设计**：订阅额度统一存储为 `service_type='stock_analysis'`，但可用于所有服务类型。

### 2.3 订阅信息与升级

| 方法 | 签名 | 返回值 | 说明 |
|------|------|--------|------|
| `get_user_subscription_info` | `(user_id)` | `dict` | 返回订阅状态、plan_tier、billing_cycle 等 |
| `upgrade_subscription` | `(user_id, new_price_key)` | `(dict, error)` | 即时升级，Stripe proration |
| `cancel_subscription` | `(user_id)` | `(dict, error)` | `cancel_at_period_end=True` |
| `get_upgrade_options` | `(user_id)` | `dict` | 返回可升级的 price_key 列表 |

### 2.4 辅助方法

| 方法 | 签名 | 返回值 | 说明 |
|------|------|--------|------|
| `get_current_price_key` | `(subscription)` | `str` | 从周期长度或 Stripe API 推断当前 price_key |
| `is_upgrade` | `(current_price_key, new_price_key)` | `bool` | 基于 `PRICE_TIER_ORDER` 判断是否为升级 |

---

## 3. 订阅计划配置

### 3.1 价格配置（类属性 `PRICES`）

所有 Stripe Price ID 从环境变量读取：

| price_key | 环境变量 | 用途 |
|-----------|----------|------|
| `plus_monthly` | `STRIPE_PRICE_PLUS_MONTHLY` | Plus 月付 |
| `plus_yearly` | `STRIPE_PRICE_PLUS_YEARLY` | Plus 年付 |
| `pro_monthly` | `STRIPE_PRICE_PRO_MONTHLY` | Pro 月付 |
| `pro_yearly` | `STRIPE_PRICE_PRO_YEARLY` | Pro 年付 |
| `topup_100` | `STRIPE_PRICE_TOPUP_100` | 加油包 100 次 |

### 3.2 套餐额度（类属性 `PLAN_CONFIG`）

| 套餐 | 月付额度 | 年付额度 | 月付价格 | 年付价格 |
|------|----------|----------|----------|----------|
| Plus | 1,000 次 | 12,000 次 | $58.80 | $588.00 |
| Pro  | 5,000 次 | 60,000 次 | $99.80 | $998.00 |

### 3.3 加油包

| 名称 | 价格 | 额度 | 有效期 |
|------|------|------|--------|
| 额度加油包 | $4.99 | 100 次 | 3 个月（90 天） |

### 3.4 升级排序（`PRICE_TIER_ORDER`）

```python
PRICE_TIER_ORDER = {
    'plus_monthly': 1,
    'plus_yearly': 2,
    'pro_monthly': 3,
    'pro_yearly': 4,
}
```

`is_upgrade()` 通过比较 tier 数值判断：`new_tier > current_tier` 为升级。只允许升级，不允许降级。

---

## 4. 额度管理机制

### 4.1 免费配额

**配置：**

```python
FREE_USER_DAILY_QUOTA = 2          # 所有服务共享的每日总次数
DAILY_FREE_QUOTA = {
    'stock_analysis': 2,
    'option_analysis': 2,
    'deep_report': 0,               # Deep Report 无免费额度
}
```

> **注意**：`check_and_deduct_credits()` 实际使用 `FREE_USER_DAILY_QUOTA`（共享 2 次），而非按服务类型分别计算。

**DailyQueryCount 模型追踪：**

- 以 `(user_id, date)` 为维度记录当日已用次数
- `date` 使用 `datetime.now().date()`（服务器本地时间）
- `reset_time` 字段记录第二天零点，用于前端倒计时展示
- 每日首次请求时自动创建记录（`query_count=amount`）

### 4.2 付费额度（CreditLedger FIFO）

**消费策略：**

1. 按 `expires_at ASC NULLS LAST` 排序 -- 先到期的先消费，永久有效的最后
2. `with_for_update()` 行级锁 -- 防止并发扣减导致超卖
3. 如果行锁不被支持（如 SQLite），fallback 到普通查询
4. 跳过 `expires_at <= utcnow()` 的过期记录
5. 单次扣减只从第一条记录扣（`.first()`），不跨行拆分

**额度来源（`CreditSource` enum）：**

| 值 | 说明 | 有效期 |
|------|------|--------|
| `subscription` | 订阅发放 | 月付 30 天 / 年付 365 天 |
| `top_up` | 加油包购买 | 90 天 |
| `referral` | 推荐奖励 | 90 天 |
| `system_grant` | 系统赠送 | 由管理员指定 |
| `refund` | 退款补发 | 由管理员指定 |

### 4.3 额度发放

**订阅额度发放规则：**

- **唯一入口**：`handle_invoice_payment_succeeded()` -- 由 `invoice.payment_succeeded` webhook 触发
- **幂等去重**：以 `stripe_invoice_id` 为唯一键，Transaction 表 unique 约束
- **首次订阅**：`billing_reason='subscription_create'` → 发放额度 + 检查推荐奖励
- **续费**：`billing_reason='subscription_cycle'` → 发放新周期额度
- **升级**：`billing_reason='subscription_update'` → 跳过（由 `upgrade_subscription` 方法处理）

**加油包额度发放：**

- 在 `handle_checkout_completed()` 中直接处理（Top-up 不产生 invoice）
- 幂等检查：`payment_intent_id` 去重

---

## 5. Webhook 处理

文件：`app/api/payment.py`，第 51-133 行

### 5.1 签名验证

使用 `stripe.Webhook.construct_event(request.data, Stripe-Signature header, STRIPE_WEBHOOK_SECRET)` 验证。签名无效 → 400；密钥未配置 → 500。

### 5.2 事件处理映射

| Stripe 事件 | 处理方法 | 核心作用 |
|-------------|----------|----------|
| `checkout.session.completed` | `handle_checkout_completed()` | 创建 Subscription 记录（订阅）或发放额度（Top-up） |
| `invoice.payment_succeeded` / `invoice.paid` | `handle_invoice_payment_succeeded()` | **发放订阅额度（核心入口）** |
| `customer.subscription.updated` | 仅 log | 记录订阅更新日志 |
| `customer.subscription.deleted` | 内联处理 | 将 Subscription.status 设为 `'canceled'` |
| `customer.subscription.created` | 仅 log | 记录订阅创建日志 |

### 5.3 Webhook 时序与容错

```
Stripe 发送 checkout.session.completed
  └─ 创建 Subscription 记录

Stripe 发送 invoice.payment_succeeded (可能先于或后于上一事件)
  ├─ Subscription 记录已存在 → 直接使用
  └─ Subscription 记录不存在 → 从 Stripe API 获取信息创建
      └─ 通过 stripe.Subscription.retrieve() + customer → user 映射
```

> Webhook 事件到达顺序不保证，`handle_invoice_payment_succeeded` 包含 fallback 逻辑处理 Subscription 记录不存在的情况。

---

## 6. 升级/取消流程

### 6.1 升级订阅

方法：`upgrade_subscription(user_id, new_price_key)`，第 714-874 行

**流程：**

1. 查找用户活跃订阅
2. 调用 `is_upgrade()` 验证方向（仅允许升级，不允许降级）
3. `stripe.Subscription.modify()` 更新 price
   - `proration_behavior='always_invoice'` -- 立即生成差价发票
   - `payment_behavior='allow_incomplete'` -- 允许不完整付款
4. 获取最新 invoice，尝试 finalize + pay
5. 如有实际付款 → 创建 Transaction 记录
6. 更新本地 Subscription 记录（plan_tier, period_start/end）
7. **发放新套餐满额额度**（升级福利：旧额度保留 + 新额度全额发放）

**Stripe Proration 计算：** `新订阅金额 - 旧订阅剩余时间 credit = 实际收取差价`

### 6.2 取消订阅

方法：`cancel_subscription(user_id)`，第 876-914 行

- 调用 `stripe.Subscription.modify(cancel_at_period_end=True)` -- 周期结束后取消，非立即取消
- 不退款，已发放额度保留至过期，用户可继续使用至周期结束
- Stripe 在周期结束时自动发送 `customer.subscription.deleted` 事件

---

## 7. `@check_quota` 装饰器

文件：`app/utils/decorators.py`，第 104-245 行

**职责**：将认证和配额检查合并为单个装饰器，替代 `@require_auth` + 手动额度检查。

```python
@check_quota(service_type=ServiceType.STOCK_ANALYSIS.value, amount=1)
def analyze_stock():
    # g.user_id 已设置
    # g.quota_info 包含额度信息
    # 额度已扣减
    ...
```

**处理流程：**

1. **认证**（同 `@require_auth`）：验证 JWT token，设置 `g.user_id`，自动创建本地 User
2. **提取 ticker**：依次尝试 JSON body → URL path args → query params
3. **扣减额度**：调用 `PaymentService.check_and_deduct_credits()`
4. **失败** → 返回 `402`，body 含 `code: 'INSUFFICIENT_CREDITS'`
5. **成功** → 注入 `g.quota_info`（`is_free`, `free_remaining`, `free_quota`, `remaining_credits`）

**辅助函数 `check_and_deduct_quota()`**（第 13-48 行）：独立函数版本（非装饰器），返回 dict 而非 tuple。

---

## 8. 安全机制

### 8.1 Webhook 签名验证

- 使用 `stripe.Webhook.construct_event()` 验证每个 webhook 请求的签名
- `STRIPE_WEBHOOK_SECRET` 未配置时直接返回 500，拒绝处理

### 8.2 幂等性保障

| 场景 | 幂等键 | 机制 |
|------|--------|------|
| 订阅 invoice | `stripe_invoice_id` | Transaction 表 unique 约束 + 查重 |
| Top-up checkout | `stripe_payment_intent_id` | Transaction 表 unique 约束 + 查重 |
| 升级 invoice | `billing_reason='subscription_update'` | `handle_invoice_payment_succeeded` 直接跳过 |

### 8.3 并发安全

- `check_and_deduct_credits()`：`CreditLedger.query.with_for_update()` 行级锁
- `DailyQueryCount` 更新：`with_for_update()` 行级锁
- 两处均有 fallback：行锁不支持时（如 SQLite）退化为普通查询
- Transaction 创建在额度发放之前 `flush()`，确保幂等键先写入

### 8.4 Stripe 配置安全

- `stripe.api_key` 和所有 Price ID 从环境变量读取，不硬编码
- `stripe.api_key` 为空时，所有支付方法返回错误提示而非异常

---

## 9. 数据模型

文件：`app/models.py`

### 9.1 Subscription（第 172-184 行，表名 `subscriptions`）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | Integer | PK | 自增主键 |
| `user_id` | String(36) | FK, index | 关联 User |
| `stripe_subscription_id` | String(255) | unique | Stripe 订阅 ID |
| `plan_tier` | String(50) | | `'plus'` / `'pro'` |
| `status` | String(50) | | `'active'` / `'canceled'` / `'past_due'` / ... |
| `current_period_start` | DateTime | | 当前周期开始 |
| `current_period_end` | DateTime | | 当前周期结束 |
| `cancel_at_period_end` | Boolean | default=False | 是否周期结束后取消 |

### 9.2 Transaction（第 186-198 行，表名 `transactions`）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | Integer | PK | 自增主键 |
| `user_id` | String(36) | FK, index | 关联 User |
| `stripe_payment_intent_id` | String(255) | unique, nullable | 一次性付款 ID |
| `stripe_checkout_session_id` | String(255) | unique, nullable | Checkout Session ID |
| `stripe_invoice_id` | String(255) | **unique, index** | **幂等性检查核心字段** |
| `amount` | Integer | | 金额，单位 cents（美分） |
| `currency` | String(10) | default='cny' | 币种 |
| `status` | String(50) | | `'succeeded'` / `'pending'` / `'failed'` |

### 9.3 CreditLedger（第 200-212 行，表名 `credit_ledger`）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | Integer | PK | 自增主键 |
| `user_id` | String(36) | FK, index | 关联 User |
| `service_type` | String(50) | default='stock_analysis' | 服务类型 |
| `source` | String(50) | | `'subscription'` / `'top_up'` / `'referral'` / ... |
| `amount_initial` | Integer | | 初始发放额度 |
| `amount_remaining` | Integer | | 当前剩余额度（FIFO 扣减） |
| `expires_at` | DateTime | nullable | `None` = 永久有效 |
| `subscription_id` | Integer | FK, nullable | 关联 Subscription |

### 9.4 UsageLog（第 214-224 行，表名 `usage_logs`）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | Integer | PK | 自增主键 |
| `user_id` | String(36) | FK, index | 关联 User |
| `credit_ledger_id` | Integer | FK, nullable | 关联 CreditLedger；`None` = 免费额度 |
| `service_type` | String(50) | | 服务类型 |
| `ticker` | String(20) | nullable | 股票代码 |
| `amount_used` | Integer | default=1 | 消耗次数 |

### 9.5 DailyQueryCount（第 93-99 行）

| 字段 | 类型 | 说明 |
|------|------|------|
| `user_id` | String(36), FK, index | 关联 User |
| `date` | Date | 查询日期 |
| `query_count` | Integer, default=0 | 当日已用次数 |
| `max_queries` | Integer, default=5 | 历史字段，实际使用 `FREE_USER_DAILY_QUOTA` |
| `reset_time` | DateTime | 第二天零点 |

### 9.6 Enum 定义

| Enum | 值 |
|------|------|
| `ServiceType` | `stock_analysis`, `option_analysis`, `deep_report` |
| `CreditSource` | `subscription`, `top_up`, `referral`, `system_grant`, `refund` |
| `PlanTier` | `free`, `plus`, `pro` |
| `SubscriptionStatus` | `active`, `canceled`, `past_due`, `unpaid`, `trialing` |
| `TransactionStatus` | `pending`, `succeeded`, `failed` |

---

## 10. API 端点

文件：`app/api/payment.py`，437 行

```python
payment_bp = Blueprint('payment', __name__, url_prefix='/api/payment')
```

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| POST | `/api/payment/create-checkout-session` | `@require_auth` | 创建 Stripe Checkout Session |
| POST | `/api/payment/webhook` | 无（Stripe 签名验证） | Webhook 回调处理 |
| POST | `/api/payment/check-quota` | `@require_auth` | 检查额度是否足够（不扣减） |
| GET  | `/api/payment/credits` | `@require_auth` | 获取用户额度信息 |
| GET  | `/api/payment/transactions` | `@require_auth` | 分页获取交易历史 |
| GET  | `/api/payment/usage-history` | `@require_auth` | 分页获取使用记录 |
| GET  | `/api/payment/pricing` | 无 | 获取定价信息 |
| POST | `/api/payment/upgrade` | `@require_auth` | 升级订阅 |
| POST | `/api/payment/cancel` | `@require_auth` | 取消订阅 |
| GET  | `/api/payment/upgrade-options` | `@require_auth` | 获取可升级选项 |
| POST | `/api/payment/customer-portal` | `@require_auth` | 创建 Stripe Customer Portal Session |

---

## 11. 文件路径清单

| 文件 | 行数 | 职责 |
|------|------|------|
| `app/services/payment_service.py` | 947 | PaymentService 类，14 个 @classmethod |
| `app/api/payment.py` | 437 | Payment Blueprint，11 个 API 端点 |
| `app/utils/decorators.py` | 245 | `@check_quota` 装饰器、`check_and_deduct_quota()` 函数、`@db_retry` |
| `app/models.py` | 427 | Subscription (172-184), Transaction (186-198), CreditLedger (200-212), UsageLog (214-224), DailyQueryCount (93-99), Enums (8-35) |

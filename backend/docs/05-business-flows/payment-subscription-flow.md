# 支付与订阅业务流程

> 本文档描述 Stripe 支付集成的完整业务流程，包括订阅、升级、取消和加油包购买。

## 1. 流程概述

系统使用 **Stripe** 作为支付网关，支持以下操作：

| 操作 | 入口 | Stripe 模式 |
|------|------|-------------|
| 新订阅 | `create_checkout_session` | Checkout Session (subscription) |
| 升级订阅 | `upgrade_subscription` | Subscription.modify (proration) |
| 取消订阅 | `cancel_subscription` | cancel_at_period_end=True |
| 加油包充值 | `create_checkout_session` | Checkout Session (payment) |

### 套餐配置

| 计划 | 月额度 | 年额度 |
|------|--------|--------|
| Plus | 1,000 次 | 12,000 次 |
| Pro | 5,000 次 | 60,000 次 |
| Top-up 加油包 | 100 次 (90 天有效) | - |

## 2. 新订阅流程

```mermaid
sequenceDiagram
    participant FE as Frontend
    participant BE as Backend
    participant ST as Stripe
    participant DB as Database

    FE->>BE: POST /api/payment/create-checkout<br/>{price_key: "plus_monthly", success_url, cancel_url}
    BE->>BE: 检查: 是否已有活跃订阅?
    alt 已有活跃订阅
        BE-->>FE: 400 "请使用升级功能或先取消当前订阅"
    end

    BE->>DB: 查询 User → stripe_customer_id
    alt 无 Stripe Customer
        BE->>ST: stripe.Customer.create(email, metadata)
        ST-->>BE: customer.id
        BE->>DB: UPDATE User SET stripe_customer_id
    end

    BE->>ST: stripe.checkout.Session.create(<br/>  customer, price, mode='subscription',<br/>  metadata={user_id, price_key})
    ST-->>BE: checkout_session (url)
    BE-->>FE: {checkout_url}

    FE->>ST: 重定向到 Stripe Checkout 页面
    Note over FE,ST: 用户完成支付

    ST->>BE: Webhook: checkout.session.completed
    BE->>BE: handle_checkout_completed()
    BE->>ST: stripe.Subscription.retrieve(subscription_id)
    BE->>DB: INSERT Subscription(user_id, stripe_subscription_id,<br/>  plan_tier, status='active', period_start, period_end)
    Note over BE: 不在此处发放额度!<br/>额度在 invoice.payment_succeeded 中发放

    ST->>BE: Webhook: invoice.payment_succeeded
    BE->>BE: handle_invoice_payment_succeeded()
    BE->>BE: 幂等性检查: Transaction.query(stripe_invoice_id)
    BE->>DB: INSERT Transaction(stripe_invoice_id, amount, status)
    BE->>DB: INSERT CreditLedger(amount=1000, source='subscription',<br/>  expires_at=+30days)
    Note over BE: 首次订阅检查邀请奖励
    alt 有推荐人
        BE->>DB: INSERT CreditLedger(referrer_id, amount=100,<br/>  source='referral', expires_at=+90days)
    end
```

## 3. 订阅升级流程

```mermaid
sequenceDiagram
    participant FE as Frontend
    participant BE as Backend
    participant ST as Stripe
    participant DB as Database

    FE->>BE: POST /api/payment/upgrade<br/>{new_price_key: "pro_monthly"}
    BE->>DB: 查询当前活跃 Subscription
    BE->>BE: get_current_price_key() → "plus_monthly"
    BE->>BE: is_upgrade("plus_monthly" → "pro_monthly")?
    Note over BE: PRICE_TIER_ORDER:<br/>plus_monthly(1) < plus_yearly(2)<br/>< pro_monthly(3) < pro_yearly(4)

    alt 非升级 (降级)
        BE-->>FE: 400 "只支持升级，不支持降级"
    end

    BE->>ST: stripe.Subscription.modify(<br/>  items=[{price: new_price}],<br/>  proration_behavior='always_invoice')
    Note over ST: Stripe 自动计算补差价:<br/>新价格 - 旧订阅剩余时间 credit
    ST-->>BE: updated_subscription + latest_invoice

    BE->>ST: stripe.Invoice.retrieve(latest_invoice_id)
    alt Invoice 状态为 draft
        BE->>ST: stripe.Invoice.finalize_invoice()
    end
    alt Invoice 状态为 open
        BE->>ST: stripe.Invoice.pay()
    end

    alt 有实际付款 (amount_paid > 0)
        BE->>DB: INSERT Transaction(amount_paid, description="升级订阅")
    end

    BE->>DB: UPDATE Subscription(plan_tier='pro', period_end=...)
    BE->>DB: INSERT CreditLedger(amount=5000, source='subscription',<br/>  expires_at=+30days)
    Note over BE: 升级福利: 直接给新套餐满额度

    BE-->>FE: {success, new_plan, credits_added, current_period_end}
```

## 4. 取消订阅流程

```mermaid
sequenceDiagram
    participant FE as Frontend
    participant BE as Backend
    participant ST as Stripe
    participant DB as Database

    FE->>BE: POST /api/payment/cancel
    BE->>DB: 查询活跃 Subscription

    BE->>ST: stripe.Subscription.modify(<br/>  cancel_at_period_end=True)
    Note over ST: 不立即取消!<br/>当前周期结束后自动取消

    BE->>DB: UPDATE Subscription(cancel_at_period_end=True)
    BE-->>FE: {success, message: "订阅将在当前周期结束后取消",<br/>  cancel_at: "2026-03-01T00:00:00"}

    Note over ST: 周期结束时...
    ST->>BE: Webhook: customer.subscription.deleted
    BE->>DB: UPDATE Subscription(status='canceled')
    Note over BE: 已有额度保留到过期，不主动清除
```

## 5. 加油包 (Top-up) 流程

```mermaid
sequenceDiagram
    participant FE as Frontend
    participant BE as Backend
    participant ST as Stripe
    participant DB as Database

    FE->>BE: POST /api/payment/create-checkout<br/>{price_key: "topup_100"}
    BE->>ST: stripe.checkout.Session.create(<br/>  mode='payment', metadata={price_key: "topup_100"})
    ST-->>BE: checkout_session (url)
    BE-->>FE: {checkout_url}

    FE->>ST: 用户完成一次性付款
    ST->>BE: Webhook: checkout.session.completed

    BE->>BE: handle_checkout_completed()
    BE->>BE: 检测 price_key 包含 'topup'
    BE->>BE: 幂等性检查: Transaction.query(payment_intent_id)
    BE->>DB: INSERT Transaction(amount, status='succeeded')
    BE->>DB: INSERT CreditLedger(amount=100,<br/>  source='top_up', expires_at=+90days)
    Note over DB: 加油包: 100 次额度, 90 天有效

    BE-->>FE: (via Stripe success_url redirect)
```

## 6. 续费流程 (自动)

```mermaid
sequenceDiagram
    participant ST as Stripe
    participant BE as Backend
    participant DB as Database

    Note over ST: 订阅周期结束，Stripe 自动扣费
    ST->>BE: Webhook: invoice.payment_succeeded<br/>billing_reason='subscription_cycle'

    BE->>BE: handle_invoice_payment_succeeded()
    BE->>BE: 幂等性检查: Transaction.query(stripe_invoice_id)

    BE->>ST: stripe.Subscription.retrieve()
    BE->>BE: 判断年付/月付 (period_days > 60 → yearly)

    BE->>DB: UPDATE Subscription(period_start, period_end)
    BE->>DB: INSERT Transaction(description="订阅续费")
    BE->>DB: INSERT CreditLedger(amount=credits,<br/>  source='subscription', expires_at=+30/365days)
```

## 7. 幂等性设计

所有 webhook 处理都实现了幂等性，防止 Stripe 重复推送导致额度重复发放：

| Webhook | 幂等键 | 检查方式 |
|---------|--------|----------|
| checkout.session.completed (topup) | `payment_intent_id` | `Transaction.query(stripe_payment_intent_id)` |
| invoice.payment_succeeded | `invoice_id` | `Transaction.query(stripe_invoice_id)` |
| upgrade (invoice) | `payment_intent_id` | 升级方法内部处理，不经过 webhook |

**关键**: `invoice.payment_succeeded` 中 `billing_reason='subscription_update'` 的发票会被跳过，
因为升级逻辑在 `upgrade_subscription` 方法中已经完成了额度发放。

## 8. 异常处理

| 场景 | 处理策略 |
|------|----------|
| Stripe API Key 未配置 | 返回 "Stripe未配置" 错误 |
| 重复 checkout session | 幂等性检查，返回 "已处理" |
| Stripe Card Error | 记录日志，Invoice 保持 open 状态 |
| Webhook 顺序颠倒 | `invoice.payment_succeeded` 可以独立创建 Subscription |
| DB 写入失败 | `db.session.rollback()` 回滚 |
| 升级降级 | `is_upgrade()` 检查 `PRICE_TIER_ORDER`，降级返回错误 |

## 9. 相关文件

| 文件 | 说明 |
|------|------|
| `app/services/payment_service.py` | `PaymentService` 完整支付逻辑 |
| `app/models.py` | `Subscription`, `Transaction`, `CreditLedger` 模型 |
| `app/api/payment.py` | 支付 API 端点 |
| `app/config.py` | Stripe 环境变量配置 |

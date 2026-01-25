# AlphaGBM 订阅系统配置指南

> 最后更新：2026-01-25

## 一、定价方案

### 1.1 订阅计划

| 计划 | 月付价格 | 年付价格 | 月额度 | 年额度(一次性发放) |
|------|----------|----------|--------|-------------------|
| **Plus** | $58.80/月 | $588/年 (省17%) | 1,000次 | 12,000次 |
| **Pro** | $99.80/月 | $998/年 (省17%) | 5,000次 | 60,000次 |

### 1.2 额度加油包

| 包名 | 价格 | 额度 | 有效期 |
|------|------|------|--------|
| 100次包 | $4.99 | 100次 | 3个月 |

### 1.3 免费用户

- 每日免费额度：**10次**（股票分析和期权分析各自独立计算）
- 每日零点重置

---

## 二、Stripe Dashboard 配置步骤

### 2.1 创建产品 (Products)

在 Stripe Dashboard → Products → Add Product，创建以下产品：

#### 产品 1: AlphaGBM Plus
- Name: `AlphaGBM Plus`
- Description: `1000 AI分析次数/月，期权分析、股票分析`

在此产品下添加 2 个价格 (Prices)：

| Price Name | 金额 | 计费周期 | 获得的 Price ID |
|------------|------|----------|-----------------|
| Plus Monthly | $58.80 | Monthly, recurring | `price_xxx` → 填入 `STRIPE_PRICE_PLUS_MONTHLY` |
| Plus Yearly | $588.00 | Yearly, recurring | `price_xxx` → 填入 `STRIPE_PRICE_PLUS_YEARLY` |

#### 产品 2: AlphaGBM Pro
- Name: `AlphaGBM Pro`
- Description: `5000 AI分析次数/月，期权分析、反向查分、股票分析、投资回顾`

在此产品下添加 2 个价格：

| Price Name | 金额 | 计费周期 | 获得的 Price ID |
|------------|------|----------|-----------------|
| Pro Monthly | $99.80 | Monthly, recurring | `price_xxx` → 填入 `STRIPE_PRICE_PRO_MONTHLY` |
| Pro Yearly | $998.00 | Yearly, recurring | `price_xxx` → 填入 `STRIPE_PRICE_PRO_YEARLY` |

#### 产品 3: 额度加油包
- Name: `AlphaGBM Credits Top-up`
- Description: `100次AI分析额度，3个月有效`

添加 1 个价格：

| Price Name | 金额 | 计费周期 | 获得的 Price ID |
|------------|------|----------|-----------------|
| 100 Credits | $4.99 | One-time | `price_xxx` → 填入 `STRIPE_PRICE_TOPUP_100` |

### 2.2 配置 Webhook

在 Stripe Dashboard → Developers → Webhooks → Add Endpoint：

- **Endpoint URL**: `https://your-domain.com/api/payment/webhook`
- **Events to listen**:
  - `checkout.session.completed` - 首次订阅/购买完成
  - `invoice.payment_succeeded` - 订阅续费成功
  - `customer.subscription.deleted` - 订阅被删除
  - `customer.subscription.updated` - 订阅变更（升级/降级）

创建后，复制 **Signing Secret** → 填入 `STRIPE_WEBHOOK_SECRET`

### 2.3 ⚠️ 重要：配置 Proration 设置

**这是解决"升级不退款/补差价"问题的关键！**

在 Stripe Dashboard → Settings → Billing → Subscriptions：

1. **Proration behavior**: 选择 `Always invoice immediately`
2. **Prorations**: 确保启用 `Create prorations when subscription changes`

或者，在代码层面，确保升级时使用：
```python
stripe.Subscription.modify(
    subscription_id,
    items=[{'id': item_id, 'price': new_price_id}],
    proration_behavior='always_invoice',  # 立即计算差价并扣款
)
```

---

## 三、环境变量配置

在后端 `.env` 文件中配置：

```bash
# Stripe API Keys
STRIPE_SECRET_KEY=sk_live_xxx          # 生产环境用 sk_live_，测试用 sk_test_
STRIPE_WEBHOOK_SECRET=whsec_xxx        # Webhook 签名密钥

# Stripe Price IDs (从 Dashboard 复制)
STRIPE_PRICE_PLUS_MONTHLY=price_xxx    # Plus 月付
STRIPE_PRICE_PLUS_YEARLY=price_xxx     # Plus 年付
STRIPE_PRICE_PRO_MONTHLY=price_xxx     # Pro 月付
STRIPE_PRICE_PRO_YEARLY=price_xxx      # Pro 年付
STRIPE_PRICE_TOPUP_100=price_xxx       # 100次加油包
```

---

## 四、订阅变更逻辑

### 4.1 升级 (Upgrade) - 已实现

**场景**：Plus → Pro，或 月付 → 年付

**处理逻辑**：
1. 立即切换到新价格
2. Stripe 自动计算旧订阅剩余时间的价值（credit）
3. 新订阅扣除 credit 后的差价立即收取
4. 本地数据库立即刷新额度为新套餐额度

**代码**：`backend/app/services/payment_service.py` → `upgrade_subscription()`

```python
stripe.Subscription.modify(
    subscription_id,
    items=[{'id': item_id, 'price': new_price_id}],
    proration_behavior='always_invoice',  # 关键：立即扣差价
)
```

### 4.2 降级 (Downgrade) - 当前禁止

**场景**：Pro → Plus，或 年付 → 月付

**处理逻辑**：**当前系统不允许降级**，用户需联系客服或等待订阅到期后选择新计划。

如需支持降级（周期结束后生效）：
```python
stripe.Subscription.modify(
    subscription_id,
    items=[{'id': item_id, 'price': new_price_id}],
    proration_behavior='none',  # 不产生退款
    billing_cycle_anchor='unchanged',  # 保持原计费周期
)
# 并设置 cancel_at_period_end=False 后在 period_end 时生效
```

### 4.3 取消订阅 (Cancel) - 已实现

**处理逻辑**：
1. 设置订阅在周期结束时取消
2. 用户继续享受服务直到当前周期结束
3. 不退款

**代码**：`backend/app/services/payment_service.py` → `cancel_subscription()`

```python
stripe.Subscription.modify(
    subscription_id,
    cancel_at_period_end=True
)
```

---

## 五、额度发放逻辑

### 5.1 首次订阅

触发事件：`checkout.session.completed`

处理：
1. 创建本地 Subscription 记录
2. **不发放额度**（等待 invoice.payment_succeeded）

### 5.2 订阅续费 / 升级付款成功

触发事件：`invoice.payment_succeeded`

处理：
1. 根据 `price_id` 判断套餐类型
2. 发放对应额度到 CreditLedger

| Price ID | 发放额度 |
|----------|----------|
| plus_monthly | 1,000 |
| plus_yearly | 12,000 |
| pro_monthly | 5,000 |
| pro_yearly | 60,000 |

### 5.3 额度加油包

触发事件：`checkout.session.completed`（一次性付款）

处理：
1. 识别为 topup 类型
2. 直接发放 100 额度到 CreditLedger
3. 设置 3 个月有效期

---

## 六、数据库模型

### 6.1 Subscription 表

```python
class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'))
    stripe_subscription_id = db.Column(db.String(255))
    stripe_customer_id = db.Column(db.String(255))
    plan_type = db.Column(db.String(50))  # 'plus' / 'pro'
    billing_cycle = db.Column(db.String(20))  # 'monthly' / 'yearly'
    status = db.Column(db.String(50))  # 'active' / 'canceled' / 'past_due'
    current_period_start = db.Column(db.DateTime)
    current_period_end = db.Column(db.DateTime)
    cancel_at_period_end = db.Column(db.Boolean, default=False)
```

### 6.2 CreditLedger 表（额度账本）

```python
class CreditLedger(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'))
    credits = db.Column(db.Integer)  # 剩余额度
    service_type = db.Column(db.String(50))  # 'stock_analysis' / 'option_analysis'
    source = db.Column(db.String(50))  # 'subscription' / 'topup'
    expires_at = db.Column(db.DateTime)  # 过期时间
    created_at = db.Column(db.DateTime)
```

### 6.3 DailyQueryCount 表（每日免费额度）

```python
class DailyQueryCount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36))
    date = db.Column(db.Date)  # 日期
    query_count = db.Column(db.Integer, default=0)  # 已使用次数
```

---

## 七、故障排查

### 7.1 升级没有按比例退款/补差价

**可能原因**：
1. Stripe Dashboard 中 proration 设置未开启
2. 两个 Price 不属于同一个 Product（Stripe 建议同产品不同价格之间切换）
3. 代码中 `proration_behavior` 未设置为 `'always_invoice'`

**解决方案**：
1. 检查 Stripe Dashboard → Settings → Billing → Subscriptions → Proration behavior
2. 确保升级代码使用了 `proration_behavior='always_invoice'`
3. 查看 Stripe Dashboard → Customers → [用户] → Invoices，确认是否有 proration line items

### 7.2 额度重复发放

**可能原因**：
1. 同时处理了 `checkout.session.completed` 和 `invoice.payment_succeeded`

**解决方案**：
- 订阅额度只在 `invoice.payment_succeeded` 中发放
- 一次性购买（top-up）只在 `checkout.session.completed` 中发放

### 7.3 Webhook 未收到

**检查步骤**：
1. Stripe Dashboard → Developers → Webhooks → 查看事件日志
2. 确认 Endpoint URL 正确且可公网访问
3. 确认 `STRIPE_WEBHOOK_SECRET` 正确

---

## 八、前端价格展示

在 `frontend/src/pages/Pricing.tsx` 中的价格配置：

```typescript
// Plus 套餐
monthly: $58.80
yearly: $588 (相当于 $49/月，省17%)

// Pro 套餐
monthly: $99.80
yearly: $998 (相当于 $83.17/月，省17%)

// 加油包
100次: $4.99
```

---

## 九、API 接口列表

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/payment/pricing` | GET | 获取定价信息 |
| `/api/payment/create-checkout-session` | POST | 创建支付会话 |
| `/api/payment/webhook` | POST | Stripe 回调 |
| `/api/payment/credits` | GET | 获取用户额度 |
| `/api/payment/check-quota` | POST | 检查额度是否充足 |
| `/api/payment/upgrade` | POST | 升级订阅 |
| `/api/payment/cancel` | POST | 取消订阅 |
| `/api/payment/upgrade-options` | GET | 获取可升级选项 |
| `/api/payment/customer-portal` | POST | Stripe 客户门户 |
| `/api/payment/transactions` | GET | 交易历史 |
| `/api/payment/usage-history` | GET | 使用历史 |

---

## 十、测试清单

- [ ] 新用户订阅 Plus Monthly → 检查额度发放
- [ ] 新用户订阅 Pro Yearly → 检查一次性发放 60,000 额度
- [ ] Plus → Pro 升级 → 检查差价计算和额度刷新
- [ ] Monthly → Yearly 升级 → 检查差价计算
- [ ] 取消订阅 → 检查服务维持到周期结束
- [ ] 购买 Top-up → 检查 100 额度发放
- [ ] 免费用户每日 10 次限制
- [ ] 期权分析多 symbol 计数

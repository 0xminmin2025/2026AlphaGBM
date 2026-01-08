# 支付模块文档

## 📦 模块概述

AlphaGBM 支付模块是一个基于"点数/额度（Credits）"的账本系统，支持订阅制、一次性充值、复杂的配额有效期管理。

## 🎯 核心特性

### 1. 多种支付方式
- **订阅制**：Plus会员（¥399/月，1000次/月）、Pro会员（¥999/月，5000次/月）
- **一次性充值**：额度加油包（100次¥29，3个月有效，仅限付费用户）
- **邀请奖励**：邀请好友付费，获得100次查询（90天有效）

### 2. 灵活的额度管理
- **订阅额度**：每月自动发放，月底清零
- **充值额度**：3个月有效期（仅限付费用户购买）
- **赠送额度**：3个月有效期
- **每日免费**：股票分析每天2次，期权分析每天1次

### 3. FIFO扣费逻辑
系统按照以下优先级扣除额度：
1. 当日免费额度（每日重置）
2. 即将过期的赠送额度（如邀请奖励）
3. 订阅月度额度（月底清零）
4. 充值额度（永久有效）

### 4. 服务类型分离
- **股票分析** (`stock_analysis`)
- **期权分析** (`option_analysis`)
- **深度研报** (`deep_report`)

## 🏗️ 架构设计

### 数据库模型

```
Users (扩展)
├── stripe_customer_id: Stripe客户ID
└── referrer_id: 邀请人ID

Subscriptions
├── stripe_subscription_id: Stripe订阅ID
├── plan_tier: 计划类型 (plus/pro)
└── status: 订阅状态

Transactions (幂等性控制)
├── stripe_payment_intent_id: 支付ID（唯一索引）
└── status: 交易状态

CreditLedger (额度账本)
├── amount_initial: 初始额度
├── amount_remaining: 剩余额度
├── expires_at: 过期时间
└── source: 来源 (subscription/top_up/referral/free_daily)

UsageLog (消耗记录)
├── credit_ledger_id: 关联的额度记录
└── amount_used: 消耗数量
```

### 核心流程

```
用户请求分析
  ↓
检查每日免费额度
  ↓ (如果已用完)
查找有效额度 (FIFO)
  ↓
扣减额度 (原子操作)
  ↓
记录使用日志
  ↓
执行分析
```

## 🔌 API接口

### 1. 创建支付会话

```http
POST /api/payment/create-checkout-session
Authorization: Bearer <token>
Content-Type: application/json

{
  "price_key": "plus_monthly",  // 或 "topup_100"
  "success_url": "https://...",
  "cancel_url": "https://..."
}
```

**响应**:
```json
{
  "session_id": "cs_...",
  "checkout_url": "https://checkout.stripe.com/..."
}
```

### 2. 查询用户额度

```http
GET /api/payment/credits?service_type=stock_analysis
Authorization: Bearer <token>
```

**响应**:
```json
{
  "total_credits": 1250,
  "subscription": {
    "has_subscription": true,
    "plan_tier": "plus",
    "status": "active",
    "current_period_end": "2024-02-01T00:00:00"
  },
  "daily_free": {
    "quota": 2,
    "used": 1,
    "remaining": 1
  }
}
```

### 3. 获取定价信息

```http
GET /api/payment/pricing
```

**响应**: 包含所有计划和加油包的定价信息

### 4. Webhook回调

```http
POST /api/payment/webhook
Stripe-Signature: <signature>
```

处理Stripe事件：
- `checkout.session.completed`: 支付完成
- `invoice.payment_succeeded`: 订阅续费
- `customer.subscription.deleted`: 订阅取消

## 💻 代码使用

### 在API中使用装饰器

```python
from payment_module.decorators import check_quota

@app.route('/api/analyze', methods=['POST'])
@jwt_required()
@check_quota(service_type='stock_analysis', amount=1)
def analyze():
    # 原有分析逻辑
    ...
```

### 手动检查额度

```python
from payment_module import PaymentService

# 检查并扣减
success, message, remaining = payment_service.check_and_deduct_credits(
    user_id=user_id,
    service_type='stock_analysis',
    amount=1
)

if not success:
    return jsonify({'error': message}), 402
```

## 🔐 安全特性

1. **幂等性控制**：使用 `stripe_payment_intent_id` 防止重复处理
2. **并发控制**：使用数据库行锁 `with_for_update()` 防止超卖
3. **Webhook验证**：验证Stripe签名确保请求来源
4. **事务处理**：所有操作在事务中，失败自动回滚

## 📊 额度扣减逻辑（FIFO）

系统按照以下顺序查找可用额度：

1. **每日免费额度**：优先使用，每天重置
2. **即将过期的额度**：按过期时间升序（先过期的先用）
3. **永久有效额度**：最后使用

查询SQL示例：
```sql
SELECT * FROM credit_ledger
WHERE user_id = ? 
  AND service_type = ?
  AND amount_remaining > 0
  AND (expires_at IS NULL OR expires_at > NOW())
ORDER BY expires_at ASC NULLS LAST
LIMIT 1
FOR UPDATE  -- 行锁
```

## 🧪 测试

### 本地测试Webhook

使用Stripe CLI：

```bash
# 安装Stripe CLI
brew install stripe/stripe-cli/stripe

# 登录
stripe login

# 转发Webhook到本地
stripe listen --forward-to localhost:5002/api/payment/webhook

# 触发测试事件
stripe trigger checkout.session.completed
```

### 测试额度扣减

```python
# 测试脚本
from app import app, db
from payment_module import PaymentService, create_payment_models

with app.app_context():
    # 创建测试额度
    payment_service.add_credits(
        user_id=1,
        amount=100,
        source='top_up',
        service_type='stock_analysis',
        days_valid=30
    )
    
    # 测试扣减
    success, msg, remaining = payment_service.check_and_deduct_credits(
        user_id=1,
        service_type='stock_analysis',
        amount=1
    )
    print(f"成功: {success}, 剩余: {remaining}")
```

## 📝 配置说明

### 环境变量

```env
# Stripe配置
STRIPE_SECRET_KEY=sk_test_...  # 或 sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Stripe价格ID（在Stripe Dashboard创建产品后获取）
STRIPE_PRICE_PLUS_MONTHLY=price_...
STRIPE_PRICE_PLUS_YEARLY=price_...
STRIPE_PRICE_PRO_MONTHLY=price_...
STRIPE_PRICE_PRO_YEARLY=price_...
STRIPE_PRICE_TOPUP_100=price_...
STRIPE_PRICE_TOPUP_500=price_...
```

### Stripe Dashboard设置

1. **创建产品**：
   - Plus月度订阅：¥399/月
   - Plus年度订阅：¥3990/年
   - Pro月度订阅：¥999/月
   - Pro年度订阅：¥9990/年
   - 额度加油包100次：¥29
   - 额度加油包500次：¥129

2. **配置Webhook**：
   - URL: `https://yourdomain.com/api/payment/webhook`
   - 事件：`checkout.session.completed`, `invoice.payment_succeeded`, `customer.subscription.deleted`

3. **启用支付方式**：
   - 信用卡
   - 支付宝（Alipay）
   - 微信支付（WeChat Pay）

## 🚀 部署注意事项

1. **HTTPS必需**：Webhook URL必须是HTTPS
2. **测试环境**：开发时使用测试密钥，生产环境使用正式密钥
3. **时区**：所有时间使用UTC存储
4. **监控**：建议监控Webhook处理失败的情况
5. **备份**：定期备份交易和额度数据

## 📚 相关文档

- [集成指南](./integration_guide.md)
- [Stripe官方文档](https://stripe.com/docs)
- [Stripe Webhook指南](https://stripe.com/docs/webhooks)

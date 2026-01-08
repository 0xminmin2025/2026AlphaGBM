# 支付模块集成指南

## 📋 概述

本支付模块基于"点数/额度（Credits）"账本系统，支持：
- 订阅制（Plus/Pro会员）
- 一次性充值（额度加油包）
- 复杂的配额有效期管理（订阅月清零、充值永久有效、赠送3个月有效）
- 股票分析、期权分析、深度研报分开收费

## 🏗️ 架构设计

### 核心组件

1. **数据库模型** (`models.py`)
   - `Subscription`: 订阅记录
   - `Transaction`: 支付流水（幂等性控制）
   - `CreditLedger`: 额度账本（FIFO扣减）
   - `UsageLog`: 消耗流水

2. **支付服务** (`payment_service.py`)
   - Stripe支付集成
   - 额度发放逻辑
   - 额度扣减逻辑（FIFO）
   - 每日免费额度管理

3. **路由** (`routes.py`)
   - 创建支付会话
   - Webhook回调处理
   - 额度查询API

4. **装饰器** (`decorators.py`)
   - `@check_quota`: 自动检查并扣减额度

## 🔧 集成步骤

### 1. 安装依赖

```bash
pip install stripe
```

### 2. 更新User模型

在 `app.py` 中扩展User模型：

```python
class User(db.Model):
    # ... 现有字段 ...
    
    # 新增字段
    stripe_customer_id = db.Column(db.String(255), index=True, nullable=True)
    referrer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # 关联
    referrer = db.relationship('User', remote_side=[id], backref='referrals')
```

### 3. 创建数据库表

在 `app.py` 的初始化函数中：

```python
from payment_module import create_payment_models

# 创建支付模型
PaymentModels = create_payment_models(db)
Subscription = PaymentModels['Subscription']
Transaction = PaymentModels['Transaction']
CreditLedger = PaymentModels['CreditLedger']
UsageLog = PaymentModels['UsageLog']

# 创建表
with app.app_context():
    db.create_all()
```

### 4. 初始化支付服务

在 `app.py` 中：

```python
from payment_module import PaymentService, payment_bp, init_payment_routes, init_decorators
from payment_module.decorators import check_quota

# 初始化支付服务
payment_service = PaymentService(
    db=db,
    User=User,
    Subscription=Subscription,
    Transaction=Transaction,
    CreditLedger=CreditLedger,
    UsageLog=UsageLog,
    DailyQueryCount=DailyQueryCount
)

# 初始化路由
init_payment_routes(payment_service, get_user_info_from_token)

# 初始化装饰器
init_decorators(payment_service, get_user_info_from_token)

# 注册蓝图
app.register_blueprint(payment_bp)
```

### 5. 在分析API中使用装饰器

修改 `/api/analyze` 路由：

```python
@app.route('/api/analyze', methods=['POST'])
@jwt_required()
@check_quota(service_type='stock_analysis', amount=1)  # 添加装饰器
def analyze():
    # ... 原有逻辑 ...
```

### 6. 配置环境变量

在 `.env` 文件中添加：

```env
# Stripe配置
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Stripe价格ID（在Stripe后台创建产品后填入）
STRIPE_PRICE_PLUS_MONTHLY=price_...
STRIPE_PRICE_PLUS_YEARLY=price_...
STRIPE_PRICE_PRO_MONTHLY=price_...
STRIPE_PRICE_PRO_YEARLY=price_...
STRIPE_PRICE_TOPUP_100=price_...
STRIPE_PRICE_TOPUP_500=price_...
```

### 7. 配置Webhook

在Stripe Dashboard中：
1. 进入 Webhooks 设置
2. 添加端点：`https://yourdomain.com/api/payment/webhook`
3. 选择事件：
   - `checkout.session.completed`
   - `invoice.payment_succeeded`
   - `customer.subscription.deleted`
4. 复制 Webhook Secret 到 `.env`

## 📊 数据库迁移

如果已有数据库，需要执行迁移：

```python
# 迁移脚本示例
from app import app, db
from payment_module import create_payment_models

with app.app_context():
    PaymentModels = create_payment_models(db)
    db.create_all()
    print("支付模块表创建完成")
```

## 🎯 使用示例

### 前端：创建支付会话

```javascript
async function checkout(priceKey) {
    const response = await fetch('/api/payment/create-checkout-session', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
            price_key: priceKey,  // 'plus_monthly', 'topup_100' 等
            success_url: window.location.origin + '/dashboard?success=true',
            cancel_url: window.location.origin + '/pricing?canceled=true'
        })
    });
    
    const data = await response.json();
    if (data.session_id) {
        // 跳转到Stripe支付页面
        window.location.href = data.checkout_url;
    }
}
```

### 查询用户额度

```javascript
async function getCredits() {
    const response = await fetch('/api/payment/credits', {
        headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
    });
    const data = await response.json();
    console.log('剩余额度:', data.total_credits);
    console.log('订阅信息:', data.subscription);
    console.log('每日免费:', data.daily_free);
}
```

## 🔒 安全注意事项

1. **幂等性**：所有Webhook处理都检查 `stripe_payment_intent_id`，防止重复处理
2. **并发控制**：使用 `with_for_update()` 行锁防止超卖
3. **Webhook验证**：必须验证Stripe签名
4. **事务处理**：所有数据库操作都在事务中，失败时回滚

## 📈 扩展功能

### 添加新的服务类型

1. 在 `models.py` 的 `ServiceType` 枚举中添加
2. 在 `DAILY_FREE_QUOTA` 中配置免费额度
3. 在API中使用对应的 `service_type`

### 添加新的订阅计划

1. 在Stripe后台创建产品和价格
2. 在 `.env` 中添加价格ID
3. 在 `PLAN_CONFIG` 中配置额度

### 自定义有效期规则

修改 `add_credits()` 函数的 `days_valid` 参数逻辑

## 🐛 调试技巧

1. **查看额度流水**：
```python
ledgers = CreditLedger.query.filter_by(user_id=1).all()
for ledger in ledgers:
    print(f"{ledger.source}: {ledger.amount_remaining}/{ledger.amount_initial}, 过期: {ledger.expires_at}")
```

2. **查看使用日志**：
```python
logs = UsageLog.query.filter_by(user_id=1).order_by(UsageLog.created_at.desc()).limit(10).all()
```

3. **测试Webhook**：使用Stripe CLI
```bash
stripe listen --forward-to localhost:5002/api/payment/webhook
stripe trigger checkout.session.completed
```

## 📝 注意事项

1. **Stripe测试模式**：开发时使用测试密钥，生产环境使用正式密钥
2. **Webhook URL**：生产环境需要HTTPS
3. **时区处理**：所有时间使用UTC存储
4. **额度过期**：建议添加定时任务清理过期额度

# 支付模块集成完成说明

## ✅ 已完成的集成

### 1. 数据库模型扩展
- ✅ User模型已添加 `stripe_customer_id` 和 `referrer_id` 字段
- ✅ 支付模块的4个表已创建（Subscription, Transaction, CreditLedger, UsageLog）

### 2. 后端集成
- ✅ 支付模块已集成到 `app.py`
- ✅ 在 `initialize_app()` 中初始化支付服务
- ✅ `/api/analyze` 路由已添加 `@check_quota` 装饰器
- ✅ 支付API路由已注册（`/api/payment/*`）

### 3. 前端页面
- ✅ 创建了定价页面 `/pricing`
- ✅ 包含订阅计划（免费版、Plus、Pro）
- ✅ 包含额度加油包（100次、500次）
- ✅ 支持月度/年度切换
- ✅ 显示用户额度信息

## 📋 使用前准备

### 1. 安装依赖
```bash
pip install stripe
```

### 2. 配置环境变量
在 `.env` 文件中添加：
```env
# Stripe配置（测试环境）
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Stripe价格ID（在Stripe Dashboard创建产品后获取）
STRIPE_PRICE_PLUS_MONTHLY=price_...
STRIPE_PRICE_PLUS_YEARLY=price_...
STRIPE_PRICE_PRO_MONTHLY=price_...
STRIPE_PRICE_PRO_YEARLY=price_...
STRIPE_PRICE_TOPUP_100=price_...
STRIPE_PRICE_TOPUP_500=price_...
```

### 3. 运行数据库迁移（如果需要）
```bash
python payment_module/migration_script.py
```

### 4. 在Stripe Dashboard配置
1. 创建产品和价格
2. 配置Webhook端点：`https://yourdomain.com/api/payment/webhook`
3. 选择事件：`checkout.session.completed`, `invoice.payment_succeeded`, `customer.subscription.deleted`

## 🚀 启动服务器

```bash
python app.py
```

访问：
- 主页：http://localhost:5002
- 定价页面：http://localhost:5002/pricing

## 📝 注意事项

1. **Stripe测试模式**：开发时使用测试密钥（`sk_test_`），生产环境使用正式密钥（`sk_live_`）
2. **Webhook URL**：生产环境必须是HTTPS
3. **前端Stripe公钥**：在 `pricing.html` 中需要更新Stripe公钥（`pk_test_...` 或 `pk_live_...`）
4. **额度扣减**：每次调用 `/api/analyze` 会自动检查并扣减额度
5. **免费额度**：每天2次股票分析免费，使用完后需要付费

## 🔍 测试流程

1. 启动服务器
2. 访问 `/pricing` 页面
3. 登录后可以看到额度信息
4. 点击"订阅"或"充值"按钮（需要配置Stripe）
5. 完成支付后，额度会自动到账
6. 使用股票分析功能时，会自动扣减额度

## 📊 API端点

- `GET /pricing` - 定价页面
- `POST /api/payment/create-checkout-session` - 创建支付会话
- `GET /api/payment/credits` - 查询用户额度
- `GET /api/payment/pricing` - 获取定价信息（JSON）
- `POST /api/payment/webhook` - Stripe Webhook回调

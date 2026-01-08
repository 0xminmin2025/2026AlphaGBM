# 支付请求失败 - 快速修复指南

## 问题诊断

如果点击订阅后出现"支付请求失败"，可能的原因：

### 1. 缺少stripe模块（最常见）
**症状**: 日志显示 `No module named 'stripe'`，API返回404

**解决方案**:
```bash
pip install stripe
```

### 2. Stripe未配置
**症状**: API返回错误，提示"Stripe未配置"

**解决方案**:
在 `.env` 文件中添加：
```env
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_PLUS_MONTHLY=price_...
STRIPE_PRICE_PLUS_YEARLY=price_...
STRIPE_PRICE_PRO_MONTHLY=price_...
STRIPE_PRICE_PRO_YEARLY=price_...
STRIPE_PRICE_TOPUP_100=price_...
STRIPE_PRICE_TOPUP_500=price_...
```

### 3. 支付模块未加载
**症状**: API返回404，日志显示"支付模块未加载"

**可能原因**:
- SQLAlchemy版本问题（`with_for_update`导入失败）
- 缺少依赖模块

**解决方案**:
1. 检查日志：`tail -20 logs/app.log | grep -i "支付\|payment"`
2. 如果看到 `with_for_update` 错误，代码已修复，重启服务器即可
3. 如果看到其他导入错误，安装缺失的依赖

### 4. 服务器未重启
**症状**: 修改代码后仍然报错

**解决方案**:
```bash
# 停止旧服务器
ps aux | grep "python.*app.py" | grep -v grep | awk '{print $2}' | xargs kill

# 启动新服务器
python3 app.py
```

## 测试步骤

1. **检查支付模块是否加载**:
   ```bash
   tail -20 logs/app.log | grep -i "支付模块"
   ```
   应该看到 "支付模块已加载" 或 "支付模块初始化成功"

2. **测试API端点**:
   ```bash
   curl -X POST http://localhost:5002/api/payment/create-checkout-session \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -d '{"price_key":"plus_monthly"}'
   ```

3. **检查浏览器控制台**:
   - 打开浏览器开发者工具（F12）
   - 查看Console标签页的错误信息
   - 查看Network标签页的请求详情

## 常见错误信息

| 错误信息 | 原因 | 解决方案 |
|---------|------|---------|
| `支付功能暂未启用` | 支付模块未加载 | 检查日志，安装依赖，重启服务器 |
| `请先登录` | 未登录或token过期 | 重新登录 |
| `Stripe未配置` | 缺少环境变量 | 配置 `.env` 文件 |
| `价格配置不存在` | Stripe价格ID未配置 | 在 `.env` 中添加价格ID |
| `404 Not Found` | 路由未注册 | 检查支付模块是否加载 |

## 完整配置检查清单

- [ ] 已安装 `stripe`: `pip install stripe`
- [ ] `.env` 文件包含 `STRIPE_SECRET_KEY`
- [ ] `.env` 文件包含所有价格ID
- [ ] 服务器已重启（加载最新代码）
- [ ] 日志显示"支付模块初始化成功"
- [ ] 用户已登录（有有效的JWT token）

## 如果仍然无法解决

1. 查看完整日志：`tail -50 logs/app.log`
2. 检查浏览器控制台的详细错误
3. 确认Stripe Dashboard中的产品和价格已创建
4. 确认使用的是正确的Stripe密钥（测试/生产）

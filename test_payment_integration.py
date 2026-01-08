"""
测试支付模块集成
检查代码是否可以正常导入和运行
"""
import sys
import os

print("=" * 60)
print("支付模块集成测试")
print("=" * 60)

# 1. 测试支付模块导入
print("\n1. 测试支付模块导入...")
try:
    from payment_module import create_payment_models, PaymentService
    print("   ✅ 支付模块导入成功")
except ImportError as e:
    print(f"   ⚠️  支付模块导入失败: {e}")
    print("   提示: 如果缺少stripe，这是正常的（开发环境）")

# 2. 测试app.py导入
print("\n2. 测试app.py导入...")
try:
    # 设置环境变量避免实际初始化
    os.environ['STRIPE_SECRET_KEY'] = 'sk_test_dummy'
    import app
    print("   ✅ app.py 导入成功")
except Exception as e:
    print(f"   ❌ app.py 导入失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 3. 检查路由
print("\n3. 检查路由...")
routes = [str(rule) for rule in app.app.url_map.iter_rules()]
payment_routes = [r for r in routes if '/payment' in r or '/pricing' in r]
if payment_routes:
    print("   ✅ 支付相关路由已注册:")
    for route in payment_routes:
        print(f"      - {route}")
else:
    print("   ⚠️  未找到支付相关路由（可能支付模块未加载）")

# 4. 检查模板
print("\n4. 检查模板文件...")
pricing_template = os.path.join('templates', 'pricing.html')
if os.path.exists(pricing_template):
    print(f"   ✅ 定价页面模板存在: {pricing_template}")
    size = os.path.getsize(pricing_template)
    print(f"      文件大小: {size} 字节")
else:
    print(f"   ❌ 定价页面模板不存在: {pricing_template}")

# 5. 检查User模型
print("\n5. 检查User模型扩展...")
if hasattr(app, 'User'):
    user_attrs = dir(app.User)
    if 'stripe_customer_id' in [attr for attr in user_attrs if not attr.startswith('_')]:
        print("   ✅ User模型已扩展（包含stripe_customer_id）")
    else:
        print("   ⚠️  User模型未找到stripe_customer_id字段")
else:
    print("   ⚠️  未找到User模型（可能SQLAlchemy未加载）")

print("\n" + "=" * 60)
print("测试完成！")
print("=" * 60)
print("\n📝 下一步:")
print("1. 安装stripe: pip install stripe")
print("2. 配置Stripe环境变量（.env文件）")
print("3. 运行数据库迁移: python payment_module/migration_script.py")
print("4. 启动服务器: python app.py")
print("5. 访问定价页面: http://localhost:5002/pricing")

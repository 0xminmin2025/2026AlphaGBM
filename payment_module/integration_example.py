"""
支付模块集成示例
展示如何将支付模块集成到现有的app.py中
"""
# 这个文件仅作为示例，不要直接运行

# ========== 在 app.py 中添加以下代码 ==========

# 1. 导入支付模块
from payment_module import (
    create_payment_models, 
    PaymentService, 
    payment_bp, 
    init_payment_routes,
    init_decorators
)
from payment_module.decorators import check_quota

# 2. 扩展User模型（在User类定义后添加字段）
# 注意：如果User表已存在，需要执行数据库迁移
class User(db.Model):
    # ... 现有字段 ...
    
    # 新增字段（如果还没有）
    stripe_customer_id = db.Column(db.String(255), index=True, nullable=True)
    referrer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # 关联
    referrer = db.relationship('User', remote_side=[id], backref='referrals')

# 3. 创建支付模型（在数据库初始化后）
PaymentModels = create_payment_models(db)
Subscription = PaymentModels['Subscription']
Transaction = PaymentModels['Transaction']
CreditLedger = PaymentModels['CreditLedger']
UsageLog = PaymentModels['UsageLog']

# 4. 初始化支付服务（在app创建后）
payment_service = PaymentService(
    db=db,
    User=User,
    Subscription=Subscription,
    Transaction=Transaction,
    CreditLedger=CreditLedger,
    UsageLog=UsageLog,
    DailyQueryCount=DailyQueryCount
)

# 5. 初始化路由和装饰器
init_payment_routes(payment_service, get_user_info_from_token)
init_decorators(payment_service, get_user_info_from_token)

# 6. 注册蓝图
app.register_blueprint(payment_bp)

# 7. 修改现有的分析API（添加装饰器）
@app.route('/api/analyze', methods=['POST'])
@jwt_required()
@check_quota(service_type='stock_analysis', amount=1)  # 添加这一行
def analyze():
    # ... 原有逻辑保持不变 ...
    pass

# 8. 创建数据库表（在应用初始化时）
def initialize_app():
    # ... 现有初始化逻辑 ...
    
    # 创建支付模块的表
    with app.app_context():
        db.create_all()
        logger.info("数据库表创建完成（包括支付模块）")

# ========== 数据库迁移脚本 ==========
# 如果User表已存在，需要添加新字段
# 可以创建一个迁移脚本：

"""
from app import app, db
from sqlalchemy import text

with app.app_context():
    # 检查字段是否存在
    inspector = db.inspect(db.engine)
    columns = [col['name'] for col in inspector.get_columns('user')]
    
    # 添加stripe_customer_id字段（如果不存在）
    if 'stripe_customer_id' not in columns:
        db.engine.execute(text('ALTER TABLE user ADD COLUMN stripe_customer_id VARCHAR(255)'))
        db.engine.execute(text('CREATE INDEX idx_user_stripe_customer ON user(stripe_customer_id)'))
        print("已添加 stripe_customer_id 字段")
    
    # 添加referrer_id字段（如果不存在）
    if 'referrer_id' not in columns:
        db.engine.execute(text('ALTER TABLE user ADD COLUMN referrer_id INTEGER'))
        db.engine.execute(text('CREATE INDEX idx_user_referrer ON user(referrer_id)'))
        print("已添加 referrer_id 字段")
    
    # 创建支付模块的表
    PaymentModels = create_payment_models(db)
    db.create_all()
    print("支付模块表创建完成")
"""

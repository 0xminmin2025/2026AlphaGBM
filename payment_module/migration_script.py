"""
支付模块数据库迁移脚本
用于在现有数据库中添加支付相关表和字段
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from payment_module import create_payment_models
from sqlalchemy import text, inspect

def migrate_database():
    """执行数据库迁移"""
    with app.app_context():
        print("开始数据库迁移...")
        
        # 1. 检查并扩展User表
        print("\n1. 检查User表...")
        inspector = inspect(db.engine)
        
        try:
            columns = {col['name']: col for col in inspector.get_columns('user')}
            
            # 添加stripe_customer_id字段
            if 'stripe_customer_id' not in columns:
                print("  添加 stripe_customer_id 字段...")
                db.session.execute(text('ALTER TABLE user ADD COLUMN stripe_customer_id VARCHAR(255)'))
                db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_user_stripe_customer ON user(stripe_customer_id)'))
                db.session.commit()
                print("  ✅ stripe_customer_id 字段已添加")
            else:
                print("  ✅ stripe_customer_id 字段已存在")
            
            # 添加referrer_id字段
            if 'referrer_id' not in columns:
                print("  添加 referrer_id 字段...")
                db.session.execute(text('ALTER TABLE user ADD COLUMN referrer_id INTEGER'))
                db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_user_referrer ON user(referrer_id)'))
                db.session.commit()
                print("  ✅ referrer_id 字段已添加")
            else:
                print("  ✅ referrer_id 字段已存在")
                
        except Exception as e:
            print(f"  ⚠️ User表检查失败: {e}")
            print("  如果是SQLite，可能需要手动添加字段")
        
        # 2. 创建支付模块的表
        print("\n2. 创建支付模块表...")
        try:
            PaymentModels = create_payment_models(db)
            db.create_all()
            print("  ✅ 支付模块表创建完成")
            print("     - subscriptions")
            print("     - transactions")
            print("     - credit_ledger")
            print("     - usage_logs")
        except Exception as e:
            print(f"  ❌ 表创建失败: {e}")
            db.session.rollback()
            return False
        
        print("\n✅ 数据库迁移完成！")
        return True

if __name__ == '__main__':
    migrate_database()

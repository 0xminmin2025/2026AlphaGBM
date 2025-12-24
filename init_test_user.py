#!/usr/bin/env python3
"""
初始化测试用户
"""

from app import app, db, User
from werkzeug.security import generate_password_hash

def init_test_user():
    """创建测试用户"""
    with app.app_context():
        # 检查测试用户是否已存在
        test_user = User.query.filter_by(email='test@test.com').first()
        
        if test_user:
            print("✅ 测试用户已存在")
            print(f"   邮箱: {test_user.email}")
            print(f"   用户名: {test_user.username}")
            return
        
        # 创建测试用户
        test_user = User(
            username='testuser',
            email='test@test.com',
            is_email_verified=True  # 直接标记为已验证
        )
        test_user.set_password('test123')
        
        db.session.add(test_user)
        db.session.commit()
        
        print("✅ 测试用户创建成功！")
        print(f"   邮箱: test@test.com")
        print(f"   密码: test123")
        print(f"   用户ID: {test_user.id}")

if __name__ == '__main__':
    init_test_user()


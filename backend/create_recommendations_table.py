"""
创建每日期权推荐表
"""

import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import db, DailyRecommendation

def create_table():
    """创建 daily_recommendations 表"""
    app = create_app()

    with app.app_context():
        # 检查表是否已存在
        inspector = db.inspect(db.engine)
        if 'daily_recommendations' in inspector.get_table_names():
            print("表 daily_recommendations 已存在")
            return

        # 创建表
        DailyRecommendation.__table__.create(db.engine)
        print("表 daily_recommendations 创建成功")

if __name__ == '__main__':
    create_table()

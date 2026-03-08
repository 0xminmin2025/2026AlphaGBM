"""
迁移脚本：为 daily_query_count 表添加 service_type 列
"""
import os
import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import db

def migrate():
    """添加 service_type 列到 daily_query_count 表"""
    app = create_app()

    with app.app_context():
        # 检查列是否已存在
        result = db.session.execute(db.text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'daily_query_count'
            AND column_name = 'service_type'
        """))

        if result.fetchone():
            print("service_type 列已存在，检查是否需要清理重复数据...")
            db.session.commit()

            # 清理重复数据并添加唯一约束
            cleanup_and_add_constraint()
            return

        print("开始迁移：添加 service_type 列...")

        # 1. 添加 service_type 列（允许 NULL，稍后设置默认值）
        db.session.execute(db.text("""
            ALTER TABLE daily_query_count
            ADD COLUMN service_type VARCHAR(50)
        """))
        db.session.commit()
        print("✓ 添加 service_type 列")

        # 2. 更新现有记录的 service_type 为默认值
        db.session.execute(db.text("""
            UPDATE daily_query_count
            SET service_type = 'stock_analysis'
            WHERE service_type IS NULL
        """))
        db.session.commit()
        print("✓ 更新现有记录的 service_type")

        # 3. 设置列为 NOT NULL
        db.session.execute(db.text("""
            ALTER TABLE daily_query_count
            ALTER COLUMN service_type SET NOT NULL
        """))
        db.session.commit()
        print("✓ 设置 service_type 为 NOT NULL")

        # 4. 设置默认值
        db.session.execute(db.text("""
            ALTER TABLE daily_query_count
            ALTER COLUMN service_type SET DEFAULT 'stock_analysis'
        """))
        db.session.commit()
        print("✓ 设置默认值")

        # 5. 删除旧的唯一约束（如果存在）
        db.session.execute(db.text("""
            ALTER TABLE daily_query_count
            DROP CONSTRAINT IF EXISTS daily_query_count_user_id_date_key
        """))
        db.session.commit()
        print("✓ 删除旧的唯一约束（如果存在）")

        # 6. 清理重复数据并添加唯一约束
        cleanup_and_add_constraint()

        print("\n迁移完成！")


def cleanup_and_add_constraint():
    """清理重复数据并添加唯一约束"""
    # 检查是否存在重复数据
    result = db.session.execute(db.text("""
        SELECT user_id, date, service_type, COUNT(*) as cnt
        FROM daily_query_count
        GROUP BY user_id, date, service_type
        HAVING COUNT(*) > 1
    """))
    rows = result.fetchall()

    if rows:
        print(f"发现 {len(rows)} 组重复记录，正在清理...")
        for row in rows:
            print(f"  user_id={row[0][:8]}..., date={row[1]}, service_type={row[2]}, count={row[3]}")

        # 保留每组中 query_count 最大的记录
        db.session.execute(db.text("""
            DELETE FROM daily_query_count a
            USING daily_query_count b
            WHERE a.user_id = b.user_id
            AND a.date = b.date
            AND a.service_type = b.service_type
            AND a.id < b.id
        """))
        db.session.commit()
        print("✓ 重复记录已清理")

    # 检查唯一约束是否已存在
    result = db.session.execute(db.text("""
        SELECT constraint_name
        FROM information_schema.table_constraints
        WHERE table_name = 'daily_query_count'
        AND constraint_name = 'uix_user_date_service'
    """))

    if result.fetchone():
        print("✓ 唯一约束已存在")
        db.session.commit()
        return

    # 添加唯一约束
    try:
        db.session.execute(db.text("""
            ALTER TABLE daily_query_count
            ADD CONSTRAINT uix_user_date_service
            UNIQUE (user_id, date, service_type)
        """))
        db.session.commit()
        print("✓ 添加唯一约束 (user_id, date, service_type)")
    except Exception as e:
        db.session.rollback()
        print(f"  添加唯一约束失败: {e}")


if __name__ == '__main__':
    migrate()

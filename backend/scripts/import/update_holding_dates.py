"""
Update all portfolio holdings' created_at date to 2026-01-01
Run this from the backend directory: python3 update_holding_dates.py
"""
import os
import sys
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Try to load dotenv, but don't fail if not available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from app import create_app
from app.models import db

def update_holding_dates():
    """Update all portfolio holdings' created_at to 2026-01-01"""
    app = create_app()
    with app.app_context():
        try:
            # Target date: 2026-01-01 00:00:00 UTC
            target_date = datetime(2026, 1, 1, 0, 0, 0)
            
            # Count holdings first
            from sqlalchemy import text
            result = db.session.execute(text("SELECT COUNT(*) FROM portfolio_holdings"))
            total_count = result.scalar()
            print(f"Found {total_count} portfolio holdings")
            
            # Update all holdings using raw SQL
            result = db.session.execute(
                text("UPDATE portfolio_holdings SET created_at = :target_date WHERE created_at != :target_date"),
                {"target_date": target_date}
            )
            updated_count = result.rowcount
            db.session.commit()
            
            if updated_count > 0:
                print(f"✅ Successfully updated {updated_count} holdings' created_at to 2026-01-01")
            else:
                print("✅ All holdings already have created_at = 2026-01-01")
            
            # Verify
            print("\nVerifying updates...")
            result = db.session.execute(
                text("SELECT ticker, style, created_at FROM portfolio_holdings LIMIT 5")
            )
            for row in result:
                print(f"  {row[0]} ({row[1]}): {row[2]}")
                
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error updating holding dates: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == "__main__":
    update_holding_dates()

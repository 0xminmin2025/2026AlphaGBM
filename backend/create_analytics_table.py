"""
Create analytics_events table for user behavior tracking
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import db, AnalyticsEvent

def create_analytics_table():
    """Create the analytics_events table if it doesn't exist"""
    app = create_app()

    with app.app_context():
        # Create the table
        db.create_all()
        print("✅ analytics_events table created successfully!")

        # Verify table exists
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()

        if 'analytics_events' in tables:
            print("✅ Verified: analytics_events table exists")

            # Show table columns
            columns = inspector.get_columns('analytics_events')
            print("\nTable columns:")
            for col in columns:
                print(f"  - {col['name']}: {col['type']}")
        else:
            print("❌ Error: analytics_events table was not created")

if __name__ == '__main__':
    create_analytics_table()

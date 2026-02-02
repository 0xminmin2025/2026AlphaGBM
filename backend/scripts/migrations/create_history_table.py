#!/usr/bin/env python3
"""
Migration script to create the stock_analysis_history table
Run this script to add the new table to your database
"""

import os
import sys
from pathlib import Path

# Add the parent directory to the path to import the app
sys.path.append(str(Path(__file__).parent))

from app import create_app

def create_history_table():
    """Create the stock_analysis_history table"""
    app = create_app()

    with app.app_context():
        try:
            # Import models within app context
            from app.models import db, StockAnalysisHistory

            # Create the table
            db.create_all()
            print("✅ Successfully created stock_analysis_history table")

            # Verify the table was created
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()

            if 'stock_analysis_history' in tables:
                print("✅ Table 'stock_analysis_history' exists in database")

                # Show table structure
                columns = inspector.get_columns('stock_analysis_history')
                print("\n📋 Table structure:")
                for column in columns:
                    print(f"  - {column['name']}: {column['type']}")
            else:
                print("❌ Table 'stock_analysis_history' was not created")

        except Exception as e:
            print(f"❌ Error creating table: {e}")
            import traceback
            traceback.print_exc()
            return False

    return True

if __name__ == '__main__':
    print("🔄 Creating stock_analysis_history table...")
    success = create_history_table()

    if success:
        print("\n✅ Migration completed successfully!")
        print("\nNext steps:")
        print("1. Restart your Flask backend")
        print("2. The stock analysis endpoint will now consume credits")
        print("3. Analysis history will be saved automatically")
        print("4. Use the history UI in the frontend to view past analyses")
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)
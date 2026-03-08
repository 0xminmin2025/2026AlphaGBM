#!/usr/bin/env python3
"""
Update AnalysisTask current_step field from VARCHAR(500) to TEXT
to support longer error messages
"""

import os
import sys
from dotenv import load_dotenv

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

load_dotenv()

from app import create_app
from app.models import db
from sqlalchemy import text

def update_field_to_text():
    """Update the current_step field to TEXT type"""
    app = create_app()

    with app.app_context():
        try:
            # Check database type
            db_url = app.config.get('SQLALCHEMY_DATABASE_URI', '')
            print(f"Database URL: {db_url[:50]}...")
            
            if 'postgresql' in db_url or 'postgres' in db_url:
                # PostgreSQL
                print("Detected PostgreSQL database")
                print("Updating current_step field from VARCHAR(500) to TEXT...")
                with db.engine.begin() as conn:
                    conn.execute(text("""
                        ALTER TABLE analysis_tasks
                        ALTER COLUMN current_step TYPE TEXT
                    """))
                print("✅ Successfully updated current_step field to TEXT (PostgreSQL)")
                
            elif 'sqlite' in db_url:
                # SQLite - TEXT is the default, but we can still try to alter
                print("Detected SQLite database")
                print("SQLite uses TEXT by default, but checking schema...")
                # SQLite doesn't support ALTER COLUMN TYPE directly
                # We need to recreate the table
                print("⚠️  SQLite requires table recreation. This script will not modify SQLite tables.")
                print("   For SQLite, the model change should work on new tables.")
                
            elif 'mysql' in db_url:
                # MySQL
                print("Detected MySQL database")
                print("Updating current_step field from VARCHAR(500) to TEXT...")
                with db.engine.begin() as conn:
                    conn.execute(text("""
                        ALTER TABLE analysis_tasks
                        MODIFY COLUMN current_step TEXT
                    """))
                print("✅ Successfully updated current_step field to TEXT (MySQL)")
            else:
                print("⚠️  Unknown database type. Please update manually.")

        except Exception as e:
            print(f"❌ Error updating field: {e}")
            import traceback
            traceback.print_exc()
            print("\n⚠️  If the field is already TEXT type, this error is expected.")
            print("   You can safely ignore this if the model change is already applied.")

if __name__ == "__main__":
    update_field_to_text()

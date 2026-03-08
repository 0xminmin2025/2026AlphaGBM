#!/usr/bin/env python3
"""
Update AnalysisTask current_step field length from VARCHAR(100) to VARCHAR(500)
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

def update_field_length():
    """Update the current_step field length"""
    app = create_app()

    with app.app_context():
        try:
            # Check current schema
            print("Checking current schema...")

            # Update the field length using raw SQL
            print("Updating current_step field length from VARCHAR(100) to VARCHAR(500)...")
            with db.engine.begin() as conn:
                conn.execute(text("""
                    ALTER TABLE analysis_tasks
                    ALTER COLUMN current_step TYPE VARCHAR(500)
                """))

            print("✅ Successfully updated current_step field length")

        except Exception as e:
            print(f"❌ Error updating field length: {e}")
            print("This might be expected if the field is already the correct length.")

if __name__ == "__main__":
    update_field_length()
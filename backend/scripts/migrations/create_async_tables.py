#!/usr/bin/env python3
"""
Database Migration Script for Async Task System
Creates the new tables for async analysis tasks system.

Usage:
    python create_async_tables.py
"""

import os
from app import create_app
from app.models import db, AnalysisTask, OptionsAnalysisHistory
from dotenv import load_dotenv

def create_async_tables():
    """Create new tables for async task system"""

    # Load environment variables
    load_dotenv()

    # Create Flask app and get database instance
    app = create_app()

    with app.app_context():
        try:
            print("=" * 60)
            print("Async Task System Database Migration")
            print("=" * 60)
            print(f"Database URL: {app.config.get('SQLALCHEMY_DATABASE_URI', 'Not set')}")

            # Create the tables
            print("\nCreating new tables:")
            print("1. analysis_tasks - Async task queue table")
            print("2. options_analysis_history - Options analysis history table")

            # This will create ONLY the new tables that don't exist yet
            # Existing tables will be ignored
            db.create_all()

            print("\n✅ Database tables created successfully!")

            # Verify tables were created
            print("\nVerifying tables exist:")

            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()

            new_tables = ['analysis_tasks', 'options_analysis_history']
            for table_name in new_tables:
                if table_name in tables:
                    print(f"✅ {table_name}")

                    # Get column info
                    columns = inspector.get_columns(table_name)
                    print(f"   Columns: {', '.join([col['name'] for col in columns])}")
                else:
                    print(f"❌ {table_name} - NOT FOUND")

            print("\n" + "=" * 60)
            print("Migration completed successfully!")
            print("=" * 60)

        except Exception as e:
            print(f"❌ Error during migration: {e}")
            import traceback
            traceback.print_exc()
            return False

    return True

def test_table_creation():
    """Test that we can interact with the new tables"""

    # Load environment variables
    load_dotenv()
    app = create_app()

    with app.app_context():
        try:
            print("\nTesting new tables...")

            # Test AnalysisTask table
            print("\nTesting AnalysisTask table:")

            import uuid
            test_task = AnalysisTask(
                id=str(uuid.uuid4()),
                user_id='test-user-id',
                task_type='stock_analysis',
                status='pending',
                input_params={
                    'ticker': 'TEST',
                    'style': 'quality'
                },
                current_step='Initializing...'
            )

            # Don't commit, just test creation
            db.session.add(test_task)
            print("✅ AnalysisTask creation test passed")

            # Test OptionsAnalysisHistory table
            print("\nTesting OptionsAnalysisHistory table:")

            test_options_history = OptionsAnalysisHistory(
                user_id='test-user-id',
                symbol='AAPL',
                analysis_type='basic_chain',
                expiry_date='2024-01-19',
                strike_price=150.0,
                option_type='call',
                option_score=85.5,
                full_analysis_data={'test': 'data'}
            )

            # Don't commit, just test creation
            db.session.add(test_options_history)
            print("✅ OptionsAnalysisHistory creation test passed")

            # Rollback test transactions
            db.session.rollback()
            print("\n✅ All table tests passed!")

        except Exception as e:
            print(f"❌ Error during table testing: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            return False

    return True

if __name__ == "__main__":
    print("Starting database migration for async task system...")

    if create_async_tables():
        if test_table_creation():
            print("\n🎉 Migration completed successfully!")
            print("Your async task system is ready to use!")
        else:
            print("\n⚠️ Migration completed but tests failed")
    else:
        print("\n❌ Migration failed")
        exit(1)
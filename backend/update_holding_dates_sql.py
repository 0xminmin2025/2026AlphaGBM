#!/usr/bin/env python3
"""
Update all portfolio holdings' created_at date to 2026-01-01 using direct SQL
"""
import os
import sys
import psycopg2
from datetime import datetime

def update_holding_dates():
    """Update all portfolio holdings' created_at to 2026-01-01"""
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        # Try to construct from individual env vars
        db_user = os.getenv('DB_USER', 'postgres')
        db_password = os.getenv('DB_PASSWORD', '')
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME', 'alphagbm')
        
        if db_password:
            database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        else:
            database_url = f"postgresql://{db_user}@{db_host}:{db_port}/{db_name}"
    
    if not database_url:
        print("❌ Error: DATABASE_URL or DB_* environment variables not set")
        sys.exit(1)
    
    try:
        print(f"Connecting to database...")
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Target date: 2026-01-01 00:00:00 UTC
        target_date = datetime(2026, 1, 1, 0, 0, 0)
        
        # Count holdings
        cursor.execute("SELECT COUNT(*) FROM portfolio_holdings")
        total_count = cursor.fetchone()[0]
        print(f"Found {total_count} portfolio holdings")
        
        # Update all holdings
        cursor.execute(
            "UPDATE portfolio_holdings SET created_at = %s WHERE created_at != %s",
            (target_date, target_date)
        )
        
        updated_count = cursor.rowcount
        conn.commit()
        
        if updated_count > 0:
            print(f"✅ Successfully updated {updated_count} holdings' created_at to 2026-01-01")
        else:
            print("✅ All holdings already have created_at = 2026-01-01")
        
        # Verify
        cursor.execute("SELECT ticker, style, created_at FROM portfolio_holdings LIMIT 5")
        print("\nSample holdings after update:")
        for row in cursor.fetchall():
            print(f"  {row[0]} ({row[1]}): {row[2]}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error updating holding dates: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    # Try to load .env file if it exists
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    update_holding_dates()

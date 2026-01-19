#!/usr/bin/env python3
"""
Simple script to update portfolio holdings' created_at to 2026-01-01
Uses direct database connection
"""
import os
import sys
from datetime import datetime

# Try to load environment variables
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
try:
    from dotenv import load_dotenv
    load_dotenv(env_path)
    print(f"Loaded .env from {env_path}")
except Exception as e:
    print(f"Warning: Could not load .env: {e}")

# Get database URL
database_url = os.getenv('POSTGRES_URL') or os.getenv('SQLALCHEMY_DATABASE_URI') or os.getenv('DATABASE_URL')

# If still not found, try reading .env file directly
if not database_url and os.path.exists(env_path):
    print("Reading .env file directly...")
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key in ['POSTGRES_URL', 'SQLALCHEMY_DATABASE_URI', 'DATABASE_URL']:
                    database_url = value
                    print(f"Found {key} in .env file")
                    break
                # Also set it as environment variable for next attempts
                os.environ[key] = value

if not database_url:
    print("Error: No database URL found in environment variables")
    print("Please set POSTGRES_URL, SQLALCHEMY_DATABASE_URI, or DATABASE_URL")
    sys.exit(1)

# Convert postgres:// to postgresql:// if needed
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

try:
    from sqlalchemy import create_engine, text
    
    print(f"Connecting to database...")
    engine = create_engine(database_url)
    
    target_date = datetime(2026, 1, 1, 0, 0, 0)
    
    with engine.connect() as conn:
        # Count holdings
        result = conn.execute(text("SELECT COUNT(*) FROM portfolio_holdings"))
        total_count = result.scalar()
        print(f"Found {total_count} portfolio holdings")
        
        # Update all holdings
        result = conn.execute(
            text("UPDATE portfolio_holdings SET created_at = :target_date WHERE created_at != :target_date"),
            {"target_date": target_date}
        )
        updated_count = result.rowcount
        conn.commit()
        
        if updated_count > 0:
            print(f"✅ Successfully updated {updated_count} holdings' created_at to 2026-01-01")
        else:
            print("✅ All holdings already have created_at = 2026-01-01")
        
        # Verify
        print("\nVerifying updates...")
        result = conn.execute(
            text("SELECT ticker, style, created_at FROM portfolio_holdings ORDER BY ticker LIMIT 5")
        )
        for row in result:
            print(f"  {row[0]} ({row[1]}): {row[2]}")
    
    print("\n✅ Update completed successfully!")
    
except ImportError as e:
    print(f"Error: Missing required package: {e}")
    print("Please install: pip install sqlalchemy psycopg2-binary")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

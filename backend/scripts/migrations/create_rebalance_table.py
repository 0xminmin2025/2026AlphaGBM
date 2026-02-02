"""
Create portfolio_rebalances table for tracking rebalancing history
"""
import os
import sys
from dotenv import load_dotenv
from app import create_app
from app.models import db
from sqlalchemy import text

def create_rebalance_table():
    app = create_app()
    with app.app_context():
        try:
            print("Creating portfolio_rebalances table...")
            
            # Check if table exists
            result = db.session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'portfolio_rebalances'
                );
            """))
            
            table_exists = result.scalar()
            
            if table_exists:
                print("Table 'portfolio_rebalances' already exists.")
                return
            
            # Create table
            db.session.execute(text("""
                CREATE TABLE portfolio_rebalances (
                    id SERIAL PRIMARY KEY,
                    rebalance_date DATE NOT NULL,
                    rebalance_number INTEGER NOT NULL,
                    holdings_added INTEGER DEFAULT 0,
                    holdings_removed INTEGER DEFAULT 0,
                    holdings_adjusted INTEGER DEFAULT 0,
                    total_investment FLOAT NOT NULL,
                    total_market_value FLOAT NOT NULL,
                    total_profit_loss FLOAT NOT NULL,
                    total_profit_loss_percent FLOAT NOT NULL,
                    style_stats JSONB,
                    changes_detail JSONB,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            
            # Create indexes
            db.session.execute(text("""
                CREATE INDEX idx_rebalance_date ON portfolio_rebalances(rebalance_date);
            """))
            
            db.session.commit()
            print("✅ Successfully created portfolio_rebalances table with indexes")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error creating table: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    load_dotenv()
    create_rebalance_table()

"""
Insert sample rebalance history data for demonstration
"""
import os
import sys
from dotenv import load_dotenv
from app import create_app
from app.models import db, PortfolioRebalance
from datetime import date, timedelta

def insert_sample_rebalances():
    app = create_app()
    with app.app_context():
        try:
            print("Inserting sample rebalance history...")
            
            # Check if data already exists
            existing = PortfolioRebalance.query.first()
            if existing:
                print("Rebalance history already exists. Skipping sample data insertion.")
                return
            
            # Sample rebalance data (every 2 weeks from 2026-01-01)
            base_date = date(2026, 1, 1)
            sample_rebalances = [
                {
                    'rebalance_date': base_date,
                    'rebalance_number': 1,
                    'holdings_added': 2,
                    'holdings_removed': 0,
                    'holdings_adjusted': 1,
                    'total_investment': 1000000.0,
                    'total_market_value': 1012000.0,
                    'total_profit_loss': 12000.0,
                    'total_profit_loss_percent': 1.2,
                    'style_stats': {
                        'quality': {
                            'investment': 250000.0,
                            'market_value': 253000.0,
                            'profit_loss': 3000.0,
                            'profit_loss_percent': 1.2
                        },
                        'value': {
                            'investment': 250000.0,
                            'market_value': 252000.0,
                            'profit_loss': 2000.0,
                            'profit_loss_percent': 0.8
                        },
                        'growth': {
                            'investment': 250000.0,
                            'market_value': 254000.0,
                            'profit_loss': 4000.0,
                            'profit_loss_percent': 1.6
                        },
                        'momentum': {
                            'investment': 250000.0,
                            'market_value': 253000.0,
                            'profit_loss': 3000.0,
                            'profit_loss_percent': 1.2
                        }
                    },
                    'changes_detail': {
                        'added': [
                            {'ticker': 'AAPL', 'name': 'Apple Inc.', 'shares': 50, 'buy_price': 180.0, 'style': 'quality'},
                            {'ticker': 'MSFT', 'name': 'Microsoft Corporation', 'shares': 30, 'buy_price': 380.0, 'style': 'growth'}
                        ],
                        'removed': [],
                        'adjusted': [
                            {'ticker': 'TSLA', 'name': 'Tesla Inc.', 'old_shares': 100, 'new_shares': 120, 'old_price': 250.0, 'new_price': 248.0, 'style': 'momentum'}
                        ]
                    },
                    'notes': '首次调仓：增持科技股，调整TSLA仓位'
                },
                {
                    'rebalance_date': base_date + timedelta(days=14),
                    'rebalance_number': 2,
                    'holdings_added': 1,
                    'holdings_removed': 1,
                    'holdings_adjusted': 2,
                    'total_investment': 1000000.0,
                    'total_market_value': 1025000.0,
                    'total_profit_loss': 25000.0,
                    'total_profit_loss_percent': 2.5,
                    'style_stats': {
                        'quality': {
                            'investment': 250000.0,
                            'market_value': 256000.0,
                            'profit_loss': 6000.0,
                            'profit_loss_percent': 2.4
                        },
                        'value': {
                            'investment': 250000.0,
                            'market_value': 254000.0,
                            'profit_loss': 4000.0,
                            'profit_loss_percent': 1.6
                        },
                        'growth': {
                            'investment': 250000.0,
                            'market_value': 257000.0,
                            'profit_loss': 7000.0,
                            'profit_loss_percent': 2.8
                        },
                        'momentum': {
                            'investment': 250000.0,
                            'market_value': 254000.0,
                            'profit_loss': 4000.0,
                            'profit_loss_percent': 1.6
                        }
                    },
                    'changes_detail': {
                        'added': [
                            {'ticker': 'NVDA', 'name': 'NVIDIA Corporation', 'shares': 40, 'buy_price': 500.0, 'style': 'growth'}
                        ],
                        'removed': [
                            {'ticker': 'TSLA', 'name': 'Tesla Inc.', 'shares': 120, 'style': 'momentum'}
                        ],
                        'adjusted': [
                            {'ticker': 'AAPL', 'name': 'Apple Inc.', 'old_shares': 50, 'new_shares': 60, 'old_price': 180.0, 'new_price': 185.0, 'style': 'quality'},
                            {'ticker': 'MSFT', 'name': 'Microsoft Corporation', 'old_shares': 30, 'new_shares': 35, 'old_price': 380.0, 'new_price': 385.0, 'style': 'growth'}
                        ]
                    },
                    'notes': '第二次调仓：增持AI相关股票，移除TSLA，调整核心持仓'
                },
                {
                    'rebalance_date': base_date + timedelta(days=28),
                    'rebalance_number': 3,
                    'holdings_added': 0,
                    'holdings_removed': 0,
                    'holdings_adjusted': 3,
                    'total_investment': 1000000.0,
                    'total_market_value': 1038000.0,
                    'total_profit_loss': 38000.0,
                    'total_profit_loss_percent': 3.8,
                    'style_stats': {
                        'quality': {
                            'investment': 250000.0,
                            'market_value': 259000.0,
                            'profit_loss': 9000.0,
                            'profit_loss_percent': 3.6
                        },
                        'value': {
                            'investment': 250000.0,
                            'market_value': 256000.0,
                            'profit_loss': 6000.0,
                            'profit_loss_percent': 2.4
                        },
                        'growth': {
                            'investment': 250000.0,
                            'market_value': 261000.0,
                            'profit_loss': 11000.0,
                            'profit_loss_percent': 4.4
                        },
                        'momentum': {
                            'investment': 250000.0,
                            'market_value': 262000.0,
                            'profit_loss': 12000.0,
                            'profit_loss_percent': 4.8
                        }
                    },
                    'changes_detail': {
                        'added': [],
                        'removed': [],
                        'adjusted': [
                            {'ticker': 'AAPL', 'name': 'Apple Inc.', 'old_shares': 60, 'new_shares': 65, 'old_price': 185.0, 'new_price': 190.0, 'style': 'quality'},
                            {'ticker': 'MSFT', 'name': 'Microsoft Corporation', 'old_shares': 35, 'new_shares': 40, 'old_price': 385.0, 'new_price': 390.0, 'style': 'growth'},
                            {'ticker': 'NVDA', 'name': 'NVIDIA Corporation', 'old_shares': 40, 'new_shares': 45, 'old_price': 500.0, 'new_price': 510.0, 'style': 'growth'}
                        ]
                    },
                    'notes': '第三次调仓：微调仓位，增持表现良好的持仓'
                }
            ]
            
            for rebalance_data in sample_rebalances:
                rebalance = PortfolioRebalance(**rebalance_data)
                db.session.add(rebalance)
            
            db.session.commit()
            print(f"✅ Successfully inserted {len(sample_rebalances)} sample rebalance records")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error inserting sample data: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    load_dotenv()
    insert_sample_rebalances()

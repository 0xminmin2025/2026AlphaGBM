#!/usr/bin/env python3
"""
Historical Data Import Script

This script imports portfolio holdings and profit/loss history data from JSON files
into the database. Used for development and testing purposes.

Usage:
    python import_historical_data.py

Required files:
    - portfolio.json: Portfolio holdings data
    - history_loss.json: Historical profit/loss data
"""

import json
import os
from datetime import datetime
from app import create_app
from app.models import db, PortfolioHolding, DailyProfitLoss, StyleProfit
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def clear_existing_data():
    """Clear existing portfolio and profit/loss data"""
    print("Clearing existing data...")

    # Clear in order to respect foreign key constraints
    StyleProfit.query.delete()
    DailyProfitLoss.query.delete()
    PortfolioHolding.query.delete()

    db.session.commit()
    print("Existing data cleared successfully!")

def import_portfolio_holdings(portfolio_data):
    """Import portfolio holdings from portfolio.json structure"""
    print("Importing portfolio holdings...")

    if not portfolio_data.get('success') or 'portfolio' not in portfolio_data:
        print("Error: Invalid portfolio data structure")
        return

    portfolio = portfolio_data['portfolio']
    stocks = portfolio.get('stocks', [])

    holdings_imported = 0

    for stock in stocks:
        print(f"Processing {stock['ticker']} ({stock['style']})...")

        # Create new portfolio holding
        portfolio_holding = PortfolioHolding(
            ticker=stock['ticker'],
            name=stock.get('name', stock['ticker']),
            shares=stock['shares'],
            buy_price=stock['buyPrice'],  # Using buyPrice from JSON
            style=stock['style'],
            user_id=None,  # Public portfolio data
            currency=stock.get('currency', 'USD')
        )

        db.session.add(portfolio_holding)
        holdings_imported += 1
        print(f"Added: {stock['ticker']} - {stock['shares']} shares at {stock['currency']} {stock['buyPrice']}")

    db.session.commit()
    print(f"Imported {holdings_imported} portfolio holdings successfully!")

def import_profit_loss_history(history_data):
    """Import profit/loss history from history_loss.json structure"""
    print("Importing profit/loss history...")

    if not history_data.get('success') or 'data' not in history_data:
        print("Error: Invalid profit/loss history data structure")
        return

    data = history_data['data']
    items = data.get('items', [])

    daily_records_imported = 0
    style_records_imported = 0

    for record in items:
        trading_date = datetime.strptime(record['date'], '%Y-%m-%d').date()
        print(f"Processing date: {trading_date}")

        # Create daily profit/loss record
        daily_record = DailyProfitLoss(
            trading_date=trading_date,
            total_actual_investment=record['total_investment'],
            total_market_value=record['total_market_value'],
            total_profit_loss=record['total_profit_loss'],
            total_profit_loss_percent=record['total_profit_loss_percent'],
            user_id=None  # Public data
        )
        db.session.add(daily_record)
        daily_records_imported += 1
        print(f"Added daily record for {trading_date}: {record['total_profit_loss_percent']:.2f}%")

        # Import style-specific data
        style_profits = record.get('style_profits', {})
        for style_name, style_data in style_profits.items():
            style_record = StyleProfit(
                trading_date=trading_date,
                style=style_name,
                style_investment=250000,  # Each style has $250K as base investment
                style_market_value=250000 + style_data['profit_loss'],  # Market value = base + profit/loss
                style_profit_loss=style_data['profit_loss'],
                style_profit_loss_percent=style_data['profit_loss_percent']
            )
            db.session.add(style_record)
            style_records_imported += 1
            print(f"Added {style_name} record for {trading_date}: {style_data['profit_loss_percent']:.2f}%")

    db.session.commit()
    print(f"Imported {daily_records_imported} daily records and {style_records_imported} style records successfully!")

def load_json_file(filename):
    """Load and parse JSON file"""
    if not os.path.exists(filename):
        print(f"Warning: {filename} not found. Please ensure the file exists.")
        return None

    try:
        with open(filename, 'r', encoding='utf-8') as file:
            return json.load(file)
    except json.JSONDecodeError as e:
        print(f"Error parsing {filename}: {e}")
        return None
    except Exception as e:
        print(f"Error reading {filename}: {e}")
        return None

def main():
    """Main import function"""
    print("="*60)
    print("Historical Data Import Script")
    print("="*60)

    # Create Flask app and initialize database
    app = create_app()

    with app.app_context():
        try:
            # Ensure tables exist
            db.create_all()
            print("Database tables ready.")

            # Clear existing data first
            clear_existing_data()

            print("-" * 40)

            # Load portfolio data from project root
            portfolio_data = load_json_file('../../portfolio.json')
            if portfolio_data:
                import_portfolio_holdings(portfolio_data)
            else:
                print("Skipping portfolio import (file not found or invalid)")

            print("-" * 40)

            # Load profit/loss history data from project root
            history_data = load_json_file('../../history_loss.json')
            if history_data:
                import_profit_loss_history(history_data)
            else:
                print("Skipping profit/loss history import (file not found or invalid)")

            print("="*60)
            print("Import completed successfully!")
            print("="*60)

        except Exception as e:
            print(f"Import failed: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()

def create_sample_data():
    """Create sample data for testing if JSON files are not available"""
    print("Creating sample data for testing...")

    # Sample portfolio holdings
    sample_holdings = {
        'quality': [
            {'ticker': 'NVDA', 'name': '英伟达', 'shares': 214, 'cost': 194.2, 'currency': 'USD'},
            {'ticker': 'GOOGL', 'name': '谷歌', 'shares': 157, 'cost': 263.8, 'currency': 'USD'},
            {'ticker': '9988.HK', 'name': '阿里巴巴', 'shares': 1917, 'cost': 169.5, 'currency': 'HKD'}
        ],
        'value': [
            {'ticker': 'COP', 'name': '康菲石油', 'shares': 462, 'cost': 90.03, 'currency': 'USD'},
            {'ticker': '0883.HK', 'name': '中国海油', 'shares': 16839, 'cost': 19.3, 'currency': 'HKD'}
        ],
        'growth': [
            {'ticker': 'MU', 'name': '美光科技', 'shares': 550, 'cost': 88.00, 'currency': 'USD'}
        ],
        'momentum': [
            {'ticker': 'TSLA', 'name': '特斯拉', 'shares': 200, 'cost': 245.00, 'currency': 'USD'}
        ]
    }

    import_portfolio_holdings(sample_holdings)
    print("Sample portfolio data imported!")

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--sample':
        # Create sample data mode
        app = create_app()
        with app.app_context():
            db.create_all()
            create_sample_data()
    else:
        # Normal import mode
        main()
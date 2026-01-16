"""
Daily Profit/Loss Calculation Scheduler

This module handles the daily calculation and storage of portfolio profit/loss data.
Based on the original app.py calculate_daily_profit_loss() function.
"""

import logging
import yfinance as yf
import requests
from datetime import datetime, date
from apscheduler.schedulers.background import BackgroundScheduler
from .models import db, PortfolioHolding, DailyProfitLoss, StyleProfit
from .utils.serialization import convert_numpy_types

logger = logging.getLogger(__name__)

# Exchange rate caching
exchange_rates_cache = {}
cache_timestamp = None

def get_exchange_rates():
    """Get USD exchange rates for HKD and CNY"""
    global exchange_rates_cache, cache_timestamp

    try:
        # Use cached rates if less than 1 hour old
        if cache_timestamp and (datetime.now() - cache_timestamp).seconds < 3600:
            return exchange_rates_cache

        # Fetch new rates from exchangerate-api.com (free tier)
        response = requests.get('https://api.exchangerate-api.com/v4/latest/USD', timeout=10)
        data = response.json()

        exchange_rates_cache = {
            'USD_TO_HKD': data['rates']['HKD'],
            'USD_TO_CNY': data['rates']['CNY'],
            'HKD_TO_USD': 1 / data['rates']['HKD'],
            'CNY_TO_USD': 1 / data['rates']['CNY']
        }
        cache_timestamp = datetime.now()
        logger.info(f"Updated exchange rates: {exchange_rates_cache}")

    except Exception as e:
        logger.error(f"Failed to fetch exchange rates: {e}")
        # Use fallback rates if API fails
        exchange_rates_cache = {
            'USD_TO_HKD': 7.8,
            'USD_TO_CNY': 7.2,
            'HKD_TO_USD': 0.128,
            'CNY_TO_USD': 0.139
        }
        logger.warning("Using fallback exchange rates")

    return exchange_rates_cache

def get_current_stock_price(ticker):
    """Get current stock price using yfinance"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        # Try different price fields in order of preference
        current_price = (
            info.get('currentPrice') or
            info.get('regularMarketPrice') or
            info.get('previousClose') or
            info.get('lastPrice')
        )

        if current_price:
            logger.debug(f"Got price for {ticker}: {current_price}")
            return float(current_price)
        else:
            logger.warning(f"No price data available for {ticker}")
            return None

    except Exception as e:
        logger.error(f"Error fetching price for {ticker}: {e}")
        return None

def convert_to_usd(amount, currency, rates):
    """Convert amount to USD using exchange rates"""
    if currency == 'USD':
        return amount
    elif currency == 'HKD':
        return amount * rates['HKD_TO_USD']
    elif currency == 'CNY':
        return amount * rates['CNY_TO_USD']
    else:
        logger.warning(f"Unknown currency: {currency}, treating as USD")
        return amount

def calculate_daily_profit_loss():
    """
    Calculate daily profit/loss for all portfolio holdings

    This function replicates the logic from the original app.py calculate_daily_profit_loss()
    """
    try:
        logger.info("Starting daily profit/loss calculation...")

        # Get current date
        today = date.today()

        # Check if we already calculated for today
        existing_daily = DailyProfitLoss.query.filter_by(trading_date=today).first()
        if existing_daily:
            logger.info(f"Profit/loss already calculated for {today}")
            return

        # Get exchange rates
        rates = get_exchange_rates()

        # Get all portfolio holdings
        holdings = PortfolioHolding.query.all()
        if not holdings:
            logger.warning("No portfolio holdings found")
            return

        # Calculate profit/loss by style
        style_calculations = {
            'quality': {'investment': 0, 'market_value': 0, 'profit_loss': 0},
            'value': {'investment': 0, 'market_value': 0, 'profit_loss': 0},
            'growth': {'investment': 0, 'market_value': 0, 'profit_loss': 0},
            'momentum': {'investment': 0, 'market_value': 0, 'profit_loss': 0}
        }

        total_investment_usd = 0
        total_market_value_usd = 0

        logger.info(f"Processing {len(holdings)} holdings...")

        for holding in holdings:
            try:
                # Get current price
                current_price = get_current_stock_price(holding.ticker)

                if current_price is None:
                    logger.warning(f"Skipping {holding.ticker} - no price data")
                    continue

                # Calculate investment and market value in original currency
                investment_amount = holding.buy_price * holding.shares
                market_value_amount = current_price * holding.shares
                profit_loss_amount = market_value_amount - investment_amount

                # Convert to USD for totals
                investment_usd = convert_to_usd(investment_amount, holding.currency, rates)
                market_value_usd = convert_to_usd(market_value_amount, holding.currency, rates)

                # Add to style calculations
                style = holding.style.lower()
                if style in style_calculations:
                    style_calculations[style]['investment'] += investment_usd
                    style_calculations[style]['market_value'] += market_value_usd
                    style_calculations[style]['profit_loss'] += (market_value_usd - investment_usd)

                # Add to totals
                total_investment_usd += investment_usd
                total_market_value_usd += market_value_usd

                logger.debug(f"{holding.ticker}: {holding.currency} {current_price}, USD equivalent: {market_value_usd:.2f}")

            except Exception as e:
                logger.error(f"Error processing {holding.ticker}: {e}")
                continue

        # Calculate total profit/loss
        total_profit_loss_usd = total_market_value_usd - total_investment_usd
        total_profit_loss_percent = (total_profit_loss_usd / total_investment_usd * 100) if total_investment_usd > 0 else 0

        # Save daily profit/loss record
        daily_record = DailyProfitLoss(
            trading_date=today,
            total_actual_investment=total_investment_usd,
            total_market_value=total_market_value_usd,
            total_profit_loss=total_profit_loss_usd,
            total_profit_loss_percent=total_profit_loss_percent,
            user_id=None  # Public data
        )
        db.session.add(daily_record)

        logger.info(f"Total Portfolio: Investment: ${total_investment_usd:,.2f}, "
                   f"Market Value: ${total_market_value_usd:,.2f}, "
                   f"P/L: {total_profit_loss_percent:.2f}%")

        # Save style-specific records
        for style_name, calc in style_calculations.items():
            if calc['investment'] > 0:
                style_profit_loss_percent = (calc['profit_loss'] / calc['investment'] * 100)

                style_record = StyleProfit(
                    trading_date=today,
                    style=style_name,
                    style_investment=calc['investment'],
                    style_market_value=calc['market_value'],
                    style_profit_loss=calc['profit_loss'],
                    style_profit_loss_percent=style_profit_loss_percent
                )
                db.session.add(style_record)

                logger.info(f"{style_name.title()} Style: Investment: ${calc['investment']:,.2f}, "
                           f"Market Value: ${calc['market_value']:,.2f}, "
                           f"P/L: {style_profit_loss_percent:.2f}%")

        # Commit all changes
        db.session.commit()
        logger.info(f"Daily profit/loss calculation completed successfully for {today}")

    except Exception as e:
        logger.error(f"Daily profit/loss calculation failed: {e}")
        db.session.rollback()
        raise

# Global scheduler instance
scheduler = None

def init_scheduler(app):
    """Initialize the scheduler with Flask app context"""
    global scheduler

    if scheduler is not None:
        return  # Already initialized

    try:
        scheduler = BackgroundScheduler(daemon=True)

        # Add the daily profit/loss calculation job - runs every day at 6:12 PM
        scheduler.add_job(
            func=lambda: run_with_app_context(app, calculate_daily_profit_loss),
            trigger='cron',
            hour=18,  # 6 PM
            minute=12,
            id='daily_profit_loss_calculation',
            name='Daily Profit/Loss Calculation',
            replace_existing=True
        )

        scheduler.start()
        logger.info("Scheduler initialized successfully - Daily P/L calculation will run at 6:12 PM")

    except Exception as e:
        logger.error(f"Failed to initialize scheduler: {e}")

def run_with_app_context(app, func):
    """Run function within Flask app context"""
    with app.app_context():
        func()

def shutdown_scheduler():
    """Shutdown the scheduler"""
    global scheduler
    if scheduler:
        scheduler.shutdown()
        scheduler = None
        logger.info("Scheduler shut down")
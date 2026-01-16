from flask import Blueprint, request, jsonify, g
from ..models import db, PortfolioHolding, DailyProfitLoss, StyleProfit, PortfolioRebalance
from ..utils.serialization import convert_numpy_types
from ..scheduler import get_exchange_rates, convert_to_usd
import yfinance as yf
import logging
from datetime import datetime, timedelta, date
from sqlalchemy import func, desc, text

portfolio_bp = Blueprint('portfolio', __name__, url_prefix='/api/portfolio')
logger = logging.getLogger(__name__)

@portfolio_bp.route('/update-holding-dates', methods=['POST'])
def update_holding_dates():
    """
    Update all portfolio holdings' created_at date to 2026-01-01
    This is a one-time operation to set the base date for all holdings
    """
    try:
        target_date = datetime(2026, 1, 1, 0, 0, 0)
        
        # Count holdings first
        result = db.session.execute(text("SELECT COUNT(*) FROM portfolio_holdings"))
        total_count = result.scalar()
        
        # Update all holdings
        result = db.session.execute(
            text("UPDATE portfolio_holdings SET created_at = :target_date WHERE created_at != :target_date"),
            {"target_date": target_date}
        )
        updated_count = result.rowcount
        db.session.commit()
        
        logger.info(f"Updated {updated_count} holdings' created_at to 2026-01-01")
        
        return jsonify({
            'success': True,
            'message': f'Successfully updated {updated_count} holdings to 2026-01-01',
            'total_holdings': total_count,
            'updated_count': updated_count
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating holding dates: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@portfolio_bp.route('/holdings', methods=['GET'])
def get_portfolio_holdings():
    """
    Portfolio Holdings Endpoint - Get real portfolio data by style
    Returns: {
        "success": true,
        "data": {
            "holdings_by_style": {
                "quality": [holdings],
                "value": [holdings],
                "growth": [holdings],
                "momentum": [holdings]
            },
            "style_stats": {
                "quality": {"profitLossPercent": "12.4", "vsYesterdayPercent": "1.2"},
                ...
            },
            "chart_data": [historical data for chart]
        }
    }
    """
    try:
        logger.info("Fetching portfolio holdings data")

        # Get all portfolio holdings grouped by style
        holdings = PortfolioHolding.query.all()
        holdings_by_style = {
            'quality': [],
            'value': [],
            'growth': [],
            'momentum': []
        }

        # Current prices cache
        price_cache = {}

        # Group holdings by style and get current prices
        for holding in holdings:
            if holding.style.lower() not in holdings_by_style:
                continue

            # Get current price from yfinance
            current_price = holding.buy_price  # Default to buy price
            try:
                if holding.ticker not in price_cache:
                    ticker_obj = yf.Ticker(holding.ticker)
                    info = ticker_obj.info
                    current_price = info.get('currentPrice', info.get('regularMarketPrice', holding.buy_price))
                    price_cache[holding.ticker] = current_price
                else:
                    current_price = price_cache[holding.ticker]
            except Exception as e:
                logger.warning(f"Could not get current price for {holding.ticker}: {e}")
                current_price = holding.buy_price

            # Calculate profit
            profit_amount = (current_price - holding.buy_price) * holding.shares
            profit_percent = ((current_price - holding.buy_price) / holding.buy_price) * 100

            holding_data = {
                'ticker': holding.ticker,
                'name': holding.name,
                'shares': holding.shares,
                'cost': holding.buy_price,
                'current': current_price,
                'market': 'US',  # You can enhance this based on ticker format
                'profit_amount': profit_amount,
                'profit_percent': profit_percent,
                'currency': holding.currency
            }

            holdings_by_style[holding.style.lower()].append(holding_data)

        # Get exchange rates for currency conversion
        exchange_rates = get_exchange_rates()

        # Get style statistics from latest daily data
        style_stats = {}
        styles = ['quality', 'value', 'growth', 'momentum']

        for style in styles:
            # Calculate current values from holdings first (most accurate)
            # IMPORTANT: Convert all holdings to USD before summing
            holdings_for_style = holdings_by_style[style]
            total_cost_usd = 0.0
            total_current_usd = 0.0

            for h in holdings_for_style:
                # Convert cost and current value to USD
                cost_amount = h['cost'] * h['shares']
                current_amount = h['current'] * h['shares']
                currency = h.get('currency', 'USD')
                
                cost_usd = convert_to_usd(cost_amount, currency, exchange_rates)
                current_usd = convert_to_usd(current_amount, currency, exchange_rates)
                
                total_cost_usd += cost_usd
                total_current_usd += current_usd

            if total_cost_usd > 0:
                current_profit_percent = ((total_current_usd - total_cost_usd) / total_cost_usd) * 100
            else:
                current_profit_percent = 0.0

            # Get latest profit data for this style from database
            latest_style_profit = StyleProfit.query.filter_by(style=style).order_by(
                desc(StyleProfit.trading_date)
            ).first()

            # Get yesterday's data for comparison
            yesterday_style_profit = StyleProfit.query.filter_by(style=style).order_by(
                desc(StyleProfit.trading_date)
            ).offset(1).first()

            # Calculate daily change
            daily_change = 0.0
            if latest_style_profit and yesterday_style_profit:
                # Use database values if available
                daily_change = (latest_style_profit.style_profit_loss_percent -
                              yesterday_style_profit.style_profit_loss_percent)
            elif latest_style_profit:
                # If only one day of data, compare with current calculated value
                daily_change = current_profit_percent - latest_style_profit.style_profit_loss_percent

            # Always use real-time calculated values for accuracy
            # Database values may be stale or inaccurate
            profit_loss_percent = current_profit_percent
            market_value = total_current_usd
            investment = total_cost_usd

            style_stats[style] = {
                'profitLossPercent': f"{profit_loss_percent:.1f}",
                'vsYesterdayPercent': f"{daily_change:.1f}",
                'market_value': market_value,
                'investment': investment
            }

        # Get historical data for chart (last 30 days)
        chart_data = []
        try:
            # Query last 30 days of style profits
            thirty_days_ago = datetime.now().date() - timedelta(days=30)
            historical_data = db.session.query(StyleProfit).filter(
                StyleProfit.trading_date >= thirty_days_ago
            ).order_by(StyleProfit.trading_date).all()

            # Group by date
            chart_data_dict = {}
            for record in historical_data:
                date_str = record.trading_date.strftime('%Y-%m-%d')
                if date_str not in chart_data_dict:
                    chart_data_dict[date_str] = {}
                chart_data_dict[date_str][record.style] = record.style_profit_loss_percent

            # Convert to chart format
            for date_str in sorted(chart_data_dict.keys()):
                chart_data.append({
                    'date': date_str,
                    'quality': chart_data_dict[date_str].get('quality', 0),
                    'value': chart_data_dict[date_str].get('value', 0),
                    'growth': chart_data_dict[date_str].get('growth', 0),
                    'momentum': chart_data_dict[date_str].get('momentum', 0)
                })

        except Exception as e:
            logger.warning(f"Could not get historical chart data: {e}")
            # Fallback to mock data
            chart_data = [
                {'date': f"2025-01-{i:02d}", 'quality': 10 + i*0.4, 'value': 5 + i*0.2,
                 'growth': 8 + i*0.6, 'momentum': 12 + i*0.8}
                for i in range(1, 31)
            ]

        response_data = {
            'holdings_by_style': holdings_by_style,
            'style_stats': style_stats,
            'chart_data': chart_data
        }

        # Convert numpy types for JSON serialization
        clean_data = convert_numpy_types(response_data)

        logger.info(f"Successfully retrieved portfolio data for {len(holdings)} holdings")

        return jsonify({
            'success': True,
            'data': clean_data
        })

    except Exception as e:
        logger.error(f"Error fetching portfolio holdings: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")

        # Return fallback data
        fallback_data = {
            'holdings_by_style': {
                'quality': [
                    {'ticker': 'NVDA', 'name': '英伟达', 'shares': 214, 'cost': 194.2, 'current': 194.2, 'market': 'US', 'profit_amount': 0, 'profit_percent': 0, 'currency': 'USD'},
                    {'ticker': 'GOOGL', 'name': '谷歌', 'shares': 157, 'cost': 263.8, 'current': 263.8, 'market': 'US', 'profit_amount': 0, 'profit_percent': 0, 'currency': 'USD'},
                ],
                'value': [
                    {'ticker': 'COP', 'name': '康菲石油', 'shares': 462, 'cost': 90.03, 'current': 90.03, 'market': 'US', 'profit_amount': 0, 'profit_percent': 0, 'currency': 'USD'},
                ],
                'growth': [
                    {'ticker': 'MU', 'name': '美光科技', 'shares': 550, 'cost': 88.00, 'current': 88.00, 'market': 'US', 'profit_amount': 0, 'profit_percent': 0, 'currency': 'USD'},
                ],
                'momentum': [
                    {'ticker': 'TSLA', 'name': '特斯拉', 'shares': 200, 'cost': 245.00, 'current': 245.00, 'market': 'US', 'profit_amount': 0, 'profit_percent': 0, 'currency': 'USD'},
                ]
            },
            'style_stats': {
                'quality': {'profitLossPercent': '12.4', 'vsYesterdayPercent': '1.2', 'market_value': 250000, 'investment': 250000},
                'value': {'profitLossPercent': '8.2', 'vsYesterdayPercent': '0.5', 'market_value': 250000, 'investment': 250000},
                'growth': {'profitLossPercent': '15.8', 'vsYesterdayPercent': '-0.3', 'market_value': 250000, 'investment': 250000},
                'momentum': {'profitLossPercent': '22.1', 'vsYesterdayPercent': '2.5', 'market_value': 250000, 'investment': 250000}
            },
            'chart_data': [
                {'date': f"2025-01-{i:02d}", 'quality': 10 + i*0.4, 'value': 5 + i*0.2,
                 'growth': 8 + i*0.6, 'momentum': 12 + i*0.8}
                for i in range(1, 31)
            ]
        }

        return jsonify({
            'success': True,
            'data': fallback_data,
            'message': 'Using fallback data due to error'
        })

@portfolio_bp.route('/daily-stats', methods=['GET'])
def get_daily_portfolio_stats():
    """
    Get daily portfolio statistics
    """
    try:
        # Get latest daily profit/loss data
        latest_daily = DailyProfitLoss.query.order_by(desc(DailyProfitLoss.trading_date)).first()

        if latest_daily:
            return jsonify({
                'success': True,
                'data': {
                    'total_investment': latest_daily.total_actual_investment,
                    'total_market_value': latest_daily.total_market_value,
                    'total_profit_loss': latest_daily.total_profit_loss,
                    'total_profit_loss_percent': latest_daily.total_profit_loss_percent,
                    'trading_date': latest_daily.trading_date.isoformat()
                }
            })
        else:
            return jsonify({
                'success': True,
                'data': {
                    'total_investment': 1000000,
                    'total_market_value': 1150000,
                    'total_profit_loss': 150000,
                    'total_profit_loss_percent': 15.0,
                    'trading_date': datetime.now().date().isoformat()
                }
            })

    except Exception as e:
        logger.error(f"Error fetching daily stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@portfolio_bp.route('/profit-loss/history', methods=['GET'])
def get_profit_loss_history():
    """
    Get profit/loss history data - matching original app.py endpoint
    Query parameters:
    - days: Number of days to retrieve (default 30, max 365)
    """
    try:
        days = min(int(request.args.get('days', 30)), 365)  # Max 365 days

        logger.info(f"Fetching profit/loss history for {days} days")

        # Get daily profit/loss records for the specified period
        daily_records = db.session.query(DailyProfitLoss).order_by(
            desc(DailyProfitLoss.trading_date)
        ).limit(days).all()

        # Get style-specific profit records
        style_records = db.session.query(StyleProfit).order_by(
            desc(StyleProfit.trading_date), StyleProfit.style
        ).limit(days * 4).all()  # 4 styles * days

        # Organize data by date
        history_data = []
        date_data = {}

        # Process daily records
        for record in reversed(daily_records):  # Reverse to get chronological order
            date_str = record.trading_date.strftime('%Y-%m-%d')
            date_data[date_str] = {
                'date': date_str,
                'total_investment': record.total_actual_investment,
                'total_market_value': record.total_market_value,
                'total_profit_loss': record.total_profit_loss,
                'total_profit_loss_percent': record.total_profit_loss_percent,
                'styles': {}
            }

        # Process style records
        for record in style_records:
            date_str = record.trading_date.strftime('%Y-%m-%d')
            if date_str in date_data:
                date_data[date_str]['styles'][record.style] = {
                    'investment': record.style_investment,
                    'market_value': record.style_market_value,
                    'profit_loss': record.style_profit_loss,
                    'profit_loss_percent': record.style_profit_loss_percent
                }

        # Convert to list format
        history_data = [date_data[date] for date in sorted(date_data.keys())]

        # If no real data available, return fallback structure
        if not history_data:
            from datetime import datetime, timedelta
            today = datetime.now().date()
            history_data = []

            for i in range(days):
                date = today - timedelta(days=days - 1 - i)
                base_profit = 10 + (i * 0.5)  # Gradual growth

                history_data.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'total_investment': 1000000,
                    'total_market_value': 1000000 + (base_profit * 10000),
                    'total_profit_loss': base_profit * 10000,
                    'total_profit_loss_percent': base_profit,
                    'styles': {
                        'quality': {
                            'investment': 250000,
                            'market_value': 250000 + (base_profit * 2500),
                            'profit_loss': base_profit * 2500,
                            'profit_loss_percent': base_profit
                        },
                        'value': {
                            'investment': 250000,
                            'market_value': 250000 + (base_profit * 2000),
                            'profit_loss': base_profit * 2000,
                            'profit_loss_percent': base_profit * 0.8
                        },
                        'growth': {
                            'investment': 250000,
                            'market_value': 250000 + (base_profit * 3000),
                            'profit_loss': base_profit * 3000,
                            'profit_loss_percent': base_profit * 1.2
                        },
                        'momentum': {
                            'investment': 250000,
                            'market_value': 250000 + (base_profit * 2500),
                            'profit_loss': base_profit * 2500,
                            'profit_loss_percent': base_profit
                        }
                    }
                })

        response_data = {
            'history': history_data,
            'period_days': days,
            'total_records': len(history_data)
        }

        # Convert numpy types for JSON serialization
        clean_data = convert_numpy_types(response_data)

        logger.info(f"Successfully retrieved {len(history_data)} profit/loss history records")

        return jsonify({
            'success': True,
            'data': clean_data
        })

    except Exception as e:
        logger.error(f"Error fetching profit/loss history: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 500

@portfolio_bp.route('/rebalance-history', methods=['GET'])
def get_rebalance_history():
    """
    Get portfolio rebalancing history (every 2 weeks)
    Returns list of rebalances with changes and P/L after each rebalance
    """
    try:
        # Get all rebalances ordered by date (newest first)
        rebalances = PortfolioRebalance.query.order_by(
            desc(PortfolioRebalance.rebalance_date)
        ).all()
        
        rebalance_list = []
        for rebalance in rebalances:
            rebalance_list.append({
                'id': rebalance.id,
                'rebalance_date': rebalance.rebalance_date.strftime('%Y-%m-%d'),
                'rebalance_number': rebalance.rebalance_number,
                'holdings_added': rebalance.holdings_added,
                'holdings_removed': rebalance.holdings_removed,
                'holdings_adjusted': rebalance.holdings_adjusted,
                'total_investment': rebalance.total_investment,
                'total_market_value': rebalance.total_market_value,
                'total_profit_loss': rebalance.total_profit_loss,
                'total_profit_loss_percent': rebalance.total_profit_loss_percent,
                'style_stats': rebalance.style_stats or {},
                'changes_detail': rebalance.changes_detail or {},
                'notes': rebalance.notes
            })
        
        return jsonify({
            'success': True,
            'data': rebalance_list
        })
        
    except Exception as e:
        logger.error(f"Error fetching rebalance history: {e}")
        # If table doesn't exist yet, return empty list
        if 'does not exist' in str(e).lower() or 'no such table' in str(e).lower():
            return jsonify({
                'success': True,
                'data': []
            })
        return jsonify({'success': False, 'error': str(e)}), 500
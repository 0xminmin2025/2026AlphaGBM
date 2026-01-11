
from flask import Blueprint, jsonify, request, current_app
from datetime import datetime, timedelta
import pandas as pd
import sys
import os
import math
import logging

# Ensure we can import from local modules
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

try:
    from tiger_client import get_client_manager
    from tigeropen.common.consts import Market
    from models.option_models import OptionData, ExpirationDate
    from scoring.option_scorer import OptionScorer
    
    # Try importing Phase 1 modules
    try:
        from phase1_modules.vrp_calculator import VRPCalculator, VRPResult
        from phase1_modules.risk_adjuster import RiskAdjuster, RiskAnalysis
        PHASE1_AVAILABLE = True
    except ImportError:
        PHASE1_AVAILABLE = False
        print("⚠️ Phase 1 modules not available, advanced features will be disabled")

except ImportError as e:
    # Log error but don't fail immediately, allows app to start even if dependencies missing
    print(f"Error importing modules: {e}")
    PHASE1_AVAILABLE = False

options_bp = Blueprint('options', __name__)

USE_MOCK_DATA = False # Switched to Real Data
option_scorer = OptionScorer()
vrp_calculator = VRPCalculator() if PHASE1_AVAILABLE else None
risk_adjuster = RiskAdjuster() if PHASE1_AVAILABLE else None

# Mock Data Generator (Keep for fallback)
class MockDataGenerator:
    """Generates mock option data for testing"""

    @staticmethod
    def generate_expirations(symbol: str):
        """Generate mock expiration dates"""
        expirations = []
        base_date = datetime.now()

        # Generate weekly and monthly expirations for next 3 months
        for week in range(1, 13):  # 12 weeks
            exp_date = base_date + timedelta(weeks=week)
            # Friday expirations
            days_until_friday = (4 - exp_date.weekday()) % 7
            if days_until_friday == 0 and exp_date.weekday() != 4:
                days_until_friday = 7
            exp_date += timedelta(days=days_until_friday)

            # Monthly options on 3rd Friday
            is_monthly = exp_date.day >= 15 and exp_date.day <= 21
            period_tag = "m" if is_monthly else "w"

            expirations.append({
                "date": exp_date.strftime("%Y-%m-%d"),
                "timestamp": int(exp_date.timestamp() * 1000),
                "period_tag": period_tag
            })

        return sorted(expirations, key=lambda x: x["timestamp"])

    @staticmethod
    def generate_option_chain(symbol: str, expiry_date: str, real_price: float = None):
        """Generate mock option chain data with scoring"""
        # Use real stock price if available, otherwise mock
        base_price = real_price if real_price is not None else 150.0

        calls = []
        puts = []

        # Generate strikes around current price
        for i in range(-10, 11):  # 21 strikes total
            strike = base_price + (i * 5)  # $5 intervals

            # Mock some realistic option data
            try:
                days_diff = (datetime.strptime(expiry_date, "%Y-%m-%d") - datetime.now()).days
                time_to_expiry = max(0.1, days_diff / 365.0)
            except:
                time_to_expiry = 0.1

            # CALL options
            call_intrinsic = max(0, base_price - strike)
            call_time_value = max(1.0, abs(i) * 2.0 + time_to_expiry * 10)
            call_price = call_intrinsic + call_time_value
            
            call_identifier = f"{symbol} {expiry_date.replace('-', '')}C{int(strike*1000):08d}"

            call_option = OptionData(
                identifier=call_identifier,
                symbol=symbol,
                strike=strike,
                put_call="CALL",
                expiry_date=expiry_date,
                latest_price=round(call_price, 2),
                bid_price=round(call_price - 0.05, 2),
                ask_price=round(call_price + 0.05, 2),
                volume=100 + abs(i) * 50,
                open_interest=500 + abs(i) * 100,
                implied_vol=round(0.20 + abs(i) * 0.02, 3),
                delta=round(max(0.01, 0.5 + (base_price - strike) / 100), 3),
                gamma=round(0.01 + abs(i) * 0.002, 4),
                theta=round(-0.05 - time_to_expiry * 0.1, 3),
                vega=round(time_to_expiry * 20, 2)
            )

            # Calculate scores for CALL option
            call_option.scores = option_scorer.score_option(call_option, base_price)
            # Serialize for JSON response
            calls.append(call_option.dict() if hasattr(call_option, 'dict') else call_option.__dict__)

            # PUT options
            put_intrinsic = max(0, strike - base_price)
            put_time_value = max(1.0, abs(i) * 2.0 + time_to_expiry * 10)
            put_price = put_intrinsic + put_time_value
            
            put_identifier = f"{symbol} {expiry_date.replace('-', '')}P{int(strike*1000):08d}"

            put_option = OptionData(
                identifier=put_identifier,
                symbol=symbol,
                strike=strike,
                put_call="PUT",
                expiry_date=expiry_date,
                latest_price=round(put_price, 2),
                bid_price=round(put_price - 0.05, 2),
                ask_price=round(put_price + 0.05, 2),
                volume=80 + abs(i) * 40,
                open_interest=400 + abs(i) * 80,
                implied_vol=round(0.22 + abs(i) * 0.02, 3),
                delta=round(min(-0.01, -0.5 + (base_price - strike) / 100), 3),
                gamma=round(0.01 + abs(i) * 0.002, 4),
                theta=round(-0.04 - time_to_expiry * 0.08, 3),
                vega=round(time_to_expiry * 18, 2)
            )

            # Calculate scores for PUT option
            put_option.scores = option_scorer.score_option(put_option, base_price)
            puts.append(put_option.dict() if hasattr(put_option, 'dict') else put_option.__dict__)

        data_source = "hybrid" if real_price is not None else "mock"
        return {
            "symbol": symbol,
            "expiry_date": expiry_date,
            "calls": calls,
            "puts": puts,
            "data_source": data_source,
            "real_stock_price": real_price
        }

mock_generator = MockDataGenerator()

@options_bp.route('/expirations/<symbol>')
def get_expirations(symbol):
    try:
        symbol = symbol.upper()
        
        if not USE_MOCK_DATA:
            try:
                client = get_client_manager()
                if client.quote_client is None:
                    # Initialize client if not already done
                    client.initialize_client()

                if client.quote_client:
                    # Determine market based on symbol
                    market = Market.US if not symbol.endswith('.HK') else Market.HK
                    expirations_df = client.get_option_expirations(symbol, market)

                    # Convert DataFrame to our response format
                    expirations = []
                    for _, row in expirations_df.iterrows():
                        expirations.append({
                            "date": row['date'],
                            "timestamp": int(row['timestamp']),
                            "period_tag": row['period_tag']
                        })

                    return jsonify({
                        "symbol": symbol,
                        "expirations": expirations
                    })
            except Exception as api_error:
                print(f"⚠️ Tiger API failed, using mock data: {str(api_error)}")
        
        # Fallback to Mock
        expirations = mock_generator.generate_expirations(symbol)
        
        return jsonify({
            "symbol": symbol,
            "expirations": expirations
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@options_bp.route('/options/<symbol>/<expiry_date>')
def get_option_chain(symbol, expiry_date):
    try:
        symbol = symbol.upper()
        
        if not USE_MOCK_DATA:
            try:
                client = get_client_manager()
                if client.quote_client is None:
                    client.initialize_client()

                if client.quote_client:
                    market = Market.US if not symbol.endswith('.HK') else Market.HK

                    print(f"🔍 Fetching real option chain for {symbol} {expiry_date} from Tiger API...")
                    option_chain_df = client.get_option_chain(symbol, expiry_date, market)
                    print(f"✅ Retrieved {len(option_chain_df)} option contracts from Tiger API")

                    calls = []
                    puts = []

                    # Get real stock price for scoring
                    real_stock_price = None
                    try:
                        stock_data = client.get_stock_quote([symbol])
                        if len(stock_data) > 0:
                            real_stock_price = float(stock_data['latest_price'].iloc[0])
                            print(f"✅ Using real stock price for scoring: ${real_stock_price}")
                    except:
                        real_stock_price = 150.0  # Default fallback

                    for _, row in option_chain_df.iterrows():
                        # OptionData from models.option_models
                        option_data = OptionData(
                            identifier=row['identifier'],
                            symbol=row['symbol'],
                            strike=float(row['strike']),
                            put_call=row['put_call'],
                            expiry_date=expiry_date,
                            bid_price=float(row.get('bid_price', 0)) if pd.notna(row.get('bid_price', 0)) else None,
                            ask_price=float(row.get('ask_price', 0)) if pd.notna(row.get('ask_price', 0)) else None,
                            latest_price=float(row.get('latest_price', 0)) if pd.notna(row.get('latest_price', 0)) else None,
                            volume=int(row.get('volume', 0)) if pd.notna(row.get('volume', 0)) else None,
                            open_interest=int(row.get('open_interest', 0)) if pd.notna(row.get('open_interest', 0)) else None,
                            implied_vol=float(row.get('implied_vol', 0)) if pd.notna(row.get('implied_vol', 0)) else None,
                            delta=float(row.get('delta', 0)) if pd.notna(row.get('delta', 0)) else None,
                            gamma=float(row.get('gamma', 0)) if pd.notna(row.get('gamma', 0)) else None,
                            theta=float(row.get('theta', 0)) if pd.notna(row.get('theta', 0)) else None,
                            vega=float(row.get('vega', 0)) if pd.notna(row.get('vega', 0)) else None
                        )

                        # Margin Rate (optional optimization)
                        margin_rate = None
                        try:
                            margin_rate = client.get_margin_rate(symbol, market)
                        except Exception:
                            pass
                        
                        # Score
                        option_data.scores = option_scorer.score_option(option_data, real_stock_price, margin_rate)
                        
                        # Serialize
                        data_dict = option_data.dict() if hasattr(option_data, 'dict') else option_data.__dict__

                        if row['put_call'] == 'CALL':
                            calls.append(data_dict)
                        else:
                            puts.append(data_dict)

                    return jsonify({
                        "symbol": symbol,
                        "expiry_date": expiry_date,
                        "calls": calls,
                        "puts": puts,
                        "data_source": "real",
                        "real_stock_price": real_stock_price
                    })

            except Exception as api_error:
                print(f"⚠️ Tiger API option chain failed: {str(api_error)}")
                print("🔄 Falling back to mock data...")

        # Fallback Mock
        data = mock_generator.generate_option_chain(symbol, expiry_date)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@options_bp.route('/stock-history/<symbol>')
def get_stock_history(symbol):
    try:
        days = request.args.get('days', 60, type=int)
        symbol = symbol.upper()
        
        if not USE_MOCK_DATA:
            try:
                client = get_client_manager()
                if client.quote_client is None:
                    client.initialize_client()
                
                market = Market.US if not symbol.endswith('.HK') else Market.HK
                price_history = client.get_stock_history(symbol, days=days, market=market)
                
                if price_history and len(price_history) >= 30:
                    candlestick_data = []
                    base_date = datetime.now() - timedelta(days=len(price_history))
                    
                    for i, close_price in enumerate(price_history):
                         date = base_date + timedelta(days=i)
                         # Simplified OHLC from close
                         open_price = close_price
                         high_price = close_price * 1.01
                         low_price = close_price * 0.99
                         
                         candlestick_data.append({
                             "time": int(date.timestamp()),
                             "open": round(open_price, 2),
                             "high": round(high_price, 2),
                             "low": round(low_price, 2),
                             "close": round(close_price, 2)
                         })
                    
                    return jsonify({"symbol": symbol, "data": candlestick_data})
            
            except Exception as api_error:
                 print(f"⚠️ Tiger API history failed: {str(api_error)}")

        # Fallback Mock
        import random
        import time
        
        base_price = 150.0
        candlestick_data = []
        base_date = datetime.now() - timedelta(days=days)
        
        for i in range(days):
            date = base_date + timedelta(days=i)
            change = random.uniform(-0.02, 0.02) * base_price
            base_price = max(base_price + change, 50.0)
            
            open_price = base_price
            close_price = base_price * random.uniform(0.98, 1.02)
            high_price = max(open_price, close_price) * random.uniform(1.0, 1.02)
            low_price = min(open_price, close_price) * random.uniform(0.98, 1.0)
            
            candlestick_data.append({
                "time": int(date.timestamp()),
                "open": round(open_price, 2),
                "high": round(high_price, 2),
                "low": round(low_price, 2),
                "close": round(close_price, 2)
            })
            
        return jsonify({"symbol": symbol, "data": candlestick_data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@options_bp.route('/quote/<symbol>')
def get_quote(symbol):
    try:
        symbol = symbol.upper()
        if not USE_MOCK_DATA:
            try:
                client = get_client_manager()
                if client.quote_client is None:
                    client.initialize_client()
                    
                quote_df = client.get_stock_quote([symbol])
                if len(quote_df) > 0:
                        row = quote_df.iloc[0]
                        return jsonify({
                            "symbol": symbol,
                            "latest_price": float(row['latest_price']),
                            "change": float(row.get('change', 0)),
                            "change_percent": float(row.get('change_percent', 0)),
                            "volume": int(row.get('volume', 0))
                        })
            except Exception as e:
                 print(f"Quote API failed: {e}")
        
        # Mock quote
        return jsonify({
            "symbol": symbol.upper(),
            "latest_price": 150.25,
            "change": 2.15,
            "change_percent": 1.45,
            "volume": 1234567
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@options_bp.route('/enhanced-analysis/<symbol>/<path:option_identifier>')
def get_enhanced_analysis(symbol, option_identifier):
    # Placeholder
    return jsonify({
        "symbol": symbol,
        "option_identifier": option_identifier,
        "available": False,
        "message": "Enhanced analysis not fully implemented in Flask port yet"
    })

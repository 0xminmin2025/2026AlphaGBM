"""
Option Service Backend Logic
Ported from new_options_module/option_service.py and consolidated with Flask logic
"""

from datetime import datetime, timedelta
import math
import pandas as pd
from typing import List, Optional, Union
import random
import time
import numpy as np

# Internal services
from .tiger_client import get_client_manager
from tigeropen.common.consts import Market
from .option_models import OptionData, OptionChainResponse, ExpirationDate, ExpirationResponse, StockQuote, EnhancedAnalysisResponse, VRPResult as VRPResultModel, RiskAnalysis as RiskAnalysisModel
from .option_scorer import OptionScorer

# Try importing Phase 1 modules
try:
    from .phase1.vrp_calculator import VRPCalculator, VRPResult
    from .phase1.risk_adjuster import RiskAdjuster, RiskAnalysis, RiskLevel
    PHASE1_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Phase 1 modules not available: {e}")
    PHASE1_AVAILABLE = False

# Configuration
USE_MOCK_DATA = False # Default to Real Data

option_scorer = OptionScorer()
vrp_calculator = VRPCalculator() if PHASE1_AVAILABLE else None
risk_adjuster = RiskAdjuster() if PHASE1_AVAILABLE else None

class MockDataGenerator:
    """Generates mock option data for testing"""

    @staticmethod
    def generate_expirations(symbol: str) -> List[ExpirationDate]:
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

            expirations.append(ExpirationDate(
                date=exp_date.strftime("%Y-%m-%d"),
                timestamp=int(exp_date.timestamp() * 1000),
                period_tag=period_tag
            ))

        return sorted(expirations, key=lambda x: x.timestamp)

    @staticmethod
    def generate_option_chain(symbol: str, expiry_date: str, real_price: float = None) -> OptionChainResponse:
        """Generate mock option chain data with scoring"""
        base_price = real_price if real_price is not None else 150.0

        calls = []
        puts = []

        for i in range(-10, 11):  # 21 strikes total
            strike = base_price + (i * 5)  # $5 intervals

            try:
                days_diff = (datetime.strptime(expiry_date, "%Y-%m-%d") - datetime.now()).days
                time_to_expiry = max(0.1, days_diff / 365.0)
            except:
                time_to_expiry = 0.1

            # CALL options
            call_intrinsic = max(0, base_price - strike)
            call_time_value = max(1.0, abs(i) * 2.0 + time_to_expiry * 10)
            call_price = call_intrinsic + call_time_value

            call_option = OptionData(
                identifier=f"{symbol} {expiry_date.replace('-', '')}C{int(strike*1000):08d}",
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
            call_option.scores = option_scorer.score_option(call_option, base_price)
            calls.append(call_option)

            # PUT options
            put_intrinsic = max(0, strike - base_price)
            put_time_value = max(1.0, abs(i) * 2.0 + time_to_expiry * 10)
            put_price = put_intrinsic + put_time_value

            put_option = OptionData(
                identifier=f"{symbol} {expiry_date.replace('-', '')}P{int(strike*1000):08d}",
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
            put_option.scores = option_scorer.score_option(put_option, base_price)
            puts.append(put_option)

        data_source = "hybrid" if real_price is not None else "mock"
        return OptionChainResponse(
            symbol=symbol,
            expiry_date=expiry_date,
            calls=calls,
            puts=puts,
            data_source=data_source,
            real_stock_price=base_price  # Always return the price used for option calculations
        )

mock_generator = MockDataGenerator()

class OptionsService:

    @staticmethod
    def get_expirations(symbol: str) -> ExpirationResponse:
        try:
            symbol = symbol.upper()
            if not USE_MOCK_DATA:
                try:
                    client = get_client_manager()
                    if client.quote_client is None:
                        client.initialize_client()

                    if client.quote_client:
                        market = Market.US if not symbol.endswith('.HK') else Market.HK
                        expirations_df = client.get_option_expirations(symbol, market)
                        expirations = []
                        for _, row in expirations_df.iterrows():
                            expirations.append(ExpirationDate(
                                date=row['date'],
                                timestamp=int(row['timestamp']),
                                period_tag=row['period_tag']
                            ))
                        return ExpirationResponse(symbol=symbol, expirations=expirations)
                except Exception as e:
                    print(f"⚠️ Tiger API failed: {e}")

            expirations = mock_generator.generate_expirations(symbol)
            return ExpirationResponse(symbol=symbol, expirations=expirations)
        except Exception as e:
             raise e

    @staticmethod
    def get_option_chain(symbol: str, expiry_date: str) -> OptionChainResponse:
        try:
            symbol = symbol.upper()
            
            # Validate format
            try:
                datetime.strptime(expiry_date, "%Y-%m-%d")
            except ValueError:
                raise ValueError("Invalid date format. Use YYYY-MM-DD")

            if not USE_MOCK_DATA:
                try:
                    client = get_client_manager()
                    if client.quote_client is None:
                        client.initialize_client()

                    if client.quote_client:
                        market = Market.US if not symbol.endswith('.HK') else Market.HK
                        option_chain_df = client.get_option_chain(symbol, expiry_date, market)
                        
                        calls = []
                        puts = []
                        real_stock_price = 150.0  # Default price
                        try:
                            stock_data = client.get_stock_quote([symbol])
                            if len(stock_data) > 0:
                                real_stock_price = float(stock_data['latest_price'].iloc[0])
                        except:
                            pass  # Keep default price

                        for _, row in option_chain_df.iterrows():
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

                            margin_rate = client.get_margin_rate(symbol, market)
                            option_data.scores = option_scorer.score_option(option_data, real_stock_price, margin_rate)

                            if row['put_call'] == 'CALL':
                                calls.append(option_data)
                            else:
                                puts.append(option_data)

                        return OptionChainResponse(
                            symbol=symbol,
                            expiry_date=expiry_date,
                            calls=calls,
                            puts=puts,
                            data_source="real",
                            real_stock_price=real_stock_price
                        )
                except Exception as e:
                    print(f"⚠️ Tiger API failed: {e}")
            
            # Mock fallback
            try:
                 client = get_client_manager()
                 if client.quote_client:
                     stock_data = client.get_stock_quote([symbol])
                     if len(stock_data) > 0:
                         real_price = float(stock_data['latest_price'].iloc[0])
                         return mock_generator.generate_option_chain(symbol, expiry_date, real_price)
            except:
                pass
            return mock_generator.generate_option_chain(symbol, expiry_date)

        except Exception as e:
            raise e

    @staticmethod
    def get_stock_history(symbol: str, days: int = 60):
        """Get stock OHLC history data using yfinance"""
        try:
            import yfinance as yf

            symbol = symbol.upper()
            print(f"Fetching {days} days of history for {symbol} using yfinance...")

            # Use yfinance to get real OHLC data
            stock = yf.Ticker(symbol)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days + 10)  # Extra days to ensure enough data

            hist = stock.history(start=start_date, end=end_date)

            if hist.empty:
                print(f"No history data returned for {symbol}")
                return {"symbol": symbol, "data": [], "error": "No data available"}

            # Convert to candlestick format for lightweight-charts
            candlestick_data = []
            for date, row in hist.iterrows():
                # Convert pandas timestamp to unix timestamp (seconds)
                timestamp = int(date.timestamp())
                candlestick_data.append({
                    "time": timestamp,
                    "open": round(float(row['Open']), 2),
                    "high": round(float(row['High']), 2),
                    "low": round(float(row['Low']), 2),
                    "close": round(float(row['Close']), 2)
                })

            # Sort by time ascending
            candlestick_data.sort(key=lambda x: x['time'])

            # Limit to requested days
            if len(candlestick_data) > days:
                candlestick_data = candlestick_data[-days:]

            print(f"Successfully fetched {len(candlestick_data)} days of OHLC data for {symbol}")
            return {"symbol": symbol, "data": candlestick_data}

        except Exception as e:
            print(f"Error fetching stock history for {symbol}: {e}")
            return {"symbol": symbol, "data": [], "error": str(e)}

    @staticmethod
    def get_stock_quote(symbol):
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
                        return StockQuote(
                            symbol=symbol,
                            latest_price=float(row['latest_price']),
                            change=float(row.get('change', 0)),
                            change_percent=float(row.get('change_percent', 0)),
                            volume=int(row.get('volume', 0))
                        )
                except Exception:
                    pass
            
            return StockQuote(
                symbol=symbol,
                latest_price=150.25,
                change=2.15,
                change_percent=1.45,
                volume=1234567
            )
        except Exception as e:
            raise e

    @staticmethod
    def get_enhanced_analysis(symbol: str, option_identifier: str) -> EnhancedAnalysisResponse:
        if not PHASE1_AVAILABLE or not vrp_calculator or not risk_adjuster:
             return EnhancedAnalysisResponse(symbol=symbol, option_identifier=option_identifier, available=False)
        
        try:
            symbol = symbol.upper()
            
            # 1. Price History
            client = get_client_manager()
            if client.quote_client is None:
                client.initialize_client()
            
            market = Market.US if not symbol.endswith('.HK') else Market.HK
            price_history = client.get_stock_history(symbol, days=60, market=market)
            
            if not price_history or len(price_history) < 30:
                return EnhancedAnalysisResponse(
                    symbol=symbol, option_identifier=option_identifier, vrp_result=None, risk_analysis=None, available=True
                )
            
            # 2. VRP
            import math
            import numpy as np
            returns = []
            for i in range(1, len(price_history)):
                if price_history[i-1] > 0:
                     returns.append(math.log(price_history[i] / price_history[i-1]))
            
            if returns:
                hist_vol = np.std(returns) * math.sqrt(252)
                estimated_iv = hist_vol # Placeholder
                vrp_result_data = vrp_calculator.calculate_vrp_result(
                    current_iv=estimated_iv,
                    price_history=price_history
                )
                vrp_result = VRPResultModel(
                    vrp=vrp_result_data.vrp,
                    iv=vrp_result_data.iv,
                    rv_forecast=vrp_result_data.rv_forecast,
                    iv_rank=vrp_result_data.iv_rank,
                    iv_percentile=vrp_result_data.iv_percentile,
                    recommendation=vrp_result_data.recommendation
                )
            else:
                vrp_result = None

            return EnhancedAnalysisResponse(
                symbol=symbol,
                option_identifier=option_identifier,
                vrp_result=vrp_result,
                risk_analysis=None, # Requires specific option data retrieval which is separate
                available=True
            )
        except Exception as e:
             print(f"Error in enhanced analysis: {e}")
             return EnhancedAnalysisResponse(symbol=symbol, option_identifier=option_identifier, available=False)

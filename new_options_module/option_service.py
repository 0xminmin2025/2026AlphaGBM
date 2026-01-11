"""
Option Query Backend Service with Option Scoring
A FastAPI-based service for querying stock option data with quantitative scoring

Provides endpoints for:
- Getting option expiration dates
- Getting option chains (CALL and PUT data) with scoring metrics
- Basic stock quotes

Features quantitative option scoring with SPRV, SCRV, BCRV algorithms
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, validator
from typing import List, Optional, Union
from datetime import datetime, timedelta
import pandas as pd
import json
import os

# Import our Tiger client
from tiger_client import get_client_manager
from tigeropen.common.consts import Market

# Import new models and scoring
from models.option_models import (
    OptionData, OptionChainResponse, ExpirationDate,
    ExpirationResponse, StockQuote, OptionScores,
    VRPResult as VRPResultModel, RiskAnalysis as RiskAnalysisModel,
    EnhancedAnalysisResponse
)
from scoring.option_scorer import OptionScorer

# Import Phase 1 modules
try:
    from phase1_modules.vrp_calculator import VRPCalculator, VRPResult
    from phase1_modules.risk_adjuster import RiskAdjuster, RiskAnalysis, RiskLevel
    PHASE1_AVAILABLE = True
except ImportError:
    PHASE1_AVAILABLE = False
    print("⚠️ Phase 1 modules not available, advanced features will be disabled")

# Configuration - Set to False to use real Tiger API data
USE_MOCK_DATA = False

# Initialize option scorer
option_scorer = OptionScorer()

# Initialize Phase 1 modules if available
vrp_calculator = VRPCalculator() if PHASE1_AVAILABLE else None
risk_adjuster = RiskAdjuster() if PHASE1_AVAILABLE else None

app = FastAPI(
    title="Option Query Service with Scoring",
    description="A backend service for querying stock option data with quantitative scoring algorithms",
    version="2.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock data generator
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
        # Use real stock price if available, otherwise mock
        base_price = real_price if real_price is not None else 150.0

        calls = []
        puts = []

        # Generate strikes around current price
        for i in range(-10, 11):  # 21 strikes total
            strike = base_price + (i * 5)  # $5 intervals

            # Mock some realistic option data
            time_to_expiry = max(0.1, (datetime.strptime(expiry_date, "%Y-%m-%d") - datetime.now()).days / 365.0)

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

            # Calculate scores for CALL option
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

            # Calculate scores for PUT option
            put_option.scores = option_scorer.score_option(put_option, base_price)
            puts.append(put_option)

        data_source = "hybrid" if real_price is not None else "mock"
        return OptionChainResponse(
            symbol=symbol,
            expiry_date=expiry_date,
            calls=calls,
            puts=puts,
            data_source=data_source,
            real_stock_price=real_price
        )

# Global mock data generator
mock_generator = MockDataGenerator()

# API Routes
@app.get("/")
async def frontend():
    """
    Serve the frontend HTML page
    """
    try:
        return FileResponse('frontend.html')
    except FileNotFoundError:
        return HTMLResponse("""
        <html>
            <head>
                <title>Option Query Service</title>
            </head>
            <body>
                <h1>🚀 Option Query Service</h1>
                <h2>Available Endpoints:</h2>
                <ul>
                    <li><a href="/docs">📚 API Documentation</a></li>
                    <li><code>GET /expirations/{symbol}</code> - Get option expiration dates</li>
                    <li><code>GET /options/{symbol}/{expiry_date}</code> - Get option chain data</li>
                    <li><code>GET /quote/{symbol}</code> - Get basic stock quote</li>
                </ul>
                <h2>Example Usage:</h2>
                <ul>
                    <li><a href="/expirations/AAPL">/expirations/AAPL</a></li>
                    <li><a href="/options/AAPL/2024-01-19">/options/AAPL/2024-01-19</a></li>
                    <li><a href="/quote/AAPL">/quote/AAPL</a></li>
                </ul>
                <p><strong>Note:</strong> Frontend HTML file not found. Please ensure frontend.html is in the same directory.</p>
            </body>
        </html>
        """)

@app.get("/expirations/{symbol}", response_model=ExpirationResponse)
async def get_expirations(symbol: str):
    """
    Get option expiration dates for a symbol

    Args:
        symbol: Stock symbol (e.g., AAPL, TSLA, NVDA)

    Returns:
        ExpirationResponse: List of available expiration dates
    """
    try:
        symbol = symbol.upper()

        # Try real Tiger API data if configured
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
                        expirations.append(ExpirationDate(
                            date=row['date'],
                            timestamp=int(row['timestamp']),
                            period_tag=row['period_tag']
                        ))

                    return ExpirationResponse(
                        symbol=symbol,
                        expirations=expirations
                    )
            except Exception as api_error:
                print(f"⚠️ Tiger API failed, using mock data: {str(api_error)}")

        # Fall back to mock data
        expirations = mock_generator.generate_expirations(symbol)

        return ExpirationResponse(
            symbol=symbol,
            expirations=expirations
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching expirations: {str(e)}")

@app.get("/options/{symbol}/{expiry_date}", response_model=OptionChainResponse)
async def get_option_chain(symbol: str, expiry_date: str):
    """
    Get option chain data for a symbol and expiration date

    Args:
        symbol: Stock symbol (e.g., AAPL, TSLA, NVDA)
        expiry_date: Expiration date in YYYY-MM-DD format

    Returns:
        OptionChainResponse: Complete option chain with CALLS and PUTS
    """
    try:
        symbol = symbol.upper()

        # Validate date format
        try:
            datetime.strptime(expiry_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

        # Try to get real Tiger API option chain data
        if not USE_MOCK_DATA:
            try:
                client = get_client_manager()
                if client.quote_client is None:
                    client.initialize_client()

                if client.quote_client:
                    # Determine market based on symbol
                    market = Market.US if not symbol.endswith('.HK') else Market.HK

                    print(f"🔍 Fetching real option chain for {symbol} {expiry_date} from Tiger API...")

                    # Get real option chain with Greeks
                    option_chain_df = client.get_option_chain(symbol, expiry_date, market)

                    print(f"✅ Retrieved {len(option_chain_df)} option contracts from Tiger API")

                    # Convert DataFrame to our response format
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

                        # Try to get margin rate from API (for more accurate margin calculation)
                        margin_rate = None
                        try:
                            margin_rate = client.get_margin_rate(symbol, market)
                            if margin_rate:
                                print(f"✅ Using margin rate {margin_rate*100:.1f}% for {symbol}")
                        except Exception as e:
                            print(f"⚠️ Could not fetch margin rate, using standard rules: {str(e)}")
                        
                        # Calculate scores for real option data (with margin_rate if available)
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

            except Exception as api_error:
                print(f"⚠️ Tiger API option chain failed: {str(api_error)}")
                print("🔄 Falling back to mock data...")

        # Fall back to mock data if API fails
        try:
            # Try to get real stock price for mock data with scoring
            client = get_client_manager()
            if client.quote_client:
                stock_data = client.get_stock_quote([symbol])
                if len(stock_data) > 0:
                    real_price = float(stock_data['latest_price'].iloc[0])
                    print(f"✅ Using real stock price for {symbol}: ${real_price}")
                    option_chain = mock_generator.generate_option_chain(symbol, expiry_date, real_price)
                    return option_chain
        except:
            pass

        # Pure mock data as final fallback (will still include scoring)
        option_chain = mock_generator.generate_option_chain(symbol, expiry_date)
        return option_chain

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching option chain: {str(e)}")

@app.get("/quote/{symbol}", response_model=StockQuote)
async def get_stock_quote(symbol: str):
    """
    Get basic stock quote data

    Args:
        symbol: Stock symbol (e.g., AAPL, TSLA, NVDA)

    Returns:
        StockQuote: Basic stock quote information
    """
    try:
        symbol = symbol.upper()

        # Try real Tiger API data if configured
        if not USE_MOCK_DATA:
            try:
                client = get_client_manager()
                if client.quote_client is None:
                    client.initialize_client()

                if client.quote_client:
                    quote_df = client.get_stock_quote([symbol])

                    if len(quote_df) > 0:
                        row = quote_df.iloc[0]
                        return StockQuote(
                            symbol=symbol,
                            latest_price=float(row['latest_price']),
                            change=float(row.get('change', 0)),
                            change_percent=float(row.get('change_percent', 0)),
                            volume=int(row.get('volume', 0)),
                            market_cap=None  # Not available in basic quote
                        )
            except Exception as api_error:
                print(f"⚠️ Tiger API failed, using mock data: {str(api_error)}")

        # Fall back to mock data
        return StockQuote(
            symbol=symbol,
            latest_price=150.25,
            change=2.15,
            change_percent=1.45,
            volume=1234567,
            market_cap=2500000000000
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stock quote: {str(e)}")

@app.get("/stock-history/{symbol}")
async def get_stock_history(symbol: str, days: int = Query(60, ge=30, le=200)):
    """
    Get historical stock price data for chart display
    
    Args:
        symbol: Stock symbol (e.g., AAPL, TSLA, NVDA)
        days: Number of days of history to retrieve (30-200, default 60)
    
    Returns:
        JSON with historical price data in candlestick format
    """
    try:
        symbol = symbol.upper()
        
        # Try real Tiger API data if configured
        if not USE_MOCK_DATA:
            try:
                client = get_client_manager()
                if client.quote_client is None:
                    client.initialize_client()
                
                market = Market.US if not symbol.endswith('.HK') else Market.HK
                price_history = client.get_stock_history(symbol, days=days, market=market)
                
                if price_history and len(price_history) >= 30:
                    # Convert price history to candlestick format
                    # For simplicity, we'll use close prices and generate OHLC from them
                    from datetime import datetime, timedelta
                    import time
                    
                    candlestick_data = []
                    base_date = datetime.now() - timedelta(days=len(price_history))
                    
                    for i, close_price in enumerate(price_history):
                        # Generate OHLC from close price (simplified)
                        # In production, you'd want actual OHLC data from the API
                        date = base_date + timedelta(days=i)
                        # Use close as base, generate open/high/low with small variations
                        open_price = close_price * (1 + (i % 3 - 1) * 0.005)  # Small variation
                        high_price = max(open_price, close_price) * 1.01
                        low_price = min(open_price, close_price) * 0.99
                        
                        candlestick_data.append({
                            "time": int(time.mktime(date.timetuple())),
                            "open": round(open_price, 2),
                            "high": round(high_price, 2),
                            "low": round(low_price, 2),
                            "close": round(close_price, 2)
                        })
                    
                    return {"symbol": symbol, "data": candlestick_data}
            
            except Exception as api_error:
                print(f"⚠️ Tiger API failed for history: {str(api_error)}")
        
        # Return mock data if API fails
        from datetime import datetime, timedelta
        import time
        import random
        
        base_price = 150.0
        candlestick_data = []
        base_date = datetime.now() - timedelta(days=days)
        
        for i in range(days):
            date = base_date + timedelta(days=i)
            # Generate realistic price movement
            change = random.uniform(-0.02, 0.02) * base_price
            base_price = max(base_price + change, 50.0)  # Prevent negative prices
            
            open_price = base_price
            close_price = base_price * random.uniform(0.98, 1.02)
            high_price = max(open_price, close_price) * random.uniform(1.0, 1.02)
            low_price = min(open_price, close_price) * random.uniform(0.98, 1.0)
            
            candlestick_data.append({
                "time": int(time.mktime(date.timetuple())),
                "open": round(open_price, 2),
                "high": round(high_price, 2),
                "low": round(low_price, 2),
                "close": round(close_price, 2)
            })
        
        return {"symbol": symbol, "data": candlestick_data}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stock history: {str(e)}")

@app.get("/config")
async def get_config():
    """
    Get current service configuration
    """
    client = get_client_manager()
    tiger_status = "not_initialized"

    if client.quote_client is not None:
        tiger_status = "initialized"
    elif not USE_MOCK_DATA:
        # Try to initialize and check status
        try:
            if client.initialize_client():
                tiger_status = "working"
            else:
                tiger_status = "auth_failed"
        except:
            tiger_status = "auth_failed"

    return {
        "data_source": "mock" if USE_MOCK_DATA else "tiger_api",
        "tiger_api_status": tiger_status,
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/config/data-source/{source}")
async def set_data_source(source: str):
    """
    Set data source (mock or real)

    Args:
        source: Either 'mock' or 'real'
    """
    global USE_MOCK_DATA

    if source.lower() == 'mock':
        USE_MOCK_DATA = True
        return {"message": "Switched to mock data", "data_source": "mock"}
    elif source.lower() == 'real':
        USE_MOCK_DATA = False
        # Try to initialize Tiger API client
        client = get_client_manager()
        try:
            if client.initialize_client():
                return {"message": "Switched to real Tiger API data", "data_source": "tiger_api"}
            else:
                USE_MOCK_DATA = True  # Fall back to mock
                return {"message": "Failed to initialize Tiger API, staying with mock data", "data_source": "mock"}
        except Exception as e:
            USE_MOCK_DATA = True  # Fall back to mock
            return {"message": f"Tiger API initialization failed: {str(e)}, using mock data", "data_source": "mock"}
    else:
        raise HTTPException(status_code=400, detail="Invalid data source. Use 'mock' or 'real'")

@app.get("/enhanced-analysis/{symbol}/{option_identifier}", response_model=EnhancedAnalysisResponse)
async def get_enhanced_analysis(symbol: str, option_identifier: str):
    """
    Get enhanced analysis (VRP and Risk Analysis) for an option
    
    Args:
        symbol: Stock symbol (e.g., AAPL)
        option_identifier: Option identifier (e.g., "AAPL 20250117C00150000")
    
    Returns:
        EnhancedAnalysisResponse: VRP and risk analysis results
    """
    if not PHASE1_AVAILABLE or not vrp_calculator or not risk_adjuster:
        return EnhancedAnalysisResponse(
            symbol=symbol.upper(),
            option_identifier=option_identifier,
            available=False
        )
    
    try:
        symbol = symbol.upper()
        
        # Get option data from option chain to extract IV and other metrics
        # First, try to get the option from a recent query or fetch it
        # For now, we'll need to parse the identifier or fetch from option chain
        # This is a simplified version - in production, you might want to cache option data
        
        # Get current stock price and implied volatility
        # We'll need to fetch the option chain to get IV, or accept IV as a parameter
        # For MVP, let's fetch price history and use a default IV if not available
        
        # 1. Get price history
        client = get_client_manager()
        if client.quote_client is None:
            client.initialize_client()
        
        market = Market.US if not symbol.endswith('.HK') else Market.HK
        price_history = client.get_stock_history(symbol, days=60, market=market)
        
        if not price_history or len(price_history) < 30:
            # Data insufficient, return None for VRP
            return EnhancedAnalysisResponse(
                symbol=symbol,
                option_identifier=option_identifier,
                vrp_result=None,
                risk_analysis=None,
                available=True
            )
        
        # 2. Get current stock price
        try:
            stock_quote = client.get_stock_quote([symbol])
            if not stock_quote.empty:
                current_price = float(stock_quote['latest_price'].iloc[0])
            else:
                # Use last price from history
                current_price = price_history[-1] if price_history else 0
        except:
            current_price = price_history[-1] if price_history else 0
        
        # 3. Parse option identifier to extract strike, expiry, type
        # Format: "AAPL 20250117C00150000" or similar
        # For MVP, we'll need IV from option chain - let's make it optional
        # If IV is not available, we'll skip VRP calculation
        
        # Try to get IV from option chain (simplified - in production, cache this)
        # For now, we'll calculate VRP with a placeholder IV
        # In production, you should pass IV as a parameter or fetch from option chain
        
        # 4. Calculate VRP (if we have IV)
        # For now, we'll calculate VRP with estimated IV from price history
        # In production, IV should come from option chain data
        
        # Estimate IV from historical volatility (simplified)
        if len(price_history) >= 30:
            try:
                # Calculate historical volatility as a proxy for IV
                import numpy as np
                import math
                returns = []
                for i in range(1, len(price_history)):
                    if price_history[i-1] > 0:
                        returns.append(math.log(price_history[i] / price_history[i-1]))
                
                if returns:
                    hist_vol = np.std(returns) * math.sqrt(252)  # Annualized
                    estimated_iv = hist_vol
                    
                    # Calculate VRP
                    vrp_result_data = vrp_calculator.calculate_vrp_result(
                        current_iv=estimated_iv,
                        price_history=price_history,
                        iv_history=None  # Could fetch from option chain if available
                    )
                    
                    # Convert to response model
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
            except Exception as e:
                print(f"⚠️ Error calculating VRP: {str(e)}")
                vrp_result = None
        else:
            vrp_result = None
        
        # 5. Calculate risk analysis (requires option data)
        # For now, return None - in production, fetch option data from option chain
        risk_analysis = None
        
        return EnhancedAnalysisResponse(
            symbol=symbol,
            option_identifier=option_identifier,
            vrp_result=vrp_result,
            risk_analysis=risk_analysis,
            available=True
        )
    
    except Exception as e:
        print(f"❌ Error in enhanced analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error calculating enhanced analysis: {str(e)}")

@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    client = get_client_manager()

    return {
        "status": "healthy",
        "data_source": "mock" if USE_MOCK_DATA else "tiger_api",
        "tiger_api_available": client.quote_client is not None,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
"""
Formula Tester Backend - FastAPI Application
Provides APIs for raw data fetching and formula calculations
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import logging

from data_fetcher import fetch_stock_data, fetch_options_data, fetch_history
from formulas.technical_formulas import (
    calculate_atr,
    calculate_atr_stop_loss,
    calculate_rsi,
    calculate_moving_averages,
    calculate_volatility,
    calculate_atr_safety_margin,
    calculate_liquidity_score
)
from formulas.stock_formulas import (
    calculate_risk_score,
    calculate_market_sentiment,
    calculate_target_price,
    calculate_growth_score,
    calculate_value_score,
    calculate_quality_score,
    calculate_momentum_score
)
from formulas.options_formulas import (
    calculate_vrp,
    calculate_trend,
    calculate_trend_alignment_score,
    calculate_probability,
    calculate_sell_put_score,
    calculate_sell_call_score,
    calculate_buy_call_score,
    calculate_buy_put_score,
    calculate_risk_return_profile
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Formula Tester API",
    description="API for testing stock and options analysis formulas",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Data Fetching Endpoints
# =============================================================================

@app.get("/api/stock/{symbol}")
async def get_stock_data(symbol: str):
    """Get comprehensive stock data for a symbol"""
    result = fetch_stock_data(symbol)
    if not result.get('success'):
        raise HTTPException(status_code=404, detail=result.get('error', 'Failed to fetch data'))
    return result


@app.get("/api/options/{symbol}")
async def get_options_data(
    symbol: str,
    expiry: Optional[str] = Query(None, description="Expiration date YYYY-MM-DD")
):
    """Get options chain data for a symbol"""
    result = fetch_options_data(symbol, expiry)
    if not result.get('success'):
        raise HTTPException(status_code=404, detail=result.get('error', 'Failed to fetch data'))
    return result


@app.get("/api/history/{symbol}")
async def get_history(
    symbol: str,
    period: str = Query("6mo", description="Data period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y"),
    interval: str = Query("1d", description="Data interval: 1m, 5m, 15m, 1h, 1d, 1wk")
):
    """Get historical OHLCV data"""
    result = fetch_history(symbol, period, interval)
    if not result.get('success'):
        raise HTTPException(status_code=404, detail=result.get('error', 'Failed to fetch data'))
    return result


# =============================================================================
# Technical Indicator Endpoints
# =============================================================================

class ATRInput(BaseModel):
    high: List[float] = Field(..., description="High prices")
    low: List[float] = Field(..., description="Low prices")
    close: List[float] = Field(..., description="Close prices")
    period: int = Field(14, ge=2, le=50, description="ATR period")


@app.post("/api/calculate/atr")
async def calc_atr(data: ATRInput):
    """Calculate ATR (Average True Range)"""
    return calculate_atr(data.high, data.low, data.close, data.period)


class ATRStopLossInput(BaseModel):
    buy_price: float = Field(..., gt=0)
    atr: float = Field(..., gt=0)
    atr_multiplier: float = Field(2.5, ge=1.0, le=5.0)
    min_stop_loss_pct: float = Field(0.15, ge=0.05, le=0.30)
    beta: Optional[float] = None


@app.post("/api/calculate/atr-stop-loss")
async def calc_atr_stop_loss(data: ATRStopLossInput):
    """Calculate ATR-based stop loss"""
    return calculate_atr_stop_loss(
        data.buy_price, data.atr, data.atr_multiplier,
        data.min_stop_loss_pct, data.beta
    )


class RSIInput(BaseModel):
    prices: List[float] = Field(..., min_items=15)
    period: int = Field(14, ge=5, le=30)


@app.post("/api/calculate/rsi")
async def calc_rsi(data: RSIInput):
    """Calculate RSI (Relative Strength Index)"""
    return calculate_rsi(data.prices, data.period)


class MAInput(BaseModel):
    prices: List[float] = Field(..., min_items=5)
    periods: List[int] = Field([5, 20, 50, 200])


@app.post("/api/calculate/moving-averages")
async def calc_ma(data: MAInput):
    """Calculate multiple moving averages"""
    return calculate_moving_averages(data.prices, data.periods)


class VolatilityInput(BaseModel):
    prices: List[float] = Field(..., min_items=31)
    period: int = Field(30, ge=10, le=60)


@app.post("/api/calculate/volatility")
async def calc_volatility(data: VolatilityInput):
    """Calculate historical volatility"""
    return calculate_volatility(data.prices, data.period)


class ATRSafetyInput(BaseModel):
    current_price: float = Field(..., gt=0)
    strike: float = Field(..., gt=0)
    atr: float = Field(..., gt=0)
    atr_ratio: float = Field(2.0, ge=1.0, le=4.0)


@app.post("/api/calculate/atr-safety")
async def calc_atr_safety(data: ATRSafetyInput):
    """Calculate ATR-based safety margin for options"""
    return calculate_atr_safety_margin(
        data.current_price, data.strike, data.atr, data.atr_ratio
    )


class LiquidityInput(BaseModel):
    volume: int = Field(..., ge=0)
    open_interest: int = Field(..., ge=0)
    bid: float = Field(..., ge=0)
    ask: float = Field(..., gt=0)


@app.post("/api/calculate/liquidity")
async def calc_liquidity(data: LiquidityInput):
    """Calculate options liquidity score"""
    return calculate_liquidity_score(
        data.volume, data.open_interest, data.bid, data.ask
    )


# =============================================================================
# Stock Analysis Endpoints
# =============================================================================

class RiskScoreInput(BaseModel):
    volatility: float = Field(..., ge=0, le=2, description="Annualized volatility as decimal")
    pe_ratio: Optional[float] = None
    debt_to_equity: Optional[float] = None
    market_cap: Optional[float] = None
    risk_premium: Optional[float] = None
    sector: str = Field("general")


@app.post("/api/calculate/risk-score")
async def calc_risk_score(data: RiskScoreInput):
    """Calculate comprehensive risk score"""
    return calculate_risk_score(
        data.volatility, data.pe_ratio, data.debt_to_equity,
        data.market_cap, data.risk_premium, data.sector
    )


class SentimentInput(BaseModel):
    prices: List[float] = Field(..., min_items=20)
    volumes: List[float] = Field(..., min_items=20)


@app.post("/api/calculate/sentiment")
async def calc_sentiment(data: SentimentInput):
    """Calculate market sentiment score"""
    return calculate_market_sentiment(data.prices, data.volumes)


class TargetPriceInput(BaseModel):
    current_price: float = Field(..., gt=0)
    pe_ratio: Optional[float] = None
    forward_pe: Optional[float] = None
    peg_ratio: Optional[float] = None
    book_value: Optional[float] = None
    revenue_growth: Optional[float] = None
    earnings_growth: Optional[float] = None
    risk_score: float = Field(50, ge=0, le=100)
    style: str = Field("balanced")


@app.post("/api/calculate/target-price")
async def calc_target_price(data: TargetPriceInput):
    """Calculate target price using multiple methods"""
    return calculate_target_price(
        data.current_price, data.pe_ratio, data.forward_pe,
        data.peg_ratio, data.book_value, data.revenue_growth,
        data.earnings_growth, data.risk_score, data.style
    )


class GrowthScoreInput(BaseModel):
    revenue_growth: Optional[float] = None
    earnings_growth: Optional[float] = None
    peg_ratio: Optional[float] = None


@app.post("/api/calculate/growth-score")
async def calc_growth_score(data: GrowthScoreInput):
    """Calculate growth stock score"""
    return calculate_growth_score(
        data.revenue_growth, data.earnings_growth, data.peg_ratio
    )


class ValueScoreInput(BaseModel):
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    dividend_yield: Optional[float] = None


@app.post("/api/calculate/value-score")
async def calc_value_score(data: ValueScoreInput):
    """Calculate value stock score"""
    return calculate_value_score(
        data.pe_ratio, data.pb_ratio, data.dividend_yield
    )


class QualityScoreInput(BaseModel):
    roe: Optional[float] = None
    gross_margin: Optional[float] = None
    fcf_to_net_income: Optional[float] = None
    debt_to_equity: Optional[float] = None


@app.post("/api/calculate/quality-score")
async def calc_quality_score(data: QualityScoreInput):
    """Calculate quality stock score"""
    return calculate_quality_score(
        data.roe, data.gross_margin, data.fcf_to_net_income, data.debt_to_equity
    )


class MomentumScoreInput(BaseModel):
    prices: List[float] = Field(..., min_items=50)
    volumes: List[float] = Field(..., min_items=50)
    week_52_high: Optional[float] = None
    week_52_low: Optional[float] = None


@app.post("/api/calculate/momentum-score")
async def calc_momentum_score(data: MomentumScoreInput):
    """Calculate momentum stock score"""
    return calculate_momentum_score(
        data.prices, data.volumes, data.week_52_high, data.week_52_low
    )


# =============================================================================
# Options Analysis Endpoints
# =============================================================================

class VRPInput(BaseModel):
    implied_volatility: float = Field(..., ge=0, le=3, description="IV as decimal")
    historical_volatility: float = Field(..., gt=0, le=3, description="HV as decimal")
    atm_iv: Optional[float] = None


@app.post("/api/calculate/vrp")
async def calc_vrp(data: VRPInput):
    """Calculate Volatility Risk Premium"""
    return calculate_vrp(
        data.implied_volatility, data.historical_volatility, data.atm_iv
    )


class TrendInput(BaseModel):
    prices: List[float] = Field(..., min_items=6)
    current_price: float = Field(..., gt=0)


@app.post("/api/calculate/trend")
async def calc_trend(data: TrendInput):
    """Determine intraday trend"""
    return calculate_trend(data.prices, data.current_price)


class TrendAlignmentInput(BaseModel):
    strategy: str = Field(..., description="sell_put, sell_call, buy_call, buy_put")
    trend: str = Field(..., description="uptrend, downtrend, sideways")
    trend_strength: float = Field(0.5, ge=0, le=1)


@app.post("/api/calculate/trend-alignment")
async def calc_trend_alignment(data: TrendAlignmentInput):
    """Calculate trend alignment score for strategy"""
    return calculate_trend_alignment_score(
        data.strategy, data.trend, data.trend_strength
    )


class ProbabilityInput(BaseModel):
    current_price: float = Field(..., gt=0)
    strike: float = Field(..., gt=0)
    days_to_expiry: int = Field(..., ge=1, le=365)
    implied_volatility: float = Field(..., gt=0, le=3)
    risk_free_rate: float = Field(0.05, ge=0, le=0.2)
    option_type: str = Field("put", description="put or call")


@app.post("/api/calculate/probability")
async def calc_probability(data: ProbabilityInput):
    """Calculate Black-Scholes probability"""
    return calculate_probability(
        data.current_price, data.strike, data.days_to_expiry,
        data.implied_volatility, data.risk_free_rate, data.option_type
    )


class SellPutScoreInput(BaseModel):
    current_price: float = Field(..., gt=0)
    strike: float = Field(..., gt=0)
    bid: float = Field(..., ge=0)
    ask: float = Field(..., gt=0)
    days_to_expiry: int = Field(..., ge=1, le=365)
    implied_volatility: float = Field(..., gt=0, le=3)
    volume: int = Field(0, ge=0)
    open_interest: int = Field(0, ge=0)
    atr: Optional[float] = None
    support_1: Optional[float] = None
    support_2: Optional[float] = None
    ma_50: Optional[float] = None
    ma_200: Optional[float] = None
    low_52w: Optional[float] = None
    trend: str = Field("sideways")
    trend_strength: float = Field(0.5, ge=0, le=1)


@app.post("/api/calculate/sell-put-score")
async def calc_sell_put_score(data: SellPutScoreInput):
    """Calculate comprehensive Sell Put score"""
    return calculate_sell_put_score(
        data.current_price, data.strike, data.bid, data.ask,
        data.days_to_expiry, data.implied_volatility,
        data.volume, data.open_interest, data.atr,
        data.support_1, data.support_2, data.ma_50, data.ma_200, data.low_52w,
        data.trend, data.trend_strength
    )


class SellCallScoreInput(BaseModel):
    current_price: float = Field(..., gt=0)
    strike: float = Field(..., gt=0)
    bid: float = Field(..., ge=0)
    ask: float = Field(..., gt=0)
    days_to_expiry: int = Field(..., ge=1, le=365)
    implied_volatility: float = Field(..., gt=0, le=3)
    volume: int = Field(0, ge=0)
    open_interest: int = Field(0, ge=0)
    atr: Optional[float] = None
    resistance_1: Optional[float] = None
    resistance_2: Optional[float] = None
    ma_50: Optional[float] = None
    ma_200: Optional[float] = None
    high_52w: Optional[float] = None
    is_covered: bool = Field(False)
    change_percent: float = Field(0)
    trend: str = Field("sideways")
    trend_strength: float = Field(0.5, ge=0, le=1)


@app.post("/api/calculate/sell-call-score")
async def calc_sell_call_score(data: SellCallScoreInput):
    """Calculate comprehensive Sell Call score"""
    return calculate_sell_call_score(
        data.current_price, data.strike, data.bid, data.ask,
        data.days_to_expiry, data.implied_volatility,
        data.volume, data.open_interest, data.atr,
        data.resistance_1, data.resistance_2, data.ma_50, data.ma_200, data.high_52w,
        data.is_covered, data.change_percent, data.trend, data.trend_strength
    )


class BuyCallScoreInput(BaseModel):
    current_price: float = Field(..., gt=0)
    strike: float = Field(..., gt=0)
    bid: float = Field(..., ge=0)
    ask: float = Field(..., gt=0)
    days_to_expiry: int = Field(..., ge=1, le=365)
    implied_volatility: float = Field(..., gt=0, le=3)
    historical_volatility: float = Field(..., gt=0, le=3)
    delta: Optional[float] = None
    volume: int = Field(0, ge=0)
    open_interest: int = Field(0, ge=0)
    change_percent: float = Field(0)
    resistance_1: Optional[float] = None
    resistance_2: Optional[float] = None
    high_52w: Optional[float] = None
    low_52w: Optional[float] = None


@app.post("/api/calculate/buy-call-score")
async def calc_buy_call_score(data: BuyCallScoreInput):
    """Calculate comprehensive Buy Call score"""
    return calculate_buy_call_score(
        data.current_price, data.strike, data.bid, data.ask,
        data.days_to_expiry, data.implied_volatility, data.historical_volatility,
        data.delta, data.volume, data.open_interest, data.change_percent,
        data.resistance_1, data.resistance_2, data.high_52w, data.low_52w
    )


class BuyPutScoreInput(BaseModel):
    current_price: float = Field(..., gt=0)
    strike: float = Field(..., gt=0)
    bid: float = Field(..., ge=0)
    ask: float = Field(..., gt=0)
    days_to_expiry: int = Field(..., ge=1, le=365)
    implied_volatility: float = Field(..., gt=0, le=3)
    historical_volatility: float = Field(..., gt=0, le=3)
    delta: Optional[float] = None
    volume: int = Field(0, ge=0)
    open_interest: int = Field(0, ge=0)
    change_percent: float = Field(0)
    support_1: Optional[float] = None
    support_2: Optional[float] = None
    high_52w: Optional[float] = None
    low_52w: Optional[float] = None


@app.post("/api/calculate/buy-put-score")
async def calc_buy_put_score(data: BuyPutScoreInput):
    """Calculate comprehensive Buy Put score"""
    return calculate_buy_put_score(
        data.current_price, data.strike, data.bid, data.ask,
        data.days_to_expiry, data.implied_volatility, data.historical_volatility,
        data.delta, data.volume, data.open_interest, data.change_percent,
        data.support_1, data.support_2, data.high_52w, data.low_52w
    )


class RiskReturnProfileInput(BaseModel):
    strategy: str = Field(..., description="sell_put, sell_call, buy_call, buy_put")
    current_price: float = Field(..., gt=0)
    strike: float = Field(..., gt=0)
    premium: float = Field(..., gt=0)
    days_to_expiry: int = Field(..., ge=1, le=365)
    implied_volatility: float = Field(..., gt=0, le=3)
    vrp_level: str = Field("normal")


@app.post("/api/calculate/risk-return-profile")
async def calc_risk_return_profile(data: RiskReturnProfileInput):
    """Calculate risk-return profile and style classification"""
    return calculate_risk_return_profile(
        data.strategy, data.current_price, data.strike,
        data.premium, data.days_to_expiry, data.implied_volatility,
        data.vrp_level
    )


# =============================================================================
# Health Check
# =============================================================================

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        "name": "Formula Tester API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "data": ["/api/stock/{symbol}", "/api/options/{symbol}", "/api/history/{symbol}"],
            "technical": ["/api/calculate/atr", "/api/calculate/rsi", "/api/calculate/volatility"],
            "stock": ["/api/calculate/risk-score", "/api/calculate/sentiment", "/api/calculate/target-price"],
            "options": ["/api/calculate/vrp", "/api/calculate/sell-put-score", "/api/calculate/sell-call-score"]
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8100)

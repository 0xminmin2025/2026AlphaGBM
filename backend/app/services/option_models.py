"""
Option data models with scoring capabilities
Ported from new_options_module/models/option_models.py
"""

from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

class OptionType(str, Enum):
    """Option type enumeration"""
    CALL = "CALL"
    PUT = "PUT"

class OptionStrategy(str, Enum):
    """Option strategy types for scoring"""
    SELL_PUT = "sell_put"          # Short Put
    SELL_CALL = "sell_call"        # Covered Call / Short Call
    BUY_CALL = "buy_call"          # Long Call
    BUY_PUT = "buy_put"            # Long Put

class RiskReturnProfile(BaseModel):
    """风险收益风格标签"""
    style: str                         # 'steady_income', 'high_risk_high_reward', 'balanced', 'hedge'
    style_label: str                   # 中英双语标签
    style_label_cn: str                # 纯中文标签
    style_label_en: str                # 纯英文标签
    risk_level: str                    # 'low', 'moderate', 'high', 'very_high'
    risk_color: str                    # 'green', 'yellow', 'orange', 'red'
    max_loss_pct: float                # 最大亏损百分比
    max_profit_pct: float              # 最大收益百分比
    win_probability: float             # 胜率估算 (0-1)
    risk_reward_ratio: float           # 风险收益比
    summary: str                       # 一句话总结
    summary_cn: str                    # 中文总结
    strategy_type: str                 # 'buyer' or 'seller'
    time_decay_impact: str             # 'positive', 'negative', 'neutral'
    volatility_impact: str             # 'positive', 'negative', 'neutral'


class OptionScores(BaseModel):
    """Option scoring metrics"""
    sprv: Optional[float] = None   # Sell Put Recommendation Value
    scrv: Optional[float] = None   # Sell Call Recommendation Value
    bcrv: Optional[float] = None   # Buy Call Recommendation Value
    bprv: Optional[float] = None   # Buy Put Recommendation Value
    liquidity_factor: Optional[float] = None
    iv_rank: Optional[float] = None
    iv_percentile: Optional[float] = None
    days_to_expiry: Optional[int] = None

    # Assignment probability using Black-Scholes N(d2)
    assignment_probability: Optional[float] = None  # Probability of assignment (0-100%)

    # Premium and capital calculations for sell strategies
    premium_income: Optional[float] = None      # Premium received from selling option
    margin_requirement: Optional[float] = None  # Capital requirement (Cash for PUT, Stock Value for CALL)
    annualized_return: Optional[float] = None   # Annual return %

    # 风险收益风格标签
    risk_return_profile: Optional[RiskReturnProfile] = None

class OptionData(BaseModel):
    """Enhanced option contract data with scoring"""
    # Basic option information
    identifier: str
    symbol: str
    strike: float
    put_call: OptionType
    expiry_date: str

    # Market data
    bid_price: Optional[float] = None
    ask_price: Optional[float] = None
    latest_price: Optional[float] = None
    volume: Optional[int] = None
    open_interest: Optional[int] = None

    # Greeks
    implied_vol: Optional[float] = None
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    rho: Optional[float] = None

    # Scoring metrics
    scores: Optional[OptionScores] = None

    # Additional metrics for scoring
    premium: Optional[float] = None  # Option premium in dollars
    spread_percentage: Optional[float] = None  # (Ask - Bid) / Mid price

    class Config:
        use_enum_values = True

class OptionChainResponse(BaseModel):
    """Option chain response with enhanced data"""
    symbol: str
    expiry_date: str
    calls: List[OptionData]
    puts: List[OptionData]
    data_source: Optional[str] = None  # "real", "mock", "hybrid"
    real_stock_price: Optional[float] = None

    # Market context for scoring
    stock_price: Optional[float] = None
    iv_rank_30d: Optional[float] = None  # 30-day IV rank
    iv_percentile_30d: Optional[float] = None  # 30-day IV percentile
    historical_volatility: Optional[float] = None

class ExpirationDate(BaseModel):
    """Option expiration date"""
    date: str
    timestamp: int
    period_tag: str  # "m" for monthly, "w" for weekly

class ExpirationResponse(BaseModel):
    """Option expiration dates response"""
    symbol: str
    expirations: List[ExpirationDate]

class StockQuote(BaseModel):
    """Basic stock quote data"""
    symbol: str
    latest_price: float
    change: float
    change_percent: float
    volume: int
    market_cap: Optional[float] = None

class ScoringParams(BaseModel):
    """Parameters for option scoring algorithms"""
    # Market environment
    risk_free_rate: float = 0.05  # 5% risk-free rate

    # SPRV parameters
    sprv_delta_power: float = 1.5
    sprv_ivr_base: float = 10.0

    # SCRV parameters
    scrv_ivp_weight: float = 1.0

    # BCRV parameters
    bcrv_min_volume: int = 500  # Minimum daily volume for liquidity

    # BPRV parameters
    bprv_correlation: float = 0.7  # Assumed correlation with portfolio
    bprv_skew_penalty: float = 2.0  # Penalty for extreme OTM puts

    # Liquidity thresholds
    liquidity_good_spread: float = 0.05  # 5% or less = good liquidity
    liquidity_poor_spread: float = 0.10  # 10% or more = poor liquidity

    # Margin parameters (simplified)
    put_margin_rate: float = 0.20  # 20% of strike for short puts
    call_margin_rate: float = 0.20  # 20% of stock value for short calls

# Phase 1 models for VRP and Risk Analysis
class VRPResult(BaseModel):
    """VRP计算结果"""
    vrp: float                    # VRP值（IV - RV）
    iv: float                     # 当前隐含波动率
    rv_forecast: float            # 预测的已实现波动率
    iv_rank: float                # IV Rank (0-100)
    iv_percentile: float          # IV Percentile (0-100)
    recommendation: str           # "sell", "buy", or "neutral"

class RiskAnalysis(BaseModel):
    """风险分析结果"""
    expected_value: float            # 期望值
    risk_adjusted_expectancy: float  # 风险调整后期望值 (RAE)
    max_loss: float                  # 最大潜在亏损
    tail_risk_var: float             # 尾部风险 (VaR proxy)
    win_rate: float                  # 胜率 (0-100)
    risk_level: str                  # "low", "medium", "high", "extreme"
    tail_risk_warning: str           # 风险警告信息

class EnhancedAnalysisResponse(BaseModel):
    """增强分析响应（包含VRP和风险分析）"""
    symbol: str
    option_identifier: str
    vrp_result: Optional[VRPResult] = None
    risk_analysis: Optional[RiskAnalysis] = None
    available: bool  # Phase 1模块是否可用

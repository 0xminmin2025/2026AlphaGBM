"""
Parameters Module

Centralized configuration parameters for the AlphaGBM backend.
All configuration parameters are organized into logical modules:

- valuation: Stock valuation parameters (growth, PEG, PE percentiles)
- risk_management: Risk and stop loss parameters (ATR, Beta, VIX)
- market: Market-specific configurations (US, CN, HK)
- sector_rotation: Sector rotation analysis parameters
- capital_structure: Capital flow and structure analysis

Usage:
    # Import specific parameters
    from app.params.valuation import GROWTH_DISCOUNT_FACTOR
    from app.params.risk_management import ATR_PERIOD
    from app.params.market import get_market_config

    # Or import from this module (all re-exported)
    from app.params import GROWTH_DISCOUNT_FACTOR, get_market_config

    # Or use backward-compatible constants.py
    from app.constants import GROWTH_DISCOUNT_FACTOR
"""

# ==================== Valuation Parameters ====================
from .valuation import (
    GROWTH_DISCOUNT_FACTOR,
    TECHNICAL_SENTIMENT_BOOST,
    PRICE_POSITION_LOW,
    PRICE_POSITION_MID,
    PEG_THRESHOLD_BASE,
    TREASURY_YIELD_HIGH_THRESHOLD,
    HIGH_YIELD_PEG_ADJUSTMENT,
    PE_HISTORY_WINDOW_YEARS,
    PE_MIN_DATA_POINTS,
    PE_PERCENTILE_SENTIMENT,
    PE_Z_SCORE_THRESHOLD,
    PE_Z_SCORE_ADJUSTMENT,
    EARNINGS_LAG_DAYS,
    WEIGHT_BASELINE,
    WEIGHT_EARNINGS_LAG,
)

# ==================== Risk Management Parameters ====================
from .risk_management import (
    ATR_PERIOD,
    ATR_MULTIPLIER_BASE,
    ATR_MULTIPLIER_MIN,
    ATR_MULTIPLIER_MAX,
    BETA_HIGH_THRESHOLD,
    BETA_MID_HIGH_THRESHOLD,
    BETA_LOW_THRESHOLD,
    BETA_MID_LOW_THRESHOLD,
    BETA_HIGH_MULTIPLIER,
    BETA_MID_HIGH_MULTIPLIER,
    BETA_LOW_MULTIPLIER,
    BETA_MID_LOW_MULTIPLIER,
    FIXED_STOP_LOSS_PCT,
    PE_HIGH_THRESHOLD,
    PE_VERY_HIGH_THRESHOLD,
    PEG_HIGH_THRESHOLD,
    GROWTH_NEGATIVE_THRESHOLD,
    VIX_HIGH,
    VIX_MEDIUM,
    VIX_RISING,
    PUT_CALL_HIGH,
    PUT_CALL_MEDIUM,
    TREASURY_YIELD_VERY_HIGH,
    TREASURY_YIELD_HIGH,
    MIN_DAILY_VOLUME_USD,
    VOLUME_ANOMALY_HIGH,
    VOLUME_ANOMALY_LOW,
)

# ==================== Market Configuration ====================
from .market import (
    MARKET_CONFIG,
    MARKET_STYLE_WEIGHTS,
    TICKER_SUFFIX_TO_MARKET,
    CN_STOCK_PREFIX_RULES,
    get_market_config,
    get_market_style_weights,
    adjust_parameter_for_market,
)

# ==================== Sector Rotation Configuration ====================
from .sector_rotation import (
    SECTOR_ROTATION_CONFIG,
    get_sector_rotation_config,
    get_market_rotation_adjustment,
)

# ==================== Capital Structure Configuration ====================
from .capital_structure import (
    CAPITAL_STRUCTURE_CONFIG,
    get_capital_structure_config,
    get_propagation_stage_factor,
    get_persistence_probability,
)


__all__ = [
    # Valuation
    'GROWTH_DISCOUNT_FACTOR',
    'TECHNICAL_SENTIMENT_BOOST',
    'PRICE_POSITION_LOW',
    'PRICE_POSITION_MID',
    'PEG_THRESHOLD_BASE',
    'TREASURY_YIELD_HIGH_THRESHOLD',
    'HIGH_YIELD_PEG_ADJUSTMENT',
    'PE_HISTORY_WINDOW_YEARS',
    'PE_MIN_DATA_POINTS',
    'PE_PERCENTILE_SENTIMENT',
    'PE_Z_SCORE_THRESHOLD',
    'PE_Z_SCORE_ADJUSTMENT',
    'EARNINGS_LAG_DAYS',
    'WEIGHT_BASELINE',
    'WEIGHT_EARNINGS_LAG',
    # Risk Management
    'ATR_PERIOD',
    'ATR_MULTIPLIER_BASE',
    'ATR_MULTIPLIER_MIN',
    'ATR_MULTIPLIER_MAX',
    'BETA_HIGH_THRESHOLD',
    'BETA_MID_HIGH_THRESHOLD',
    'BETA_LOW_THRESHOLD',
    'BETA_MID_LOW_THRESHOLD',
    'BETA_HIGH_MULTIPLIER',
    'BETA_MID_HIGH_MULTIPLIER',
    'BETA_LOW_MULTIPLIER',
    'BETA_MID_LOW_MULTIPLIER',
    'FIXED_STOP_LOSS_PCT',
    'PE_HIGH_THRESHOLD',
    'PE_VERY_HIGH_THRESHOLD',
    'PEG_HIGH_THRESHOLD',
    'GROWTH_NEGATIVE_THRESHOLD',
    'VIX_HIGH',
    'VIX_MEDIUM',
    'VIX_RISING',
    'PUT_CALL_HIGH',
    'PUT_CALL_MEDIUM',
    'TREASURY_YIELD_VERY_HIGH',
    'TREASURY_YIELD_HIGH',
    'MIN_DAILY_VOLUME_USD',
    'VOLUME_ANOMALY_HIGH',
    'VOLUME_ANOMALY_LOW',
    # Market
    'MARKET_CONFIG',
    'MARKET_STYLE_WEIGHTS',
    'TICKER_SUFFIX_TO_MARKET',
    'CN_STOCK_PREFIX_RULES',
    'get_market_config',
    'get_market_style_weights',
    'adjust_parameter_for_market',
    # Sector Rotation
    'SECTOR_ROTATION_CONFIG',
    'get_sector_rotation_config',
    'get_market_rotation_adjustment',
    # Capital Structure
    'CAPITAL_STRUCTURE_CONFIG',
    'get_capital_structure_config',
    'get_propagation_stage_factor',
    'get_persistence_probability',
]

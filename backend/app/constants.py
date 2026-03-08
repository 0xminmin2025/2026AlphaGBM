"""
系统配置参数 - 向后兼容模块

DEPRECATED: This module is maintained for backward compatibility.
New code should import directly from app.params:

    from app.params import GROWTH_DISCOUNT_FACTOR, get_market_config
    from app.params.valuation import PE_PERCENTILE_SENTIMENT
    from app.params.risk_management import ATR_PERIOD

All parameters are now organized in app/params/:
- valuation.py: Growth, PEG, PE parameters
- risk_management.py: ATR, Beta, VIX parameters
- market.py: Market-specific configurations
- sector_rotation.py: Sector rotation config
- capital_structure.py: Capital structure config
"""

# ==================== Re-export from params modules ====================

# Valuation Parameters
from .params.valuation import (
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

# Risk Management Parameters
from .params.risk_management import (
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

# Market Configuration
from .params.market import (
    MARKET_CONFIG,
    MARKET_STYLE_WEIGHTS,
    TICKER_SUFFIX_TO_MARKET,
    CN_STOCK_PREFIX_RULES,
    get_market_config,
    get_market_style_weights,
    adjust_parameter_for_market,
)

# Sector Rotation Configuration
from .params.sector_rotation import (
    SECTOR_ROTATION_CONFIG,
    get_sector_rotation_config,
    get_market_rotation_adjustment,
)

# Capital Structure Configuration
from .params.capital_structure import (
    CAPITAL_STRUCTURE_CONFIG,
    get_capital_structure_config,
    get_propagation_stage_factor,
    get_persistence_probability,
)


# ==================== Market Detection (Backward Compatibility) ====================

def detect_market_from_ticker(ticker: str) -> str:
    """
    根据股票代码识别市场

    NOTE: This function delegates to the unified market detector.
    Consider using `from app.services.market_data import detect_market` directly.

    Args:
        ticker: 股票代码

    Returns:
        市场代码 ('US', 'CN', 'HK')

    Examples:
        >>> detect_market_from_ticker("AAPL")
        'US'
        >>> detect_market_from_ticker("600519")
        'CN'
        >>> detect_market_from_ticker("0700.HK")
        'HK'
    """
    from app.services.market_data import detect_market
    market = detect_market(ticker)
    return market.value.upper()


# ==================== Module Exports ====================

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
    'detect_market_from_ticker',
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

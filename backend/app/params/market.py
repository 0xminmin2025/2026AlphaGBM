"""
Market-Specific Configuration

Contains market-differentiated parameters for:
- US, China A-share, and Hong Kong markets
- Market identification rules
- Style weights per market
"""

from typing import Dict, Any


# ==================== Market Configuration ====================

# Market-specific parameters for US, A-share, and Hong Kong
MARKET_CONFIG: Dict[str, Dict[str, Any]] = {
    'US': {  # US Market - Baseline parameters
        'name': '美股',
        'name_en': 'US Market',
        'min_daily_volume_usd': 5_000_000,    # Minimum daily volume (USD)
        'risk_premium': 1.0,                   # Risk premium coefficient (baseline)
        'growth_discount': 0.6,                # Growth rate discount factor
        'pe_high_threshold': 40,               # PE high risk threshold
        'pe_very_high_threshold': 60,          # PE very high risk threshold
        'liquidity_coefficient': 1.0,          # Liquidity coefficient
        'volatility_adjustment': 1.0,          # Volatility adjustment
        'currency': 'USD',
        'trading_hours': 'US_MARKET',
    },
    'CN': {  # China A-share Market
        'name': 'A股',
        'name_en': 'China A-Share',
        'min_daily_volume_usd': 1_000_000,    # Lower liquidity requirement (CNY converted)
        'risk_premium': 1.3,                   # Policy risk premium
        'growth_discount': 0.7,                # More aggressive growth discount (A-share prefers growth)
        'pe_high_threshold': 50,               # A-share PE is generally higher
        'pe_very_high_threshold': 80,
        'liquidity_coefficient': 0.5,          # Lower liquidity requirement
        'volatility_adjustment': 1.2,          # Higher volatility
        'policy_risk_factor': 1.2,             # Policy sensitivity
        'currency': 'CNY',
        'trading_hours': 'CN_MARKET',
    },
    'HK': {  # Hong Kong Market
        'name': '港股',
        'name_en': 'Hong Kong',
        'min_daily_volume_usd': 2_000_000,    # Medium liquidity requirement
        'risk_premium': 1.15,                  # Slightly higher risk premium
        'growth_discount': 0.65,               # Medium growth discount
        'pe_high_threshold': 35,               # HK PE is generally lower
        'pe_very_high_threshold': 50,
        'liquidity_coefficient': 0.6,          # Medium liquidity requirement
        'volatility_adjustment': 1.1,          # Slightly higher volatility
        'discount_factor': 0.95,               # H-share vs A-share discount
        'fx_risk_coefficient': 0.1,            # FX risk (HKD pegged to USD)
        'currency': 'HKD',
        'trading_hours': 'HK_MARKET',
    }
}


# ==================== Market Style Weights ====================

# Investment style preference weights by market
MARKET_STYLE_WEIGHTS: Dict[str, Dict[str, float]] = {
    'US': {  # US Market - Balanced
        'quality': 1.0,
        'value': 1.0,
        'growth': 1.0,
        'momentum': 1.0,
        'balanced': 1.0
    },
    'CN': {  # A-share - Growth and Momentum preference
        'quality': 0.8,
        'value': 0.7,
        'growth': 1.3,
        'momentum': 1.2,
        'balanced': 1.0
    },
    'HK': {  # Hong Kong - Value and Quality preference
        'quality': 1.2,
        'value': 1.3,
        'growth': 0.9,
        'momentum': 0.8,
        'balanced': 1.0
    }
}


# ==================== Market Identification Rules ====================
# NOTE: For actual market detection, use app.services.market_data.detect_market()
# These constants are kept for reference and backward compatibility

# Ticker suffix to market mapping
TICKER_SUFFIX_TO_MARKET = {
    '.SS': 'CN',   # Shanghai Stock Exchange
    '.SZ': 'CN',   # Shenzhen Stock Exchange
    '.SH': 'CN',   # Shanghai (alternative)
    '.HK': 'HK',   # Hong Kong Exchange
    '.T': 'JP',    # Tokyo (not supported)
    '.L': 'UK',    # London (not supported)
}

# A-share code prefix rules (for 6-digit codes without suffix)
CN_STOCK_PREFIX_RULES = {
    '60': 'SS',    # Shanghai Main Board
    '68': 'SS',    # Shanghai STAR Market (科创板)
    '00': 'SZ',    # Shenzhen Main Board
    '30': 'SZ',    # Shenzhen ChiNext (创业板)
}


# ==================== Helper Functions ====================

def get_market_config(market: str) -> Dict[str, Any]:
    """
    Get market configuration.

    Args:
        market: Market code ('US', 'CN', 'HK')

    Returns:
        Market configuration dictionary
    """
    return MARKET_CONFIG.get(market, MARKET_CONFIG['US'])


def get_market_style_weights(market: str) -> Dict[str, float]:
    """
    Get market style weights.

    Args:
        market: Market code

    Returns:
        Style weights dictionary
    """
    return MARKET_STYLE_WEIGHTS.get(market, MARKET_STYLE_WEIGHTS['US'])


def adjust_parameter_for_market(base_value: float, market: str, param_type: str) -> float:
    """
    Adjust a parameter value based on market.

    Args:
        base_value: Base parameter value
        market: Market code
        param_type: Parameter type ('risk', 'growth', 'pe', 'liquidity')

    Returns:
        Adjusted parameter value
    """
    config = get_market_config(market)

    if param_type == 'risk':
        return base_value * config.get('risk_premium', 1.0)
    elif param_type == 'growth':
        return base_value * config.get('growth_discount', 0.6) / 0.6  # Relative to baseline
    elif param_type == 'pe':
        return config.get('pe_high_threshold', base_value)
    elif param_type == 'liquidity':
        return base_value * config.get('liquidity_coefficient', 1.0)
    else:
        return base_value

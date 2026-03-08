"""
Sector Rotation Analysis Configuration

Contains parameters for sector rotation strategy including:
- Analysis periods
- Rotation premiums
- Leader detection thresholds
- Strength scoring weights
- Market-specific adjustments
"""

from typing import Dict, Any


# ==================== Sector Rotation Configuration ====================

SECTOR_ROTATION_CONFIG: Dict[str, Any] = {
    # Cache configuration
    'cache_ttl': 300,              # 5-minute cache (seconds)

    # Analysis periods (days)
    'analysis_periods': [5, 20, 60],

    # Rotation premium range
    'rotation_premium_max': 0.10,  # Maximum rotation premium +10%
    'rotation_premium_min': -0.05, # Minimum rotation premium -5%

    # Leader detection threshold
    'leader_outperform_threshold': 0.05,  # 5% outperformance to be leader

    # Strength scoring weights
    'weight_relative_strength': 0.40,     # Relative strength weight
    'weight_momentum': 0.30,              # Momentum trend weight
    'weight_volume': 0.20,                # Capital flow weight
    'weight_rotation_stage': 0.10,        # Rotation position weight

    # Market-specific adjustments
    'market_adjustments': {
        'US': {
            'relative_strength_sensitivity': 1.0,
            'volume_importance': 1.0,
        },
        'HK': {
            'relative_strength_sensitivity': 1.1,   # HK slightly higher volatility
            'volume_importance': 0.9,               # HK volume less reliable
        },
        'CN': {
            'relative_strength_sensitivity': 1.2,   # A-share higher volatility
            'volume_importance': 1.1,               # A-share volume more important
        },
    },
}


def get_sector_rotation_config() -> Dict[str, Any]:
    """Get the sector rotation configuration."""
    return SECTOR_ROTATION_CONFIG


def get_market_rotation_adjustment(market: str) -> Dict[str, float]:
    """
    Get market-specific rotation adjustments.

    Args:
        market: Market code ('US', 'CN', 'HK')

    Returns:
        Market adjustment parameters
    """
    adjustments = SECTOR_ROTATION_CONFIG.get('market_adjustments', {})
    return adjustments.get(market, adjustments.get('US', {}))

"""
Capital Structure Analysis Configuration

Contains parameters for capital flow and structure analysis including:
- Volume concentration thresholds
- Price-volume harmony analysis
- Capital factor ranges
- Scoring weights
- Sentiment propagation stages
"""

from typing import Dict, Any


# ==================== Capital Structure Configuration ====================

CAPITAL_STRUCTURE_CONFIG: Dict[str, Any] = {
    # Volume concentration threshold
    'volume_concentration_threshold': 1.5,    # Volume ratio threshold

    # Price-volume harmony lookback period
    'harmony_lookback': 20,

    # Capital factor range
    'capital_factor_max': 0.05,     # Maximum +5%
    'capital_factor_min': -0.03,    # Minimum -3%

    # Scoring weights
    'weight_volume_concentration': 0.30,
    'weight_price_volume_harmony': 0.30,
    'weight_chip_concentration': 0.25,
    'weight_turnover': 0.15,

    # Sentiment propagation stage factors
    'propagation_stage_factors': {
        'leader_start': 0.05,       # Leader initiation phase
        'early_spread': 0.03,       # Early spread phase
        'full_spread': 0.01,        # Full spread phase
        'high_divergence': -0.02,   # High divergence phase
        'retreat': -0.03,           # Retreat phase
        'neutral': 0.0,             # Neutral phase
    },

    # Persistence probability by stage
    'persistence_probability': {
        'leader_start': 0.70,
        'early_spread': 0.65,
        'full_spread': 0.50,
        'high_divergence': 0.40,
        'retreat': 0.35,
        'neutral': 0.50,
    },
}


def get_capital_structure_config() -> Dict[str, Any]:
    """Get the capital structure configuration."""
    return CAPITAL_STRUCTURE_CONFIG


def get_propagation_stage_factor(stage: str) -> float:
    """
    Get the factor for a specific propagation stage.

    Args:
        stage: Propagation stage name

    Returns:
        Stage factor (can be positive or negative)
    """
    factors = CAPITAL_STRUCTURE_CONFIG.get('propagation_stage_factors', {})
    return factors.get(stage, 0.0)


def get_persistence_probability(stage: str) -> float:
    """
    Get the persistence probability for a stage.

    Args:
        stage: Propagation stage name

    Returns:
        Probability between 0 and 1
    """
    probabilities = CAPITAL_STRUCTURE_CONFIG.get('persistence_probability', {})
    return probabilities.get(stage, 0.50)

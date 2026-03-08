"""
Valuation Parameters Configuration

Contains parameters for stock valuation calculations including:
- Growth rate discounting
- Technical sentiment adjustments
- Price position thresholds
- PEG calculations
- PE percentile scoring
"""

# ==================== Growth & Sentiment Parameters ====================

# Growth rate discount factor (used in growth_multiplier)
GROWTH_DISCOUNT_FACTOR = 0.6  # Apply 60% growth premium

# Technical analysis coefficient
TECHNICAL_SENTIMENT_BOOST = 0.10  # 10% sentiment score boost

# ==================== Price Position Thresholds ====================

# Price position within 52-week range
PRICE_POSITION_LOW = 0.3   # Below 30% is considered low
PRICE_POSITION_MID = 0.7   # Below 70% is considered mid

# ==================== PEG Parameters ====================

# Base PEG threshold (dynamically adjusted by Treasury yield)
PEG_THRESHOLD_BASE = 1.5

# Treasury yield threshold for high-rate environment
TREASURY_YIELD_HIGH_THRESHOLD = 4.0  # High rate threshold (%)

# PEG adjustment in high-yield environment
HIGH_YIELD_PEG_ADJUSTMENT = 0.8  # Reduce by 20% (multiply by 0.8)

# ==================== PE Percentile Parameters ====================

# PE history window for percentile calculation
PE_HISTORY_WINDOW_YEARS = 5  # 5-year historical window
PE_MIN_DATA_POINTS = 20      # Minimum data points required

# PE percentile to sentiment score mapping
# Format: (min_percentile, max_percentile, sentiment_score)
PE_PERCENTILE_SENTIMENT = {
    'very_low': (0, 20, 3.0),      # 0-20%: 3.0 score
    'low': (20, 40, 4.5),          # 20-40%: 4.5 score
    'neutral_low': (40, 60, 5.5),  # 40-60%: 5.5 score
    'neutral_high': (60, 80, 6.5), # 60-80%: 6.5 score
    'high': (80, 90, 8.0),         # 80-90%: 8.0 score
    'very_high': (90, 100, 9.0),   # 90-100%: 9.0 score
}

# Z-score adjustment threshold
PE_Z_SCORE_THRESHOLD = 2.0   # Beyond 2 std deviation
PE_Z_SCORE_ADJUSTMENT = 0.5  # Adjustment magnitude

# ==================== Earnings Lag Handling ====================

# Days after earnings release when data lags
EARNINGS_LAG_DAYS = 3  # 3 days post-earnings, reduce fundamental weight

# Baseline weights for analysis components
WEIGHT_BASELINE = {
    'fundamental': 0.40,  # Normal fundamental weight
    'technical': 0.30,    # Normal technical weight
    'sentiment': 0.30,    # Normal sentiment weight
}

# Adjusted weights during earnings lag period
WEIGHT_EARNINGS_LAG = {
    'fundamental': 0.20,  # Reduced fundamental weight (lagging data)
    'technical': 0.45,    # Increased technical weight
    'sentiment': 0.35,    # Increased sentiment weight
}

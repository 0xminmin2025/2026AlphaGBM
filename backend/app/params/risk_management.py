"""
Risk Management Configuration

Contains parameters for:
- Stop loss calculations (ATR-based and fixed)
- Beta adjustments
- Risk scoring thresholds
- Market sentiment indicators (VIX, Put/Call, Treasury)
"""

# ==================== ATR Stop Loss Parameters ====================

ATR_PERIOD = 14              # ATR calculation period (days)
ATR_MULTIPLIER_BASE = 2.5    # Base ATR multiplier
ATR_MULTIPLIER_MIN = 1.5     # Minimum ATR multiplier
ATR_MULTIPLIER_MAX = 4.0     # Maximum ATR multiplier

# ==================== Beta Adjustment Parameters ====================

# Beta thresholds for categorization
BETA_HIGH_THRESHOLD = 1.5        # High beta threshold
BETA_MID_HIGH_THRESHOLD = 1.2    # Mid-high beta threshold
BETA_LOW_THRESHOLD = 0.8         # Low beta threshold
BETA_MID_LOW_THRESHOLD = 1.0     # Mid-low beta threshold

# ATR multiplier adjustments based on beta
BETA_HIGH_MULTIPLIER = 1.2       # High beta: increase ATR multiplier
BETA_MID_HIGH_MULTIPLIER = 1.1   # Mid-high beta
BETA_LOW_MULTIPLIER = 0.8        # Low beta: decrease ATR multiplier
BETA_MID_LOW_MULTIPLIER = 0.9    # Mid-low beta

# ==================== Fixed Stop Loss ====================

FIXED_STOP_LOSS_PCT = 0.15   # Fixed stop loss percentage (15%)

# ==================== Risk Scoring Thresholds ====================

# PE ratio thresholds
PE_HIGH_THRESHOLD = 40       # PE above 40 is high risk
PE_VERY_HIGH_THRESHOLD = 60  # PE above 60 is very high risk

# PEG ratio threshold
PEG_HIGH_THRESHOLD = 2.0     # PEG above 2.0 is high risk

# Growth rate threshold
GROWTH_NEGATIVE_THRESHOLD = -0.10  # Growth below -10% is high risk

# ==================== Market Sentiment Thresholds ====================

# VIX (Volatility Index) thresholds
VIX_HIGH = 30.0              # VIX above 30 = high fear
VIX_MEDIUM = 25.0            # VIX above 25 = elevated fear
VIX_RISING = 20.0            # VIX above 20 and rising = caution

# Put/Call ratio thresholds
PUT_CALL_HIGH = 1.5          # Ratio above 1.5 = extreme bearishness
PUT_CALL_MEDIUM = 1.2        # Ratio above 1.2 = bearish sentiment

# Treasury yield thresholds (%)
TREASURY_YIELD_VERY_HIGH = 5.0   # Above 5.0% = very restrictive
TREASURY_YIELD_HIGH = 4.5        # Above 4.5% = restrictive

# ==================== Liquidity Parameters ====================

# Minimum daily trading volume (USD)
MIN_DAILY_VOLUME_USD = 5_000_000  # $5 million minimum

# Volume anomaly thresholds
VOLUME_ANOMALY_HIGH = 2.0    # Volume > 2x average = unusual activity
VOLUME_ANOMALY_LOW = 0.3     # Volume < 30% of average = low liquidity

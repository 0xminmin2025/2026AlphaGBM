"""
Mock options data fixtures for testing options analysis components.

Provides realistic AAPL options chain data including:
- Calls and puts DataFrames with strike, bid, ask, IV, OI, and Greeks
- OptionsChainData dataclass builder
- Sample expiration dates
- Enhanced analysis fixtures (VRP, risk analysis)
"""
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

AAPL_UNDERLYING_PRICE = 189.84
AAPL_SYMBOL = 'AAPL'
SAMPLE_EXPIRY = '2026-03-20'  # Third Friday of March 2026

# Expiration dates available for AAPL
AAPL_EXPIRATIONS = [
    '2026-02-14',
    '2026-02-21',
    '2026-02-28',
    '2026-03-07',
    '2026-03-14',
    '2026-03-20',
    '2026-04-17',
    '2026-05-15',
    '2026-06-19',
    '2026-09-18',
    '2026-12-18',
    '2027-01-15',
    '2027-06-18',
]


# ---------------------------------------------------------------------------
# Calls DataFrame
# ---------------------------------------------------------------------------

def _make_calls_df() -> pd.DataFrame:
    """
    Build a realistic AAPL calls DataFrame with 15 strikes
    centered around the underlying price.
    """
    strikes = np.arange(175.0, 205.0, 2.5)  # 12 strikes: 175, 177.5, ... , 202.5
    n = len(strikes)

    # Intrinsic value for ITM calls
    intrinsic = np.maximum(AAPL_UNDERLYING_PRICE - strikes, 0)

    # Time value decays as we move further OTM
    moneyness = (AAPL_UNDERLYING_PRICE - strikes) / AAPL_UNDERLYING_PRICE
    time_value = np.clip(5.0 - 15 * np.abs(moneyness), 0.5, 8.0)

    mid_prices = intrinsic + time_value
    spreads = np.clip(mid_prices * 0.03, 0.05, 0.80)
    bids = np.round(mid_prices - spreads / 2, 2)
    asks = np.round(mid_prices + spreads / 2, 2)
    last_prices = np.round(mid_prices + np.random.uniform(-0.10, 0.10, n), 2)

    # IV smile: higher at wings, lower ATM
    iv_base = 0.28
    iv = iv_base + 0.12 * moneyness ** 2 + np.random.uniform(-0.01, 0.01, n)
    iv = np.round(np.clip(iv, 0.15, 0.65), 4)

    # Volume and OI: highest near ATM
    atm_idx = np.argmin(np.abs(strikes - AAPL_UNDERLYING_PRICE))
    vol_base = np.exp(-0.3 * np.abs(np.arange(n) - atm_idx))
    volumes = np.round(vol_base * 5000).astype(int)
    open_interest = np.round(vol_base * 25000).astype(int)

    # Greeks
    delta = np.round(np.clip(0.5 + 0.4 * moneyness / 0.10, 0.02, 0.98), 4)
    gamma = np.round(0.03 * np.exp(-0.5 * (moneyness / 0.05) ** 2), 5)
    theta = np.round(-0.05 * (1 + 2 * np.exp(-0.5 * (moneyness / 0.05) ** 2)), 4)
    vega = np.round(0.15 * np.exp(-0.5 * (moneyness / 0.08) ** 2), 4)

    return pd.DataFrame({
        'strike': strikes,
        'bid': bids,
        'ask': asks,
        'lastPrice': last_prices,
        'volume': volumes,
        'openInterest': open_interest,
        'impliedVolatility': iv,
        'delta': delta,
        'gamma': gamma,
        'theta': theta,
        'vega': vega,
        'inTheMoney': strikes < AAPL_UNDERLYING_PRICE,
        'contractSymbol': [f'AAPL260320C{int(s*1000):08d}' for s in strikes],
        'expiry': SAMPLE_EXPIRY,
    })


# ---------------------------------------------------------------------------
# Puts DataFrame
# ---------------------------------------------------------------------------

def _make_puts_df() -> pd.DataFrame:
    """
    Build a realistic AAPL puts DataFrame with the same strikes as calls.
    """
    strikes = np.arange(175.0, 205.0, 2.5)
    n = len(strikes)

    intrinsic = np.maximum(strikes - AAPL_UNDERLYING_PRICE, 0)
    moneyness = (strikes - AAPL_UNDERLYING_PRICE) / AAPL_UNDERLYING_PRICE
    time_value = np.clip(5.0 - 15 * np.abs(moneyness), 0.5, 8.0)

    mid_prices = intrinsic + time_value
    spreads = np.clip(mid_prices * 0.03, 0.05, 0.80)
    bids = np.round(mid_prices - spreads / 2, 2)
    asks = np.round(mid_prices + spreads / 2, 2)
    last_prices = np.round(mid_prices + np.random.uniform(-0.10, 0.10, n), 2)

    # IV smile for puts (slightly higher due to skew)
    iv_base = 0.30
    iv = iv_base + 0.15 * moneyness ** 2 + 0.03 * np.clip(-moneyness, 0, 1)
    iv = iv + np.random.uniform(-0.01, 0.01, n)
    iv = np.round(np.clip(iv, 0.15, 0.70), 4)

    atm_idx = np.argmin(np.abs(strikes - AAPL_UNDERLYING_PRICE))
    vol_base = np.exp(-0.3 * np.abs(np.arange(n) - atm_idx))
    volumes = np.round(vol_base * 4000).astype(int)
    open_interest = np.round(vol_base * 20000).astype(int)

    # Greeks for puts
    delta = np.round(np.clip(-0.5 + 0.4 * moneyness / 0.10, -0.98, -0.02), 4)
    gamma = np.round(0.03 * np.exp(-0.5 * (moneyness / 0.05) ** 2), 5)
    theta = np.round(-0.04 * (1 + 2 * np.exp(-0.5 * (moneyness / 0.05) ** 2)), 4)
    vega = np.round(0.15 * np.exp(-0.5 * (moneyness / 0.08) ** 2), 4)

    return pd.DataFrame({
        'strike': strikes,
        'bid': bids,
        'ask': asks,
        'lastPrice': last_prices,
        'volume': volumes,
        'openInterest': open_interest,
        'impliedVolatility': iv,
        'delta': delta,
        'gamma': gamma,
        'theta': theta,
        'vega': vega,
        'inTheMoney': strikes > AAPL_UNDERLYING_PRICE,
        'contractSymbol': [f'AAPL260320P{int(s*1000):08d}' for s in strikes],
        'expiry': SAMPLE_EXPIRY,
    })


# Pre-built DataFrames for quick fixture access
AAPL_CALLS_DF = _make_calls_df()
AAPL_PUTS_DF = _make_puts_df()


# ---------------------------------------------------------------------------
# VRP (Volatility Risk Premium) sample data
# ---------------------------------------------------------------------------

AAPL_VRP_RESULT = {
    'implied_vol': 0.285,
    'realized_vol': 0.220,
    'vrp': 0.065,
    'vrp_percentile': 72.0,
    'iv_rank': 45.0,
    'iv_percentile': 52.0,
    'hv_20': 0.218,
    'hv_60': 0.235,
    'signal': 'sell_premium',
    'confidence': 'medium',
}


# ---------------------------------------------------------------------------
# Risk analysis sample data
# ---------------------------------------------------------------------------

AAPL_RISK_ANALYSIS = {
    'risk_level': 'medium',
    'risk_score': 0.45,
    'max_loss': -1250.0,
    'max_gain': 3800.0,
    'breakeven_price': 192.50,
    'probability_of_profit': 0.58,
    'expected_value': 320.0,
    'risk_reward_ratio': 3.04,
    'position_size_suggestion': {
        'max_contracts': 5,
        'total_premium': 2500.0,
        'portfolio_risk_pct': 0.025,
    },
}


# ---------------------------------------------------------------------------
# Enhanced analysis result (combined VRP + risk + scoring)
# ---------------------------------------------------------------------------

AAPL_ENHANCED_ANALYSIS = {
    'symbol': AAPL_SYMBOL,
    'underlying_price': AAPL_UNDERLYING_PRICE,
    'expiry': SAMPLE_EXPIRY,
    'option_type': 'call',
    'strike': 190.0,
    'bid': 5.80,
    'ask': 6.10,
    'iv': 0.285,
    'score': 78.5,
    'rating': 'A',
    'vrp_analysis': AAPL_VRP_RESULT,
    'risk_analysis': AAPL_RISK_ANALYSIS,
    'recommendation': 'Buy call - favorable risk/reward with moderate IV premium',
}


# ---------------------------------------------------------------------------
# Option scorer input/output samples
# ---------------------------------------------------------------------------

AAPL_SCORE_INPUT = {
    'symbol': AAPL_SYMBOL,
    'strike': 190.0,
    'expiry': SAMPLE_EXPIRY,
    'option_type': 'call',
    'bid': 5.80,
    'ask': 6.10,
    'iv': 0.285,
    'delta': 0.52,
    'gamma': 0.028,
    'theta': -0.12,
    'vega': 0.14,
    'volume': 3200,
    'open_interest': 18500,
    'underlying_price': AAPL_UNDERLYING_PRICE,
}

AAPL_SCORE_OUTPUT = {
    'overall_score': 78.5,
    'rating': 'A',
    'components': {
        'liquidity_score': 85.0,
        'value_score': 72.0,
        'risk_reward_score': 80.0,
        'technical_score': 75.0,
    },
}


# ---------------------------------------------------------------------------
# Helper: build OptionsChainData dataclass
# ---------------------------------------------------------------------------

def make_options_chain_data():
    """Build an OptionsChainData dataclass instance from the AAPL fixtures."""
    from app.services.market_data.interfaces import OptionsChainData
    return OptionsChainData(
        symbol=AAPL_SYMBOL,
        expiry_date=SAMPLE_EXPIRY,
        underlying_price=AAPL_UNDERLYING_PRICE,
        calls=AAPL_CALLS_DF.copy(),
        puts=AAPL_PUTS_DF.copy(),
        source='test',
    )


def make_empty_options_chain():
    """Build an empty OptionsChainData for edge-case testing."""
    from app.services.market_data.interfaces import OptionsChainData
    return OptionsChainData(
        symbol=AAPL_SYMBOL,
        expiry_date=SAMPLE_EXPIRY,
        underlying_price=AAPL_UNDERLYING_PRICE,
        calls=pd.DataFrame(),
        puts=pd.DataFrame(),
        source='test',
    )

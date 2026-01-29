"""
Options Analysis Formulas
Sell Put, Sell Call, Buy Call, Buy Put scoring
VRP calculation, Trend alignment, Risk-Return profiles
"""

import numpy as np
from typing import Dict, Any, List, Optional
import math

try:
    from scipy.stats import norm
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


# =============================================================================
# VRP (Volatility Risk Premium) Calculation
# =============================================================================

def calculate_vrp(
    implied_volatility: float,  # Weighted IV as decimal
    historical_volatility: float,  # 30-day HV as decimal
    atm_iv: Optional[float] = None
) -> Dict[str, Any]:
    """
    Calculate Volatility Risk Premium

    VRP = IV - HV
    VRP Relative = (IV - HV) / HV
    """
    if historical_volatility <= 0:
        return {
            'success': False,
            'error': 'Historical volatility must be positive'
        }

    # VRP calculations
    vrp_absolute = implied_volatility - historical_volatility
    vrp_relative = (implied_volatility - historical_volatility) / historical_volatility
    vol_ratio = implied_volatility / historical_volatility

    # ATM VRP if available
    if atm_iv:
        atm_vrp = atm_iv - historical_volatility
        atm_vrp_relative = (atm_iv - historical_volatility) / historical_volatility
    else:
        atm_vrp = vrp_absolute
        atm_vrp_relative = vrp_relative

    # Signal strength
    if vrp_relative >= 0.20:
        signal_strength = 'very_strong_positive'
    elif vrp_relative >= 0.10:
        signal_strength = 'strong_positive'
    elif vrp_relative >= 0.05:
        signal_strength = 'moderate_positive'
    elif vrp_relative >= -0.05:
        signal_strength = 'neutral'
    elif vrp_relative >= -0.10:
        signal_strength = 'moderate_negative'
    elif vrp_relative >= -0.20:
        signal_strength = 'strong_negative'
    else:
        signal_strength = 'very_strong_negative'

    # VRP Level
    if vrp_relative >= 0.15:
        vrp_level = 'very_high'
    elif vrp_relative >= 0.05:
        vrp_level = 'high'
    elif vrp_relative >= -0.05:
        vrp_level = 'normal'
    elif vrp_relative >= -0.15:
        vrp_level = 'low'
    else:
        vrp_level = 'very_low'

    # Strategy suggestions
    if vrp_level in ['very_high', 'high']:
        strategy_bias = 'seller'
        suggested_strategies = ['sell_put', 'sell_call', 'iron_condor']
    elif vrp_level in ['very_low', 'low']:
        strategy_bias = 'buyer'
        suggested_strategies = ['buy_call', 'buy_put', 'long_straddle']
    else:
        strategy_bias = 'neutral'
        suggested_strategies = ['directional_based']

    return {
        'success': True,
        'vrp_absolute': round(vrp_absolute * 100, 2),  # As percentage
        'vrp_relative_pct': round(vrp_relative * 100, 2),
        'atm_vrp': round(atm_vrp * 100, 2),
        'atm_vrp_relative_pct': round(atm_vrp_relative * 100, 2),
        'volatility_ratio': round(vol_ratio, 3),
        'signal_strength': signal_strength,
        'vrp_level': vrp_level,
        'strategy_bias': strategy_bias,
        'suggested_strategies': suggested_strategies,
        'implied_vol_pct': round(implied_volatility * 100, 2),
        'historical_vol_pct': round(historical_volatility * 100, 2)
    }


# =============================================================================
# Trend Analysis
# =============================================================================

def calculate_trend(
    prices: List[float],  # Need at least 6 prices
    current_price: float
) -> Dict[str, Any]:
    """
    Determine intraday trend using 3-signal method

    Signals:
    1. Today's change (vs previous close)
    2. Position vs MA5
    3. 5-day momentum
    """
    if len(prices) < 6:
        return {
            'success': False,
            'error': 'Need at least 6 price points'
        }

    prices_arr = np.array(prices[-6:])
    prev_close = prices_arr[-2] if len(prices_arr) >= 2 else prices_arr[-1]

    signals = {}

    # Signal 1: Today's change
    today_change = (current_price - prev_close) / prev_close if prev_close > 0 else 0
    if today_change > 0.005:
        signals['today_change'] = 'bullish'
    elif today_change < -0.005:
        signals['today_change'] = 'bearish'
    else:
        signals['today_change'] = 'neutral'

    # Signal 2: MA5 position
    ma5 = np.mean(prices_arr[-5:])
    ma5_position = (current_price - ma5) / ma5 if ma5 > 0 else 0
    if ma5_position > 0.01:
        signals['ma5_position'] = 'bullish'
    elif ma5_position < -0.01:
        signals['ma5_position'] = 'bearish'
    else:
        signals['ma5_position'] = 'neutral'

    # Signal 3: 5-day momentum
    momentum_5d = (current_price - prices_arr[0]) / prices_arr[0] if prices_arr[0] > 0 else 0
    if momentum_5d > 0.02:
        signals['momentum_5d'] = 'bullish'
    elif momentum_5d < -0.02:
        signals['momentum_5d'] = 'bearish'
    else:
        signals['momentum_5d'] = 'neutral'

    # Count signals
    bullish_count = sum(1 for s in signals.values() if s == 'bullish')
    bearish_count = sum(1 for s in signals.values() if s == 'bearish')

    # Determine trend
    if bullish_count >= 2:
        trend = 'uptrend'
        strength = bullish_count / 3
    elif bearish_count >= 2:
        trend = 'downtrend'
        strength = bearish_count / 3
    else:
        trend = 'sideways'
        strength = 0.5

    return {
        'success': True,
        'trend': trend,
        'strength': round(strength, 2),
        'signals': signals,
        'today_change_pct': round(today_change * 100, 2),
        'ma5_position_pct': round(ma5_position * 100, 2),
        'momentum_5d_pct': round(momentum_5d * 100, 2)
    }


def calculate_trend_alignment_score(
    strategy: str,  # sell_put, sell_call, buy_call, buy_put
    trend: str,  # uptrend, downtrend, sideways
    trend_strength: float
) -> Dict[str, Any]:
    """
    Calculate trend alignment score for a strategy

    Matrix:
    - Sell Call: uptrend=100, sideways=60, downtrend=30
    - Sell Put: downtrend=100, sideways=60, uptrend=30
    - Buy Call: uptrend=100, sideways=50, downtrend=20
    - Buy Put: downtrend=100, sideways=50, uptrend=20
    """
    trend_score_matrix = {
        'sell_call': {'uptrend': 100, 'sideways': 60, 'downtrend': 30},
        'sell_put': {'downtrend': 100, 'sideways': 60, 'uptrend': 30},
        'buy_call': {'uptrend': 100, 'sideways': 50, 'downtrend': 20},
        'buy_put': {'downtrend': 100, 'sideways': 50, 'uptrend': 20}
    }

    ideal_trend_map = {
        'sell_call': 'uptrend',
        'sell_put': 'downtrend',
        'buy_call': 'uptrend',
        'buy_put': 'downtrend'
    }

    strategy = strategy.lower()
    trend = trend.lower()

    if strategy not in trend_score_matrix:
        return {
            'success': False,
            'error': f'Unknown strategy: {strategy}'
        }

    base_score = trend_score_matrix[strategy].get(trend, 50)
    ideal_trend = ideal_trend_map[strategy]
    is_ideal = trend == ideal_trend

    # Strength adjustment
    if base_score >= 80:  # Matching trend
        adjusted_score = base_score * (1 + trend_strength * 0.2)
    else:  # Non-matching trend
        adjusted_score = base_score * (1 - trend_strength * 0.3)

    adjusted_score = round(min(120, max(0, adjusted_score)), 1)

    # Warning message
    warning = None
    if not is_ideal and trend != 'sideways':
        trend_names = {'uptrend': 'uptrend', 'downtrend': 'downtrend'}
        warning = f"Current {trend_names.get(trend, trend)} is not ideal for {strategy}"

    return {
        'success': True,
        'base_score': base_score,
        'adjusted_score': adjusted_score,
        'is_ideal_trend': is_ideal,
        'ideal_trend': ideal_trend,
        'warning': warning
    }


# =============================================================================
# Black-Scholes Probability
# =============================================================================

def calculate_probability(
    current_price: float,
    strike: float,
    days_to_expiry: int,
    implied_volatility: float,
    risk_free_rate: float = 0.05,
    option_type: str = 'put'  # 'put' or 'call'
) -> Dict[str, Any]:
    """
    Calculate probability of option expiring ITM/OTM using Black-Scholes

    d1 = (ln(S/K) + (r + σ²/2)T) / (σ√T)
    """
    if days_to_expiry <= 0 or implied_volatility <= 0:
        return {
            'success': False,
            'error': 'Days to expiry and IV must be positive'
        }

    t = days_to_expiry / 365

    if HAS_SCIPY:
        d1 = (math.log(current_price / strike) + (risk_free_rate + 0.5 * implied_volatility ** 2) * t) / (implied_volatility * math.sqrt(t))

        prob_above_strike = norm.cdf(d1)
        prob_below_strike = 1 - prob_above_strike

        if option_type.lower() == 'put':
            # Sell Put wins if price stays above strike
            prob_profit = prob_above_strike
        else:
            # Buy Call profits if price goes above strike + premium
            prob_profit = prob_above_strike
    else:
        # Fallback without scipy
        distance_pct = (current_price - strike) / current_price * 100
        if option_type.lower() == 'put':
            if distance_pct >= 15:
                prob_profit = 0.95
            elif distance_pct >= 10:
                prob_profit = 0.85
            elif distance_pct >= 5:
                prob_profit = 0.70
            elif distance_pct >= 0:
                prob_profit = 0.55
            else:
                prob_profit = max(0.20, 0.55 + distance_pct * 0.02)
        else:
            if distance_pct <= 0:  # ITM call
                prob_profit = 0.55
            elif distance_pct <= 5:
                prob_profit = 0.45
            elif distance_pct <= 10:
                prob_profit = 0.35
            else:
                prob_profit = 0.20

        prob_above_strike = prob_profit if option_type.lower() == 'put' else prob_profit
        prob_below_strike = 1 - prob_above_strike

    return {
        'success': True,
        'prob_above_strike': round(prob_above_strike, 4),
        'prob_below_strike': round(prob_below_strike, 4),
        'prob_profit': round(prob_profit, 4),
        'prob_profit_pct': round(prob_profit * 100, 1),
        'd1': round(d1 if HAS_SCIPY else 0, 4),
        'method': 'Black-Scholes' if HAS_SCIPY else 'Simplified'
    }


# =============================================================================
# Sell Put Scoring
# =============================================================================

def calculate_sell_put_score(
    current_price: float,
    strike: float,
    bid: float,
    ask: float,
    days_to_expiry: int,
    implied_volatility: float,
    volume: int = 0,
    open_interest: int = 0,
    atr: Optional[float] = None,
    support_1: Optional[float] = None,
    support_2: Optional[float] = None,
    ma_50: Optional[float] = None,
    ma_200: Optional[float] = None,
    low_52w: Optional[float] = None,
    trend: str = 'sideways',
    trend_strength: float = 0.5
) -> Dict[str, Any]:
    """
    Calculate Sell Put comprehensive score

    Weights:
    - premium_yield: 20%
    - safety_margin: 15%
    - support_strength: 20%
    - trend_alignment: 15%
    - probability_profit: 15%
    - liquidity: 10%
    - time_decay: 5%
    """
    weights = {
        'premium_yield': 0.20,
        'safety_margin': 0.15,
        'support_strength': 0.20,
        'trend_alignment': 0.15,
        'probability_profit': 0.15,
        'liquidity': 0.10,
        'time_decay': 0.05
    }

    mid_price = (bid + ask) / 2 if bid > 0 and ask > 0 else 0
    intrinsic_value = max(0, strike - current_price)
    time_value = max(0, mid_price - intrinsic_value)

    scores = {}

    # 1. Premium Yield Score
    if strike > 0 and days_to_expiry > 0:
        premium_yield = (time_value / strike) * 100
        annualized_return = (premium_yield / days_to_expiry) * 365

        if annualized_return >= 20:
            scores['premium_yield'] = 100
        elif annualized_return >= 15:
            scores['premium_yield'] = 80 + (annualized_return - 15) * 4
        elif annualized_return >= 10:
            scores['premium_yield'] = 60 + (annualized_return - 10) * 4
        elif annualized_return >= 5:
            scores['premium_yield'] = 40 + (annualized_return - 5) * 4
        else:
            scores['premium_yield'] = max(0, annualized_return * 8)
    else:
        premium_yield = 0
        annualized_return = 0
        scores['premium_yield'] = 0

    # 2. Safety Margin Score
    safety_margin_pct = ((current_price - strike) / current_price) * 100 if current_price > 0 else 0

    if safety_margin_pct >= 10:
        base_safety = 100
    elif safety_margin_pct >= 5:
        base_safety = 80 + (safety_margin_pct - 5) * 4
    elif safety_margin_pct >= 0:
        base_safety = 50 + safety_margin_pct * 6
    else:
        base_safety = max(0, 50 + safety_margin_pct * 2)

    # ATR adjustment
    atr_bonus = 0
    atr_safety = None
    if atr and atr > 0:
        required_buffer = atr * 2.0
        actual_buffer = abs(current_price - strike)
        safety_ratio = actual_buffer / required_buffer

        if safety_ratio >= 1.5:
            atr_bonus = 15
        elif safety_ratio >= 1.0:
            atr_bonus = 5
        elif safety_ratio >= 0.5:
            atr_bonus = -10
        else:
            atr_bonus = -20

        atr_safety = {
            'safety_ratio': round(safety_ratio, 2),
            'atr_multiples': round(actual_buffer / atr, 2),
            'is_safe': safety_ratio >= 1.0
        }

    scores['safety_margin'] = min(100, max(0, base_safety + atr_bonus))

    # 3. Support Strength Score
    support_levels = [
        (support_1, 25, 'S1'),
        (support_2, 20, 'S2'),
        (ma_50, 20, 'MA50'),
        (ma_200, 25, 'MA200'),
        (low_52w, 10, '52W Low')
    ]

    support_scores = []
    matched_supports = []
    for level, max_score, name in support_levels:
        if level and level > 0:
            diff_pct = abs(strike - level) / current_price * 100
            if diff_pct <= 1:
                support_scores.append(max_score)
                matched_supports.append(f'{name} (exact)')
            elif diff_pct <= 3:
                support_scores.append(max_score * 0.7)
                matched_supports.append(f'{name} (near)')
            elif diff_pct <= 5:
                support_scores.append(max_score * 0.4)
                matched_supports.append(f'{name} (close)')

    if support_scores:
        scores['support_strength'] = min(100, sum(support_scores))
    else:
        if safety_margin_pct >= 10:
            scores['support_strength'] = 60
        elif safety_margin_pct >= 5:
            scores['support_strength'] = 40
        else:
            scores['support_strength'] = 20

    # 4. Trend Alignment Score
    trend_result = calculate_trend_alignment_score('sell_put', trend, trend_strength)
    scores['trend_alignment'] = trend_result['adjusted_score'] if trend_result['success'] else 50

    # 5. Probability of Profit Score
    prob_result = calculate_probability(current_price, strike, days_to_expiry, implied_volatility, option_type='put')
    if prob_result['success']:
        scores['probability_profit'] = prob_result['prob_profit_pct']
    else:
        scores['probability_profit'] = 50

    # 6. Liquidity Score
    if bid > 0 and ask > 0:
        spread_pct = (ask - bid) / mid_price * 100
        vol_score = min(50, volume / 10)
        oi_score = min(30, open_interest / 50)

        if spread_pct <= 5:
            spread_score = 20
        elif spread_pct <= 10:
            spread_score = 15
        elif spread_pct <= 20:
            spread_score = 10
        else:
            spread_score = max(0, 10 - (spread_pct - 20) / 2)

        scores['liquidity'] = vol_score + oi_score + spread_score
    else:
        scores['liquidity'] = 0

    # 7. Time Decay Score
    if 20 <= days_to_expiry <= 45:
        scores['time_decay'] = 100
    elif 10 <= days_to_expiry < 20:
        scores['time_decay'] = 70 + (days_to_expiry - 10) * 3
    elif 45 < days_to_expiry <= 90:
        scores['time_decay'] = 100 - (days_to_expiry - 45) * 1.5
    elif days_to_expiry < 10:
        scores['time_decay'] = max(10, 70 - (10 - days_to_expiry) * 6)
    else:
        scores['time_decay'] = max(20, 100 - (days_to_expiry - 90) * 0.5)

    # Calculate weighted total
    total_score = sum(scores[k] * weights[k] for k in weights.keys())

    # Assignment risk
    if safety_margin_pct >= 15:
        assignment_risk = 'very_low'
    elif safety_margin_pct >= 10:
        assignment_risk = 'low'
    elif safety_margin_pct >= 5:
        assignment_risk = 'moderate'
    elif safety_margin_pct >= 0:
        assignment_risk = 'high'
    else:
        assignment_risk = 'very_high'

    return {
        'success': True,
        'total_score': round(total_score, 1),
        'score_breakdown': {k: round(v, 1) for k, v in scores.items()},
        'weights': weights,
        'metrics': {
            'mid_price': round(mid_price, 2),
            'time_value': round(time_value, 2),
            'intrinsic_value': round(intrinsic_value, 2),
            'premium_yield_pct': round(premium_yield, 2),
            'annualized_return_pct': round(annualized_return, 1),
            'safety_margin_pct': round(safety_margin_pct, 2),
            'breakeven': round(strike - mid_price, 2),
            'max_profit': round(mid_price * 100, 0),
            'max_loss': round((strike - mid_price) * 100, 0)
        },
        'assignment_risk': assignment_risk,
        'atr_safety': atr_safety,
        'matched_supports': matched_supports,
        'trend_warning': trend_result.get('warning'),
        'is_ideal_trend': trend_result.get('is_ideal_trend', False)
    }


# =============================================================================
# Sell Call Scoring
# =============================================================================

def calculate_sell_call_score(
    current_price: float,
    strike: float,
    bid: float,
    ask: float,
    days_to_expiry: int,
    implied_volatility: float,
    volume: int = 0,
    open_interest: int = 0,
    atr: Optional[float] = None,
    resistance_1: Optional[float] = None,
    resistance_2: Optional[float] = None,
    ma_50: Optional[float] = None,
    ma_200: Optional[float] = None,
    high_52w: Optional[float] = None,
    is_covered: bool = False,
    change_percent: float = 0,
    trend: str = 'sideways',
    trend_strength: float = 0.5
) -> Dict[str, Any]:
    """
    Calculate Sell Call comprehensive score

    Weights:
    - premium_yield: 20%
    - resistance_strength: 20%
    - trend_alignment: 15%
    - upside_buffer: 15%
    - liquidity: 10%
    - is_covered: 10%
    - time_decay: 5%
    - overvaluation: 5%
    """
    weights = {
        'premium_yield': 0.20,
        'resistance_strength': 0.20,
        'trend_alignment': 0.15,
        'upside_buffer': 0.15,
        'liquidity': 0.10,
        'is_covered': 0.10,
        'time_decay': 0.05,
        'overvaluation': 0.05
    }

    mid_price = (bid + ask) / 2 if bid > 0 and ask > 0 else 0
    intrinsic_value = max(0, current_price - strike)
    time_value = max(0, mid_price - intrinsic_value)

    scores = {}

    # 1. Premium Yield Score
    if current_price > 0 and days_to_expiry > 0:
        premium_yield = (time_value / current_price) * 100
        annualized_return = (premium_yield / days_to_expiry) * 365

        if annualized_return >= 15:
            scores['premium_yield'] = 100
        elif annualized_return >= 12:
            scores['premium_yield'] = 85 + (annualized_return - 12) * 5
        elif annualized_return >= 8:
            scores['premium_yield'] = 70 + (annualized_return - 8) * 3.75
        elif annualized_return >= 5:
            scores['premium_yield'] = 50 + (annualized_return - 5) * 6.67
        else:
            scores['premium_yield'] = max(0, annualized_return * 10)
    else:
        premium_yield = 0
        annualized_return = 0
        scores['premium_yield'] = 0

    # 2. Resistance Strength Score
    resistance_levels = [
        (resistance_1, 25, 'R1'),
        (resistance_2, 20, 'R2'),
        (high_52w, 25, '52W High')
    ]

    if current_price > (ma_50 or 0):
        resistance_levels.append(((ma_50 or 0) * 1.05, 15, 'MA50+5%'))
    if current_price > (ma_200 or 0):
        resistance_levels.append(((ma_200 or 0) * 1.08, 15, 'MA200+8%'))

    resistance_scores = []
    matched_resistances = []
    for level, max_score, name in resistance_levels:
        if level and level > 0:
            diff_pct = abs(strike - level) / current_price * 100
            if diff_pct <= 1:
                resistance_scores.append(max_score)
                matched_resistances.append(f'{name} (exact)')
            elif diff_pct <= 3:
                resistance_scores.append(max_score * 0.7)
                matched_resistances.append(f'{name} (near)')
            elif diff_pct <= 5:
                resistance_scores.append(max_score * 0.4)
                matched_resistances.append(f'{name} (close)')

    upside_buffer_pct = ((strike - current_price) / current_price) * 100 if current_price > 0 else 0

    if resistance_scores:
        scores['resistance_strength'] = min(100, sum(resistance_scores))
    else:
        if 5 <= upside_buffer_pct <= 10:
            scores['resistance_strength'] = 60
        elif 2 <= upside_buffer_pct < 5:
            scores['resistance_strength'] = 50
        elif upside_buffer_pct > 15:
            scores['resistance_strength'] = 30
        else:
            scores['resistance_strength'] = 40

    # 3. Trend Alignment Score
    trend_result = calculate_trend_alignment_score('sell_call', trend, trend_strength)
    scores['trend_alignment'] = trend_result['adjusted_score'] if trend_result['success'] else 50

    # 4. Upside Buffer Score
    if upside_buffer_pct >= 10:
        base_buffer = 80
    elif upside_buffer_pct >= 5:
        base_buffer = 60 + (upside_buffer_pct - 5) * 4
    elif upside_buffer_pct >= 2:
        base_buffer = 40 + (upside_buffer_pct - 2) * 6.67
    else:
        base_buffer = max(10, upside_buffer_pct * 20)

    atr_bonus = 0
    atr_safety = None
    if atr and atr > 0:
        required_buffer = atr * 2.0
        actual_buffer = abs(strike - current_price)
        safety_ratio = actual_buffer / required_buffer

        if safety_ratio >= 1.5:
            atr_bonus = 15
        elif safety_ratio >= 1.0:
            atr_bonus = 5
        elif safety_ratio >= 0.5:
            atr_bonus = -10
        else:
            atr_bonus = -20

        atr_safety = {
            'safety_ratio': round(safety_ratio, 2),
            'atr_multiples': round(actual_buffer / atr, 2),
            'is_safe': safety_ratio >= 1.0
        }

    scores['upside_buffer'] = min(100, max(0, base_buffer + atr_bonus))

    # 5. Liquidity Score
    if bid > 0 and ask > 0:
        spread_pct = (ask - bid) / mid_price * 100
        vol_score = min(50, volume / 10)
        oi_score = min(30, open_interest / 50)

        if spread_pct <= 5:
            spread_score = 20
        elif spread_pct <= 10:
            spread_score = 15
        elif spread_pct <= 20:
            spread_score = 10
        else:
            spread_score = max(0, 10 - (spread_pct - 20) / 2)

        scores['liquidity'] = vol_score + oi_score + spread_score
    else:
        scores['liquidity'] = 0

    # 6. Covered Call Score
    scores['is_covered'] = 100 if is_covered else 50

    # 7. Time Decay Score
    if 15 <= days_to_expiry <= 30:
        scores['time_decay'] = 100
    elif 7 <= days_to_expiry < 15:
        scores['time_decay'] = 90
    elif 30 < days_to_expiry <= 45:
        scores['time_decay'] = 80 - (days_to_expiry - 30) * 1.5
    elif days_to_expiry < 7:
        scores['time_decay'] = max(20, 90 - (7 - days_to_expiry) * 10)
    else:
        scores['time_decay'] = max(30, 80 - (days_to_expiry - 45) * 0.8)

    # 8. Overvaluation Score
    overval_scores = []

    if resistance_1:
        dist_r1 = (resistance_1 - current_price) / current_price * 100
        if dist_r1 <= 2:
            overval_scores.append(90)
        elif dist_r1 <= 5:
            overval_scores.append(70)
        elif dist_r1 <= 10:
            overval_scores.append(50)
        else:
            overval_scores.append(30)

    if high_52w:
        dist_high = (high_52w - current_price) / current_price * 100
        if dist_high <= 3:
            overval_scores.append(85)
        elif dist_high <= 8:
            overval_scores.append(60)
        else:
            overval_scores.append(40)

    if change_percent >= 3:
        overval_scores.append(80)
    elif change_percent >= 1:
        overval_scores.append(60)
    elif change_percent <= -2:
        overval_scores.append(20)
    else:
        overval_scores.append(50)

    scores['overvaluation'] = np.mean(overval_scores) if overval_scores else 50

    # Calculate weighted total
    total_score = sum(scores[k] * weights[k] for k in weights.keys())

    return {
        'success': True,
        'total_score': round(total_score, 1),
        'score_breakdown': {k: round(v, 1) for k, v in scores.items()},
        'weights': weights,
        'metrics': {
            'mid_price': round(mid_price, 2),
            'time_value': round(time_value, 2),
            'intrinsic_value': round(intrinsic_value, 2),
            'premium_yield_pct': round(premium_yield, 2),
            'annualized_return_pct': round(annualized_return, 1),
            'upside_buffer_pct': round(upside_buffer_pct, 2),
            'breakeven': round(strike + mid_price, 2),
            'max_profit': round(mid_price * 100, 0)
        },
        'atr_safety': atr_safety,
        'matched_resistances': matched_resistances,
        'trend_warning': trend_result.get('warning'),
        'is_ideal_trend': trend_result.get('is_ideal_trend', False),
        'is_covered': is_covered
    }


# =============================================================================
# Buy Call Scoring
# =============================================================================

def calculate_buy_call_score(
    current_price: float,
    strike: float,
    bid: float,
    ask: float,
    days_to_expiry: int,
    implied_volatility: float,
    historical_volatility: float,
    delta: Optional[float] = None,
    volume: int = 0,
    open_interest: int = 0,
    change_percent: float = 0,
    resistance_1: Optional[float] = None,
    resistance_2: Optional[float] = None,
    high_52w: Optional[float] = None,
    low_52w: Optional[float] = None
) -> Dict[str, Any]:
    """
    Calculate Buy Call comprehensive score

    Weights:
    - bullish_momentum: 25%
    - breakout_potential: 20%
    - value_efficiency: 20%
    - volatility_timing: 15%
    - liquidity: 10%
    - time_optimization: 10%
    """
    weights = {
        'bullish_momentum': 0.25,
        'breakout_potential': 0.20,
        'value_efficiency': 0.20,
        'volatility_timing': 0.15,
        'liquidity': 0.10,
        'time_optimization': 0.10
    }

    mid_price = (bid + ask) / 2 if bid > 0 and ask > 0 else 0
    intrinsic_value = max(0, current_price - strike)
    time_value = max(0, mid_price - intrinsic_value)
    moneyness = (current_price - strike) / current_price * 100 if current_price > 0 else 0

    scores = {}

    # 1. Bullish Momentum Score
    if change_percent >= 3:
        momentum_score = 100
    elif change_percent >= 2:
        momentum_score = 90
    elif change_percent >= 1:
        momentum_score = 75
    elif change_percent >= 0:
        momentum_score = 60
    elif change_percent >= -1:
        momentum_score = 40
    else:
        momentum_score = max(10, 40 - abs(change_percent + 1) * 10)

    # 52-week position bonus
    if high_52w and low_52w and high_52w > low_52w:
        position = (current_price - low_52w) / (high_52w - low_52w) * 100
        if position >= 70:
            momentum_score += 20
        elif position >= 50:
            momentum_score += 15
        elif position <= 30:
            momentum_score -= 10

    # Resistance distance bonus
    if resistance_1:
        dist_r1 = (resistance_1 - current_price) / current_price * 100
        if dist_r1 <= 5:
            momentum_score += 10
        elif dist_r1 >= 15:
            momentum_score -= 5

    scores['bullish_momentum'] = min(100, momentum_score)

    # 2. Breakout Potential Score
    breakout_score = 50

    if resistance_1:
        dist_r1 = (resistance_1 - current_price) / current_price * 100
        if dist_r1 <= 3:
            breakout_score += 25
        elif dist_r1 <= 6:
            breakout_score += 20
        elif dist_r1 <= 10:
            breakout_score += 15
        else:
            breakout_score += 5

        if strike >= resistance_1 * 1.02:
            breakout_score += 20

    if resistance_2 and strike >= resistance_2:
        breakout_score += 15

    if high_52w:
        dist_high = (high_52w - current_price) / current_price * 100
        if dist_high <= 5:
            breakout_score += 15
            if strike >= high_52w:
                breakout_score += 10
        elif dist_high >= 20:
            breakout_score += 5

    if change_percent >= 2 and resistance_1 and current_price >= resistance_1 * 0.98:
        breakout_score += 20

    scores['breakout_potential'] = min(100, breakout_score)

    # 3. Value Efficiency Score (Delta/Price)
    if delta and delta > 0 and mid_price > 0:
        efficiency = delta / mid_price

        if efficiency >= 0.6:
            eff_score = 100
        elif efficiency >= 0.4:
            eff_score = 90
        elif efficiency >= 0.3:
            eff_score = 80
        elif efficiency >= 0.2:
            eff_score = 70
        elif efficiency >= 0.1:
            eff_score = 60
        else:
            eff_score = 40

        # Moneyness adjustment
        if -5 <= moneyness <= 5:
            eff_score += 10
        elif moneyness < -15:
            eff_score -= 15
        elif moneyness > 15:
            eff_score -= 5

        scores['value_efficiency'] = min(100, eff_score)
    else:
        scores['value_efficiency'] = 50

    # 4. Volatility Timing Score
    vol_score = 50
    if historical_volatility > 0:
        vol_ratio = implied_volatility / historical_volatility

        if vol_ratio <= 0.85:
            vol_score += 25
        elif vol_ratio <= 0.95:
            vol_score += 15
        elif vol_ratio <= 1.05:
            vol_score += 5
        elif vol_ratio <= 1.2:
            vol_score -= 10
        else:
            vol_score -= 20

    # IV percentile approximation
    if implied_volatility <= 0.15:
        vol_score += 20
    elif implied_volatility <= 0.20:
        vol_score += 10
    elif implied_volatility >= 0.35:
        vol_score -= 15

    if abs(change_percent) >= 2:
        vol_score += 10

    scores['volatility_timing'] = min(100, max(0, vol_score))

    # 5. Liquidity Score
    if bid > 0 and ask > 0:
        spread_pct = (ask - bid) / mid_price * 100
        vol_score = min(40, volume / 8)
        oi_score = min(30, open_interest / 40)

        if spread_pct <= 6:
            spread_score = 30
        elif spread_pct <= 12:
            spread_score = 20
        elif spread_pct <= 20:
            spread_score = 10
        else:
            spread_score = max(0, 10 - (spread_pct - 20) / 3)

        scores['liquidity'] = vol_score + oi_score + spread_score
    else:
        scores['liquidity'] = 0

    # 6. Time Optimization Score
    time_score = 50

    if mid_price > 0:
        time_value_ratio = time_value / mid_price
        if 0.2 <= time_value_ratio <= 0.6:
            time_score += 30
        elif 0.1 <= time_value_ratio < 0.2:
            time_score += 20
        elif 0.6 < time_value_ratio <= 0.8:
            time_score += 10
        elif time_value_ratio > 0.9:
            time_score -= 25
        elif time_value_ratio < 0.1:
            time_score += 25

    if days_to_expiry <= 7:
        time_score -= 20
    elif days_to_expiry <= 30:
        time_score += 15
    elif days_to_expiry <= 60:
        time_score += 20
    elif days_to_expiry <= 90:
        time_score += 10
    else:
        time_score -= 10

    scores['time_optimization'] = min(100, max(0, time_score))

    # Calculate weighted total
    total_score = sum(scores[k] * weights[k] for k in weights.keys())

    # Breakeven
    breakeven = strike + mid_price
    required_move_pct = ((breakeven - current_price) / current_price) * 100

    return {
        'success': True,
        'total_score': round(total_score, 1),
        'score_breakdown': {k: round(v, 1) for k, v in scores.items()},
        'weights': weights,
        'metrics': {
            'mid_price': round(mid_price, 2),
            'time_value': round(time_value, 2),
            'intrinsic_value': round(intrinsic_value, 2),
            'moneyness_pct': round(moneyness, 2),
            'breakeven': round(breakeven, 2),
            'required_move_pct': round(required_move_pct, 2),
            'max_loss': round(mid_price * 100, 0),
            'leverage_ratio': round((delta or 0.5) * current_price / mid_price, 2) if mid_price > 0 else 0
        }
    }


# =============================================================================
# Buy Put Scoring
# =============================================================================

def calculate_buy_put_score(
    current_price: float,
    strike: float,
    bid: float,
    ask: float,
    days_to_expiry: int,
    implied_volatility: float,
    historical_volatility: float,
    delta: Optional[float] = None,
    volume: int = 0,
    open_interest: int = 0,
    change_percent: float = 0,
    support_1: Optional[float] = None,
    support_2: Optional[float] = None,
    high_52w: Optional[float] = None,
    low_52w: Optional[float] = None
) -> Dict[str, Any]:
    """
    Calculate Buy Put comprehensive score

    Weights:
    - bearish_momentum: 25%
    - support_break: 20%
    - value_efficiency: 20%
    - volatility_expansion: 15%
    - liquidity: 10%
    - time_value: 10%
    """
    weights = {
        'bearish_momentum': 0.25,
        'support_break': 0.20,
        'value_efficiency': 0.20,
        'volatility_expansion': 0.15,
        'liquidity': 0.10,
        'time_value': 0.10
    }

    mid_price = (bid + ask) / 2 if bid > 0 and ask > 0 else 0
    intrinsic_value = max(0, strike - current_price)
    time_value = max(0, mid_price - intrinsic_value)
    moneyness = (strike - current_price) / current_price * 100 if current_price > 0 else 0

    scores = {}

    # 1. Bearish Momentum Score
    if change_percent <= -3:
        momentum_score = 100
    elif change_percent <= -2:
        momentum_score = 90
    elif change_percent <= -1:
        momentum_score = 75
    elif change_percent <= 0:
        momentum_score = 60
    elif change_percent <= 1:
        momentum_score = 40
    else:
        momentum_score = max(10, 40 - (change_percent - 1) * 10)

    # 52-week position
    if high_52w and low_52w and high_52w > low_52w:
        position = (current_price - low_52w) / (high_52w - low_52w) * 100
        if position <= 20:
            momentum_score += 15
        elif position <= 40:
            momentum_score += 10
        elif position >= 80:
            momentum_score -= 10

    scores['bearish_momentum'] = min(100, momentum_score)

    # 2. Support Break Potential Score
    break_score = 50

    if support_1:
        dist_s1 = (current_price - support_1) / current_price * 100
        if dist_s1 <= 3:
            break_score += 30
        elif dist_s1 <= 6:
            break_score += 20
        elif dist_s1 <= 10:
            break_score += 10

        if strike <= support_1:
            break_score += 20

    if support_2 and strike <= support_2:
        break_score += 15

    if change_percent <= -2 and support_1 and current_price <= support_1 * 1.02:
        break_score += 25

    scores['support_break'] = min(100, break_score)

    # 3. Value Efficiency Score
    if delta and delta < 0 and mid_price > 0:
        efficiency = abs(delta) / mid_price

        if efficiency >= 0.5:
            eff_score = 100
        elif efficiency >= 0.4:
            eff_score = 90
        elif efficiency >= 0.3:
            eff_score = 80
        elif efficiency >= 0.2:
            eff_score = 70
        elif efficiency >= 0.1:
            eff_score = 60
        else:
            eff_score = 40

        # Moneyness adjustment
        if -5 <= moneyness <= 5:
            eff_score += 10
        elif moneyness < -10:
            eff_score -= 10
        elif moneyness > 10:
            eff_score -= 5

        scores['value_efficiency'] = min(100, eff_score)
    else:
        scores['value_efficiency'] = 50

    # 4. Volatility Expansion Score
    vol_score = 50
    if historical_volatility > 0:
        vol_ratio = implied_volatility / historical_volatility

        if vol_ratio <= 0.8:
            vol_score += 30
        elif vol_ratio <= 0.9:
            vol_score += 20
        elif vol_ratio <= 1.0:
            vol_score += 10
        elif vol_ratio <= 1.2:
            vol_score -= 5
        else:
            vol_score -= 15

    # IV percentile
    if implied_volatility <= 0.15:
        vol_score += 25
    elif implied_volatility <= 0.20:
        vol_score += 15
    elif implied_volatility >= 0.35:
        vol_score -= 20

    scores['volatility_expansion'] = min(100, max(0, vol_score))

    # 5. Liquidity Score
    if bid > 0 and ask > 0:
        spread_pct = (ask - bid) / mid_price * 100
        vol_score = min(40, volume / 8)
        oi_score = min(30, open_interest / 40)

        if spread_pct <= 8:
            spread_score = 30
        elif spread_pct <= 15:
            spread_score = 20
        elif spread_pct <= 25:
            spread_score = 10
        else:
            spread_score = max(0, 10 - (spread_pct - 25) / 3)

        scores['liquidity'] = vol_score + oi_score + spread_score
    else:
        scores['liquidity'] = 0

    # 6. Time Value Score
    time_score = 50

    if mid_price > 0:
        time_value_ratio = time_value / mid_price
        if 0.3 <= time_value_ratio <= 0.7:
            time_score += 30
        elif 0.2 <= time_value_ratio < 0.3:
            time_score += 20
        elif 0.7 < time_value_ratio <= 0.8:
            time_score += 15
        elif time_value_ratio > 0.9:
            time_score -= 20
        elif time_value_ratio < 0.1:
            time_score += 10

    if days_to_expiry <= 7:
        time_score -= 15
    elif days_to_expiry <= 30:
        time_score += 10
    elif days_to_expiry <= 60:
        time_score += 15
    elif days_to_expiry <= 90:
        time_score += 5
    else:
        time_score -= 10

    scores['time_value'] = min(100, max(0, time_score))

    # Calculate weighted total
    total_score = sum(scores[k] * weights[k] for k in weights.keys())

    # Breakeven
    breakeven = strike - mid_price
    max_profit = breakeven * 100 if breakeven > 0 else 0

    return {
        'success': True,
        'total_score': round(total_score, 1),
        'score_breakdown': {k: round(v, 1) for k, v in scores.items()},
        'weights': weights,
        'metrics': {
            'mid_price': round(mid_price, 2),
            'time_value': round(time_value, 2),
            'intrinsic_value': round(intrinsic_value, 2),
            'moneyness_pct': round(moneyness, 2),
            'breakeven': round(breakeven, 2),
            'max_loss': round(mid_price * 100, 0),
            'max_profit_potential': round(max_profit, 0)
        }
    }


# =============================================================================
# Risk-Return Profile
# =============================================================================

def calculate_risk_return_profile(
    strategy: str,
    current_price: float,
    strike: float,
    premium: float,
    days_to_expiry: int,
    implied_volatility: float,
    vrp_level: str = 'normal'
) -> Dict[str, Any]:
    """
    Calculate risk-return profile and style classification
    """
    if strategy == 'sell_put':
        safety_margin_pct = (current_price - strike) / current_price * 100
        max_profit_pct = (premium / strike) * 100
        max_loss_pct = ((strike - premium) / strike) * 100
        annualized_return = (max_profit_pct / days_to_expiry) * 365

        # Win probability
        prob_result = calculate_probability(current_price, strike, days_to_expiry, implied_volatility, option_type='put')
        base_win_prob = prob_result.get('prob_profit', 0.60)

        # VRP adjustment
        if vrp_level == 'very_high':
            base_win_prob = min(0.90, base_win_prob + 0.05)
        elif vrp_level == 'high':
            base_win_prob = min(0.85, base_win_prob + 0.03)

        # Style classification
        if safety_margin_pct >= 10 and annualized_return <= 25:
            style = 'steady_income'
            risk_level = 'low'
        elif safety_margin_pct >= 5 and annualized_return <= 40:
            style = 'balanced'
            risk_level = 'moderate'
        elif safety_margin_pct < 3 or annualized_return > 50:
            style = 'high_risk_high_reward'
            risk_level = 'high' if safety_margin_pct >= 0 else 'very_high'
        else:
            style = 'balanced'
            risk_level = 'moderate'

    elif strategy == 'sell_call':
        distance_pct = (strike - current_price) / current_price * 100
        max_profit_pct = (premium / current_price) * 100
        max_loss_pct = 100
        annualized_return = (max_profit_pct / days_to_expiry) * 365

        prob_result = calculate_probability(current_price, strike, days_to_expiry, implied_volatility, option_type='call')
        base_win_prob = 1 - prob_result.get('prob_profit', 0.45)

        if distance_pct >= 15 and annualized_return <= 20:
            style = 'steady_income'
            risk_level = 'moderate'
        elif distance_pct >= 8:
            style = 'balanced'
            risk_level = 'moderate'
        else:
            style = 'high_risk_high_reward'
            risk_level = 'high'

    elif strategy == 'buy_call':
        distance_pct = (strike - current_price) / current_price * 100
        max_loss_pct = 100
        breakeven_move_pct = ((strike + premium - current_price) / current_price) * 100

        prob_result = calculate_probability(current_price, strike + premium, days_to_expiry, implied_volatility, option_type='call')
        base_win_prob = prob_result.get('prob_profit', 0.35)

        # VRP adjustment (low VRP favors buyers)
        if vrp_level == 'very_low':
            base_win_prob = min(0.60, base_win_prob + 0.05)
        elif vrp_level == 'low':
            base_win_prob = min(0.55, base_win_prob + 0.03)

        if distance_pct > 20:
            style = 'high_risk_high_reward'
            risk_level = 'very_high'
            max_profit_pct = 500
        elif distance_pct > 10:
            style = 'high_risk_high_reward'
            risk_level = 'high'
            max_profit_pct = 300
        elif distance_pct > 3:
            style = 'balanced'
            risk_level = 'high'
            max_profit_pct = 200
        else:
            style = 'balanced'
            risk_level = 'moderate'
            max_profit_pct = 150
        annualized_return = 0  # N/A for buyers

    elif strategy == 'buy_put':
        distance_pct = (current_price - strike) / current_price * 100
        hedge_cost_pct = (premium / current_price) * 100
        max_loss_pct = 100
        breakeven = strike - premium

        prob_result = calculate_probability(current_price, breakeven, days_to_expiry, implied_volatility, option_type='put')
        base_win_prob = 1 - prob_result.get('prob_profit', 0.65)

        is_protective = distance_pct <= 5

        if is_protective and hedge_cost_pct <= 5:
            style = 'hedge'
            risk_level = 'low'
            max_profit_pct = 100
        elif distance_pct > 15:
            style = 'high_risk_high_reward'
            risk_level = 'very_high'
            max_profit_pct = 400
        elif distance_pct > 8:
            style = 'high_risk_high_reward'
            risk_level = 'high'
            max_profit_pct = 250
        else:
            style = 'balanced'
            risk_level = 'moderate'
            max_profit_pct = 150
        annualized_return = 0

    else:
        return {
            'success': False,
            'error': f'Unknown strategy: {strategy}'
        }

    # Style labels
    style_labels = {
        'steady_income': {'cn': '稳健收益', 'en': 'STEADY INCOME'},
        'balanced': {'cn': '稳中求进', 'en': 'BALANCED'},
        'high_risk_high_reward': {'cn': '高风险高收益', 'en': 'HIGH RISK HIGH REWARD'},
        'hedge': {'cn': '保护对冲', 'en': 'HEDGE'}
    }

    risk_colors = {
        'low': 'green',
        'moderate': 'yellow',
        'high': 'orange',
        'very_high': 'red'
    }

    risk_reward_ratio = max_profit_pct / max_loss_pct if max_loss_pct > 0 else 0

    return {
        'success': True,
        'style': style,
        'style_label_cn': style_labels[style]['cn'],
        'style_label_en': style_labels[style]['en'],
        'risk_level': risk_level,
        'risk_color': risk_colors[risk_level],
        'win_probability': round(base_win_prob, 2),
        'win_probability_pct': round(base_win_prob * 100, 1),
        'max_profit_pct': round(max_profit_pct, 2),
        'max_loss_pct': round(max_loss_pct, 2),
        'risk_reward_ratio': round(risk_reward_ratio, 3),
        'strategy_type': 'seller' if strategy.startswith('sell') else 'buyer',
        'time_decay_impact': 'positive' if strategy.startswith('sell') else 'negative',
        'volatility_impact': 'negative' if strategy.startswith('sell') else 'positive'
    }

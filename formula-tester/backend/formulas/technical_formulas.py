"""
Technical Analysis Formulas
ATR, RSI, MA, Support/Resistance calculations
"""

import numpy as np
from typing import Dict, Any, List, Optional
import math


def calculate_atr(
    high_prices: List[float],
    low_prices: List[float],
    close_prices: List[float],
    period: int = 14
) -> Dict[str, Any]:
    """
    Calculate Average True Range (ATR)

    True Range = max(
        High - Low,
        |High - PrevClose|,
        |Low - PrevClose|
    )
    ATR = Simple Moving Average of TR over period
    """
    if len(close_prices) < period + 1:
        return {
            'success': False,
            'error': f'Need at least {period + 1} data points, got {len(close_prices)}'
        }

    high = np.array(high_prices)
    low = np.array(low_prices)
    close = np.array(close_prices)

    # Calculate True Range components
    tr1 = high[1:] - low[1:]  # Current high - current low
    tr2 = np.abs(high[1:] - close[:-1])  # |Current high - Previous close|
    tr3 = np.abs(low[1:] - close[:-1])  # |Current low - Previous close|

    # True Range is the maximum of the three
    tr = np.maximum(np.maximum(tr1, tr2), tr3)

    # ATR is the simple moving average of TR
    atr = np.mean(tr[-period:])

    # Calculate ATR as percentage of current price
    current_price = close[-1]
    atr_pct = (atr / current_price) * 100 if current_price > 0 else 0

    return {
        'success': True,
        'atr': round(atr, 4),
        'atr_pct': round(atr_pct, 2),
        'current_price': current_price,
        'period': period,
        'true_range_history': tr[-period:].tolist()
    }


def calculate_atr_stop_loss(
    buy_price: float,
    atr: float,
    atr_multiplier: float = 2.5,
    min_stop_loss_pct: float = 0.15,
    beta: Optional[float] = None
) -> Dict[str, Any]:
    """
    Calculate ATR-based stop loss with beta adjustment
    """
    if buy_price <= 0 or atr <= 0:
        return {
            'success': False,
            'error': 'Buy price and ATR must be positive'
        }

    # Beta adjustment
    adjusted_multiplier = atr_multiplier
    if beta is not None:
        if beta > 1.5:
            adjusted_multiplier = atr_multiplier * 1.2
        elif beta < 0.8:
            adjusted_multiplier = atr_multiplier * 0.8

    # ATR-based stop loss
    atr_stop_loss = buy_price - (atr * adjusted_multiplier)
    atr_stop_loss_pct = (buy_price - atr_stop_loss) / buy_price

    # Minimum stop loss
    min_stop_loss_price = buy_price * (1 - min_stop_loss_pct)

    # Final stop loss (max of ATR-based and minimum)
    if atr_stop_loss > min_stop_loss_price:
        final_stop_loss = atr_stop_loss
        method = 'ATR-based'
    else:
        final_stop_loss = min_stop_loss_price
        method = 'Minimum percentage'

    final_stop_loss_pct = (buy_price - final_stop_loss) / buy_price

    return {
        'success': True,
        'stop_loss_price': round(final_stop_loss, 2),
        'stop_loss_pct': round(final_stop_loss_pct * 100, 2),
        'atr_stop_loss': round(atr_stop_loss, 2),
        'atr_stop_loss_pct': round(atr_stop_loss_pct * 100, 2),
        'min_stop_loss': round(min_stop_loss_price, 2),
        'method': method,
        'adjusted_multiplier': round(adjusted_multiplier, 2),
        'beta_used': beta
    }


def calculate_rsi(
    prices: List[float],
    period: int = 14
) -> Dict[str, Any]:
    """
    Calculate Relative Strength Index (RSI)

    RSI = 100 - (100 / (1 + RS))
    RS = Average Gain / Average Loss
    """
    if len(prices) < period + 1:
        return {
            'success': False,
            'error': f'Need at least {period + 1} prices, got {len(prices)}'
        }

    prices_arr = np.array(prices)
    deltas = np.diff(prices_arr)

    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)

    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])

    if avg_loss == 0:
        rsi = 100
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

    # Signal interpretation
    if rsi >= 70:
        signal = 'overbought'
    elif rsi <= 30:
        signal = 'oversold'
    else:
        signal = 'neutral'

    return {
        'success': True,
        'rsi': round(rsi, 2),
        'signal': signal,
        'avg_gain': round(avg_gain, 4),
        'avg_loss': round(avg_loss, 4),
        'period': period
    }


def calculate_moving_averages(
    prices: List[float],
    periods: List[int] = [5, 20, 50, 200]
) -> Dict[str, Any]:
    """
    Calculate multiple Simple Moving Averages
    """
    prices_arr = np.array(prices)
    current_price = prices_arr[-1]

    results = {
        'success': True,
        'current_price': current_price,
        'moving_averages': {}
    }

    for period in periods:
        if len(prices_arr) >= period:
            ma = np.mean(prices_arr[-period:])
            position_pct = ((current_price - ma) / ma) * 100
            results['moving_averages'][f'MA{period}'] = {
                'value': round(ma, 2),
                'position_pct': round(position_pct, 2),
                'above': current_price > ma
            }
        else:
            results['moving_averages'][f'MA{period}'] = {
                'value': None,
                'error': f'Need at least {period} prices'
            }

    return results


def calculate_volatility(
    prices: List[float],
    period: int = 30
) -> Dict[str, Any]:
    """
    Calculate annualized historical volatility
    """
    if len(prices) < period + 1:
        return {
            'success': False,
            'error': f'Need at least {period + 1} prices'
        }

    prices_arr = np.array(prices[-period-1:])
    returns = np.diff(prices_arr) / prices_arr[:-1]

    daily_vol = np.std(returns)
    annualized_vol = daily_vol * math.sqrt(252)

    return {
        'success': True,
        'daily_volatility': round(daily_vol * 100, 4),
        'annualized_volatility': round(annualized_vol * 100, 2),
        'period': period
    }


def calculate_atr_safety_margin(
    current_price: float,
    strike: float,
    atr: float,
    atr_ratio: float = 2.0
) -> Dict[str, Any]:
    """
    Calculate ATR-based safety margin for options

    Safety Ratio = Actual Buffer / Required Buffer
    Required Buffer = ATR * ratio
    """
    if atr <= 0:
        return {
            'success': False,
            'error': 'ATR must be positive'
        }

    required_buffer = atr * atr_ratio
    actual_buffer = abs(current_price - strike)
    safety_ratio = actual_buffer / required_buffer
    atr_multiples = actual_buffer / atr
    is_safe = safety_ratio >= 1.0

    # Safety score
    if safety_ratio >= 2.0:
        base_score = 100
    elif safety_ratio >= 1.5:
        base_score = 90 + (safety_ratio - 1.5) * 20
    elif safety_ratio >= 1.0:
        base_score = 70 + (safety_ratio - 1.0) * 40
    elif safety_ratio >= 0.5:
        base_score = 40 + (safety_ratio - 0.5) * 60
    else:
        base_score = max(0, safety_ratio * 80)

    # ATR multiples bonus
    if atr_multiples >= 3:
        bonus = 10
    elif atr_multiples >= 2:
        bonus = 5
    elif atr_multiples < 1:
        bonus = -10
    else:
        bonus = 0

    safety_score = min(100, max(0, base_score + bonus))

    return {
        'success': True,
        'safety_ratio': round(safety_ratio, 2),
        'atr_multiples': round(atr_multiples, 2),
        'is_safe': is_safe,
        'safety_score': round(safety_score, 1),
        'required_buffer': round(required_buffer, 2),
        'actual_buffer': round(actual_buffer, 2),
        'atr': round(atr, 2),
        'atr_pct': round((atr / current_price) * 100, 2) if current_price > 0 else 0
    }


def calculate_liquidity_score(
    volume: int,
    open_interest: int,
    bid: float,
    ask: float
) -> Dict[str, Any]:
    """
    Calculate options liquidity score
    """
    if bid <= 0 or ask <= 0:
        return {
            'success': False,
            'error': 'Bid and ask must be positive'
        }

    mid_price = (bid + ask) / 2
    bid_ask_spread = ask - bid
    bid_ask_spread_pct = (bid_ask_spread / mid_price) * 100

    # Volume score (max 50)
    volume_score = min(50, volume / 10)

    # Open interest score (max 30)
    oi_score = min(30, open_interest / 50)

    # Spread score (max 20)
    if bid_ask_spread_pct <= 5:
        spread_score = 20
    elif bid_ask_spread_pct <= 10:
        spread_score = 15
    elif bid_ask_spread_pct <= 20:
        spread_score = 10
    else:
        spread_score = max(0, 10 - (bid_ask_spread_pct - 20) / 2)

    total_score = volume_score + oi_score + spread_score

    return {
        'success': True,
        'total_score': round(total_score, 1),
        'volume_score': round(volume_score, 1),
        'oi_score': round(oi_score, 1),
        'spread_score': round(spread_score, 1),
        'bid_ask_spread': round(bid_ask_spread, 2),
        'bid_ask_spread_pct': round(bid_ask_spread_pct, 2),
        'mid_price': round(mid_price, 2)
    }

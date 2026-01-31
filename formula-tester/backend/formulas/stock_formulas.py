"""
Stock Analysis Formulas
Risk scoring, sentiment, target price, style scoring
"""

import numpy as np
from typing import Dict, Any, List, Optional
import math


def calculate_risk_score(
    volatility: float,  # Annualized volatility as decimal (e.g., 0.30 = 30%)
    pe_ratio: Optional[float] = None,
    debt_to_equity: Optional[float] = None,
    market_cap: Optional[float] = None,
    risk_premium: Optional[float] = None,
    sector: str = 'general'
) -> Dict[str, Any]:
    """
    Calculate comprehensive risk score (0-100)

    Components:
    - Volatility risk (0-25)
    - Valuation risk (0-20)
    - Financial risk (0-15)
    - Market cap risk (0-10)
    - Market risk premium adjustment
    """
    risk_score = 0
    components = {}

    # 1. Volatility Risk (0-25)
    if volatility > 0.5:
        vol_risk = 25
    elif volatility > 0.3:
        vol_risk = 15
    elif volatility > 0.2:
        vol_risk = 8
    else:
        vol_risk = 0
    risk_score += vol_risk
    components['volatility_risk'] = vol_risk

    # 2. Valuation Risk (0-20)
    val_risk = 0
    if pe_ratio is not None:
        pe_high = 25 if sector in ['Technology', 'Healthcare'] else 20
        if pe_ratio > pe_high * 1.5:
            val_risk = 20
        elif pe_ratio > pe_high:
            val_risk = 10
        elif pe_ratio < 8 and pe_ratio > 0:
            val_risk = 15  # Abnormally low
    risk_score += val_risk
    components['valuation_risk'] = val_risk

    # 3. Financial Risk (0-15)
    fin_risk = 0
    if debt_to_equity is not None:
        if debt_to_equity > 200:
            fin_risk = 15
        elif debt_to_equity > 100:
            fin_risk = 8
        elif debt_to_equity > 50:
            fin_risk = 3
    risk_score += fin_risk
    components['financial_risk'] = fin_risk

    # 4. Market Cap Risk (0-10)
    cap_risk = 0
    if market_cap is not None:
        if market_cap < 1_000_000_000:  # < $1B
            cap_risk = 10
        elif market_cap < 5_000_000_000:  # < $5B
            cap_risk = 5
    risk_score += cap_risk
    components['market_cap_risk'] = cap_risk

    # 5. Market Risk Premium Adjustment
    premium_adj = 0
    if risk_premium is not None and risk_premium > 1.0:
        premium_adj = (risk_premium - 1.0) * 20
        risk_score += premium_adj
    components['risk_premium_adjustment'] = round(premium_adj, 1)

    # Cap at 100
    risk_score = min(100, risk_score)

    # Determine risk level and position size
    if risk_score >= 60:
        risk_level = 'high'
        position_size_pct = 2
    elif risk_score >= 35:
        risk_level = 'medium'
        position_size_pct = 3
    else:
        risk_level = 'low'
        position_size_pct = 5

    # Risk adjustment factor for target price
    risk_adjustment_factor = max(1 - (risk_score / 100) * 0.5, 0.5)

    return {
        'success': True,
        'risk_score': round(risk_score, 1),
        'risk_level': risk_level,
        'position_size_pct': position_size_pct,
        'risk_adjustment_factor': round(risk_adjustment_factor, 3),
        'components': components
    }


def calculate_market_sentiment(
    prices: List[float],
    volumes: List[float]
) -> Dict[str, Any]:
    """
    Calculate market sentiment score (-100 to +100)

    Components:
    - Price momentum (capped at +/- 50)
    - Volume trend (capped at +/- 25)
    - Volatility (negative score for high vol)
    - Technical position vs MAs
    """
    if len(prices) < 20 or len(volumes) < 20:
        return {
            'success': False,
            'error': 'Need at least 20 data points for prices and volumes'
        }

    prices_arr = np.array(prices)
    volumes_arr = np.array(volumes)
    current_price = prices_arr[-1]

    components = {}

    # 1. Price Momentum (-50 to +50)
    recent_prices = prices_arr[-5:]
    price_trend = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]
    momentum_score = min(max(price_trend * 100, -50), 50)
    components['price_momentum'] = round(momentum_score, 1)

    # 2. Volume Trend (-25 to +25)
    avg_vol_5d = np.mean(volumes_arr[-5:])
    avg_vol_20d = np.mean(volumes_arr[-20:])
    vol_ratio = avg_vol_5d / avg_vol_20d if avg_vol_20d > 0 else 1
    volume_score = min(max((vol_ratio - 1) * 50, -25), 25)
    components['volume_trend'] = round(volume_score, 1)

    # 3. Volatility (negative for high vol)
    price_changes = np.diff(prices_arr) / prices_arr[:-1]
    daily_vol = np.std(price_changes)
    annualized_vol = daily_vol * math.sqrt(252)
    volatility_score = -min(annualized_vol * 100, 30)
    components['volatility'] = round(volatility_score, 1)

    # 4. Technical Position
    sma_20 = np.mean(prices_arr[-20:])
    sma_50 = np.mean(prices_arr[-50:]) if len(prices_arr) >= 50 else sma_20

    pos_vs_sma20 = (current_price - sma_20) / sma_20
    pos_vs_sma50 = (current_price - sma_50) / sma_50
    technical_score = (pos_vs_sma20 + pos_vs_sma50) * 25
    technical_score = min(max(technical_score, -25), 25)
    components['technical_position'] = round(technical_score, 1)

    # Overall score
    overall_score = momentum_score + volume_score + volatility_score + technical_score
    overall_score = max(min(overall_score, 100), -100)

    # Signal interpretation
    if overall_score >= 30:
        signal = 'bullish'
    elif overall_score >= 10:
        signal = 'slightly_bullish'
    elif overall_score <= -30:
        signal = 'bearish'
    elif overall_score <= -10:
        signal = 'slightly_bearish'
    else:
        signal = 'neutral'

    return {
        'success': True,
        'overall_score': round(overall_score, 1),
        'signal': signal,
        'components': components
    }


def calculate_target_price(
    current_price: float,
    pe_ratio: Optional[float] = None,
    forward_pe: Optional[float] = None,
    peg_ratio: Optional[float] = None,
    book_value: Optional[float] = None,
    revenue_growth: Optional[float] = None,
    earnings_growth: Optional[float] = None,
    risk_score: float = 50,
    style: str = 'balanced'  # growth, value, balanced
) -> Dict[str, Any]:
    """
    Calculate target price using multiple methods

    Methods:
    1. PE Multiple Method
    2. PEG Valuation Method
    3. Price-to-Book Method
    4. Revenue Growth Method
    """
    if current_price <= 0:
        return {
            'success': False,
            'error': 'Current price must be positive'
        }

    methods_used = []
    target_prices = []

    # 1. PE Multiple Method
    if pe_ratio and pe_ratio > 0:
        if style == 'growth':
            reasonable_pe = pe_ratio * 1.1
        elif style == 'value':
            reasonable_pe = pe_ratio * 0.9
        else:
            reasonable_pe = pe_ratio

        eps = current_price / pe_ratio
        target_pe = eps * reasonable_pe
        target_prices.append(target_pe)
        methods_used.append({
            'method': 'PE Multiple',
            'target': round(target_pe, 2),
            'reasonable_pe': round(reasonable_pe, 1)
        })

    # 2. PEG Valuation Method
    if peg_ratio and earnings_growth and pe_ratio:
        reasonable_peg = 1.0 if style == 'growth' else 0.8
        target_pe_peg = earnings_growth * 100 * reasonable_peg
        eps = current_price / pe_ratio
        target_peg = eps * target_pe_peg
        if target_peg > 0:
            target_prices.append(target_peg)
            methods_used.append({
                'method': 'PEG Valuation',
                'target': round(target_peg, 2),
                'implied_pe': round(target_pe_peg, 1)
            })

    # 3. Price-to-Book Method
    if book_value and book_value > 0:
        pb_ratio = current_price / book_value
        reasonable_pb = max(pb_ratio * 0.9, 1.0)
        target_pb = book_value * reasonable_pb
        target_prices.append(target_pb)
        methods_used.append({
            'method': 'Price-to-Book',
            'target': round(target_pb, 2),
            'reasonable_pb': round(reasonable_pb, 2)
        })

    # 4. Revenue Growth Method
    if revenue_growth:
        growth_multiplier = min(1 + revenue_growth, 1.3)  # Max 30% upside
        target_rev = current_price * growth_multiplier
        target_prices.append(target_rev)
        methods_used.append({
            'method': 'Revenue Growth',
            'target': round(target_rev, 2),
            'growth_multiplier': round(growth_multiplier, 2)
        })

    if not target_prices:
        return {
            'success': False,
            'error': 'Insufficient data for any valuation method'
        }

    # Calculate average target
    avg_target = np.mean(target_prices)

    # Apply risk adjustment
    risk_adjustment_factor = max(1 - (risk_score / 100) * 0.5, 0.5)
    adjusted_target = current_price + (avg_target - current_price) * risk_adjustment_factor

    upside_potential = ((adjusted_target - current_price) / current_price) * 100

    # Confidence level
    if len(methods_used) >= 3:
        confidence = 'high'
    elif len(methods_used) >= 2:
        confidence = 'medium'
    else:
        confidence = 'low'

    return {
        'success': True,
        'target_price': round(adjusted_target, 2),
        'upside_potential_pct': round(upside_potential, 1),
        'unadjusted_target': round(avg_target, 2),
        'risk_adjustment_factor': round(risk_adjustment_factor, 3),
        'confidence': confidence,
        'methods_used': methods_used
    }


def calculate_growth_score(
    revenue_growth: Optional[float] = None,  # As decimal, e.g., 0.25 = 25%
    earnings_growth: Optional[float] = None,
    peg_ratio: Optional[float] = None
) -> Dict[str, Any]:
    """
    Calculate growth stock score (0-100)
    """
    score = 0
    components = {}

    # Revenue Growth Score (max 30)
    if revenue_growth is not None:
        if revenue_growth > 0.25:
            rev_score = 30
        elif revenue_growth > 0.15:
            rev_score = 20
        elif revenue_growth > 0.08:
            rev_score = 10
        elif revenue_growth > 0:
            rev_score = 5
        else:
            rev_score = 0
        score += rev_score
        components['revenue_growth'] = rev_score

    # Earnings Growth Score (max 25)
    if earnings_growth is not None:
        if earnings_growth > 0.30:
            earn_score = 25
        elif earnings_growth > 0.15:
            earn_score = 15
        elif earnings_growth > 0:
            earn_score = 5
        else:
            earn_score = 0
        score += earn_score
        components['earnings_growth'] = earn_score

    # PEG Ratio Score (max 15)
    if peg_ratio is not None and peg_ratio > 0:
        if peg_ratio < 1.0:
            peg_score = 15
        elif peg_ratio < 1.5:
            peg_score = 10
        elif peg_ratio < 2.0:
            peg_score = 5
        else:
            peg_score = 0
        score += peg_score
        components['peg_ratio'] = peg_score

    # Rating
    if score >= 50:
        rating = 'excellent'
    elif score >= 30:
        rating = 'good'
    elif score >= 15:
        rating = 'fair'
    else:
        rating = 'poor'

    return {
        'success': True,
        'growth_score': score,
        'rating': rating,
        'components': components
    }


def calculate_value_score(
    pe_ratio: Optional[float] = None,
    pb_ratio: Optional[float] = None,
    dividend_yield: Optional[float] = None  # As decimal
) -> Dict[str, Any]:
    """
    Calculate value stock score (0-100)
    """
    score = 0
    components = {}

    # PE Ratio Score (max 25)
    if pe_ratio is not None and pe_ratio > 0:
        if pe_ratio < 10:
            pe_score = 25
        elif pe_ratio < 15:
            pe_score = 20
        elif pe_ratio < 20:
            pe_score = 10
        elif pe_ratio < 25:
            pe_score = 5
        else:
            pe_score = 0
        score += pe_score
        components['pe_ratio'] = pe_score

    # PB Ratio Score (max 20)
    if pb_ratio is not None and pb_ratio > 0:
        if pb_ratio < 1.0:
            pb_score = 20
        elif pb_ratio < 1.5:
            pb_score = 15
        elif pb_ratio < 2.5:
            pb_score = 10
        elif pb_ratio < 4.0:
            pb_score = 5
        else:
            pb_score = 0
        score += pb_score
        components['pb_ratio'] = pb_score

    # Dividend Yield Score (max 15)
    if dividend_yield is not None:
        if dividend_yield > 0.04:
            div_score = 15
        elif dividend_yield > 0.02:
            div_score = 10
        elif dividend_yield > 0:
            div_score = 5
        else:
            div_score = 0
        score += div_score
        components['dividend_yield'] = div_score

    # Rating
    if score >= 45:
        rating = 'excellent'
    elif score >= 30:
        rating = 'good'
    elif score >= 15:
        rating = 'fair'
    else:
        rating = 'poor'

    return {
        'success': True,
        'value_score': score,
        'rating': rating,
        'components': components
    }


def calculate_quality_score(
    roe: Optional[float] = None,  # As decimal
    gross_margin: Optional[float] = None,
    fcf_to_net_income: Optional[float] = None,
    debt_to_equity: Optional[float] = None
) -> Dict[str, Any]:
    """
    Calculate quality stock score (0-100)
    """
    score = 0
    components = {}

    # ROE Score (max 30)
    if roe is not None:
        if roe > 0.25:
            roe_score = 30
        elif roe > 0.20:
            roe_score = 25
        elif roe > 0.15:
            roe_score = 20
        elif roe > 0.10:
            roe_score = 12
        elif roe > 0:
            roe_score = 5
        else:
            roe_score = 0
        score += roe_score
        components['roe'] = roe_score

    # Gross Margin Score (max 20)
    if gross_margin is not None:
        if gross_margin > 0.50:
            margin_score = 20
        elif gross_margin > 0.40:
            margin_score = 16
        elif gross_margin > 0.30:
            margin_score = 12
        elif gross_margin > 0.20:
            margin_score = 6
        else:
            margin_score = 0
        score += margin_score
        components['gross_margin'] = margin_score

    # FCF Quality Score (max 20)
    if fcf_to_net_income is not None:
        if fcf_to_net_income > 1.0:
            fcf_score = 20
        elif fcf_to_net_income > 0.8:
            fcf_score = 15
        elif fcf_to_net_income > 0.5:
            fcf_score = 10
        elif fcf_to_net_income > 0:
            fcf_score = 5
        else:
            fcf_score = 0
        score += fcf_score
        components['fcf_quality'] = fcf_score

    # Debt Score (max 15)
    if debt_to_equity is not None:
        if debt_to_equity < 30:
            debt_score = 15
        elif debt_to_equity < 50:
            debt_score = 12
        elif debt_to_equity < 100:
            debt_score = 8
        elif debt_to_equity < 150:
            debt_score = 4
        else:
            debt_score = 0
        score += debt_score
        components['debt'] = debt_score

    # Rating
    if score >= 60:
        rating = 'excellent'
    elif score >= 40:
        rating = 'good'
    elif score >= 20:
        rating = 'fair'
    else:
        rating = 'poor'

    return {
        'success': True,
        'quality_score': score,
        'rating': rating,
        'components': components
    }


def calculate_momentum_score(
    prices: List[float],
    volumes: List[float],
    week_52_high: Optional[float] = None,
    week_52_low: Optional[float] = None
) -> Dict[str, Any]:
    """
    Calculate momentum stock score (0-100)
    """
    if len(prices) < 50:
        return {
            'success': False,
            'error': 'Need at least 50 price data points'
        }

    prices_arr = np.array(prices)
    volumes_arr = np.array(volumes)
    current_price = prices_arr[-1]

    score = 0
    components = {}

    # 5-day change score (max 25)
    change_5d = (prices_arr[-1] / prices_arr[-5] - 1) * 100
    if change_5d > 8:
        score_5d = 25
    elif change_5d > 5:
        score_5d = 20
    elif change_5d > 2:
        score_5d = 15
    elif change_5d > -2:
        score_5d = 8
    elif change_5d > -5:
        score_5d = 3
    else:
        score_5d = 0
    score += score_5d
    components['change_5d'] = score_5d

    # MA Trend Score (max 30)
    ma20 = np.mean(prices_arr[-20:])
    ma50 = np.mean(prices_arr[-50:])
    ma_ratio = ma20 / ma50

    if ma_ratio > 1.08:
        ma_score = 25
    elif ma_ratio > 1.03:
        ma_score = 20
    elif ma_ratio > 0.98:
        ma_score = 12
    elif ma_ratio > 0.93:
        ma_score = 5
    else:
        ma_score = 0

    # Golden cross bonus
    if current_price > ma20 > ma50:
        ma_score += 5

    score += ma_score
    components['ma_trend'] = ma_score

    # RSI Score (max 20)
    deltas = np.diff(prices_arr[-15:])
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains)
    avg_loss = np.mean(losses)

    if avg_loss == 0:
        rsi = 100
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

    if 60 <= rsi <= 70:
        rsi_score = 20
    elif 50 <= rsi < 60:
        rsi_score = 15
    elif 40 <= rsi < 50:
        rsi_score = 10
    elif rsi > 70:
        rsi_score = 8
    elif rsi < 30:
        rsi_score = 5
    else:
        rsi_score = 3
    score += rsi_score
    components['rsi'] = rsi_score

    # Volume Score (max 12)
    vol_5d = np.mean(volumes_arr[-5:])
    vol_20d = np.mean(volumes_arr[-20:])
    vol_ratio = vol_5d / vol_20d if vol_20d > 0 else 1

    if vol_ratio > 2.0:
        vol_score = 12
    elif vol_ratio > 1.5:
        vol_score = 10
    elif vol_ratio > 1.0:
        vol_score = 6
    elif vol_ratio > 0.5:
        vol_score = 3
    else:
        vol_score = 0
    score += vol_score
    components['volume'] = vol_score

    # 52-week position bonus (max 8)
    pos_score = 0
    if week_52_high and week_52_low and week_52_high > week_52_low:
        position = (current_price - week_52_low) / (week_52_high - week_52_low)
        if position > 0.9:
            pos_score = 8
        elif position > 0.7:
            pos_score = 5
        elif position > 0.5:
            pos_score = 2
    score += pos_score
    components['52_week_position'] = pos_score

    # Rating
    if score >= 70:
        rating = 'excellent'
    elif score >= 50:
        rating = 'good'
    elif score >= 30:
        rating = 'fair'
    else:
        rating = 'poor'

    return {
        'success': True,
        'momentum_score': score,
        'rating': rating,
        'rsi': round(rsi, 1),
        'ma_ratio': round(ma_ratio, 3),
        'change_5d_pct': round(change_5d, 2),
        'components': components
    }

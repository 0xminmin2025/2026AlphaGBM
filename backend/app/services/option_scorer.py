"""
Option scoring algorithms based on quantitative models
Ported from new_options_module/scoring/option_scorer.py
"""

import math
from datetime import datetime
from typing import Optional
from scipy.stats import norm
from .option_models import OptionData, OptionScores, ScoringParams

class OptionScorer:
    """Option scoring calculator implementing quantitative models"""

    def __init__(self, params: Optional[ScoringParams] = None):
        self.params = params or ScoringParams()

    def calculate_days_to_expiry(self, expiry_date: str) -> int:
        """Calculate days to expiration"""
        try:
            expiry = datetime.strptime(expiry_date, "%Y-%m-%d")
            today = datetime.now()
            return max(1, (expiry - today).days)  # Minimum 1 day to avoid division by zero
        except:
            return 30  # Default fallback

    def calculate_liquidity_factor(self, bid_price: float, ask_price: float,
                                 open_interest: Optional[int] = None,
                                 latest_price: Optional[float] = None) -> float:
        """
        Calculate composite liquidity factor based on bid-ask spread ratio and Open Interest (OI)
        """
        # ========== 一票否决：OI < 10 ==========
        if open_interest is not None and open_interest < 10:
            return 0.0  # Veto: insufficient OI depth
        
        # ========== Spread Score (40% weight) ==========
        spread_score = 0.5  # Default poor liquidity
        if bid_price and ask_price and bid_price > 0 and ask_price > 0:
            mid_price = (bid_price + ask_price) / 2
            if mid_price > 0:
                spread_ratio = (ask_price - bid_price) / mid_price
                
                if spread_ratio <= 0.01:  # <1%
                    spread_score = 1.0
                elif spread_ratio <= 0.03:  # 1-3%
                    spread_score = 0.8 + (0.03 - spread_ratio) / 0.02 * 0.2
                elif spread_ratio <= 0.05:  # 3-5%
                    spread_score = 0.5 + (0.05 - spread_ratio) / 0.02 * 0.3
                elif spread_ratio <= 0.10:  # 5-10%
                    spread_score = 0.2 + (0.10 - spread_ratio) / 0.05 * 0.3
                else:  # >10%
                    spread_score = 0.0
        
        # ========== OI Score (60% weight) ==========
        oi_score = 0.0  # Default no liquidity
        if open_interest is not None and open_interest >= 10:
            if open_interest >= 500:
                oi_score = 1.0
            elif open_interest >= 200:
                oi_score = 0.8 + (open_interest - 200) / 300 * 0.15
            elif open_interest >= 50:
                oi_score = 0.6 + (open_interest - 50) / 150 * 0.2
            elif open_interest >= 10:
                oi_score = 0.3 + (open_interest - 10) / 40 * 0.3
        elif open_interest is None:
            oi_score = 0.3
        
        # ========== Composite Factor = 40% Spread + 60% OI ==========
        composite_factor = 0.4 * spread_score + 0.6 * oi_score
        
        # Ensure result is in valid range [0.0, 1.0]
        return max(0.0, min(1.0, composite_factor))

    def calculate_iv_rank(self, implied_vol: Optional[float]) -> float:
        """Estimate IV Rank (simplified calculation)"""
        if not implied_vol:
            return 50.0  # Default moderate IV rank

        if implied_vol < 0.15:      # Low IV
            return 20.0
        elif implied_vol < 0.25:    # Moderate IV
            return 40.0
        elif implied_vol < 0.35:    # Elevated IV
            return 60.0
        elif implied_vol < 0.50:    # High IV
            return 80.0
        else:                       # Very high IV
            return 95.0

    def calculate_iv_percentile(self, implied_vol: Optional[float]) -> float:
        """Estimate IV Percentile (simplified calculation)"""
        if not implied_vol:
            return 50.0

        iv_rank = self.calculate_iv_rank(implied_vol)
        return min(99.0, iv_rank + 5.0)  # IVP typically slightly higher than IVR

    def calculate_assignment_probability(self, option: OptionData, stock_price: float) -> Optional[float]:
        """Calculate assignment probability using Black-Scholes N(d2) formula"""
        if (not option.implied_vol or not option.strike or
            option.implied_vol <= 0 or option.strike <= 0 or stock_price <= 0):
            return None

        dte_days = self.calculate_days_to_expiry(option.expiry_date)
        T = dte_days / 365.0

        if T <= 0:
            if option.put_call == "PUT":
                return 100.0 if stock_price < option.strike else 0.0
            else:  # CALL
                return 100.0 if stock_price > option.strike else 0.0

        S = stock_price
        K = option.strike
        r = self.params.risk_free_rate
        sigma = option.implied_vol

        try:
            ln_s_k = math.log(S / K)
            sqrt_t = math.sqrt(T)
            d2 = (ln_s_k + (r - 0.5 * sigma**2) * T) / (sigma * sqrt_t)
            prob_itm = norm.cdf(d2)

            if option.put_call == "PUT":
                assignment_prob = (1.0 - prob_itm) * 100.0
            else:  # CALL
                assignment_prob = prob_itm * 100.0

            return max(0.0, min(100.0, assignment_prob))

        except (ValueError, ZeroDivisionError):
            return None

    def calculate_sprv(self, option: OptionData, stock_price: float) -> float:
        """Calculate Sell Put Recommendation Value (SPRV)"""
        if (not option.latest_price or not option.delta or not option.strike or
            option.put_call != "PUT" or option.latest_price <= 0):
            return 0.0

        dte = self.calculate_days_to_expiry(option.expiry_date)
        premium = option.latest_price * 100

        if option.strike <= 0:
            return 0.0
        annual_return = (premium / (option.strike * 100)) * (365 / dte)

        win_rate_weight = (1 - abs(option.delta)) ** self.params.sprv_delta_power
        iv_rank = self.calculate_iv_rank(option.implied_vol)
        volatility_premium = math.log10(iv_rank + self.params.sprv_ivr_base)

        liquidity = self.calculate_liquidity_factor(
            option.bid_price or 0, option.ask_price or 0, 
            option.open_interest, option.latest_price
        )

        sprv = annual_return * win_rate_weight * volatility_premium * liquidity
        return round(sprv, 4)

    def calculate_scrv(self, option: OptionData, stock_price: float) -> float:
        """Calculate Sell Call Recommendation Value (SCRV)"""
        if (not option.latest_price or not option.delta or not option.theta or
            not option.strike or option.put_call != "CALL" or
            option.delta <= 0 or stock_price <= 0):
            return 0.0

        annual_theta_yield = (abs(option.theta) * 365) / stock_price
        anti_callback = 1.0 / option.delta
        iv_percentile = self.calculate_iv_percentile(option.implied_vol)
        volatility_reward = 1.0 + (iv_percentile / 100.0) * self.params.scrv_ivp_weight

        if option.strike <= stock_price:
            upside_space = 0.01
        else:
            upside_space = (option.strike - stock_price) / stock_price

        scrv = annual_theta_yield * anti_callback * volatility_reward * upside_space
        return round(scrv, 4)

    def calculate_bcrv(self, option: OptionData, stock_price: float) -> float:
        """Calculate Buy Call Recommendation Value (BCRV)"""
        if (not option.latest_price or not option.delta or not option.gamma or
            not option.theta or option.put_call != "CALL" or
            abs(option.theta) <= 0):
            return 0.0

        efficiency_ratio = option.gamma / abs(option.theta)
        iv_rank = self.calculate_iv_rank(option.implied_vol)
        low_vol_bonus = 100.0 / (iv_rank + 1.0)
        directional_leverage = option.delta ** 2

        volume_score = 1.0
        if option.volume and option.volume >= self.params.bcrv_min_volume:
            volume_score = min(2.0, option.volume / self.params.bcrv_min_volume)
        elif option.volume and option.volume < self.params.bcrv_min_volume:
            volume_score = 0.5
        
        bcrv = efficiency_ratio * low_vol_bonus * directional_leverage * volume_score
        return round(bcrv, 4)

    def calculate_bprv(self, option: OptionData, stock_price: float) -> float:
        """Calculate Buy Put Recommendation Value (BPRV)"""
        if (not option.latest_price or not option.delta or
            option.put_call != "PUT" or option.latest_price <= 0):
            return 0.0

        premium = option.latest_price
        hedge_leverage = abs(option.delta) / premium
        iv_rank = self.calculate_iv_rank(option.implied_vol)
        reverse_vrp = max(0.1, (100.0 - iv_rank) / 100.0)
        correlation_hedge = 1.0 - self.params.bprv_correlation
        
        distance_from_atm = abs(option.strike - stock_price) / stock_price
        skew_factor = max(0.5, 1.0 - distance_from_atm * self.params.bprv_skew_penalty)

        bprv = hedge_leverage * reverse_vrp * correlation_hedge * skew_factor
        return round(bprv, 4)

    def calculate_premium_and_margin(self, option: OptionData, stock_price: float, 
                                    margin_rate: Optional[float] = None) -> tuple:
        """Calculate premium income and capital requirement for sell strategies"""
        if not option.latest_price or option.latest_price <= 0:
            return 0.0, 0.0, 0.0

        premium_income = option.latest_price * 100
        capital_requirement = 0.0

        if option.put_call == "PUT":
            if margin_rate is not None:
                capital_requirement = option.strike * 100 * margin_rate
            else:
                otm_amount = max(0, (option.strike - stock_price)) * 100
                margin_20pct = 0.20 * option.strike * 100
                margin_10pct = 0.10 * option.strike * 100
                capital_requirement = max(margin_20pct - otm_amount, margin_10pct) + premium_income

        elif option.put_call == "CALL":
            if margin_rate is not None:
                capital_requirement = stock_price * 100 * margin_rate
            else:
                capital_requirement = stock_price * 100

        dte = self.calculate_days_to_expiry(option.expiry_date)
        annualized_return = 0.0
        if capital_requirement > 0 and dte > 0:
            return_rate = premium_income / capital_requirement
            annualized_return = (return_rate * 365 / dte) * 100

        return round(premium_income, 2), round(capital_requirement, 2), round(annualized_return, 2)

    def score_option(self, option: OptionData, stock_price: float, 
                     margin_rate: Optional[float] = None) -> OptionScores:
        """Calculate all scoring metrics for an option"""
        scores = OptionScores()

        scores.days_to_expiry = self.calculate_days_to_expiry(option.expiry_date)
        scores.liquidity_factor = self.calculate_liquidity_factor(
            option.bid_price or 0, option.ask_price or 0, 
            option.open_interest, option.latest_price
        )
        scores.iv_rank = self.calculate_iv_rank(option.implied_vol)
        scores.iv_percentile = self.calculate_iv_percentile(option.implied_vol)
        scores.assignment_probability = self.calculate_assignment_probability(option, stock_price)

        if option.put_call == "PUT":
            scores.sprv = self.calculate_sprv(option, stock_price)
            scores.bprv = self.calculate_bprv(option, stock_price)

        if option.put_call == "CALL":
            scores.scrv = self.calculate_scrv(option, stock_price)
            scores.bcrv = self.calculate_bcrv(option, stock_price)

        premium_income, margin_req, annual_return = self.calculate_premium_and_margin(
            option, stock_price, margin_rate
        )
        scores.premium_income = premium_income
        scores.margin_requirement = margin_req
        scores.annualized_return = annual_return

        return scores

    def rank_options_by_strategy(self, options: list, strategy: str) -> list:
        if strategy == "sell_put":
            return sorted(options, key=lambda x: x.scores.sprv or 0, reverse=True)
        elif strategy == "sell_call":
            return sorted(options, key=lambda x: x.scores.scrv or 0, reverse=True)
        elif strategy == "buy_call":
            return sorted(options, key=lambda x: x.scores.bcrv or 0, reverse=True)
        else:
            return options

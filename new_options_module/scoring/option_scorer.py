"""
Option scoring algorithms based on quantitative models

Implements three main scoring formulas:
1. SPRV (Sell Put Recommendation Value) - for selling put options
2. SCRV (Sell Call Recommendation Value) - for selling call options
3. BCRV (Buy Call Recommendation Value) - for buying call options
"""

import math
from datetime import datetime
from typing import Optional
from scipy.stats import norm
from models.option_models import OptionData, OptionScores, ScoringParams

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
        
        New Logic (v2.0):
        - Composite Factor = 40% Spread Score + 60% OI Score
        - Spread Ratio = (Ask - Bid) / MidPrice (proportional to option price)
        - OI is the "gold standard" for liquidity depth, especially during pre-market or low volume periods
        
        Veto Rule:
        - If OI < 10 contracts, return 0.0 (prevent market maker fishing orders)
        
        Returns:
            Standardized score 0.0 - 1.0
        """
        # ========== 一票否决：OI < 10 ==========
        if open_interest is not None and open_interest < 10:
            return 0.0  # Veto: insufficient OI depth
        
        # ========== Spread Score (40% weight) ==========
        spread_score = 0.5  # Default poor liquidity
        if bid_price and ask_price and bid_price > 0 and ask_price > 0:
            mid_price = (bid_price + ask_price) / 2
            if mid_price > 0:
                # Spread Ratio: (Ask - Bid) / MidPrice
                spread_ratio = (ask_price - bid_price) / mid_price
                
                # Score: <1% = 1.0, 1-3% = 0.8-1.0, 3-5% = 0.5-0.8, 5-10% = 0.2-0.5, >10% = 0.0
                if spread_ratio <= 0.01:  # <1%
                    spread_score = 1.0
                elif spread_ratio <= 0.03:  # 1-3%
                    spread_score = 0.8 + (0.03 - spread_ratio) / 0.02 * 0.2  # Linear: 0.8-1.0
                elif spread_ratio <= 0.05:  # 3-5%
                    spread_score = 0.5 + (0.05 - spread_ratio) / 0.02 * 0.3  # Linear: 0.5-0.8
                elif spread_ratio <= 0.10:  # 5-10%
                    spread_score = 0.2 + (0.10 - spread_ratio) / 0.05 * 0.3  # Linear: 0.2-0.5
                else:  # >10%
                    spread_score = 0.0
        
        # ========== OI Score (60% weight) ==========
        oi_score = 0.0  # Default no liquidity
        if open_interest is not None and open_interest >= 10:
            # Score: 10-50 = 0.3-0.6, 50-200 = 0.6-0.8, 200-500 = 0.8-0.95, >500 = 1.0
            if open_interest >= 500:
                oi_score = 1.0
            elif open_interest >= 200:
                oi_score = 0.8 + (open_interest - 200) / 300 * 0.15  # Linear: 0.8-0.95
            elif open_interest >= 50:
                oi_score = 0.6 + (open_interest - 50) / 150 * 0.2  # Linear: 0.6-0.8
            elif open_interest >= 10:
                oi_score = 0.3 + (open_interest - 10) / 40 * 0.3  # Linear: 0.3-0.6
        elif open_interest is None:
            # If OI data is missing, use a conservative default (0.3)
            oi_score = 0.3
        
        # ========== Composite Factor = 40% Spread + 60% OI ==========
        composite_factor = 0.4 * spread_score + 0.6 * oi_score
        
        # Ensure result is in valid range [0.0, 1.0]
        return max(0.0, min(1.0, composite_factor))

    def calculate_iv_rank(self, implied_vol: Optional[float]) -> float:
        """
        Estimate IV Rank (simplified calculation)
        In production, this would use historical IV data
        """
        if not implied_vol:
            return 50.0  # Default moderate IV rank

        # Simple heuristic: assume IV rank based on absolute IV level
        # This is a simplified approximation
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
        """
        Estimate IV Percentile (simplified calculation)
        In production, this would use historical data
        """
        if not implied_vol:
            return 50.0

        # Simple heuristic mapping
        iv_rank = self.calculate_iv_rank(implied_vol)
        return min(99.0, iv_rank + 5.0)  # IVP typically slightly higher than IVR

    def calculate_assignment_probability(self, option: OptionData, stock_price: float) -> Optional[float]:
        """
        Calculate assignment probability using Black-Scholes N(d2) formula

        Formula: P(Assignment) = N(d2) = N((ln(S/K) + (r - σ²/2)T) / (σ√T))

        Where:
        - S: Current stock price
        - K: Strike price
        - r: Risk-free rate
        - σ: Implied volatility
        - T: Time to expiration (in years)
        - N(·): Standard normal cumulative distribution function

        Returns:
            Assignment probability as percentage (0-100%) or None if data insufficient
        """
        # Return None if critical data is missing to avoid misleading users
        if (not option.implied_vol or not option.strike or
            option.implied_vol <= 0 or option.strike <= 0 or stock_price <= 0):
            return None  # Missing data - return None to display "- %"

        # Time to expiration in years
        dte_days = self.calculate_days_to_expiry(option.expiry_date)
        T = dte_days / 365.0

        if T <= 0:
            # For expired options, assignment probability is 100% if ITM, 0% if OTM
            if option.put_call == "PUT":
                return 100.0 if stock_price < option.strike else 0.0
            else:  # CALL
                return 100.0 if stock_price > option.strike else 0.0

        # Black-Scholes parameters
        S = stock_price  # Current stock price
        K = option.strike  # Strike price
        r = self.params.risk_free_rate  # Risk-free rate (5% default)
        sigma = option.implied_vol  # Implied volatility

        # Calculate d2 parameter
        try:
            ln_s_k = math.log(S / K)
            sqrt_t = math.sqrt(T)
            d2 = (ln_s_k + (r - 0.5 * sigma**2) * T) / (sigma * sqrt_t)

            # N(d2) = Standard normal cumulative distribution function
            prob_itm = norm.cdf(d2)

            # For PUT options, we want P(S < K), which is 1 - N(d2)
            # For CALL options, we want P(S > K), which is N(d2)
            if option.put_call == "PUT":
                assignment_prob = (1.0 - prob_itm) * 100.0
            else:  # CALL
                assignment_prob = prob_itm * 100.0

            # Ensure result is within valid range
            return max(0.0, min(100.0, assignment_prob))

        except (ValueError, ZeroDivisionError):
            # Return None for calculation errors to show "- %" instead of misleading data
            return None

    def calculate_sprv(self, option: OptionData, stock_price: float) -> float:
        """
        Calculate Sell Put Recommendation Value (SPRV)

        Formula:
        SPRV = (Premium/(Strike×100) × 365/DTE) × (1-|Delta|)^1.5 × log10(IVR+10) × L_liq

        Components:
        - Annual return factor
        - Win rate weighting (probability of profit)
        - Volatility premium bonus
        - Liquidity adjustment
        """
        if (not option.latest_price or not option.delta or not option.strike or
            option.put_call != "PUT" or option.latest_price <= 0):
            return 0.0

        dte = self.calculate_days_to_expiry(option.expiry_date)
        premium = option.latest_price * 100  # Convert to dollars

        # Annual return factor
        if option.strike <= 0:
            return 0.0
        annual_return = (premium / (option.strike * 100)) * (365 / dte)

        # Win rate weighting: (1 - |Delta|)^1.5
        # Higher for OTM puts (lower absolute delta)
        win_rate_weight = (1 - abs(option.delta)) ** self.params.sprv_delta_power

        # Volatility premium: log10(IVR + 10)
        iv_rank = self.calculate_iv_rank(option.implied_vol)
        volatility_premium = math.log10(iv_rank + self.params.sprv_ivr_base)

        # Liquidity factor (with OI)
        liquidity = self.calculate_liquidity_factor(
            option.bid_price or 0, option.ask_price or 0, 
            option.open_interest, option.latest_price
        )

        sprv = annual_return * win_rate_weight * volatility_premium * liquidity
        return round(sprv, 4)

    def calculate_scrv(self, option: OptionData, stock_price: float) -> float:
        """
        Calculate Sell Call Recommendation Value (SCRV)

        Formula:
        SCRV = (Theta×365/StockPrice) × (1/Delta) × (1+IVP/100) × (Strike-Current)/Current

        Components:
        - Annual theta yield (time decay income)
        - Anti-call-away factor (prefer OTM calls)
        - High volatility reward
        - Upside participation space
        """
        if (not option.latest_price or not option.delta or not option.theta or
            not option.strike or option.put_call != "CALL" or
            option.delta <= 0 or stock_price <= 0):
            return 0.0

        # Annual theta yield: (Theta × 365) / Stock Price
        annual_theta_yield = (abs(option.theta) * 365) / stock_price

        # Anti-call-away factor: 1/Delta (prefer lower delta = OTM calls)
        anti_callback = 1.0 / option.delta

        # High volatility reward: 1 + IVP/100
        iv_percentile = self.calculate_iv_percentile(option.implied_vol)
        volatility_reward = 1.0 + (iv_percentile / 100.0) * self.params.scrv_ivp_weight

        # Upside space: (Strike - Current) / Current
        if option.strike <= stock_price:
            upside_space = 0.01  # Minimal score for ITM calls
        else:
            upside_space = (option.strike - stock_price) / stock_price

        scrv = annual_theta_yield * anti_callback * volatility_reward * upside_space
        return round(scrv, 4)

    def calculate_bcrv(self, option: OptionData, stock_price: float) -> float:
        """
        Calculate Buy Call Recommendation Value (BCRV)

        Formula:
        BCRV = (Gamma/Theta) × (100/(IVR+1)) × Delta² × Vol_score

        Components:
        - Efficiency ratio (gamma potential vs theta cost)
        - Low volatility bonus (buy when IV is cheap)
        - Directional leverage (reward high delta)
        - Volume/liquidity score
        """
        if (not option.latest_price or not option.delta or not option.gamma or
            not option.theta or option.put_call != "CALL" or
            abs(option.theta) <= 0):
            return 0.0

        # Efficiency ratio: Gamma / |Theta|
        efficiency_ratio = option.gamma / abs(option.theta)

        # Low volatility bonus: 100 / (IVR + 1)
        iv_rank = self.calculate_iv_rank(option.implied_vol)
        low_vol_bonus = 100.0 / (iv_rank + 1.0)

        # Directional leverage: Delta²
        directional_leverage = option.delta ** 2

        # Volume score (simplified)
        volume_score = 1.0
        if option.volume and option.volume >= self.params.bcrv_min_volume:
            volume_score = min(2.0, option.volume / self.params.bcrv_min_volume)
        elif option.volume and option.volume < self.params.bcrv_min_volume:
            volume_score = 0.5  # Penalty for low volume

        bcrv = efficiency_ratio * low_vol_bonus * directional_leverage * volume_score
        return round(bcrv, 4)

    def calculate_bprv(self, option: OptionData, stock_price: float) -> float:
        """
        Calculate Buy Put Recommendation Value (BPRV)

        Formula:
        BPRV = (|Delta|/Premium) × VRP_neg × (1-ρ) × Skew_factor

        Components:
        - Hedge leverage (negative delta per dollar premium)
        - Reverse VRP (volatility risk premium)
        - Correlation hedge factor
        - Skew factor
        """
        if (not option.latest_price or not option.delta or
            option.put_call != "PUT" or option.latest_price <= 0):
            return 0.0

        # Hedge leverage: |Delta| / Premium
        premium = option.latest_price
        hedge_leverage = abs(option.delta) / premium

        # Reverse VRP factor (simplified)
        iv_rank = self.calculate_iv_rank(option.implied_vol)
        # We want lower IV rank for puts (buy cheap protection)
        reverse_vrp = max(0.1, (100.0 - iv_rank) / 100.0)

        # Correlation hedge factor (simplified, assume moderate correlation)
        correlation_hedge = 1.0 - self.params.bprv_correlation

        # Skew factor (simplified approximation)
        # Deep OTM puts typically have higher IV, penalize extreme skew
        distance_from_atm = abs(option.strike - stock_price) / stock_price
        skew_factor = max(0.5, 1.0 - distance_from_atm * self.params.bprv_skew_penalty)

        bprv = hedge_leverage * reverse_vrp * correlation_hedge * skew_factor
        return round(bprv, 4)

    def calculate_premium_and_margin(self, option: OptionData, stock_price: float, 
                                    margin_rate: Optional[float] = None) -> tuple:
        """
        Calculate premium income and capital requirement for sell strategies
        
        Improved margin calculation (v2.0):
        - For Sell Put: Uses Reg-T margin rules or custom margin rate from API
        - For Sell Call: Uses Covered Call (stock value) or margin rate if provided
        
        Args:
            option: Option data
            stock_price: Current stock price
            margin_rate: Optional margin rate from API (e.g., 0.20 for 20%)
                        If None, uses standard Reg-T rules for PUT, stock value for CALL
        
        Capital requirements:
        - Sell Put (Naked Put): 
            * If margin_rate provided: Strike × 100 × margin_rate
            * Otherwise: Reg-T = max(20% × Strike × 100 - OTM, 10% × Strike × 100) + Premium
        - Sell Call (Covered Call):
            * If margin_rate provided: Stock Price × 100 × margin_rate
            * Otherwise: Stock Price × 100 (assumes you own the stock)

        Returns:
            tuple: (premium_income, capital_requirement, annualized_return)
        """
        if not option.latest_price or option.latest_price <= 0:
            return 0.0, 0.0, 0.0

        # Premium income (per contract = 100 shares)
        premium_income = option.latest_price * 100

        # Capital requirement calculation (per contract)
        capital_requirement = 0.0

        if option.put_call == "PUT":
            # Sell Put (Naked Put)
            if margin_rate is not None:
                # Use margin rate from API: Strike × 100 × margin_rate
                capital_requirement = option.strike * 100 * margin_rate
            else:
                # Reg-T margin calculation (standard for naked puts)
                # Formula: max(20% × Strike × 100 - OTM, 10% × Strike × 100) + Premium
                # OTM (Out of The Money) = max(0, Strike - StockPrice) × 100
                otm_amount = max(0, (option.strike - stock_price)) * 100
                margin_20pct = 0.20 * option.strike * 100
                margin_10pct = 0.10 * option.strike * 100
                capital_requirement = max(margin_20pct - otm_amount, margin_10pct) + premium_income

        elif option.put_call == "CALL":
            # Sell Call (Covered Call or Naked Call)
            if margin_rate is not None:
                # Use margin rate from API: Stock Price × 100 × margin_rate
                capital_requirement = stock_price * 100 * margin_rate
            else:
                # Covered Call: assumes you own the stock
                # Stock Value = Stock Price × 100
                capital_requirement = stock_price * 100

        # Annualized return calculation
        dte = self.calculate_days_to_expiry(option.expiry_date)
        annualized_return = 0.0
        if capital_requirement > 0 and dte > 0:
            # Calculate return based on premium income vs capital tied up
            return_rate = premium_income / capital_requirement
            annualized_return = (return_rate * 365 / dte) * 100  # Convert to percentage

        return round(premium_income, 2), round(capital_requirement, 2), round(annualized_return, 2)

    def score_option(self, option: OptionData, stock_price: float, 
                     margin_rate: Optional[float] = None) -> OptionScores:
        """
        Calculate all scoring metrics for an option

        Args:
            option: Option data to score
            stock_price: Current underlying stock price
            margin_rate: Optional margin rate from API (e.g., 0.20 for 20%)
                        If None, uses standard Reg-T rules for PUT, stock value for CALL

        Returns:
            OptionScores with all calculated metrics
        """
        scores = OptionScores()

        # Calculate basic metrics
        scores.days_to_expiry = self.calculate_days_to_expiry(option.expiry_date)
        scores.liquidity_factor = self.calculate_liquidity_factor(
            option.bid_price or 0, option.ask_price or 0, 
            option.open_interest, option.latest_price
        )
        scores.iv_rank = self.calculate_iv_rank(option.implied_vol)
        scores.iv_percentile = self.calculate_iv_percentile(option.implied_vol)

        # Calculate assignment probability using Black-Scholes N(d2)
        scores.assignment_probability = self.calculate_assignment_probability(option, stock_price)

        # Calculate strategy-specific scores
        if option.put_call == "PUT":
            scores.sprv = self.calculate_sprv(option, stock_price)
            scores.bprv = self.calculate_bprv(option, stock_price)

        if option.put_call == "CALL":
            scores.scrv = self.calculate_scrv(option, stock_price)
            scores.bcrv = self.calculate_bcrv(option, stock_price)

        # Calculate premium and margin for sell strategies (with margin_rate if available)
        premium_income, margin_req, annual_return = self.calculate_premium_and_margin(
            option, stock_price, margin_rate
        )
        scores.premium_income = premium_income
        scores.margin_requirement = margin_req
        scores.annualized_return = annual_return

        return scores

    def rank_options_by_strategy(self, options: list, strategy: str) -> list:
        """
        Rank options by strategy-specific score

        Args:
            options: List of OptionData with scores calculated
            strategy: 'sell_put', 'sell_call', 'buy_call'

        Returns:
            List of options sorted by score (highest first)
        """
        if strategy == "sell_put":
            return sorted(options, key=lambda x: x.scores.sprv or 0, reverse=True)
        elif strategy == "sell_call":
            return sorted(options, key=lambda x: x.scores.scrv or 0, reverse=True)
        elif strategy == "buy_call":
            return sorted(options, key=lambda x: x.scores.bcrv or 0, reverse=True)
        else:
            return options
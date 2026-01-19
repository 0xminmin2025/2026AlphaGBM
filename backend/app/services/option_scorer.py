"""
Option scoring algorithms based on quantitative models
Ported from new_options_module/scoring/option_scorer.py
"""

import math
from datetime import datetime
from typing import Optional
from scipy.stats import norm
from .option_models import OptionData, OptionScores, ScoringParams, RiskReturnProfile

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
        """
        Calculate Sell Put Recommendation Value (SPRV)
        归一化到 0-100 分，包含 Theta 权重和 Gamma 风险惩罚
        """
        if (not option.latest_price or not option.delta or not option.strike or
            option.put_call != "PUT" or option.latest_price <= 0 or stock_price <= 0):
            return 0.0

        # ========== 合理性检查：只考虑虚值或平值看跌期权 ==========
        if option.strike > stock_price * 1.02:  # 实值期权，不适合sell put
            return 0.0

        # 深度虚值期权惩罚
        moneyness_ratio = option.strike / stock_price if stock_price > 0 else 0
        if moneyness_ratio < 0.7:
            depth_penalty = moneyness_ratio / 0.7
        elif moneyness_ratio < 0.85:
            depth_penalty = 0.6 + (moneyness_ratio - 0.7) / 0.15 * 0.3
        elif moneyness_ratio < 0.95:
            depth_penalty = 0.9 + (moneyness_ratio - 0.85) / 0.1 * 0.1
        else:
            depth_penalty = 1.0

        dte = self.calculate_days_to_expiry(option.expiry_date)
        if dte <= 0:
            return 0.0

        if option.strike <= 0:
            return 0.0

        # ========== 1. 收益率得分 (30分满分) ==========
        premium = option.latest_price * 100
        annual_return = (premium / (option.strike * 100)) * (365 / dte)
        # 年化收益 0-50% 映射到 0-30 分
        return_score = min(30, annual_return / 0.50 * 30)

        # ========== 2. 胜率得分 (25分满分) ==========
        win_rate = 1 - abs(option.delta)  # delta 越小，胜率越高
        win_rate_score = win_rate * 25

        # ========== 3. 波动率溢价得分 (15分满分) ==========
        iv_rank = self.calculate_iv_rank(option.implied_vol)
        # IV Rank 50-100 是理想范围，映射到 0-15 分
        iv_score = min(15, max(0, (iv_rank - 30) / 70 * 15))

        # ========== 4. 流动性得分 (15分满分) ==========
        liquidity = self.calculate_liquidity_factor(
            option.bid_price or 0, option.ask_price or 0,
            option.open_interest, option.latest_price
        )
        liquidity_score = liquidity * 15

        # ========== 5. Theta 时间衰减得分 (10分满分) ==========
        # Sell Put 受益于时间衰减，Theta 越负（绝对值越大），对卖方越有利
        theta = option.theta or 0
        theta_abs = abs(theta)
        # Theta 绝对值 0.01-0.10 映射到 0-10 分
        theta_score = min(10, theta_abs / 0.10 * 10)

        # ========== 6. Gamma 风险惩罚 (最多扣 5 分) ==========
        # Gamma 越大，价格变动风险越大，对卖方不利
        gamma = option.gamma or 0
        # Gamma > 0.05 开始惩罚，0.10 以上扣满 5 分
        gamma_penalty = min(5, max(0, (gamma - 0.02) / 0.08 * 5))

        # ========== 综合评分 ==========
        raw_score = return_score + win_rate_score + iv_score + liquidity_score + theta_score - gamma_penalty

        # 应用深度虚值惩罚
        final_score = raw_score * depth_penalty

        return round(max(0, min(100, final_score)), 2)

    def calculate_scrv(self, option: OptionData, stock_price: float) -> float:
        """
        Calculate Sell Call Recommendation Value (SCRV)
        归一化到 0-100 分，包含 Theta 权重和 Gamma 风险惩罚
        """
        if (not option.latest_price or not option.delta or not option.theta or
            not option.strike or option.put_call != "CALL" or
            option.delta <= 0 or stock_price <= 0):
            return 0.0

        # ========== 合理性检查：只考虑虚值或平值看涨期权 ==========
        if option.strike < stock_price * 0.98:  # 实值期权，不适合sell call
            return 0.0

        # 深度虚值期权惩罚
        moneyness_ratio = option.strike / stock_price if stock_price > 0 else 0
        if moneyness_ratio > 1.3:
            depth_penalty = 1.3 / moneyness_ratio
        elif moneyness_ratio > 1.15:
            depth_penalty = 0.6 + (1.3 - moneyness_ratio) / 0.15 * 0.3
        elif moneyness_ratio > 1.05:
            depth_penalty = 0.9 + (1.15 - moneyness_ratio) / 0.1 * 0.1
        else:
            depth_penalty = 1.0

        dte = self.calculate_days_to_expiry(option.expiry_date)
        if dte <= 0:
            return 0.0

        # ========== 1. 收益率得分 (30分满分) ==========
        premium = option.latest_price * 100
        annual_return = (premium / (stock_price * 100)) * (365 / dte)
        return_score = min(30, annual_return / 0.50 * 30)

        # ========== 2. 胜率得分 (25分满分) ==========
        # 对于 Sell Call，1-delta 是不被行权的概率
        win_rate = 1 - option.delta
        win_rate_score = win_rate * 25

        # ========== 3. 波动率溢价得分 (15分满分) ==========
        iv_percentile = self.calculate_iv_percentile(option.implied_vol)
        iv_score = min(15, max(0, (iv_percentile - 30) / 70 * 15))

        # ========== 4. 流动性得分 (15分满分) ==========
        liquidity = self.calculate_liquidity_factor(
            option.bid_price or 0, option.ask_price or 0,
            option.open_interest, option.latest_price
        )
        liquidity_score = liquidity * 15

        # ========== 5. Theta 时间衰减得分 (10分满分) ==========
        theta_abs = abs(option.theta)
        theta_score = min(10, theta_abs / 0.10 * 10)

        # ========== 6. Gamma 风险惩罚 (最多扣 5 分) ==========
        gamma = option.gamma or 0
        gamma_penalty = min(5, max(0, (gamma - 0.02) / 0.08 * 5))

        # ========== 7. 上涨空间加分 (最多 5 分) ==========
        # 执行价越高于当前价，被行权风险越低
        upside_space = (option.strike - stock_price) / stock_price if option.strike > stock_price else 0
        upside_bonus = min(5, upside_space / 0.15 * 5)

        # ========== 综合评分 ==========
        raw_score = return_score + win_rate_score + iv_score + liquidity_score + theta_score + upside_bonus - gamma_penalty

        # 应用深度虚值惩罚
        final_score = raw_score * depth_penalty

        return round(max(0, min(100, final_score)), 2)

    def calculate_bcrv(self, option: OptionData, stock_price: float) -> float:
        """
        Calculate Buy Call Recommendation Value (BCRV)
        归一化到 0-100 分，包含 Theta 权重和 Gamma 优势
        """
        if (not option.latest_price or not option.delta or not option.gamma or
            not option.theta or option.put_call != "CALL" or
            abs(option.theta) <= 0 or stock_price <= 0):
            return 0.0

        # ========== 合理性检查：深度实值期权成本太高 ==========
        if option.strike < stock_price * 0.8:
            return 0.0

        # ========== 1. Delta 方向性得分 (30分满分) ==========
        # Delta 越高，方向性杠杆越大
        delta_score = option.delta * 30

        # ========== 2. Gamma/Theta 效率得分 (25分满分) ==========
        # 对于买方，Gamma 高且 Theta 低是好的
        efficiency_ratio = option.gamma / abs(option.theta) if abs(option.theta) > 0.001 else 0
        # 效率比 0-2 映射到 0-25 分
        efficiency_score = min(25, efficiency_ratio / 2.0 * 25)

        # ========== 3. 低波动率加分 (15分满分) ==========
        # 买方希望 IV 低（便宜）
        iv_rank = self.calculate_iv_rank(option.implied_vol)
        # IV Rank 0-50 是理想范围
        low_iv_score = max(0, (60 - iv_rank) / 60 * 15)

        # ========== 4. 流动性得分 (15分满分) ==========
        liquidity = self.calculate_liquidity_factor(
            option.bid_price or 0, option.ask_price or 0,
            option.open_interest, option.latest_price
        )
        liquidity_score = liquidity * 15

        # ========== 5. Theta 时间衰减惩罚 (最多扣 10 分) ==========
        # 买方受 Theta 损害，Theta 越负（绝对值越大），对买方越不利
        theta_abs = abs(option.theta)
        theta_penalty = min(10, theta_abs / 0.15 * 10)

        # ========== 6. Gamma 杠杆加分 (最多 5 分) ==========
        # 对于买方，高 Gamma 意味着更大的上涨潜力
        gamma = option.gamma or 0
        gamma_bonus = min(5, gamma / 0.10 * 5)

        # ========== 综合评分 ==========
        raw_score = delta_score + efficiency_score + low_iv_score + liquidity_score + gamma_bonus - theta_penalty

        return round(max(0, min(100, raw_score)), 2)

    def calculate_bprv(self, option: OptionData, stock_price: float) -> float:
        """
        Calculate Buy Put Recommendation Value (BPRV)
        归一化到 0-100 分，包含 Theta 权重和 Gamma 优势
        """
        if (not option.latest_price or not option.delta or
            option.put_call != "PUT" or option.latest_price <= 0 or stock_price <= 0):
            return 0.0

        # ========== 合理性检查：深度实值期权成本太高 ==========
        if option.strike > stock_price * 1.2:
            return 0.0

        # ========== 1. Delta 对冲杠杆得分 (30分满分) ==========
        # |Delta| 越高，对冲效果越好
        delta_abs = abs(option.delta)
        delta_score = delta_abs * 30

        # ========== 2. 性价比得分 (25分满分) ==========
        # Delta/Premium 比值，衡量对冲的性价比
        premium = option.latest_price
        hedge_efficiency = delta_abs / premium if premium > 0 else 0
        # 效率 0-1 映射到 0-25 分
        efficiency_score = min(25, hedge_efficiency / 1.0 * 25)

        # ========== 3. 低波动率加分 (15分满分) ==========
        # 买方希望 IV 低（便宜）
        iv_rank = self.calculate_iv_rank(option.implied_vol)
        low_iv_score = max(0, (60 - iv_rank) / 60 * 15)

        # ========== 4. 流动性得分 (15分满分) ==========
        liquidity = self.calculate_liquidity_factor(
            option.bid_price or 0, option.ask_price or 0,
            option.open_interest, option.latest_price
        )
        liquidity_score = liquidity * 15

        # ========== 5. Theta 时间衰减惩罚 (最多扣 10 分) ==========
        theta = option.theta or 0
        theta_abs = abs(theta)
        theta_penalty = min(10, theta_abs / 0.15 * 10)

        # ========== 6. Gamma 杠杆加分 (最多 5 分) ==========
        gamma = option.gamma or 0
        gamma_bonus = min(5, gamma / 0.10 * 5)

        # ========== 7. 距离 ATM 惩罚 (最多扣 5 分) ==========
        # 太深的虚值期权对冲效果差
        distance_from_atm = abs(option.strike - stock_price) / stock_price
        distance_penalty = min(5, distance_from_atm / 0.20 * 5)

        # ========== 综合评分 ==========
        raw_score = delta_score + efficiency_score + low_iv_score + liquidity_score + gamma_bonus - theta_penalty - distance_penalty

        return round(max(0, min(100, raw_score)), 2)

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

        # 计算风险收益风格标签
        scores.risk_return_profile = self.calculate_risk_return_profile(option, stock_price)

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

    def calculate_risk_return_profile(self, option: OptionData, stock_price: float) -> Optional[RiskReturnProfile]:
        """
        计算期权的风险收益风格标签

        Args:
            option: 期权数据
            stock_price: 股票当前价格

        Returns:
            RiskReturnProfile: 风险收益风格标签
        """
        if not option.strike or stock_price <= 0:
            return None

        try:
            dte = self.calculate_days_to_expiry(option.expiry_date)
            mid_price = ((option.bid_price or 0) + (option.ask_price or 0)) / 2
            if mid_price <= 0:
                mid_price = option.latest_price or 0
            if mid_price <= 0:
                return None

            implied_vol = option.implied_vol or 0.25

            if option.put_call == "PUT":
                # 计算 Sell Put 的风格标签
                return self._calculate_sell_put_profile(
                    option.strike, mid_price, stock_price, dte, implied_vol
                )
            else:  # CALL
                # 计算 Sell Call 的风格标签
                return self._calculate_sell_call_profile(
                    option.strike, mid_price, stock_price, dte, implied_vol
                )
        except Exception:
            return None

    def _calculate_sell_put_profile(
        self, strike: float, premium: float, current_price: float,
        days_to_expiry: int, implied_vol: float
    ) -> RiskReturnProfile:
        """计算 Sell Put 策略的风格标签"""
        # 计算关键指标
        safety_margin_pct = (current_price - strike) / current_price * 100
        max_profit_pct = (premium / strike) * 100
        max_loss_pct = ((strike - premium) / strike) * 100
        annualized_return = (max_profit_pct / days_to_expiry) * 365 if days_to_expiry > 0 else 0

        # 胜率估算
        base_win_prob = self._estimate_win_probability(
            current_price, strike, implied_vol, days_to_expiry, is_put=True, is_sell=True
        )

        # 风格判定 (基于安全边际和年化收益)
        # steady_income: 深度OTM，高安全边际(>=8%)，低收益
        # balanced: 中度OTM，中等安全边际(3-8%)
        # high_risk_high_reward: 接近ATM或ITM，高收益高风险
        if safety_margin_pct >= 8:
            style = 'steady_income'
            style_label = '稳健收益 / STEADY INCOME'
            style_label_cn = '稳健收益'
            style_label_en = 'STEADY INCOME'
            risk_level = 'low'
            risk_color = 'green'
        elif safety_margin_pct >= 3:
            style = 'balanced'
            style_label = '稳中求进 / BALANCED'
            style_label_cn = '稳中求进'
            style_label_en = 'BALANCED'
            risk_level = 'moderate'
            risk_color = 'yellow'
        else:
            # 安全边际 < 3%，包括 ATM 和 ITM
            style = 'high_risk_high_reward'
            style_label = '高风险高收益 / HIGH RISK HIGH REWARD'
            style_label_cn = '高风险高收益'
            style_label_en = 'HIGH RISK HIGH REWARD'
            risk_level = 'high' if safety_margin_pct >= 0 else 'very_high'
            risk_color = 'orange' if safety_margin_pct >= 0 else 'red'

        risk_reward_ratio = max_profit_pct / max_loss_pct if max_loss_pct > 0 else 0

        # 生成摘要
        if style == 'steady_income':
            summary_cn = f"胜率{base_win_prob:.0%}，月收益约{max_profit_pct:.1f}%，安全边际{safety_margin_pct:.1f}%"
        elif style == 'high_risk_high_reward':
            summary_cn = f"胜率{base_win_prob:.0%}，收益{max_profit_pct:.1f}%，安全边际仅{safety_margin_pct:.1f}%"
        else:
            summary_cn = f"胜率{base_win_prob:.0%}，收益{max_profit_pct:.1f}%，风险收益均衡"

        return RiskReturnProfile(
            style=style,
            style_label=style_label,
            style_label_cn=style_label_cn,
            style_label_en=style_label_en,
            risk_level=risk_level,
            risk_color=risk_color,
            max_loss_pct=round(max_loss_pct, 2),
            max_profit_pct=round(max_profit_pct, 2),
            win_probability=round(base_win_prob, 2),
            risk_reward_ratio=round(risk_reward_ratio, 3),
            summary=summary_cn,
            summary_cn=summary_cn,
            strategy_type='seller',
            time_decay_impact='positive',
            volatility_impact='negative'
        )

    def _calculate_sell_call_profile(
        self, strike: float, premium: float, current_price: float,
        days_to_expiry: int, implied_vol: float
    ) -> RiskReturnProfile:
        """计算 Sell Call 策略的风格标签"""
        # 计算关键指标
        distance_pct = (strike - current_price) / current_price * 100
        max_profit_pct = (premium / current_price) * 100
        max_loss_pct = 100  # 理论上无限
        annualized_return = (max_profit_pct / days_to_expiry) * 365 if days_to_expiry > 0 else 0

        # 胜率估算
        base_win_prob = self._estimate_win_probability(
            current_price, strike, implied_vol, days_to_expiry, is_put=False, is_sell=True
        )

        # 风格判定 (基于虚值程度)
        # steady_income: 深度OTM (>=10%)，高安全边际
        # balanced: 中度OTM (3-10%)
        # high_risk_high_reward: 接近ATM或ITM (<3%)
        if distance_pct >= 10:
            style = 'steady_income'
            style_label = '稳健收益 / STEADY INCOME'
            style_label_cn = '稳健收益'
            style_label_en = 'STEADY INCOME'
            risk_level = 'low'
            risk_color = 'green'
        elif distance_pct >= 3:
            style = 'balanced'
            style_label = '稳中求进 / BALANCED'
            style_label_cn = '稳中求进'
            style_label_en = 'BALANCED'
            risk_level = 'moderate'
            risk_color = 'yellow'
        else:
            # 虚值程度 < 3%，接近ATM或ITM
            style = 'high_risk_high_reward'
            style_label = '高风险高收益 / HIGH RISK HIGH REWARD'
            style_label_cn = '高风险高收益'
            style_label_en = 'HIGH RISK HIGH REWARD'
            risk_level = 'high'
            risk_color = 'orange'

        risk_reward_ratio = max_profit_pct / max_loss_pct if max_loss_pct > 0 else 0
        summary_cn = f"胜率约{base_win_prob:.0%}，年化收益{annualized_return:.0f}%，虚值{distance_pct:.1f}%"

        return RiskReturnProfile(
            style=style,
            style_label=style_label,
            style_label_cn=style_label_cn,
            style_label_en=style_label_en,
            risk_level=risk_level,
            risk_color=risk_color,
            max_loss_pct=round(max_loss_pct, 2),
            max_profit_pct=round(max_profit_pct, 2),
            win_probability=round(base_win_prob, 2),
            risk_reward_ratio=round(risk_reward_ratio, 3),
            summary=summary_cn,
            summary_cn=summary_cn,
            strategy_type='seller',
            time_decay_impact='positive',
            volatility_impact='negative'
        )

    def _estimate_win_probability(
        self, current_price: float, strike: float, implied_vol: float,
        days_to_expiry: int, is_put: bool = True, is_sell: bool = True
    ) -> float:
        """
        估算胜率 - 使用 Black-Scholes N(d2) 公式

        N(d2) 是到期时股价高于执行价的风险中性概率
        - Sell Put 胜率 = P(S_T > K) = N(d2)
        - Sell Call 胜率 = P(S_T < K) = N(-d2)
        - Buy Put 胜率 = P(S_T < K) = N(-d2)
        - Buy Call 胜率 = P(S_T > K) = N(d2)
        """
        try:
            if implied_vol <= 0 or days_to_expiry <= 0:
                return 0.55

            t = days_to_expiry / 365
            r = 0.05  # 无风险利率
            sqrt_t = math.sqrt(t)

            # 计算 d1 和 d2
            d1 = (math.log(current_price / strike) + (r + 0.5 * implied_vol ** 2) * t) / (implied_vol * sqrt_t)
            d2 = d1 - implied_vol * sqrt_t  # d2 = d1 - σ√t

            if is_put:
                if is_sell:
                    # Sell Put 胜率: 股价到期高于执行价的概率 = N(d2)
                    prob = norm.cdf(d2)
                else:
                    # Buy Put 胜率: 股价到期低于执行价的概率 = N(-d2)
                    prob = norm.cdf(-d2)
            else:
                if is_sell:
                    # Sell Call 胜率: 股价到期低于执行价的概率 = N(-d2)
                    prob = norm.cdf(-d2)
                else:
                    # Buy Call 胜率: 股价到期高于执行价的概率 = N(d2)
                    prob = norm.cdf(d2)

            return min(0.95, max(0.15, prob))

        except Exception:
            # 简化计算
            if is_put:
                distance_pct = (current_price - strike) / current_price * 100
                if is_sell:
                    if distance_pct >= 15: return 0.85
                    elif distance_pct >= 10: return 0.78
                    elif distance_pct >= 5: return 0.70
                    elif distance_pct >= 0: return 0.60
                    else: return max(0.35, 0.60 + distance_pct * 0.02)
            else:
                distance_pct = (strike - current_price) / current_price * 100
                if is_sell:
                    if distance_pct >= 15: return 0.80
                    elif distance_pct >= 10: return 0.72
                    elif distance_pct >= 5: return 0.62
                    elif distance_pct >= 0: return 0.50
                    else: return max(0.30, 0.50 + distance_pct * 0.02)
            return 0.50

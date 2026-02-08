"""
Sell Put 期权策略计分器
实现卖出看跌期权的专门计分算法

优化版本（基于真实交易者反馈）：
- 趋势过滤：Sell Put 只在下跌时做（显示但降分）
- ATR动态安全边际：不同股票波动不同
- 支撑位强度评估：执行价是否为真实支撑位
"""

import logging
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from .trend_analyzer import TrendAnalyzer, ATRCalculator
from ..option_market_config import OptionMarketConfig, US_OPTIONS_CONFIG

logger = logging.getLogger(__name__)


class SellPutScorer:
    """卖出看跌期权计分器"""

    def __init__(self):
        """初始化Sell Put计分器"""
        self.strategy_name = "sell_put"

        # 优化后的权重配置（基于真实交易者反馈）
        self.weight_config = {
            'premium_yield': 0.20,       # 期权费收益率 (降低，避免追求高收益)
            'safety_margin': 0.15,       # 安全边际 (改用ATR自适应)
            'support_strength': 0.20,    # 新增：支撑位强度
            'trend_alignment': 0.15,     # 新增：趋势匹配度
            'probability_profit': 0.15,  # 盈利概率
            'liquidity': 0.10,           # 流动性
            'time_decay': 0.05,          # 时间衰减
        }

        # 初始化趋势分析器和ATR计算器
        self.trend_analyzer = TrendAnalyzer()
        self.atr_calculator = ATRCalculator()

    def score_options(self, options_data: Dict, stock_data: Dict,
                      market_config: OptionMarketConfig = None) -> Dict[str, Any]:
        """
        为Sell Put策略计分期权

        Args:
            options_data: 期权链数据
            stock_data: 标的股票数据
            market_config: 市场配置（可选，默认 US）

        Returns:
            计分结果
        """
        try:
            if market_config is None:
                market_config = US_OPTIONS_CONFIG

            logger.info(f"开始Sell Put策略计分: {options_data.get('symbol', 'Unknown')} (市场: {market_config.market})")

            if not options_data.get('success'):
                return {
                    'success': False,
                    'strategy': self.strategy_name,
                    'error': '期权数据无效'
                }

            puts = options_data.get('puts', [])
            if not puts:
                return {
                    'success': False,
                    'strategy': self.strategy_name,
                    'error': '无看跌期权数据'
                }

            current_price = stock_data.get('current_price', 0)
            if not current_price:
                return {
                    'success': False,
                    'strategy': self.strategy_name,
                    'error': '无法获取当前股价'
                }

            # 新增：趋势分析（基于当天趋势）
            trend_info = self._analyze_trend(stock_data, current_price)

            # 新增：计算ATR用于动态安全边际
            atr_14 = self._get_atr(stock_data, market_config)

            # 筛选和计分期权
            scored_options = []
            for put_option in puts:
                score_result = self._score_individual_put(
                    put_option, current_price, stock_data, trend_info, atr_14,
                    market_config=market_config
                )
                if score_result and score_result.get('score', 0) > 0:
                    scored_options.append(score_result)

            # 排序并选择最佳期权
            scored_options.sort(key=lambda x: x.get('score', 0), reverse=True)

            # 生成策略分析
            strategy_analysis = self._generate_strategy_analysis(
                scored_options, current_price, stock_data, trend_info
            )

            return {
                'success': True,
                'strategy': self.strategy_name,
                'symbol': options_data.get('symbol'),
                'current_price': current_price,
                'analysis_time': datetime.now().isoformat(),
                'total_options_analyzed': len(puts),
                'qualified_options': len(scored_options),
                'recommendations': scored_options[:10],  # 返回前10个
                'strategy_analysis': strategy_analysis,
                'scoring_weights': self.weight_config,
                # 新增：趋势信息
                'trend_info': trend_info,
                'atr_14': atr_14,
            }

        except Exception as e:
            logger.error(f"Sell Put计分失败: {e}")
            return {
                'success': False,
                'strategy': self.strategy_name,
                'error': f"计分失败: {str(e)}"
            }

    def _analyze_trend(self, stock_data: Dict, current_price: float) -> Dict[str, Any]:
        """分析当前趋势"""
        try:
            # 从stock_data获取价格历史
            price_history = stock_data.get('price_history', [])
            if isinstance(price_history, list) and len(price_history) >= 6:
                price_series = pd.Series(price_history)
            else:
                # 如果没有历史数据，尝试从其他字段构建
                price_series = pd.Series([current_price] * 7)

            return self.trend_analyzer.analyze_trend_for_strategy(
                price_series, current_price, 'sell_put'
            )
        except Exception as e:
            logger.error(f"趋势分析失败: {e}")
            return {
                'trend': 'sideways',
                'trend_strength': 0.5,
                'trend_alignment_score': 60,
                'display_info': {
                    'trend_name_cn': '横盘整理',
                    'is_ideal_trend': False,
                    'warning': '无法确定趋势'
                }
            }

    def _get_atr(self, stock_data: Dict, market_config: OptionMarketConfig = None) -> float:
        """获取或计算ATR"""
        if market_config is None:
            market_config = US_OPTIONS_CONFIG
        trading_days = market_config.trading_days_per_year

        # 优先使用已计算的ATR
        atr = stock_data.get('atr_14', 0)
        if atr > 0:
            return atr

        # 尝试从OHLC数据计算
        try:
            high = stock_data.get('high_prices', [])
            low = stock_data.get('low_prices', [])
            close = stock_data.get('close_prices', stock_data.get('price_history', []))

            if high and low and close:
                return self.atr_calculator.calculate_atr(
                    pd.Series(high), pd.Series(low), pd.Series(close)
                )
        except Exception as e:
            logger.warning(f"ATR计算失败: {e}")

        # 备用：使用波动率估算
        vol_30d = stock_data.get('volatility_30d', 0.25)
        current_price = stock_data.get('current_price', 100)
        return current_price * vol_30d / np.sqrt(trading_days)

    def _score_individual_put(self, put_option: Dict, current_price: float,
                             stock_data: Dict, trend_info: Dict = None,
                             atr_14: float = 0,
                             market_config: OptionMarketConfig = None) -> Optional[Dict]:
        """计分单个看跌期权（优化版本：含趋势和ATR评分）"""
        try:
            if market_config is None:
                market_config = US_OPTIONS_CONFIG
            multiplier = market_config.get_multiplier(
                stock_data.get('symbol', '') if isinstance(stock_data, dict) else ''
            )
            trading_days = market_config.trading_days_per_year

            strike = put_option.get('strike', 0)
            bid = put_option.get('bid', 0)
            ask = put_option.get('ask', 0)
            volume = put_option.get('volume', 0)
            open_interest = put_option.get('open_interest', 0)
            implied_volatility = put_option.get('implied_volatility', 0)
            days_to_expiry = put_option.get('days_to_expiry', 0)

            if not all([strike, bid > 0, days_to_expiry > 0]):
                return None

            # 只考虑虚值或平值看跌期权（适合卖出）
            # PUT期权：行权价 < 当前股价 才是虚值(OTM)，才适合卖出
            if strike > current_price * 1.02:  # 实值超过2%，跳过
                return None

            # 基础计分指标
            mid_price = (bid + ask) / 2

            # 对于 Sell Put，只计算时间价值部分的收益（不含内在价值）
            intrinsic_value = max(0, strike - current_price)
            time_value = max(0, mid_price - intrinsic_value)

            if time_value <= 0:
                return None  # 没有时间价值的期权不适合卖出

            # 单次收益率 = 时间价值 / 被指派后的持仓成本(行权价)
            premium_yield = (time_value / strike) * 100
            safety_margin = ((current_price - strike) / current_price) * 100  # 安全边际%

            # 年化收益率计算
            annualized_return = (premium_yield / days_to_expiry) * trading_days

            # 计算各项得分
            scores = {}

            # 1. 期权费收益率得分 (20%)
            scores['premium_yield'] = self._score_premium_yield(premium_yield, days_to_expiry)

            # 2. 安全边际得分 - 使用ATR动态计算 (15%)
            atr_safety = self._calculate_atr_safety(current_price, strike, atr_14)
            scores['safety_margin'] = self._score_safety_margin_with_atr(
                safety_margin, atr_safety
            )

            # 3. 新增：支撑位强度评分 (20%)
            scores['support_strength'] = self._score_support_strength(
                strike, current_price, stock_data
            )

            # 4. 新增：趋势匹配度评分 (15%)
            if trend_info:
                scores['trend_alignment'] = trend_info.get('trend_alignment_score', 60)
            else:
                scores['trend_alignment'] = 60

            # 5. 盈利概率得分 (15%)
            scores['probability_profit'] = self._score_profit_probability(
                current_price, strike, implied_volatility, days_to_expiry,
                risk_free_rate=market_config.risk_free_rate
            )

            # 6. 流动性得分 (10%)
            scores['liquidity'] = self._score_liquidity(volume, open_interest, bid, ask)

            # 7. 时间衰减得分 (5%)
            scores['time_decay'] = self._score_time_decay(days_to_expiry)

            # 计算加权总分
            total_score = sum(
                scores[factor] * self.weight_config.get(factor, 0)
                for factor in scores.keys()
            )

            # 商品期权：交割月风险惩罚
            delivery_risk_data = None
            if market_config and market_config.market == 'COMMODITY':
                contract_code = put_option.get('contract') or put_option.get('expiry', '')
                if contract_code:
                    from ..advanced.delivery_risk import DeliveryRiskCalculator
                    delivery_risk_data = DeliveryRiskCalculator().assess(contract_code)
                    total_score *= (1.0 - delivery_risk_data.delivery_penalty)

            # 构建趋势警告信息
            trend_warning = None
            if trend_info and trend_info.get('display_info'):
                display = trend_info['display_info']
                if not display.get('is_ideal_trend'):
                    trend_warning = display.get('warning')

            result = {
                'option_symbol': put_option.get('symbol', f"PUT_{strike}_{put_option.get('expiry')}"),
                'strike': strike,
                'expiry': put_option.get('expiry'),
                'days_to_expiry': days_to_expiry,
                'bid': bid,
                'ask': ask,
                'mid_price': round(mid_price, 2),
                'time_value': round(time_value, 2),
                'intrinsic_value': round(intrinsic_value, 2),
                'premium_yield': round(premium_yield, 2),
                'annualized_return': round(annualized_return, 2),
                'is_short_term': days_to_expiry <= 7,
                'safety_margin': round(safety_margin, 2),
                'implied_volatility': round(implied_volatility * 100, 1),
                'volume': volume,
                'open_interest': open_interest,
                'score': round(total_score, 1),
                'score_breakdown': {k: round(v, 1) for k, v in scores.items()},
                'assignment_risk': self._calculate_assignment_risk(current_price, strike),
                'max_profit': round(time_value * multiplier, 0),
                'breakeven': round(strike - mid_price, 2),
                'strategy_notes': self._generate_put_notes(current_price, strike, premium_yield, days_to_expiry),
                # 新增：ATR安全边际信息
                'atr_safety': atr_safety,
                # 新增：趋势信息
                'trend_warning': trend_warning,
                'is_ideal_trend': trend_info.get('is_ideal_trend', True) if trend_info else True,
            }

            if delivery_risk_data:
                result['delivery_risk'] = delivery_risk_data.to_dict()

            return result

        except Exception as e:
            logger.error(f"单个期权计分失败: {e}")
            return None

    def _calculate_atr_safety(self, current_price: float, strike: float,
                             atr_14: float) -> Dict[str, Any]:
        """计算基于ATR的安全边际"""
        if atr_14 <= 0:
            return {
                'safety_ratio': 0,
                'atr_multiples': 0,
                'is_safe': False
            }
        return self.atr_calculator.calculate_atr_based_safety(
            current_price, strike, atr_14, atr_ratio=2.0
        )

    def _score_safety_margin_with_atr(self, safety_margin: float,
                                      atr_safety: Dict) -> float:
        """结合ATR的安全边际评分"""
        # 原始安全边际评分
        base_score = self._score_safety_margin(safety_margin)

        # ATR调整
        safety_ratio = atr_safety.get('safety_ratio', 0)
        atr_multiples = atr_safety.get('atr_multiples', 0)

        if safety_ratio >= 1.5:  # 1.5倍以上需求缓冲
            atr_bonus = 15
        elif safety_ratio >= 1.0:  # 刚好满足
            atr_bonus = 5
        elif safety_ratio >= 0.5:  # 不足
            atr_bonus = -10
        else:  # 严重不足
            atr_bonus = -20

        return min(100, max(0, base_score + atr_bonus))

    def _score_support_strength(self, strike: float, current_price: float,
                                stock_data: Dict) -> float:
        """评分执行价作为支撑位的强度"""
        try:
            support_resistance = stock_data.get('support_resistance', {})

            # 获取支撑位
            support_1 = support_resistance.get('support_1', 0)
            support_2 = support_resistance.get('support_2', 0)
            low_52w = support_resistance.get('low_52w', 0)

            # MA支撑
            ma_50 = stock_data.get('ma_50', 0)
            ma_200 = stock_data.get('ma_200', 0)

            scores = []

            # 检查执行价是否接近各支撑位
            support_levels = [
                (support_1, 25, 'S1'),
                (support_2, 20, 'S2'),
                (ma_50, 20, 'MA50'),
                (ma_200, 25, 'MA200'),
                (low_52w, 10, '52W Low'),
            ]

            for level, max_score, name in support_levels:
                if level and level > 0:
                    # 执行价与支撑位的距离（百分比）
                    diff_pct = abs(strike - level) / current_price * 100
                    if diff_pct <= 1:  # 1%以内
                        scores.append(max_score)
                    elif diff_pct <= 3:  # 3%以内
                        scores.append(max_score * 0.7)
                    elif diff_pct <= 5:  # 5%以内
                        scores.append(max_score * 0.4)

            # 如果没有匹配的支撑位，给基础分
            if not scores:
                # 基于安全边际给分
                safety_pct = (current_price - strike) / current_price * 100
                if safety_pct >= 10:
                    return 60
                elif safety_pct >= 5:
                    return 40
                else:
                    return 20

            return min(100, sum(scores))

        except Exception as e:
            logger.error(f"支撑位评分失败: {e}")
            return 50

    def _score_premium_yield(self, premium_yield: float, days_to_expiry: int) -> float:
        """计分期权费收益率"""
        # 年化收益率计算
        annualized_yield = (premium_yield / days_to_expiry) * 365

        # 得分标准
        if annualized_yield >= 20:
            return 100
        elif annualized_yield >= 15:
            return 80 + (annualized_yield - 15) * 4
        elif annualized_yield >= 10:
            return 60 + (annualized_yield - 10) * 4
        elif annualized_yield >= 5:
            return 40 + (annualized_yield - 5) * 4
        else:
            return max(0, annualized_yield * 8)

    def _score_safety_margin(self, safety_margin: float) -> float:
        """计分安全边际"""
        # 正值表示虚值，安全性高
        if safety_margin >= 10:
            return 100
        elif safety_margin >= 5:
            return 80 + (safety_margin - 5) * 4
        elif safety_margin >= 0:
            return 50 + safety_margin * 6
        else:
            # 实值期权，风险较高
            return max(0, 50 + safety_margin * 2)

    def _score_profit_probability(self, current_price: float, strike: float,
                                 implied_vol: float, days_to_expiry: int,
                                 risk_free_rate: float = 0.05) -> float:
        """计分盈利概率（期权到期时价值为0的概率）"""
        try:
            # 使用布莱克-肖尔斯模型估算概率
            from scipy.stats import norm
            import math

            if implied_vol <= 0 or days_to_expiry <= 0:
                return 50

            # 计算期权到期时股价低于执行价的概率
            t = days_to_expiry / 365
            d1 = (math.log(current_price / strike) + (risk_free_rate + 0.5 * implied_vol ** 2) * t) / (implied_vol * math.sqrt(t))
            prob_below_strike = norm.cdf(-d1)

            # 转换为得分
            return min(100, prob_below_strike * 100)

        except:
            # 简化计算
            distance_pct = (current_price - strike) / current_price * 100
            if distance_pct >= 15:
                return 95
            elif distance_pct >= 10:
                return 85
            elif distance_pct >= 5:
                return 70
            elif distance_pct >= 0:
                return 55
            else:
                return max(20, 55 + distance_pct * 2)

    def _score_liquidity(self, volume: int, open_interest: int, bid: float, ask: float) -> float:
        """计分流动性"""
        if bid <= 0 or ask <= 0:
            return 0

        bid_ask_spread_pct = (ask - bid) / ((ask + bid) / 2) * 100

        # 成交量得分
        volume_score = min(50, volume / 10)

        # 持仓量得分
        oi_score = min(30, open_interest / 50)

        # 价差得分
        if bid_ask_spread_pct <= 5:
            spread_score = 20
        elif bid_ask_spread_pct <= 10:
            spread_score = 15
        elif bid_ask_spread_pct <= 20:
            spread_score = 10
        else:
            spread_score = max(0, 10 - (bid_ask_spread_pct - 20) / 2)

        return volume_score + oi_score + spread_score

    def _score_time_decay(self, days_to_expiry: int) -> float:
        """计分时间衰减优势"""
        # Sell Put策略偏好适中的到期时间
        if 20 <= days_to_expiry <= 45:
            return 100
        elif 10 <= days_to_expiry < 20:
            return 70 + (days_to_expiry - 10) * 3
        elif 45 < days_to_expiry <= 90:
            return 100 - (days_to_expiry - 45) * 1.5
        elif days_to_expiry < 10:
            return max(10, 70 - (10 - days_to_expiry) * 6)
        else:
            return max(20, 100 - (days_to_expiry - 90) * 0.5)

    def _score_volatility_premium(self, implied_vol: float, historical_vol: float) -> float:
        """计分波动率溢价"""
        if historical_vol <= 0:
            return 50

        vol_premium = (implied_vol - historical_vol) / historical_vol * 100

        # 隐含波动率高于历史波动率有利于卖方
        if vol_premium >= 20:
            return 100
        elif vol_premium >= 10:
            return 80 + (vol_premium - 10) * 2
        elif vol_premium >= 0:
            return 50 + vol_premium * 3
        else:
            return max(0, 50 + vol_premium * 2)

    def _calculate_assignment_risk(self, current_price: float, strike: float) -> str:
        """计算被指派风险等级"""
        distance_pct = (current_price - strike) / current_price * 100

        if distance_pct >= 15:
            return "very_low"
        elif distance_pct >= 10:
            return "low"
        elif distance_pct >= 5:
            return "moderate"
        elif distance_pct >= 0:
            return "high"
        else:
            return "very_high"

    def _generate_put_notes(self, current_price: float, strike: float,
                           premium_yield: float, days_to_expiry: int) -> List[str]:
        """生成看跌期权策略提示"""
        notes = []

        distance_pct = (current_price - strike) / current_price * 100

        if distance_pct >= 10:
            notes.append("较大安全边际，被指派风险低")
        elif distance_pct < 0:
            notes.append("实值期权，被指派风险高，需谨慎")

        if premium_yield >= 2:
            notes.append("期权费收益率较高")
        elif premium_yield < 1:
            notes.append("期权费收益率较低")

        if days_to_expiry <= 15:
            notes.append("临近到期，时间衰减快")
        elif days_to_expiry >= 60:
            notes.append("到期时间较长，需要耐心持有")

        return notes

    def _generate_strategy_analysis(self, scored_options: List, current_price: float,
                                   stock_data: Dict, trend_info: Dict = None) -> Dict[str, Any]:
        """生成策略分析摘要"""
        if not scored_options:
            return {
                'market_outlook': 'neutral',
                'strategy_suitability': 'poor',
                'risk_level': 'high',
                'recommendations': ['当前市场条件下无合适的Sell Put机会'],
                'trend_analysis': trend_info.get('display_info') if trend_info else None
            }

        # 分析最佳期权
        best_option = scored_options[0]
        avg_score = np.mean([opt.get('score', 0) for opt in scored_options[:5]])

        # 趋势影响策略适宜性判断
        trend_is_ideal = trend_info.get('is_ideal_trend', True) if trend_info else True
        if not trend_is_ideal:
            # 趋势不理想时，降低策略适宜性评级
            if avg_score >= 80:
                suitability = 'good'  # excellent -> good
            elif avg_score >= 60:
                suitability = 'moderate'  # good -> moderate
            else:
                suitability = 'poor'
        else:
            suitability = 'excellent' if avg_score >= 80 else 'good' if avg_score >= 60 else 'moderate'

        analysis = {
            'market_outlook': self._assess_market_outlook(scored_options, stock_data),
            'strategy_suitability': suitability,
            'risk_level': self._assess_risk_level(scored_options),
            'best_opportunity': {
                'strike': best_option.get('strike'),
                'premium_yield': best_option.get('premium_yield'),
                'score': best_option.get('score'),
                'days_to_expiry': best_option.get('days_to_expiry'),
                'support_score': best_option.get('score_breakdown', {}).get('support_strength', 0),
            },
            'recommendations': self._generate_recommendations(
                scored_options, current_price, trend_info
            ),
            # 新增：趋势分析
            'trend_analysis': trend_info.get('display_info') if trend_info else None
        }

        return analysis

    def _assess_market_outlook(self, scored_options: List, stock_data: Dict) -> str:
        """评估市场前景"""
        # 基于期权分布和股票数据评估
        high_score_count = len([opt for opt in scored_options if opt.get('score', 0) >= 70])

        if high_score_count >= 3:
            return 'bullish'  # 多个高分期权，看涨
        elif high_score_count >= 1:
            return 'neutral_to_bullish'
        else:
            return 'neutral'

    def _assess_risk_level(self, scored_options: List) -> str:
        """评估风险等级"""
        if not scored_options:
            return 'high'

        # 基于最佳期权的特征评估风险
        best_option = scored_options[0]
        safety_margin = best_option.get('safety_margin', 0)

        if safety_margin >= 10:
            return 'low'
        elif safety_margin >= 5:
            return 'moderate'
        else:
            return 'high'

    def _generate_recommendations(self, scored_options: List, current_price: float,
                                   trend_info: Dict = None) -> List[str]:
        """生成策略建议"""
        recommendations = []

        if not scored_options:
            recommendations.append("当前无合适的Sell Put机会，建议等待更好时机")
            return recommendations

        best_option = scored_options[0]

        # 新增：趋势提示
        if trend_info:
            display = trend_info.get('display_info', {})
            trend = trend_info.get('trend', 'sideways')
            is_ideal = display.get('is_ideal_trend', True)

            if is_ideal:
                recommendations.append(f"当前{display.get('trend_name_cn', '下跌趋势')}，适合Sell Put策略")
            else:
                recommendations.append(f"⚠️ {display.get('warning', '趋势不匹配')}")

        if best_option.get('score', 0) >= 80:
            recommendations.append(f"推荐卖出执行价 ${best_option.get('strike')} 的看跌期权")

        # 新增：支撑位提示
        support_score = best_option.get('score_breakdown', {}).get('support_strength', 0)
        if support_score >= 70:
            recommendations.append("执行价接近重要支撑位，被击穿风险较低")
        elif support_score < 40:
            recommendations.append("⚠️ 执行价远离支撑位，需注意下跌风险")

        if best_option.get('premium_yield', 0) >= 2:
            recommendations.append("期权费收益率理想，适合收取权利金策略")

        # 新增：ATR安全提示
        atr_safety = best_option.get('atr_safety', {})
        if atr_safety.get('is_safe'):
            recommendations.append(f"安全缓冲{atr_safety.get('atr_multiples', 0):.1f}倍ATR，波动风险可控")
        elif atr_safety.get('safety_ratio', 0) < 0.5:
            recommendations.append("⚠️ 安全缓冲不足，高波动时可能被击穿")

        if len([opt for opt in scored_options if opt.get('score', 0) >= 60]) >= 3:
            recommendations.append("多个期权机会可供选择，建议分散投资")

        recommendations.append("注意管理被指派风险，必要时及时止损")

        return recommendations


# 独立测试功能
if __name__ == "__main__":
    print("🧪 Sell Put策略计分器独立测试")
    print("=" * 50)

    # 创建计分器实例
    scorer = SellPutScorer()
    print("✅ Sell Put计分器创建成功")

    # 模拟测试数据
    mock_puts = [
        {
            'symbol': 'AAPL_2024-02-16_170_P',
            'strike': 170,
            'expiry': '2024-02-16',
            'bid': 2.5,
            'ask': 2.7,
            'volume': 150,
            'open_interest': 500,
            'implied_volatility': 0.25,
            'days_to_expiry': 30
        },
        {
            'symbol': 'AAPL_2024-02-16_165_P',
            'strike': 165,
            'expiry': '2024-02-16',
            'bid': 1.8,
            'ask': 2.0,
            'volume': 80,
            'open_interest': 300,
            'implied_volatility': 0.22,
            'days_to_expiry': 30
        }
    ]

    mock_options_data = {
        'success': True,
        'symbol': 'AAPL',
        'puts': mock_puts
    }

    mock_stock_data = {
        'current_price': 175.0,
        'volatility_30d': 0.20
    }

    print(f"\n📊 测试期权计分...")
    result = scorer.score_options(mock_options_data, mock_stock_data)

    if result.get('success'):
        print(f"  ✅ 计分成功")
        print(f"  📈 分析期权数: {result.get('total_options_analyzed')}")
        print(f"  🎯 合格期权数: {result.get('qualified_options')}")

        recommendations = result.get('recommendations', [])
        if recommendations:
            best = recommendations[0]
            print(f"  🏆 最佳推荐:")
            print(f"    执行价: ${best.get('strike')}")
            print(f"    得分: {best.get('score')}")
            print(f"    期权费收益: {best.get('premium_yield'):.2f}%")
            print(f"    安全边际: {best.get('safety_margin'):.2f}%")

    else:
        print(f"  ❌ 计分失败: {result.get('error')}")

    print("\n💡 策略说明:")
    print("- Sell Put适合看涨或中性市场")
    print("- 收取期权费作为收益")
    print("- 注意被指派风险管理")
    print("- 选择适当的执行价和到期时间")

    print("\n🎉 Sell Put策略计分器独立测试完成!")
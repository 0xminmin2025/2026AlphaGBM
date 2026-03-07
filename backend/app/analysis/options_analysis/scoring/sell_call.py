"""
Sell Call 期权策略计分器
实现卖出看涨期权的专门计分算法

优化版本（基于真实交易者反馈）：
- 趋势过滤：Sell Call 只在上涨时做（显示但降分）
- ATR动态安全边际：不同股票波动不同
- 阻力位强度评估：执行价是否为真实阻力位
"""

import logging
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from .trend_analyzer import TrendAnalyzer, ATRCalculator
from .macro_event_calendar import calculate_event_penalty, generate_event_notes, get_vix_penalty_for_seller
from ..option_market_config import OptionMarketConfig, US_OPTIONS_CONFIG

logger = logging.getLogger(__name__)


class SellCallScorer:
    """卖出看涨期权计分器"""

    def __init__(self):
        """初始化Sell Call计分器"""
        self.strategy_name = "sell_call"

        # 优化后的权重配置（基于真实交易者反馈）
        self.weight_config = {
            'premium_yield': 0.18,         # 期权费收益率（略降）
            'resistance_strength': 0.20,   # 阻力位强度
            'trend_alignment': 0.12,       # 趋势匹配度（略降）
            'upside_buffer': 0.25,         # 上涨缓冲（提升：安全性是sell_call核心）
            'liquidity': 0.10,             # 流动性
            'is_covered': 0.05,            # 是否有现股（裸卖时权重降低）
            'time_decay': 0.05,            # 时间衰减
            'overvaluation': 0.05,         # 超买程度
        }

        # 初始化趋势分析器和ATR计算器
        self.trend_analyzer = TrendAnalyzer()
        self.atr_calculator = ATRCalculator()

    def score_options(self, options_data: Dict, stock_data: Dict,
                      user_holdings: List[str] = None,
                      market_config: OptionMarketConfig = None,
                      vix_level: float = 0) -> Dict[str, Any]:
        """
        为Sell Call策略计分期权

        Args:
            options_data: 期权链数据
            stock_data: 标的股票数据
            user_holdings: 用户持有的股票列表（用于Covered Call识别）
            market_config: 市场配置（可选，默认 US）
            vix_level: 当前VIX水平（用于卖方策略风险调整）

        Returns:
            计分结果
        """
        try:
            if market_config is None:
                market_config = US_OPTIONS_CONFIG

            logger.info(f"开始Sell Call策略计分: {options_data.get('symbol', 'Unknown')} (市场: {market_config.market})")

            if not options_data.get('success'):
                return {
                    'success': False,
                    'strategy': self.strategy_name,
                    'error': '期权数据无效'
                }

            calls = options_data.get('calls', [])
            if not calls:
                return {
                    'success': False,
                    'strategy': self.strategy_name,
                    'error': '无看涨期权数据'
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

            # 新增：计算ATR用于动态上涨缓冲
            atr_14 = self._get_atr(stock_data, market_config)

            # 检查是否为Covered Call
            symbol = options_data.get('symbol', '')
            is_covered = user_holdings and symbol in user_holdings

            # VIX环境分层：高VIX时卖方策略降分
            vix_penalty_info = get_vix_penalty_for_seller(vix_level) if vix_level > 0 else None

            # 筛选和计分期权
            scored_options = []
            for call_option in calls:
                score_result = self._score_individual_call(
                    call_option, current_price, stock_data,
                    trend_info, atr_14, is_covered,
                    market_config=market_config
                )
                if score_result and score_result.get('score', 0) > 0:
                    # VIX惩罚
                    if vix_penalty_info and vix_penalty_info['penalty_factor'] < 1.0:
                        score_result['score'] = round(
                            score_result['score'] * vix_penalty_info['penalty_factor'], 1
                        )
                        if vix_penalty_info['warning']:
                            score_result.setdefault('strategy_notes', []).append(
                                vix_penalty_info['warning']
                            )
                        score_result['vix_zone'] = vix_penalty_info['vix_zone']
                    scored_options.append(score_result)

            # 排序并选择最佳期权
            scored_options.sort(key=lambda x: x.get('score', 0), reverse=True)

            # 生成策略分析
            strategy_analysis = self._generate_strategy_analysis(
                scored_options, current_price, stock_data, trend_info, is_covered
            )

            return {
                'success': True,
                'strategy': self.strategy_name,
                'symbol': options_data.get('symbol'),
                'current_price': current_price,
                'analysis_time': datetime.now().isoformat(),
                'total_options_analyzed': len(calls),
                'qualified_options': len(scored_options),
                'recommendations': scored_options[:10],
                'strategy_analysis': strategy_analysis,
                'scoring_weights': self.weight_config,
                # 新增：趋势信息
                'trend_info': trend_info,
                'atr_14': atr_14,
                'is_covered': is_covered,
            }

        except Exception as e:
            logger.error(f"Sell Call计分失败: {e}")
            return {
                'success': False,
                'strategy': self.strategy_name,
                'error': f"计分失败: {str(e)}"
            }

    def _analyze_trend(self, stock_data: Dict, current_price: float) -> Dict[str, Any]:
        """分析当前趋势"""
        try:
            price_history = stock_data.get('price_history', [])
            if isinstance(price_history, list) and len(price_history) >= 6:
                price_series = pd.Series(price_history)
            else:
                price_series = pd.Series([current_price] * 7)

            return self.trend_analyzer.analyze_trend_for_strategy(
                price_series, current_price, 'sell_call'
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

        atr = stock_data.get('atr_14', 0)
        if atr > 0:
            return atr

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

        vol_30d = stock_data.get('volatility_30d', 0.25)
        current_price = stock_data.get('current_price', 100)
        return current_price * vol_30d / np.sqrt(trading_days)

    def _score_individual_call(self, call_option: Dict, current_price: float,
                              stock_data: Dict, trend_info: Dict = None,
                              atr_14: float = 0, is_covered: bool = False,
                              market_config: OptionMarketConfig = None) -> Optional[Dict]:
        """计分单个看涨期权（优化版本：含趋势和ATR评分）"""
        try:
            if market_config is None:
                market_config = US_OPTIONS_CONFIG
            multiplier = market_config.get_multiplier(
                stock_data.get('symbol', '') if isinstance(stock_data, dict) else ''
            )
            trading_days = market_config.trading_days_per_year

            strike = call_option.get('strike', 0)
            bid = call_option.get('bid', 0)
            ask = call_option.get('ask', 0)
            volume = call_option.get('volume', 0)
            open_interest = call_option.get('open_interest', 0)
            implied_volatility = call_option.get('implied_volatility', 0)
            days_to_expiry = call_option.get('days_to_expiry', 0)

            if not all([strike, bid > 0, days_to_expiry > 0]):
                return None

            # CALL期权：行权价 > 当前股价 才是虚值(OTM)，才适合卖出
            if strike < current_price * 0.98:
                return None

            mid_price = (bid + ask) / 2
            intrinsic_value = max(0, current_price - strike)
            time_value = max(0, mid_price - intrinsic_value)

            if time_value <= 0:
                return None

            premium_yield = (time_value / current_price) * 100
            upside_buffer = ((strike - current_price) / current_price) * 100

            annualized_return = (premium_yield / days_to_expiry) * trading_days

            # 计算各项得分
            scores = {}

            # 1. 期权费收益率得分 (20%)
            scores['premium_yield'] = self._score_premium_yield(premium_yield, days_to_expiry)

            # 2. 新增：阻力位强度评分 (20%)
            scores['resistance_strength'] = self._score_resistance_strength(
                strike, current_price, stock_data
            )

            # 3. 新增：趋势匹配度评分 (15%)
            if trend_info:
                scores['trend_alignment'] = trend_info.get('trend_alignment_score', 60)
            else:
                scores['trend_alignment'] = 60

            # 4. 上涨缓冲评分 - 使用ATR动态计算 (15%)
            atr_safety = self._calculate_atr_safety(current_price, strike, atr_14)
            scores['upside_buffer'] = self._score_upside_buffer_with_atr(
                upside_buffer, atr_safety
            )

            # 5. 流动性得分 (10%)
            scores['liquidity'] = self._score_liquidity(volume, open_interest, bid, ask)

            # 6. 新增：Covered Call 加分 (10%)
            scores['is_covered'] = 100 if is_covered else 50

            # 7. 时间衰减得分 (5%)
            scores['time_decay'] = self._score_time_decay(days_to_expiry)

            # 8. 超买程度得分 (5%)
            scores['overvaluation'] = self._score_overvaluation(current_price, stock_data)

            # 计算加权总分
            total_score = sum(
                scores[factor] * self.weight_config.get(factor, 0)
                for factor in scores.keys()
            )

            # 宏观事件风险检测（Sell Call：加警告标签，不降分）
            expiry_str = call_option.get('expiry', '')
            event_penalty = calculate_event_penalty(expiry_str, days_to_expiry, 'sell_call')

            # 商品期权：交割月风险惩罚
            delivery_risk_data = None
            if market_config and market_config.market == 'COMMODITY':
                contract_code = call_option.get('contract') or call_option.get('expiry', '')
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

            # 生成策略提示（含宏观事件提示）
            strategy_notes = self._generate_call_notes(current_price, strike, premium_yield, days_to_expiry)
            event_notes = generate_event_notes(expiry_str, days_to_expiry)
            strategy_notes.extend(event_notes)
            if event_penalty['warnings']:
                strategy_notes.extend(event_penalty['warnings'])

            result = {
                'option_symbol': call_option.get('symbol', f"CALL_{strike}_{call_option.get('expiry')}"),
                'strike': strike,
                'expiry': call_option.get('expiry'),
                'days_to_expiry': days_to_expiry,
                'bid': bid,
                'ask': ask,
                'mid_price': round(mid_price, 2),
                'time_value': round(time_value, 2),
                'intrinsic_value': round(intrinsic_value, 2),
                'premium_yield': round(premium_yield, 2),
                'annualized_return': round(annualized_return, 2),
                'is_short_term': days_to_expiry <= 7,
                'upside_buffer': round(upside_buffer, 2),
                'implied_volatility': round(implied_volatility * 100, 1),
                'volume': volume,
                'open_interest': open_interest,
                'score': round(total_score, 1),
                'score_breakdown': {k: round(v, 1) for k, v in scores.items()},
                'assignment_risk': self._calculate_assignment_risk(current_price, strike),
                'max_profit': round(time_value * multiplier, 0),
                'breakeven': round(current_price + mid_price, 2),
                'profit_range': f"${current_price:.2f} - ${strike:.2f}",
                'strategy_notes': strategy_notes,
                # 新增：ATR安全边际信息
                'atr_safety': atr_safety,
                # 新增：趋势信息
                'trend_warning': trend_warning,
                'is_ideal_trend': trend_info.get('is_ideal_trend', True) if trend_info else True,
                # 新增：Covered Call标识
                'is_covered': is_covered,
                # 新增：宏观事件风险
                'macro_event_risk': event_penalty['event_info'] if event_penalty['has_event_risk'] else None,
            }

            if delivery_risk_data:
                result['delivery_risk'] = delivery_risk_data.to_dict()

            return result

        except Exception as e:
            logger.error(f"单个期权计分失败: {e}")
            return None

    def _calculate_atr_safety(self, current_price: float, strike: float,
                             atr_14: float) -> Dict[str, Any]:
        """计算基于ATR的上涨缓冲"""
        if atr_14 <= 0:
            return {
                'safety_ratio': 0,
                'atr_multiples': 0,
                'is_safe': False
            }
        return self.atr_calculator.calculate_atr_based_safety(
            current_price, strike, atr_14, atr_ratio=2.0
        )

    def _score_upside_buffer_with_atr(self, upside_buffer: float,
                                      atr_safety: Dict) -> float:
        """结合ATR的上涨缓冲评分"""
        # 基础评分（基于百分比缓冲）
        if upside_buffer >= 10:
            base_score = 80
        elif upside_buffer >= 5:
            base_score = 60 + (upside_buffer - 5) * 4
        elif upside_buffer >= 2:
            base_score = 40 + (upside_buffer - 2) * 6.67
        else:
            base_score = max(10, upside_buffer * 20)

        # ATR调整
        safety_ratio = atr_safety.get('safety_ratio', 0)

        if safety_ratio >= 1.5:
            atr_bonus = 15
        elif safety_ratio >= 1.0:
            atr_bonus = 5
        elif safety_ratio >= 0.5:
            atr_bonus = -10
        else:
            atr_bonus = -20

        return min(100, max(0, base_score + atr_bonus))

    def _score_resistance_strength(self, strike: float, current_price: float,
                                   stock_data: Dict) -> float:
        """评分执行价作为阻力位的强度"""
        try:
            support_resistance = stock_data.get('support_resistance', {})

            # 获取阻力位
            resistance_1 = support_resistance.get('resistance_1', 0)
            resistance_2 = support_resistance.get('resistance_2', 0)
            high_52w = support_resistance.get('high_52w', 0)

            # MA阻力
            ma_50 = stock_data.get('ma_50', 0)
            ma_200 = stock_data.get('ma_200', 0)

            scores = []

            # 检查执行价是否接近各阻力位
            resistance_levels = [
                (resistance_1, 25, 'R1'),
                (resistance_2, 20, 'R2'),
                (high_52w, 25, '52W High'),
            ]

            # 如果价格在MA上方，MA可以作为阻力参考
            if current_price > ma_50 > 0:
                resistance_levels.append((ma_50 * 1.05, 15, 'MA50+5%'))
            if current_price > ma_200 > 0:
                resistance_levels.append((ma_200 * 1.08, 15, 'MA200+8%'))

            for level, max_score, name in resistance_levels:
                if level and level > 0:
                    diff_pct = abs(strike - level) / current_price * 100
                    if diff_pct <= 1:
                        scores.append(max_score)
                    elif diff_pct <= 3:
                        scores.append(max_score * 0.7)
                    elif diff_pct <= 5:
                        scores.append(max_score * 0.4)

            if not scores:
                # 基于上涨缓冲给分
                upside_pct = (strike - current_price) / current_price * 100
                if 5 <= upside_pct <= 10:
                    return 60
                elif 2 <= upside_pct < 5:
                    return 50
                elif upside_pct > 15:
                    return 30
                else:
                    return 40

            return min(100, sum(scores))

        except Exception as e:
            logger.error(f"阻力位评分失败: {e}")
            return 50

    def _score_premium_yield(self, premium_yield: float, days_to_expiry: int) -> float:
        """计分期权费收益率"""
        # 年化收益率计算
        annualized_yield = (premium_yield / days_to_expiry) * 365

        # 得分标准 (Sell Call一般收益率低于Sell Put)
        if annualized_yield >= 15:
            return 100
        elif annualized_yield >= 12:
            return 85 + (annualized_yield - 12) * 5
        elif annualized_yield >= 8:
            return 70 + (annualized_yield - 8) * 3.75
        elif annualized_yield >= 5:
            return 50 + (annualized_yield - 5) * 6.67
        else:
            return max(0, annualized_yield * 10)

    def _score_overvaluation(self, current_price: float, stock_data: Dict) -> float:
        """计分股票超买程度"""
        try:
            # 基于技术指标评估超买
            resistance_1 = stock_data.get('support_resistance', {}).get('resistance_1', 0)
            resistance_2 = stock_data.get('support_resistance', {}).get('resistance_2', 0)
            high_52w = stock_data.get('support_resistance', {}).get('high_52w', 0)

            scores = []

            # 接近阻力位得分
            if resistance_1:
                distance_to_r1 = (resistance_1 - current_price) / current_price * 100
                if distance_to_r1 <= 2:
                    scores.append(90)  # 很接近第一阻力位
                elif distance_to_r1 <= 5:
                    scores.append(70)
                elif distance_to_r1 <= 10:
                    scores.append(50)
                else:
                    scores.append(30)

            # 52周高位分析
            if high_52w:
                distance_to_high = (high_52w - current_price) / current_price * 100
                if distance_to_high <= 3:
                    scores.append(85)  # 接近52周高点
                elif distance_to_high <= 8:
                    scores.append(60)
                else:
                    scores.append(40)

            # 价格变化分析
            change_percent = stock_data.get('change_percent', 0)
            if change_percent >= 3:
                scores.append(80)  # 当日涨幅较大
            elif change_percent >= 1:
                scores.append(60)
            elif change_percent <= -2:
                scores.append(20)  # 下跌不适合卖Call
            else:
                scores.append(50)

            return np.mean(scores) if scores else 50

        except Exception as e:
            logger.error(f"超买程度评估失败: {e}")
            return 50

    def _score_resistance_level(self, strike: float, current_price: float, stock_data: Dict) -> float:
        """计分执行价与阻力位关系"""
        try:
            support_resistance = stock_data.get('support_resistance', {})
            resistance_1 = support_resistance.get('resistance_1', 0)
            resistance_2 = support_resistance.get('resistance_2', 0)

            # 执行价接近阻力位时得分高
            scores = []

            if resistance_1:
                diff_r1 = abs(strike - resistance_1) / current_price * 100
                if diff_r1 <= 2:
                    scores.append(100)  # 执行价在阻力位附近
                elif diff_r1 <= 5:
                    scores.append(80)
                else:
                    scores.append(60)

            if resistance_2:
                diff_r2 = abs(strike - resistance_2) / current_price * 100
                if diff_r2 <= 2:
                    scores.append(90)
                elif diff_r2 <= 5:
                    scores.append(70)

            # 执行价高度分析
            upside_pct = (strike - current_price) / current_price * 100
            if 3 <= upside_pct <= 10:
                scores.append(80)  # 理想的缓冲区间
            elif 0 <= upside_pct < 3:
                scores.append(60)  # 较小缓冲
            elif upside_pct > 15:
                scores.append(40)  # 缓冲过大，收益率低
            else:
                scores.append(30)

            return np.mean(scores) if scores else 60

        except Exception as e:
            logger.error(f"阻力位分析失败: {e}")
            return 60

    def _score_liquidity(self, volume: int, open_interest: int, bid: float, ask: float) -> float:
        """计分流动性（与sell put相同）"""
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
        # Sell Call策略偏好较短的到期时间以快速获利
        if 15 <= days_to_expiry <= 30:
            return 100
        elif 7 <= days_to_expiry < 15:
            return 90
        elif 30 < days_to_expiry <= 45:
            return 80 - (days_to_expiry - 30) * 1.5
        elif days_to_expiry < 7:
            return max(20, 90 - (7 - days_to_expiry) * 10)
        else:
            return max(30, 80 - (days_to_expiry - 45) * 0.8)

    def _score_volatility_timing(self, implied_vol: float, historical_vol: float) -> float:
        """计分波动率择时"""
        if historical_vol <= 0:
            return 50

        vol_premium = (implied_vol - historical_vol) / historical_vol * 100

        # 隐含波动率高于历史波动率有利于卖方，但过高也要警惕
        if vol_premium >= 30:
            return 100
        elif vol_premium >= 15:
            return 80 + (vol_premium - 15) * 1.33
        elif vol_premium >= 0:
            return 50 + vol_premium * 2
        else:
            return max(20, 50 + vol_premium * 1.5)

    def _calculate_assignment_risk(self, current_price: float, strike: float) -> str:
        """计算被指派风险等级"""
        distance_pct = (strike - current_price) / current_price * 100

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

    def _generate_call_notes(self, current_price: float, strike: float,
                            premium_yield: float, days_to_expiry: int) -> List[str]:
        """生成看涨期权策略提示"""
        notes = []

        distance_pct = (strike - current_price) / current_price * 100

        if distance_pct >= 8:
            notes.append("较大上涨空间，被指派风险较低")
        elif distance_pct < 2:
            notes.append("接近执行价，被指派风险较高")

        if premium_yield >= 1.5:
            notes.append("期权费收益率不错")
        elif premium_yield < 0.8:
            notes.append("期权费收益率偏低")

        if days_to_expiry <= 15:
            notes.append("临近到期，适合快速获利")
        elif days_to_expiry >= 45:
            notes.append("到期时间较长，需要股价配合")

        notes.append("适合中性或轻微看跌市场")

        return notes

    def _generate_strategy_analysis(self, scored_options: List, current_price: float,
                                   stock_data: Dict, trend_info: Dict = None,
                                   is_covered: bool = False) -> Dict[str, Any]:
        """生成策略分析摘要"""
        if not scored_options:
            return {
                'market_outlook': 'neutral',
                'strategy_suitability': 'poor',
                'risk_level': 'high',
                'recommendations': ['当前市场条件下无合适的Sell Call机会'],
                'trend_analysis': trend_info.get('display_info') if trend_info else None
            }

        best_option = scored_options[0]
        avg_score = np.mean([opt.get('score', 0) for opt in scored_options[:5]])

        # 趋势影响策略适宜性判断
        trend_is_ideal = trend_info.get('is_ideal_trend', True) if trend_info else True
        if not trend_is_ideal:
            if avg_score >= 75:
                suitability = 'good'
            elif avg_score >= 55:
                suitability = 'moderate'
            else:
                suitability = 'poor'
        else:
            suitability = 'excellent' if avg_score >= 75 else 'good' if avg_score >= 55 else 'moderate'

        # Covered Call 提升适宜性
        if is_covered and suitability != 'excellent':
            suitability_upgrade = {'poor': 'moderate', 'moderate': 'good', 'good': 'excellent'}
            suitability = suitability_upgrade.get(suitability, suitability)

        analysis = {
            'market_outlook': self._assess_market_outlook(scored_options, stock_data),
            'strategy_suitability': suitability,
            'risk_level': self._assess_risk_level(scored_options),
            'best_opportunity': {
                'strike': best_option.get('strike'),
                'premium_yield': best_option.get('premium_yield'),
                'score': best_option.get('score'),
                'days_to_expiry': best_option.get('days_to_expiry'),
                'upside_buffer': best_option.get('upside_buffer'),
                'resistance_score': best_option.get('score_breakdown', {}).get('resistance_strength', 0),
            },
            'recommendations': self._generate_recommendations(
                scored_options, current_price, stock_data, trend_info, is_covered
            ),
            'trend_analysis': trend_info.get('display_info') if trend_info else None,
            'is_covered_call': is_covered,
        }

        return analysis

    def _assess_market_outlook(self, scored_options: List, stock_data: Dict) -> str:
        """评估市场前景"""
        # 基于技术指标评估
        change_percent = stock_data.get('change_percent', 0)
        resistance_distance = self._calculate_resistance_distance(stock_data)

        if change_percent >= 2 or resistance_distance <= 5:
            return 'bearish_to_neutral'  # 适合卖Call
        elif change_percent <= -2:
            return 'bearish'  # 不适合卖Call
        else:
            return 'neutral'

    def _calculate_resistance_distance(self, stock_data: Dict) -> float:
        """计算到阻力位距离"""
        current_price = stock_data.get('current_price', 0)
        resistance_1 = stock_data.get('support_resistance', {}).get('resistance_1', 0)

        if resistance_1 and current_price:
            return (resistance_1 - current_price) / current_price * 100

        return 100  # 如果无阻力位数据，返回大值

    def _assess_risk_level(self, scored_options: List) -> str:
        """评估风险等级"""
        if not scored_options:
            return 'high'

        best_option = scored_options[0]
        upside_buffer = best_option.get('upside_buffer', 0)

        if upside_buffer >= 10:
            return 'low'
        elif upside_buffer >= 5:
            return 'moderate'
        else:
            return 'high'

    def _generate_recommendations(self, scored_options: List, current_price: float,
                                 stock_data: Dict, trend_info: Dict = None,
                                 is_covered: bool = False) -> List[str]:
        """生成策略建议"""
        recommendations = []

        if not scored_options:
            recommendations.append("当前无合适的Sell Call机会，建议等待股价上涨")
            return recommendations

        best_option = scored_options[0]

        # 新增：Covered Call 提示
        if is_covered:
            recommendations.append("✅ 持有现股，可执行 Covered Call 策略（风险可控）")

        # 新增：趋势提示
        if trend_info:
            display = trend_info.get('display_info', {})
            is_ideal = display.get('is_ideal_trend', True)

            if is_ideal:
                recommendations.append(f"当前{display.get('trend_name_cn', '上涨趋势')}，适合Sell Call策略")
            else:
                recommendations.append(f"⚠️ {display.get('warning', '趋势不匹配')}")

        if best_option.get('score', 0) >= 70:
            recommendations.append(f"推荐卖出执行价 ${best_option.get('strike')} 的看涨期权")

        # 新增：阻力位提示
        resistance_score = best_option.get('score_breakdown', {}).get('resistance_strength', 0)
        if resistance_score >= 70:
            recommendations.append("执行价接近重要阻力位，被突破风险较低")
        elif resistance_score < 40:
            recommendations.append("⚠️ 执行价远离阻力位，需注意上涨风险")

        # 基于市场状况给建议
        change_percent = stock_data.get('change_percent', 0)
        if change_percent >= 2:
            recommendations.append("股价有所上涨，是卖出看涨期权的好时机")

        # 新增：ATR安全提示
        atr_safety = best_option.get('atr_safety', {})
        if atr_safety.get('is_safe'):
            recommendations.append(f"上涨缓冲{atr_safety.get('atr_multiples', 0):.1f}倍ATR，波动风险可控")
        elif atr_safety.get('safety_ratio', 0) < 0.5:
            recommendations.append("⚠️ 上涨缓冲不足，高波动时可能被突破")

        resistance_distance = self._calculate_resistance_distance(stock_data)
        if resistance_distance <= 8:
            recommendations.append("股价接近阻力位，有利于Sell Call策略")

        if len([opt for opt in scored_options if opt.get('score', 0) >= 60]) >= 3:
            recommendations.append("多个期权机会可供选择，建议选择不同到期时间分散风险")

        recommendations.append("密切关注股价走势，必要时及时平仓止损")

        return recommendations


# 独立测试功能
if __name__ == "__main__":
    print("🧪 Sell Call策略计分器独立测试")
    print("=" * 50)

    # 创建计分器实例
    scorer = SellCallScorer()
    print("✅ Sell Call计分器创建成功")

    # 模拟测试数据
    mock_calls = [
        {
            'symbol': 'AAPL_2024-02-16_180_C',
            'strike': 180,
            'expiry': '2024-02-16',
            'bid': 1.8,
            'ask': 2.0,
            'volume': 200,
            'open_interest': 600,
            'implied_volatility': 0.28,
            'days_to_expiry': 25
        },
        {
            'symbol': 'AAPL_2024-02-16_185_C',
            'strike': 185,
            'expiry': '2024-02-16',
            'bid': 1.0,
            'ask': 1.2,
            'volume': 120,
            'open_interest': 400,
            'implied_volatility': 0.26,
            'days_to_expiry': 25
        }
    ]

    mock_options_data = {
        'success': True,
        'symbol': 'AAPL',
        'calls': mock_calls
    }

    mock_stock_data = {
        'current_price': 175.0,
        'change_percent': 2.1,
        'volatility_30d': 0.22,
        'support_resistance': {
            'resistance_1': 180.0,
            'resistance_2': 185.0,
            'support_1': 170.0,
            'support_2': 165.0,
            'high_52w': 190.0,
            'low_52w': 145.0
        }
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
            print(f"    上涨缓冲: {best.get('upside_buffer'):.2f}%")
            print(f"    获利区间: {best.get('profit_range')}")

        strategy_analysis = result.get('strategy_analysis', {})
        print(f"  📊 市场前景: {strategy_analysis.get('market_outlook')}")
        print(f"  📋 策略适宜性: {strategy_analysis.get('strategy_suitability')}")
        print(f"  ⚠️  风险等级: {strategy_analysis.get('risk_level')}")

    else:
        print(f"  ❌ 计分失败: {result.get('error')}")

    print("\n💡 策略说明:")
    print("- Sell Call适合中性或轻微看跌市场")
    print("- 股价上涨至执行价以上会被指派")
    print("- 最好在股价接近阻力位时操作")
    print("- 收取期权费作为收益，有封顶风险")

    print("\n🎉 Sell Call策略计分器独立测试完成!")
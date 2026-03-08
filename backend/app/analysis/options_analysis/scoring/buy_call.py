"""
Buy Call 期权策略计分器
实现买入看涨期权的专门计分算法
"""

import logging
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from .trend_analyzer import TrendAnalyzer
from .macro_event_calendar import calculate_event_penalty, generate_event_notes, get_vix_penalty_for_seller
from ..option_market_config import OptionMarketConfig, US_OPTIONS_CONFIG

logger = logging.getLogger(__name__)


class BuyCallScorer:
    """买入看涨期权计分器"""

    def __init__(self):
        """初始化Buy Call计分器"""
        self.strategy_name = "buy_call"
        self.weight_config = {
            'bullish_momentum': 0.20,     # 上涨动量权重（略降）
            'breakout_potential': 0.15,   # 突破潜力权重（略降）
            'value_efficiency': 0.25,     # 价值效率权重（提升：高delta=高胜率）
            'volatility_timing': 0.20,    # 波动率择时权重（提升：低IV买入是核心）
            'liquidity': 0.10,            # 流动性权重
            'time_optimization': 0.10     # 时间价值优化权重
        }
        self.trend_analyzer = TrendAnalyzer()

    def score_options(self, options_data: Dict, stock_data: Dict,
                      market_config: OptionMarketConfig = None) -> Dict[str, Any]:
        """
        为Buy Call策略计分期权

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

            logger.info(f"开始Buy Call策略计分: {options_data.get('symbol', 'Unknown')} (市场: {market_config.market})")

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

            # 趋势分析：下跌趋势中买Call风险高
            trend_penalty = self._calculate_trend_penalty(stock_data, current_price)

            # 筛选和计分期权
            scored_options = []
            for call_option in calls:
                score_result = self._score_individual_call(call_option, current_price, stock_data, market_config=market_config)
                if score_result and score_result.get('score', 0) > 0:
                    # 趋势惩罚
                    if trend_penalty < 1.0:
                        score_result['score'] = round(score_result['score'] * trend_penalty, 1)
                    # IV过滤：高IV环境不推荐买入
                    vol_score = score_result.get('score_breakdown', {}).get('volatility_timing', 0)
                    if vol_score < 40:
                        continue
                    scored_options.append(score_result)

            # 排序并选择最佳期权
            scored_options.sort(key=lambda x: x.get('score', 0), reverse=True)

            # 生成策略分析
            strategy_analysis = self._generate_strategy_analysis(scored_options, current_price, stock_data)

            return {
                'success': True,
                'strategy': self.strategy_name,
                'symbol': options_data.get('symbol'),
                'current_price': current_price,
                'analysis_time': datetime.now().isoformat(),
                'total_options_analyzed': len(calls),
                'qualified_options': len(scored_options),
                'recommendations': scored_options[:10],  # 返回前10个
                'strategy_analysis': strategy_analysis,
                'scoring_weights': self.weight_config
            }

        except Exception as e:
            logger.error(f"Buy Call计分失败: {e}")
            return {
                'success': False,
                'strategy': self.strategy_name,
                'error': f"计分失败: {str(e)}"
            }

    def _score_individual_call(self, call_option: Dict, current_price: float,
                              stock_data: Dict,
                              market_config: OptionMarketConfig = None) -> Optional[Dict]:
        """计分单个看涨期权"""
        try:
            if market_config is None:
                market_config = US_OPTIONS_CONFIG
            multiplier = market_config.get_multiplier(
                stock_data.get('symbol', '') if isinstance(stock_data, dict) else ''
            )

            strike = call_option.get('strike', 0)
            bid = call_option.get('bid', 0)
            ask = call_option.get('ask', 0)
            volume = call_option.get('volume', 0)
            open_interest = call_option.get('open_interest', 0)
            implied_volatility = call_option.get('implied_volatility', 0)
            days_to_expiry = call_option.get('days_to_expiry', 0)
            delta = call_option.get('delta', None)

            if not all([strike, ask > 0, days_to_expiry > 0]):
                return None

            # Buy Call适合各种执行价，但重点关注平值和轻度虚值
            mid_price = (bid + ask) / 2
            intrinsic_value = max(0, current_price - strike)
            time_value = mid_price - intrinsic_value
            moneyness = (current_price - strike) / current_price * 100

            # 计算各项得分
            scores = {}

            # 1. 上涨动量得分 (25%)
            scores['bullish_momentum'] = self._score_bullish_momentum(stock_data)

            # 2. 突破潜力得分 (20%)
            scores['breakout_potential'] = self._score_breakout_potential(current_price, strike, stock_data)

            # 3. 价值效率得分 (20%)
            scores['value_efficiency'] = self._score_value_efficiency(delta, mid_price, moneyness)

            # 4. 波动率择时得分 (20%)
            scores['volatility_timing'] = self._score_volatility_timing(
                implied_volatility, stock_data.get('volatility_30d', 0.2),
                change_percent=stock_data.get('change_percent', 0)
            )

            # 5. 流动性得分 (10%)
            scores['liquidity'] = self._score_liquidity(volume, open_interest, bid, ask)

            # 6. 时间价值优化得分 (10%)
            scores['time_optimization'] = self._score_time_optimization(time_value, mid_price, days_to_expiry)

            # 计算加权总分
            total_score = sum(
                scores[factor] * self.weight_config[factor]
                for factor in scores.keys()
            )

            # 宏观事件风险惩罚（Buy Call：短期期权在事件日前到期时降分）
            expiry_str = call_option.get('expiry', '')
            event_penalty = calculate_event_penalty(expiry_str, days_to_expiry, 'buy_call')
            if event_penalty['has_event_risk']:
                total_score *= event_penalty['penalty_factor']

            # 商品期权：交割月风险惩罚
            delivery_risk_data = None
            if market_config and market_config.market == 'COMMODITY':
                contract_code = call_option.get('contract') or call_option.get('expiry', '')
                if contract_code:
                    from ..advanced.delivery_risk import DeliveryRiskCalculator
                    delivery_risk_data = DeliveryRiskCalculator().assess(contract_code)
                    total_score *= (1.0 - delivery_risk_data.delivery_penalty)

            # 计算盈亏平衡点
            breakeven = strike + mid_price
            required_move = ((breakeven - current_price) / current_price) * 100

            # 生成策略提示（含宏观事件提示）
            strategy_notes = self._generate_call_notes(current_price, strike, moneyness, time_value, days_to_expiry)
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
                'intrinsic_value': round(intrinsic_value, 2),
                'time_value': round(time_value, 2),
                'moneyness_pct': round(moneyness, 2),
                'implied_volatility': round(implied_volatility * 100, 1),
                'delta': delta,
                'volume': volume,
                'open_interest': open_interest,
                'score': round(total_score, 1),
                'score_breakdown': {k: round(v, 1) for k, v in scores.items()},
                'breakeven': round(breakeven, 2),
                'required_move_pct': round(required_move, 2),
                'max_loss': round(mid_price * multiplier, 0),  # 1份合约
                'max_profit_potential': 'unlimited',
                'leverage_ratio': round((delta if delta else 0.5) * current_price / mid_price, 2),
                'strategy_notes': strategy_notes,
                'macro_event_risk': event_penalty['event_info'] if event_penalty['has_event_risk'] else None,
            }

            if delivery_risk_data:
                result['delivery_risk'] = delivery_risk_data.to_dict()

            return result

        except Exception as e:
            logger.error(f"单个期权计分失败: {e}")
            return None

    def _calculate_trend_penalty(self, stock_data: Dict, current_price: float) -> float:
        """
        计算趋势惩罚因子。下跌趋势中买Call成功率低。

        Returns:
            惩罚因子 (0.0-1.0)，1.0表示无惩罚
        """
        try:
            price_history = stock_data.get('price_history', [])
            if isinstance(price_history, list) and len(price_history) >= 6:
                price_series = pd.Series(price_history)
            else:
                return 1.0

            trend, strength = self.trend_analyzer.determine_intraday_trend(
                price_series, current_price
            )

            if trend == 'downtrend':
                # 下跌趋势：强下跌惩罚35%，弱下跌惩罚20%
                return 1.0 - strength * 0.35
            elif trend == 'sideways':
                # 横盘：轻微惩罚10%
                return 0.90
            else:
                # 上涨趋势：无惩罚
                return 1.0
        except Exception as e:
            logger.error(f"趋势惩罚计算失败: {e}")
            return 1.0

    def _score_bullish_momentum(self, stock_data: Dict) -> float:
        """计分上涨动量"""
        try:
            change_percent = stock_data.get('change_percent', 0)

            # 基于当日变化
            momentum_score = 50  # 基础分

            if change_percent >= 3:
                momentum_score = 100  # 强烈上涨信号
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

            # 基于52周位置
            high_52w = stock_data.get('support_resistance', {}).get('high_52w', 0)
            low_52w = stock_data.get('support_resistance', {}).get('low_52w', 0)
            current_price = stock_data.get('current_price', 0)

            if high_52w and low_52w and current_price:
                position_in_range = (current_price - low_52w) / (high_52w - low_52w) * 100
                if position_in_range >= 70:
                    momentum_score += 20  # 接近52周高点，动量强劲
                elif position_in_range >= 50:
                    momentum_score += 15
                elif position_in_range <= 30:
                    momentum_score -= 10  # 接近低点，动量不足

            # 基于阻力位距离
            resistance_1 = stock_data.get('support_resistance', {}).get('resistance_1', 0)
            if resistance_1 and current_price:
                distance_to_resistance = (resistance_1 - current_price) / current_price * 100
                if distance_to_resistance <= 5:
                    momentum_score += 10  # 接近阻力位，突破可能带来强动量
                elif distance_to_resistance >= 15:
                    momentum_score -= 5   # 距离阻力位较远

            return min(100, momentum_score)

        except Exception as e:
            logger.error(f"上涨动量评估失败: {e}")
            return 50

    def _score_breakout_potential(self, current_price: float, strike: float, stock_data: Dict) -> float:
        """计分突破潜力"""
        try:
            support_resistance = stock_data.get('support_resistance', {})
            resistance_1 = support_resistance.get('resistance_1', 0)
            resistance_2 = support_resistance.get('resistance_2', 0)
            high_52w = support_resistance.get('high_52w', 0)

            score = 50  # 基础分

            # 当前价格相对阻力位的位置
            if resistance_1:
                distance_to_r1 = (resistance_1 - current_price) / current_price * 100
                if distance_to_r1 <= 3:
                    score += 25  # 非常接近第一阻力位
                elif distance_to_r1 <= 6:
                    score += 20
                elif distance_to_r1 <= 10:
                    score += 15
                else:
                    score += 5   # 距离较远但仍有突破空间

            # 执行价相对阻力位的位置
            if resistance_1 and strike >= resistance_1 * 1.02:
                score += 20  # 执行价在阻力位上方，突破后获利空间大

            if resistance_2 and strike >= resistance_2:
                score += 15  # 执行价在第二阻力位上方

            # 52周高点分析
            if high_52w:
                distance_to_high = (high_52w - current_price) / current_price * 100
                if distance_to_high <= 5:
                    score += 15  # 接近52周高点
                    if strike >= high_52w:
                        score += 10  # 执行价在52周高点上方
                elif distance_to_high >= 20:
                    score += 5   # 有较大上升空间

            # 技术分析信号
            change_percent = stock_data.get('change_percent', 0)
            if change_percent >= 2 and resistance_1 and current_price >= resistance_1 * 0.98:
                score += 20  # 上涨且接近阻力位

            return min(100, score)

        except Exception as e:
            logger.error(f"突破潜力评估失败: {e}")
            return 50

    def _score_value_efficiency(self, delta: Optional[float], mid_price: float, moneyness: float) -> float:
        """计分价值效率 (Delta/价格比率)"""
        try:
            if not delta or mid_price <= 0:
                return 40

            # Delta应该是正值（看涨期权）
            if delta <= 0:
                return 20

            # 计算效率比率
            efficiency = delta / mid_price

            # 平值和轻度虚值期权通常效率较高
            base_score = 50

            # 基于效率比率评分
            if efficiency >= 0.6:
                base_score = 100
            elif efficiency >= 0.4:
                base_score = 90
            elif efficiency >= 0.3:
                base_score = 80
            elif efficiency >= 0.2:
                base_score = 70
            elif efficiency >= 0.1:
                base_score = 60
            else:
                base_score = 40

            # 基于价值状态调整
            if -5 <= moneyness <= 5:
                base_score += 10  # 平值期权加分
            elif moneyness < -15:
                base_score -= 15  # 深度虚值减分较多
            elif moneyness > 15:
                base_score -= 5   # 深度实值略减分

            return min(100, base_score)

        except Exception as e:
            logger.error(f"价值效率评估失败: {e}")
            return 50

    def _score_volatility_timing(self, implied_vol: float, historical_vol: float,
                                 change_percent: float = 0) -> float:
        """计分波动率择时"""
        try:
            if historical_vol <= 0:
                return 50

            vol_ratio = implied_vol / historical_vol
            vol_percentile = self._estimate_vol_percentile(implied_vol)

            score = 50

            # 相对低隐含波动率有利于买入期权
            if vol_ratio <= 0.85:
                score += 25  # 隐含波动率相对较低
            elif vol_ratio <= 0.95:
                score += 15
            elif vol_ratio <= 1.05:
                score += 5
            elif vol_ratio <= 1.2:
                score -= 10
            else:
                score -= 20  # 隐含波动率过高

            # 基于波动率历史位置
            if vol_percentile <= 30:
                score += 20  # 低波动率环境，适合买入
            elif vol_percentile <= 50:
                score += 10
            elif vol_percentile >= 80:
                score -= 15  # 高波动率环境，期权费贵

            # 波动率扩张预期
            if abs(change_percent) >= 2:
                score += 10  # 大幅价格变动可能带来波动率上升

            return min(100, max(0, score))

        except Exception as e:
            logger.error(f"波动率择时评估失败: {e}")
            return 50

    def _estimate_vol_percentile(self, implied_vol: float) -> float:
        """估算波动率历史位置（简化实现）"""
        # 简化的波动率分位数估算
        if implied_vol <= 0.15:
            return 15
        elif implied_vol <= 0.20:
            return 30
        elif implied_vol <= 0.25:
            return 50
        elif implied_vol <= 0.35:
            return 75
        else:
            return 90

    def _score_liquidity(self, volume: int, open_interest: int, bid: float, ask: float) -> float:
        """计分流动性"""
        if bid <= 0 or ask <= 0:
            return 0

        bid_ask_spread_pct = (ask - bid) / ((ask + bid) / 2) * 100

        # 成交量得分
        volume_score = min(40, volume / 8)

        # 持仓量得分
        oi_score = min(30, open_interest / 40)

        # 价差得分
        if bid_ask_spread_pct <= 6:
            spread_score = 30
        elif bid_ask_spread_pct <= 12:
            spread_score = 20
        elif bid_ask_spread_pct <= 20:
            spread_score = 10
        else:
            spread_score = max(0, 10 - (bid_ask_spread_pct - 20) / 3)

        return volume_score + oi_score + spread_score

    def _score_time_optimization(self, time_value: float, mid_price: float, days_to_expiry: int) -> float:
        """计分时间价值优化"""
        try:
            if mid_price <= 0:
                return 40

            time_value_ratio = time_value / mid_price

            score = 50

            # 时间价值比例评估（Buy Call希望时间价值不要太高）
            if 0.2 <= time_value_ratio <= 0.6:
                score += 30  # 理想的时间价值比例
            elif 0.1 <= time_value_ratio < 0.2:
                score += 20
            elif 0.6 < time_value_ratio <= 0.8:
                score += 10
            elif time_value_ratio > 0.9:
                score -= 25  # 时间价值过高，不划算
            elif time_value_ratio < 0.1:
                score += 25  # 低时间价值，主要是内在价值

            # 基于到期时间调整（Buy Call偏好中等期限）
            if days_to_expiry <= 7:
                score -= 20  # 太短，时间衰减快
            elif days_to_expiry <= 30:
                score += 15  # 理想期限
            elif days_to_expiry <= 60:
                score += 20  # 最佳期限
            elif days_to_expiry <= 90:
                score += 10  # 较好期限
            else:
                score -= 10  # 太长，时间价值高

            return min(100, max(0, score))

        except Exception as e:
            logger.error(f"时间价值优化评估失败: {e}")
            return 50

    def _generate_call_notes(self, current_price: float, strike: float,
                            moneyness: float, time_value: float, days_to_expiry: int) -> List[str]:
        """生成看涨期权策略提示"""
        notes = []

        if moneyness >= 5:
            notes.append("实值期权，内在价值较高，风险相对较低")
        elif moneyness >= -5:
            notes.append("平值期权，价格敏感度适中")
        else:
            notes.append("虚值期权，杠杆效应强，高风险高收益")

        time_value_pct = time_value / strike * 100 if strike > 0 else 0
        if time_value_pct <= 2:
            notes.append("时间价值较低，性价比较高")
        elif time_value_pct >= 5:
            notes.append("时间价值较高，注意时间衰减风险")

        if days_to_expiry <= 15:
            notes.append("临近到期，需要股价快速上涨")
        elif days_to_expiry >= 60:
            notes.append("到期时间充足，适合长期趋势交易")

        if moneyness < -10:
            notes.append("需要股价大幅上涨才能获利")

        notes.append("适合看涨市场和突破交易")

        return notes

    def _generate_strategy_analysis(self, scored_options: List, current_price: float,
                                   stock_data: Dict) -> Dict[str, Any]:
        """生成策略分析摘要"""
        if not scored_options:
            return {
                'market_outlook': 'neutral',
                'strategy_suitability': 'poor',
                'risk_level': 'high',
                'recommendations': ['当前市场条件下无合适的Buy Call机会']
            }

        # 分析最佳期权
        best_option = scored_options[0]
        avg_score = np.mean([opt.get('score', 0) for opt in scored_options[:5]])

        analysis = {
            'market_outlook': self._assess_market_outlook(stock_data),
            'strategy_suitability': 'excellent' if avg_score >= 75 else 'good' if avg_score >= 55 else 'moderate',
            'risk_level': self._assess_risk_level(scored_options),
            'best_opportunity': {
                'strike': best_option.get('strike'),
                'cost': best_option.get('mid_price'),
                'breakeven': best_option.get('breakeven'),
                'required_move': best_option.get('required_move_pct'),
                'score': best_option.get('score'),
                'days_to_expiry': best_option.get('days_to_expiry')
            },
            'recommendations': self._generate_recommendations(scored_options, current_price, stock_data)
        }

        return analysis

    def _assess_market_outlook(self, stock_data: Dict) -> str:
        """评估市场前景"""
        change_percent = stock_data.get('change_percent', 0)
        current_price = stock_data.get('current_price', 0)
        resistance_1 = stock_data.get('support_resistance', {}).get('resistance_1', 0)

        # 基于价格动量和技术位置
        if change_percent >= 2:
            return 'bullish'
        elif change_percent >= 1:
            return 'bullish_to_neutral'
        elif resistance_1 and current_price >= resistance_1 * 0.98:
            return 'bullish_to_neutral'  # 接近阻力位，突破可能
        else:
            return 'neutral'

    def _assess_risk_level(self, scored_options: List) -> str:
        """评估风险等级"""
        if not scored_options:
            return 'high'

        # Buy Call策略风险相对可控（最大损失是期权费），但要考虑成本
        best_option = scored_options[0]
        cost_pct = best_option.get('mid_price', 0) / best_option.get('strike', 1) * 100
        moneyness = best_option.get('moneyness_pct', 0)

        if cost_pct <= 1 and moneyness >= 0:
            return 'low'
        elif cost_pct <= 3 and moneyness >= -5:
            return 'moderate'
        else:
            return 'high'

    def _generate_recommendations(self, scored_options: List, current_price: float,
                                 stock_data: Dict) -> List[str]:
        """生成策略建议"""
        recommendations = []

        if not scored_options:
            recommendations.append("当前市场条件不适合Buy Call策略")
            return recommendations

        best_option = scored_options[0]

        if best_option.get('score', 0) >= 70:
            recommendations.append(f"推荐买入执行价 ${best_option.get('strike')} 的看涨期权")

        # 基于市场状况给建议
        change_percent = stock_data.get('change_percent', 0)
        if change_percent >= 2:
            recommendations.append("股价上涨势头良好，适合买入看涨期权")

        resistance_1 = stock_data.get('support_resistance', {}).get('resistance_1', 0)
        if resistance_1 and current_price >= resistance_1 * 0.97:
            recommendations.append("价格接近阻力位，突破后有较大上涨空间")

        # 基于最佳期权特征给建议
        required_move = best_option.get('required_move_pct', 0)
        if required_move <= 5:
            recommendations.append("需要的价格涨幅合理，成功概率较高")
        elif required_move >= 15:
            recommendations.append("需要的价格涨幅较大，注意风险控制")

        high_score_count = len([opt for opt in scored_options if opt.get('score', 0) >= 60])
        if high_score_count >= 3:
            recommendations.append("多个期权机会可供选择，建议分散投资不同行权价")

        recommendations.append("设定合理的获利目标和止损点，控制仓位大小")

        return recommendations


# 独立测试功能
if __name__ == "__main__":
    print("🧪 Buy Call策略计分器独立测试")
    print("=" * 50)

    # 创建计分器实例
    scorer = BuyCallScorer()
    print("✅ Buy Call计分器创建成功")

    # 模拟测试数据
    mock_calls = [
        {
            'symbol': 'AAPL_2024-02-16_180_C',
            'strike': 180,
            'expiry': '2024-02-16',
            'bid': 2.8,
            'ask': 3.2,
            'volume': 250,
            'open_interest': 800,
            'implied_volatility': 0.22,
            'delta': 0.55,
            'days_to_expiry': 35
        },
        {
            'symbol': 'AAPL_2024-02-16_185_C',
            'strike': 185,
            'expiry': '2024-02-16',
            'bid': 1.5,
            'ask': 1.8,
            'volume': 180,
            'open_interest': 600,
            'implied_volatility': 0.24,
            'delta': 0.35,
            'days_to_expiry': 35
        }
    ]

    mock_options_data = {
        'success': True,
        'symbol': 'AAPL',
        'calls': mock_calls
    }

    mock_stock_data = {
        'current_price': 177.0,
        'change_percent': 1.8,
        'volatility_30d': 0.25,
        'support_resistance': {
            'resistance_1': 180.0,
            'resistance_2': 185.0,
            'support_1': 172.0,
            'support_2': 168.0,
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
            print(f"    成本: ${best.get('mid_price')}")
            print(f"    盈亏平衡: ${best.get('breakeven')}")
            print(f"    需要涨幅: {best.get('required_move_pct'):.1f}%")
            print(f"    杠杆比例: {best.get('leverage_ratio', 'N/A')}倍")
            print(f"    价值状态: {best.get('moneyness_pct'):.1f}%")

        strategy_analysis = result.get('strategy_analysis', {})
        print(f"  📊 市场前景: {strategy_analysis.get('market_outlook')}")
        print(f"  📋 策略适宜性: {strategy_analysis.get('strategy_suitability')}")
        print(f"  ⚠️  风险等级: {strategy_analysis.get('risk_level')}")

        print(f"  📝 策略建议:")
        for i, rec in enumerate(strategy_analysis.get('recommendations', [])[:3], 1):
            print(f"    {i}. {rec}")

    else:
        print(f"  ❌ 计分失败: {result.get('error')}")

    print("\n💡 策略说明:")
    print("- Buy Call适合看涨市场和突破交易")
    print("- 最大损失限定为支付的期权费")
    print("- 股价上涨越多，获利越大")
    print("- 注意时间衰减和波动率变化影响")
    print("- 选择合适的执行价和到期时间很重要")

    print("\n🎉 Buy Call策略计分器独立测试完成!")
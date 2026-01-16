"""
Buy Put 期权策略计分器
实现买入看跌期权的专门计分算法
"""

import logging
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class BuyPutScorer:
    """买入看跌期权计分器"""

    def __init__(self):
        """初始化Buy Put计分器"""
        self.strategy_name = "buy_put"
        self.weight_config = {
            'bearish_momentum': 0.25,    # 下跌动量权重
            'support_break': 0.20,       # 支撑位突破权重
            'value_efficiency': 0.20,    # 价值效率权重 (Delta/价格)
            'volatility_expansion': 0.15, # 波动率扩张权重
            'liquidity': 0.10,           # 流动性权重
            'time_value': 0.10           # 时间价值权重
        }

    def score_options(self, options_data: Dict, stock_data: Dict) -> Dict[str, Any]:
        """
        为Buy Put策略计分期权

        Args:
            options_data: 期权链数据
            stock_data: 标的股票数据

        Returns:
            计分结果
        """
        try:
            logger.info(f"开始Buy Put策略计分: {options_data.get('symbol', 'Unknown')}")

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

            # 筛选和计分期权
            scored_options = []
            for put_option in puts:
                score_result = self._score_individual_put(put_option, current_price, stock_data)
                if score_result and score_result.get('score', 0) > 0:
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
                'total_options_analyzed': len(puts),
                'qualified_options': len(scored_options),
                'recommendations': scored_options[:10],  # 返回前10个
                'strategy_analysis': strategy_analysis,
                'scoring_weights': self.weight_config
            }

        except Exception as e:
            logger.error(f"Buy Put计分失败: {e}")
            return {
                'success': False,
                'strategy': self.strategy_name,
                'error': f"计分失败: {str(e)}"
            }

    def _score_individual_put(self, put_option: Dict, current_price: float,
                             stock_data: Dict) -> Optional[Dict]:
        """计分单个看跌期权"""
        try:
            strike = put_option.get('strike', 0)
            bid = put_option.get('bid', 0)
            ask = put_option.get('ask', 0)
            volume = put_option.get('volume', 0)
            open_interest = put_option.get('open_interest', 0)
            implied_volatility = put_option.get('implied_volatility', 0)
            days_to_expiry = put_option.get('days_to_expiry', 0)
            delta = put_option.get('delta', None)

            if not all([strike, ask > 0, days_to_expiry > 0]):
                return None

            # Buy Put适合各种执行价，但重点关注平值和轻度实值
            mid_price = (bid + ask) / 2
            intrinsic_value = max(0, strike - current_price)
            time_value = mid_price - intrinsic_value
            moneyness = (strike - current_price) / current_price * 100

            # 计算各项得分
            scores = {}

            # 1. 下跌动量得分 (25%)
            scores['bearish_momentum'] = self._score_bearish_momentum(stock_data)

            # 2. 支撑位突破得分 (20%)
            scores['support_break'] = self._score_support_break(current_price, strike, stock_data)

            # 3. 价值效率得分 (20%)
            scores['value_efficiency'] = self._score_value_efficiency(delta, mid_price, moneyness)

            # 4. 波动率扩张得分 (15%)
            scores['volatility_expansion'] = self._score_volatility_expansion(
                implied_volatility, stock_data.get('volatility_30d', 0.2)
            )

            # 5. 流动性得分 (10%)
            scores['liquidity'] = self._score_liquidity(volume, open_interest, bid, ask)

            # 6. 时间价值得分 (10%)
            scores['time_value'] = self._score_time_value(time_value, mid_price, days_to_expiry)

            # 计算加权总分
            total_score = sum(
                scores[factor] * self.weight_config[factor]
                for factor in scores.keys()
            )

            # 计算盈亏平衡点
            breakeven = strike - mid_price
            max_profit = (breakeven * 100) if breakeven > 0 else 0  # 假设1份合约

            return {
                'option_symbol': put_option.get('symbol', f"PUT_{strike}_{put_option.get('expiry')}"),
                'strike': strike,
                'expiry': put_option.get('expiry'),
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
                'max_loss': round(mid_price * 100, 0),  # 假设1份合约
                'max_profit_potential': 'unlimited' if breakeven > 0 else 'limited',
                'profit_potential': round(max_profit, 0),
                'strategy_notes': self._generate_put_notes(current_price, strike, moneyness, time_value, days_to_expiry)
            }

        except Exception as e:
            logger.error(f"单个期权计分失败: {e}")
            return None

    def _score_bearish_momentum(self, stock_data: Dict) -> float:
        """计分下跌动量"""
        try:
            change_percent = stock_data.get('change_percent', 0)

            # 基于当日变化
            momentum_score = 50  # 基础分

            if change_percent <= -3:
                momentum_score = 100  # 强烈下跌信号
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

            # 基于52周位置
            high_52w = stock_data.get('support_resistance', {}).get('high_52w', 0)
            low_52w = stock_data.get('support_resistance', {}).get('low_52w', 0)
            current_price = stock_data.get('current_price', 0)

            if high_52w and low_52w and current_price:
                position_in_range = (current_price - low_52w) / (high_52w - low_52w) * 100
                if position_in_range <= 20:
                    momentum_score += 15  # 接近52周低点
                elif position_in_range <= 40:
                    momentum_score += 10
                elif position_in_range >= 80:
                    momentum_score -= 10  # 接近高点，不利于买Put

            return min(100, momentum_score)

        except Exception as e:
            logger.error(f"下跌动量评估失败: {e}")
            return 50

    def _score_support_break(self, current_price: float, strike: float, stock_data: Dict) -> float:
        """计分支撑位突破潜力"""
        try:
            support_resistance = stock_data.get('support_resistance', {})
            support_1 = support_resistance.get('support_1', 0)
            support_2 = support_resistance.get('support_2', 0)

            score = 50  # 基础分

            # 当前价格相对支撑位的位置
            if support_1:
                distance_to_s1 = (current_price - support_1) / current_price * 100
                if distance_to_s1 <= 3:
                    score += 30  # 非常接近支撑位
                elif distance_to_s1 <= 6:
                    score += 20
                elif distance_to_s1 <= 10:
                    score += 10

            # 执行价相对支撑位的位置
            if support_1 and strike <= support_1:
                score += 20  # 执行价在支撑位下方，有利于突破后获利

            if support_2 and strike <= support_2:
                score += 15  # 执行价在第二支撑位下方

            # 技术分析信号
            change_percent = stock_data.get('change_percent', 0)
            if change_percent <= -2 and support_1 and current_price <= support_1 * 1.02:
                score += 25  # 下跌且接近支撑位

            return min(100, score)

        except Exception as e:
            logger.error(f"支撑位突破评估失败: {e}")
            return 50

    def _score_value_efficiency(self, delta: Optional[float], mid_price: float, moneyness: float) -> float:
        """计分价值效率 (Delta/价格比率)"""
        try:
            if not delta or mid_price <= 0:
                return 40

            # Delta应该是负值（看跌期权）
            if delta > 0:
                return 20

            # 计算效率比率
            efficiency = abs(delta) / mid_price

            # 平值和轻度虚值期权通常效率较高
            base_score = 50

            # 基于效率比率评分
            if efficiency >= 0.5:
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
            elif moneyness < -10:
                base_score -= 10  # 深度虚值减分
            elif moneyness > 10:
                base_score -= 5   # 深度实值略减分

            return min(100, base_score)

        except Exception as e:
            logger.error(f"价值效率评估失败: {e}")
            return 50

    def _score_volatility_expansion(self, implied_vol: float, historical_vol: float) -> float:
        """计分波动率扩张潜力"""
        try:
            if historical_vol <= 0:
                return 50

            vol_ratio = implied_vol / historical_vol
            vol_percentile = self._estimate_vol_percentile(implied_vol)

            score = 50

            # 低隐含波动率有利于买入期权
            if vol_ratio <= 0.8:
                score += 30  # 隐含波动率较低
            elif vol_ratio <= 0.9:
                score += 20
            elif vol_ratio <= 1.0:
                score += 10
            elif vol_ratio <= 1.2:
                score -= 5
            else:
                score -= 15  # 隐含波动率过高

            # 基于波动率历史位置
            if vol_percentile <= 20:
                score += 25  # 低波动率环境
            elif vol_percentile <= 40:
                score += 15
            elif vol_percentile >= 80:
                score -= 20  # 高波动率环境

            return min(100, max(0, score))

        except Exception as e:
            logger.error(f"波动率扩张评估失败: {e}")
            return 50

    def _estimate_vol_percentile(self, implied_vol: float) -> float:
        """估算波动率历史位置（简化实现）"""
        # 简化的波动率分位数估算
        if implied_vol <= 0.15:
            return 10
        elif implied_vol <= 0.20:
            return 25
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
        if bid_ask_spread_pct <= 8:
            spread_score = 30
        elif bid_ask_spread_pct <= 15:
            spread_score = 20
        elif bid_ask_spread_pct <= 25:
            spread_score = 10
        else:
            spread_score = max(0, 10 - (bid_ask_spread_pct - 25) / 3)

        return volume_score + oi_score + spread_score

    def _score_time_value(self, time_value: float, mid_price: float, days_to_expiry: int) -> float:
        """计分时间价值合理性"""
        try:
            if mid_price <= 0:
                return 40

            time_value_ratio = time_value / mid_price

            score = 50

            # 时间价值比例评估
            if 0.3 <= time_value_ratio <= 0.7:
                score += 30  # 理想的时间价值比例
            elif 0.2 <= time_value_ratio < 0.3:
                score += 20
            elif 0.7 < time_value_ratio <= 0.8:
                score += 15
            elif time_value_ratio > 0.9:
                score -= 20  # 时间价值过高
            elif time_value_ratio < 0.1:
                score += 10   # 低时间价值可能合适

            # 基于到期时间调整
            if days_to_expiry <= 7:
                score -= 15  # 太短，时间衰减快
            elif days_to_expiry <= 30:
                score += 10
            elif days_to_expiry <= 60:
                score += 15
            elif days_to_expiry <= 90:
                score += 5
            else:
                score -= 10  # 太长，时间价值高

            return min(100, max(0, score))

        except Exception as e:
            logger.error(f"时间价值评估失败: {e}")
            return 50

    def _generate_put_notes(self, current_price: float, strike: float,
                           moneyness: float, time_value: float, days_to_expiry: int) -> List[str]:
        """生成看跌期权策略提示"""
        notes = []

        if moneyness >= 5:
            notes.append("实值期权，内在价值较高")
        elif moneyness >= -5:
            notes.append("平值期权，价格敏感度适中")
        else:
            notes.append("虚值期权，杠杆效应明显")

        if time_value / (strike * 0.01) <= 2:  # 简化的时间价值评估
            notes.append("时间价值合理")
        else:
            notes.append("时间价值偏高，注意时间衰减")

        if days_to_expiry <= 15:
            notes.append("临近到期，需要快速走势")
        elif days_to_expiry >= 60:
            notes.append("到期时间充足，适合趋势交易")

        notes.append("适合看跌市场或对冲策略")

        return notes

    def _generate_strategy_analysis(self, scored_options: List, current_price: float,
                                   stock_data: Dict) -> Dict[str, Any]:
        """生成策略分析摘要"""
        if not scored_options:
            return {
                'market_outlook': 'neutral',
                'strategy_suitability': 'poor',
                'risk_level': 'high',
                'recommendations': ['当前市场条件下无合适的Buy Put机会']
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
                'score': best_option.get('score'),
                'days_to_expiry': best_option.get('days_to_expiry')
            },
            'recommendations': self._generate_recommendations(scored_options, current_price, stock_data)
        }

        return analysis

    def _assess_market_outlook(self, stock_data: Dict) -> str:
        """评估市场前景"""
        change_percent = stock_data.get('change_percent', 0)

        # 基于价格动量和技术位置
        current_price = stock_data.get('current_price', 0)
        support_1 = stock_data.get('support_resistance', {}).get('support_1', 0)

        if change_percent <= -2:
            return 'bearish'
        elif change_percent <= -1:
            return 'bearish_to_neutral'
        elif support_1 and current_price <= support_1 * 1.05:
            return 'bearish_to_neutral'
        else:
            return 'neutral'

    def _assess_risk_level(self, scored_options: List) -> str:
        """评估风险等级"""
        if not scored_options:
            return 'high'

        # Buy Put策略风险相对可控（最大损失是期权费）
        best_option = scored_options[0]
        cost_ratio = best_option.get('mid_price', 0) / best_option.get('strike', 1) * 100

        if cost_ratio <= 2:
            return 'low'
        elif cost_ratio <= 5:
            return 'moderate'
        else:
            return 'high'

    def _generate_recommendations(self, scored_options: List, current_price: float,
                                 stock_data: Dict) -> List[str]:
        """生成策略建议"""
        recommendations = []

        if not scored_options:
            recommendations.append("当前市场条件不适合Buy Put策略")
            return recommendations

        best_option = scored_options[0]

        if best_option.get('score', 0) >= 70:
            recommendations.append(f"推荐买入执行价 ${best_option.get('strike')} 的看跌期权")

        # 基于市场状况给建议
        change_percent = stock_data.get('change_percent', 0)
        if change_percent <= -2:
            recommendations.append("股价下跌趋势明显，适合买入看跌期权")

        support_1 = stock_data.get('support_resistance', {}).get('support_1', 0)
        if support_1 and current_price <= support_1 * 1.03:
            recommendations.append("价格接近关键支撑位，突破后有较大下跌空间")

        high_score_count = len([opt for opt in scored_options if opt.get('score', 0) >= 60])
        if high_score_count >= 3:
            recommendations.append("多个期权机会可供选择，建议考虑不同行权价的组合")

        recommendations.append("控制仓位大小，设定明确的止损和获利目标")

        return recommendations


# 独立测试功能
if __name__ == "__main__":
    print("🧪 Buy Put策略计分器独立测试")
    print("=" * 50)

    # 创建计分器实例
    scorer = BuyPutScorer()
    print("✅ Buy Put计分器创建成功")

    # 模拟测试数据
    mock_puts = [
        {
            'symbol': 'AAPL_2024-02-16_170_P',
            'strike': 170,
            'expiry': '2024-02-16',
            'bid': 3.2,
            'ask': 3.5,
            'volume': 180,
            'open_interest': 450,
            'implied_volatility': 0.18,
            'delta': -0.45,
            'days_to_expiry': 30
        },
        {
            'symbol': 'AAPL_2024-02-16_165_P',
            'strike': 165,
            'expiry': '2024-02-16',
            'bid': 1.8,
            'ask': 2.1,
            'volume': 120,
            'open_interest': 350,
            'implied_volatility': 0.16,
            'delta': -0.25,
            'days_to_expiry': 30
        }
    ]

    mock_options_data = {
        'success': True,
        'symbol': 'AAPL',
        'puts': mock_puts
    }

    mock_stock_data = {
        'current_price': 172.0,
        'change_percent': -2.1,
        'volatility_30d': 0.22,
        'support_resistance': {
            'resistance_1': 180.0,
            'resistance_2': 185.0,
            'support_1': 168.0,
            'support_2': 162.0,
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
            print(f"    最大损失: ${best.get('max_loss')}")
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
    print("- Buy Put适合看跌市场或对冲策略")
    print("- 最大损失限定为支付的期权费")
    print("- 股价下跌越多，获利越大")
    print("- 注意时间衰减和波动率变化影响")

    print("\n🎉 Buy Put策略计分器独立测试完成!")
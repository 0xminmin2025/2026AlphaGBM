"""
Sell Put 期权策略计分器
实现卖出看跌期权的专门计分算法
"""

import logging
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SellPutScorer:
    """卖出看跌期权计分器"""

    def __init__(self):
        """初始化Sell Put计分器"""
        self.strategy_name = "sell_put"
        self.weight_config = {
            'premium_yield': 0.25,      # 期权费收益率权重
            'safety_margin': 0.20,      # 安全边际权重
            'probability_profit': 0.20,  # 盈利概率权重
            'liquidity': 0.15,          # 流动性权重
            'time_decay': 0.10,         # 时间衰减权重
            'volatility_premium': 0.10   # 波动率溢价权重
        }

    def score_options(self, options_data: Dict, stock_data: Dict) -> Dict[str, Any]:
        """
        为Sell Put策略计分期权

        Args:
            options_data: 期权链数据
            stock_data: 标的股票数据

        Returns:
            计分结果
        """
        try:
            logger.info(f"开始Sell Put策略计分: {options_data.get('symbol', 'Unknown')}")

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
            logger.error(f"Sell Put计分失败: {e}")
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

            if not all([strike, bid > 0, days_to_expiry > 0]):
                return None

            # 只考虑虚值或平值看跌期权（适合卖出）
            # PUT期权：行权价 < 当前股价 才是虚值(OTM)，才适合卖出
            if strike > current_price * 1.02:  # 实值超过2%，跳过
                return None

            # 基础计分指标
            mid_price = (bid + ask) / 2

            # 对于 Sell Put，只计算时间价值部分的收益（不含内在价值）
            # 内在价值 = max(0, strike - current_price)（对于ITM put）
            # 时间价值 = mid_price - 内在价值
            intrinsic_value = max(0, strike - current_price)
            time_value = max(0, mid_price - intrinsic_value)

            # 收益率应该基于时间价值，而非总权利金
            # 因为卖出 ITM put 的内在价值部分不是"收益"
            if time_value <= 0:
                return None  # 没有时间价值的期权不适合卖出

            # 单次收益率 = 时间价值 / 被指派后的持仓成本(行权价)
            premium_yield = (time_value / strike) * 100
            safety_margin = ((current_price - strike) / current_price) * 100  # 安全边际%

            # 年化收益率计算
            annualized_return = (premium_yield / days_to_expiry) * 365

            # 计算各项得分
            scores = {}

            # 1. 期权费收益率得分 (25%)
            scores['premium_yield'] = self._score_premium_yield(premium_yield, days_to_expiry)

            # 2. 安全边际得分 (20%)
            scores['safety_margin'] = self._score_safety_margin(safety_margin)

            # 3. 盈利概率得分 (20%)
            scores['probability_profit'] = self._score_profit_probability(
                current_price, strike, implied_volatility, days_to_expiry
            )

            # 4. 流动性得分 (15%)
            scores['liquidity'] = self._score_liquidity(volume, open_interest, bid, ask)

            # 5. 时间衰减得分 (10%)
            scores['time_decay'] = self._score_time_decay(days_to_expiry)

            # 6. 波动率溢价得分 (10%)
            scores['volatility_premium'] = self._score_volatility_premium(
                implied_volatility, stock_data.get('volatility_30d', 0.2)
            )

            # 计算加权总分
            total_score = sum(
                scores[factor] * self.weight_config[factor]
                for factor in scores.keys()
            )

            return {
                'option_symbol': put_option.get('symbol', f"PUT_{strike}_{put_option.get('expiry')}"),
                'strike': strike,
                'expiry': put_option.get('expiry'),
                'days_to_expiry': days_to_expiry,
                'bid': bid,
                'ask': ask,
                'mid_price': round(mid_price, 2),
                'time_value': round(time_value, 2),  # 时间价值
                'intrinsic_value': round(intrinsic_value, 2),  # 内在价值
                'premium_yield': round(premium_yield, 2),  # 单次收益率% (基于时间价值)
                'annualized_return': round(annualized_return, 2),  # 年化收益率
                'is_short_term': days_to_expiry <= 7,  # 是否短期期权
                'safety_margin': round(safety_margin, 2),
                'implied_volatility': round(implied_volatility * 100, 1),
                'volume': volume,
                'open_interest': open_interest,
                'score': round(total_score, 1),
                'score_breakdown': {k: round(v, 1) for k, v in scores.items()},
                'assignment_risk': self._calculate_assignment_risk(current_price, strike),
                'max_profit': round(time_value * 100, 0),  # 最大收益是时间价值部分
                'breakeven': round(strike - mid_price, 2),
                'strategy_notes': self._generate_put_notes(current_price, strike, premium_yield, days_to_expiry)
            }

        except Exception as e:
            logger.error(f"单个期权计分失败: {e}")
            return None

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
                                 implied_vol: float, days_to_expiry: int) -> float:
        """计分盈利概率（期权到期时价值为0的概率）"""
        try:
            # 使用布莱克-肖尔斯模型估算概率
            from scipy.stats import norm
            import math

            if implied_vol <= 0 or days_to_expiry <= 0:
                return 50

            # 计算期权到期时股价低于执行价的概率
            t = days_to_expiry / 365
            d1 = (math.log(current_price / strike) + (0.05 + 0.5 * implied_vol ** 2) * t) / (implied_vol * math.sqrt(t))
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
                                   stock_data: Dict) -> Dict[str, Any]:
        """生成策略分析摘要"""
        if not scored_options:
            return {
                'market_outlook': 'neutral',
                'strategy_suitability': 'poor',
                'risk_level': 'high',
                'recommendations': ['当前市场条件下无合适的Sell Put机会']
            }

        # 分析最佳期权
        best_option = scored_options[0]
        avg_score = np.mean([opt.get('score', 0) for opt in scored_options[:5]])

        analysis = {
            'market_outlook': self._assess_market_outlook(scored_options, stock_data),
            'strategy_suitability': 'excellent' if avg_score >= 80 else 'good' if avg_score >= 60 else 'moderate',
            'risk_level': self._assess_risk_level(scored_options),
            'best_opportunity': {
                'strike': best_option.get('strike'),
                'premium_yield': best_option.get('premium_yield'),
                'score': best_option.get('score'),
                'days_to_expiry': best_option.get('days_to_expiry')
            },
            'recommendations': self._generate_recommendations(scored_options, current_price)
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

    def _generate_recommendations(self, scored_options: List, current_price: float) -> List[str]:
        """生成策略建议"""
        recommendations = []

        if not scored_options:
            recommendations.append("当前无合适的Sell Put机会，建议等待更好时机")
            return recommendations

        best_option = scored_options[0]

        if best_option.get('score', 0) >= 80:
            recommendations.append(f"推荐卖出执行价 ${best_option.get('strike')} 的看跌期权")

        if best_option.get('premium_yield', 0) >= 2:
            recommendations.append("期权费收益率理想，适合收取权利金策略")

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
"""
VRP (Volatility Risk Premium) 计算器
分析隐含波动率与实际波动率的差异，识别期权定价偏差
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import math

logger = logging.getLogger(__name__)


class VRPCalculator:
    """波动率风险溢价计算器"""

    def __init__(self):
        """初始化VRP计算器"""
        self.historical_lookback = 30  # 历史波动率回看天数
        self.vrp_thresholds = {
            'high_premium': 0.15,      # 高溢价阈值 (15%)
            'moderate_premium': 0.05,   # 中等溢价阈值 (5%)
            'low_premium': -0.05,      # 低溢价阈值 (-5%)
            'negative_premium': -0.15   # 负溢价阈值 (-15%)
        }

    def calculate(self, symbol: str, options_data: Dict, stock_data: Dict) -> Dict[str, Any]:
        """
        计算VRP分析

        Args:
            symbol: 股票代码
            options_data: 期权链数据
            stock_data: 股票历史数据

        Returns:
            VRP分析结果
        """
        try:
            logger.info(f"开始VRP计算: {symbol}")

            if not options_data.get('success') or not stock_data.get('success', True):
                return {
                    'success': False,
                    'error': '数据无效'
                }

            # 1. 计算历史波动率
            historical_volatility = self._calculate_historical_volatility(stock_data)

            # 2. 计算隐含波动率指标
            iv_metrics = self._calculate_implied_volatility_metrics(options_data)

            # 3. 计算VRP指标
            vrp_analysis = self._calculate_vrp_metrics(iv_metrics, historical_volatility)

            # 4. 生成VRP等级和建议
            vrp_level, recommendations = self._assess_vrp_level(vrp_analysis)

            # 5. 计算期权策略建议
            strategy_suggestions = self._generate_strategy_suggestions(vrp_analysis, vrp_level)

            return {
                'success': True,
                'symbol': symbol,
                'analysis_time': datetime.now().isoformat(),
                'historical_volatility': historical_volatility,
                'implied_volatility_metrics': iv_metrics,
                'vrp_analysis': vrp_analysis,
                'vrp_level': vrp_level,
                'recommendations': recommendations,
                'strategy_suggestions': strategy_suggestions,
                'market_regime': self._identify_market_regime(vrp_analysis, stock_data)
            }

        except Exception as e:
            logger.error(f"VRP计算失败: {e}")
            return {
                'success': False,
                'error': f"VRP计算失败: {str(e)}"
            }

    def _calculate_historical_volatility(self, stock_data: Dict) -> Dict[str, float]:
        """计算历史波动率"""
        try:
            # 获取历史价格数据
            history = stock_data.get('history', {})

            if not history or 'Close' not in history:
                # 如果没有详细历史数据，使用简化计算
                return {
                    'volatility_30d': stock_data.get('volatility_30d', 0.2),
                    'volatility_10d': stock_data.get('volatility_30d', 0.2) * 1.1,  # 估算
                    'volatility_5d': stock_data.get('volatility_30d', 0.2) * 1.3,   # 估算
                    'volatility_percentile': 50.0,  # 默认中位数
                    'data_quality': 'estimated'
                }

            # 转换为DataFrame进行计算
            if isinstance(history['Close'], dict):
                close_prices = pd.Series(history['Close'])
            else:
                close_prices = pd.Series(history['Close'])

            if len(close_prices) < 10:
                # 数据不足，返回估算值
                base_vol = 0.2
                return {
                    'volatility_30d': base_vol,
                    'volatility_10d': base_vol * 1.1,
                    'volatility_5d': base_vol * 1.3,
                    'volatility_percentile': 50.0,
                    'data_quality': 'insufficient'
                }

            # 计算日收益率
            returns = close_prices.pct_change().dropna()

            # 计算不同周期的波动率
            vol_30d = self._calculate_period_volatility(returns, 30)
            vol_10d = self._calculate_period_volatility(returns, 10)
            vol_5d = self._calculate_period_volatility(returns, 5)

            # 计算波动率分位数
            vol_percentile = self._calculate_volatility_percentile(returns)

            return {
                'volatility_30d': vol_30d,
                'volatility_10d': vol_10d,
                'volatility_5d': vol_5d,
                'volatility_percentile': vol_percentile,
                'data_quality': 'calculated'
            }

        except Exception as e:
            logger.error(f"历史波动率计算失败: {e}")
            # 返回默认值
            base_vol = 0.25
            return {
                'volatility_30d': base_vol,
                'volatility_10d': base_vol * 1.1,
                'volatility_5d': base_vol * 1.3,
                'volatility_percentile': 50.0,
                'data_quality': 'error_fallback'
            }

    def _calculate_period_volatility(self, returns: pd.Series, period: int) -> float:
        """计算指定周期的波动率"""
        if len(returns) < period:
            return returns.std() * math.sqrt(252)  # 使用全部数据

        recent_returns = returns.tail(period)
        return recent_returns.std() * math.sqrt(252)  # 年化波动率

    def _calculate_volatility_percentile(self, returns: pd.Series) -> float:
        """计算当前波动率在历史中的分位数"""
        try:
            if len(returns) < 60:  # 数据不足
                return 50.0

            # 使用滚动窗口计算历史波动率
            rolling_vol = returns.rolling(window=20).std() * math.sqrt(252)
            rolling_vol = rolling_vol.dropna()

            if len(rolling_vol) < 10:
                return 50.0

            current_vol = rolling_vol.iloc[-1]
            percentile = (rolling_vol <= current_vol).sum() / len(rolling_vol) * 100

            return float(percentile)

        except Exception as e:
            logger.error(f"波动率分位数计算失败: {e}")
            return 50.0

    def _calculate_implied_volatility_metrics(self, options_data: Dict) -> Dict[str, Any]:
        """计算隐含波动率指标"""
        try:
            calls = options_data.get('calls', [])
            puts = options_data.get('puts', [])

            all_options = calls + puts

            if not all_options:
                return {
                    'average_iv': 0.2,
                    'iv_weighted_by_oi': 0.2,
                    'iv_range': {'min': 0.15, 'max': 0.25},
                    'call_put_iv_skew': 0.0,
                    'atm_iv': 0.2,
                    'data_quality': 'no_data'
                }

            # 提取有效的IV数据
            valid_ivs = []
            valid_weights = []
            call_ivs = []
            put_ivs = []

            current_price = options_data.get('current_price', 100)

            atm_iv = None
            min_strike_diff = float('inf')

            for option in all_options:
                iv = option.get('implied_volatility', 0)
                oi = option.get('open_interest', 0)
                strike = option.get('strike', 0)
                option_type = option.get('option_type', '')

                if iv > 0 and strike > 0:
                    valid_ivs.append(iv)
                    valid_weights.append(max(1, oi))  # 最小权重为1

                    # 分别收集看涨和看跌IV
                    if 'call' in option_type.lower() or option in calls:
                        call_ivs.append(iv)
                    else:
                        put_ivs.append(iv)

                    # 寻找最接近平值的期权
                    strike_diff = abs(strike - current_price)
                    if strike_diff < min_strike_diff:
                        min_strike_diff = strike_diff
                        atm_iv = iv

            if not valid_ivs:
                return {
                    'average_iv': 0.2,
                    'iv_weighted_by_oi': 0.2,
                    'iv_range': {'min': 0.15, 'max': 0.25},
                    'call_put_iv_skew': 0.0,
                    'atm_iv': 0.2,
                    'data_quality': 'invalid_data'
                }

            # 计算各种IV指标
            avg_iv = np.mean(valid_ivs)
            weighted_iv = np.average(valid_ivs, weights=valid_weights)
            iv_min = min(valid_ivs)
            iv_max = max(valid_ivs)

            # 计算Call-Put IV偏斜
            call_put_skew = 0.0
            if call_ivs and put_ivs:
                call_put_skew = np.mean(call_ivs) - np.mean(put_ivs)

            return {
                'average_iv': float(avg_iv),
                'iv_weighted_by_oi': float(weighted_iv),
                'iv_range': {'min': float(iv_min), 'max': float(iv_max)},
                'call_put_iv_skew': float(call_put_skew),
                'atm_iv': float(atm_iv) if atm_iv else float(avg_iv),
                'data_quality': 'calculated',
                'sample_size': len(valid_ivs)
            }

        except Exception as e:
            logger.error(f"隐含波动率指标计算失败: {e}")
            return {
                'average_iv': 0.2,
                'iv_weighted_by_oi': 0.2,
                'iv_range': {'min': 0.15, 'max': 0.25},
                'call_put_iv_skew': 0.0,
                'atm_iv': 0.2,
                'data_quality': 'error_fallback'
            }

    def _calculate_vrp_metrics(self, iv_metrics: Dict, hv_metrics: Dict) -> Dict[str, Any]:
        """计算VRP指标"""
        try:
            # 获取关键波动率数据
            implied_vol = iv_metrics.get('iv_weighted_by_oi', 0.2)
            historical_vol = hv_metrics.get('volatility_30d', 0.2)
            atm_iv = iv_metrics.get('atm_iv', implied_vol)

            # 计算VRP (隐含波动率 - 历史波动率)
            vrp_absolute = implied_vol - historical_vol
            vrp_relative = (implied_vol - historical_vol) / historical_vol if historical_vol > 0 else 0

            # ATM VRP
            atm_vrp = atm_iv - historical_vol
            atm_vrp_relative = (atm_iv - historical_vol) / historical_vol if historical_vol > 0 else 0

            # 计算波动率比率
            vol_ratio = implied_vol / historical_vol if historical_vol > 0 else 1.0

            # 计算IV Rank (简化版本)
            iv_min = iv_metrics.get('iv_range', {}).get('min', 0.15)
            iv_max = iv_metrics.get('iv_range', {}).get('max', 0.25)
            if iv_max > iv_min:
                iv_rank = (implied_vol - iv_min) / (iv_max - iv_min) * 100
            else:
                iv_rank = 50.0

            # 计算VRP信号强度
            signal_strength = self._calculate_vrp_signal_strength(vrp_relative)

            return {
                'vrp_absolute': float(vrp_absolute),
                'vrp_relative_pct': float(vrp_relative * 100),
                'atm_vrp': float(atm_vrp),
                'atm_vrp_relative_pct': float(atm_vrp_relative * 100),
                'volatility_ratio': float(vol_ratio),
                'iv_rank': float(iv_rank),
                'signal_strength': signal_strength,
                'implied_vol': float(implied_vol),
                'historical_vol': float(historical_vol),
                'vol_percentile': hv_metrics.get('volatility_percentile', 50.0)
            }

        except Exception as e:
            logger.error(f"VRP指标计算失败: {e}")
            return {
                'vrp_absolute': 0.0,
                'vrp_relative_pct': 0.0,
                'atm_vrp': 0.0,
                'atm_vrp_relative_pct': 0.0,
                'volatility_ratio': 1.0,
                'iv_rank': 50.0,
                'signal_strength': 'neutral',
                'implied_vol': 0.2,
                'historical_vol': 0.2,
                'vol_percentile': 50.0
            }

    def _calculate_vrp_signal_strength(self, vrp_relative: float) -> str:
        """计算VRP信号强度"""
        if vrp_relative >= 0.20:
            return 'very_strong_positive'  # 非常强的正溢价
        elif vrp_relative >= 0.10:
            return 'strong_positive'       # 强正溢价
        elif vrp_relative >= 0.05:
            return 'moderate_positive'     # 中等正溢价
        elif vrp_relative >= -0.05:
            return 'neutral'              # 中性
        elif vrp_relative >= -0.10:
            return 'moderate_negative'     # 中等负溢价
        elif vrp_relative >= -0.20:
            return 'strong_negative'       # 强负溢价
        else:
            return 'very_strong_negative'  # 非常强的负溢价

    def _assess_vrp_level(self, vrp_analysis: Dict) -> Tuple[str, List[str]]:
        """评估VRP等级并生成建议"""
        vrp_relative = vrp_analysis.get('vrp_relative_pct', 0) / 100
        signal_strength = vrp_analysis.get('signal_strength', 'neutral')
        iv_rank = vrp_analysis.get('iv_rank', 50)

        recommendations = []

        # 确定VRP等级
        if vrp_relative >= 0.15:
            level = 'very_high'
            recommendations.extend([
                "隐含波动率显著高于历史波动率",
                "期权定价偏贵，适合卖方策略",
                "考虑卖出跨式或宽跨式策略"
            ])
        elif vrp_relative >= 0.05:
            level = 'high'
            recommendations.extend([
                "隐含波动率高于历史波动率",
                "期权费相对较贵，偏向卖方",
                "可考虑卖出期权收取时间价值"
            ])
        elif vrp_relative >= -0.05:
            level = 'normal'
            recommendations.extend([
                "隐含波动率接近历史波动率",
                "期权定价相对合理",
                "根据方向性判断选择策略"
            ])
        elif vrp_relative >= -0.15:
            level = 'low'
            recommendations.extend([
                "隐含波动率低于历史波动率",
                "期权费相对便宜，偏向买方",
                "可考虑买入期权进行方向性交易"
            ])
        else:
            level = 'very_low'
            recommendations.extend([
                "隐含波动率显著低于历史波动率",
                "期权定价偏便宜，适合买方策略",
                "考虑买入跨式或保护性策略"
            ])

        # 基于IV Rank添加建议
        if iv_rank >= 80:
            recommendations.append("IV Rank较高，波动率可能回归")
        elif iv_rank <= 20:
            recommendations.append("IV Rank较低，波动率可能扩张")

        return level, recommendations

    def _generate_strategy_suggestions(self, vrp_analysis: Dict, vrp_level: str) -> List[Dict]:
        """根据VRP分析生成策略建议"""
        suggestions = []

        vrp_relative = vrp_analysis.get('vrp_relative_pct', 0) / 100
        iv_rank = vrp_analysis.get('iv_rank', 50)

        if vrp_level in ['very_high', 'high']:
            # 高VRP，偏向卖方策略
            suggestions.extend([
                {
                    'strategy': 'sell_put',
                    'rationale': '高VRP环境下收取期权费',
                    'confidence': 'high' if vrp_level == 'very_high' else 'medium',
                    'risk_level': 'medium'
                },
                {
                    'strategy': 'sell_call',
                    'rationale': '利用高隐含波动率收取时间价值',
                    'confidence': 'medium',
                    'risk_level': 'medium'
                }
            ])

            if vrp_level == 'very_high':
                suggestions.append({
                    'strategy': 'iron_condor',
                    'rationale': '极高VRP适合做空波动率策略',
                    'confidence': 'high',
                    'risk_level': 'medium'
                })

        elif vrp_level in ['very_low', 'low']:
            # 低VRP，偏向买方策略
            suggestions.extend([
                {
                    'strategy': 'buy_call',
                    'rationale': '低VRP环境下买入期权成本较低',
                    'confidence': 'high' if vrp_level == 'very_low' else 'medium',
                    'risk_level': 'medium'
                },
                {
                    'strategy': 'buy_put',
                    'rationale': '便宜的期权费提供保护或方向性交易',
                    'confidence': 'medium',
                    'risk_level': 'medium'
                }
            ])

            if vrp_level == 'very_low':
                suggestions.append({
                    'strategy': 'long_straddle',
                    'rationale': '极低VRP适合做多波动率策略',
                    'confidence': 'medium',
                    'risk_level': 'high'
                })

        else:
            # 中性VRP
            suggestions.extend([
                {
                    'strategy': 'directional_bias',
                    'rationale': '中性VRP环境下重点关注方向性判断',
                    'confidence': 'medium',
                    'risk_level': 'varies'
                }
            ])

        return suggestions

    def _identify_market_regime(self, vrp_analysis: Dict, stock_data: Dict) -> Dict[str, Any]:
        """识别市场波动率状态"""
        vol_percentile = vrp_analysis.get('vol_percentile', 50)
        iv_rank = vrp_analysis.get('iv_rank', 50)
        vrp_relative = vrp_analysis.get('vrp_relative_pct', 0)

        # 确定波动率状态
        if vol_percentile >= 80:
            vol_regime = 'high_volatility'
        elif vol_percentile >= 60:
            vol_regime = 'elevated_volatility'
        elif vol_percentile <= 20:
            vol_regime = 'low_volatility'
        elif vol_percentile <= 40:
            vol_regime = 'below_average_volatility'
        else:
            vol_regime = 'normal_volatility'

        # 确定期权定价状态
        if abs(vrp_relative) <= 5:
            pricing_regime = 'fairly_priced'
        elif vrp_relative > 5:
            pricing_regime = 'overpriced'
        else:
            pricing_regime = 'underpriced'

        return {
            'volatility_regime': vol_regime,
            'option_pricing_regime': pricing_regime,
            'vol_percentile': vol_percentile,
            'iv_rank': iv_rank,
            'market_stress_level': self._assess_market_stress(vol_percentile, stock_data)
        }

    def _assess_market_stress(self, vol_percentile: float, stock_data: Dict) -> str:
        """评估市场压力水平"""
        change_percent = abs(stock_data.get('change_percent', 0))

        if vol_percentile >= 90 and change_percent >= 3:
            return 'high_stress'
        elif vol_percentile >= 70 or change_percent >= 2:
            return 'moderate_stress'
        elif vol_percentile <= 30 and change_percent <= 1:
            return 'low_stress'
        else:
            return 'normal_stress'


# 独立测试功能
if __name__ == "__main__":
    print("🧪 VRP计算器独立测试")
    print("=" * 50)

    # 创建VRP计算器实例
    calculator = VRPCalculator()
    print("✅ VRP计算器创建成功")

    # 模拟测试数据
    mock_options_data = {
        'success': True,
        'symbol': 'AAPL',
        'current_price': 175.0,
        'calls': [
            {'implied_volatility': 0.25, 'open_interest': 500, 'strike': 175, 'option_type': 'call'},
            {'implied_volatility': 0.27, 'open_interest': 300, 'strike': 180, 'option_type': 'call'},
        ],
        'puts': [
            {'implied_volatility': 0.26, 'open_interest': 400, 'strike': 175, 'option_type': 'put'},
            {'implied_volatility': 0.28, 'open_interest': 250, 'strike': 170, 'option_type': 'put'},
        ]
    }

    # 模拟生成历史价格数据
    mock_stock_data = {
        'current_price': 175.0,
        'change_percent': -1.2,
        'volatility_30d': 0.20,  # 20% 年化历史波动率
        'history': {
            'Close': {i: 175 + np.random.normal(0, 3) for i in range(60)}  # 60天历史数据
        }
    }

    print(f"\n📊 测试VRP计算...")
    result = calculator.calculate('AAPL', mock_options_data, mock_stock_data)

    if result.get('success'):
        print(f"  ✅ VRP计算成功")

        vrp_analysis = result.get('vrp_analysis', {})
        print(f"  📈 VRP分析:")
        print(f"    隐含波动率: {vrp_analysis.get('implied_vol', 0) * 100:.1f}%")
        print(f"    历史波动率: {vrp_analysis.get('historical_vol', 0) * 100:.1f}%")
        print(f"    VRP (绝对值): {vrp_analysis.get('vrp_absolute', 0) * 100:.1f}%")
        print(f"    VRP (相对值): {vrp_analysis.get('vrp_relative_pct', 0):.1f}%")
        print(f"    IV Rank: {vrp_analysis.get('iv_rank', 0):.1f}")
        print(f"    信号强度: {vrp_analysis.get('signal_strength', 'unknown')}")

        print(f"  🎯 VRP等级: {result.get('vrp_level')}")

        market_regime = result.get('market_regime', {})
        print(f"  🌊 市场状态:")
        print(f"    波动率状态: {market_regime.get('volatility_regime')}")
        print(f"    期权定价: {market_regime.get('option_pricing_regime')}")
        print(f"    市场压力: {market_regime.get('market_stress_level')}")

        print(f"  📝 主要建议:")
        for i, rec in enumerate(result.get('recommendations', [])[:3], 1):
            print(f"    {i}. {rec}")

        print(f"  🔧 策略建议:")
        for suggestion in result.get('strategy_suggestions', [])[:2]:
            strategy = suggestion.get('strategy')
            rationale = suggestion.get('rationale')
            confidence = suggestion.get('confidence')
            print(f"    {strategy}: {rationale} (信心: {confidence})")

    else:
        print(f"  ❌ VRP计算失败: {result.get('error')}")

    print("\n💡 VRP说明:")
    print("- VRP > 0: 隐含波动率高于历史波动率，适合卖方策略")
    print("- VRP < 0: 隐含波动率低于历史波动率，适合买方策略")
    print("- IV Rank: 当前IV在历史范围内的位置")
    print("- 结合市场状态制定最佳期权策略")

    print("\n🎉 VRP计算器独立测试完成!")
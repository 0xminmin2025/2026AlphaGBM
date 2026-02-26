"""
Risk Adjuster 风险调整器
分析期权组合风险并提供仓位大小和风险管理建议
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import math

from ..option_market_config import OptionMarketConfig, US_OPTIONS_CONFIG

logger = logging.getLogger(__name__)


class RiskAdjuster:
    """期权风险调整器"""

    def __init__(self):
        """初始化风险调整器"""
        self.risk_tolerance_configs = {
            'conservative': {
                'max_portfolio_risk': 0.02,     # 最大组合风险2%
                'max_single_position': 0.01,   # 单笔交易最大风险1%
                'max_correlation': 0.6,        # 最大相关性60%
                'preferred_strategies': ['sell_put', 'covered_call'],
                'volatility_multiplier': 0.8
            },
            'moderate': {
                'max_portfolio_risk': 0.05,     # 最大组合风险5%
                'max_single_position': 0.025,   # 单笔交易最大风险2.5%
                'max_correlation': 0.8,
                'preferred_strategies': ['sell_put', 'sell_call', 'buy_put', 'buy_call'],
                'volatility_multiplier': 1.0
            },
            'aggressive': {
                'max_portfolio_risk': 0.10,     # 最大组合风险10%
                'max_single_position': 0.05,    # 单笔交易最大风险5%
                'max_correlation': 1.0,
                'preferred_strategies': ['buy_call', 'buy_put', 'straddle', 'strangle'],
                'volatility_multiplier': 1.3
            }
        }

    def analyze_portfolio_risk(self, strategy_analysis: Dict, stock_data: Dict) -> Dict[str, Any]:
        """
        分析组合风险

        Args:
            strategy_analysis: 策略分析结果
            stock_data: 股票数据

        Returns:
            风险分析结果
        """
        try:
            logger.info("开始组合风险分析")

            if not strategy_analysis:
                return {
                    'success': False,
                    'error': '无策略分析数据'
                }

            # 1. 分析各策略风险
            strategy_risks = self._analyze_strategy_risks(strategy_analysis, stock_data)

            # 2. 计算组合风险指标
            portfolio_risk = self._calculate_portfolio_risk(strategy_risks, stock_data)

            # 3. 生成风险等级评估
            risk_assessment = self._assess_overall_risk(portfolio_risk, strategy_risks)

            # 4. 计算风险调整建议
            risk_adjustments = self._generate_risk_adjustments(risk_assessment, stock_data)

            return {
                'success': True,
                'analysis_time': datetime.now().isoformat(),
                'strategy_risks': strategy_risks,
                'portfolio_risk': portfolio_risk,
                'risk_assessment': risk_assessment,
                'risk_adjustments': risk_adjustments,
                'overall_risk': risk_assessment.get('overall_risk_level', 'medium')
            }

        except Exception as e:
            logger.error(f"组合风险分析失败: {e}")
            return {
                'success': False,
                'error': f"风险分析失败: {str(e)}"
            }

    def calculate_position_sizing(self, strategy_analysis: Dict, portfolio_value: float,
                                risk_tolerance: str = 'moderate',
                                market_config: OptionMarketConfig = None) -> Dict[str, Any]:
        """
        计算仓位大小

        Args:
            strategy_analysis: 策略分析结果
            portfolio_value: 组合总价值
            risk_tolerance: 风险承受度
            market_config: 市场配置（可选，默认 US）

        Returns:
            仓位建议
        """
        try:
            if market_config is None:
                market_config = US_OPTIONS_CONFIG

            logger.info(f"计算仓位大小，风险承受度: {risk_tolerance}, 市场: {market_config.market}")

            if risk_tolerance not in self.risk_tolerance_configs:
                risk_tolerance = 'moderate'

            config = self.risk_tolerance_configs[risk_tolerance]

            # 计算各策略的仓位建议
            position_recommendations = []

            for strategy, result in strategy_analysis.items():
                if not result.get('success') or not result.get('recommendations'):
                    continue

                # 分析最佳期权
                best_option = result['recommendations'][0]
                position_sizing = self._calculate_individual_position_size(
                    strategy, best_option, portfolio_value, config, market_config
                )

                position_recommendations.append({
                    'strategy': strategy,
                    'option_details': best_option,
                    'position_sizing': position_sizing
                })

            # 计算组合级别的调整
            portfolio_adjustments = self._calculate_portfolio_adjustments(
                position_recommendations, portfolio_value, config
            )

            return {
                'success': True,
                'risk_tolerance': risk_tolerance,
                'portfolio_value': portfolio_value,
                'position_recommendations': position_recommendations,
                'portfolio_adjustments': portfolio_adjustments,
                'total_capital_allocation': sum(
                    pos.get('position_sizing', {}).get('suggested_capital', 0)
                    for pos in position_recommendations
                ),
                'risk_metrics': self._calculate_position_risk_metrics(position_recommendations)
            }

        except Exception as e:
            logger.error(f"仓位计算失败: {e}")
            return {
                'success': False,
                'error': f"仓位计算失败: {str(e)}"
            }

    def _analyze_strategy_risks(self, strategy_analysis: Dict, stock_data: Dict) -> Dict[str, Any]:
        """分析各策略的风险特征"""
        strategy_risks = {}

        for strategy, result in strategy_analysis.items():
            if not result.get('success'):
                continue

            risk_profile = self._get_strategy_risk_profile(strategy)
            market_risk = self._calculate_market_risk(strategy, stock_data)

            recommendations = result.get('recommendations', [])
            if recommendations:
                best_option = recommendations[0]
                option_specific_risk = self._calculate_option_specific_risk(strategy, best_option)
            else:
                option_specific_risk = {'risk_score': 70}  # 默认风险分数

            strategy_risks[strategy] = {
                'base_risk_profile': risk_profile,
                'market_risk': market_risk,
                'option_specific_risk': option_specific_risk,
                'combined_risk_score': self._combine_risk_scores(
                    risk_profile['risk_score'],
                    market_risk['risk_score'],
                    option_specific_risk['risk_score']
                )
            }

        return strategy_risks

    def _get_strategy_risk_profile(self, strategy: str) -> Dict[str, Any]:
        """获取策略基础风险特征"""
        risk_profiles = {
            'sell_put': {
                'risk_score': 60,
                'max_loss': 'high',
                'profit_potential': 'limited',
                'time_decay': 'positive',
                'volatility_impact': 'negative',
                'primary_risks': ['assignment_risk', 'downside_unlimited']
            },
            'sell_call': {
                'risk_score': 70,
                'max_loss': 'unlimited',
                'profit_potential': 'limited',
                'time_decay': 'positive',
                'volatility_impact': 'negative',
                'primary_risks': ['upside_unlimited', 'early_assignment']
            },
            'buy_put': {
                'risk_score': 50,
                'max_loss': 'limited',
                'profit_potential': 'high',
                'time_decay': 'negative',
                'volatility_impact': 'positive',
                'primary_risks': ['time_decay', 'volatility_crush']
            },
            'buy_call': {
                'risk_score': 55,
                'max_loss': 'limited',
                'profit_potential': 'unlimited',
                'time_decay': 'negative',
                'volatility_impact': 'positive',
                'primary_risks': ['time_decay', 'volatility_crush']
            }
        }

        return risk_profiles.get(strategy, {
            'risk_score': 65,
            'max_loss': 'unknown',
            'profit_potential': 'unknown',
            'time_decay': 'neutral',
            'volatility_impact': 'neutral',
            'primary_risks': ['unknown']
        })

    def _calculate_market_risk(self, strategy: str, stock_data: Dict) -> Dict[str, Any]:
        """计算市场风险"""
        try:
            volatility = stock_data.get('volatility_30d', 0.2)
            change_percent = abs(stock_data.get('change_percent', 0))

            # 基础风险分数
            vol_risk = min(100, volatility * 250)  # 波动率风险
            momentum_risk = min(100, change_percent * 10)  # 动量风险

            # 根据策略调整风险权重
            if strategy in ['sell_put', 'sell_call']:
                # 卖方策略对波动率更敏感
                market_risk_score = vol_risk * 0.7 + momentum_risk * 0.3
            else:
                # 买方策略对动量更敏感
                market_risk_score = vol_risk * 0.4 + momentum_risk * 0.6

            return {
                'risk_score': min(100, market_risk_score),
                'volatility_risk': vol_risk,
                'momentum_risk': momentum_risk,
                'primary_concern': 'volatility' if vol_risk > momentum_risk else 'momentum'
            }

        except Exception as e:
            logger.error(f"市场风险计算失败: {e}")
            return {
                'risk_score': 50,
                'volatility_risk': 50,
                'momentum_risk': 50,
                'primary_concern': 'unknown'
            }

    def _calculate_option_specific_risk(self, strategy: str, option_details: Dict) -> Dict[str, Any]:
        """计算期权特定风险"""
        try:
            days_to_expiry = option_details.get('days_to_expiry', 30)
            mid_price = option_details.get('mid_price', 0)
            strike = option_details.get('strike', 0)

            # 时间风险
            time_risk = max(0, 100 - days_to_expiry * 2)  # 天数越少风险越高

            # 价格风险（基于期权费相对执行价的比例）
            if strike > 0:
                price_risk = min(100, (mid_price / strike) * 1000)
            else:
                price_risk = 50

            # 流动性风险
            volume = option_details.get('volume', 0)
            liquidity_risk = max(0, 100 - volume / 5)  # 成交量越小风险越高

            # 综合风险分数
            if strategy in ['buy_put', 'buy_call']:
                # 买方策略更关心时间衰减和流动性
                option_risk = time_risk * 0.5 + liquidity_risk * 0.3 + price_risk * 0.2
            else:
                # 卖方策略更关心价格变化和流动性
                option_risk = price_risk * 0.4 + liquidity_risk * 0.4 + time_risk * 0.2

            return {
                'risk_score': min(100, option_risk),
                'time_risk': time_risk,
                'price_risk': price_risk,
                'liquidity_risk': liquidity_risk,
                'days_to_expiry': days_to_expiry
            }

        except Exception as e:
            logger.error(f"期权特定风险计算失败: {e}")
            return {
                'risk_score': 60,
                'time_risk': 50,
                'price_risk': 50,
                'liquidity_risk': 50
            }

    def _combine_risk_scores(self, base_risk: float, market_risk: float, option_risk: float) -> float:
        """组合风险分数"""
        # 加权平均
        return base_risk * 0.4 + market_risk * 0.4 + option_risk * 0.2

    def _calculate_portfolio_risk(self, strategy_risks: Dict, stock_data: Dict) -> Dict[str, Any]:
        """计算组合级别风险"""
        if not strategy_risks:
            return {
                'overall_score': 50,
                'diversification_benefit': 0,
                'concentration_risk': 0,
                'correlation_risk': 0
            }

        # 计算平均风险
        risk_scores = [risk['combined_risk_score'] for risk in strategy_risks.values()]
        avg_risk = np.mean(risk_scores)

        # 分散化效益（策略数量越多，风险越分散）
        num_strategies = len(strategy_risks)
        diversification_benefit = min(20, num_strategies * 5)  # 最多20分的分散化效益

        # 集中度风险（如果某个策略风险特别高）
        max_risk = max(risk_scores)
        concentration_risk = max(0, max_risk - avg_risk) * 0.5

        # 相关性风险（简化计算 - 如果都是同类策略）
        sell_strategies = [s for s in strategy_risks.keys() if 'sell' in s]
        buy_strategies = [s for s in strategy_risks.keys() if 'buy' in s]

        if len(sell_strategies) >= 3 or len(buy_strategies) >= 3:
            correlation_risk = 15  # 同类策略过多
        elif len(sell_strategies) >= 2 or len(buy_strategies) >= 2:
            correlation_risk = 10
        else:
            correlation_risk = 0

        # 综合组合风险
        portfolio_risk_score = avg_risk - diversification_benefit + concentration_risk + correlation_risk

        return {
            'overall_score': max(0, min(100, portfolio_risk_score)),
            'average_strategy_risk': avg_risk,
            'diversification_benefit': diversification_benefit,
            'concentration_risk': concentration_risk,
            'correlation_risk': correlation_risk,
            'num_strategies': num_strategies
        }

    def _assess_overall_risk(self, portfolio_risk: Dict, strategy_risks: Dict) -> Dict[str, Any]:
        """评估总体风险等级"""
        overall_score = portfolio_risk.get('overall_score', 50)

        if overall_score <= 30:
            risk_level = 'low'
            risk_description = '低风险：风险可控，适合保守投资者'
        elif overall_score <= 50:
            risk_level = 'moderate'
            risk_description = '中等风险：风险适中，需要适当监控'
        elif overall_score <= 70:
            risk_level = 'high'
            risk_description = '高风险：需要密切监控和主动管理'
        else:
            risk_level = 'very_high'
            risk_description = '极高风险：建议减少仓位或重新评估策略'

        # 识别主要风险因子
        main_risk_factors = []
        if portfolio_risk.get('concentration_risk', 0) >= 10:
            main_risk_factors.append('concentration')
        if portfolio_risk.get('correlation_risk', 0) >= 10:
            main_risk_factors.append('correlation')

        # 检查策略特定风险
        for strategy, risk in strategy_risks.items():
            if risk['combined_risk_score'] >= 80:
                main_risk_factors.append(f'{strategy}_high_risk')

        return {
            'overall_risk_level': risk_level,
            'overall_risk_score': overall_score,
            'risk_description': risk_description,
            'main_risk_factors': main_risk_factors,
            'monitoring_priority': 'high' if overall_score >= 60 else 'medium' if overall_score >= 40 else 'low'
        }

    def _generate_risk_adjustments(self, risk_assessment: Dict, stock_data: Dict) -> List[Dict]:
        """生成风险调整建议"""
        adjustments = []

        risk_level = risk_assessment.get('overall_risk_level', 'moderate')
        risk_factors = risk_assessment.get('main_risk_factors', [])

        # 基于风险等级的通用建议
        if risk_level == 'very_high':
            adjustments.extend([
                {
                    'type': 'position_sizing',
                    'action': 'reduce_positions',
                    'reason': '总体风险过高',
                    'priority': 'urgent'
                },
                {
                    'type': 'monitoring',
                    'action': 'increase_monitoring_frequency',
                    'reason': '需要密切监控',
                    'priority': 'high'
                }
            ])
        elif risk_level == 'high':
            adjustments.append({
                'type': 'risk_management',
                'action': 'implement_stop_loss',
                'reason': '建议设置止损点',
                'priority': 'medium'
            })

        # 基于特定风险因子的建议
        if 'concentration' in risk_factors:
            adjustments.append({
                'type': 'diversification',
                'action': 'diversify_strategies',
                'reason': '集中度风险过高，需要分散化',
                'priority': 'high'
            })

        if 'correlation' in risk_factors:
            adjustments.append({
                'type': 'strategy_mix',
                'action': 'rebalance_strategy_types',
                'reason': '策略相关性过高',
                'priority': 'medium'
            })

        # 基于市场条件的建议
        volatility = stock_data.get('volatility_30d', 0.2)
        if volatility > 0.4:
            adjustments.append({
                'type': 'market_adaptation',
                'action': 'adjust_for_high_volatility',
                'reason': '高波动率环境需要调整策略',
                'priority': 'medium'
            })

        return adjustments

    def _calculate_individual_position_size(self, strategy: str, option_details: Dict,
                                          portfolio_value: float, risk_config: Dict,
                                          market_config: OptionMarketConfig = None) -> Dict[str, Any]:
        """计算单个仓位大小"""
        try:
            if market_config is None:
                market_config = US_OPTIONS_CONFIG
            multiplier = market_config.contract_multiplier

            max_single_position = risk_config['max_single_position']
            volatility_multiplier = risk_config['volatility_multiplier']

            # 期权价格和风险
            mid_price = option_details.get('mid_price', 0)

            # 基础仓位大小（基于最大单笔风险）
            max_capital = portfolio_value * max_single_position

            if mid_price > 0:
                max_contracts = int(max_capital / (mid_price * multiplier))
            else:
                max_contracts = 0

            # 基于策略类型调整
            if strategy in ['buy_put', 'buy_call']:
                # 买方策略风险有限，可以用足仓位
                suggested_contracts = max_contracts
                suggested_capital = suggested_contracts * mid_price * multiplier
            else:
                # 卖方策略需要考虑保证金和潜在损失
                margin_requirement = self._estimate_margin_requirement(strategy, option_details, market_config)
                available_contracts = int(max_capital / margin_requirement) if margin_requirement > 0 else 0
                suggested_contracts = min(max_contracts, available_contracts)
                suggested_capital = max_capital

            # 波动率调整
            suggested_contracts = int(suggested_contracts * volatility_multiplier)

            return {
                'max_contracts': max_contracts,
                'suggested_contracts': max(1, suggested_contracts),  # 至少1份合约
                'suggested_capital': suggested_capital,
                'capital_utilization_pct': (suggested_capital / portfolio_value) * 100,
                'risk_per_contract': mid_price * multiplier,
                'estimated_margin': margin_requirement if strategy.startswith('sell') else 0
            }

        except Exception as e:
            logger.error(f"仓位计算失败: {e}")
            return {
                'max_contracts': 1,
                'suggested_contracts': 1,
                'suggested_capital': portfolio_value * 0.02,
                'capital_utilization_pct': 2.0,
                'risk_per_contract': 1000,
                'estimated_margin': 0
            }

    def _estimate_margin_requirement(self, strategy: str, option_details: Dict,
                                     market_config: OptionMarketConfig = None) -> float:
        """估算保证金需求"""
        if not strategy.startswith('sell'):
            return 0

        if market_config is None:
            market_config = US_OPTIONS_CONFIG
        multiplier = market_config.contract_multiplier
        margin_rate = market_config.default_margin_rate

        strike = option_details.get('strike', 100)
        mid_price = option_details.get('mid_price', 1)

        if strategy == 'sell_put':
            margin = strike * multiplier * margin_rate
        elif strategy == 'sell_call':
            margin = strike * multiplier * margin_rate
        else:
            margin = strike * multiplier * margin_rate * 0.75

        # 减去收到的期权费
        return max(0, margin - mid_price * multiplier)

    def _calculate_portfolio_adjustments(self, position_recommendations: List,
                                       portfolio_value: float, risk_config: Dict) -> Dict[str, Any]:
        """计算组合级别调整"""
        if not position_recommendations:
            return {
                'total_capital_used': 0,
                'portfolio_utilization': 0,
                'scaling_factor': 1.0,
                'adjustment_needed': False
            }

        # 计算总资本使用
        total_capital_used = sum(
            pos.get('position_sizing', {}).get('suggested_capital', 0)
            for pos in position_recommendations
        )

        portfolio_utilization = total_capital_used / portfolio_value
        max_portfolio_risk = risk_config['max_portfolio_risk']

        # 如果超过组合风险限制，计算缩放因子
        if portfolio_utilization > max_portfolio_risk:
            scaling_factor = max_portfolio_risk / portfolio_utilization
            adjustment_needed = True
        else:
            scaling_factor = 1.0
            adjustment_needed = False

        return {
            'total_capital_used': total_capital_used,
            'portfolio_utilization': portfolio_utilization * 100,
            'max_allowed_utilization': max_portfolio_risk * 100,
            'scaling_factor': scaling_factor,
            'adjustment_needed': adjustment_needed,
            'adjusted_capital': total_capital_used * scaling_factor
        }

    def _calculate_position_risk_metrics(self, position_recommendations: List) -> Dict[str, Any]:
        """计算仓位风险指标"""
        if not position_recommendations:
            return {
                'diversification_score': 0,
                'risk_concentration': 100,
                'strategy_balance': 'none'
            }

        # 策略分散化分析
        strategies = [pos.get('strategy') for pos in position_recommendations]
        unique_strategies = len(set(strategies))
        diversification_score = min(100, unique_strategies * 25)  # 4个不同策略 = 100分

        # 风险集中度
        capital_allocations = [
            pos.get('position_sizing', {}).get('suggested_capital', 0)
            for pos in position_recommendations
        ]
        total_capital = sum(capital_allocations)

        if total_capital > 0:
            max_allocation = max(capital_allocations) / total_capital
            risk_concentration = max_allocation * 100
        else:
            risk_concentration = 100

        # 策略平衡
        sell_count = len([s for s in strategies if 'sell' in s])
        buy_count = len([s for s in strategies if 'buy' in s])

        if sell_count == 0:
            strategy_balance = 'buy_only'
        elif buy_count == 0:
            strategy_balance = 'sell_only'
        elif abs(sell_count - buy_count) <= 1:
            strategy_balance = 'balanced'
        else:
            strategy_balance = 'imbalanced'

        return {
            'diversification_score': diversification_score,
            'risk_concentration': risk_concentration,
            'strategy_balance': strategy_balance,
            'total_positions': len(position_recommendations),
            'unique_strategies': unique_strategies
        }


# 独立测试功能
if __name__ == "__main__":
    print("🧪 风险调整器独立测试")
    print("=" * 50)

    # 创建风险调整器实例
    adjuster = RiskAdjuster()
    print("✅ 风险调整器创建成功")

    # 模拟策略分析结果
    mock_strategy_analysis = {
        'sell_put': {
            'success': True,
            'recommendations': [{
                'strike': 170,
                'mid_price': 2.5,
                'days_to_expiry': 30,
                'volume': 150,
                'score': 85
            }]
        },
        'buy_call': {
            'success': True,
            'recommendations': [{
                'strike': 180,
                'mid_price': 3.0,
                'days_to_expiry': 35,
                'volume': 200,
                'score': 75
            }]
        }
    }

    mock_stock_data = {
        'volatility_30d': 0.25,
        'change_percent': 1.5
    }

    print(f"\n📊 测试组合风险分析...")
    risk_result = adjuster.analyze_portfolio_risk(mock_strategy_analysis, mock_stock_data)

    if risk_result.get('success'):
        print(f"  ✅ 风险分析成功")

        portfolio_risk = risk_result.get('portfolio_risk', {})
        print(f"  📈 组合风险:")
        print(f"    总体得分: {portfolio_risk.get('overall_score', 0):.1f}")
        print(f"    分散化效益: {portfolio_risk.get('diversification_benefit', 0):.1f}")
        print(f"    集中度风险: {portfolio_risk.get('concentration_risk', 0):.1f}")

        risk_assessment = risk_result.get('risk_assessment', {})
        print(f"  🎯 风险评估:")
        print(f"    总体风险等级: {risk_assessment.get('overall_risk_level')}")
        print(f"    监控优先级: {risk_assessment.get('monitoring_priority')}")
        print(f"    主要风险因子: {risk_assessment.get('main_risk_factors', [])}")

        adjustments = risk_result.get('risk_adjustments', [])
        if adjustments:
            print(f"  🔧 风险调整建议:")
            for adj in adjustments[:3]:
                print(f"    - {adj.get('action')}: {adj.get('reason')} (优先级: {adj.get('priority')})")

    else:
        print(f"  ❌ 风险分析失败: {risk_result.get('error')}")

    print(f"\n💰 测试仓位计算...")
    portfolio_value = 100000  # 10万组合
    position_result = adjuster.calculate_position_sizing(
        mock_strategy_analysis, portfolio_value, 'moderate'
    )

    if position_result.get('success'):
        print(f"  ✅ 仓位计算成功")
        print(f"  💼 组合价值: ${portfolio_value:,}")
        print(f"  🎯 风险承受度: {position_result.get('risk_tolerance')}")

        total_allocation = position_result.get('total_capital_allocation', 0)
        print(f"  📊 总资本配置: ${total_allocation:,.0f} ({total_allocation/portfolio_value*100:.1f}%)")

        positions = position_result.get('position_recommendations', [])
        print(f"  📋 仓位建议:")
        for pos in positions:
            strategy = pos.get('strategy')
            sizing = pos.get('position_sizing', {})
            print(f"    {strategy}: {sizing.get('suggested_contracts')}份合约, ${sizing.get('suggested_capital', 0):,.0f}")

        risk_metrics = position_result.get('risk_metrics', {})
        print(f"  📏 风险指标:")
        print(f"    分散化得分: {risk_metrics.get('diversification_score', 0):.0f}")
        print(f"    策略平衡: {risk_metrics.get('strategy_balance')}")

    else:
        print(f"  ❌ 仓位计算失败: {position_result.get('error')}")

    print("\n💡 风险管理说明:")
    print("- 保守型: 最大组合风险2%，单笔风险1%")
    print("- 中等型: 最大组合风险5%，单笔风险2.5%")
    print("- 积极型: 最大组合风险10%，单笔风险5%")
    print("- 实时监控和动态调整是关键")

    print("\n🎉 风险调整器独立测试完成!")
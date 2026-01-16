"""
期权分析引擎
整合期权数据获取、策略计分、风险分析等功能
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import traceback

from .data_fetcher import OptionsDataFetcher
from .tiger_client import TigerOptionsClient
from ..scoring.sell_put import SellPutScorer
from ..scoring.sell_call import SellCallScorer
from ..scoring.buy_put import BuyPutScorer
from ..scoring.buy_call import BuyCallScorer
from ..advanced.vrp_calculator import VRPCalculator
from ..advanced.risk_adjuster import RiskAdjuster

logger = logging.getLogger(__name__)


class OptionsAnalysisEngine:
    """期权分析引擎主类"""

    def __init__(self):
        """初始化期权分析引擎"""
        self.data_fetcher = OptionsDataFetcher()
        self.tiger_client = TigerOptionsClient()

        # 期权策略计分器
        self.scorers = {
            'sell_put': SellPutScorer(),
            'sell_call': SellCallScorer(),
            'buy_put': BuyPutScorer(),
            'buy_call': BuyCallScorer()
        }

        # 高级分析模块
        self.vrp_calculator = VRPCalculator()
        self.risk_adjuster = RiskAdjuster()

    def analyze_options_chain(self, symbol: str, strategy: str = 'all') -> Dict[str, Any]:
        """
        分析期权链

        Args:
            symbol: 股票代码
            strategy: 期权策略 ('sell_put', 'sell_call', 'buy_put', 'buy_call', 'all')

        Returns:
            完整的期权分析结果
        """
        try:
            logger.info(f"开始分析期权链: {symbol}, 策略: {strategy}")

            # 1. 获取期权数据
            options_data = self.data_fetcher.get_options_chain(symbol)
            if not options_data.get('success'):
                return {
                    'success': False,
                    'error': f"无法获取期权数据: {options_data.get('error', 'Unknown error')}"
                }

            # 2. 获取股票基础数据（用于分析）
            stock_data = self.data_fetcher.get_underlying_stock_data(symbol)

            # 3. 执行策略分析
            analysis_results = {}

            if strategy == 'all':
                # 分析所有策略
                for strategy_name in self.scorers.keys():
                    analysis_results[strategy_name] = self._analyze_strategy(
                        options_data, stock_data, strategy_name
                    )
            else:
                # 分析特定策略
                if strategy in self.scorers:
                    analysis_results[strategy] = self._analyze_strategy(
                        options_data, stock_data, strategy
                    )
                else:
                    return {
                        'success': False,
                        'error': f"不支持的策略: {strategy}"
                    }

            # 4. 计算VRP和风险指标
            vrp_analysis = self.vrp_calculator.calculate(symbol, options_data, stock_data)
            risk_analysis = self.risk_adjuster.analyze_portfolio_risk(analysis_results, stock_data)

            return {
                'success': True,
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'options_data': options_data,
                'stock_data': stock_data,
                'strategy_analysis': analysis_results,
                'vrp_analysis': vrp_analysis,
                'risk_analysis': risk_analysis,
                'summary': self._generate_analysis_summary(analysis_results, vrp_analysis, risk_analysis)
            }

        except Exception as e:
            logger.error(f"期权链分析失败: {e}")
            logger.error(traceback.format_exc())
            return {
                'success': False,
                'error': f"分析失败: {str(e)}"
            }

    def _analyze_strategy(self, options_data: Dict, stock_data: Dict, strategy: str) -> Dict[str, Any]:
        """分析特定期权策略"""
        try:
            scorer = self.scorers[strategy]
            return scorer.score_options(options_data, stock_data)
        except Exception as e:
            logger.error(f"策略 {strategy} 分析失败: {e}")
            return {
                'success': False,
                'strategy': strategy,
                'error': str(e)
            }

    def get_options_quotes(self, symbols: List[str]) -> Dict[str, Any]:
        """
        获取多个期权的实时报价

        Args:
            symbols: 期权代码列表

        Returns:
            期权报价数据
        """
        try:
            return self.data_fetcher.get_options_quotes(symbols)
        except Exception as e:
            logger.error(f"获取期权报价失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def calculate_position_sizing(self, strategy_analysis: Dict, portfolio_value: float,
                                risk_tolerance: str = 'moderate') -> Dict[str, Any]:
        """
        计算期权仓位大小

        Args:
            strategy_analysis: 策略分析结果
            portfolio_value: 组合总价值
            risk_tolerance: 风险承受度 ('conservative', 'moderate', 'aggressive')

        Returns:
            仓位建议
        """
        try:
            return self.risk_adjuster.calculate_position_sizing(
                strategy_analysis, portfolio_value, risk_tolerance
            )
        except Exception as e:
            logger.error(f"仓位计算失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _generate_analysis_summary(self, strategy_analysis: Dict, vrp_analysis: Dict,
                                 risk_analysis: Dict) -> Dict[str, Any]:
        """生成分析摘要"""
        try:
            # 找出最佳策略
            best_strategies = []
            for strategy, result in strategy_analysis.items():
                if result.get('success') and result.get('recommendations'):
                    top_option = result['recommendations'][0] if result['recommendations'] else None
                    if top_option and top_option.get('score', 0) > 70:  # 分数阈值
                        best_strategies.append({
                            'strategy': strategy,
                            'score': top_option.get('score'),
                            'option': top_option
                        })

            # 按分数排序
            best_strategies.sort(key=lambda x: x['score'], reverse=True)

            return {
                'total_strategies_analyzed': len(strategy_analysis),
                'successful_analysis': len([r for r in strategy_analysis.values() if r.get('success')]),
                'best_strategies': best_strategies[:3],  # 取前3个
                'vrp_level': vrp_analysis.get('level', 'unknown'),
                'overall_risk': risk_analysis.get('overall_risk', 'unknown'),
                'recommendation': self._get_overall_recommendation(best_strategies, vrp_analysis, risk_analysis)
            }

        except Exception as e:
            logger.error(f"生成分析摘要失败: {e}")
            return {
                'error': f"摘要生成失败: {str(e)}"
            }

    def _get_overall_recommendation(self, best_strategies: List, vrp_analysis: Dict,
                                   risk_analysis: Dict) -> Dict[str, Any]:
        """生成总体建议"""
        if not best_strategies:
            return {
                'action': 'wait',
                'reason': '当前没有发现高质量的期权交易机会',
                'confidence': 'low'
            }

        best_strategy = best_strategies[0]
        vrp_level = vrp_analysis.get('level', 'normal')
        risk_level = risk_analysis.get('overall_risk', 'medium')

        # 基于最佳策略和风险状况给出建议
        if best_strategy['score'] > 85 and risk_level in ['low', 'medium']:
            action = 'strong_buy'
            confidence = 'high'
        elif best_strategy['score'] > 70 and vrp_level in ['low', 'normal']:
            action = 'buy'
            confidence = 'medium'
        else:
            action = 'cautious'
            confidence = 'low'

        return {
            'action': action,
            'strategy': best_strategy['strategy'],
            'score': best_strategy['score'],
            'confidence': confidence,
            'reason': f"基于 {best_strategy['strategy']} 策略分析，得分 {best_strategy['score']:.1f}，VRP水平 {vrp_level}，风险等级 {risk_level}"
        }


# 独立测试功能
if __name__ == "__main__":
    print("🧪 期权分析引擎独立测试")
    print("=" * 50)

    # 创建引擎实例
    engine = OptionsAnalysisEngine()
    print("✅ 期权分析引擎创建成功")

    # 测试参数
    test_symbol = "AAPL"

    print(f"\n📊 测试期权链分析: {test_symbol}")
    print("注意: 这需要有效的Tiger API配置和网络连接")

    # 这里可以添加更多的测试逻辑
    # 在实际环境中会调用真实的API

    print("\n💡 测试提示:")
    print("- 确保Tiger API配置正确")
    print("- 检查网络连接")
    print("- 验证期权数据可访问性")
    print("- 每个计分器模块都可独立测试")

    print("\n🎉 期权分析引擎独立测试完成!")
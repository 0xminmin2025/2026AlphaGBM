"""
期权分析引擎
整合期权数据获取、策略计分、风险分析等功能
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import traceback

from .data_fetcher import OptionsDataFetcher
from ..scoring.sell_put import SellPutScorer
from ..scoring.sell_call import SellCallScorer
from ..scoring.buy_put import BuyPutScorer
from ..scoring.buy_call import BuyCallScorer
from ..scoring.risk_return_profile import calculate_risk_return_profile, add_profiles_to_options
from ..scoring.macro_event_calendar import get_upcoming_events
from ..advanced.vrp_calculator import VRPCalculator
from ..advanced.risk_adjuster import RiskAdjuster
from ..option_market_config import get_option_market_config, OptionMarketConfig, US_OPTIONS_CONFIG

logger = logging.getLogger(__name__)


class OptionsAnalysisEngine:
    """期权分析引擎主类"""

    def __init__(self):
        """初始化期权分析引擎"""
        self.data_fetcher = OptionsDataFetcher()

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

            # 0. 解析市场配置
            market_config = get_option_market_config(symbol)

            # 白名单校验：HK/CN市场强制白名单
            if market_config.whitelist_enforced and not market_config.is_symbol_allowed(symbol):
                allowed = market_config.get_allowed_symbols()
                return {
                    'success': False,
                    'error': f"标的 {symbol} 不在 {market_config.market} 市场期权白名单中",
                    'allowed_symbols': allowed,
                    'market': market_config.market
                }

            # 1. 获取期权数据
            options_data = self.data_fetcher.get_options_chain(symbol, market_config=market_config)
            if not options_data.get('success'):
                return {
                    'success': False,
                    'error': f"无法获取期权数据: {options_data.get('error', 'Unknown error')}"
                }

            # 2. 获取股票基础数据（用于分析）
            stock_data = self.data_fetcher.get_underlying_stock_data(symbol)

            # 3. 先计算VRP（用于后续策略分析）
            vrp_analysis = self.vrp_calculator.calculate(symbol, options_data, stock_data, market_config=market_config)

            # 4. 执行策略分析（带风格标签）
            analysis_results = {}

            if strategy == 'all':
                # 分析所有策略
                for strategy_name in self.scorers.keys():
                    analysis_results[strategy_name] = self._analyze_strategy(
                        options_data, stock_data, strategy_name, vrp_analysis, market_config=market_config
                    )
            else:
                # 分析特定策略
                if strategy in self.scorers:
                    analysis_results[strategy] = self._analyze_strategy(
                        options_data, stock_data, strategy, vrp_analysis, market_config=market_config
                    )
                else:
                    return {
                        'success': False,
                        'error': f"不支持的策略: {strategy}"
                    }

            # 5. 计算风险指标
            risk_analysis = self.risk_adjuster.analyze_portfolio_risk(analysis_results, stock_data)

            # 提取趋势信息（从任意策略分析中获取，它们使用相同的趋势数据）
            trend_info = None
            for strategy_name, result in analysis_results.items():
                if result.get('success') and result.get('trend_info'):
                    trend_info = result['trend_info']
                    break

            # 获取未来7天内的宏观事件（便于前端展示）
            upcoming_macro_events = get_upcoming_events(days_ahead=7)

            result = {
                'success': True,
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'options_data': options_data,
                'stock_data': stock_data,
                'strategy_analysis': analysis_results,
                'vrp_analysis': vrp_analysis,
                'risk_analysis': risk_analysis,
                'summary': self._generate_analysis_summary(analysis_results, vrp_analysis, risk_analysis),
                # 新增：趋势信息（便于前端显示）
                'trend_info': trend_info,
                # 新增：市场信息
                'market_info': {
                    'market': market_config.market,
                    'currency': market_config.currency,
                    'contract_multiplier': market_config.get_multiplier(symbol),
                    'cash_settlement': market_config.cash_settlement,
                },
                # 新增：未来宏观事件提醒
                'upcoming_macro_events': [
                    {
                        'date': e['date'].isoformat(),
                        'type': e['type'],
                        'name': e['name'],
                        'days_until': e['days_until'],
                    }
                    for e in upcoming_macro_events
                ],
            }

            # 商品期权：附加商品特有信息
            if market_config.market == 'COMMODITY':
                from ..advanced.delivery_risk import DeliveryRiskCalculator
                from ....services.market_data.adapters.akshare_commodity_adapter import AkShareCommodityAdapter

                product = AkShareCommodityAdapter._extract_product(symbol)
                # 取主力合约的交割风险
                dominant_contract = options_data.get('expiry_dates', [''])[0] if options_data.get('expiry_dates') else ''
                delivery_risk = DeliveryRiskCalculator().assess(dominant_contract).to_dict() if dominant_contract else {}

                result['commodity_info'] = {
                    'product': product,
                    'product_name': AkShareCommodityAdapter.PRODUCT_DISPLAY_NAME.get(product, product),
                    'exchange': AkShareCommodityAdapter.PRODUCT_EXCHANGE.get(product, ''),
                    'dominant_contract': dominant_contract,
                    'delivery_risk': delivery_risk,
                    'has_night_session': product in ('au', 'ag', 'cu', 'al'),
                    'product_multiplier': market_config.get_multiplier(symbol),
                }

            return result

        except Exception as e:
            logger.error(f"期权链分析失败: {e}")
            logger.error(traceback.format_exc())
            return {
                'success': False,
                'error': f"分析失败: {str(e)}"
            }

    def _analyze_strategy(self, options_data: Dict, stock_data: Dict, strategy: str,
                         vrp_analysis: Dict = None, market_config: OptionMarketConfig = None) -> Dict[str, Any]:
        """
        分析特定期权策略

        Args:
            options_data: 期权数据
            stock_data: 股票数据
            strategy: 策略类型
            vrp_analysis: VRP分析结果（用于风格标签计算）
            market_config: 市场配置（默认US）

        Returns:
            策略分析结果，包含风格标签
        """
        try:
            scorer = self.scorers[strategy]

            # 卖方策略传入VIX水平用于风险调整
            kwargs = {'market_config': market_config}
            if strategy in ('sell_put', 'sell_call'):
                vix_level = stock_data.get('vix', 0)
                kwargs['vix_level'] = vix_level

            result = scorer.score_options(options_data, stock_data, **kwargs)

            # 为推荐的期权添加风险收益风格标签
            if result.get('success') and result.get('recommendations'):
                result['recommendations'] = add_profiles_to_options(
                    result['recommendations'],
                    stock_data,
                    strategy,
                    vrp_analysis
                )

            return result
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
                                risk_tolerance: str = 'moderate',
                                market_config: OptionMarketConfig = None) -> Dict[str, Any]:
        """
        计算期权仓位大小

        Args:
            strategy_analysis: 策略分析结果
            portfolio_value: 组合总价值
            risk_tolerance: 风险承受度 ('conservative', 'moderate', 'aggressive')
            market_config: 市场配置（默认US）

        Returns:
            仓位建议
        """
        try:
            return self.risk_adjuster.calculate_position_sizing(
                strategy_analysis, portfolio_value, risk_tolerance,
                market_config=market_config
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
                        # 包含风格标签信息
                        profile = top_option.get('risk_return_profile', {})
                        best_strategies.append({
                            'strategy': strategy,
                            'score': top_option.get('score'),
                            'option': top_option,
                            'style_label': profile.get('style_label', ''),
                            'risk_level': profile.get('risk_level', 'unknown'),
                            'win_probability': profile.get('win_probability', 0),
                            'summary': profile.get('summary_cn', '')
                        })

            # 按分数排序
            best_strategies.sort(key=lambda x: x['score'], reverse=True)

            # 按风格分组推荐
            style_grouped = self._group_by_style(strategy_analysis)

            return {
                'total_strategies_analyzed': len(strategy_analysis),
                'successful_analysis': len([r for r in strategy_analysis.values() if r.get('success')]),
                'best_strategies': best_strategies[:3],  # 取前3个
                'style_grouped_recommendations': style_grouped,
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

    def _group_by_style(self, strategy_analysis: Dict) -> Dict[str, List]:
        """按风格分组推荐"""
        style_groups = {
            'steady_income': [],       # 稳健收益
            'high_risk_high_reward': [], # 高风险高收益
            'balanced': [],            # 稳中求进
            'hedge': []                # 保护对冲
        }

        for strategy, result in strategy_analysis.items():
            if not result.get('success') or not result.get('recommendations'):
                continue

            for option in result.get('recommendations', [])[:5]:  # 每个策略取前5
                profile = option.get('risk_return_profile', {})
                style = profile.get('style', 'balanced')

                if style in style_groups:
                    style_groups[style].append({
                        'strategy': strategy,
                        'strike': option.get('strike'),
                        'expiry': option.get('expiry'),
                        'score': option.get('score'),
                        'style_label': profile.get('style_label'),
                        'risk_color': profile.get('risk_color'),
                        'win_probability': profile.get('win_probability'),
                        'max_profit_pct': profile.get('max_profit_pct'),
                        'max_loss_pct': profile.get('max_loss_pct'),
                        'summary': profile.get('summary_cn')
                    })

        # 每组按分数排序，取前3
        for style in style_groups:
            style_groups[style].sort(key=lambda x: x.get('score', 0), reverse=True)
            style_groups[style] = style_groups[style][:3]

        return style_groups


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
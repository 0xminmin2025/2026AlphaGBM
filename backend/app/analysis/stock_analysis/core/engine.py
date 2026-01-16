"""
股票分析核心引擎
负责整合各个分析组件，提供统一的分析接口
"""

from typing import Dict, Any, Tuple, Optional
import logging
from .data_fetcher import StockDataFetcher
from .calculator import StockCalculator
from ..strategies.basic import BasicAnalysisStrategy

logger = logging.getLogger(__name__)


class StockAnalysisEngine:
    """
    股票分析引擎主类
    提供股票分析的统一接口，整合数据获取、计算和策略分析
    """

    def __init__(self):
        """初始化分析引擎"""
        self.data_fetcher = StockDataFetcher()
        self.calculator = StockCalculator()
        self.basic_strategy = BasicAnalysisStrategy()

    def analyze_stock(self, ticker: str, style: str = 'growth', **kwargs) -> Dict[str, Any]:
        """
        执行完整的股票分析

        参数:
            ticker: 股票代码
            style: 分析风格 ('growth', 'value', 'balanced')
            **kwargs: 其他分析参数

        返回:
            完整的分析结果字典
        """
        try:
            logger.info(f"开始分析股票: {ticker}, 风格: {style}")

            # 1. 获取市场数据
            market_data = self.data_fetcher.get_market_data(
                ticker,
                **kwargs
            )

            if not market_data or 'error' in market_data:
                return {
                    'success': False,
                    'error': f"无法获取 {ticker} 的市场数据"
                }

            # 2. 检查流动性
            is_liquid, liquidity_info = self.calculator.check_liquidity(market_data)

            # 3. 执行基础分析
            analysis_result = self.basic_strategy.analyze(
                data=market_data,
                style=style,
                liquidity_info=liquidity_info
            )

            # 4. 整合结果
            result = {
                'success': True,
                'ticker': ticker.upper(),
                'analysis_style': style,
                'market_data': market_data,
                'liquidity_analysis': {
                    'is_liquid': is_liquid,
                    'liquidity_info': liquidity_info
                },
                **analysis_result
            }

            logger.info(f"股票分析完成: {ticker}")
            return result

        except Exception as e:
            logger.error(f"分析股票 {ticker} 时发生错误: {e}")
            return {
                'success': False,
                'error': f"分析失败: {str(e)}",
                'ticker': ticker
            }

    def get_quick_quote(self, ticker: str) -> Dict[str, Any]:
        """
        获取快速报价信息

        参数:
            ticker: 股票代码

        返回:
            快速报价数据
        """
        try:
            return self.data_fetcher.get_ticker_price(ticker)
        except Exception as e:
            logger.error(f"获取 {ticker} 快速报价失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def check_stock_liquidity(self, ticker: str) -> Tuple[bool, Dict[str, Any]]:
        """
        检查股票流动性

        参数:
            ticker: 股票代码

        返回:
            (是否满足流动性要求, 流动性信息)
        """
        try:
            market_data = self.data_fetcher.get_market_data(ticker, onlyHistoryData=True)
            if not market_data or 'error' in market_data:
                return False, {'error': '无法获取市场数据'}

            return self.calculator.check_liquidity(market_data)
        except Exception as e:
            logger.error(f"检查 {ticker} 流动性失败: {e}")
            return False, {'error': str(e)}

    def calculate_target_price(self, ticker: str, style: str = 'growth') -> Dict[str, Any]:
        """
        计算目标价格

        参数:
            ticker: 股票代码
            style: 分析风格

        返回:
            目标价格分析结果
        """
        try:
            market_data = self.data_fetcher.get_market_data(ticker)
            if not market_data or 'error' in market_data:
                return {
                    'success': False,
                    'error': '无法获取市场数据'
                }

            # 先做风险分析
            risk_result = self.basic_strategy.analyze_risk_and_position(
                style=style,
                data=market_data
            )

            # 计算目标价格
            target_price = self.calculator.calculate_target_price(
                data=market_data,
                risk_result=risk_result,
                style=style
            )

            return {
                'success': True,
                'ticker': ticker.upper(),
                'target_price': target_price,
                'risk_analysis': risk_result
            }

        except Exception as e:
            logger.error(f"计算 {ticker} 目标价格失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# 为了向后兼容，提供一个简化的工厂函数
def create_stock_engine() -> StockAnalysisEngine:
    """创建股票分析引擎实例"""
    return StockAnalysisEngine()


# 为了独立测试，提供一个主函数
if __name__ == "__main__":
    # 独立测试代码
    engine = StockAnalysisEngine()

    # 测试股票分析
    test_ticker = "AAPL"
    result = engine.analyze_stock(test_ticker, style='growth')

    print(f"=== {test_ticker} 分析结果 ===")
    print(f"成功: {result.get('success', False)}")
    if result.get('success'):
        print(f"流动性: {result.get('liquidity_analysis', {}).get('is_liquid', 'Unknown')}")
        print(f"目标价格: {result.get('target_price', 'N/A')}")
    else:
        print(f"错误: {result.get('error', 'Unknown error')}")
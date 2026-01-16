"""
股票分析模块独立测试
演示如何独立运行和测试股票分析功能，无需依赖完整的Flask应用
"""

import sys
import os
import unittest
from unittest.mock import patch, Mock
import pandas as pd
import numpy as np

# 添加项目路径，确保可以导入模块
current_dir = os.path.dirname(__file__)
backend_dir = os.path.abspath(os.path.join(current_dir, '../../../..'))
sys.path.insert(0, backend_dir)

try:
    # 导入股票分析模块
    from app.analysis.stock_analysis.core.engine import StockAnalysisEngine
    from app.analysis.stock_analysis.core.data_fetcher import StockDataFetcher
    from app.analysis.stock_analysis.core.calculator import StockCalculator
    from app.analysis.stock_analysis.strategies.basic import BasicAnalysisStrategy

    print("✅ 成功导入所有股票分析模块")
except ImportError as e:
    print(f"❌ 导入模块失败: {e}")
    print("请确保在正确的目录下运行测试")
    exit(1)


class TestStockAnalysisIndependent(unittest.TestCase):
    """独立股票分析测试类"""

    def setUp(self):
        """设置测试环境"""
        print("\n" + "="*50)
        print(f"开始测试: {self._testMethodName}")
        print("="*50)

        # 创建测试用的模拟数据
        self.mock_stock_data = {
            'success': True,
            'ticker': 'AAPL',
            'info': {
                'regularMarketPrice': 150.0,
                'marketCap': 2500000000000,  # 2.5T
                'trailingPE': 25.0,
                'forwardPE': 22.0,
                'priceToBook': 8.5,
                'pegRatio': 1.2,
                'revenueGrowth': 0.12,
                'earningsGrowth': 0.18,
                'dividendYield': 0.005,
                'debtToEquity': 120.0,
                'sector': 'Technology',
                'industry': 'Consumer Electronics',
                'shortName': 'Apple Inc.',
                'longName': 'Apple Inc.',
                'currency': 'USD',
                'averageVolume': 80000000,
                'bookValue': 17.65
            },
            'history_prices': [140 + i + np.random.normal(0, 2) for i in range(100)],
            'history_volumes': [75000000 + np.random.randint(-10000000, 10000000) for _ in range(100)],
            'history_dates': [f'2023-{i//30+1:02d}-{i%30+1:02d}' for i in range(100)],
            'current_price': 150.0,
            'previous_close': 148.0,
            'change': 2.0,
            'change_percent': 1.35
        }

        # 创建股票分析引擎实例
        self.engine = StockAnalysisEngine()
        self.data_fetcher = StockDataFetcher()
        self.calculator = StockCalculator()
        self.strategy = BasicAnalysisStrategy()

    def test_data_fetcher_normalize_ticker(self):
        """测试股票代码规范化功能"""
        test_cases = [
            ('AAPL', 'AAPL'),
            ('aapl', 'AAPL'),
            ('600519', '600519.SS'),  # 上海股票
            ('000001', '000001.SZ'),  # 深圳股票
            ('600519.SS', '600519.SS'),  # 已经规范化的
        ]

        for input_ticker, expected in test_cases:
            result = self.data_fetcher.normalize_ticker(input_ticker)
            self.assertEqual(result, expected, f"代码规范化失败: {input_ticker} -> {result}, 期望: {expected}")
            print(f"  ✅ {input_ticker} -> {result}")

    def test_calculator_check_liquidity(self):
        """测试流动性检查功能"""
        # 测试高流动性股票
        high_liquidity_data = self.mock_stock_data.copy()
        is_liquid, liquidity_info = self.calculator.check_liquidity(high_liquidity_data)

        self.assertTrue(is_liquid, "高流动性股票应该被认为是流动的")
        self.assertIn('avg_daily_volume_usd', liquidity_info)
        self.assertGreater(liquidity_info['avg_daily_volume_usd'], 0)

        print(f"  ✅ 流动性检查: {is_liquid}, 平均日成交额: ${liquidity_info['avg_daily_volume_usd']:,.0f}")

        # 测试低流动性股票
        low_liquidity_data = self.mock_stock_data.copy()
        low_liquidity_data['history_volumes'] = [1000 for _ in range(100)]  # 极低成交量

        is_liquid_low, liquidity_info_low = self.calculator.check_liquidity(low_liquidity_data)
        self.assertFalse(is_liquid_low, "低流动性股票应该被认为是不流动的")
        print(f"  ✅ 低流动性检查: {is_liquid_low}, 平均日成交额: ${liquidity_info_low['avg_daily_volume_usd']:,.0f}")

    def test_calculator_atr(self):
        """测试ATR计算功能"""
        # 创建模拟历史数据
        dates = pd.date_range('2023-01-01', periods=50, freq='D')
        hist_data = pd.DataFrame({
            'High': [145 + i + np.random.uniform(0, 3) for i in range(50)],
            'Low': [140 + i + np.random.uniform(0, 3) for i in range(50)],
            'Close': [142 + i + np.random.uniform(0, 3) for i in range(50)]
        }, index=dates)

        atr = self.calculator.calculate_atr(hist_data, period=14)
        self.assertGreater(atr, 0, "ATR应该大于0")
        self.assertLess(atr, 20, "ATR应该在合理范围内")

        print(f"  ✅ ATR计算: {atr:.4f}")

    def test_calculator_market_sentiment(self):
        """测试市场情绪分析"""
        sentiment = self.calculator.calculate_market_sentiment(self.mock_stock_data)

        self.assertIn('overall_score', sentiment)
        self.assertIn('sentiment_level', sentiment)
        self.assertIn('factors', sentiment)

        score = sentiment['overall_score']
        level = sentiment['sentiment_level']

        print(f"  ✅ 市场情绪分析: 得分 {score:.1f}, 等级 {level}")

    def test_strategy_company_classification(self):
        """测试公司分类功能"""
        classification = self.strategy.classify_company(self.mock_stock_data)

        self.assertIn('cap_category', classification)
        self.assertIn('sector', classification)
        self.assertIn('growth_vs_value', classification)

        cap_category = classification['cap_category']
        sector = classification['sector']
        growth_vs_value = classification['growth_vs_value']

        print(f"  ✅ 公司分类: {cap_category}, {sector}, {growth_vs_value}")

    def test_strategy_risk_analysis(self):
        """测试风险分析功能"""
        risk_result = self.strategy.analyze_risk_and_position('growth', self.mock_stock_data)

        self.assertIn('risk_score', risk_result)
        self.assertIn('risk_level', risk_result)
        self.assertIn('position_size_pct', risk_result)

        risk_score = risk_result['risk_score']
        risk_level = risk_result['risk_level']
        position_size = risk_result['position_size_pct']

        print(f"  ✅ 风险分析: 得分 {risk_score}, 等级 {risk_level}, 建议仓位 {position_size:.1f}%")

    def test_strategy_style_analysis(self):
        """测试不同投资风格的分析"""
        styles = ['growth', 'value', 'balanced']

        for style in styles:
            print(f"\n  测试 {style.upper()} 风格分析:")

            # 模拟流动性信息
            liquidity_info = {'is_liquid': True, 'avg_daily_volume_usd': 1000000000}

            # 执行分析
            result = self.strategy.analyze(self.mock_stock_data, style, liquidity_info)

            self.assertTrue(result.get('success', False), f"{style} 风格分析应该成功")
            self.assertIn('recommendation', result)

            recommendation = result['recommendation']
            action = recommendation.get('action', 'N/A')
            confidence = recommendation.get('confidence', 'N/A')
            reason = recommendation.get('reason', 'N/A')

            print(f"    ✅ 建议: {action}, 信心: {confidence}")
            print(f"    📝 原因: {reason}")

    @patch('app.analysis.stock_analysis.core.data_fetcher.StockDataFetcher.get_market_data')
    def test_engine_full_analysis(self, mock_get_data):
        """测试完整分析流程（使用Mock数据）"""
        # 配置Mock数据
        mock_get_data.return_value = self.mock_stock_data

        # 执行完整分析
        result = self.engine.analyze_stock('AAPL', 'growth')

        # 验证结果
        self.assertTrue(result.get('success', False), "完整分析应该成功")
        self.assertEqual(result.get('ticker'), 'AAPL')
        self.assertEqual(result.get('analysis_style'), 'growth')
        self.assertIn('market_data', result)
        self.assertIn('liquidity_analysis', result)
        self.assertIn('recommendation', result)

        recommendation = result['recommendation']
        print(f"  ✅ 完整分析结果:")
        print(f"    📊 股票: {result.get('ticker')}")
        print(f"    📈 风格: {result.get('analysis_style')}")
        print(f"    💧 流动性: {result['liquidity_analysis']['is_liquid']}")
        print(f"    🎯 建议: {recommendation.get('action')}")
        print(f"    🔒 信心: {recommendation.get('confidence')}")

    def test_engine_quick_quote(self):
        """测试快速报价功能（使用Mock数据）"""
        with patch.object(self.engine.data_fetcher, 'get_ticker_price') as mock_get_price:
            mock_price_data = {
                'success': True,
                'ticker': 'AAPL',
                'current_price': 150.0,
                'previous_close': 148.0,
                'change': 2.0,
                'change_percent': 1.35,
                'volume': 80000000
            }
            mock_get_price.return_value = mock_price_data

            result = self.engine.get_quick_quote('AAPL')

            self.assertTrue(result.get('success', False))
            self.assertEqual(result.get('current_price'), 150.0)

            print(f"  ✅ 快速报价:")
            print(f"    💰 当前价格: ${result.get('current_price')}")
            print(f"    📈 涨跌: ${result.get('change')} ({result.get('change_percent'):.2f}%)")

    def test_independent_module_integration(self):
        """测试模块间的独立集成"""
        print("\n  🔗 测试模块间集成:")

        # 1. 数据获取 -> 计算
        print("    1. 数据获取 -> 计算模块")
        is_liquid, liquidity_info = self.calculator.check_liquidity(self.mock_stock_data)
        self.assertTrue(isinstance(is_liquid, bool))

        # 2. 计算 -> 策略
        print("    2. 计算 -> 策略模块")
        liquidity_dict = {'is_liquid': is_liquid, **liquidity_info}
        analysis_result = self.strategy.analyze(self.mock_stock_data, 'growth', liquidity_dict)
        self.assertTrue(analysis_result.get('success', False))

        # 3. 所有模块 -> 引擎
        print("    3. 所有模块 -> 分析引擎")
        # 这个在 test_engine_full_analysis 中已经测试

        print("    ✅ 模块间集成测试通过")


def run_independent_demo():
    """运行独立演示"""
    print("="*70)
    print("🚀 股票分析模块独立演示")
    print("="*70)

    print("\n📋 演示说明:")
    print("  这个演示展示了股票分析模块如何独立于Flask应用运行")
    print("  可以用于本地调试、算法优化和独立测试")

    print("\n🔧 创建分析引擎实例...")
    engine = StockAnalysisEngine()

    print("\n📊 模拟真实分析场景:")

    # 模拟股票分析
    test_symbols = ['AAPL', 'MSFT', '600519']  # 美股和A股

    for symbol in test_symbols:
        print(f"\n--- 分析 {symbol} ---")

        # 标准化股票代码
        normalized = engine.data_fetcher.normalize_ticker(symbol)
        print(f"📝 规范化代码: {symbol} -> {normalized}")

        # 模拟不同风格的分析建议
        styles = ['growth', 'value', 'balanced']
        for style in styles:
            print(f"  📈 {style.upper()} 风格: ", end="")

            # 这里在实际使用中会调用真实的API
            # 为了演示，我们跳过真实的API调用
            print("(需要真实市场数据)")

    print("\n✅ 独立演示完成!")
    print("\n💡 提示:")
    print("  - 修改 constants.py 中的参数来调整分析算法")
    print("  - 每个模块都可以独立测试和调试")
    print("  - 支持不同投资风格的分析策略")
    print("  - 可以轻松扩展新的分析算法")


if __name__ == '__main__':
    print("🧪 股票分析模块独立测试套件")
    print("可选择运行模式:")
    print("1. 单元测试 (python test_stock_analysis.py test)")
    print("2. 独立演示 (python test_stock_analysis.py demo)")
    print("3. 默认运行演示")

    import sys

    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        # 运行单元测试
        print("\n🧪 运行单元测试...")
        unittest.main(argv=[''], exit=False, verbosity=2)
    else:
        # 运行独立演示
        run_independent_demo()

        # 也运行一个简单的测试
        print("\n" + "="*70)
        print("🧪 快速验证测试")
        print("="*70)

        # 创建测试实例并运行关键测试
        test_instance = TestStockAnalysisIndependent()
        test_instance.setUp()

        try:
            print("\n📝 测试股票代码规范化...")
            test_instance.test_data_fetcher_normalize_ticker()

            print("\n💧 测试流动性分析...")
            test_instance.test_calculator_check_liquidity()

            print("\n🏢 测试公司分类...")
            test_instance.test_strategy_company_classification()

            print("\n⚠️  测试风险分析...")
            test_instance.test_strategy_risk_analysis()

            print("\n📊 测试投资风格分析...")
            test_instance.test_strategy_style_analysis()

            print("\n✅ 所有快速验证测试通过!")

        except Exception as e:
            print(f"\n❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()

        print("\n🎉 股票分析模块独立测试完成!")
        print("📁 模块位置: app/analysis/stock_analysis/")
        print("🔧 可以独立调试、测试和维护")
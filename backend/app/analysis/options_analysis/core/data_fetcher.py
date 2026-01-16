"""
期权数据获取模块
整合Tiger API和其他数据源，提供统一的期权数据接口
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
import numpy as np

from .tiger_client import TigerOptionsClient

logger = logging.getLogger(__name__)


class OptionsDataFetcher:
    """期权数据获取器"""

    def __init__(self):
        """初始化数据获取器"""
        self.tiger_client = TigerOptionsClient()
        self.cache_duration = 300  # 缓存5分钟
        self._cache = {}

    def get_options_chain(self, symbol: str, expiry_days: int = 45) -> Dict[str, Any]:
        """
        获取期权链数据

        Args:
            symbol: 股票代码
            expiry_days: 到期天数范围

        Returns:
            期权链数据
        """
        try:
            cache_key = f"chain_{symbol}_{expiry_days}"

            # 检查缓存
            if self._is_cache_valid(cache_key):
                logger.info(f"使用缓存的期权链数据: {symbol}")
                return self._cache[cache_key]['data']

            logger.info(f"获取期权链数据: {symbol}, 到期天数: {expiry_days}")

            # 尝试从Tiger API获取
            tiger_data = self.tiger_client.get_options_chain(symbol, expiry_days)

            if tiger_data.get('success'):
                # 使用Tiger数据
                result = self._format_tiger_options_data(tiger_data)
            else:
                # 备用：使用yfinance数据
                logger.warning(f"Tiger API失败，使用yfinance备用数据: {tiger_data.get('error')}")
                result = self._get_yfinance_options_data(symbol)

            # 添加额外的分析数据
            if result.get('success'):
                result = self._enrich_options_data(result)

            # 更新缓存
            self._cache[cache_key] = {
                'data': result,
                'timestamp': datetime.now()
            }

            return result

        except Exception as e:
            logger.error(f"获取期权链失败: {symbol}, 错误: {e}")
            return {
                'success': False,
                'error': f"期权链获取失败: {str(e)}",
                'symbol': symbol
            }

    def get_options_quotes(self, option_symbols: List[str]) -> Dict[str, Any]:
        """
        获取期权实时报价

        Args:
            option_symbols: 期权代码列表

        Returns:
            期权报价数据
        """
        try:
            logger.info(f"获取期权报价: {len(option_symbols)} 个期权")

            # 尝试从Tiger API获取实时数据
            tiger_quotes = self.tiger_client.get_options_quotes(option_symbols)

            if tiger_quotes.get('success'):
                return tiger_quotes
            else:
                # 备用方案：返回模拟数据
                logger.warning(f"Tiger报价失败，使用模拟数据: {tiger_quotes.get('error')}")
                return self._generate_mock_quotes(option_symbols)

        except Exception as e:
            logger.error(f"获取期权报价失败: {e}")
            return {
                'success': False,
                'error': f"期权报价获取失败: {str(e)}"
            }

    def get_underlying_stock_data(self, symbol: str) -> Dict[str, Any]:
        """
        获取标的股票数据

        Args:
            symbol: 股票代码

        Returns:
            股票数据
        """
        try:
            cache_key = f"stock_{symbol}"

            # 检查缓存
            if self._is_cache_valid(cache_key):
                return self._cache[cache_key]['data']

            logger.info(f"获取标的股票数据: {symbol}")

            # 使用yfinance获取股票数据
            ticker = yf.Ticker(symbol)

            # 获取基本信息
            info = ticker.info

            # 获取历史价格数据
            hist = ticker.history(period="1mo")

            # 获取期权到期日
            expiry_dates = ticker.options if hasattr(ticker, 'options') else []

            # 计算技术指标
            current_price = info.get('regularMarketPrice', hist['Close'].iloc[-1] if not hist.empty else None)

            result = {
                'success': True,
                'symbol': symbol,
                'current_price': current_price,
                'previous_close': info.get('regularMarketPreviousClose'),
                'change': current_price - info.get('regularMarketPreviousClose', current_price) if current_price else 0,
                'change_percent': ((current_price - info.get('regularMarketPreviousClose', current_price)) / info.get('regularMarketPreviousClose', current_price) * 100) if current_price and info.get('regularMarketPreviousClose') else 0,
                'volume': info.get('regularMarketVolume'),
                'market_cap': info.get('marketCap'),
                'info': info,
                'history': hist.to_dict() if not hist.empty else {},
                'expiry_dates': expiry_dates,
                'volatility_30d': self._calculate_volatility(hist),
                'support_resistance': self._calculate_support_resistance(hist)
            }

            # 更新缓存
            self._cache[cache_key] = {
                'data': result,
                'timestamp': datetime.now()
            }

            return result

        except Exception as e:
            logger.error(f"获取标的股票数据失败: {symbol}, 错误: {e}")
            return {
                'success': False,
                'error': f"股票数据获取失败: {str(e)}",
                'symbol': symbol
            }

    def _format_tiger_options_data(self, tiger_data: Dict) -> Dict[str, Any]:
        """格式化Tiger期权数据"""
        try:
            formatted_data = {
                'success': True,
                'source': 'tiger',
                'symbol': tiger_data.get('symbol'),
                'timestamp': datetime.now().isoformat(),
                'calls': tiger_data.get('calls', []),
                'puts': tiger_data.get('puts', []),
                'expiry_dates': tiger_data.get('expiry_dates', []),
                'raw_data': tiger_data
            }

            return formatted_data

        except Exception as e:
            logger.error(f"格式化Tiger数据失败: {e}")
            return {
                'success': False,
                'error': f"Tiger数据格式化失败: {str(e)}"
            }

    def _get_yfinance_options_data(self, symbol: str) -> Dict[str, Any]:
        """使用yfinance获取期权数据（备用方案）"""
        try:
            ticker = yf.Ticker(symbol)

            # 获取期权到期日
            expiry_dates = ticker.options

            if not expiry_dates:
                return {
                    'success': False,
                    'error': f"无期权数据可用: {symbol}"
                }

            # 获取最近的期权链数据
            calls_data = []
            puts_data = []

            for expiry in expiry_dates[:3]:  # 只取前3个到期日
                try:
                    option_chain = ticker.option_chain(expiry)

                    # 处理看涨期权
                    calls = option_chain.calls
                    for _, call in calls.iterrows():
                        calls_data.append({
                            'strike': call.get('strike'),
                            'expiry': expiry,
                            'bid': call.get('bid'),
                            'ask': call.get('ask'),
                            'last_price': call.get('lastPrice'),
                            'volume': call.get('volume'),
                            'open_interest': call.get('openInterest'),
                            'implied_volatility': call.get('impliedVolatility'),
                            'delta': call.get('delta', None),
                            'gamma': call.get('gamma', None),
                            'theta': call.get('theta', None),
                            'vega': call.get('vega', None)
                        })

                    # 处理看跌期权
                    puts = option_chain.puts
                    for _, put in puts.iterrows():
                        puts_data.append({
                            'strike': put.get('strike'),
                            'expiry': expiry,
                            'bid': put.get('bid'),
                            'ask': put.get('ask'),
                            'last_price': put.get('lastPrice'),
                            'volume': put.get('volume'),
                            'open_interest': put.get('openInterest'),
                            'implied_volatility': put.get('impliedVolatility'),
                            'delta': put.get('delta', None),
                            'gamma': put.get('gamma', None),
                            'theta': put.get('theta', None),
                            'vega': put.get('vega', None)
                        })

                except Exception as e:
                    logger.warning(f"获取 {expiry} 期权链失败: {e}")
                    continue

            return {
                'success': True,
                'source': 'yfinance',
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'calls': calls_data,
                'puts': puts_data,
                'expiry_dates': list(expiry_dates)
            }

        except Exception as e:
            logger.error(f"yfinance期权数据获取失败: {e}")
            return {
                'success': False,
                'error': f"yfinance数据获取失败: {str(e)}"
            }

    def _enrich_options_data(self, options_data: Dict) -> Dict[str, Any]:
        """丰富期权数据，添加分析指标"""
        try:
            # 计算期权链分析指标
            calls = options_data.get('calls', [])
            puts = options_data.get('puts', [])

            # 计算Put/Call比率
            put_volume = sum(opt.get('volume', 0) for opt in puts)
            call_volume = sum(opt.get('volume', 0) for opt in calls)
            put_call_ratio = put_volume / call_volume if call_volume > 0 else 0

            # 计算最大痛点
            max_pain = self._calculate_max_pain(calls, puts)

            # 添加流动性分析
            liquid_options = self._analyze_option_liquidity(calls + puts)

            # 添加到结果中
            options_data.update({
                'analytics': {
                    'put_call_ratio': put_call_ratio,
                    'max_pain': max_pain,
                    'total_call_volume': call_volume,
                    'total_put_volume': put_volume,
                    'liquid_options_count': len(liquid_options),
                    'total_options_count': len(calls) + len(puts)
                },
                'liquid_options': liquid_options
            })

            return options_data

        except Exception as e:
            logger.error(f"丰富期权数据失败: {e}")
            return options_data

    def _calculate_max_pain(self, calls: List, puts: List) -> Optional[float]:
        """计算最大痛点"""
        try:
            if not calls and not puts:
                return None

            # 收集所有行权价
            strikes = set()
            for opt in calls + puts:
                if opt.get('strike'):
                    strikes.add(opt['strike'])

            if not strikes:
                return None

            max_pain_strike = None
            min_pain_value = float('inf')

            for strike in strikes:
                # 计算该行权价的总痛苦值
                call_pain = sum(max(0, strike - opt.get('strike', 0)) * opt.get('open_interest', 0)
                              for opt in calls if opt.get('strike', 0) < strike)
                put_pain = sum(max(0, opt.get('strike', 0) - strike) * opt.get('open_interest', 0)
                             for opt in puts if opt.get('strike', 0) > strike)

                total_pain = call_pain + put_pain

                if total_pain < min_pain_value:
                    min_pain_value = total_pain
                    max_pain_strike = strike

            return max_pain_strike

        except Exception as e:
            logger.error(f"计算最大痛点失败: {e}")
            return None

    def _analyze_option_liquidity(self, options: List) -> List[Dict]:
        """分析期权流动性"""
        liquid_options = []

        for opt in options:
            volume = opt.get('volume', 0)
            open_interest = opt.get('open_interest', 0)
            bid = opt.get('bid', 0)
            ask = opt.get('ask', 0)

            # 流动性标准
            is_liquid = (
                volume >= 10 and  # 最小成交量
                open_interest >= 50 and  # 最小持仓量
                bid > 0 and ask > 0 and  # 有效报价
                (ask - bid) / ((ask + bid) / 2) <= 0.1  # 价差不超过10%
            )

            if is_liquid:
                liquid_options.append(opt)

        return liquid_options

    def _calculate_volatility(self, hist_data: pd.DataFrame) -> Optional[float]:
        """计算30天历史波动率"""
        try:
            if hist_data.empty:
                return None

            returns = hist_data['Close'].pct_change().dropna()
            volatility = returns.std() * np.sqrt(252)  # 年化波动率
            return float(volatility)

        except Exception as e:
            logger.error(f"计算波动率失败: {e}")
            return None

    def _calculate_support_resistance(self, hist_data: pd.DataFrame) -> Dict[str, float]:
        """计算支撑阻力位"""
        try:
            if hist_data.empty:
                return {}

            # 简单的支撑阻力计算
            high = hist_data['High'].max()
            low = hist_data['Low'].min()
            close = hist_data['Close'].iloc[-1]

            # 使用斐波那契回调位
            diff = high - low
            resistance_1 = close + diff * 0.236
            resistance_2 = close + diff * 0.382
            support_1 = close - diff * 0.236
            support_2 = close - diff * 0.382

            return {
                'resistance_1': float(resistance_1),
                'resistance_2': float(resistance_2),
                'support_1': float(support_1),
                'support_2': float(support_2),
                'high_52w': float(high),
                'low_52w': float(low)
            }

        except Exception as e:
            logger.error(f"计算支撑阻力失败: {e}")
            return {}

    def _generate_mock_quotes(self, option_symbols: List[str]) -> Dict[str, Any]:
        """生成模拟期权报价数据（用于测试）"""
        mock_quotes = {}

        for symbol in option_symbols:
            mock_quotes[symbol] = {
                'bid': round(np.random.uniform(0.5, 10.0), 2),
                'ask': round(np.random.uniform(0.5, 10.0), 2),
                'last_price': round(np.random.uniform(0.5, 10.0), 2),
                'volume': np.random.randint(0, 1000),
                'timestamp': datetime.now().isoformat()
            }

        return {
            'success': True,
            'source': 'mock',
            'quotes': mock_quotes,
            'timestamp': datetime.now().isoformat()
        }

    def _is_cache_valid(self, cache_key: str) -> bool:
        """检查缓存是否有效"""
        if cache_key not in self._cache:
            return False

        cache_time = self._cache[cache_key]['timestamp']
        return (datetime.now() - cache_time).total_seconds() < self.cache_duration

    def clear_cache(self):
        """清除所有缓存"""
        self._cache.clear()
        logger.info("期权数据缓存已清除")


# 独立测试功能
if __name__ == "__main__":
    print("🧪 期权数据获取器独立测试")
    print("=" * 50)

    # 创建数据获取器实例
    fetcher = OptionsDataFetcher()
    print("✅ 期权数据获取器创建成功")

    # 测试参数
    test_symbol = "AAPL"

    print(f"\n📊 测试标的股票数据获取: {test_symbol}")
    stock_data = fetcher.get_underlying_stock_data(test_symbol)

    if stock_data.get('success'):
        print(f"  ✅ 股票数据获取成功")
        print(f"  💰 当前价格: ${stock_data.get('current_price', 'N/A')}")
        print(f"  📈 价格变化: {stock_data.get('change_percent', 0):.2f}%")
        print(f"  📊 30日波动率: {stock_data.get('volatility_30d', 'N/A')}")
    else:
        print(f"  ❌ 股票数据获取失败: {stock_data.get('error')}")

    print(f"\n📋 测试期权链数据获取: {test_symbol}")
    options_data = fetcher.get_options_chain(test_symbol)

    if options_data.get('success'):
        print(f"  ✅ 期权链数据获取成功")
        print(f"  📞 看涨期权数量: {len(options_data.get('calls', []))}")
        print(f"  📉 看跌期权数量: {len(options_data.get('puts', []))}")
        print(f"  💧 流动期权数量: {options_data.get('analytics', {}).get('liquid_options_count', 0)}")
        print(f"  🎯 最大痛点: ${options_data.get('analytics', {}).get('max_pain', 'N/A')}")
    else:
        print(f"  ❌ 期权链数据获取失败: {options_data.get('error')}")

    print("\n💡 测试提示:")
    print("- 确保网络连接正常")
    print("- 验证Tiger API配置（如果使用）")
    print("- yfinance数据作为备用方案")
    print("- 数据会缓存5分钟以提高性能")

    print("\n🎉 期权数据获取器独立测试完成!")
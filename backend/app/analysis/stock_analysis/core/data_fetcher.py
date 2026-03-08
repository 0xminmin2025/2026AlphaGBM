"""
股票数据获取模块
负责从各种数据源获取股票相关数据
"""

import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import time
import logging
from typing import Dict, Any, Optional

# Use DataProvider for unified data access with metrics tracking
from ....services.data_provider import DataProvider

# 导入配置参数
try:
    from ....constants import *
except ImportError:
    # 如果constants不存在，使用默认值
    GROWTH_DISCOUNT_FACTOR = 0.6
    ATR_MULTIPLIER_BASE = 2.5
    MIN_DAILY_VOLUME_USD = 5_000_000
    FIXED_STOP_LOSS_PCT = 0.15
    PEG_THRESHOLD_BASE = 1.5

logger = logging.getLogger(__name__)


class StockDataFetcher:
    """
    股票数据获取器
    负责从yfinance等数据源获取股票数据
    """

    def __init__(self):
        """初始化数据获取器"""
        self.default_period = "2y"  # 默认获取2年历史数据

    @staticmethod
    def _create_ticker(symbol: str):
        """Create a ticker object using DataProvider (unified data access)."""
        return DataProvider(symbol)

    def normalize_ticker(self, ticker: str) -> str:
        """
        规范化股票代码格式

        参数:
            ticker: 原始股票代码

        返回:
            规范化的股票代码
        """
        if not ticker:
            return ""

        # 转换为大写并去除空格
        ticker = ticker.upper().strip()

        # 处理中国股票代码格式
        if ticker.endswith('.SS') or ticker.endswith('.SZ'):
            return ticker
        elif ticker.isdigit() and len(ticker) == 6:
            # 中国股票代码：6位数字
            if ticker.startswith(('60', '68')):
                return f"{ticker}.SS"  # 上海交易所
            elif ticker.startswith(('00', '30')):
                return f"{ticker}.SZ"  # 深圳交易所

        # 美股代码直接返回
        return ticker

    def get_ticker_price(self, ticker: str, max_retries: int = 3, retry_delay: int = 2) -> Dict[str, Any]:
        """
        获取股票实时价格信息

        参数:
            ticker: 股票代码
            max_retries: 最大重试次数
            retry_delay: 重试间隔（秒）

        返回:
            包含价格信息的字典
        """
        normalized_ticker = self.normalize_ticker(ticker)

        for attempt in range(max_retries):
            try:
                logger.info(f"获取 {normalized_ticker} 实时价格，尝试 {attempt + 1}/{max_retries}")

                stock = self._create_ticker(normalized_ticker)
                info = stock.info

                if not info or 'regularMarketPrice' not in info:
                    logger.warning(f"无法获取 {normalized_ticker} 的价格信息")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    else:
                        return {
                            'success': False,
                            'error': f'无法获取 {normalized_ticker} 的价格信息'
                        }

                # 构建返回数据
                result = {
                    'success': True,
                    'ticker': normalized_ticker,
                    'current_price': info.get('regularMarketPrice', 0),
                    'previous_close': info.get('regularMarketPreviousClose', 0),
                    'open_price': info.get('regularMarketOpen', 0),
                    'day_high': info.get('regularMarketDayHigh', 0),
                    'day_low': info.get('regularMarketDayLow', 0),
                    'volume': info.get('regularMarketVolume', 0),
                    'market_cap': info.get('marketCap', 0),
                    'currency': info.get('currency', 'USD')
                }

                # 计算涨跌幅
                if result['previous_close'] and result['current_price']:
                    result['change'] = result['current_price'] - result['previous_close']
                    result['change_percent'] = (result['change'] / result['previous_close']) * 100

                logger.info(f"成功获取 {normalized_ticker} 价格信息")
                return result

            except YFRateLimitError:
                logger.warning(f"yfinance 限流，等待 {retry_delay * 2} 秒后重试")
                time.sleep(retry_delay * 2)
                if attempt < max_retries - 1:
                    continue
                else:
                    return {
                        'success': False,
                        'error': 'API调用频率过高，请稍后再试'
                    }

            except Exception as e:
                logger.error(f"获取 {normalized_ticker} 价格时发生错误: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    return {
                        'success': False,
                        'error': f'获取价格失败: {str(e)}'
                    }

    def get_market_data(self, ticker: str, onlyHistoryData: bool = False, startDate: Optional[str] = None,
                       max_retries: int = 3, retry_delay: int = 2, use_backup: bool = True) -> Dict[str, Any]:
        """
        获取完整的市场数据

        参数:
            ticker: 股票代码
            onlyHistoryData: 是否只获取历史数据
            startDate: 开始日期
            max_retries: 最大重试次数
            retry_delay: 重试间隔
            use_backup: 是否使用备用方案

        返回:
            包含完整市场数据的字典
        """
        normalized_ticker = self.normalize_ticker(ticker)

        for attempt in range(max_retries):
            try:
                logger.info(f"获取 {normalized_ticker} 市场数据，尝试 {attempt + 1}/{max_retries}")

                stock = self._create_ticker(normalized_ticker)

                # 获取基本信息
                info = stock.info
                if not info:
                    logger.warning(f"无法获取 {normalized_ticker} 的基本信息")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    else:
                        return {'error': f'无法获取 {normalized_ticker} 的基本信息'}

                # 获取历史数据
                try:
                    if startDate:
                        start = datetime.strptime(startDate, '%Y-%m-%d')
                    else:
                        start = datetime.now() - relativedelta(years=2)

                    end = datetime.now()

                    hist = stock.history(start=start, end=end)

                    if hist.empty:
                        logger.warning(f"{normalized_ticker} 历史数据为空")
                        if attempt < max_retries - 1:
                            time.sleep(retry_delay)
                            continue
                        else:
                            return {'error': f'{normalized_ticker} 历史数据为空'}

                except Exception as e:
                    logger.error(f"获取 {normalized_ticker} 历史数据失败: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    else:
                        return {'error': f'获取历史数据失败: {str(e)}'}

                # 构建返回数据
                result = {
                    'success': True,
                    'ticker': normalized_ticker,
                    'info': info,
                    'history_data': hist,
                    'history_prices': hist['Close'].tolist() if 'Close' in hist.columns else [],
                    'history_volumes': hist['Volume'].tolist() if 'Volume' in hist.columns else [],
                    'history_dates': [d.strftime('%Y-%m-%d') for d in hist.index.tolist()],
                }

                # 如果只需要历史数据，直接返回
                if onlyHistoryData:
                    logger.info(f"成功获取 {normalized_ticker} 历史数据")
                    return result

                # 添加实时价格信息
                current_price_data = self.get_ticker_price(normalized_ticker)
                if current_price_data.get('success'):
                    result.update({
                        'current_price': current_price_data.get('current_price', 0),
                        'previous_close': current_price_data.get('previous_close', 0),
                        'change': current_price_data.get('change', 0),
                        'change_percent': current_price_data.get('change_percent', 0)
                    })

                # 添加计算字段
                if result['history_prices']:
                    result['latest_price'] = result['history_prices'][-1]
                    result['avg_volume_30d'] = np.mean(result['history_volumes'][-30:]) if len(result['history_volumes']) >= 30 else 0

                    # 计算价格统计
                    prices = np.array(result['history_prices'])
                    result['price_52w_high'] = float(np.max(prices)) if len(prices) > 0 else 0
                    result['price_52w_low'] = float(np.min(prices)) if len(prices) > 0 else 0

                logger.info(f"成功获取 {normalized_ticker} 完整市场数据")
                return result

            except YFRateLimitError:
                logger.warning(f"yfinance 限流，等待 {retry_delay * 2} 秒后重试")
                time.sleep(retry_delay * 2)
                if attempt < max_retries - 1:
                    continue
                else:
                    return {'error': 'API调用频率过高，请稍后再试'}

            except Exception as e:
                logger.error(f"获取 {normalized_ticker} 市场数据时发生错误: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    return {'error': f'获取市场数据失败: {str(e)}'}

    def get_macro_market_data(self) -> Dict[str, Any]:
        """
        获取宏观市场数据

        返回:
            宏观市场数据字典
        """
        try:
            logger.info("获取宏观市场数据")

            result = {
                'success': True,
                'timestamp': datetime.now().isoformat(),
            }

            # 获取主要指数
            indices = {
                'SPY': '^GSPC',  # S&P 500
                'QQQ': '^IXIC',  # NASDAQ
                'IWM': '^RUT',   # Russell 2000
                'VIX': '^VIX',   # VIX恐慌指数
            }

            indices_data = {}
            for name, symbol in indices.items():
                try:
                    data = self.get_ticker_price(symbol)
                    if data.get('success'):
                        indices_data[name] = {
                            'price': data.get('current_price', 0),
                            'change_percent': data.get('change_percent', 0)
                        }
                except Exception as e:
                    logger.error(f"获取 {name} 数据失败: {e}")
                    indices_data[name] = {'price': 0, 'change_percent': 0}

            result['indices'] = indices_data

            # 获取利率数据 (使用10年期美债作为参考)
            try:
                tnx_data = self.get_ticker_price('^TNX')
                if tnx_data.get('success'):
                    result['treasury_10y'] = tnx_data.get('current_price', 0)
                else:
                    result['treasury_10y'] = 4.5  # 默认值
            except:
                result['treasury_10y'] = 4.5

            logger.info("成功获取宏观市场数据")
            return result

        except Exception as e:
            logger.error(f"获取宏观市场数据失败: {e}")
            return {
                'success': False,
                'error': f'获取宏观市场数据失败: {str(e)}'
            }

    def get_stock_history(self, ticker: str, days: int = 60) -> Dict[str, Any]:
        """
        获取指定天数的股票历史数据

        参数:
            ticker: 股票代码
            days: 历史天数

        返回:
            历史数据字典
        """
        try:
            logger.info(f"获取 {ticker} {days}天历史数据")

            normalized_ticker = self.normalize_ticker(ticker)
            stock = self._create_ticker(normalized_ticker)

            # 计算开始日期
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            hist = stock.history(start=start_date, end=end_date)

            if hist.empty:
                return {
                    'success': False,
                    'error': '无法获取历史数据'
                }

            # 格式化数据
            history_data = []
            for date, row in hist.iterrows():
                history_data.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'open': float(row['Open']),
                    'high': float(row['High']),
                    'low': float(row['Low']),
                    'close': float(row['Close']),
                    'volume': int(row['Volume'])
                })

            result = {
                'success': True,
                'ticker': normalized_ticker,
                'days': days,
                'data': history_data,
                'total_points': len(history_data)
            }

            logger.info(f"成功获取 {normalized_ticker} {days}天历史数据，共{len(history_data)}个数据点")
            return result

        except Exception as e:
            logger.error(f"获取 {ticker} 历史数据失败: {e}")
            return {
                'success': False,
                'error': f'获取历史数据失败: {str(e)}'
            }


# 为独立测试提供主函数
if __name__ == "__main__":
    # 独立测试代码
    fetcher = StockDataFetcher()

    # 测试股票代码规范化
    test_tickers = ["AAPL", "600519", "000001.sz"]
    print("=== 股票代码规范化测试 ===")
    for ticker in test_tickers:
        normalized = fetcher.normalize_ticker(ticker)
        print(f"{ticker} -> {normalized}")

    # 测试价格获取
    print("\n=== 价格获取测试 ===")
    price_data = fetcher.get_ticker_price("AAPL")
    print(f"AAPL价格数据: {price_data}")

    # 测试市场数据获取
    print("\n=== 市场数据获取测试 ===")
    market_data = fetcher.get_market_data("AAPL", onlyHistoryData=True)
    if market_data.get('success'):
        print(f"AAPL历史数据点数: {len(market_data.get('history_prices', []))}")
    else:
        print(f"获取失败: {market_data.get('error', 'Unknown')}")
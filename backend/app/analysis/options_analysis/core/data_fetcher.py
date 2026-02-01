"""
期权数据获取模块
整合Tiger API和其他数据源，提供统一的期权数据接口

所有数据通过 DataProvider 获取，DataProvider 内部自动处理多数据源切换和指标追踪
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Use DataProvider for unified data access with metrics tracking
from ....services.data_provider import DataProvider


def _create_ticker(symbol: str):
    """Create a ticker object using DataProvider (unified data access)."""
    return DataProvider(symbol)

logger = logging.getLogger(__name__)


class OptionsDataFetcher:
    """期权数据获取器 - 使用 DataProvider 统一访问数据"""

    def __init__(self):
        """初始化数据获取器"""
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

            # 使用 DataProvider 获取期权数据 (内部自动选择最优数据源)
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

            # 使用模拟数据 (TODO: 未来可通过 DataProvider 添加实时报价支持)
            return self._generate_mock_quotes(option_symbols)

        except Exception as e:
            logger.error(f"获取期权报价失败: {e}")
            return {
                'success': False,
                'error': f"期权报价获取失败: {str(e)}"
            }

    def get_underlying_stock_data(self, symbol: str) -> Dict[str, Any]:
        """
        获取标的股票数据（优化版本：含趋势分析所需数据）

        Args:
            symbol: 股票代码

        Returns:
            股票数据（含价格历史、ATR、技术指标等）
        """
        try:
            cache_key = f"stock_{symbol}"

            # 检查缓存
            if self._is_cache_valid(cache_key):
                return self._cache[cache_key]['data']

            logger.info(f"获取标的股票数据: {symbol}")

            # 使用DataProvider获取股票数据 (yfinance + defeatbeta fallback)
            ticker = _create_ticker(symbol)

            # 获取基本信息
            info = ticker.info

            # 获取历史价格数据（扩展到3个月以获取更多数据）
            hist = ticker.history(period="3mo")

            # 获取期权到期日
            expiry_dates = ticker.options if hasattr(ticker, 'options') else []

            # 计算技术指标
            current_price = info.get('regularMarketPrice', hist['Close'].iloc[-1] if not hist.empty else None)
            previous_close = info.get('regularMarketPreviousClose', hist['Close'].iloc[-2] if len(hist) >= 2 else current_price)

            result = {
                'success': True,
                'symbol': symbol,
                'current_price': current_price,
                'previous_close': previous_close,
                'change': current_price - previous_close if current_price and previous_close else 0,
                'change_percent': ((current_price - previous_close) / previous_close * 100) if current_price and previous_close else 0,
                'volume': info.get('regularMarketVolume'),
                'market_cap': info.get('marketCap'),
                'info': info,
                'history': hist.to_dict() if not hist.empty else {},
                'expiry_dates': expiry_dates,
                'volatility_30d': self._calculate_volatility(hist),
                'support_resistance': self._calculate_support_resistance(hist),
            }

            # 新增：趋势分析所需的价格历史数据
            if not hist.empty:
                result['price_history'] = hist['Close'].tolist()
                result['high_prices'] = hist['High'].tolist()
                result['low_prices'] = hist['Low'].tolist()
                result['close_prices'] = hist['Close'].tolist()

                # 计算ATR
                result['atr_14'] = self._calculate_atr(hist)

                # 计算移动平均线
                if len(hist) >= 50:
                    result['ma_50'] = float(hist['Close'].rolling(window=50).mean().iloc[-1])
                if len(hist) >= 20:
                    result['ma_20'] = float(hist['Close'].rolling(window=20).mean().iloc[-1])

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

    def _calculate_atr(self, hist_data: pd.DataFrame, period: int = 14) -> float:
        """计算ATR（Average True Range）"""
        try:
            if len(hist_data) < period + 1:
                return 0

            high = hist_data['High'].values
            low = hist_data['Low'].values
            close = hist_data['Close'].values

            # 计算True Range
            tr1 = high[1:] - low[1:]
            tr2 = np.abs(high[1:] - close[:-1])
            tr3 = np.abs(low[1:] - close[:-1])

            tr = np.maximum(np.maximum(tr1, tr2), tr3)

            # 计算ATR（简单移动平均）
            atr = np.mean(tr[-period:])

            return round(float(atr), 4)

        except Exception as e:
            logger.error(f"ATR计算失败: {e}")
            return 0

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
            ticker = _create_ticker(symbol)

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

    def _calculate_support_resistance(self, hist_data: pd.DataFrame) -> Dict[str, Any]:
        """
        计算多周期支撑阻力位（优化版本）

        多方法综合计算：
        1. Pivot Points (经典技术分析)
        2. 移动平均线 (MA20, MA50, MA200)
        3. 摆动高低点 (Swing Highs/Lows)
        4. 斐波那契回调位
        """
        try:
            if hist_data.empty:
                return {}

            close = hist_data['Close'].iloc[-1]
            high_period = hist_data['High'].max()
            low_period = hist_data['Low'].min()

            result = {
                'high_52w': float(high_period),
                'low_52w': float(low_period),
                'current_price': float(close),
            }

            # 1. Pivot Points 计算
            pivot_levels = self._calculate_pivot_points(hist_data)
            result.update(pivot_levels)

            # 2. 移动平均线支撑阻力
            ma_levels = self._calculate_ma_levels(hist_data)
            result.update(ma_levels)

            # 3. 摆动高低点
            swing_levels = self._find_swing_highs_lows(hist_data)
            result.update(swing_levels)

            # 4. 斐波那契回调位
            fib_levels = self._calculate_fibonacci_levels(hist_data)
            result.update(fib_levels)

            # 5. 汇总关键支撑阻力位（多方法交叉验证）
            consolidated = self._consolidate_levels(result, close)
            result.update(consolidated)

            return result

        except Exception as e:
            logger.error(f"计算支撑阻力失败: {e}")
            return {}

    def _calculate_pivot_points(self, hist_data: pd.DataFrame) -> Dict[str, float]:
        """计算Pivot Points (经典日内交易支撑阻力)"""
        try:
            # 使用最近一个交易日的数据
            if len(hist_data) < 1:
                return {}

            prev_high = hist_data['High'].iloc[-1]
            prev_low = hist_data['Low'].iloc[-1]
            prev_close = hist_data['Close'].iloc[-1]

            # 计算Pivot Point
            pivot = (prev_high + prev_low + prev_close) / 3

            # 支撑位
            s1 = 2 * pivot - prev_high
            s2 = pivot - (prev_high - prev_low)
            s3 = prev_low - 2 * (prev_high - pivot)

            # 阻力位
            r1 = 2 * pivot - prev_low
            r2 = pivot + (prev_high - prev_low)
            r3 = prev_high + 2 * (pivot - prev_low)

            return {
                'pivot_point': float(pivot),
                'pivot_r1': float(r1),
                'pivot_r2': float(r2),
                'pivot_r3': float(r3),
                'pivot_s1': float(s1),
                'pivot_s2': float(s2),
                'pivot_s3': float(s3),
            }

        except Exception as e:
            logger.error(f"Pivot Points计算失败: {e}")
            return {}

    def _calculate_ma_levels(self, hist_data: pd.DataFrame) -> Dict[str, float]:
        """计算移动平均线支撑阻力"""
        try:
            closes = hist_data['Close']
            result = {}

            # MA20
            if len(closes) >= 20:
                result['ma_20'] = float(closes.rolling(window=20).mean().iloc[-1])

            # MA50
            if len(closes) >= 50:
                result['ma_50'] = float(closes.rolling(window=50).mean().iloc[-1])
            elif len(closes) >= 20:
                # 数据不足时使用可用数据
                result['ma_50'] = float(closes.mean())

            # MA200 (如果数据足够)
            if len(closes) >= 200:
                result['ma_200'] = float(closes.rolling(window=200).mean().iloc[-1])
            elif len(closes) >= 50:
                result['ma_200'] = float(closes.rolling(window=len(closes)).mean().iloc[-1])

            return result

        except Exception as e:
            logger.error(f"MA计算失败: {e}")
            return {}

    def _find_swing_highs_lows(self, hist_data: pd.DataFrame, window: int = 5) -> Dict[str, Any]:
        """找到摆动高低点（局部极值）"""
        try:
            if len(hist_data) < window * 2:
                return {}

            highs = hist_data['High'].values
            lows = hist_data['Low'].values

            swing_highs = []
            swing_lows = []

            for i in range(window, len(highs) - window):
                # 检查是否为局部最高点
                if highs[i] == max(highs[i-window:i+window+1]):
                    swing_highs.append({
                        'price': float(highs[i]),
                        'index': i,
                        'date': hist_data.index[i].strftime('%Y-%m-%d') if hasattr(hist_data.index[i], 'strftime') else str(hist_data.index[i])
                    })

                # 检查是否为局部最低点
                if lows[i] == min(lows[i-window:i+window+1]):
                    swing_lows.append({
                        'price': float(lows[i]),
                        'index': i,
                        'date': hist_data.index[i].strftime('%Y-%m-%d') if hasattr(hist_data.index[i], 'strftime') else str(hist_data.index[i])
                    })

            # 按价格排序，取最近的几个
            swing_highs.sort(key=lambda x: x['index'], reverse=True)
            swing_lows.sort(key=lambda x: x['index'], reverse=True)

            result = {
                'swing_highs': swing_highs[:3],  # 最近3个摆动高点
                'swing_lows': swing_lows[:3],    # 最近3个摆动低点
            }

            # 最近的摆动高低点作为关键阻力支撑
            if swing_highs:
                result['recent_swing_high'] = swing_highs[0]['price']
            if swing_lows:
                result['recent_swing_low'] = swing_lows[0]['price']

            return result

        except Exception as e:
            logger.error(f"摆动高低点计算失败: {e}")
            return {}

    def _calculate_fibonacci_levels(self, hist_data: pd.DataFrame) -> Dict[str, float]:
        """计算斐波那契回调位"""
        try:
            high = hist_data['High'].max()
            low = hist_data['Low'].min()
            diff = high - low

            # 斐波那契回调水平
            fib_levels = {
                'fib_0': float(low),           # 0%
                'fib_236': float(low + diff * 0.236),   # 23.6%
                'fib_382': float(low + diff * 0.382),   # 38.2%
                'fib_500': float(low + diff * 0.5),     # 50%
                'fib_618': float(low + diff * 0.618),   # 61.8%
                'fib_786': float(low + diff * 0.786),   # 78.6%
                'fib_100': float(high),         # 100%
            }

            return fib_levels

        except Exception as e:
            logger.error(f"斐波那契计算失败: {e}")
            return {}

    def _consolidate_levels(self, all_levels: Dict, current_price: float) -> Dict[str, Any]:
        """
        汇总多方法的支撑阻力位，找出关键水平

        多个方法都认可的位置更可靠
        """
        try:
            # 收集所有支撑位候选（低于当前价格）
            support_candidates = []
            # 收集所有阻力位候选（高于当前价格）
            resistance_candidates = []

            # 定义价格聚类阈值（2%以内认为是同一水平）
            cluster_threshold = current_price * 0.02

            # 添加各种方法的水平
            level_sources = [
                ('pivot_s1', 'Pivot'),
                ('pivot_s2', 'Pivot'),
                ('ma_20', 'MA'),
                ('ma_50', 'MA'),
                ('ma_200', 'MA'),
                ('recent_swing_low', 'Swing'),
                ('fib_236', 'Fib'),
                ('fib_382', 'Fib'),
                ('fib_500', 'Fib'),
                ('fib_618', 'Fib'),
            ]

            for key, source in level_sources:
                level = all_levels.get(key)
                if level and level > 0:
                    if level < current_price:
                        support_candidates.append({
                            'price': level,
                            'source': source,
                            'key': key
                        })
                    else:
                        resistance_candidates.append({
                            'price': level,
                            'source': source,
                            'key': key
                        })

            # 添加阻力位来源
            resistance_sources = [
                ('pivot_r1', 'Pivot'),
                ('pivot_r2', 'Pivot'),
                ('recent_swing_high', 'Swing'),
                ('high_52w', '52W'),
            ]

            for key, source in resistance_sources:
                level = all_levels.get(key)
                if level and level > current_price:
                    resistance_candidates.append({
                        'price': level,
                        'source': source,
                        'key': key
                    })

            # 聚类相近的水平
            def cluster_levels(candidates, threshold):
                if not candidates:
                    return []

                # 按价格排序
                sorted_candidates = sorted(candidates, key=lambda x: x['price'])
                clusters = []
                current_cluster = [sorted_candidates[0]]

                for i in range(1, len(sorted_candidates)):
                    if abs(sorted_candidates[i]['price'] - current_cluster[0]['price']) <= threshold:
                        current_cluster.append(sorted_candidates[i])
                    else:
                        clusters.append(current_cluster)
                        current_cluster = [sorted_candidates[i]]

                clusters.append(current_cluster)
                return clusters

            # 处理支撑位聚类
            support_clusters = cluster_levels(support_candidates, cluster_threshold)
            resistance_clusters = cluster_levels(resistance_candidates, cluster_threshold)

            # 计算每个聚类的强度和代表价格
            def score_cluster(cluster):
                avg_price = np.mean([c['price'] for c in cluster])
                sources = set(c['source'] for c in cluster)
                strength = len(cluster) * 20 + len(sources) * 15  # 多方法确认加分
                return {
                    'price': float(avg_price),
                    'strength': min(100, strength),
                    'sources': list(sources),
                    'method_count': len(sources)
                }

            # 选择最强的支撑阻力位
            scored_supports = [score_cluster(c) for c in support_clusters]
            scored_resistances = [score_cluster(c) for c in resistance_clusters]

            # 按强度排序
            scored_supports.sort(key=lambda x: x['strength'], reverse=True)
            scored_resistances.sort(key=lambda x: x['strength'], reverse=True)

            result = {
                'key_supports': scored_supports[:3],  # 前3个强支撑
                'key_resistances': scored_resistances[:3],  # 前3个强阻力
            }

            # 兼容旧接口：设置 support_1, resistance_1 等
            if scored_supports:
                result['support_1'] = scored_supports[0]['price']
                result['support_1_strength'] = scored_supports[0]['strength']
            if len(scored_supports) > 1:
                result['support_2'] = scored_supports[1]['price']
                result['support_2_strength'] = scored_supports[1]['strength']

            if scored_resistances:
                result['resistance_1'] = scored_resistances[0]['price']
                result['resistance_1_strength'] = scored_resistances[0]['strength']
            if len(scored_resistances) > 1:
                result['resistance_2'] = scored_resistances[1]['price']
                result['resistance_2_strength'] = scored_resistances[1]['strength']

            return result

        except Exception as e:
            logger.error(f"支撑阻力汇总失败: {e}")
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
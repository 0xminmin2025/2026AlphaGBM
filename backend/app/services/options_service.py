"""
Option Service Backend Logic
Ported from new_options_module/option_service.py and consolidated with Flask logic

All data access goes through DataProvider (which uses MarketDataService) for:
- Unified metrics tracking
- Multi-provider failover
- Automatic caching
"""

from datetime import datetime, timedelta
import math
import pandas as pd
from typing import List, Optional, Union
import random
import time
import numpy as np
import logging

# Internal services - use DataProvider for all data access
from .data_provider import DataProvider
from .option_models import OptionData, OptionChainResponse, ExpirationDate, ExpirationResponse, StockQuote, EnhancedAnalysisResponse, VRPResult as VRPResultModel, RiskAnalysis as RiskAnalysisModel
from .option_scorer import OptionScorer

logger = logging.getLogger(__name__)

# Try importing Phase 1 modules
try:
    from .phase1.vrp_calculator import VRPCalculator, VRPResult
    from .phase1.risk_adjuster import RiskAdjuster, RiskAnalysis, RiskLevel
    PHASE1_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Phase 1 modules not available: {e}")
    PHASE1_AVAILABLE = False

# Configuration
USE_MOCK_DATA = False # Default to Real Data

option_scorer = OptionScorer()
vrp_calculator = VRPCalculator() if PHASE1_AVAILABLE else None
risk_adjuster = RiskAdjuster() if PHASE1_AVAILABLE else None

class MockDataGenerator:
    """Generates mock option data for testing"""

    # 支持日权（0DTE / Daily Options）的标的
    # SPY, QQQ, IWM 等主流 ETF 和指数期权有每日到期
    DAILY_EXPIRY_SYMBOLS = ['SPY', 'QQQ', 'IWM', 'SPX', 'XSP']

    @staticmethod
    def generate_expirations(symbol: str) -> List[ExpirationDate]:
        """Generate mock expiration dates - 生成到期日列表"""
        expirations = []
        base_date = datetime.now()
        seen_dates = set()

        # 日权：为 SPY, QQQ, IWM 等添加每日到期（周一至周五）
        if symbol.upper() in MockDataGenerator.DAILY_EXPIRY_SYMBOLS:
            for day_offset in range(0, 14):  # 未来14天
                exp_date = base_date + timedelta(days=day_offset)
                # 只包含工作日（周一至周五）
                if exp_date.weekday() < 5:
                    date_str = exp_date.strftime("%Y-%m-%d")
                    if date_str not in seen_dates:
                        seen_dates.add(date_str)
                        # period_tag: d=日权, w=周权, m=月权
                        expirations.append(ExpirationDate(
                            date=date_str,
                            timestamp=int(exp_date.timestamp() * 1000),
                            period_tag="d"  # 日权
                        ))

        # Generate weekly and monthly expirations for next 3 months
        for week in range(1, 13):  # 12 weeks
            exp_date = base_date + timedelta(weeks=week)
            # Friday expirations
            days_until_friday = (4 - exp_date.weekday()) % 7
            if days_until_friday == 0 and exp_date.weekday() != 4:
                days_until_friday = 7
            exp_date += timedelta(days=days_until_friday)

            date_str = exp_date.strftime("%Y-%m-%d")
            if date_str not in seen_dates:
                seen_dates.add(date_str)
                # Monthly options on 3rd Friday
                is_monthly = exp_date.day >= 15 and exp_date.day <= 21
                period_tag = "m" if is_monthly else "w"

                expirations.append(ExpirationDate(
                    date=date_str,
                    timestamp=int(exp_date.timestamp() * 1000),
                    period_tag=period_tag
                ))

        return sorted(expirations, key=lambda x: x.timestamp)

    @staticmethod
    def generate_option_chain(symbol: str, expiry_date: str, real_price: float = None) -> OptionChainResponse:
        """Generate mock option chain data with scoring"""
        base_price = real_price if real_price is not None else 150.0

        calls = []
        puts = []

        for i in range(-10, 11):  # 21 strikes total
            strike = base_price + (i * 5)  # $5 intervals

            try:
                days_diff = (datetime.strptime(expiry_date, "%Y-%m-%d") - datetime.now()).days
                time_to_expiry = max(0.1, days_diff / 365.0)
            except:
                time_to_expiry = 0.1

            # CALL options
            call_intrinsic = max(0, base_price - strike)
            call_time_value = max(1.0, abs(i) * 2.0 + time_to_expiry * 10)
            call_price = call_intrinsic + call_time_value

            call_option = OptionData(
                identifier=f"{symbol} {expiry_date.replace('-', '')}C{int(strike*1000):08d}",
                symbol=symbol,
                strike=strike,
                put_call="CALL",
                expiry_date=expiry_date,
                latest_price=round(call_price, 2),
                bid_price=round(call_price - 0.05, 2),
                ask_price=round(call_price + 0.05, 2),
                volume=100 + abs(i) * 50,
                open_interest=500 + abs(i) * 100,
                implied_vol=round(0.20 + abs(i) * 0.02, 3),
                delta=round(max(0.01, 0.5 + (base_price - strike) / 100), 3),
                gamma=round(0.01 + abs(i) * 0.002, 4),
                theta=round(-0.05 - time_to_expiry * 0.1, 3),
                vega=round(time_to_expiry * 20, 2)
            )
            call_option.scores = option_scorer.score_option(call_option, base_price)
            calls.append(call_option)

            # PUT options
            put_intrinsic = max(0, strike - base_price)
            put_time_value = max(1.0, abs(i) * 2.0 + time_to_expiry * 10)
            put_price = put_intrinsic + put_time_value

            put_option = OptionData(
                identifier=f"{symbol} {expiry_date.replace('-', '')}P{int(strike*1000):08d}",
                symbol=symbol,
                strike=strike,
                put_call="PUT",
                expiry_date=expiry_date,
                latest_price=round(put_price, 2),
                bid_price=round(put_price - 0.05, 2),
                ask_price=round(put_price + 0.05, 2),
                volume=80 + abs(i) * 40,
                open_interest=400 + abs(i) * 80,
                implied_vol=round(0.22 + abs(i) * 0.02, 3),
                delta=round(min(-0.01, -0.5 + (base_price - strike) / 100), 3),
                gamma=round(0.01 + abs(i) * 0.002, 4),
                theta=round(-0.04 - time_to_expiry * 0.08, 3),
                vega=round(time_to_expiry * 18, 2)
            )
            put_option.scores = option_scorer.score_option(put_option, base_price)
            puts.append(put_option)

        data_source = "hybrid" if real_price is not None else "mock"
        return OptionChainResponse(
            symbol=symbol,
            expiry_date=expiry_date,
            calls=calls,
            puts=puts,
            data_source=data_source,
            real_stock_price=base_price  # Always return the price used for option calculations
        )

mock_generator = MockDataGenerator()

class OptionsService:

    @staticmethod
    def get_expirations(symbol: str) -> ExpirationResponse:
        """Get option expiration dates using DataProvider (unified data access)."""
        try:
            symbol = symbol.upper()
            if not USE_MOCK_DATA:
                try:
                    # Use DataProvider for unified data access with metrics tracking
                    provider = DataProvider(symbol)
                    expiry_dates = provider.options  # Returns tuple of date strings

                    if expiry_dates:
                        expirations = []
                        for date_str in expiry_dates:
                            try:
                                # Parse date and create ExpirationDate
                                exp_date = datetime.strptime(date_str, "%Y-%m-%d")
                                # Determine period tag (weekly/monthly)
                                is_monthly = exp_date.day >= 15 and exp_date.day <= 21 and exp_date.weekday() == 4
                                period_tag = "m" if is_monthly else "w"

                                expirations.append(ExpirationDate(
                                    date=date_str,
                                    timestamp=int(exp_date.timestamp() * 1000),
                                    period_tag=period_tag
                                ))
                            except ValueError:
                                continue

                        if expirations:
                            return ExpirationResponse(symbol=symbol, expirations=expirations)
                except Exception as e:
                    logger.warning(f"DataProvider options failed for {symbol}: {e}")

            # Fallback to mock data
            expirations = mock_generator.generate_expirations(symbol)
            return ExpirationResponse(symbol=symbol, expirations=expirations)
        except Exception as e:
            raise e

    @staticmethod
    def get_option_chain(symbol: str, expiry_date: str) -> OptionChainResponse:
        """Get option chain using DataProvider (unified data access)."""
        try:
            symbol = symbol.upper()

            # Validate format
            try:
                datetime.strptime(expiry_date, "%Y-%m-%d")
            except ValueError:
                raise ValueError("Invalid date format. Use YYYY-MM-DD")

            if not USE_MOCK_DATA:
                try:
                    # Use DataProvider for unified data access with metrics tracking
                    provider = DataProvider(symbol)

                    # Get stock price first
                    info = provider.info
                    real_stock_price = info.get('regularMarketPrice') or info.get('currentPrice') or 150.0

                    # Get option chain
                    chain = provider.option_chain(expiry_date)

                    if chain and chain.calls is not None and chain.puts is not None:
                        calls = []
                        puts = []

                        # Get margin rate for scoring
                        margin_rate = provider.get_margin_rate()

                        logger.info(f"[OptionChain] DataProvider returned chain for {symbol} {expiry_date}")

                        # Process calls
                        if not chain.calls.empty:
                            for _, row in chain.calls.iterrows():
                                option_data = OptionsService._row_to_option_data(row, symbol, expiry_date, 'CALL')
                                option_data.scores = option_scorer.score_option(option_data, real_stock_price, margin_rate)
                                calls.append(option_data)

                        # Process puts
                        if not chain.puts.empty:
                            for _, row in chain.puts.iterrows():
                                option_data = OptionsService._row_to_option_data(row, symbol, expiry_date, 'PUT')
                                option_data.scores = option_scorer.score_option(option_data, real_stock_price, margin_rate)
                                puts.append(option_data)

                        if calls or puts:
                            return OptionChainResponse(
                                symbol=symbol,
                                expiry_date=expiry_date,
                                calls=calls,
                                puts=puts,
                                data_source="real",
                                real_stock_price=real_stock_price
                            )
                except Exception as e:
                    logger.warning(f"DataProvider option_chain failed for {symbol}: {e}")

            # Mock fallback - try to get real stock price first
            real_price = None
            try:
                provider = DataProvider(symbol)
                info = provider.info
                real_price = info.get('regularMarketPrice') or info.get('currentPrice')
            except:
                pass

            return mock_generator.generate_option_chain(symbol, expiry_date, real_price)

        except Exception as e:
            raise e

    @staticmethod
    def _row_to_option_data(row: pd.Series, symbol: str, expiry_date: str, put_call: str) -> OptionData:
        """Convert a DataFrame row to OptionData object."""
        def safe_float(val, default=None):
            if pd.notna(val):
                try:
                    return float(val)
                except (ValueError, TypeError):
                    pass
            return default

        def safe_int(val, default=None):
            if pd.notna(val):
                try:
                    return int(val)
                except (ValueError, TypeError):
                    pass
            return default

        # Handle different column naming conventions
        strike = safe_float(row.get('strike') or row.get('strike_price'))
        latest_price = safe_float(row.get('lastPrice') or row.get('latest_price') or row.get('lastTradePrice'))
        bid = safe_float(row.get('bid') or row.get('bid_price'))
        ask = safe_float(row.get('ask') or row.get('ask_price'))
        volume = safe_int(row.get('volume'))
        open_interest = safe_int(row.get('openInterest') or row.get('open_interest'))
        implied_vol = safe_float(row.get('impliedVolatility') or row.get('implied_vol') or row.get('volatility'))
        delta = safe_float(row.get('delta'))
        gamma = safe_float(row.get('gamma'))
        theta = safe_float(row.get('theta'))
        vega = safe_float(row.get('vega'))

        # Generate identifier if not present
        identifier = row.get('identifier') or row.get('contractSymbol') or f"{symbol}{expiry_date.replace('-', '')}{put_call[0]}{int((strike or 0)*1000):08d}"

        return OptionData(
            identifier=identifier,
            symbol=symbol,
            strike=strike or 0.0,
            put_call=put_call,
            expiry_date=expiry_date,
            bid_price=bid,
            ask_price=ask,
            latest_price=latest_price,
            volume=volume,
            open_interest=open_interest,
            implied_vol=implied_vol,
            delta=delta,
            gamma=gamma,
            theta=theta,
            vega=vega
        )

    @staticmethod
    def get_stock_history(symbol: str, days: int = 60):
        """Get stock OHLC history data using DataProvider (unified data access)."""
        try:
            symbol = symbol.upper()
            logger.info(f"Fetching {days} days of history for {symbol} using DataProvider...")

            # Use DataProvider with automatic multi-provider fallback
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days + 10)  # Extra days to ensure enough data

            stock = DataProvider(symbol)
            hist = stock.history(start=start_date, end=end_date)

            if hist.empty:
                logger.warning(f"No history data returned for {symbol}")
                return {"symbol": symbol, "data": [], "error": "No data available"}

            # Convert to candlestick format for lightweight-charts
            candlestick_data = []
            for date, row in hist.iterrows():
                # Convert pandas timestamp to unix timestamp (seconds)
                timestamp = int(date.timestamp())
                candlestick_data.append({
                    "time": timestamp,
                    "open": round(float(row['Open']), 2),
                    "high": round(float(row['High']), 2),
                    "low": round(float(row['Low']), 2),
                    "close": round(float(row['Close']), 2)
                })

            # Sort by time ascending
            candlestick_data.sort(key=lambda x: x['time'])

            # Limit to requested days
            if len(candlestick_data) > days:
                candlestick_data = candlestick_data[-days:]

            logger.info(f"Successfully fetched {len(candlestick_data)} days of OHLC data for {symbol}")
            return {"symbol": symbol, "data": candlestick_data}

        except Exception as e:
            logger.error(f"Error fetching stock history for {symbol}: {e}")
            return {"symbol": symbol, "data": [], "error": str(e)}

    @staticmethod
    def get_stock_quote(symbol):
        """Get stock quote using DataProvider (unified data access)."""
        try:
            symbol = symbol.upper()
            if not USE_MOCK_DATA:
                try:
                    provider = DataProvider(symbol)
                    info = provider.info

                    if info:
                        current_price = info.get('regularMarketPrice') or info.get('currentPrice')
                        prev_close = info.get('regularMarketPreviousClose') or info.get('previousClose')
                        volume = info.get('regularMarketVolume') or info.get('volume') or 0

                        if current_price:
                            change = 0.0
                            change_percent = 0.0
                            if prev_close and prev_close > 0:
                                change = current_price - prev_close
                                change_percent = (change / prev_close) * 100

                            return StockQuote(
                                symbol=symbol,
                                latest_price=float(current_price),
                                change=float(change),
                                change_percent=float(change_percent),
                                volume=int(volume)
                            )
                except Exception as e:
                    logger.warning(f"DataProvider get_stock_quote failed for {symbol}: {e}")

            # Mock fallback
            return StockQuote(
                symbol=symbol,
                latest_price=150.25,
                change=2.15,
                change_percent=1.45,
                volume=1234567
            )
        except Exception as e:
            raise e

    @staticmethod
    def get_enhanced_analysis(symbol: str, option_identifier: str) -> EnhancedAnalysisResponse:
        """Get enhanced options analysis using DataProvider (unified data access)."""
        if not PHASE1_AVAILABLE or not vrp_calculator or not risk_adjuster:
            return EnhancedAnalysisResponse(symbol=symbol, option_identifier=option_identifier, available=False)

        try:
            symbol = symbol.upper()

            # 1. Get price history using DataProvider
            provider = DataProvider(symbol)
            hist = provider.history(period='3mo')  # ~60 trading days

            if hist.empty or len(hist) < 30:
                return EnhancedAnalysisResponse(
                    symbol=symbol, option_identifier=option_identifier, vrp_result=None, risk_analysis=None, available=True
                )

            # Extract close prices as a list
            price_history = hist['Close'].tolist()

            # 2. Calculate VRP
            returns = []
            for i in range(1, len(price_history)):
                if price_history[i-1] > 0:
                    returns.append(math.log(price_history[i] / price_history[i-1]))

            if returns:
                hist_vol = np.std(returns) * math.sqrt(252)
                estimated_iv = hist_vol  # Placeholder
                vrp_result_data = vrp_calculator.calculate_vrp_result(
                    current_iv=estimated_iv,
                    price_history=price_history
                )
                vrp_result = VRPResultModel(
                    vrp=vrp_result_data.vrp,
                    iv=vrp_result_data.iv,
                    rv_forecast=vrp_result_data.rv_forecast,
                    iv_rank=vrp_result_data.iv_rank,
                    iv_percentile=vrp_result_data.iv_percentile,
                    recommendation=vrp_result_data.recommendation
                )
            else:
                vrp_result = None

            return EnhancedAnalysisResponse(
                symbol=symbol,
                option_identifier=option_identifier,
                vrp_result=vrp_result,
                risk_analysis=None,  # Requires specific option data retrieval which is separate
                available=True
            )
        except Exception as e:
            logger.error(f"Error in enhanced analysis: {e}")
            return EnhancedAnalysisResponse(symbol=symbol, option_identifier=option_identifier, available=False)

    @staticmethod
    def reverse_score_option(symbol: str, option_type: str, strike: float,
                            expiry_date: str, option_price: float,
                            implied_volatility: float = None) -> dict:
        """
        反向查分：根据用户输入的期权参数计算评分

        Args:
            symbol: 股票代码
            option_type: 期权类型 ('CALL' 或 'PUT')
            strike: 执行价
            expiry_date: 到期日 (YYYY-MM-DD)
            option_price: 期权价格 (bid/ask中间价)
            implied_volatility: 隐含波动率 (可选，留空自动估算)

        Returns:
            包含评分结果的字典
        """
        try:
            from datetime import datetime

            # Import DataProvider for multi-provider support
            try:
                from .data_provider import DataProvider
            except ImportError:
                DataProvider = None

            symbol = symbol.upper()
            option_type = option_type.upper()

            # 1. 获取股票当前价格和数据（使用DataProvider统一数据访问）
            ticker = DataProvider(symbol)

            current_price = None
            info = {}

            # 方法1: 从 info 获取
            try:
                info = ticker.info
                current_price = info.get('regularMarketPrice') or info.get('currentPrice') or info.get('previousClose')
                if current_price:
                    current_price = float(current_price)
            except Exception as e:
                print(f"从 ticker.info 获取 {symbol} 价格失败: {e}")

            # 方法2: 从最近历史数据获取
            if not current_price:
                try:
                    hist = ticker.history(period="5d")
                    if not hist.empty:
                        current_price = float(hist['Close'].iloc[-1])
                except Exception as e:
                    print(f"从 ticker.history 获取 {symbol} 价格失败: {e}")

            # 方法3: 从 fast_info 获取 (yfinance only)
            if not current_price and hasattr(ticker, 'fast_info'):
                try:
                    fast_info = ticker.fast_info
                    current_price = float(fast_info.get('lastPrice', 0) or fast_info.get('previousClose', 0))
                    if current_price <= 0:
                        current_price = None
                except Exception as e:
                    print(f"从 ticker.fast_info 获取 {symbol} 价格失败: {e}")

            if not current_price:
                return {
                    'success': False,
                    'error': f'无法获取 {symbol} 的当前股价，请检查股票代码是否正确'
                }

            # 2. 获取股票历史数据用于趋势分析
            try:
                hist_3mo = ticker.history(period="3mo")
                price_history = hist_3mo['Close'].tolist() if not hist_3mo.empty else []
            except Exception as e:
                print(f"获取 {symbol} 历史数据失败: {e}")
                hist_3mo = None
                price_history = []

            # 计算ATR
            atr_14 = 0
            if hist_3mo is not None and not hist_3mo.empty and len(hist_3mo) >= 15:
                try:
                    high = hist_3mo['High'].values
                    low = hist_3mo['Low'].values
                    close = hist_3mo['Close'].values
                    tr1 = high[1:] - low[1:]
                    tr2 = np.abs(high[1:] - close[:-1])
                    tr3 = np.abs(low[1:] - close[:-1])
                    tr = np.maximum(np.maximum(tr1, tr2), tr3)
                    atr_14 = float(np.mean(tr[-14:]))
                except Exception as e:
                    print(f"计算 {symbol} ATR 失败: {e}")
                    atr_14 = 0

            # 3. 如果没有提供隐含波动率，自动估算
            if implied_volatility is None or implied_volatility <= 0:
                # 使用历史波动率估算
                if len(price_history) >= 30:
                    returns = np.diff(np.log(price_history[-30:]))
                    implied_volatility = float(np.std(returns) * np.sqrt(252))
                else:
                    implied_volatility = 0.25  # 默认25%

            # 4. 计算到期天数
            try:
                expiry = datetime.strptime(expiry_date, "%Y-%m-%d")
                today = datetime.now()
                days_to_expiry = max(1, (expiry - today).days)
            except:
                days_to_expiry = 30

            # 5. 估算Greeks（简化计算）
            # Delta估算（基于货币性和到期时间）
            moneyness = strike / current_price
            time_factor = min(1, days_to_expiry / 365)

            if option_type == "CALL":
                # Call Delta: 虚值越深delta越小
                if moneyness > 1.1:  # 深度虚值
                    delta = max(0.05, 0.5 - (moneyness - 1) * 2)
                elif moneyness < 0.9:  # 深度实值
                    delta = min(0.95, 0.5 + (1 - moneyness) * 2)
                else:
                    delta = 0.5 + (1 - moneyness) * 0.5
            else:  # PUT
                if moneyness < 0.9:  # 深度虚值
                    delta = max(-0.95, -0.5 - (1 - moneyness) * 2)
                elif moneyness > 1.1:  # 深度实值
                    delta = min(-0.05, -0.5 + (moneyness - 1) * 2)
                else:
                    delta = -0.5 + (1 - moneyness) * 0.5

            # Gamma 估算 (ATM附近最大)
            gamma = 0.05 * np.exp(-((moneyness - 1) ** 2) / 0.02) * (1 / np.sqrt(time_factor + 0.01))

            # Theta 估算 (负数，ATM附近最大)
            theta = -option_price * 0.02 * (1 / np.sqrt(days_to_expiry + 1))

            # 6. 构建 OptionData 对象
            option_data = OptionData(
                identifier=f"{symbol}{expiry_date.replace('-', '')}{option_type[0]}{int(strike*1000):08d}",
                symbol=symbol,
                strike=strike,
                put_call=option_type,
                expiry_date=expiry_date,
                latest_price=option_price,
                bid_price=option_price * 0.98,  # 估算
                ask_price=option_price * 1.02,
                volume=100,  # 默认值
                open_interest=500,  # 默认值
                implied_vol=implied_volatility,
                delta=delta,
                gamma=gamma,
                theta=theta,
                vega=option_price * 0.1  # 估算
            )

            # 7. 使用 OptionScorer 计算评分
            scores = option_scorer.score_option(option_data, current_price)

            # 8. 使用高级评分器计算趋势相关评分
            # 导入趋势分析器
            try:
                from ..analysis.options_analysis.scoring.trend_analyzer import TrendAnalyzer
                trend_analyzer = TrendAnalyzer()

                import pandas as pd
                if len(price_history) >= 6:
                    price_series = pd.Series(price_history)
                    strategy = 'sell_call' if option_type == 'CALL' else 'sell_put'
                    trend_info = trend_analyzer.analyze_trend_for_strategy(
                        price_series, current_price, strategy
                    )
                else:
                    trend_info = {
                        'trend': 'sideways',
                        'trend_strength': 0.5,
                        'trend_alignment_score': 60,
                        'display_info': {
                            'trend_name_cn': '横盘整理',
                            'is_ideal_trend': False,
                            'warning': '数据不足，无法判断趋势'
                        }
                    }
            except Exception as e:
                print(f"趋势分析失败: {e}")
                trend_info = {
                    'trend': 'unknown',
                    'trend_strength': 0.5,
                    'trend_alignment_score': 50,
                    'display_info': {
                        'trend_name_cn': '未知',
                        'is_ideal_trend': False,
                        'warning': '趋势分析不可用'
                    }
                }

            # 9. 计算支撑阻力位
            support_resistance = {}
            if hist_3mo is not None and not hist_3mo.empty:
                try:
                    high_52w = float(hist_3mo['High'].max())
                    low_52w = float(hist_3mo['Low'].min())
                    ma_20 = float(hist_3mo['Close'].rolling(20).mean().iloc[-1]) if len(hist_3mo) >= 20 else current_price
                    ma_50 = float(hist_3mo['Close'].rolling(50).mean().iloc[-1]) if len(hist_3mo) >= 50 else current_price

                    support_resistance = {
                        'high_52w': high_52w,
                        'low_52w': low_52w,
                        'ma_20': ma_20,
                        'ma_50': ma_50,
                        'support_1': current_price * 0.95,
                        'resistance_1': current_price * 1.05,
                    }
                except Exception as e:
                    print(f"计算 {symbol} 支撑阻力位失败: {e}")

            # 10. 构建返回结果
            # 根据期权类型计算评分
            if option_type == 'CALL':
                sell_score = scores.scrv or 0
                buy_score = scores.bcrv or 0
                total_score = max(sell_score, buy_score)

                scores_dict = {
                    'sell_call': {
                        'score': sell_score,
                        'style_label': '稳健收益' if sell_score >= 60 else '风险较高',
                        'risk_level': 'low' if sell_score >= 70 else ('medium' if sell_score >= 50 else 'high'),
                        'risk_color': '#10B981' if sell_score >= 70 else ('#F59E0B' if sell_score >= 50 else '#EF4444'),
                        'trend_warning': trend_info.get('display_info', {}).get('warning') if not trend_info.get('display_info', {}).get('is_ideal_trend') else None,
                        'breakdown': {
                            'iv_rank': scores.iv_rank,
                            'liquidity': scores.liquidity_factor,
                            'assignment_probability': scores.assignment_probability,
                            'annualized_return': scores.annualized_return,
                        }
                    },
                    'buy_call': {
                        'score': buy_score,
                        'style_label': '激进策略' if buy_score >= 60 else '投机性强',
                        'risk_level': 'low' if buy_score >= 70 else ('medium' if buy_score >= 50 else 'high'),
                        'risk_color': '#10B981' if buy_score >= 70 else ('#F59E0B' if buy_score >= 50 else '#EF4444'),
                        'trend_warning': None if trend_info.get('trend') == 'uptrend' else '当前非上涨趋势，买入风险较高',
                        'breakdown': {
                            'iv_rank': scores.iv_rank,
                            'liquidity': scores.liquidity_factor,
                        }
                    }
                }
            else:  # PUT
                sell_score = scores.sprv or 0
                buy_score = scores.bprv or 0
                total_score = max(sell_score, buy_score)

                scores_dict = {
                    'sell_put': {
                        'score': sell_score,
                        'style_label': '稳健收益' if sell_score >= 60 else '风险较高',
                        'risk_level': 'low' if sell_score >= 70 else ('medium' if sell_score >= 50 else 'high'),
                        'risk_color': '#10B981' if sell_score >= 70 else ('#F59E0B' if sell_score >= 50 else '#EF4444'),
                        'trend_warning': trend_info.get('display_info', {}).get('warning') if not trend_info.get('display_info', {}).get('is_ideal_trend') else None,
                        'breakdown': {
                            'iv_rank': scores.iv_rank,
                            'liquidity': scores.liquidity_factor,
                            'assignment_probability': scores.assignment_probability,
                            'annualized_return': scores.annualized_return,
                            'premium_income': scores.premium_income,
                        }
                    },
                    'buy_put': {
                        'score': buy_score,
                        'style_label': '对冲策略' if buy_score >= 60 else '保险性质',
                        'risk_level': 'low' if buy_score >= 70 else ('medium' if buy_score >= 50 else 'high'),
                        'risk_color': '#10B981' if buy_score >= 70 else ('#F59E0B' if buy_score >= 50 else '#EF4444'),
                        'trend_warning': None if trend_info.get('trend') == 'downtrend' else '当前非下跌趋势，对冲需求可能不高',
                        'breakdown': {
                            'iv_rank': scores.iv_rank,
                            'liquidity': scores.liquidity_factor,
                        }
                    }
                }

            result = {
                'success': True,
                'symbol': symbol,
                'option_type': option_type,
                'strike': strike,
                'expiry_date': expiry_date,
                'days_to_expiry': days_to_expiry,
                'option_price': option_price,
                'implied_volatility': round(implied_volatility * 100, 2),  # 转为百分比
                'current_price': round(current_price, 2),  # 顶层返回当前股价
                'total_score': round(total_score, 1),       # 总评分（取最高策略分）
                'stock_data': {
                    'current_price': round(current_price, 2),
                    'atr_14': round(atr_14, 4),
                    'trend': trend_info.get('trend', 'unknown'),
                    'trend_strength': round(trend_info.get('trend_strength', 0.5), 2),
                    'support_resistance': support_resistance,
                },
                'estimated_greeks': {
                    'delta': round(delta, 4),
                    'gamma': round(gamma, 4),
                    'theta': round(theta, 4),
                },
                'scores': scores_dict,
                'trend_info': trend_info,
            }

            return result

        except Exception as e:
            import traceback
            print(f"反向查分失败: {e}")
            print(traceback.format_exc())
            return {
                'success': False,
                'error': f'反向查分计算失败: {str(e)}'
            }

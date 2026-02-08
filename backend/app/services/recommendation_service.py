"""
期权推荐服务
每日生成热门期权推荐，支持缓存

基于用户实战经验优化：
- 标的选择很重要：不以接股为目的的卖Put都是乱来
- 时机选择：最好在股票下跌时卖更低价格的Put
- 日权风险：日权不适合卖Put策略
"""

import logging
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd

from ..models import db, DailyRecommendation

# Use DataProvider for all data access (unified metrics tracking)
from .data_provider import DataProvider

from .option_scorer import OptionScorer
from .option_models import OptionData
from ..analysis.options_analysis.option_market_config import get_option_market_config

logger = logging.getLogger(__name__)

# 热门股票列表（美股常见期权标的）
# SPY, QQQ, IWM 支持日权（0DTE），是非常活跃的期权交易标的
HOT_SYMBOLS = [
    'SPY', 'QQQ', 'IWM',  # 支持日权的 ETF
    'AAPL', 'NVDA', 'TSLA', 'MSFT', 'GOOGL',
    'META', 'AMZN', 'AMD'
]

# 港股热门期权标的
HK_HOT_SYMBOLS = ['0700.HK', '9988.HK', '3690.HK']

# A股ETF期权标的
CN_HOT_SYMBOLS = ['510050.SS', '510300.SS']

# 期权策略类型
STRATEGIES = ['sell_put', 'sell_call', 'buy_call', 'buy_put']

# ========== 标的质量分级（基于用户实战经验）==========
# 用户观点：标的选择很重要，要选择愿意接股、接了后有信心涨回去的标的
SYMBOL_QUALITY = {
    # Tier 1: 蓝筹ETF/指数，长期持有无忧
    'SPY': {'tier': 1, 'quality': 95, 'description': 'S&P500 ETF，最安全的接股标的'},
    'QQQ': {'tier': 1, 'quality': 90, 'description': 'Nasdaq100 ETF，科技龙头'},
    'IWM': {'tier': 1, 'quality': 85, 'description': 'Russell 2000 ETF'},
    'DIA': {'tier': 1, 'quality': 92, 'description': '道琼斯30 ETF'},
    'VOO': {'tier': 1, 'quality': 95, 'description': 'Vanguard S&P500 ETF'},

    # Tier 2: 大盘蓝筹股，基本面稳健
    'AAPL': {'tier': 2, 'quality': 88, 'description': '苹果，现金流之王'},
    'MSFT': {'tier': 2, 'quality': 90, 'description': '微软，AI+云计算'},
    'GOOGL': {'tier': 2, 'quality': 85, 'description': '谷歌，广告+AI'},
    'AMZN': {'tier': 2, 'quality': 82, 'description': '亚马逊，电商+云'},
    'BRK-B': {'tier': 2, 'quality': 88, 'description': '伯克希尔，巴菲特'},
    'JPM': {'tier': 2, 'quality': 80, 'description': '摩根大通，银行龙头'},
    'V': {'tier': 2, 'quality': 85, 'description': 'Visa，支付网络'},

    # Tier 3: 高成长但波动大
    'NVDA': {'tier': 3, 'quality': 80, 'description': 'AI龙头，波动大'},
    'TSLA': {'tier': 3, 'quality': 70, 'description': '特斯拉，高波动'},
    'AMD': {'tier': 3, 'quality': 75, 'description': 'AMD，周期性'},
    'META': {'tier': 3, 'quality': 78, 'description': 'Meta，社交+AI'},
    'NFLX': {'tier': 3, 'quality': 72, 'description': 'Netflix，流媒体'},
    'CRM': {'tier': 3, 'quality': 76, 'description': 'Salesforce，云SaaS'},

    # Tier 4: 高风险高波动
    'COIN': {'tier': 4, 'quality': 55, 'description': 'Coinbase，加密相关'},
    'MSTR': {'tier': 4, 'quality': 50, 'description': 'MicroStrategy，比特币持仓'},
    'GME': {'tier': 4, 'quality': 40, 'description': 'GameStop，meme股'},
    'AMC': {'tier': 4, 'quality': 40, 'description': 'AMC，meme股'},

    # HK 港股期权标的
    '0700.HK': {'tier': 2, 'quality': 85, 'description': '腾讯，港股科技龙头'},
    '9988.HK': {'tier': 2, 'quality': 80, 'description': '阿里巴巴，电商+云'},
    '3690.HK': {'tier': 3, 'quality': 72, 'description': '美团，本地生活'},

    # CN A股ETF期权标的
    '510050.SS': {'tier': 1, 'quality': 90, 'description': '上证50ETF，A股蓝筹'},
    '510300.SS': {'tier': 1, 'quality': 88, 'description': '沪深300ETF，大盘指数'},
}


class RecommendationService:
    """期权推荐服务"""

    def __init__(self):
        self.scorer = OptionScorer()
        self._price_trend_cache = {}  # 价格趋势缓存

    def get_symbol_quality_score(self, symbol: str) -> Dict[str, Any]:
        """
        获取标的质量评分

        基于用户实战经验：标的选择很重要，要选择愿意接股、接了后有信心涨回去的标的

        Returns:
            {'tier': int, 'quality': float, 'description': str}
        """
        return SYMBOL_QUALITY.get(symbol.upper(), {
            'tier': 5,  # 未知标的默认 Tier 5
            'quality': 50,
            'description': '未评级标的'
        })

    def get_price_trend(self, symbol: str, days: int = 5) -> Dict[str, Any]:
        """
        获取近期价格趋势

        基于用户实战经验：最好在股票下跌时卖更低价格的Put，安全垫要高

        Args:
            symbol: 股票代码
            days: 回溯天数

        Returns:
            {
                'trend': 'down'|'up'|'sideways'|'unknown',
                'change_pct': float,
                'is_good_timing_for_put': bool
            }
        """
        cache_key = f"{symbol}_{days}"
        if cache_key in self._price_trend_cache:
            cached = self._price_trend_cache[cache_key]
            if datetime.now() - cached['time'] < timedelta(hours=1):
                return cached['data']

        try:
            # Use DataProvider if available for fallback support
            ticker = DataProvider(symbol)
            hist = ticker.history(period=f"{days + 2}d")  # 多取2天防止非交易日

            if hist is None or len(hist) < 2:
                return {'trend': 'unknown', 'change_pct': 0, 'is_good_timing_for_put': False}

            first_close = float(hist['Close'].iloc[0])
            last_close = float(hist['Close'].iloc[-1])
            change_pct = (last_close - first_close) / first_close * 100

            if change_pct < -3:
                trend = 'down'
                is_good_timing_for_put = True  # 下跌时是卖Put的好时机
            elif change_pct > 3:
                trend = 'up'
                is_good_timing_for_put = False
            else:
                trend = 'sideways'
                is_good_timing_for_put = True  # 震荡也适合卖Put

            result = {
                'trend': trend,
                'change_pct': round(change_pct, 2),
                'is_good_timing_for_put': is_good_timing_for_put
            }

            # 缓存结果
            self._price_trend_cache[cache_key] = {
                'data': result,
                'time': datetime.now()
            }

            return result

        except Exception as e:
            logger.warning(f"获取 {symbol} 价格趋势失败: {e}")
            return {'trend': 'unknown', 'change_pct': 0, 'is_good_timing_for_put': False}

    def calculate_timing_bonus(self, trend: Dict[str, Any], strategy: str) -> float:
        """
        计算时机加分

        基于用户实战经验：
        - Sell Put 在下跌时加分（逢低卖Put）
        - Sell Call 在上涨时加分

        Returns:
            加分值 (0-10)
        """
        if strategy == 'sell_put' and trend.get('trend') == 'down':
            # 下跌越多，加分越多（最多+10分）
            return min(10, abs(trend.get('change_pct', 0)) * 2)
        elif strategy == 'sell_call' and trend.get('trend') == 'up':
            # 上涨时适合卖Call
            return min(10, abs(trend.get('change_pct', 0)) * 2)
        elif trend.get('trend') == 'sideways':
            # 震荡时卖方策略都有优势
            if strategy.startswith('sell'):
                return 3
        return 0

    def get_daily_recommendations(self, count: int = 5, force_refresh: bool = False) -> Dict[str, Any]:
        """
        获取每日期权推荐

        Args:
            count: 返回推荐数量
            force_refresh: 是否强制刷新（忽略缓存）

        Returns:
            推荐结果字典
        """
        try:
            today = date.today()

            # 检查缓存（如果不强制刷新）
            if not force_refresh:
                cached = DailyRecommendation.query.filter_by(
                    recommendation_date=today
                ).first()

                if cached:
                    logger.info(f"返回缓存的推荐数据，日期: {today}")
                    recommendations = cached.recommendations[:count] if cached.recommendations else []
                    return {
                        'success': True,
                        'recommendations': recommendations,
                        'market_summary': cached.market_summary,
                        'updated_at': cached.updated_at.isoformat() if cached.updated_at else None,
                        'from_cache': True
                    }

            # 生成新推荐
            logger.info(f"生成新的每日推荐，日期: {today}")
            result = self._generate_recommendations(count)

            if result.get('success'):
                # 保存到缓存
                self._save_to_cache(today, result)

            return result

        except Exception as e:
            logger.error(f"获取每日推荐失败: {e}")
            return {
                'success': False,
                'error': f'获取推荐失败: {str(e)}'
            }

    def _generate_recommendations(self, count: int) -> Dict[str, Any]:
        """
        生成期权推荐

        遍历热门股票，分析期权链，选出最佳推荐
        """
        try:
            all_recommendations = []
            market_data = {
                'symbols_analyzed': 0,
                'total_options_scanned': 0,
            }

            # 合并 US + HK + CN 标的池
            all_symbols = HOT_SYMBOLS[:8] + HK_HOT_SYMBOLS + CN_HOT_SYMBOLS

            for symbol in all_symbols:
                try:
                    symbol_recs = self._analyze_symbol(symbol)
                    if symbol_recs:
                        all_recommendations.extend(symbol_recs)
                        market_data['symbols_analyzed'] += 1
                        market_data['total_options_scanned'] += len(symbol_recs)
                except Exception as e:
                    logger.warning(f"分析 {symbol} 失败: {e}")
                    continue

            if not all_recommendations:
                return {
                    'success': False,
                    'error': '无法生成推荐，请稍后重试'
                }

            # 按评分排序
            all_recommendations.sort(key=lambda x: x.get('score', 0), reverse=True)

            # 确保策略多样性：每种策略最多选2个
            diverse_recommendations = self._ensure_diversity(all_recommendations, count)

            # 生成市场摘要
            market_summary = self._generate_market_summary(diverse_recommendations)

            return {
                'success': True,
                'recommendations': diverse_recommendations,
                'market_summary': market_summary,
                'updated_at': datetime.now().isoformat(),
                'from_cache': False
            }

        except Exception as e:
            logger.error(f"生成推荐失败: {e}")
            return {
                'success': False,
                'error': f'生成推荐失败: {str(e)}'
            }

    def _analyze_symbol(self, symbol: str) -> List[Dict[str, Any]]:
        """
        分析单个股票的期权

        基于用户实战经验优化：
        - 排除日权（当天和明天到期的期权），日权接股风险不可控
        - 获取标的质量评分
        - 获取价格趋势，用于时机加分

        Data sources:
        - Price/info: DataProvider (yfinance + defeatbeta fallback)
        - Options: yfinance primary, Tiger API fallback

        Returns:
            该股票的期权推荐列表
        """
        try:
            # Use DataProvider for price/info (supports defeatbeta fallback)
            data_ticker = DataProvider(symbol)

            # 获取股票当前价格 (from DataProvider with fallback)
            info = data_ticker.info
            current_price = info.get('regularMarketPrice') or info.get('currentPrice')
            if current_price:
                current_price = float(current_price)
            else:
                hist = data_ticker.history(period="1d")
                if hist is not None and not hist.empty:
                    current_price = float(hist['Close'].iloc[-1])
                else:
                    return []

            # ========== 获取期权数据 (使用 DataProvider 统一访问) ==========
            # DataProvider 内部会自动选择最优数据源 (Tiger API 优先)
            expiry_dates = None

            try:
                data_ticker = DataProvider(symbol)
                if hasattr(data_ticker, 'options') and data_ticker.options:
                    expiry_dates = list(data_ticker.options[:5])
                    logger.info(f"{symbol}: 获取到 {len(expiry_dates)} 个期权到期日")
            except Exception as e:
                logger.warning(f"{symbol}: 获取期权数据失败: {e}")

            if not expiry_dates:
                return []

            # ========== 排除日权 ==========
            today_str = date.today().isoformat()
            tomorrow_str = (date.today() + timedelta(days=1)).isoformat()

            # Convert expiry dates to string format if needed and filter
            filtered_expiry_dates = []
            for exp in expiry_dates:
                exp_str = exp if isinstance(exp, str) else exp.strftime('%Y-%m-%d') if hasattr(exp, 'strftime') else str(exp)
                if exp_str > tomorrow_str:
                    filtered_expiry_dates.append(exp_str)

            expiry_dates = filtered_expiry_dates[:3]

            if not expiry_dates:
                return []

            # ========== 获取标的质量和价格趋势 ==========
            symbol_quality = self.get_symbol_quality_score(symbol)
            price_trend = self.get_price_trend(symbol)

            recommendations = []

            for expiry in expiry_dates:
                try:
                    calls_df = None
                    puts_df = None

                    # 使用 DataProvider 获取期权链 (自动选择最优数据源)
                    try:
                        chain = data_ticker.option_chain(expiry)
                        if chain:
                            calls_df = chain.calls
                            puts_df = chain.puts
                    except Exception as e:
                        logger.warning(f"DataProvider option_chain 失败 {symbol} {expiry}: {e}")
                        continue

                    # 分析看涨期权
                    if calls_df is not None and not calls_df.empty:
                        call_recs = self._score_options(
                            symbol, current_price, expiry, calls_df, 'CALL',
                            symbol_quality, price_trend
                        )
                        recommendations.extend(call_recs)

                    # 分析看跌期权
                    if puts_df is not None and not puts_df.empty:
                        put_recs = self._score_options(
                            symbol, current_price, expiry, puts_df, 'PUT',
                            symbol_quality, price_trend
                        )
                        recommendations.extend(put_recs)

                except Exception as e:
                    logger.warning(f"分析 {symbol} {expiry} 期权链失败: {e}")
                    continue

            return recommendations

        except Exception as e:
            logger.warning(f"分析 {symbol} 失败: {e}")
            return []

    def _score_options(self, symbol: str, current_price: float, expiry: str,
                      options_df, option_type: str,
                      symbol_quality: Dict[str, Any] = None,
                      price_trend: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        为期权评分

        基于用户实战经验优化：
        - 使用标的质量评分影响推荐
        - 使用价格趋势计算时机加分
        - 添加临期警告信息

        Args:
            symbol: 股票代码
            current_price: 当前股价
            expiry: 到期日
            options_df: 期权数据DataFrame
            option_type: CALL 或 PUT
            symbol_quality: 标的质量信息
            price_trend: 价格趋势信息

        Returns:
            评分后的推荐列表
        """
        recommendations = []

        # 默认值
        if symbol_quality is None:
            symbol_quality = {'tier': 5, 'quality': 50, 'description': '未评级'}
        if price_trend is None:
            price_trend = {'trend': 'unknown', 'change_pct': 0, 'is_good_timing_for_put': False}

        try:
            # Ensure strike column is numeric (Tiger API may return strings)
            if 'strike' in options_df.columns:
                options_df = options_df.copy()
                options_df['strike'] = pd.to_numeric(options_df['strike'], errors='coerce')

            # 筛选合适的期权（虚值或轻微实值）
            if option_type == 'CALL':
                # Sell Call: 选择虚值期权（执行价 > 当前价）
                suitable = options_df[options_df['strike'] > current_price * 1.02]
            else:
                # Sell Put: 选择虚值期权（执行价 < 当前价）
                suitable = options_df[options_df['strike'] < current_price * 0.98]

            # 限制数量
            suitable = suitable.head(5)

            for _, row in suitable.iterrows():
                try:
                    strike = float(row['strike'])
                    last_price = float(row.get('lastPrice', 0) or 0)
                    # Handle NaN values in bid/ask
                    bid_val = row.get('bid', 0)
                    ask_val = row.get('ask', 0)
                    bid = float(bid_val) if bid_val is not None and not (isinstance(bid_val, float) and np.isnan(bid_val)) else 0
                    ask = float(ask_val) if ask_val is not None and not (isinstance(ask_val, float) and np.isnan(ask_val)) else 0
                    # Handle NaN in volume and open_interest
                    vol_val = row.get('volume', 0)
                    oi_val = row.get('openInterest', 0)
                    iv_val = row.get('impliedVolatility', 0.25)
                    volume = int(vol_val) if vol_val is not None and not (isinstance(vol_val, float) and np.isnan(vol_val)) else 0
                    open_interest = int(oi_val) if oi_val is not None and not (isinstance(oi_val, float) and np.isnan(oi_val)) else 0
                    implied_vol = float(iv_val) if iv_val is not None and not (isinstance(iv_val, float) and np.isnan(iv_val)) else 0.25

                    # Relaxed filter: accept options with lastPrice > 0 AND (valid bid/ask OR volume > 0)
                    has_valid_price = last_price > 0
                    has_valid_spread = bid > 0 or ask > 0
                    has_volume = volume > 0

                    if not has_valid_price or (not has_valid_spread and not has_volume):
                        continue

                    mid_price = (bid + ask) / 2 if bid > 0 and ask > 0 else last_price

                    # 构建 OptionData
                    option_data = OptionData(
                        identifier=f"{symbol}{expiry.replace('-', '')}{option_type[0]}{int(strike*1000):08d}",
                        symbol=symbol,
                        strike=strike,
                        put_call=option_type,
                        expiry_date=expiry,
                        latest_price=mid_price,
                        bid_price=bid,
                        ask_price=ask,
                        volume=volume,
                        open_interest=open_interest,
                        implied_vol=implied_vol,
                        delta=row.get('delta', 0.5 if option_type == 'CALL' else -0.5),
                        gamma=row.get('gamma', 0.05),
                        theta=row.get('theta', -0.05),
                        vega=row.get('vega', 0.1),
                    )

                    # 计算评分
                    scores = self.scorer.score_option(option_data, current_price)

                    # 选择最佳策略 (阈值降低到20，因为期权评分通常较低)
                    MIN_SCORE_THRESHOLD = 20
                    if option_type == 'CALL':
                        sell_score = scores.scrv or 0
                        buy_score = scores.bcrv or 0
                        if sell_score >= buy_score and sell_score >= MIN_SCORE_THRESHOLD:
                            strategy = 'sell_call'
                            score = sell_score
                            style = '稳健收益'
                        elif buy_score >= MIN_SCORE_THRESHOLD:
                            strategy = 'buy_call'
                            score = buy_score
                            style = '看涨杠杆'
                        else:
                            continue
                    else:
                        sell_score = scores.sprv or 0
                        buy_score = scores.bprv or 0
                        if sell_score >= buy_score and sell_score >= MIN_SCORE_THRESHOLD:
                            strategy = 'sell_put'
                            score = sell_score
                            style = '稳健收益'
                        elif buy_score >= MIN_SCORE_THRESHOLD:
                            strategy = 'buy_put'
                            score = buy_score
                            style = '对冲保险'
                        else:
                            continue

                    # ========== 时机加分（新增）==========
                    timing_bonus = self.calculate_timing_bonus(price_trend, strategy)
                    score = score + timing_bonus

                    # 计算收益率
                    if strategy.startswith('sell'):
                        days_to_expiry = max(1, (datetime.strptime(expiry, '%Y-%m-%d') - datetime.now()).days)
                        premium_yield = (mid_price / strike) * 100
                        annualized = premium_yield * (365 / days_to_expiry)
                    else:
                        premium_yield = 0
                        annualized = 0
                        days_to_expiry = max(1, (datetime.strptime(expiry, '%Y-%m-%d') - datetime.now()).days)

                    # 获取市场配置（币种/市场标签）
                    market_config = get_option_market_config(symbol)

                    recommendations.append({
                        'symbol': symbol,
                        'strategy': strategy,
                        'strike': strike,
                        'expiry': expiry,
                        'score': round(min(100, score), 1),  # 限制最高100分
                        'style_label': style,
                        'option_type': option_type,
                        'current_price': round(current_price, 2),
                        'option_price': round(mid_price, 2),
                        'premium_yield': f"{premium_yield:.1f}%",
                        'annualized_return': f"{annualized:.1f}%",
                        'iv_rank': scores.iv_rank,
                        'open_interest': open_interest,
                        'reason': self._generate_reason(strategy, score, current_price, strike, implied_vol, price_trend),
                        # ========== 市场信息 ==========
                        'market': market_config.market,
                        'currency': market_config.currency,
                        # ========== 标的/趋势字段 ==========
                        'symbol_quality': symbol_quality.get('quality', 50),
                        'symbol_tier': symbol_quality.get('tier', 5),
                        'symbol_description': symbol_quality.get('description', ''),
                        'price_trend': price_trend.get('trend', 'unknown'),
                        'trend_change_pct': price_trend.get('change_pct', 0),
                        'timing_bonus': round(timing_bonus, 1),
                        'expiry_warning': scores.expiry_warning,
                        'is_daily_option': scores.is_daily_option,
                        'days_to_expiry': days_to_expiry,
                    })

                except Exception as e:
                    logger.debug(f"处理期权数据失败: {e}")
                    continue

        except Exception as e:
            logger.warning(f"期权评分失败: {e}")

        return recommendations

    def _ensure_diversity(self, recommendations: List[Dict], count: int) -> List[Dict]:
        """
        确保推荐策略多样性

        每种策略最多选择2个
        """
        strategy_counts = {s: 0 for s in STRATEGIES}
        diverse = []

        for rec in recommendations:
            strategy = rec.get('strategy')
            if strategy_counts.get(strategy, 0) < 2:
                diverse.append(rec)
                strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1

            if len(diverse) >= count:
                break

        return diverse

    def _generate_reason(self, strategy: str, score: float, current_price: float,
                        strike: float, iv: float,
                        price_trend: Dict[str, Any] = None) -> str:
        """
        生成推荐理由

        基于用户实战经验：体现时机因素
        """
        reasons = []

        if price_trend is None:
            price_trend = {'trend': 'unknown', 'change_pct': 0}

        if strategy == 'sell_put':
            buffer_pct = (current_price - strike) / current_price * 100
            reasons.append(f"安全边际{buffer_pct:.1f}%")
            if iv > 0.3:
                reasons.append("波动率处于高位")
            # 时机因素
            if price_trend.get('trend') == 'down':
                reasons.append("逢低布局良机")
            elif price_trend.get('trend') == 'sideways':
                reasons.append("震荡行情适合卖Put")
            else:
                reasons.append("适合收取权利金")

        elif strategy == 'sell_call':
            buffer_pct = (strike - current_price) / current_price * 100
            reasons.append(f"上涨缓冲{buffer_pct:.1f}%")
            if iv > 0.3:
                reasons.append("波动率溢价高")
            # 时机因素
            if price_trend.get('trend') == 'up':
                reasons.append("趋势向上时卖Call")
            else:
                reasons.append("适合增强收益")

        elif strategy == 'buy_call':
            if iv < 0.25:
                reasons.append("波动率较低")
            reasons.append("看涨方向杠杆")
            if price_trend.get('trend') == 'up':
                reasons.append("顺势而为")

        elif strategy == 'buy_put':
            reasons.append("下跌保护")
            reasons.append("对冲风险")
            if price_trend.get('trend') == 'down':
                reasons.append("趋势向下")

        if score >= 75:
            reasons.append("评分优秀")
        elif score >= 60:
            reasons.append("评分良好")

        return "，".join(reasons[:3])

    def _generate_market_summary(self, recommendations: List[Dict]) -> Dict[str, Any]:
        """生成市场摘要"""
        if not recommendations:
            return {
                'overall_trend': 'unknown',
                'recommended_strategies': [],
                'avg_iv': 0
            }

        # 统计策略分布
        strategies = [r.get('strategy') for r in recommendations]
        strategy_counts = {}
        for s in strategies:
            strategy_counts[s] = strategy_counts.get(s, 0) + 1

        # 推荐策略（出现最多的）
        top_strategies = sorted(strategy_counts.items(), key=lambda x: x[1], reverse=True)
        recommended = [s[0] for s in top_strategies[:2]]

        # 平均IV
        ivs = [r.get('iv_rank', 50) for r in recommendations if r.get('iv_rank')]
        avg_iv = np.mean(ivs) if ivs else 50

        # 判断市场趋势
        sell_count = sum(1 for s in strategies if s.startswith('sell'))
        buy_count = len(strategies) - sell_count

        if sell_count > buy_count * 1.5:
            overall_trend = 'range_bound'  # 适合卖方策略
        elif buy_count > sell_count * 1.5:
            overall_trend = 'trending'  # 适合买方策略
        else:
            overall_trend = 'mixed'

        return {
            'overall_trend': overall_trend,
            'recommended_strategies': recommended,
            'avg_iv_rank': round(avg_iv, 1),
            'strategy_distribution': strategy_counts
        }

    def _save_to_cache(self, date_key: date, result: Dict[str, Any]):
        """保存推荐到缓存"""
        try:
            # 查找或创建记录
            existing = DailyRecommendation.query.filter_by(
                recommendation_date=date_key
            ).first()

            if existing:
                existing.recommendations = result.get('recommendations', [])
                existing.market_summary = result.get('market_summary', {})
                existing.updated_at = datetime.utcnow()
            else:
                new_rec = DailyRecommendation(
                    recommendation_date=date_key,
                    recommendations=result.get('recommendations', []),
                    market_summary=result.get('market_summary', {})
                )
                db.session.add(new_rec)

            db.session.commit()
            logger.info(f"推荐数据已缓存，日期: {date_key}")

        except Exception as e:
            logger.error(f"保存推荐缓存失败: {e}")
            db.session.rollback()


# 单例实例
recommendation_service = RecommendationService()

"""
期权推荐服务
每日生成热门期权推荐，支持缓存
"""

import logging
from datetime import datetime, date
from typing import Dict, Any, List, Optional
import yfinance as yf
import numpy as np

from ..models import db, DailyRecommendation
from .option_scorer import OptionScorer
from .option_models import OptionData

logger = logging.getLogger(__name__)

# 热门股票列表（美股常见期权标的）
HOT_SYMBOLS = [
    'AAPL', 'NVDA', 'TSLA', 'MSFT', 'GOOGL',
    'META', 'AMZN', 'AMD', 'SPY', 'QQQ'
]

# 期权策略类型
STRATEGIES = ['sell_put', 'sell_call', 'buy_call', 'buy_put']


class RecommendationService:
    """期权推荐服务"""

    def __init__(self):
        self.scorer = OptionScorer()

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

            for symbol in HOT_SYMBOLS[:8]:  # 限制分析数量以提高性能
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

        Returns:
            该股票的期权推荐列表
        """
        try:
            ticker = yf.Ticker(symbol)

            # 获取股票当前价格
            info = ticker.info
            current_price = info.get('regularMarketPrice') or info.get('currentPrice')
            if not current_price:
                hist = ticker.history(period="1d")
                if not hist.empty:
                    current_price = float(hist['Close'].iloc[-1])
                else:
                    return []

            # 获取期权到期日
            if not ticker.options:
                return []

            # 选择最近的2-4周到期日
            expiry_dates = ticker.options[:3]  # 最多取3个到期日
            recommendations = []

            for expiry in expiry_dates:
                try:
                    chain = ticker.option_chain(expiry)

                    # 分析看涨期权
                    calls = chain.calls
                    if not calls.empty:
                        call_recs = self._score_options(
                            symbol, current_price, expiry, calls, 'CALL'
                        )
                        recommendations.extend(call_recs)

                    # 分析看跌期权
                    puts = chain.puts
                    if not puts.empty:
                        put_recs = self._score_options(
                            symbol, current_price, expiry, puts, 'PUT'
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
                      options_df, option_type: str) -> List[Dict[str, Any]]:
        """
        为期权评分

        Args:
            symbol: 股票代码
            current_price: 当前股价
            expiry: 到期日
            options_df: 期权数据DataFrame
            option_type: CALL 或 PUT

        Returns:
            评分后的推荐列表
        """
        recommendations = []

        try:
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
                    bid = float(row.get('bid', 0) or 0)
                    ask = float(row.get('ask', 0) or 0)
                    volume = int(row.get('volume', 0) or 0)
                    open_interest = int(row.get('openInterest', 0) or 0)
                    implied_vol = float(row.get('impliedVolatility', 0.25) or 0.25)

                    if last_price <= 0 or (bid <= 0 and ask <= 0):
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

                    # 选择最佳策略
                    if option_type == 'CALL':
                        sell_score = scores.scrv or 0
                        buy_score = scores.bcrv or 0
                        if sell_score >= buy_score and sell_score >= 50:
                            strategy = 'sell_call'
                            score = sell_score
                            style = '稳健收益'
                        elif buy_score >= 50:
                            strategy = 'buy_call'
                            score = buy_score
                            style = '看涨杠杆'
                        else:
                            continue
                    else:
                        sell_score = scores.sprv or 0
                        buy_score = scores.bprv or 0
                        if sell_score >= buy_score and sell_score >= 50:
                            strategy = 'sell_put'
                            score = sell_score
                            style = '稳健收益'
                        elif buy_score >= 50:
                            strategy = 'buy_put'
                            score = buy_score
                            style = '对冲保险'
                        else:
                            continue

                    # 计算收益率
                    if strategy.startswith('sell'):
                        days_to_expiry = max(1, (datetime.strptime(expiry, '%Y-%m-%d') - datetime.now()).days)
                        premium_yield = (mid_price / strike) * 100
                        annualized = premium_yield * (365 / days_to_expiry)
                    else:
                        premium_yield = 0
                        annualized = 0

                    recommendations.append({
                        'symbol': symbol,
                        'strategy': strategy,
                        'strike': strike,
                        'expiry': expiry,
                        'score': round(score, 1),
                        'style_label': style,
                        'option_type': option_type,
                        'current_price': round(current_price, 2),
                        'option_price': round(mid_price, 2),
                        'premium_yield': f"{premium_yield:.1f}%",
                        'annualized_return': f"{annualized:.1f}%",
                        'iv_rank': scores.iv_rank,
                        'open_interest': open_interest,
                        'reason': self._generate_reason(strategy, score, current_price, strike, implied_vol)
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
                        strike: float, iv: float) -> str:
        """生成推荐理由"""
        reasons = []

        if strategy == 'sell_put':
            buffer_pct = (current_price - strike) / current_price * 100
            reasons.append(f"安全边际{buffer_pct:.1f}%")
            if iv > 0.3:
                reasons.append("波动率处于高位")
            reasons.append("适合收取权利金")

        elif strategy == 'sell_call':
            buffer_pct = (strike - current_price) / current_price * 100
            reasons.append(f"上涨缓冲{buffer_pct:.1f}%")
            if iv > 0.3:
                reasons.append("波动率溢价高")
            reasons.append("适合增强收益")

        elif strategy == 'buy_call':
            if iv < 0.25:
                reasons.append("波动率较低")
            reasons.append("看涨方向杠杆")

        elif strategy == 'buy_put':
            reasons.append("下跌保护")
            reasons.append("对冲风险")

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

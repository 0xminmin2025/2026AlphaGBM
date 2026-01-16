"""
股票分析计算模块
负责各种技术分析指标和财务指标的计算
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple, Optional, List
import logging

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


class StockCalculator:
    """
    股票分析计算器
    负责各种技术分析指标和财务指标的计算
    """

    def __init__(self):
        """初始化计算器"""
        self.min_daily_volume_usd = MIN_DAILY_VOLUME_USD
        self.atr_multiplier_base = ATR_MULTIPLIER_BASE

    def check_liquidity(self, data: Dict[str, Any], currency_symbol: str = '$') -> Tuple[bool, Dict[str, Any]]:
        """
        检查股票流动性，判断是否满足交易要求

        参数:
            data: 包含市场数据的字典
            currency_symbol: 货币符号，用于计算成交额

        返回:
            (is_liquid, liquidity_info)
            is_liquid: 是否满足流动性要求
            liquidity_info: 流动性信息字典
        """
        try:
            # 获取历史数据中的成交量
            if 'history_prices' in data and len(data.get('history_prices', [])) > 0:
                # 从历史数据计算平均成交量
                history_prices = data.get('history_prices', [])
                history_volumes = data.get('history_volumes', [])

                if len(history_prices) != len(history_volumes) or len(history_prices) == 0:
                    logger.warning("历史价格和成交量数据不匹配")
                    return False, {
                        'error': '历史数据不完整',
                        'daily_volume_usd': 0,
                        'avg_daily_volume_usd': 0
                    }

                # 计算最近30天的平均成交额
                recent_days = min(30, len(history_prices))
                recent_prices = history_prices[-recent_days:]
                recent_volumes = history_volumes[-recent_days:]

                daily_volume_usd_list = []
                for i in range(len(recent_prices)):
                    daily_volume_usd = recent_prices[i] * recent_volumes[i]
                    daily_volume_usd_list.append(daily_volume_usd)

                avg_daily_volume_usd = np.mean(daily_volume_usd_list)
                latest_daily_volume_usd = daily_volume_usd_list[-1] if daily_volume_usd_list else 0

                liquidity_info = {
                    'daily_volume_usd': latest_daily_volume_usd,
                    'avg_daily_volume_usd': avg_daily_volume_usd,
                    'currency_symbol': currency_symbol,
                    'min_requirement': self.min_daily_volume_usd,
                    'days_analyzed': recent_days
                }

                # 判断是否满足流动性要求
                is_liquid = avg_daily_volume_usd >= self.min_daily_volume_usd

                logger.info(f"流动性检查: 平均成交额 {avg_daily_volume_usd:,.0f}, 要求 {self.min_daily_volume_usd:,.0f}, 结果: {is_liquid}")

                return is_liquid, liquidity_info

            else:
                # 尝试从info获取成交量信息
                info = data.get('info', {})
                avg_volume = info.get('averageVolume', 0)
                current_price = info.get('regularMarketPrice', 0) or info.get('currentPrice', 0)

                if avg_volume and current_price:
                    avg_daily_volume_usd = avg_volume * current_price
                    liquidity_info = {
                        'daily_volume_usd': avg_daily_volume_usd,
                        'avg_daily_volume_usd': avg_daily_volume_usd,
                        'currency_symbol': currency_symbol,
                        'min_requirement': self.min_daily_volume_usd,
                        'source': 'yfinance_info'
                    }

                    is_liquid = avg_daily_volume_usd >= self.min_daily_volume_usd
                    return is_liquid, liquidity_info

                # 如果都没有数据，返回不满足要求
                return False, {
                    'error': '无法获取成交量数据',
                    'daily_volume_usd': 0,
                    'avg_daily_volume_usd': 0
                }

        except Exception as e:
            logger.error(f"检查流动性时发生错误: {e}")
            return False, {
                'error': f'流动性检查失败: {str(e)}',
                'daily_volume_usd': 0,
                'avg_daily_volume_usd': 0
            }

    def calculate_atr(self, hist_data: pd.DataFrame, period: int = 14) -> float:
        """
        计算平均真实波动范围（ATR）

        参数:
            hist_data: 历史数据DataFrame
            period: 计算周期

        返回:
            ATR值
        """
        try:
            if hist_data.empty or len(hist_data) < period:
                logger.warning(f"历史数据不足以计算ATR，需要{period}天，实际{len(hist_data)}天")
                return 0.0

            # 计算真实波动范围
            high_low = hist_data['High'] - hist_data['Low']
            high_close_prev = abs(hist_data['High'] - hist_data['Close'].shift(1))
            low_close_prev = abs(hist_data['Low'] - hist_data['Close'].shift(1))

            # True Range是以上三者的最大值
            true_range = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)

            # 计算ATR（True Range的移动平均）
            atr = true_range.rolling(window=period).mean().iloc[-1]

            logger.info(f"计算ATR成功，周期{period}，值: {atr:.4f}")
            return float(atr) if not pd.isna(atr) else 0.0

        except Exception as e:
            logger.error(f"计算ATR时发生错误: {e}")
            return 0.0

    def calculate_atr_stop_loss(self, buy_price: float, hist_data: pd.DataFrame,
                              atr_period: Optional[int] = None, atr_multiplier: Optional[float] = None,
                              min_stop_loss_pct: Optional[float] = None, beta: Optional[float] = None) -> Dict[str, Any]:
        """
        基于ATR计算止损价格

        参数:
            buy_price: 买入价格
            hist_data: 历史数据
            atr_period: ATR计算周期
            atr_multiplier: ATR乘数
            min_stop_loss_pct: 最小止损百分比
            beta: 股票beta值

        返回:
            包含止损信息的字典
        """
        try:
            # 设置默认参数
            atr_period = atr_period or 14
            atr_multiplier = atr_multiplier or self.atr_multiplier_base
            min_stop_loss_pct = min_stop_loss_pct or FIXED_STOP_LOSS_PCT

            # 根据beta调整乘数
            if beta is not None:
                if beta > 1.5:
                    atr_multiplier *= 1.2  # 高beta股票增加止损范围
                elif beta < 0.8:
                    atr_multiplier *= 0.8  # 低beta股票减少止损范围

            # 计算ATR
            atr = self.calculate_atr(hist_data, atr_period)

            if atr == 0:
                # 如果ATR计算失败，使用固定百分比
                stop_loss_price = buy_price * (1 - min_stop_loss_pct)
                return {
                    'stop_loss_price': stop_loss_price,
                    'stop_loss_pct': min_stop_loss_pct,
                    'method': 'fixed_percentage',
                    'atr': 0,
                    'atr_multiplier': atr_multiplier
                }

            # 计算基于ATR的止损价格
            atr_stop_loss = buy_price - (atr * atr_multiplier)
            atr_stop_loss_pct = (buy_price - atr_stop_loss) / buy_price

            # 确保不低于最小止损百分比
            min_stop_loss_price = buy_price * (1 - min_stop_loss_pct)

            if atr_stop_loss > min_stop_loss_price:
                # ATR止损更保守，使用ATR
                final_stop_loss = atr_stop_loss
                final_stop_loss_pct = atr_stop_loss_pct
                method = 'atr_based'
            else:
                # 使用最小止损
                final_stop_loss = min_stop_loss_price
                final_stop_loss_pct = min_stop_loss_pct
                method = 'minimum_required'

            result = {
                'stop_loss_price': final_stop_loss,
                'stop_loss_pct': final_stop_loss_pct,
                'method': method,
                'atr': atr,
                'atr_multiplier': atr_multiplier,
                'atr_suggested_price': atr_stop_loss,
                'min_required_price': min_stop_loss_price
            }

            logger.info(f"ATR止损计算完成: 价格 {final_stop_loss:.2f}, 百分比 {final_stop_loss_pct:.2%}, 方法 {method}")
            return result

        except Exception as e:
            logger.error(f"计算ATR止损时发生错误: {e}")
            # 返回固定止损作为备用方案
            stop_loss_price = buy_price * (1 - (min_stop_loss_pct or FIXED_STOP_LOSS_PCT))
            return {
                'stop_loss_price': stop_loss_price,
                'stop_loss_pct': min_stop_loss_pct or FIXED_STOP_LOSS_PCT,
                'method': 'fallback_fixed',
                'error': str(e)
            }

    def calculate_market_sentiment(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算市场情绪指标

        参数:
            data: 市场数据

        返回:
            情绪指标字典
        """
        try:
            sentiment = {
                'overall_score': 0,
                'factors': {},
                'signals': []
            }

            # 1. 价格动量分析
            history_prices = data.get('history_prices', [])
            if len(history_prices) >= 20:
                recent_prices = history_prices[-20:]
                price_trend = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]

                sentiment['factors']['price_momentum'] = {
                    'value': price_trend,
                    'score': min(max(price_trend * 100, -50), 50)  # 限制在-50到50之间
                }

                if price_trend > 0.1:
                    sentiment['signals'].append('强势上涨趋势')
                elif price_trend < -0.1:
                    sentiment['signals'].append('明显下跌趋势')

            # 2. 成交量分析
            history_volumes = data.get('history_volumes', [])
            if len(history_volumes) >= 20:
                recent_volumes = history_volumes[-20:]
                avg_recent_volume = np.mean(recent_volumes[-5:])  # 最近5天平均
                avg_baseline_volume = np.mean(recent_volumes[-20:-5])  # 基准期平均

                if avg_baseline_volume > 0:
                    volume_ratio = avg_recent_volume / avg_baseline_volume
                    sentiment['factors']['volume_trend'] = {
                        'value': volume_ratio,
                        'score': min(max((volume_ratio - 1) * 50, -25), 25)
                    }

                    if volume_ratio > 1.5:
                        sentiment['signals'].append('成交量显著放大')
                    elif volume_ratio < 0.5:
                        sentiment['signals'].append('成交量明显萎缩')

            # 3. 波动率分析
            if len(history_prices) >= 20:
                price_changes = [history_prices[i] / history_prices[i-1] - 1 for i in range(1, len(history_prices))]
                volatility = np.std(price_changes) * np.sqrt(252)  # 年化波动率

                sentiment['factors']['volatility'] = {
                    'value': volatility,
                    'score': -min(volatility * 100, 30)  # 高波动率给负分
                }

                if volatility > 0.4:
                    sentiment['signals'].append('高波动率环境')
                elif volatility < 0.15:
                    sentiment['signals'].append('低波动率环境')

            # 4. 技术指标（如果有足够数据）
            if len(history_prices) >= 50:
                # 简单移动平均
                sma_20 = np.mean(history_prices[-20:])
                sma_50 = np.mean(history_prices[-50:])
                current_price = history_prices[-1]

                # 相对位置
                position_vs_sma20 = (current_price - sma_20) / sma_20
                position_vs_sma50 = (current_price - sma_50) / sma_50

                sentiment['factors']['technical_position'] = {
                    'sma20_position': position_vs_sma20,
                    'sma50_position': position_vs_sma50,
                    'score': (position_vs_sma20 + position_vs_sma50) * 25
                }

                if current_price > sma_20 > sma_50:
                    sentiment['signals'].append('多头排列')
                elif current_price < sma_20 < sma_50:
                    sentiment['signals'].append('空头排列')

            # 计算综合得分
            total_score = sum(factor.get('score', 0) for factor in sentiment['factors'].values())
            sentiment['overall_score'] = max(min(total_score, 100), -100)

            # 情绪等级
            if sentiment['overall_score'] > 30:
                sentiment['sentiment_level'] = 'bullish'
                sentiment['sentiment_description'] = '乐观'
            elif sentiment['overall_score'] < -30:
                sentiment['sentiment_level'] = 'bearish'
                sentiment['sentiment_description'] = '悲观'
            else:
                sentiment['sentiment_level'] = 'neutral'
                sentiment['sentiment_description'] = '中性'

            logger.info(f"市场情绪分析完成，综合得分: {sentiment['overall_score']:.1f}, 等级: {sentiment['sentiment_level']}")
            return sentiment

        except Exception as e:
            logger.error(f"计算市场情绪时发生错误: {e}")
            return {
                'overall_score': 0,
                'sentiment_level': 'neutral',
                'sentiment_description': '无法分析',
                'error': str(e)
            }

    def calculate_target_price(self, data: Dict[str, Any], risk_result: Dict[str, Any], style: str) -> Dict[str, Any]:
        """
        计算目标价格

        参数:
            data: 市场数据
            risk_result: 风险分析结果
            style: 投资风格

        返回:
            目标价格分析结果
        """
        try:
            info = data.get('info', {})
            current_price = data.get('current_price', 0) or info.get('regularMarketPrice', 0)

            if not current_price:
                return {
                    'target_price': 0,
                    'upside_potential': 0,
                    'method': 'no_current_price',
                    'error': '无法获取当前价格'
                }

            # 获取基本财务指标
            pe_ratio = info.get('trailingPE', 0)
            forward_pe = info.get('forwardPE', 0)
            peg_ratio = info.get('pegRatio', 0)
            book_value = info.get('bookValue', 0)
            revenue_growth = info.get('revenueGrowth', 0)
            earnings_growth = info.get('earningsGrowth', 0)

            target_prices = []
            methods = []

            # 方法1: PE倍数法
            if pe_ratio and pe_ratio > 0:
                # 根据投资风格调整合理PE
                if style == 'growth':
                    reasonable_pe = pe_ratio * 1.1  # 成长股可以给更高估值
                elif style == 'value':
                    reasonable_pe = pe_ratio * 0.9  # 价值股要求更低估值
                else:
                    reasonable_pe = pe_ratio

                eps = current_price / pe_ratio if pe_ratio else 0
                if eps > 0:
                    target_price_pe = eps * reasonable_pe
                    target_prices.append(target_price_pe)
                    methods.append(f'PE倍数法 (PE={reasonable_pe:.1f})')

            # 方法2: PEG估值法
            if peg_ratio and earnings_growth and earnings_growth > 0:
                reasonable_peg = 1.0 if style == 'growth' else 0.8
                target_pe = earnings_growth * 100 * reasonable_peg
                eps = current_price / pe_ratio if pe_ratio else 0
                if eps > 0:
                    target_price_peg = eps * target_pe
                    target_prices.append(target_price_peg)
                    methods.append(f'PEG估值法 (PEG={reasonable_peg})')

            # 方法3: 账面价值法（主要用于价值股）
            if book_value and style == 'value':
                pb_ratio = current_price / book_value
                reasonable_pb = max(pb_ratio * 0.9, 1.0)  # 不低于1倍PB
                target_price_pb = book_value * reasonable_pb
                target_prices.append(target_price_pb)
                methods.append(f'PB估值法 (PB={reasonable_pb:.1f})')

            # 方法4: 收入增长法（主要用于成长股）
            if revenue_growth and revenue_growth > 0 and style == 'growth':
                # 基于收入增长预期调整价格
                growth_multiplier = min(1 + revenue_growth, 1.3)  # 最大30%涨幅
                target_price_revenue = current_price * growth_multiplier
                target_prices.append(target_price_revenue)
                methods.append(f'收入增长法 (增长={revenue_growth:.1%})')

            if not target_prices:
                # 如果没有足够的财务数据，使用简单的风险调整法
                risk_level = risk_result.get('risk_level', 'medium')
                if risk_level == 'low':
                    target_price = current_price * 1.15
                elif risk_level == 'high':
                    target_price = current_price * 1.05
                else:
                    target_price = current_price * 1.10

                return {
                    'target_price': target_price,
                    'upside_potential': (target_price - current_price) / current_price,
                    'method': f'风险调整法 (风险等级: {risk_level})',
                    'current_price': current_price,
                    'confidence': 'low'
                }

            # 计算加权平均目标价格
            final_target_price = np.mean(target_prices)
            upside_potential = (final_target_price - current_price) / current_price

            # 根据风险调整目标价格
            risk_adjustment = risk_result.get('risk_adjustment_factor', 1.0)
            adjusted_target_price = current_price + (final_target_price - current_price) * risk_adjustment

            result = {
                'target_price': adjusted_target_price,
                'upside_potential': (adjusted_target_price - current_price) / current_price,
                'unadjusted_target': final_target_price,
                'current_price': current_price,
                'methods_used': methods,
                'individual_targets': target_prices,
                'risk_adjustment_factor': risk_adjustment,
                'confidence': 'high' if len(target_prices) >= 2 else 'medium'
            }

            logger.info(f"目标价格计算完成: {adjusted_target_price:.2f} (当前: {current_price:.2f}, 潜力: {upside_potential:.1%})")
            return result

        except Exception as e:
            logger.error(f"计算目标价格时发生错误: {e}")
            return {
                'target_price': 0,
                'upside_potential': 0,
                'error': str(e),
                'method': 'calculation_failed'
            }


# 为独立测试提供主函数
if __name__ == "__main__":
    # 独立测试代码
    calculator = StockCalculator()

    # 模拟测试数据
    test_data = {
        'history_prices': [100 + i + np.random.normal(0, 2) for i in range(50)],
        'history_volumes': [1000000 + np.random.randint(-100000, 100000) for _ in range(50)],
        'info': {
            'regularMarketPrice': 150,
            'trailingPE': 20,
            'pegRatio': 1.5
        }
    }

    print("=== 股票计算器独立测试 ===")

    # 测试流动性检查
    print("\n1. 流动性检查测试")
    is_liquid, liquidity_info = calculator.check_liquidity(test_data)
    print(f"流动性: {is_liquid}, 信息: {liquidity_info}")

    # 测试市场情绪
    print("\n2. 市场情绪分析测试")
    sentiment = calculator.calculate_market_sentiment(test_data)
    print(f"情绪得分: {sentiment.get('overall_score', 0)}, 等级: {sentiment.get('sentiment_level', 'unknown')}")

    print("\n测试完成!")
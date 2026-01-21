"""
趋势分析模块
基于真实交易者的决策逻辑：
- Sell Call 只在上涨时做
- Sell Put 只在下跌时做
- 趋势判断基于"买卖当天"
- 不匹配趋势时"显示但降分"
"""

import logging
from typing import Dict, Any, Tuple, List, Optional
import numpy as np
import pandas as pd
from datetime import datetime

logger = logging.getLogger(__name__)


class TrendAnalyzer:
    """趋势分析器 - 基于当天趋势判断"""

    def __init__(self):
        """初始化趋势分析器"""
        # 趋势-策略匹配评分矩阵（用户决策：显示但降分）
        self.trend_score_matrix = {
            'sell_call': {
                'uptrend': 100,      # 上涨时 Sell Call 满分
                'sideways': 60,      # 横盘中等分
                'downtrend': 30,     # 下跌大幅降分（但仍显示）
            },
            'sell_put': {
                'downtrend': 100,    # 下跌时 Sell Put 满分
                'sideways': 60,      # 横盘中等分
                'uptrend': 30,       # 上涨大幅降分（但仍显示）
            },
            'buy_call': {
                'uptrend': 100,
                'sideways': 50,
                'downtrend': 20,
            },
            'buy_put': {
                'downtrend': 100,
                'sideways': 50,
                'uptrend': 20,
            },
        }

        # 策略理想趋势映射
        self.ideal_trend_map = {
            'sell_call': 'uptrend',
            'sell_put': 'downtrend',
            'buy_call': 'uptrend',
            'buy_put': 'downtrend',
        }

    def determine_intraday_trend(
        self,
        price_history: pd.Series,
        current_price: float
    ) -> Tuple[str, float]:
        """
        基于当天的趋势判断（用户要求：买卖当天的趋势）

        使用短期指标判断当日趋势方向：
        - 当日涨跌幅
        - 相对于MA5的位置
        - 近5日动量

        Args:
            price_history: 历史收盘价序列（至少需要6个数据点）
            current_price: 当前价格

        Returns:
            Tuple[trend, strength]: 趋势方向和强度(0-1)
        """
        try:
            if len(price_history) < 6:
                logger.warning("价格历史数据不足，返回中性趋势")
                return 'sideways', 0.5

            # 确保是 numpy array 以便计算
            prices = np.array(price_history[-6:])
            prev_close = prices[-2] if len(prices) >= 2 else prices[-1]

            # 信号计算
            signals = {}

            # 1. 当日涨跌幅
            today_change = (current_price - prev_close) / prev_close if prev_close > 0 else 0
            if today_change > 0.005:  # 涨0.5%以上
                signals['today_change'] = 'bullish'
            elif today_change < -0.005:  # 跌0.5%以上
                signals['today_change'] = 'bearish'
            else:
                signals['today_change'] = 'neutral'

            # 2. 相对MA5位置
            ma5 = np.mean(prices[-5:]) if len(prices) >= 5 else np.mean(prices)
            ma5_position = (current_price - ma5) / ma5 if ma5 > 0 else 0
            if ma5_position > 0.01:  # 高于MA5 1%以上
                signals['ma5_position'] = 'bullish'
            elif ma5_position < -0.01:  # 低于MA5 1%以上
                signals['ma5_position'] = 'bearish'
            else:
                signals['ma5_position'] = 'neutral'

            # 3. 近5日动量
            if len(prices) >= 6:
                momentum_5d = (current_price - prices[-6]) / prices[-6] if prices[-6] > 0 else 0
            else:
                momentum_5d = 0

            if momentum_5d > 0.02:  # 5日涨2%以上
                signals['momentum_5d'] = 'bullish'
            elif momentum_5d < -0.02:  # 5日跌2%以上
                signals['momentum_5d'] = 'bearish'
            else:
                signals['momentum_5d'] = 'neutral'

            # 统计信号
            bullish_count = sum(1 for s in signals.values() if s == 'bullish')
            bearish_count = sum(1 for s in signals.values() if s == 'bearish')

            # 判断趋势和强度
            if bullish_count >= 2:
                strength = bullish_count / 3  # 0.67 或 1.0
                return 'uptrend', round(strength, 2)
            elif bearish_count >= 2:
                strength = bearish_count / 3  # 0.67 或 1.0
                return 'downtrend', round(strength, 2)
            else:
                return 'sideways', 0.5

        except Exception as e:
            logger.error(f"趋势判断失败: {e}")
            return 'sideways', 0.5

    def calculate_trend_alignment_score(
        self,
        strategy: str,
        trend: str,
        trend_strength: float
    ) -> float:
        """
        根据趋势计算评分（用户决策：显示但降分，不完全过滤）

        Args:
            strategy: 策略类型 ('sell_call', 'sell_put', 'buy_call', 'buy_put')
            trend: 趋势方向 ('uptrend', 'downtrend', 'sideways')
            trend_strength: 趋势强度 (0-1)

        Returns:
            趋势匹配评分 (0-120)
        """
        try:
            strategy = strategy.lower()
            trend = trend.lower()

            # 获取基础分数
            base_score = self.trend_score_matrix.get(strategy, {}).get(trend, 50)

            # 趋势强度调整
            if base_score >= 80:  # 匹配趋势
                # 趋势越强，加分越多（最多+20%）
                adjusted_score = base_score * (1 + trend_strength * 0.2)
            else:  # 不匹配趋势
                # 趋势越强，扣分越多（最多-30%）
                adjusted_score = base_score * (1 - trend_strength * 0.3)

            return round(min(120, max(0, adjusted_score)), 1)

        except Exception as e:
            logger.error(f"趋势评分计算失败: {e}")
            return 50

    def get_trend_display_info(
        self,
        trend: str,
        trend_strength: float,
        strategy: str
    ) -> Dict[str, Any]:
        """
        返回趋势显示信息，让用户看到当前趋势状态

        Args:
            trend: 趋势方向
            trend_strength: 趋势强度
            strategy: 策略类型

        Returns:
            趋势显示信息字典
        """
        trend_names = {
            'uptrend': '上涨趋势',
            'downtrend': '下跌趋势',
            'sideways': '横盘整理',
        }

        trend_icons = {
            'uptrend': '📈',
            'downtrend': '📉',
            'sideways': '➡️',
        }

        strength_desc = {
            (0, 0.4): '弱',
            (0.4, 0.7): '中等',
            (0.7, 1.1): '强',
        }

        # 获取强度描述
        strength_text = '中等'
        for (low, high), desc in strength_desc.items():
            if low <= trend_strength < high:
                strength_text = desc
                break

        # 判断是否为理想趋势
        ideal_trend = self.ideal_trend_map.get(strategy.lower())
        is_ideal = trend == ideal_trend

        # 生成警告信息
        warning = None
        if not is_ideal and trend != 'sideways':
            strategy_names = {
                'sell_call': 'Sell Call',
                'sell_put': 'Sell Put',
                'buy_call': 'Buy Call',
                'buy_put': 'Buy Put',
            }
            warning = f"当前{trend_names.get(trend, trend)}，非最佳{strategy_names.get(strategy.lower(), strategy)}时机"

        return {
            'trend': trend,
            'trend_name_cn': trend_names.get(trend, trend),
            'trend_icon': trend_icons.get(trend, '•'),
            'trend_strength': trend_strength,
            'trend_strength_desc': strength_text,
            'is_ideal_trend': is_ideal,
            'warning': warning,
            'ideal_trend': ideal_trend,
            'ideal_trend_name_cn': trend_names.get(ideal_trend, ideal_trend),
        }

    def analyze_trend_for_strategy(
        self,
        price_history: pd.Series,
        current_price: float,
        strategy: str
    ) -> Dict[str, Any]:
        """
        为特定策略进行完整的趋势分析

        Args:
            price_history: 历史价格序列
            current_price: 当前价格
            strategy: 策略类型

        Returns:
            完整的趋势分析结果
        """
        # 判断趋势
        trend, strength = self.determine_intraday_trend(price_history, current_price)

        # 计算趋势评分
        trend_score = self.calculate_trend_alignment_score(strategy, trend, strength)

        # 获取显示信息
        display_info = self.get_trend_display_info(trend, strength, strategy)

        return {
            'trend': trend,
            'trend_strength': strength,
            'trend_alignment_score': trend_score,
            'display_info': display_info,
            'is_ideal_trend': display_info['is_ideal_trend'],
            'analysis_time': datetime.now().isoformat(),
        }


class ATRCalculator:
    """ATR（平均真实波幅）计算器 - 用于动态安全边际"""

    @staticmethod
    def calculate_atr(
        high_prices: pd.Series,
        low_prices: pd.Series,
        close_prices: pd.Series,
        period: int = 14
    ) -> float:
        """
        计算ATR（Average True Range）

        Args:
            high_prices: 最高价序列
            low_prices: 最低价序列
            close_prices: 收盘价序列
            period: ATR周期，默认14

        Returns:
            ATR值
        """
        try:
            if len(close_prices) < period + 1:
                # 数据不足，使用简化计算
                return (high_prices.max() - low_prices.min()) / len(high_prices)

            # 计算True Range
            high = np.array(high_prices)
            low = np.array(low_prices)
            close = np.array(close_prices)

            tr1 = high[1:] - low[1:]  # 当日最高 - 当日最低
            tr2 = np.abs(high[1:] - close[:-1])  # 当日最高 - 昨日收盘
            tr3 = np.abs(low[1:] - close[:-1])  # 当日最低 - 昨日收盘

            tr = np.maximum(np.maximum(tr1, tr2), tr3)

            # 计算ATR（简单移动平均）
            atr = np.mean(tr[-period:])

            return round(atr, 4)

        except Exception as e:
            logger.error(f"ATR计算失败: {e}")
            return 0

    @staticmethod
    def calculate_atr_based_safety(
        current_price: float,
        strike: float,
        atr_14: float,
        atr_ratio: float = 2.0
    ) -> Dict[str, Any]:
        """
        基于ATR计算动态安全边际

        安全边际 = 执行价距离 / (ATR * 系数)

        - 高波动股（ATR大）：需要更大的价差才算安全
        - 低波动股（ATR小）：小价差也算安全

        Args:
            current_price: 当前价格
            strike: 执行价
            atr_14: 14日ATR
            atr_ratio: ATR系数，默认2.0

        Returns:
            安全边际分析结果
        """
        try:
            if atr_14 <= 0:
                return {
                    'safety_ratio': 0,
                    'atr_multiples': 0,
                    'is_safe': False,
                    'required_buffer': 0,
                    'actual_buffer': current_price - strike,
                    'atr_14': atr_14,
                    'error': 'ATR为0或负数'
                }

            # 需要的安全缓冲 = ATR * 系数
            required_buffer = atr_14 * atr_ratio

            # 实际缓冲（对于Put：当前价格 - 执行价；对于Call：执行价 - 当前价格）
            actual_buffer = abs(current_price - strike)

            # 安全边际比 = 实际缓冲 / 需要缓冲
            safety_ratio = actual_buffer / required_buffer if required_buffer > 0 else 0

            # ATR倍数 = 实际缓冲是几倍ATR
            atr_multiples = actual_buffer / atr_14 if atr_14 > 0 else 0

            return {
                'safety_ratio': round(safety_ratio, 2),
                'atr_multiples': round(atr_multiples, 2),
                'is_safe': safety_ratio >= 1.0,
                'required_buffer': round(required_buffer, 2),
                'actual_buffer': round(actual_buffer, 2),
                'atr_14': round(atr_14, 2),
                'atr_pct': round(atr_14 / current_price * 100, 2) if current_price > 0 else 0,
            }

        except Exception as e:
            logger.error(f"ATR安全边际计算失败: {e}")
            return {
                'safety_ratio': 0,
                'atr_multiples': 0,
                'is_safe': False,
                'error': str(e)
            }

    @staticmethod
    def calculate_atr_safety_score(
        safety_ratio: float,
        atr_multiples: float
    ) -> float:
        """
        基于ATR安全边际计算评分

        Args:
            safety_ratio: 安全边际比
            atr_multiples: ATR倍数

        Returns:
            安全边际评分 (0-100)
        """
        # 基于 safety_ratio 的评分
        if safety_ratio >= 2.0:  # 超过需求2倍
            base_score = 100
        elif safety_ratio >= 1.5:  # 1.5-2倍
            base_score = 90 + (safety_ratio - 1.5) * 20
        elif safety_ratio >= 1.0:  # 1-1.5倍（刚好安全）
            base_score = 70 + (safety_ratio - 1.0) * 40
        elif safety_ratio >= 0.5:  # 0.5-1倍（不够安全）
            base_score = 40 + (safety_ratio - 0.5) * 60
        else:  # < 0.5倍（危险）
            base_score = max(0, safety_ratio * 80)

        # 基于 ATR 倍数的调整
        if atr_multiples >= 3:  # 3倍ATR以上，加分
            multiplier_bonus = 10
        elif atr_multiples >= 2:  # 2-3倍ATR
            multiplier_bonus = 5
        elif atr_multiples < 1:  # 不足1倍ATR，扣分
            multiplier_bonus = -10
        else:
            multiplier_bonus = 0

        return round(min(100, max(0, base_score + multiplier_bonus)), 1)


# 独立测试
if __name__ == "__main__":
    print("🧪 趋势分析模块独立测试")
    print("=" * 50)

    # 创建分析器
    analyzer = TrendAnalyzer()
    atr_calc = ATRCalculator()

    # 模拟价格数据（上涨趋势）
    uptrend_prices = pd.Series([100, 101, 102, 103, 104, 105, 106])
    current_price = 107

    print("\n📈 测试上涨趋势判断:")
    trend, strength = analyzer.determine_intraday_trend(uptrend_prices, current_price)
    print(f"  趋势: {trend}, 强度: {strength}")

    # 测试 Sell Call 评分
    score = analyzer.calculate_trend_alignment_score('sell_call', trend, strength)
    print(f"  Sell Call 趋势评分: {score}")

    display = analyzer.get_trend_display_info(trend, strength, 'sell_call')
    print(f"  显示信息: {display['trend_icon']} {display['trend_name_cn']} ({display['trend_strength_desc']})")
    print(f"  是否理想趋势: {display['is_ideal_trend']}")

    # 模拟价格数据（下跌趋势）
    downtrend_prices = pd.Series([110, 108, 106, 104, 102, 100, 98])
    current_price = 96

    print("\n📉 测试下跌趋势判断:")
    trend, strength = analyzer.determine_intraday_trend(downtrend_prices, current_price)
    print(f"  趋势: {trend}, 强度: {strength}")

    # 测试 Sell Put 评分
    score = analyzer.calculate_trend_alignment_score('sell_put', trend, strength)
    print(f"  Sell Put 趋势评分: {score}")

    display = analyzer.get_trend_display_info(trend, strength, 'sell_put')
    print(f"  显示信息: {display['trend_icon']} {display['trend_name_cn']} ({display['trend_strength_desc']})")
    print(f"  是否理想趋势: {display['is_ideal_trend']}")

    # 测试 ATR 计算
    print("\n📊 测试 ATR 安全边际计算:")
    high_prices = pd.Series([102, 104, 106, 108, 110, 112, 114, 116, 118, 120, 118, 116, 114, 112, 110])
    low_prices = pd.Series([98, 100, 102, 104, 106, 108, 110, 112, 114, 116, 114, 112, 110, 108, 106])
    close_prices = pd.Series([100, 102, 104, 106, 108, 110, 112, 114, 116, 118, 116, 114, 112, 110, 108])

    atr = atr_calc.calculate_atr(high_prices, low_prices, close_prices)
    print(f"  14日 ATR: {atr}")

    # 测试安全边际
    current = 100
    strike_put = 90  # Sell Put 执行价
    safety = atr_calc.calculate_atr_based_safety(current, strike_put, atr)
    print(f"  Sell Put (执行价 ${strike_put}):")
    print(f"    安全边际比: {safety['safety_ratio']}")
    print(f"    ATR倍数: {safety['atr_multiples']}")
    print(f"    是否安全: {safety['is_safe']}")

    safety_score = atr_calc.calculate_atr_safety_score(safety['safety_ratio'], safety['atr_multiples'])
    print(f"    安全边际评分: {safety_score}")

    print("\n🎉 趋势分析模块测试完成!")

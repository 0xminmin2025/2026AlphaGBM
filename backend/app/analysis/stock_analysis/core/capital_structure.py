"""
资金结构分析器

基于"以果推因"方法论，通过价量特征分析资金集中度和情绪传导阶段。

由于yfinance无法获取真实资金流向数据，采用基于价量的代理指标：
1. 成交量集中度 - 近5日量比异常程度
2. 价量配合度 - 上涨放量+下跌缩量=健康
3. 筹码集中度代理 - 价格波动范围收窄程度
4. 换手率相对值 - 相对历史的活跃度

情绪传导阶段：
龙头启动期 → 扩散初期 → 全面扩散 → 高位分化 → 退潮期
   +0.05      +0.03      +0.01      -0.02      -0.03
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import logging

logger = logging.getLogger(__name__)


# 情绪传导阶段定义
PROPAGATION_STAGES = {
    'leader_start': {
        'name': '龙头启动期',
        'name_en': 'Leader Start',
        'description': '板块龙头开始异动，资金开始关注',
        'capital_factor': 0.05,
        'probability_persistence': 0.7,
    },
    'early_spread': {
        'name': '扩散初期',
        'name_en': 'Early Spread',
        'description': '资金从龙头向同板块扩散，跟风开始',
        'capital_factor': 0.03,
        'probability_persistence': 0.65,
    },
    'full_spread': {
        'name': '全面扩散',
        'name_en': 'Full Spread',
        'description': '板块全面上涨，市场情绪高涨',
        'capital_factor': 0.01,
        'probability_persistence': 0.5,
    },
    'high_divergence': {
        'name': '高位分化',
        'name_en': 'High Divergence',
        'description': '龙头滞涨，个股分化明显',
        'capital_factor': -0.02,
        'probability_persistence': 0.4,
    },
    'retreat': {
        'name': '退潮期',
        'name_en': 'Retreat',
        'description': '资金撤离，板块全面回调',
        'capital_factor': -0.03,
        'probability_persistence': 0.35,
    },
    'neutral': {
        'name': '中性期',
        'name_en': 'Neutral',
        'description': '无明显资金动向',
        'capital_factor': 0.0,
        'probability_persistence': 0.5,
    },
}


class CapitalStructureAnalyzer:
    """
    资金结构分析器

    分析个股和板块的资金集中度、情绪传导阶段
    """

    # 配置参数
    VOLUME_CONCENTRATION_THRESHOLD = 1.5  # 放量阈值
    HARMONY_LOOKBACK = 20                 # 价量配合回看天数
    CAPITAL_FACTOR_MAX = 0.05             # 最大资金因子
    CAPITAL_FACTOR_MIN = -0.03            # 最小资金因子

    # 评分权重
    WEIGHT_VOLUME_CONCENTRATION = 0.30    # 成交量集中度
    WEIGHT_PRICE_VOLUME_HARMONY = 0.30    # 价量配合度
    WEIGHT_CHIP_CONCENTRATION = 0.25      # 筹码集中度
    WEIGHT_TURNOVER = 0.15                # 换手率

    def __init__(self):
        """初始化分析器"""
        self._cache = {}

    def analyze_capital_structure(
        self,
        ticker: str,
        hist_data: Optional[pd.DataFrame] = None,
        market_cap: Optional[float] = None,
        shares_outstanding: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        分析个股资金结构

        Args:
            ticker: 股票代码
            hist_data: 历史数据（包含OHLCV）
            market_cap: 市值（可选，用于换手率计算）
            shares_outstanding: 流通股数（可选）

        Returns:
            资金结构分析结果
        """
        try:
            if hist_data is None or hist_data.empty:
                return self._default_result(ticker)

            # 1. 计算成交量集中度
            volume_concentration, volume_signals = self._calculate_volume_concentration(
                hist_data
            )

            # 2. 计算价量配合度
            price_volume_harmony, harmony_signals = self._calculate_price_volume_harmony(
                hist_data
            )

            # 3. 计算筹码集中度（价格波动收窄）
            chip_concentration, chip_signals = self._calculate_chip_concentration(
                hist_data
            )

            # 4. 计算换手率相对值
            turnover_score, turnover_signals = self._calculate_relative_turnover(
                hist_data, shares_outstanding
            )

            # 综合评分（0-100）
            concentration_score = (
                volume_concentration * self.WEIGHT_VOLUME_CONCENTRATION +
                price_volume_harmony * self.WEIGHT_PRICE_VOLUME_HARMONY +
                chip_concentration * self.WEIGHT_CHIP_CONCENTRATION +
                turnover_score * self.WEIGHT_TURNOVER
            )

            # 判断情绪传导阶段
            propagation_stage = self._determine_propagation_stage(
                volume_concentration=volume_concentration,
                price_volume_harmony=price_volume_harmony,
                chip_concentration=chip_concentration,
                hist_data=hist_data
            )

            # 计算资金因子
            capital_factor = self._calculate_capital_factor(
                concentration_score=concentration_score,
                propagation_stage=propagation_stage
            )

            # 汇总信号
            all_signals = volume_signals + harmony_signals + chip_signals + turnover_signals

            return {
                'ticker': ticker,
                'concentration_score': round(concentration_score, 1),
                'volume_concentration': round(volume_concentration, 1),
                'price_volume_harmony': round(price_volume_harmony, 1),
                'chip_concentration': round(chip_concentration, 1),
                'turnover_score': round(turnover_score, 1),
                'propagation_stage': propagation_stage,
                'stage_info': PROPAGATION_STAGES.get(propagation_stage, PROPAGATION_STAGES['neutral']),
                'capital_factor': round(capital_factor, 4),
                'signals': all_signals,
                'timestamp': datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"分析资金结构失败 {ticker}: {e}")
            return self._default_result(ticker, error=str(e))

    def analyze_sector_capital_flow(
        self,
        sector_stocks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        分析板块资金流向

        通过分析板块内多只股票的资金特征，判断板块整体资金动向

        Args:
            sector_stocks: 板块内股票列表，每个包含ticker和hist_data

        Returns:
            板块资金流向分析
        """
        try:
            if not sector_stocks:
                return {'error': '无股票数据'}

            # 分析每只股票
            stock_analyses = []
            for stock in sector_stocks:
                analysis = self.analyze_capital_structure(
                    ticker=stock.get('ticker'),
                    hist_data=stock.get('hist_data'),
                )
                if 'error' not in analysis:
                    stock_analyses.append(analysis)

            if not stock_analyses:
                return {'error': '所有股票分析失败'}

            # 计算板块平均
            avg_concentration = np.mean([a['concentration_score'] for a in stock_analyses])

            # 统计阶段分布
            stage_counts = {}
            for a in stock_analyses:
                stage = a['propagation_stage']
                stage_counts[stage] = stage_counts.get(stage, 0) + 1

            # 判断主导阶段
            dominant_stage = max(stage_counts, key=stage_counts.get)

            # 计算板块资金因子（平均）
            avg_capital_factor = np.mean([a['capital_factor'] for a in stock_analyses])

            return {
                'sector_concentration_score': round(avg_concentration, 1),
                'dominant_stage': dominant_stage,
                'stage_distribution': stage_counts,
                'sector_capital_factor': round(avg_capital_factor, 4),
                'stock_count': len(stock_analyses),
                'timestamp': datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"分析板块资金流向失败: {e}")
            return {'error': str(e)}

    # ==================== 私有方法 ====================

    def _calculate_volume_concentration(
        self,
        data: pd.DataFrame
    ) -> Tuple[float, List[str]]:
        """
        计算成交量集中度

        通过量比判断近期成交量是否异常放大
        """
        try:
            signals = []

            if 'Volume' not in data.columns or len(data) < 20:
                return 50.0, signals

            volumes = data['Volume'].values

            # 计算不同周期的均量
            vol_5d = np.mean(volumes[-5:]) if len(volumes) >= 5 else volumes[-1]
            vol_10d = np.mean(volumes[-10:]) if len(volumes) >= 10 else vol_5d
            vol_20d = np.mean(volumes[-20:]) if len(volumes) >= 20 else vol_10d

            if vol_20d <= 0:
                return 50.0, signals

            # 量比
            volume_ratio_5_20 = vol_5d / vol_20d
            volume_ratio_today = volumes[-1] / vol_20d if volumes[-1] > 0 else 1.0

            # 评分逻辑
            score = 50.0

            # 近5日量比
            if volume_ratio_5_20 > 2.0:
                score += 30
                signals.append('近5日成交量显著放大')
            elif volume_ratio_5_20 > 1.5:
                score += 20
                signals.append('近5日成交量明显放大')
            elif volume_ratio_5_20 > 1.2:
                score += 10
            elif volume_ratio_5_20 < 0.7:
                score -= 20
                signals.append('近5日成交量萎缩')
            elif volume_ratio_5_20 < 0.5:
                score -= 30
                signals.append('近5日成交量显著萎缩')

            # 今日量比
            if volume_ratio_today > 3.0:
                score += 15
                signals.append('今日成交量暴增')
            elif volume_ratio_today > 2.0:
                score += 10

            return max(0, min(100, score)), signals

        except Exception as e:
            logger.warning(f"计算成交量集中度失败: {e}")
            return 50.0, []

    def _calculate_price_volume_harmony(
        self,
        data: pd.DataFrame
    ) -> Tuple[float, List[str]]:
        """
        计算价量配合度

        理想状态：上涨放量、下跌缩量
        """
        try:
            signals = []

            if len(data) < self.HARMONY_LOOKBACK:
                return 50.0, signals

            close_prices = data['Close'].values
            volumes = data['Volume'].values

            # 计算每日涨跌和成交量变化
            price_changes = np.diff(close_prices[-self.HARMONY_LOOKBACK:])
            vol_changes = np.diff(volumes[-self.HARMONY_LOOKBACK:])

            # 统计配合情况
            harmony_count = 0
            total_count = len(price_changes)

            for i in range(len(price_changes)):
                price_up = price_changes[i] > 0
                vol_up = vol_changes[i] > 0

                # 上涨放量 或 下跌缩量 = 配合
                if (price_up and vol_up) or (not price_up and not vol_up):
                    harmony_count += 1

            harmony_ratio = harmony_count / total_count if total_count > 0 else 0.5

            # 转换为评分
            score = harmony_ratio * 100

            # 生成信号
            if harmony_ratio > 0.7:
                signals.append('价量配合良好')
            elif harmony_ratio > 0.6:
                signals.append('价量配合正常')
            elif harmony_ratio < 0.4:
                signals.append('价量配合较差')
                score -= 10
            elif harmony_ratio < 0.3:
                signals.append('价量严重背离')
                score -= 20

            # 检查特殊模式：连续放量上涨
            recent_5d_prices = close_prices[-5:]
            recent_5d_vols = volumes[-5:]
            if (all(recent_5d_prices[i] < recent_5d_prices[i+1] for i in range(4)) and
                all(recent_5d_vols[i] < recent_5d_vols[i+1] for i in range(4))):
                signals.append('连续放量上涨')
                score += 15

            return max(0, min(100, score)), signals

        except Exception as e:
            logger.warning(f"计算价量配合度失败: {e}")
            return 50.0, []

    def _calculate_chip_concentration(
        self,
        data: pd.DataFrame
    ) -> Tuple[float, List[str]]:
        """
        计算筹码集中度代理指标

        通过价格波动范围收窄程度判断筹码集中
        """
        try:
            signals = []

            if len(data) < 20:
                return 50.0, signals

            high_prices = data['High'].values
            low_prices = data['Low'].values
            close_prices = data['Close'].values

            # 计算近期和历史的波动范围
            recent_range = (np.max(high_prices[-10:]) - np.min(low_prices[-10:])) / np.mean(close_prices[-10:])
            older_range = (np.max(high_prices[-20:-10]) - np.min(low_prices[-20:-10])) / np.mean(close_prices[-20:-10])

            if older_range <= 0:
                return 50.0, signals

            # 波动收窄比例
            range_ratio = recent_range / older_range

            # 评分：波动收窄表示筹码集中
            score = 50.0

            if range_ratio < 0.5:
                score += 35
                signals.append('筹码高度集中')
            elif range_ratio < 0.7:
                score += 25
                signals.append('筹码较为集中')
            elif range_ratio < 0.9:
                score += 10
            elif range_ratio > 1.5:
                score -= 20
                signals.append('筹码分散')
            elif range_ratio > 1.2:
                score -= 10

            # 计算ATR收窄
            atr_recent = np.mean(high_prices[-5:] - low_prices[-5:])
            atr_older = np.mean(high_prices[-20:-10] - low_prices[-20:-10])

            if atr_older > 0 and atr_recent / atr_older < 0.7:
                signals.append('波动率收窄')
                score += 10

            return max(0, min(100, score)), signals

        except Exception as e:
            logger.warning(f"计算筹码集中度失败: {e}")
            return 50.0, []

    def _calculate_relative_turnover(
        self,
        data: pd.DataFrame,
        shares_outstanding: Optional[float] = None
    ) -> Tuple[float, List[str]]:
        """
        计算换手率相对值

        如果有流通股数，计算真实换手率
        否则使用成交量相对变化作为代理
        """
        try:
            signals = []

            if 'Volume' not in data.columns or len(data) < 20:
                return 50.0, signals

            volumes = data['Volume'].values

            if shares_outstanding and shares_outstanding > 0:
                # 计算真实换手率
                turnover_rate_5d = np.mean(volumes[-5:]) / shares_outstanding
                turnover_rate_20d = np.mean(volumes[-20:]) / shares_outstanding

                # 相对换手率
                relative_turnover = turnover_rate_5d / turnover_rate_20d if turnover_rate_20d > 0 else 1.0
            else:
                # 使用成交量变化作为代理
                vol_5d = np.mean(volumes[-5:])
                vol_20d = np.mean(volumes[-20:])
                relative_turnover = vol_5d / vol_20d if vol_20d > 0 else 1.0

            # 评分
            score = 50.0

            if relative_turnover > 2.0:
                score += 30
                signals.append('换手率显著上升')
            elif relative_turnover > 1.5:
                score += 20
                signals.append('换手率明显上升')
            elif relative_turnover > 1.2:
                score += 10
            elif relative_turnover < 0.6:
                score -= 20
                signals.append('换手率显著下降')
            elif relative_turnover < 0.8:
                score -= 10

            return max(0, min(100, score)), signals

        except Exception as e:
            logger.warning(f"计算换手率失败: {e}")
            return 50.0, []

    def _determine_propagation_stage(
        self,
        volume_concentration: float,
        price_volume_harmony: float,
        chip_concentration: float,
        hist_data: pd.DataFrame
    ) -> str:
        """
        判断情绪传导阶段

        基于各指标综合判断当前处于哪个阶段
        """
        try:
            if len(hist_data) < 20:
                return 'neutral'

            close_prices = hist_data['Close'].values

            # 计算价格趋势
            ret_5d = (close_prices[-1] - close_prices[-5]) / close_prices[-5] if len(close_prices) >= 5 else 0
            ret_20d = (close_prices[-1] - close_prices[-20]) / close_prices[-20] if len(close_prices) >= 20 else 0

            # 阶段判断逻辑

            # 龙头启动期：放量启动，价量配合好，中期尚未大涨
            if (volume_concentration > 70 and
                price_volume_harmony > 60 and
                ret_5d > 0.03 and ret_20d < 0.10):
                return 'leader_start'

            # 扩散初期：继续放量，价格加速
            if (volume_concentration > 65 and
                ret_5d > 0.02 and ret_20d > 0.05 and ret_20d < 0.20):
                return 'early_spread'

            # 全面扩散：高位放量，涨幅较大
            if (volume_concentration > 60 and
                ret_20d > 0.15):
                return 'full_spread'

            # 高位分化：量能下降，价格滞涨
            if (volume_concentration < 50 and
                chip_concentration < 50 and
                ret_5d < 0.01 and ret_20d > 0.10):
                return 'high_divergence'

            # 退潮期：缩量下跌
            if (volume_concentration < 45 and
                ret_5d < -0.02 and ret_20d < 0):
                return 'retreat'

            return 'neutral'

        except Exception as e:
            logger.warning(f"判断传导阶段失败: {e}")
            return 'neutral'

    def _calculate_capital_factor(
        self,
        concentration_score: float,
        propagation_stage: str
    ) -> float:
        """
        计算资金结构因子

        用于调整EV模型
        """
        try:
            # 获取阶段基础因子
            stage_info = PROPAGATION_STAGES.get(propagation_stage, PROPAGATION_STAGES['neutral'])
            base_factor = stage_info['capital_factor']

            # 根据集中度调整
            # 高集中度放大正面效果，低集中度放大负面效果
            if concentration_score > 70:
                multiplier = 1.2
            elif concentration_score > 60:
                multiplier = 1.1
            elif concentration_score < 40:
                multiplier = 0.8 if base_factor > 0 else 1.2
            else:
                multiplier = 1.0

            capital_factor = base_factor * multiplier

            # 限制范围
            return max(self.CAPITAL_FACTOR_MIN, min(self.CAPITAL_FACTOR_MAX, capital_factor))

        except Exception:
            return 0.0

    def _default_result(
        self,
        ticker: str,
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """返回默认结果"""
        result = {
            'ticker': ticker,
            'concentration_score': 50.0,
            'volume_concentration': 50.0,
            'price_volume_harmony': 50.0,
            'chip_concentration': 50.0,
            'turnover_score': 50.0,
            'propagation_stage': 'neutral',
            'stage_info': PROPAGATION_STAGES['neutral'],
            'capital_factor': 0.0,
            'signals': [],
            'timestamp': datetime.now().isoformat(),
        }
        if error:
            result['error'] = error
        return result

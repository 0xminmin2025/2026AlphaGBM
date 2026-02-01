"""
板块轮动分析器

基于"以果推因、三维分析框架"方法论，实现板块轮动分析：
1. 识别当日/阶段主线板块
2. 计算板块强度评分
3. 分析个股与板块的同步度
4. 判断轮动溢价

核心算法：
- 相对强度（40%）：板块ETF收益率 - 基准收益率
- 动量趋势（30%）：5日/20日收益率变化方向
- 资金流入（20%）：成交量/20日均量比值
- 轮动位置（10%）：轮入/轮出阶段判断
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import logging

from ..data.sector_mappings import (
    get_sector_etfs,
    get_benchmark_ticker,
    get_sector_name_zh,
    map_yfinance_sector,
    get_etf_for_stock,
    SECTOR_NAMES_ZH,
)

logger = logging.getLogger(__name__)


class SectorRotationAnalyzer:
    """
    板块轮动分析器

    负责计算板块强度、轮动阶段和个股-板块同步度
    """

    # 权重配置
    WEIGHT_RELATIVE_STRENGTH = 0.40  # 相对强度权重
    WEIGHT_MOMENTUM = 0.30           # 动量趋势权重
    WEIGHT_VOLUME = 0.20             # 资金流入权重
    WEIGHT_ROTATION_STAGE = 0.10     # 轮动位置权重

    # 分析周期
    PERIODS = [5, 20, 60]  # 短期(1周)、中期(1月)、长期(3月)

    # 龙头判断阈值
    LEADER_OUTPERFORM_THRESHOLD = 0.05  # 相对板块超额收益5%

    # 轮动溢价范围
    ROTATION_PREMIUM_MAX = 0.10
    ROTATION_PREMIUM_MIN = -0.05

    def __init__(self, data_provider=None):
        """
        初始化分析器

        Args:
            data_provider: 数据提供者实例，用于获取市场数据
        """
        self.data_provider = data_provider
        self._cache = {}  # 简单内存缓存

    def analyze_all_sectors(
        self,
        market: str = 'US',
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        分析所有板块的强度和轮动状态

        Args:
            market: 市场代码 ('US', 'HK', 'CN')
            use_cache: 是否使用缓存

        Returns:
            所有板块的分析结果，按强度排序
        """
        try:
            # 获取板块ETF配置
            sector_etfs = get_sector_etfs(market)
            benchmark = get_benchmark_ticker(market)

            # 获取基准数据
            benchmark_data = self._get_etf_data(benchmark, use_cache)
            if benchmark_data is None:
                logger.error(f"无法获取基准 {benchmark} 数据")
                return {'error': '基准数据获取失败', 'sectors': []}

            benchmark_returns = self._calculate_returns(benchmark_data)

            # 分析各板块
            sector_results = []
            for sector_name, etf_ticker in sector_etfs.items():
                try:
                    result = self._analyze_single_sector(
                        sector_name=sector_name,
                        etf_ticker=etf_ticker,
                        benchmark_returns=benchmark_returns,
                        benchmark_data=benchmark_data,
                        use_cache=use_cache
                    )
                    if result:
                        sector_results.append(result)
                except Exception as e:
                    logger.warning(f"分析板块 {sector_name} 失败: {e}")
                    continue

            # 按强度评分排序
            sector_results.sort(key=lambda x: x.get('strength_score', 0), reverse=True)

            # 判断市场轮动阶段
            rotation_stage = self._determine_market_rotation_stage(sector_results)

            return {
                'market': market,
                'benchmark': benchmark,
                'timestamp': datetime.now().isoformat(),
                'rotation_stage': rotation_stage,
                'sector_count': len(sector_results),
                'top_sectors': [s['sector'] for s in sector_results[:3]],
                'bottom_sectors': [s['sector'] for s in sector_results[-3:]],
                'sectors': sector_results,
            }

        except Exception as e:
            logger.error(f"分析所有板块失败: {e}")
            return {'error': str(e), 'sectors': []}

    def analyze_single_sector(
        self,
        sector_name: str,
        market: str = 'US',
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        分析单个板块的详细信息

        Args:
            sector_name: 板块名称
            market: 市场代码
            use_cache: 是否使用缓存

        Returns:
            单板块详细分析结果
        """
        try:
            sector_etfs = get_sector_etfs(market)
            if sector_name not in sector_etfs:
                return {'error': f'未找到板块 {sector_name}'}

            etf_ticker = sector_etfs[sector_name]
            benchmark = get_benchmark_ticker(market)

            benchmark_data = self._get_etf_data(benchmark, use_cache)
            if benchmark_data is None:
                return {'error': '基准数据获取失败'}

            benchmark_returns = self._calculate_returns(benchmark_data)

            return self._analyze_single_sector(
                sector_name=sector_name,
                etf_ticker=etf_ticker,
                benchmark_returns=benchmark_returns,
                benchmark_data=benchmark_data,
                use_cache=use_cache
            )

        except Exception as e:
            logger.error(f"分析板块 {sector_name} 失败: {e}")
            return {'error': str(e)}

    def analyze_stock_sector_alignment(
        self,
        stock_ticker: str,
        stock_sector: str,
        stock_industry: Optional[str] = None,
        stock_data: Optional[Dict] = None,
        market: str = 'US',
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        分析个股与所属板块的同步度

        Args:
            stock_ticker: 股票代码
            stock_sector: 股票所属板块（yfinance的sector字段）
            stock_industry: 股票所属行业（可选）
            stock_data: 股票历史数据（可选，包含history_prices）
            market: 市场代码
            use_cache: 是否使用缓存

        Returns:
            个股板块同步度分析结果
        """
        try:
            # 映射板块名称
            mapped_sector = map_yfinance_sector(stock_sector)

            # 获取对应ETF
            etf_ticker = get_etf_for_stock(stock_sector, stock_industry, market)

            # 获取ETF数据
            etf_data = self._get_etf_data(etf_ticker, use_cache)
            if etf_data is None:
                return {
                    'sector': mapped_sector,
                    'sector_zh': get_sector_name_zh(mapped_sector),
                    'alignment_score': 50,  # 中性
                    'is_sector_leader': False,
                    'sector_rotation_premium': 0.0,
                    'error': 'ETF数据获取失败'
                }

            # 获取基准数据
            benchmark = get_benchmark_ticker(market)
            benchmark_data = self._get_etf_data(benchmark, use_cache)

            # 获取股票历史价格
            if stock_data and 'history_prices' in stock_data:
                stock_prices = stock_data['history_prices']
            else:
                # 尝试获取股票数据
                stock_hist = self._get_etf_data(stock_ticker, use_cache)
                stock_prices = stock_hist['Close'].tolist() if stock_hist is not None else None

            if stock_prices is None or len(stock_prices) < 20:
                return {
                    'sector': mapped_sector,
                    'sector_zh': get_sector_name_zh(mapped_sector),
                    'alignment_score': 50,
                    'is_sector_leader': False,
                    'sector_rotation_premium': 0.0,
                    'error': '股票历史数据不足'
                }

            # 计算同步度
            alignment_score, correlation = self._calculate_alignment(
                stock_prices, etf_data
            )

            # 计算板块强度
            benchmark_returns = self._calculate_returns(benchmark_data) if benchmark_data is not None else {}
            sector_analysis = self._analyze_single_sector(
                sector_name=mapped_sector,
                etf_ticker=etf_ticker,
                benchmark_returns=benchmark_returns,
                benchmark_data=benchmark_data,
                use_cache=use_cache
            )

            sector_strength = sector_analysis.get('strength_score', 50) if sector_analysis else 50

            # 判断是否为板块龙头
            is_leader, outperformance = self._check_sector_leader(
                stock_prices, etf_data
            )

            # 计算轮动溢价
            rotation_premium = self._calculate_rotation_premium(
                sector_strength=sector_strength,
                alignment_score=alignment_score,
                is_leader=is_leader
            )

            return {
                'sector': mapped_sector,
                'sector_zh': get_sector_name_zh(mapped_sector),
                'etf_ticker': etf_ticker,
                'sector_strength': sector_strength,
                'alignment_score': alignment_score,
                'correlation': round(correlation, 3) if correlation else None,
                'is_sector_leader': is_leader,
                'outperformance_pct': round(outperformance * 100, 2) if outperformance else 0,
                'sector_rotation_premium': round(rotation_premium, 4),
                'sector_trend': sector_analysis.get('trend', 'neutral') if sector_analysis else 'neutral',
                'rotation_stage': sector_analysis.get('rotation_stage', 'unknown') if sector_analysis else 'unknown',
            }

        except Exception as e:
            logger.error(f"分析个股 {stock_ticker} 板块同步度失败: {e}")
            return {
                'sector': map_yfinance_sector(stock_sector),
                'sector_zh': get_sector_name_zh(map_yfinance_sector(stock_sector)),
                'alignment_score': 50,
                'is_sector_leader': False,
                'sector_rotation_premium': 0.0,
                'error': str(e)
            }

    def get_heatmap_data(self, market: str = 'US') -> List[Dict[str, Any]]:
        """
        获取板块热力图数据

        Args:
            market: 市场代码

        Returns:
            热力图数据列表
        """
        all_sectors = self.analyze_all_sectors(market)
        heatmap_data = []

        for sector in all_sectors.get('sectors', []):
            heatmap_data.append({
                'sector': sector['sector'],
                'sector_zh': sector.get('sector_zh', sector['sector']),
                'score': sector.get('strength_score', 50),
                'change_5d': sector.get('return_5d', 0),
                'change_20d': sector.get('return_20d', 0),
                'volume_ratio': sector.get('volume_ratio', 1.0),
                'trend': sector.get('trend', 'neutral'),
            })

        return heatmap_data

    # ==================== 私有方法 ====================

    def _get_etf_data(
        self,
        ticker: str,
        use_cache: bool = True
    ) -> Optional[pd.DataFrame]:
        """获取ETF历史数据"""
        try:
            cache_key = f"etf_{ticker}"
            if use_cache and cache_key in self._cache:
                cached_data, cached_time = self._cache[cache_key]
                # 5分钟缓存有效期
                if datetime.now() - cached_time < timedelta(minutes=5):
                    return cached_data

            # 使用DataProvider获取数据（统一数据访问）
            from ....services.data_provider import DataProvider
            provider = DataProvider(ticker)
            hist = provider.history(period="3mo", timeout=10)

            if hist is None or hist.empty:
                return None

            if use_cache:
                self._cache[cache_key] = (hist, datetime.now())

            return hist

        except Exception as e:
            logger.warning(f"获取ETF {ticker} 数据失败: {e}")
            return None

    def _calculate_returns(self, data: pd.DataFrame) -> Dict[str, float]:
        """计算不同周期的收益率"""
        if data is None or data.empty:
            return {}

        try:
            close_prices = data['Close'].values
            returns = {}

            for period in self.PERIODS:
                if len(close_prices) >= period:
                    ret = (close_prices[-1] - close_prices[-period]) / close_prices[-period]
                    returns[f'return_{period}d'] = ret

            return returns
        except Exception as e:
            logger.warning(f"计算收益率失败: {e}")
            return {}

    def _analyze_single_sector(
        self,
        sector_name: str,
        etf_ticker: str,
        benchmark_returns: Dict[str, float],
        benchmark_data: Optional[pd.DataFrame],
        use_cache: bool = True
    ) -> Optional[Dict[str, Any]]:
        """分析单个板块"""
        try:
            etf_data = self._get_etf_data(etf_ticker, use_cache)
            if etf_data is None:
                return None

            # 计算板块收益率
            sector_returns = self._calculate_returns(etf_data)

            # 1. 相对强度评分（0-100）
            relative_strength = self._calculate_relative_strength(
                sector_returns, benchmark_returns
            )

            # 2. 动量趋势评分（0-100）
            momentum_score = self._calculate_momentum_score(etf_data)

            # 3. 资金流入评分（0-100）
            volume_score, volume_ratio = self._calculate_volume_score(etf_data)

            # 4. 轮动阶段评分（0-100）
            rotation_stage, rotation_score = self._determine_rotation_stage(
                sector_returns, etf_data
            )

            # 综合评分
            strength_score = (
                relative_strength * self.WEIGHT_RELATIVE_STRENGTH +
                momentum_score * self.WEIGHT_MOMENTUM +
                volume_score * self.WEIGHT_VOLUME +
                rotation_score * self.WEIGHT_ROTATION_STAGE
            )

            # 确定趋势方向
            trend = self._determine_trend(sector_returns, momentum_score)

            return {
                'sector': sector_name,
                'sector_zh': get_sector_name_zh(sector_name),
                'etf_ticker': etf_ticker,
                'strength_score': round(strength_score, 1),
                'relative_strength': round(relative_strength, 1),
                'momentum_score': round(momentum_score, 1),
                'volume_score': round(volume_score, 1),
                'volume_ratio': round(volume_ratio, 2),
                'rotation_stage': rotation_stage,
                'rotation_score': round(rotation_score, 1),
                'trend': trend,
                'return_5d': round(sector_returns.get('return_5d', 0) * 100, 2),
                'return_20d': round(sector_returns.get('return_20d', 0) * 100, 2),
                'return_60d': round(sector_returns.get('return_60d', 0) * 100, 2),
            }

        except Exception as e:
            logger.warning(f"分析板块 {sector_name} 详情失败: {e}")
            return None

    def _calculate_relative_strength(
        self,
        sector_returns: Dict[str, float],
        benchmark_returns: Dict[str, float]
    ) -> float:
        """
        计算相对强度评分

        相对强度 = 板块收益率 - 基准收益率
        转换为0-100评分
        """
        try:
            # 主要看20日相对强度
            sector_ret = sector_returns.get('return_20d', 0)
            bench_ret = benchmark_returns.get('return_20d', 0)

            relative_return = sector_ret - bench_ret

            # 将相对收益率映射到0-100
            # -10% → 0分，0% → 50分，+10% → 100分
            score = 50 + (relative_return * 500)
            return max(0, min(100, score))

        except Exception:
            return 50.0

    def _calculate_momentum_score(self, data: pd.DataFrame) -> float:
        """
        计算动量趋势评分

        检查5日/20日收益率方向和趋势
        """
        try:
            close_prices = data['Close'].values

            if len(close_prices) < 20:
                return 50.0

            # 计算短期和中期收益率
            ret_5d = (close_prices[-1] - close_prices[-5]) / close_prices[-5]
            ret_20d = (close_prices[-1] - close_prices[-20]) / close_prices[-20]

            score = 50.0

            # 短期趋势（权重60%）
            if ret_5d > 0.03:
                score += 30
            elif ret_5d > 0.01:
                score += 15
            elif ret_5d < -0.03:
                score -= 30
            elif ret_5d < -0.01:
                score -= 15

            # 中期趋势（权重40%）
            if ret_20d > 0.05:
                score += 20
            elif ret_20d > 0.02:
                score += 10
            elif ret_20d < -0.05:
                score -= 20
            elif ret_20d < -0.02:
                score -= 10

            return max(0, min(100, score))

        except Exception:
            return 50.0

    def _calculate_volume_score(self, data: pd.DataFrame) -> Tuple[float, float]:
        """
        计算成交量评分和量比

        量比 = 近5日均量 / 20日均量
        """
        try:
            if 'Volume' not in data.columns:
                return 50.0, 1.0

            volumes = data['Volume'].values

            if len(volumes) < 20:
                return 50.0, 1.0

            # 计算量比
            vol_5d = np.mean(volumes[-5:])
            vol_20d = np.mean(volumes[-20:])

            if vol_20d <= 0:
                return 50.0, 1.0

            volume_ratio = vol_5d / vol_20d

            # 转换为评分
            # 量比 < 0.8 → 偏弱（40分）
            # 量比 0.8-1.2 → 正常（50分）
            # 量比 1.2-1.5 → 偏强（65分）
            # 量比 > 1.5 → 强势（80分）
            if volume_ratio < 0.8:
                score = 40
            elif volume_ratio < 1.2:
                score = 50
            elif volume_ratio < 1.5:
                score = 65
            else:
                score = min(80, 65 + (volume_ratio - 1.5) * 30)

            return score, volume_ratio

        except Exception:
            return 50.0, 1.0

    def _determine_rotation_stage(
        self,
        returns: Dict[str, float],
        data: pd.DataFrame
    ) -> Tuple[str, float]:
        """
        判断轮动阶段

        轮入期：短期上涨、中期偏弱 → 正在启动
        主升期：短期强、中期强 → 主升浪
        轮出期：短期走弱、中期仍强 → 获利了结
        调整期：短期弱、中期弱 → 调整/轮出
        """
        try:
            ret_5d = returns.get('return_5d', 0)
            ret_20d = returns.get('return_20d', 0)
            ret_60d = returns.get('return_60d', 0)

            # 轮入期：短期涨势启动
            if ret_5d > 0.02 and ret_20d < 0.03:
                return 'rotating_in', 70

            # 主升期：短中期都强
            if ret_5d > 0.01 and ret_20d > 0.03:
                return 'main_rise', 85

            # 持续强势
            if ret_5d > 0 and ret_20d > 0.05 and ret_60d > 0.10:
                return 'strong_trend', 80

            # 轮出期：短期走弱但中期仍强
            if ret_5d < 0 and ret_20d > 0.03:
                return 'rotating_out', 40

            # 调整期
            if ret_5d < -0.02 and ret_20d < 0:
                return 'correction', 25

            # 底部企稳
            if ret_5d > 0 and ret_20d < -0.05:
                return 'bottoming', 55

            return 'neutral', 50

        except Exception:
            return 'unknown', 50

    def _determine_market_rotation_stage(
        self,
        sector_results: List[Dict]
    ) -> Dict[str, Any]:
        """判断整体市场轮动阶段"""
        try:
            if not sector_results:
                return {'stage': 'unknown', 'description': '数据不足'}

            # 统计各阶段板块数量
            stage_counts = {}
            for result in sector_results:
                stage = result.get('rotation_stage', 'unknown')
                stage_counts[stage] = stage_counts.get(stage, 0) + 1

            # 判断主导阶段
            dominant_stage = max(stage_counts, key=stage_counts.get)

            # 计算市场宽度（上涨板块占比）
            rising_count = sum(
                1 for r in sector_results
                if r.get('return_5d', 0) > 0
            )
            market_breadth = rising_count / len(sector_results)

            stage_descriptions = {
                'rotating_in': '轮动启动期 - 资金开始进入',
                'main_rise': '主升浪 - 板块全面上涨',
                'strong_trend': '强势趋势 - 持续走强',
                'rotating_out': '轮出期 - 获利了结开始',
                'correction': '调整期 - 市场回调',
                'bottoming': '底部企稳 - 等待反弹',
                'neutral': '盘整期 - 方向不明',
            }

            return {
                'stage': dominant_stage,
                'description': stage_descriptions.get(dominant_stage, '未知'),
                'market_breadth': round(market_breadth, 2),
                'stage_distribution': stage_counts,
            }

        except Exception:
            return {'stage': 'unknown', 'description': '分析失败'}

    def _determine_trend(
        self,
        returns: Dict[str, float],
        momentum_score: float
    ) -> str:
        """确定趋势方向"""
        try:
            ret_5d = returns.get('return_5d', 0)
            ret_20d = returns.get('return_20d', 0)

            if momentum_score >= 70 and ret_5d > 0 and ret_20d > 0:
                return 'bullish'
            elif momentum_score <= 30 and ret_5d < 0 and ret_20d < 0:
                return 'bearish'
            elif ret_5d > 0.02:
                return 'rising'
            elif ret_5d < -0.02:
                return 'falling'
            else:
                return 'neutral'

        except Exception:
            return 'neutral'

    def _calculate_alignment(
        self,
        stock_prices: List[float],
        etf_data: pd.DataFrame
    ) -> Tuple[float, Optional[float]]:
        """
        计算个股与板块的同步度

        使用收益率相关性作为同步度指标
        """
        try:
            etf_prices = etf_data['Close'].values

            # 对齐长度
            min_len = min(len(stock_prices), len(etf_prices), 60)
            if min_len < 10:
                return 50.0, None

            stock_arr = np.array(stock_prices[-min_len:])
            etf_arr = etf_prices[-min_len:]

            # 计算收益率
            stock_returns = np.diff(stock_arr) / stock_arr[:-1]
            etf_returns = np.diff(etf_arr) / etf_arr[:-1]

            # 计算相关性
            correlation = np.corrcoef(stock_returns, etf_returns)[0, 1]

            # 转换为评分（相关性 -1 到 1 → 评分 0 到 100）
            alignment_score = (correlation + 1) * 50

            return alignment_score, correlation

        except Exception as e:
            logger.warning(f"计算同步度失败: {e}")
            return 50.0, None

    def _check_sector_leader(
        self,
        stock_prices: List[float],
        etf_data: pd.DataFrame
    ) -> Tuple[bool, Optional[float]]:
        """
        检查是否为板块龙头

        龙头定义：相对板块ETF有显著超额收益（>5%）
        """
        try:
            etf_prices = etf_data['Close'].values

            if len(stock_prices) < 20 or len(etf_prices) < 20:
                return False, None

            # 计算20日收益率
            stock_ret = (stock_prices[-1] - stock_prices[-20]) / stock_prices[-20]
            etf_ret = (etf_prices[-1] - etf_prices[-20]) / etf_prices[-20]

            outperformance = stock_ret - etf_ret

            is_leader = outperformance > self.LEADER_OUTPERFORM_THRESHOLD

            return is_leader, outperformance

        except Exception:
            return False, None

    def _calculate_rotation_premium(
        self,
        sector_strength: float,
        alignment_score: float,
        is_leader: bool
    ) -> float:
        """
        计算轮动溢价

        溢价因子取决于：
        1. 板块强度（强势板块+溢价）
        2. 同步度（高同步+溢价）
        3. 龙头地位（龙头+额外溢价）
        """
        try:
            # 基础溢价：基于板块强度
            # 强度 70-100 → +0.02 到 +0.05
            # 强度 30-70 → -0.01 到 +0.02
            # 强度 0-30 → -0.05 到 -0.01
            if sector_strength >= 70:
                base_premium = 0.02 + (sector_strength - 70) / 30 * 0.03
            elif sector_strength >= 30:
                base_premium = -0.01 + (sector_strength - 30) / 40 * 0.03
            else:
                base_premium = -0.05 + sector_strength / 30 * 0.04

            # 同步度调整：高同步度时放大溢价效果
            if alignment_score >= 70:
                sync_multiplier = 1.2
            elif alignment_score >= 50:
                sync_multiplier = 1.0
            else:
                sync_multiplier = 0.8

            premium = base_premium * sync_multiplier

            # 龙头额外溢价
            if is_leader and sector_strength >= 60:
                premium += 0.02

            # 限制范围
            return max(self.ROTATION_PREMIUM_MIN, min(self.ROTATION_PREMIUM_MAX, premium))

        except Exception:
            return 0.0

"""
资金结构分析服务

提供资金结构分析的服务层封装，包含：
- 历史数据获取
- 结果缓存
- 与板块分析整合
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import threading
import pandas as pd

from ..analysis.stock_analysis.core.capital_structure import (
    CapitalStructureAnalyzer,
    PROPAGATION_STAGES,
)
from .data_provider import DataProvider

logger = logging.getLogger(__name__)


class CapitalStructureService:
    """
    资金结构分析服务

    提供个股资金结构分析能力
    """

    # 缓存配置
    CACHE_TTL_SECONDS = 300  # 5分钟缓存

    def __init__(self):
        self._analyzer = CapitalStructureAnalyzer()
        self._cache: Dict[str, tuple] = {}  # key -> (data, timestamp)
        self._lock = threading.Lock()

    def analyze_stock_capital(
        self,
        ticker: str,
        hist_data: Optional[pd.DataFrame] = None,
        market_data: Optional[Dict] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        分析个股资金结构

        Args:
            ticker: 股票代码
            hist_data: 历史OHLCV数据（可选，如未提供则自动获取）
            market_data: 市场数据（可选，用于获取流通股等信息）
            use_cache: 是否使用缓存

        Returns:
            资金结构分析结果
        """
        try:
            cache_key = f"capital_{ticker}"

            # 检查缓存
            if use_cache:
                cached_data = self._get_from_cache(cache_key)
                if cached_data:
                    logger.debug(f"资金结构分析命中缓存: {ticker}")
                    return cached_data

            # 如果没有提供历史数据，则获取
            if hist_data is None:
                hist_data = self._get_stock_history(ticker)

            if hist_data is None or hist_data.empty:
                return {
                    'ticker': ticker,
                    'concentration_score': 50,
                    'propagation_stage': 'neutral',
                    'capital_factor': 0.0,
                    'signals': [],
                    'error': '历史数据获取失败'
                }

            # 获取流通股数（如果有market_data）
            shares_outstanding = None
            if market_data:
                shares_outstanding = market_data.get('shares_outstanding')

            # 执行分析
            result = self._analyzer.analyze_capital_structure(
                ticker=ticker,
                hist_data=hist_data,
                shares_outstanding=shares_outstanding,
            )

            # 保存到缓存
            if 'error' not in result:
                self._set_to_cache(cache_key, result)

            return result

        except Exception as e:
            logger.error(f"分析资金结构失败 {ticker}: {e}")
            return {
                'ticker': ticker,
                'concentration_score': 50,
                'propagation_stage': 'neutral',
                'capital_factor': 0.0,
                'signals': [],
                'error': str(e)
            }

    def get_capital_factor(
        self,
        ticker: str,
        hist_data: Optional[pd.DataFrame] = None
    ) -> float:
        """
        快速获取资金因子

        用于EV模型计算

        Args:
            ticker: 股票代码
            hist_data: 历史数据

        Returns:
            资金因子（-0.03 到 +0.05）
        """
        try:
            result = self.analyze_stock_capital(ticker, hist_data)
            return result.get('capital_factor', 0.0)

        except Exception as e:
            logger.warning(f"获取资金因子失败 {ticker}: {e}")
            return 0.0

    def get_propagation_stage(
        self,
        ticker: str,
        hist_data: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
        """
        获取情绪传导阶段

        Args:
            ticker: 股票代码
            hist_data: 历史数据

        Returns:
            阶段信息
        """
        try:
            result = self.analyze_stock_capital(ticker, hist_data)
            stage = result.get('propagation_stage', 'neutral')
            stage_info = PROPAGATION_STAGES.get(stage, PROPAGATION_STAGES['neutral'])

            return {
                'stage': stage,
                'name': stage_info['name'],
                'name_en': stage_info['name_en'],
                'description': stage_info['description'],
                'capital_factor': stage_info['capital_factor'],
                'probability_persistence': stage_info['probability_persistence'],
            }

        except Exception as e:
            logger.warning(f"获取传导阶段失败 {ticker}: {e}")
            return {
                'stage': 'neutral',
                'name': '中性期',
                'description': '无明显资金动向',
                'capital_factor': 0.0,
            }

    def get_concentration_signals(
        self,
        ticker: str,
        hist_data: Optional[pd.DataFrame] = None
    ) -> List[str]:
        """
        获取资金集中度信号

        Args:
            ticker: 股票代码
            hist_data: 历史数据

        Returns:
            信号列表
        """
        try:
            result = self.analyze_stock_capital(ticker, hist_data)
            return result.get('signals', [])

        except Exception as e:
            logger.warning(f"获取资金信号失败 {ticker}: {e}")
            return []

    def get_all_stages(self) -> List[Dict[str, Any]]:
        """
        获取所有情绪传导阶段定义

        Returns:
            阶段定义列表
        """
        return [
            {
                'id': stage_id,
                **stage_info
            }
            for stage_id, stage_info in PROPAGATION_STAGES.items()
        ]

    def clear_cache(self, ticker: Optional[str] = None):
        """
        清除缓存

        Args:
            ticker: 指定股票，None表示清除所有
        """
        with self._lock:
            if ticker:
                cache_key = f"capital_{ticker}"
                if cache_key in self._cache:
                    del self._cache[cache_key]
                    logger.debug(f"清除缓存: {ticker}")
            else:
                self._cache.clear()
                logger.info("清除所有资金分析缓存")

    # ==================== 私有方法 ====================

    def _get_stock_history(
        self,
        ticker: str,
        period: str = "3mo"
    ) -> Optional[pd.DataFrame]:
        """获取股票历史数据"""
        try:
            provider = DataProvider(ticker)
            hist = provider.history(period=period, timeout=10)
            return hist

        except Exception as e:
            logger.warning(f"获取历史数据失败 {ticker}: {e}")
            return None

    def _get_from_cache(self, key: str) -> Optional[Any]:
        """从缓存获取数据"""
        with self._lock:
            if key not in self._cache:
                return None

            data, timestamp = self._cache[key]
            if datetime.now() - timestamp > timedelta(seconds=self.CACHE_TTL_SECONDS):
                del self._cache[key]
                return None

            return data

    def _set_to_cache(self, key: str, data: Any):
        """保存数据到缓存"""
        with self._lock:
            self._cache[key] = (data, datetime.now())


# 单例实例
_capital_structure_service: Optional[CapitalStructureService] = None


def get_capital_structure_service() -> CapitalStructureService:
    """获取资金结构服务单例"""
    global _capital_structure_service
    if _capital_structure_service is None:
        _capital_structure_service = CapitalStructureService()
    return _capital_structure_service

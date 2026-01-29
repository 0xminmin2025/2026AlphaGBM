"""
板块轮动分析服务

提供板块轮动分析的服务层封装，包含：
- 缓存管理
- 并行数据获取
- 结果格式化
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import threading

from ..analysis.stock_analysis.core.sector_rotation import SectorRotationAnalyzer
from ..analysis.stock_analysis.data.sector_mappings import (
    get_sector_etfs,
    get_benchmark_ticker,
    get_sector_name_zh,
    SECTOR_ETF_MAPPING,
)

logger = logging.getLogger(__name__)


class SectorRotationService:
    """
    板块轮动分析服务

    提供缓存支持和并行获取能力
    """

    # 缓存配置
    CACHE_TTL_SECONDS = 300  # 5分钟缓存

    def __init__(self):
        self._analyzer = SectorRotationAnalyzer()
        self._cache: Dict[str, tuple] = {}  # key -> (data, timestamp)
        self._lock = threading.Lock()

    def get_rotation_overview(
        self,
        market: str = 'US',
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        获取板块轮动概览

        Args:
            market: 市场代码 ('US', 'HK', 'CN')
            use_cache: 是否使用缓存

        Returns:
            板块轮动概览数据
        """
        try:
            cache_key = f"rotation_overview_{market}"

            # 检查缓存
            if use_cache:
                cached_data = self._get_from_cache(cache_key)
                if cached_data:
                    logger.info(f"板块轮动概览命中缓存: {market}")
                    return cached_data

            # 执行分析
            logger.info(f"开始分析板块轮动: {market}")
            result = self._analyzer.analyze_all_sectors(market, use_cache=True)

            # 添加额外字段
            result['market_name'] = self._get_market_name(market)
            result['cache_time'] = datetime.now().isoformat()

            # 保存到缓存
            self._set_to_cache(cache_key, result)

            return result

        except Exception as e:
            logger.error(f"获取板块轮动概览失败: {e}")
            return {
                'error': str(e),
                'market': market,
                'sectors': []
            }

    def get_sector_detail(
        self,
        sector_name: str,
        market: str = 'US',
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        获取单板块详情

        Args:
            sector_name: 板块名称
            market: 市场代码

        Returns:
            板块详情
        """
        try:
            cache_key = f"sector_detail_{market}_{sector_name}"

            if use_cache:
                cached_data = self._get_from_cache(cache_key)
                if cached_data:
                    return cached_data

            result = self._analyzer.analyze_single_sector(sector_name, market, use_cache=True)

            if result and 'error' not in result:
                self._set_to_cache(cache_key, result)

            return result

        except Exception as e:
            logger.error(f"获取板块详情失败 {sector_name}: {e}")
            return {'error': str(e)}

    def analyze_stock_sector(
        self,
        ticker: str,
        sector: str,
        industry: Optional[str] = None,
        stock_data: Optional[Dict] = None,
        market: str = 'US'
    ) -> Dict[str, Any]:
        """
        分析个股的板块同步度和轮动溢价

        Args:
            ticker: 股票代码
            sector: 股票所属板块
            industry: 股票所属行业
            stock_data: 股票数据（包含history_prices）
            market: 市场代码

        Returns:
            个股板块分析结果
        """
        try:
            result = self._analyzer.analyze_stock_sector_alignment(
                stock_ticker=ticker,
                stock_sector=sector,
                stock_industry=industry,
                stock_data=stock_data,
                market=market,
                use_cache=True
            )

            return result

        except Exception as e:
            logger.error(f"分析个股板块失败 {ticker}: {e}")
            return {
                'sector': sector,
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
        try:
            cache_key = f"heatmap_{market}"
            cached_data = self._get_from_cache(cache_key)
            if cached_data:
                return cached_data

            result = self._analyzer.get_heatmap_data(market)

            if result:
                self._set_to_cache(cache_key, result)

            return result

        except Exception as e:
            logger.error(f"获取热力图数据失败: {e}")
            return []

    def get_top_sectors(
        self,
        market: str = 'US',
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        获取强势板块排行

        Args:
            market: 市场代码
            limit: 返回数量

        Returns:
            强势板块列表
        """
        try:
            overview = self.get_rotation_overview(market)
            sectors = overview.get('sectors', [])

            # 取前N个
            top_sectors = sectors[:limit]

            return [{
                'rank': i + 1,
                'sector': s['sector'],
                'sector_zh': s.get('sector_zh', s['sector']),
                'strength_score': s.get('strength_score', 0),
                'trend': s.get('trend', 'neutral'),
                'return_5d': s.get('return_5d', 0),
            } for i, s in enumerate(top_sectors)]

        except Exception as e:
            logger.error(f"获取强势板块失败: {e}")
            return []

    def get_bottom_sectors(
        self,
        market: str = 'US',
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        获取弱势板块排行

        Args:
            market: 市场代码
            limit: 返回数量

        Returns:
            弱势板块列表
        """
        try:
            overview = self.get_rotation_overview(market)
            sectors = overview.get('sectors', [])

            # 取后N个
            bottom_sectors = sectors[-limit:] if len(sectors) >= limit else sectors

            return [{
                'rank': i + 1,
                'sector': s['sector'],
                'sector_zh': s.get('sector_zh', s['sector']),
                'strength_score': s.get('strength_score', 0),
                'trend': s.get('trend', 'neutral'),
                'return_5d': s.get('return_5d', 0),
            } for i, s in enumerate(reversed(bottom_sectors))]

        except Exception as e:
            logger.error(f"获取弱势板块失败: {e}")
            return []

    def get_available_sectors(self, market: str = 'US') -> List[Dict[str, str]]:
        """
        获取可用板块列表

        Args:
            market: 市场代码

        Returns:
            板块列表
        """
        try:
            sector_etfs = get_sector_etfs(market)
            return [{
                'sector': sector,
                'sector_zh': get_sector_name_zh(sector),
                'etf_ticker': etf,
            } for sector, etf in sector_etfs.items()]

        except Exception as e:
            logger.error(f"获取板块列表失败: {e}")
            return []

    def clear_cache(self, market: Optional[str] = None):
        """
        清除缓存

        Args:
            market: 指定市场，None表示清除所有
        """
        with self._lock:
            if market:
                keys_to_remove = [k for k in self._cache.keys() if market in k]
                for key in keys_to_remove:
                    del self._cache[key]
                logger.info(f"清除{market}市场缓存: {len(keys_to_remove)}项")
            else:
                self._cache.clear()
                logger.info("清除所有板块分析缓存")

    # ==================== 私有方法 ====================

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

    def _get_market_name(self, market: str) -> str:
        """获取市场名称"""
        names = {
            'US': '美股',
            'HK': '港股',
            'CN': 'A股',
        }
        return names.get(market, market)


# 单例实例
_sector_rotation_service: Optional[SectorRotationService] = None


def get_sector_rotation_service() -> SectorRotationService:
    """获取板块轮动服务单例"""
    global _sector_rotation_service
    if _sector_rotation_service is None:
        _sector_rotation_service = SectorRotationService()
    return _sector_rotation_service

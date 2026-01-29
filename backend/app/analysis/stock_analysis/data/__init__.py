"""
Data configurations for stock analysis.
"""

from .sector_mappings import (
    US_SECTOR_ETFS,
    HK_SECTOR_ETFS,
    CN_SECTOR_ETFS,
    SECTOR_ETF_MAPPING,
    SECTOR_BENCHMARKS,
    get_sector_etfs,
    get_benchmark_ticker,
    SECTOR_NAMES_ZH,
)

__all__ = [
    'US_SECTOR_ETFS',
    'HK_SECTOR_ETFS',
    'CN_SECTOR_ETFS',
    'SECTOR_ETF_MAPPING',
    'SECTOR_BENCHMARKS',
    'get_sector_etfs',
    'get_benchmark_ticker',
    'SECTOR_NAMES_ZH',
]

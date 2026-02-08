"""
Data Provider Adapters

Each adapter implements the DataProviderAdapter interface for a specific
data source (yfinance, defeatbeta-api, Tiger API, Alpha Vantage, Tushare, etc.).
"""

from .yfinance_adapter import YFinanceAdapter
from .defeatbeta_adapter import DefeatBetaAdapter
from .tiger_adapter import TigerAdapter
from .alphavantage_adapter import AlphaVantageAdapter
from .tushare_adapter import TushareAdapter
from .akshare_commodity_adapter import AkShareCommodityAdapter

__all__ = [
    "YFinanceAdapter",
    "DefeatBetaAdapter",
    "TigerAdapter",
    "AlphaVantageAdapter",
    "TushareAdapter",
    "AkShareCommodityAdapter",
]

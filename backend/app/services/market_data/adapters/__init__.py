"""
Data Provider Adapters

Each adapter implements the DataProviderAdapter interface for a specific
data source (yfinance, defeatbeta-api, Tiger API, Alpha Vantage, etc.).
"""

from .yfinance_adapter import YFinanceAdapter
from .defeatbeta_adapter import DefeatBetaAdapter
from .tiger_adapter import TigerAdapter
from .alphavantage_adapter import AlphaVantageAdapter

__all__ = [
    "YFinanceAdapter",
    "DefeatBetaAdapter",
    "TigerAdapter",
    "AlphaVantageAdapter",
]

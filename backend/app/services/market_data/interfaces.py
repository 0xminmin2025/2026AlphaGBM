"""
Market Data Interfaces and Data Classes

Defines the abstract interface for data providers and standardized data structures
that ensure consistent data format across all providers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Union
from enum import Enum
import pandas as pd


class DataType(Enum):
    """Types of market data that can be requested."""
    QUOTE = "quote"                      # Real-time price
    HISTORY = "history"                  # Historical OHLCV
    INFO = "info"                        # Company info (sector, industry)
    FUNDAMENTALS = "fundamentals"        # PE, PB, ROE, margins
    OPTIONS_CHAIN = "options_chain"      # Full options chain
    OPTIONS_EXPIRATIONS = "options_expirations"  # Available expiry dates
    EARNINGS = "earnings"                # Quarterly earnings
    MACRO = "macro"                      # VIX, Treasury, indices


class Market(Enum):
    """Supported markets."""
    US = "us"
    HK = "hk"
    CN = "cn"


class ProviderStatus(Enum):
    """Provider health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"       # Some requests failing
    RATE_LIMITED = "rate_limited"
    UNAVAILABLE = "unavailable"


@dataclass
class QuoteData:
    """Standardized quote data across all providers."""
    symbol: str
    current_price: float
    previous_close: Optional[float] = None
    open_price: Optional[float] = None
    day_high: Optional[float] = None
    day_low: Optional[float] = None
    volume: Optional[int] = None
    market_cap: Optional[float] = None
    timestamp: Optional[datetime] = None
    source: str = ""  # Which provider returned this

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility."""
        return {
            'symbol': self.symbol,
            'currentPrice': self.current_price,
            'regularMarketPrice': self.current_price,
            'previousClose': self.previous_close,
            'open': self.open_price,
            'dayHigh': self.day_high,
            'dayLow': self.day_low,
            'volume': self.volume,
            'marketCap': self.market_cap,
            '_source': self.source,
        }


@dataclass
class FundamentalsData:
    """Standardized fundamentals data."""
    symbol: str
    # Valuation
    pe_ratio: Optional[float] = None
    forward_pe: Optional[float] = None
    pb_ratio: Optional[float] = None
    ps_ratio: Optional[float] = None
    peg_ratio: Optional[float] = None
    ev_ebitda: Optional[float] = None
    # Profitability
    profit_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    roe: Optional[float] = None
    roa: Optional[float] = None
    # Growth
    revenue_growth: Optional[float] = None
    earnings_growth: Optional[float] = None
    # Other
    beta: Optional[float] = None
    dividend_yield: Optional[float] = None
    eps_trailing: Optional[float] = None
    eps_forward: Optional[float] = None
    # Analyst
    target_high: Optional[float] = None
    target_low: Optional[float] = None
    target_mean: Optional[float] = None
    recommendation: Optional[str] = None
    source: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility."""
        return {
            'trailingPE': self.pe_ratio,
            'forwardPE': self.forward_pe,
            'priceToBook': self.pb_ratio,
            'priceToSalesTrailing12Months': self.ps_ratio,
            'pegRatio': self.peg_ratio,
            'enterpriseToEbitda': self.ev_ebitda,
            'profitMargins': self.profit_margin,
            'operatingMargins': self.operating_margin,
            'returnOnEquity': self.roe,
            'returnOnAssets': self.roa,
            'revenueGrowth': self.revenue_growth,
            'earningsGrowth': self.earnings_growth,
            'beta': self.beta,
            'dividendYield': self.dividend_yield,
            'trailingEps': self.eps_trailing,
            'forwardEps': self.eps_forward,
            'targetHighPrice': self.target_high,
            'targetLowPrice': self.target_low,
            'targetMeanPrice': self.target_mean,
            'recommendationKey': self.recommendation,
            '_source': self.source,
        }


@dataclass
class CompanyInfo:
    """Standardized company info."""
    symbol: str
    name: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    description: Optional[str] = None
    employees: Optional[int] = None
    website: Optional[str] = None
    currency: Optional[str] = None
    exchange: Optional[str] = None
    source: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility."""
        return {
            'symbol': self.symbol,
            'shortName': self.name,
            'longName': self.name,
            'sector': self.sector,
            'industry': self.industry,
            'country': self.country,
            'longBusinessSummary': self.description,
            'fullTimeEmployees': self.employees,
            'website': self.website,
            'currency': self.currency,
            'exchange': self.exchange,
            '_source': self.source,
        }


@dataclass
class HistoryData:
    """Wrapper for historical OHLCV data with metadata."""
    symbol: str
    df: pd.DataFrame  # DatetimeIndex with Open, High, Low, Close, Volume columns
    period: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    source: str = ""

    @property
    def empty(self) -> bool:
        return self.df is None or self.df.empty


@dataclass
class OptionsChainData:
    """Standardized options chain."""
    symbol: str
    expiry_date: str
    underlying_price: float
    calls: pd.DataFrame  # strike, bid, ask, last, volume, oi, iv, delta, gamma, theta, vega
    puts: pd.DataFrame
    source: str = ""

    @property
    def empty(self) -> bool:
        return (self.calls is None or self.calls.empty) and (self.puts is None or self.puts.empty)


@dataclass
class EarningsData:
    """Standardized earnings data."""
    symbol: str
    quarterly_earnings: pd.DataFrame  # Date index, Earnings, Revenue columns
    source: str = ""

    @property
    def empty(self) -> bool:
        return self.quarterly_earnings is None or self.quarterly_earnings.empty


@dataclass
class DataFetchResult:
    """Result of a data fetch operation with metadata."""
    success: bool
    data: Any = None
    source: str = ""
    fallback_used: bool = False
    fallback_from: Optional[str] = None  # Which provider failed
    error: Optional[str] = None
    response_time_ms: float = 0
    cached: bool = False

    def __bool__(self) -> bool:
        return self.success and self.data is not None


class DataProviderAdapter(ABC):
    """
    Abstract base class for all data provider adapters.

    Each adapter implements the same interface for different data sources
    (yfinance, defeatbeta-api, Tiger API, etc.).

    Implementations should:
    1. Handle their own rate limiting internally
    2. Raise exceptions only for unrecoverable errors
    3. Return None for missing/unavailable data (not exceptions)
    4. Track their own health status
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for logging/metrics."""
        pass

    @property
    @abstractmethod
    def supported_data_types(self) -> List[DataType]:
        """List of data types this provider can supply."""
        pass

    @property
    @abstractmethod
    def supported_markets(self) -> List[Market]:
        """List of markets this provider supports."""
        pass

    @abstractmethod
    def get_quote(self, symbol: str) -> Optional[QuoteData]:
        """
        Get real-time quote for a symbol.

        Returns:
            QuoteData if successful, None if data unavailable
        """
        pass

    @abstractmethod
    def get_history(
        self,
        symbol: str,
        period: Optional[str] = None,
        start: Optional[date] = None,
        end: Optional[date] = None
    ) -> Optional[HistoryData]:
        """
        Get historical OHLCV data.

        Args:
            symbol: Stock symbol
            period: Period string (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max)
            start: Start date (alternative to period)
            end: End date (alternative to period)

        Returns:
            HistoryData if successful, None if data unavailable
        """
        pass

    @abstractmethod
    def get_info(self, symbol: str) -> Optional[CompanyInfo]:
        """
        Get company info (sector, industry, description).

        Returns:
            CompanyInfo if successful, None if data unavailable
        """
        pass

    @abstractmethod
    def get_fundamentals(self, symbol: str) -> Optional[FundamentalsData]:
        """
        Get fundamental metrics (PE, PB, ROE, margins, etc.).

        Returns:
            FundamentalsData if successful, None if data unavailable
        """
        pass

    def get_options_expirations(self, symbol: str) -> Optional[List[str]]:
        """
        Get available option expiration dates.

        Override if provider supports options.

        Returns:
            List of expiry dates (YYYY-MM-DD format), None if not supported
        """
        return None

    def get_options_chain(self, symbol: str, expiry: str) -> Optional[OptionsChainData]:
        """
        Get options chain for an expiry.

        Override if provider supports options.

        Returns:
            OptionsChainData if successful, None if not supported
        """
        return None

    def get_earnings(self, symbol: str) -> Optional[EarningsData]:
        """
        Get quarterly earnings data.

        Override if provider supports earnings data.

        Returns:
            EarningsData if successful, None if not supported
        """
        return None

    @abstractmethod
    def health_check(self) -> ProviderStatus:
        """
        Check if provider is available and healthy.

        Returns:
            ProviderStatus indicating current health
        """
        pass

    @abstractmethod
    def is_rate_limited(self) -> bool:
        """
        Check if provider is currently rate-limited.

        Returns:
            True if rate limited and should not be used
        """
        pass

    def reset_rate_limit(self) -> None:
        """Reset rate limit status after cooldown period."""
        pass

    def supports_symbol(self, symbol: str) -> bool:
        """
        Check if this provider supports the given symbol.

        Override to handle special cases (e.g., index tickers, futures).

        Returns:
            True if symbol is supported
        """
        return True

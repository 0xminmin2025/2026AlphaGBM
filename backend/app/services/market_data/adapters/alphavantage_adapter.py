"""
Alpha Vantage Data Provider Adapter

Provides access to Alpha Vantage API for:
- Real-time and historical stock quotes
- Fundamental data (financial statements, ratios)
- Technical indicators

Requires ALPHA_VANTAGE_API_KEY environment variable.
Free tier: 5 requests/minute, 500 requests/day
"""

import os
import logging
import requests
from typing import Optional, List, Dict, Any
from datetime import date, datetime, timedelta
import pandas as pd

from ..interfaces import (
    DataProviderAdapter, DataType, Market, ProviderStatus,
    QuoteData, FundamentalsData, CompanyInfo, HistoryData
)
from ..config import get_timezone_for_market
from .base import BaseAdapter, safe_float, safe_int

logger = logging.getLogger(__name__)

# Alpha Vantage base URL
AV_BASE_URL = "https://www.alphavantage.co/query"


class AlphaVantageAdapter(BaseAdapter, DataProviderAdapter):
    """
    Alpha Vantage API data provider adapter.

    Provides stock quotes, historical data, and fundamental data.
    Requires API key from environment variable ALPHA_VANTAGE_API_KEY.
    """

    def __init__(self):
        # Strict rate limiting for free tier (5 req/min)
        super().__init__(cooldown_seconds=120, max_failures=2)
        self._api_key = os.environ.get("ALPHA_VANTAGE_API_KEY", "")
        self._session = requests.Session()

    @property
    def name(self) -> str:
        return "alpha_vantage"

    @property
    def supported_data_types(self) -> List[DataType]:
        return [
            DataType.QUOTE,
            DataType.HISTORY,
            DataType.FUNDAMENTALS,
            DataType.INFO,
        ]

    @property
    def supported_markets(self) -> List[Market]:
        return [Market.US]  # Alpha Vantage primarily supports US stocks

    def supports_symbol(self, symbol: str) -> bool:
        """
        Alpha Vantage supports regular stocks but has limited support for indices/futures.

        Returns False for:
        - Index tickers (^VIX, ^GSPC, ^DJI, etc.)
        - Futures (GC=F, CL=F, etc.)
        - Forex pairs (DX-Y.NYB)
        """
        # Index tickers start with ^
        if symbol.startswith('^'):
            return False
        # Futures end with =F
        if symbol.endswith('=F'):
            return False
        # Special forex/commodity tickers
        if symbol.endswith('.NYB'):
            return False
        return True

    def _is_available(self) -> bool:
        """Check if API key is configured."""
        return bool(self._api_key)

    def _make_request(self, params: Dict[str, str]) -> Optional[Dict]:
        """Make API request with error handling."""
        if not self._is_available():
            return None

        params["apikey"] = self._api_key

        try:
            response = self._session.get(AV_BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            # Check for API errors
            if "Error Message" in data:
                logger.warning(f"[AlphaVantage] API Error: {data['Error Message']}")
                return None

            if "Note" in data:
                # Rate limit warning
                logger.warning(f"[AlphaVantage] Rate limit: {data['Note']}")
                self._handle_rate_limit()
                return None

            if "Information" in data:
                # API limit reached
                logger.warning(f"[AlphaVantage] API limit: {data['Information']}")
                self._handle_rate_limit()
                return None

            return data

        except requests.exceptions.RequestException as e:
            logger.warning(f"[AlphaVantage] Request failed: {e}")
            return None

    def get_quote(self, symbol: str) -> Optional[QuoteData]:
        """Get real-time quote using GLOBAL_QUOTE endpoint."""
        if self.is_rate_limited():
            return None

        if not self._is_available():
            return None

        try:
            data = self._make_request({
                "function": "GLOBAL_QUOTE",
                "symbol": symbol
            })

            if not data or "Global Quote" not in data:
                return None

            quote = data["Global Quote"]
            if not quote:
                return None

            current_price = safe_float(quote.get("05. price"))
            if current_price is None:
                return None

            self._handle_success()
            return QuoteData(
                symbol=symbol,
                current_price=current_price,
                previous_close=safe_float(quote.get("08. previous close")),
                open_price=safe_float(quote.get("02. open")),
                day_high=safe_float(quote.get("03. high")),
                day_low=safe_float(quote.get("04. low")),
                volume=safe_int(quote.get("06. volume")),
                timestamp=datetime.now(),
                source=self.name,
            )

        except Exception as e:
            self._handle_error(e, symbol)
            return None

    def get_history(
        self,
        symbol: str,
        period: Optional[str] = None,
        start: Optional[date] = None,
        end: Optional[date] = None
    ) -> Optional[HistoryData]:
        """Get historical OHLCV data using TIME_SERIES_DAILY endpoint."""
        if self.is_rate_limited():
            return None

        if not self._is_available():
            return None

        try:
            # Determine output size
            output_size = "full" if period in ["1y", "2y", "5y", "max"] else "compact"

            data = self._make_request({
                "function": "TIME_SERIES_DAILY",
                "symbol": symbol,
                "outputsize": output_size
            })

            if not data:
                return None

            time_series_key = "Time Series (Daily)"
            if time_series_key not in data:
                return None

            time_series = data[time_series_key]
            if not time_series:
                return None

            # Convert to DataFrame
            records = []
            for date_str, values in time_series.items():
                records.append({
                    "Date": pd.Timestamp(date_str),
                    "Open": safe_float(values.get("1. open")),
                    "High": safe_float(values.get("2. high")),
                    "Low": safe_float(values.get("3. low")),
                    "Close": safe_float(values.get("4. close")),
                    "Volume": safe_int(values.get("5. volume")),
                })

            df = pd.DataFrame(records)
            df = df.set_index("Date")
            df = df.sort_index()

            # Apply period filter
            if period:
                cutoff = self._period_to_cutoff(period)
                if cutoff:
                    df = df[df.index >= cutoff]

            # Apply date filters
            if start:
                df = df[df.index >= pd.Timestamp(start)]
            if end:
                df = df[df.index <= pd.Timestamp(end)]

            if df.empty:
                return None

            # Add timezone
            if df.index.tz is None:
                df.index = df.index.tz_localize("America/New_York")

            self._handle_success()
            return HistoryData(
                symbol=symbol,
                df=df,
                period=period,
                start_date=start,
                end_date=end,
                source=self.name,
            )

        except Exception as e:
            self._handle_error(e, symbol)
            return None

    def _period_to_cutoff(self, period: str) -> Optional[pd.Timestamp]:
        """Convert period string to cutoff date."""
        now = pd.Timestamp.now()
        period_map = {
            "1d": timedelta(days=1),
            "5d": timedelta(days=5),
            "1mo": timedelta(days=30),
            "3mo": timedelta(days=90),
            "6mo": timedelta(days=180),
            "1y": timedelta(days=365),
            "2y": timedelta(days=730),
            "5y": timedelta(days=1825),
        }
        delta = period_map.get(period)
        if delta:
            return now - delta
        return None

    def get_info(self, symbol: str) -> Optional[CompanyInfo]:
        """Get company overview information."""
        if self.is_rate_limited():
            return None

        if not self._is_available():
            return None

        try:
            data = self._make_request({
                "function": "OVERVIEW",
                "symbol": symbol
            })

            if not data or "Symbol" not in data:
                return None

            self._handle_success()
            return CompanyInfo(
                symbol=symbol,
                name=data.get("Name", symbol),
                sector=data.get("Sector"),
                industry=data.get("Industry"),
                country=data.get("Country"),
                description=data.get("Description"),
                employees=safe_int(data.get("FullTimeEmployees")),
                website=None,  # Not provided by Alpha Vantage
                currency=data.get("Currency", "USD"),
                exchange=data.get("Exchange"),
                source=self.name,
            )

        except Exception as e:
            self._handle_error(e, symbol)
            return None

    def get_fundamentals(self, symbol: str) -> Optional[FundamentalsData]:
        """Get fundamental data from company overview."""
        if self.is_rate_limited():
            return None

        if not self._is_available():
            return None

        try:
            data = self._make_request({
                "function": "OVERVIEW",
                "symbol": symbol
            })

            if not data or "Symbol" not in data:
                return None

            self._handle_success()
            return FundamentalsData(
                symbol=symbol,
                pe_ratio=safe_float(data.get("TrailingPE")),
                forward_pe=safe_float(data.get("ForwardPE")),
                pb_ratio=safe_float(data.get("PriceToBookRatio")),
                ps_ratio=safe_float(data.get("PriceToSalesRatioTTM")),
                peg_ratio=safe_float(data.get("PEGRatio")),
                ev_ebitda=safe_float(data.get("EVToEBITDA")),
                profit_margin=safe_float(data.get("ProfitMargin")),
                operating_margin=safe_float(data.get("OperatingMarginTTM")),
                roe=safe_float(data.get("ReturnOnEquityTTM")),
                roa=safe_float(data.get("ReturnOnAssetsTTM")),
                revenue_growth=safe_float(data.get("QuarterlyRevenueGrowthYOY")),
                earnings_growth=safe_float(data.get("QuarterlyEarningsGrowthYOY")),
                beta=safe_float(data.get("Beta")),
                dividend_yield=safe_float(data.get("DividendYield")),
                eps_trailing=safe_float(data.get("EPS")),
                eps_forward=None,  # Not directly available
                target_high=safe_float(data.get("AnalystTargetPrice")),
                target_low=None,
                target_mean=safe_float(data.get("AnalystTargetPrice")),
                recommendation=None,
                source=self.name,
            )

        except Exception as e:
            self._handle_error(e, symbol)
            return None

    def get_options_expirations(self, symbol: str) -> Optional[List[str]]:
        """Alpha Vantage doesn't provide options data."""
        return None

    def get_options_chain(self, symbol: str, expiry: str) -> None:
        """Alpha Vantage doesn't provide options data."""
        return None

    def health_check(self) -> ProviderStatus:
        """Check provider health."""
        if not self._is_available():
            return ProviderStatus.UNAVAILABLE
        return super().health_check()


# Test the adapter if run directly
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    adapter = AlphaVantageAdapter()

    print("Testing Alpha Vantage Adapter...")
    print(f"API Key configured: {adapter._is_available()}")

    if adapter._is_available():
        quote = adapter.get_quote("AAPL")
        if quote:
            print(f"Quote: ${quote.current_price}")
        else:
            print("Quote failed")
    else:
        print("Set ALPHA_VANTAGE_API_KEY environment variable to test")

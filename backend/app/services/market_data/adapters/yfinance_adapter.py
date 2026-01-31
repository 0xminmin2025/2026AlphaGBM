"""
yfinance Data Provider Adapter

Primary data provider for US and HK stocks. Supports:
- Real-time quotes
- Historical OHLCV data
- Company info and fundamentals
- Options chains
- Earnings data
- Macro/index data
"""

import logging
from typing import Optional, List
from datetime import date
import pandas as pd

from ..interfaces import (
    DataProviderAdapter, DataType, Market, ProviderStatus,
    QuoteData, FundamentalsData, CompanyInfo, HistoryData,
    OptionsChainData, EarningsData
)
from ..config import is_macro_ticker, get_timezone_for_market, get_market_for_symbol
from .base import BaseAdapter, safe_float, safe_int, safe_str

logger = logging.getLogger(__name__)

# Import yfinance
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    yf = None
    YFINANCE_AVAILABLE = False


class YFinanceAdapter(BaseAdapter, DataProviderAdapter):
    """
    yfinance data provider adapter.

    Primary provider for stock data with comprehensive coverage
    of US and HK markets.
    """

    def __init__(self):
        super().__init__(cooldown_seconds=60, max_failures=3)

    @property
    def name(self) -> str:
        return "yfinance"

    @property
    def supported_data_types(self) -> List[DataType]:
        return [
            DataType.QUOTE,
            DataType.HISTORY,
            DataType.INFO,
            DataType.FUNDAMENTALS,
            DataType.OPTIONS_CHAIN,
            DataType.OPTIONS_EXPIRATIONS,
            DataType.EARNINGS,
            DataType.MACRO,
        ]

    @property
    def supported_markets(self) -> List[Market]:
        return [Market.US, Market.HK]

    def supports_symbol(self, symbol: str) -> bool:
        """yfinance supports most symbols including macro tickers."""
        return True

    def get_quote(self, symbol: str) -> Optional[QuoteData]:
        """Get real-time quote."""
        if not YFINANCE_AVAILABLE:
            return None

        if self.is_rate_limited():
            return None

        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            if not info or len(info) < 5:
                return None

            current_price = safe_float(info.get('currentPrice')) or safe_float(info.get('regularMarketPrice'))
            if current_price is None:
                # Try to get from history
                hist = ticker.history(period="1d")
                if hist is not None and not hist.empty:
                    current_price = safe_float(hist['Close'].iloc[-1])

            if current_price is None:
                return None

            self._handle_success()
            return QuoteData(
                symbol=symbol,
                current_price=current_price,
                previous_close=safe_float(info.get('previousClose')),
                open_price=safe_float(info.get('open')) or safe_float(info.get('regularMarketOpen')),
                day_high=safe_float(info.get('dayHigh')) or safe_float(info.get('regularMarketDayHigh')),
                day_low=safe_float(info.get('dayLow')) or safe_float(info.get('regularMarketDayLow')),
                volume=safe_int(info.get('volume')) or safe_int(info.get('regularMarketVolume')),
                market_cap=safe_float(info.get('marketCap')),
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
        """Get historical OHLCV data."""
        if not YFINANCE_AVAILABLE:
            return None

        if self.is_rate_limited():
            return None

        try:
            ticker = yf.Ticker(symbol)

            kwargs = {}
            if period:
                kwargs['period'] = period
            if start:
                kwargs['start'] = start
            if end:
                kwargs['end'] = end

            # Default to 1 month if nothing specified
            if not kwargs:
                kwargs['period'] = '1mo'

            hist = ticker.history(**kwargs)

            if hist is None or hist.empty:
                return None

            # Ensure proper timezone
            market = get_market_for_symbol(symbol)
            tz = get_timezone_for_market(market)
            if hist.index.tz is None:
                hist.index = hist.index.tz_localize(tz)
            elif str(hist.index.tz) != tz:
                hist.index = hist.index.tz_convert(tz)

            self._handle_success()
            return HistoryData(
                symbol=symbol,
                df=hist,
                period=period,
                start_date=start,
                end_date=end,
                source=self.name,
            )
        except Exception as e:
            self._handle_error(e, symbol)
            return None

    def get_info(self, symbol: str) -> Optional[CompanyInfo]:
        """Get company info."""
        if not YFINANCE_AVAILABLE:
            return None

        if self.is_rate_limited():
            return None

        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            if not info or len(info) < 5:
                return None

            self._handle_success()
            return CompanyInfo(
                symbol=symbol,
                name=safe_str(info.get('shortName')) or safe_str(info.get('longName')) or symbol,
                sector=safe_str(info.get('sector')),
                industry=safe_str(info.get('industry')),
                country=safe_str(info.get('country')),
                description=safe_str(info.get('longBusinessSummary')),
                employees=safe_int(info.get('fullTimeEmployees')),
                website=safe_str(info.get('website')),
                currency=safe_str(info.get('currency')),
                exchange=safe_str(info.get('exchange')),
                source=self.name,
            )
        except Exception as e:
            self._handle_error(e, symbol)
            return None

    def get_fundamentals(self, symbol: str) -> Optional[FundamentalsData]:
        """Get fundamental metrics."""
        if not YFINANCE_AVAILABLE:
            return None

        if self.is_rate_limited():
            return None

        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            if not info or len(info) < 5:
                return None

            self._handle_success()
            return FundamentalsData(
                symbol=symbol,
                pe_ratio=safe_float(info.get('trailingPE')),
                forward_pe=safe_float(info.get('forwardPE')),
                pb_ratio=safe_float(info.get('priceToBook')),
                ps_ratio=safe_float(info.get('priceToSalesTrailing12Months')),
                peg_ratio=safe_float(info.get('pegRatio')),
                ev_ebitda=safe_float(info.get('enterpriseToEbitda')),
                profit_margin=safe_float(info.get('profitMargins')),
                operating_margin=safe_float(info.get('operatingMargins')),
                roe=safe_float(info.get('returnOnEquity')),
                roa=safe_float(info.get('returnOnAssets')),
                revenue_growth=safe_float(info.get('revenueGrowth')),
                earnings_growth=safe_float(info.get('earningsGrowth')),
                beta=safe_float(info.get('beta')),
                dividend_yield=safe_float(info.get('dividendYield')),
                eps_trailing=safe_float(info.get('trailingEps')),
                eps_forward=safe_float(info.get('forwardEps')),
                target_high=safe_float(info.get('targetHighPrice')),
                target_low=safe_float(info.get('targetLowPrice')),
                target_mean=safe_float(info.get('targetMeanPrice')),
                recommendation=safe_str(info.get('recommendationKey')),
                source=self.name,
            )
        except Exception as e:
            self._handle_error(e, symbol)
            return None

    def get_options_expirations(self, symbol: str) -> Optional[List[str]]:
        """Get available option expiration dates."""
        if not YFINANCE_AVAILABLE:
            return None

        if self.is_rate_limited():
            return None

        # Macro tickers don't have options
        if is_macro_ticker(symbol):
            return None

        try:
            ticker = yf.Ticker(symbol)
            expirations = ticker.options

            if not expirations:
                return None

            self._handle_success()
            return list(expirations)
        except Exception as e:
            self._handle_error(e, symbol)
            return None

    def get_options_chain(self, symbol: str, expiry: str) -> Optional[OptionsChainData]:
        """Get options chain for an expiry."""
        if not YFINANCE_AVAILABLE:
            return None

        if self.is_rate_limited():
            return None

        # Macro tickers don't have options
        if is_macro_ticker(symbol):
            return None

        try:
            ticker = yf.Ticker(symbol)

            # Get current price
            info = ticker.info
            underlying_price = safe_float(info.get('currentPrice')) or safe_float(info.get('regularMarketPrice'))
            if underlying_price is None:
                hist = ticker.history(period="1d")
                if hist is not None and not hist.empty:
                    underlying_price = safe_float(hist['Close'].iloc[-1])

            if underlying_price is None:
                return None

            # Get options chain
            chain = ticker.option_chain(expiry)

            if chain is None:
                return None

            calls = chain.calls if hasattr(chain, 'calls') else pd.DataFrame()
            puts = chain.puts if hasattr(chain, 'puts') else pd.DataFrame()

            if calls.empty and puts.empty:
                return None

            self._handle_success()
            return OptionsChainData(
                symbol=symbol,
                expiry_date=expiry,
                underlying_price=underlying_price,
                calls=calls,
                puts=puts,
                source=self.name,
            )
        except Exception as e:
            self._handle_error(e, symbol)
            return None

    def get_earnings(self, symbol: str) -> Optional[EarningsData]:
        """Get quarterly earnings data."""
        if not YFINANCE_AVAILABLE:
            return None

        if self.is_rate_limited():
            return None

        try:
            ticker = yf.Ticker(symbol)
            earnings = ticker.quarterly_earnings

            if earnings is None or earnings.empty:
                return None

            self._handle_success()
            return EarningsData(
                symbol=symbol,
                quarterly_earnings=earnings,
                source=self.name,
            )
        except Exception as e:
            self._handle_error(e, symbol)
            return None

    def health_check(self) -> ProviderStatus:
        """Check provider health."""
        if not YFINANCE_AVAILABLE:
            return ProviderStatus.UNAVAILABLE
        return super().health_check()

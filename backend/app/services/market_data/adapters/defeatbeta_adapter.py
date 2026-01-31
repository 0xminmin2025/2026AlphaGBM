"""
defeatbeta-api Data Provider Adapter

Fallback data provider using local DuckDB + HuggingFace datasets.
Provides stock data for US markets without rate limiting concerns.

Does NOT support:
- Options data
- Macro/index tickers (^VIX, ^GSPC, etc.)
- Real-time quotes (data may be delayed)
"""

import logging
from typing import Optional, List
from datetime import date, datetime, timedelta
import pandas as pd
import numpy as np

from ..interfaces import (
    DataProviderAdapter, DataType, Market, ProviderStatus,
    QuoteData, FundamentalsData, CompanyInfo, HistoryData, EarningsData
)
from ..config import is_macro_ticker, get_timezone_for_market
from .base import BaseAdapter, safe_float, safe_int, safe_str

logger = logging.getLogger(__name__)

# Import defeatbeta-api
try:
    from defeatbeta_api.data.ticker import Ticker as DBTicker
    DEFEATBETA_AVAILABLE = True
except ImportError:
    DBTicker = None
    DEFEATBETA_AVAILABLE = False


class DefeatBetaAdapter(BaseAdapter, DataProviderAdapter):
    """
    defeatbeta-api data provider adapter.

    Uses local DuckDB database with data from HuggingFace datasets.
    No rate limiting, but data may be delayed (not real-time).
    Only supports US stocks (no indices, futures, or options).
    """

    def __init__(self):
        super().__init__(cooldown_seconds=30, max_failures=5)

    @property
    def name(self) -> str:
        return "defeatbeta"

    @property
    def supported_data_types(self) -> List[DataType]:
        return [
            DataType.QUOTE,
            DataType.HISTORY,
            DataType.INFO,
            DataType.FUNDAMENTALS,
            DataType.EARNINGS,
        ]

    @property
    def supported_markets(self) -> List[Market]:
        return [Market.US]  # Only US stocks

    def supports_symbol(self, symbol: str) -> bool:
        """defeatbeta does not support macro/index tickers."""
        if is_macro_ticker(symbol):
            return False
        # Check for HK/CN suffixes
        if symbol.endswith('.HK') or symbol.endswith('.SS') or symbol.endswith('.SZ'):
            return False
        return True

    def _get_ticker(self, symbol: str) -> Optional[object]:
        """Get defeatbeta ticker object."""
        if not DEFEATBETA_AVAILABLE:
            return None
        if not self.supports_symbol(symbol):
            return None
        try:
            return DBTicker(symbol)
        except Exception as e:
            logger.debug(f"[defeatbeta] Cannot create ticker for {symbol}: {e}")
            return None

    def get_quote(self, symbol: str) -> Optional[QuoteData]:
        """Get quote data (may be delayed, not real-time)."""
        if not self.supports_symbol(symbol):
            return None

        if self.is_rate_limited():
            return None

        try:
            db = self._get_ticker(symbol)
            if db is None:
                return None

            # Get price data
            price_df = db.price()
            if price_df is None or price_df.empty:
                return None

            # Get latest row
            latest = price_df.iloc[-1]
            current_price = safe_float(latest.get('close'))

            if current_price is None:
                return None

            # Get previous close if we have enough data
            previous_close = None
            if len(price_df) >= 2:
                previous_close = safe_float(price_df.iloc[-2].get('close'))

            # Try to get market cap from summary
            market_cap = None
            try:
                summary_df = db.summary()
                if summary_df is not None and not summary_df.empty:
                    market_cap = safe_float(summary_df.iloc[-1].get('market_cap'))
            except Exception:
                pass

            self._handle_success()
            return QuoteData(
                symbol=symbol,
                current_price=current_price,
                previous_close=previous_close,
                open_price=safe_float(latest.get('open')),
                day_high=safe_float(latest.get('high')),
                day_low=safe_float(latest.get('low')),
                volume=safe_int(latest.get('volume')),
                market_cap=market_cap,
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
        if not self.supports_symbol(symbol):
            return None

        if self.is_rate_limited():
            return None

        try:
            db = self._get_ticker(symbol)
            if db is None:
                return None

            price_df = db.price()
            if price_df is None or price_df.empty:
                return None

            # Convert to DataFrame with proper structure
            df = price_df.copy()

            # Ensure date column exists and is datetime
            if 'report_date' in df.columns:
                df['Date'] = pd.to_datetime(df['report_date'])
            elif 'date' in df.columns:
                df['Date'] = pd.to_datetime(df['date'])
            else:
                return None

            df = df.set_index('Date')

            # Rename columns to match yfinance format
            column_map = {
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume',
            }
            df = df.rename(columns=column_map)

            # Filter columns
            columns_to_keep = ['Open', 'High', 'Low', 'Close', 'Volume']
            df = df[[c for c in columns_to_keep if c in df.columns]]

            # Convert to numeric
            for col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            # Sort by date
            df = df.sort_index()

            # Apply date filters
            if start:
                df = df[df.index >= pd.Timestamp(start)]
            if end:
                df = df[df.index <= pd.Timestamp(end)]

            # Apply period filter
            if period and not start and not end:
                period_days = self._period_to_days(period)
                cutoff = datetime.now() - timedelta(days=period_days)
                df = df[df.index >= pd.Timestamp(cutoff)]

            if df.empty:
                return None

            # Add timezone
            tz = get_timezone_for_market(Market.US)
            if df.index.tz is None:
                df.index = df.index.tz_localize(tz)

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

    def _period_to_days(self, period: str) -> int:
        """Convert period string to approximate number of days."""
        period_map = {
            '1d': 1,
            '5d': 5,
            '1wk': 7,
            '1mo': 30,
            '3mo': 90,
            '6mo': 180,
            '1y': 365,
            '2y': 730,
            '5y': 1825,
            '10y': 3650,
            'max': 7300,
        }
        return period_map.get(period, 30)

    def get_info(self, symbol: str) -> Optional[CompanyInfo]:
        """Get company info."""
        if not self.supports_symbol(symbol):
            return None

        if self.is_rate_limited():
            return None

        try:
            db = self._get_ticker(symbol)
            if db is None:
                return None

            # Try info() first
            info_df = db.info()
            if info_df is None or info_df.empty:
                return None

            latest = info_df.iloc[-1]

            self._handle_success()
            return CompanyInfo(
                symbol=symbol,
                name=safe_str(latest.get('short_name')) or safe_str(latest.get('long_name')) or symbol,
                sector=safe_str(latest.get('sector')),
                industry=safe_str(latest.get('industry')),
                country=safe_str(latest.get('country')),
                description=safe_str(latest.get('long_business_summary')),
                employees=safe_int(latest.get('full_time_employees')),
                website=safe_str(latest.get('website')),
                currency=safe_str(latest.get('currency')),
                exchange=safe_str(latest.get('exchange')),
                source=self.name,
            )
        except Exception as e:
            self._handle_error(e, symbol)
            return None

    def get_fundamentals(self, symbol: str) -> Optional[FundamentalsData]:
        """Get fundamental metrics."""
        if not self.supports_symbol(symbol):
            return None

        if self.is_rate_limited():
            return None

        try:
            db = self._get_ticker(symbol)
            if db is None:
                return None

            fundamentals = FundamentalsData(symbol=symbol, source=self.name)

            # Get summary data (PE, market cap, beta, etc.)
            try:
                summary_df = db.summary()
                if summary_df is not None and not summary_df.empty:
                    latest = summary_df.iloc[-1]
                    fundamentals.pe_ratio = safe_float(latest.get('trailing_pe'))
                    fundamentals.forward_pe = safe_float(latest.get('forward_pe'))
                    fundamentals.beta = safe_float(latest.get('beta'))
                    fundamentals.eps_trailing = safe_float(latest.get('tailing_eps'))  # Note: typo in defeatbeta
                    fundamentals.eps_forward = safe_float(latest.get('forward_eps'))
                    fundamentals.peg_ratio = safe_float(latest.get('peg_ratio'))
            except Exception as e:
                logger.debug(f"[defeatbeta] summary() failed for {symbol}: {e}")

            # Get PB ratio
            try:
                pb_df = db.pb_ratio()
                if pb_df is not None and not pb_df.empty:
                    fundamentals.pb_ratio = safe_float(pb_df.iloc[-1].get('pb_ratio'))
            except Exception:
                pass

            # Get PS ratio
            try:
                ps_df = db.ps_ratio()
                if ps_df is not None and not ps_df.empty:
                    fundamentals.ps_ratio = safe_float(ps_df.iloc[-1].get('ps_ratio'))
            except Exception:
                pass

            # Get profit margins
            try:
                margin_df = db.quarterly_net_margin()
                if margin_df is not None and not margin_df.empty:
                    fundamentals.profit_margin = safe_float(margin_df.iloc[-1].get('net_margin'))
            except Exception:
                pass

            # Get operating margins
            try:
                op_margin_df = db.quarterly_operating_margin()
                if op_margin_df is not None and not op_margin_df.empty:
                    fundamentals.operating_margin = safe_float(op_margin_df.iloc[-1].get('operating_margin'))
            except Exception:
                pass

            # Get ROE
            try:
                roe_df = db.roe()
                if roe_df is not None and not roe_df.empty:
                    fundamentals.roe = safe_float(roe_df.iloc[-1].get('roe'))
            except Exception:
                pass

            # Get ROA
            try:
                roa_df = db.roa()
                if roa_df is not None and not roa_df.empty:
                    fundamentals.roa = safe_float(roa_df.iloc[-1].get('roa'))
            except Exception:
                pass

            # Get revenue growth
            try:
                growth_df = db.quarterly_revenue_yoy_growth()
                if growth_df is not None and not growth_df.empty:
                    fundamentals.revenue_growth = safe_float(growth_df.iloc[-1].get('revenue_yoy_growth'))
            except Exception:
                pass

            # Get dividend yield
            try:
                div_df = db.dividends()
                if div_df is not None and not div_df.empty:
                    fundamentals.dividend_yield = safe_float(div_df.iloc[-1].get('dividend_yield'))
            except Exception:
                pass

            self._handle_success()
            return fundamentals
        except Exception as e:
            self._handle_error(e, symbol)
            return None

    def get_earnings(self, symbol: str) -> Optional[EarningsData]:
        """Get quarterly earnings data."""
        if not self.supports_symbol(symbol):
            return None

        if self.is_rate_limited():
            return None

        try:
            db = self._get_ticker(symbol)
            if db is None:
                return None

            earnings_df = db.earnings()
            if earnings_df is None or earnings_df.empty:
                return None

            # Transform to match yfinance format
            df = earnings_df.copy()

            # Rename columns
            if 'eps_actual' in df.columns:
                df['Earnings'] = pd.to_numeric(df['eps_actual'], errors='coerce')

            # Set index to quarter date if available
            if 'quarter_date' in df.columns:
                df['Date'] = pd.to_datetime(df['quarter_date'])
                df = df.set_index('Date')
            elif 'quarter_name' in df.columns:
                # Try to parse quarter name like "Q1 2024"
                df = df.set_index('quarter_name')

            # Keep only relevant columns
            columns_to_keep = ['Earnings']
            if 'Revenue' in df.columns:
                columns_to_keep.append('Revenue')
            df = df[[c for c in columns_to_keep if c in df.columns]]

            self._handle_success()
            return EarningsData(
                symbol=symbol,
                quarterly_earnings=df,
                source=self.name,
            )
        except Exception as e:
            self._handle_error(e, symbol)
            return None

    def health_check(self) -> ProviderStatus:
        """Check provider health."""
        if not DEFEATBETA_AVAILABLE:
            return ProviderStatus.UNAVAILABLE
        return super().health_check()

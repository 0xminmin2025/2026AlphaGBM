"""
Unified Data Provider with multi-provider support and automatic failover.

This module provides a drop-in replacement for yf.Ticker() that uses
the centralized MarketDataService for all data access. All data fetches
are automatically tracked in the metrics dashboard.

Usage:
    # Instead of: stock = yf.Ticker('AAPL')
    # Use:        stock = DataProvider('AAPL')
    #
    # Same interface: stock.info, stock.history(), stock.quarterly_earnings, etc.

NOTE: This is a backward-compatible facade over MarketDataService.
      For new code, prefer using market_data_service directly:

      from app.services.market_data import market_data_service
      quote = market_data_service.get_quote("AAPL")
      history = market_data_service.get_history("AAPL", period="1mo")
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional
from collections import namedtuple

# Import market data service (singleton)
from .market_data import market_data_service

logger = logging.getLogger(__name__)


class DataProvider:
    """
    Drop-in replacement for yf.Ticker using the centralized MarketDataService.

    All data access goes through market_data_service which provides:
    - Multi-provider support (yfinance, Tiger, defeatbeta, Tushare, Alpha Vantage)
    - Automatic failover between providers
    - Request deduplication
    - Caching
    - Metrics tracking

    Exposes the same interface as yf.Ticker:
        - .info (property) -> dict
        - .history(period=, start=, end=, timeout=) -> DataFrame
        - .quarterly_earnings (property) -> DataFrame
        - .options (property) -> tuple
        - .option_chain(date) -> OptionChain
        - .fast_info (property)
        - .calendar (property)
        - .news (property)
        - .get_margin_rate() -> float

    For new code, prefer using market_data_service directly:
        from app.services.market_data import market_data_service
        quote = market_data_service.get_quote("AAPL")
    """

    def __init__(self, ticker: str):
        self.ticker = ticker
        self._info_cache = None

    # ──────────────────────────────────────────────
    # .info property
    # ──────────────────────────────────────────────
    @property
    def info(self) -> dict:
        """
        Returns a dict compatible with yfinance's stock.info.
        Uses MarketDataService with automatic multi-provider failover.
        """
        if self._info_cache is not None:
            return self._info_cache

        try:
            result = market_data_service.get_ticker_data(self.ticker)
            # get_ticker_data() returns yfinance-compatible keys (regularMarketPrice, currentPrice)
            if result and (result.get('regularMarketPrice') is not None or result.get('currentPrice') is not None):
                self._info_cache = result
                return self._info_cache
        except Exception as e:
            logger.warning(f"[DataProvider] market_data_service failed for {self.ticker}: {e}")

        return {'symbol': self.ticker}

    # ──────────────────────────────────────────────
    # .history() method
    # ──────────────────────────────────────────────
    def history(self, period=None, start=None, end=None, timeout=30) -> pd.DataFrame:
        """
        Returns OHLCV DataFrame in yfinance format.
        Uses MarketDataService with automatic multi-provider failover.
        """
        try:
            # Convert start/end to date objects if needed
            start_date = None
            end_date = None
            if start is not None:
                if isinstance(start, str):
                    start_date = pd.Timestamp(start).date()
                elif hasattr(start, 'date'):
                    start_date = start.date() if callable(getattr(start, 'date', None)) else start
                else:
                    start_date = start
            if end is not None:
                if isinstance(end, str):
                    end_date = pd.Timestamp(end).date()
                elif hasattr(end, 'date'):
                    end_date = end.date() if callable(getattr(end, 'date', None)) else end
                else:
                    end_date = end

            result = market_data_service.get_history_df(
                self.ticker,
                period=period,
                start=start_date,
                end=end_date
            )
            if result is not None and not result.empty:
                return result
        except Exception as e:
            logger.warning(f"[DataProvider] market_data_service history failed for {self.ticker}: {e}")

        return pd.DataFrame()

    # ──────────────────────────────────────────────
    # .quarterly_earnings property
    # ──────────────────────────────────────────────
    @property
    def quarterly_earnings(self) -> pd.DataFrame:
        """
        Returns quarterly earnings DataFrame.
        yfinance format: index=date, columns=['Revenue', 'Earnings']
        """
        try:
            earnings = market_data_service.get_earnings(self.ticker)
            if earnings and not earnings.empty:
                return earnings.quarterly_earnings
        except Exception as e:
            logger.warning(f"[DataProvider] market_data_service earnings failed for {self.ticker}: {e}")

        return pd.DataFrame()

    # ──────────────────────────────────────────────
    # .options property
    # ──────────────────────────────────────────────
    @property
    def options(self):
        """Returns available option expiration dates."""
        try:
            expirations = market_data_service.get_options_expirations(self.ticker)
            if expirations:
                return tuple(expirations)
        except Exception as e:
            logger.warning(f"[DataProvider] market_data_service options failed for {self.ticker}: {e}")

        return ()

    # ──────────────────────────────────────────────
    # .option_chain() method
    # ──────────────────────────────────────────────
    def option_chain(self, date):
        """Returns option chain for a specific date."""
        try:
            chain = market_data_service.get_options_chain(self.ticker, date)
            if chain and not chain.empty:
                # Convert to yfinance-compatible format
                OptionChain = namedtuple('OptionChain', ['calls', 'puts'])
                return OptionChain(calls=chain.calls, puts=chain.puts)
        except Exception as e:
            logger.warning(f"[DataProvider] market_data_service option_chain failed for {self.ticker}: {e}")

        return None

    # ──────────────────────────────────────────────
    # .fast_info property
    # ──────────────────────────────────────────────
    @property
    def fast_info(self):
        """
        Returns fast_info-like dict using market_data_service.
        Returns subset of info for quick access.
        """
        try:
            quote = market_data_service.get_quote(self.ticker)
            if quote:
                return {
                    'lastPrice': quote.current_price,
                    'previousClose': quote.previous_close,
                    'open': quote.open_price,
                    'dayHigh': quote.day_high,
                    'dayLow': quote.day_low,
                    'volume': quote.volume,
                    'marketCap': quote.market_cap,
                }
        except Exception:
            pass
        return None

    # ──────────────────────────────────────────────
    # .calendar property
    # ──────────────────────────────────────────────
    @property
    def calendar(self):
        """
        Returns calendar data (earnings dates, dividends, etc.)
        Not currently supported by market_data_service.
        """
        # Calendar data is not supported in market_data_service
        # Returns None to indicate no data available
        return None

    # ──────────────────────────────────────────────
    # .news property
    # ──────────────────────────────────────────────
    @property
    def news(self):
        """
        Returns news data for the ticker.
        Not currently supported by market_data_service.
        """
        # News is not supported in market_data_service
        return []

    # ──────────────────────────────────────────────
    # .get_margin_rate() method
    # ──────────────────────────────────────────────
    def get_margin_rate(self) -> Optional[float]:
        """
        Get margin requirement rate for this symbol.

        Returns:
            Margin rate as a decimal (e.g., 0.25 for 25% margin requirement),
            or None if unavailable.
        """
        try:
            return market_data_service.get_margin_rate(self.ticker)
        except Exception as e:
            logger.warning(f"[DataProvider] get_margin_rate failed for {self.ticker}: {e}")
            return None


def data_provider_download(ticker: str, period: str = '6mo', progress: bool = False) -> pd.DataFrame:
    """
    Drop-in replacement for yf.download() with multi-provider failover.
    Returns a DataFrame with OHLCV data.
    """
    try:
        result = market_data_service.get_history_df(ticker, period=period)
        if result is not None and not result.empty:
            return result
    except Exception as e:
        logger.warning(f"[DataProvider] market_data_service download failed for {ticker}: {e}")

    return pd.DataFrame()

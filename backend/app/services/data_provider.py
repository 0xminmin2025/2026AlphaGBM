"""
Unified Data Provider with yfinance-first, defeatbeta-api fallback.

This module provides a drop-in replacement for yf.Ticker() that automatically
falls back to defeatbeta-api when yfinance hits rate limits.

Usage:
    # Instead of: stock = yf.Ticker('AAPL')
    # Use:        stock = DataProvider('AAPL')
    #
    # Same interface: stock.info, stock.history(), stock.quarterly_earnings, etc.
"""

import logging
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import Optional

import yfinance as yf

# Import yfinance rate limit exception
try:
    from yfinance.exceptions import YFRateLimitError
except ImportError:
    YFRateLimitError = type('YFRateLimitError', (Exception,), {})

# Import defeatbeta-api (optional — gracefully degrade if unavailable)
try:
    from defeatbeta_api.data.ticker import Ticker as DBTicker
    DEFEATBETA_AVAILABLE = True
except ImportError:
    DBTicker = None
    DEFEATBETA_AVAILABLE = False

logger = logging.getLogger(__name__)


def _is_rate_limit_error(e: Exception) -> bool:
    """Check if an exception is a yfinance rate limit error or related network issue."""
    import json
    error_msg = str(e)
    error_type = type(e).__name__

    # Direct rate limit errors
    if isinstance(e, YFRateLimitError) or error_type == 'YFRateLimitError':
        return True

    # JSONDecodeError often happens when yfinance gets rate limited (empty response)
    if isinstance(e, json.JSONDecodeError) or error_type == 'JSONDecodeError':
        return True

    # String-based detection
    rate_limit_indicators = [
        'Too Many Requests',
        'Rate limited',
        '429',
        'Expecting value: line 1 column 1',  # Empty JSON response
        'Max retries exceeded',
        'SSLError',
        'Connection refused',
    ]
    return any(indicator in error_msg for indicator in rate_limit_indicators)


def _is_index_or_macro_ticker(ticker: str) -> bool:
    """Check if a ticker is an index/futures/macro symbol that defeatbeta can't handle."""
    macro_prefixes = ('^', )
    macro_suffixes = ('=F', '.NYB')
    return (
        ticker.startswith(macro_prefixes) or
        ticker.endswith(macro_suffixes) or
        ticker in ('DX-Y.NYB', 'SPY', 'QQQ', 'IWM')
    )


class DataProvider:
    """
    Drop-in replacement for yf.Ticker with automatic defeatbeta fallback.

    Exposes the same interface as yf.Ticker:
        - .info (property) -> dict
        - .history(period=, start=, end=, timeout=) -> DataFrame
        - .quarterly_earnings (property) -> DataFrame
        - .options (property) -> tuple
        - .option_chain(date) -> OptionChain
        - .fast_info (property)
        - .calendar (property)
    """

    def __init__(self, ticker: str):
        self.ticker = ticker
        self._yf_ticker = None
        self._db_ticker = None
        self._yf_failed = False  # Set to True after rate limit hit
        self._db_cache = {}  # Cache defeatbeta results within this instance

    def _get_yf(self):
        """Lazy-init yfinance ticker."""
        if self._yf_ticker is None:
            self._yf_ticker = yf.Ticker(self.ticker)
        return self._yf_ticker

    def _get_db(self):
        """Lazy-init defeatbeta ticker."""
        if self._db_ticker is None:
            if not DEFEATBETA_AVAILABLE:
                raise ImportError("defeatbeta-api is not installed")
            if _is_index_or_macro_ticker(self.ticker):
                raise ValueError(f"defeatbeta does not support index/macro ticker: {self.ticker}")
            self._db_ticker = DBTicker(self.ticker)
        return self._db_ticker

    # ──────────────────────────────────────────────
    # .info property
    # ──────────────────────────────────────────────
    @property
    def info(self) -> dict:
        """
        Returns a dict compatible with yfinance's stock.info.
        Tries yfinance first; falls back to defeatbeta on rate limit.
        """
        if not self._yf_failed:
            try:
                result = self._get_yf().info
                # Check if result is valid (yfinance returns empty/minimal dict on rate limit)
                if result and len(result) >= 5 and result.get('regularMarketPrice') is not None:
                    return result
                # If result is empty or missing key fields, treat as rate limit
                logger.warning(f"[DataProvider] yfinance returned empty/invalid info for {self.ticker}, falling back to defeatbeta")
                self._yf_failed = True
            except Exception as e:
                if _is_rate_limit_error(e):
                    logger.warning(f"[DataProvider] yfinance rate limited for {self.ticker}.info, falling back to defeatbeta")
                    self._yf_failed = True
                else:
                    # For any other exception, also try defeatbeta fallback
                    logger.warning(f"[DataProvider] yfinance error for {self.ticker}.info ({e}), falling back to defeatbeta")
                    self._yf_failed = True

        # Fallback to defeatbeta
        if _is_index_or_macro_ticker(self.ticker):
            return {}

        return self._build_info_from_defeatbeta()

    def _build_info_from_defeatbeta(self) -> dict:
        """Build a yfinance-compatible info dict from defeatbeta data sources."""
        if 'info' in self._db_cache:
            return self._db_cache['info']

        info = {}
        db = self._get_db()

        # --- Price data from price() ---
        try:
            price_df = db.price()
            if price_df is not None and len(price_df) > 0:
                latest = price_df.iloc[-1]
                info['regularMarketPrice'] = float(latest['close'])
                info['currentPrice'] = float(latest['close'])
                info['regularMarketOpen'] = float(latest['open'])
                info['regularMarketDayHigh'] = float(latest['high'])
                info['regularMarketDayLow'] = float(latest['low'])
                info['regularMarketVolume'] = int(latest['volume'])

                if len(price_df) >= 2:
                    prev = price_df.iloc[-2]
                    info['regularMarketPreviousClose'] = float(prev['close'])
                    info['previousClose'] = float(prev['close'])

                # 52-week high/low from ~252 trading days
                recent_252 = price_df.tail(252)
                info['fiftyTwoWeekHigh'] = float(recent_252['high'].max())
                info['fiftyTwoWeekLow'] = float(recent_252['low'].min())

                # Average volume
                recent_30 = price_df.tail(30)
                info['averageVolume'] = int(recent_30['volume'].mean())
                recent_10 = price_df.tail(10)
                info['averageVolume10days'] = int(recent_10['volume'].mean())
        except Exception as e:
            logger.warning(f"[DataProvider] defeatbeta price() failed for {self.ticker}: {e}")

        # --- Summary data (PE, beta, EPS, market cap, etc.) ---
        try:
            summary = db.summary()
            if summary is not None and len(summary) > 0:
                row = summary.iloc[0]
                info['marketCap'] = self._safe_float(row.get('market_cap'))
                info['enterpriseValue'] = self._safe_float(row.get('enterprise_value'))
                info['sharesOutstanding'] = self._safe_float(row.get('shares_outstanding'))
                info['beta'] = self._safe_float(row.get('beta'))
                info['trailingPE'] = self._safe_float(row.get('trailing_pe'))
                info['forwardPE'] = self._safe_float(row.get('forward_pe'))
                info['trailingEps'] = self._safe_float(row.get('tailing_eps'))
                info['forwardEps'] = self._safe_float(row.get('forward_eps'))
                info['enterpriseToEbitda'] = self._safe_float(row.get('enterprise_to_ebitda'))
                info['enterpriseToRevenue'] = self._safe_float(row.get('enterprise_to_revenue'))
                info['pegRatio'] = self._safe_float(row.get('peg_ratio'))
                currency = row.get('currency')
                if currency and str(currency) != 'nan':
                    info['currency'] = str(currency)
                else:
                    info['currency'] = 'USD'
        except Exception as e:
            logger.warning(f"[DataProvider] defeatbeta summary() failed for {self.ticker}: {e}")

        # --- Company info (sector, industry, name) ---
        try:
            company_info = db.info()
            if company_info is not None and len(company_info) > 0:
                row = company_info.iloc[0]
                info['sector'] = str(row.get('sector', '')) if row.get('sector') else ''
                info['industry'] = str(row.get('industry', '')) if row.get('industry') else ''
                info['shortName'] = str(row.get('symbol', self.ticker))
                info['longName'] = str(row.get('symbol', self.ticker))
                info['country'] = str(row.get('country', '')) if row.get('country') else ''
        except Exception as e:
            logger.warning(f"[DataProvider] defeatbeta info() failed for {self.ticker}: {e}")

        # --- Profitability metrics ---
        try:
            nm = db.quarterly_net_margin()
            if nm is not None and len(nm) > 0:
                info['profitMargins'] = self._safe_float(nm.iloc[-1].get('net_margin'))
        except Exception as e:
            logger.debug(f"[DataProvider] defeatbeta quarterly_net_margin() failed: {e}")

        try:
            om = db.quarterly_operating_margin()
            if om is not None and len(om) > 0:
                info['operatingMargins'] = self._safe_float(om.iloc[-1].get('operating_margin'))
        except Exception as e:
            logger.debug(f"[DataProvider] defeatbeta quarterly_operating_margin() failed: {e}")

        # --- ROE, ROA ---
        try:
            roe = db.roe()
            if roe is not None and len(roe) > 0:
                info['returnOnEquity'] = self._safe_float(roe.iloc[-1].get('roe'))
        except Exception as e:
            logger.debug(f"[DataProvider] defeatbeta roe() failed: {e}")

        try:
            roa = db.roa()
            if roa is not None and len(roa) > 0:
                info['returnOnAssets'] = self._safe_float(roa.iloc[-1].get('roa'))
        except Exception as e:
            logger.debug(f"[DataProvider] defeatbeta roa() failed: {e}")

        # --- Growth metrics ---
        try:
            rg = db.quarterly_revenue_yoy_growth()
            if rg is not None and len(rg) > 0:
                info['revenueGrowth'] = self._safe_float(rg.iloc[-1].get('yoy_growth'))
        except Exception as e:
            logger.debug(f"[DataProvider] defeatbeta revenue_growth failed: {e}")

        try:
            eg = db.quarterly_net_income_yoy_growth()
            if eg is not None and len(eg) > 0:
                info['earningsGrowth'] = self._safe_float(eg.iloc[-1].get('yoy_growth'))
        except Exception as e:
            logger.debug(f"[DataProvider] defeatbeta earnings_growth failed: {e}")

        # --- Revenue (TTM) ---
        try:
            rev = db.ttm_revenue()
            if rev is not None and len(rev) > 0:
                info['totalRevenue'] = self._safe_float(rev.iloc[-1].get('ttm_total_revenue'))
        except Exception as e:
            logger.debug(f"[DataProvider] defeatbeta ttm_revenue() failed: {e}")

        # --- PB ratio ---
        try:
            pb = db.pb_ratio()
            if pb is not None and len(pb) > 0:
                info['priceToBook'] = self._safe_float(pb.iloc[-1].get('pb_ratio'))
                bv_per_share = None
                bv = self._safe_float(pb.iloc[-1].get('book_value_of_equity_usd'))
                shares = info.get('sharesOutstanding')
                if bv and shares and shares > 0:
                    bv_per_share = bv / shares
                info['bookValue'] = bv_per_share
        except Exception as e:
            logger.debug(f"[DataProvider] defeatbeta pb_ratio() failed: {e}")

        # --- PS ratio ---
        try:
            ps = db.ps_ratio()
            if ps is not None and len(ps) > 0:
                info['priceToSalesTrailing12Months'] = self._safe_float(ps.iloc[-1].get('ps_ratio'))
        except Exception as e:
            logger.debug(f"[DataProvider] defeatbeta ps_ratio() failed: {e}")

        # --- Dividends ---
        try:
            divs = db.dividends()
            if divs is not None and len(divs) > 0:
                # Calculate annual dividend from last 4 quarterly payments
                recent_divs = divs.tail(4)
                annual_div = sum(float(r['amount']) for _, r in recent_divs.iterrows())
                info['dividendRate'] = annual_div
                current_price = info.get('currentPrice', 0)
                if current_price and current_price > 0:
                    info['dividendYield'] = annual_div / current_price
        except Exception as e:
            logger.debug(f"[DataProvider] defeatbeta dividends() failed: {e}")

        # Fields that defeatbeta CANNOT provide — set to None/defaults
        # These will be filled by yfinance if it recovers, or skipped gracefully
        info.setdefault('targetHighPrice', None)
        info.setdefault('targetLowPrice', None)
        info.setdefault('targetMeanPrice', None)
        info.setdefault('targetMedianPrice', None)
        info.setdefault('recommendationKey', None)
        info.setdefault('numberOfAnalystOpinions', None)
        info.setdefault('sharesShort', None)
        info.setdefault('shortRatio', None)
        info.setdefault('shortPercentOfFloat', None)
        info.setdefault('heldPercentInsiders', None)
        info.setdefault('heldPercentInstitutions', None)
        info.setdefault('floatShares', None)
        info.setdefault('quickRatio', None)
        info.setdefault('currentRatio', None)
        info.setdefault('debtToEquity', None)
        info.setdefault('totalCash', None)
        info.setdefault('totalDebt', None)
        info.setdefault('revenuePerShare', None)
        info.setdefault('payoutRatio', None)

        self._db_cache['info'] = info
        logger.info(f"[DataProvider] Built info from defeatbeta for {self.ticker} ({len(info)} fields)")
        return info

    # ──────────────────────────────────────────────
    # .history() method
    # ──────────────────────────────────────────────
    def history(self, period=None, start=None, end=None, timeout=30) -> pd.DataFrame:
        """
        Returns OHLCV DataFrame in yfinance format.
        Falls back to defeatbeta on rate limit or empty results.
        """
        if not self._yf_failed:
            try:
                kwargs = {'timeout': timeout}
                if period:
                    kwargs['period'] = period
                if start is not None:
                    kwargs['start'] = start
                if end is not None:
                    kwargs['end'] = end

                result = self._get_yf().history(**kwargs)
                if result is not None and not result.empty:
                    return result
                # yfinance returned empty - treat as rate limit
                logger.warning(f"[DataProvider] yfinance returned empty history for {self.ticker}, falling back to defeatbeta")
                self._yf_failed = True
            except Exception as e:
                if _is_rate_limit_error(e):
                    logger.warning(f"[DataProvider] yfinance rate limited for {self.ticker}.history(), falling back to defeatbeta")
                    self._yf_failed = True
                else:
                    # For any other exception, also try defeatbeta fallback
                    logger.warning(f"[DataProvider] yfinance error for {self.ticker}.history() ({e}), falling back to defeatbeta")
                    self._yf_failed = True

        # Fallback to defeatbeta
        if _is_index_or_macro_ticker(self.ticker):
            return pd.DataFrame()

        return self._get_history_from_defeatbeta(period, start, end)

    def _get_history_from_defeatbeta(self, period=None, start=None, end=None) -> pd.DataFrame:
        """Convert defeatbeta price() data to yfinance history format."""
        try:
            db = self._get_db()
            price_df = db.price()

            if price_df is None or price_df.empty:
                return pd.DataFrame()

            # Convert to yfinance format
            df = price_df.copy()
            df['report_date'] = pd.to_datetime(df['report_date'])
            df = df.set_index('report_date')
            df.index.name = 'Date'

            # Rename columns to match yfinance (capitalized)
            df = df.rename(columns={
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume',
            })

            # Keep only OHLCV columns
            cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            df = df[[c for c in cols if c in df.columns]]

            # Ensure numeric types
            for col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            # Filter by date range
            if start is not None:
                if isinstance(start, str):
                    start = pd.Timestamp(start)
                elif isinstance(start, datetime):
                    start = pd.Timestamp(start)
                df = df[df.index >= start]

            if end is not None:
                if isinstance(end, str):
                    end = pd.Timestamp(end)
                elif isinstance(end, datetime):
                    end = pd.Timestamp(end)
                df = df[df.index <= end]

            # Handle period-based filtering
            if period and start is None and end is None:
                now = pd.Timestamp.now()
                period_map = {
                    '1d': timedelta(days=1),
                    '5d': timedelta(days=5),
                    '1mo': timedelta(days=30),
                    '3mo': timedelta(days=90),
                    '6mo': timedelta(days=180),
                    '1y': timedelta(days=365),
                    '2y': timedelta(days=730),
                    '5y': timedelta(days=1825),
                    '10y': timedelta(days=3650),
                    'max': timedelta(days=36500),
                }
                delta = period_map.get(period)
                if delta:
                    cutoff = now - delta
                    df = df[df.index >= cutoff]

            # Make index timezone-aware if needed (yfinance returns tz-aware)
            if df.index.tz is None:
                df.index = df.index.tz_localize('America/New_York')

            return df

        except Exception as e:
            logger.error(f"[DataProvider] defeatbeta history fallback failed for {self.ticker}: {e}")
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
        if not self._yf_failed:
            try:
                result = self._get_yf().quarterly_earnings
                if result is not None and not result.empty:
                    return result
            except Exception as e:
                if _is_rate_limit_error(e):
                    logger.warning(f"[DataProvider] yfinance rate limited for {self.ticker}.quarterly_earnings")
                    self._yf_failed = True
                else:
                    raise

        # Fallback to defeatbeta
        if _is_index_or_macro_ticker(self.ticker):
            return pd.DataFrame()

        return self._get_earnings_from_defeatbeta()

    def _get_earnings_from_defeatbeta(self) -> pd.DataFrame:
        """Convert defeatbeta earnings() to yfinance quarterly_earnings format."""
        try:
            db = self._get_db()
            earnings = db.earnings()

            if earnings is None or earnings.empty:
                return pd.DataFrame()

            # yfinance quarterly_earnings has index=date, columns=['Revenue', 'Earnings']
            # defeatbeta has: symbol, eps_actual, eps_estimate, surprise_percent, quarter_name, quarter_date
            df = pd.DataFrame()
            df['Earnings'] = pd.to_numeric(earnings['eps_actual'], errors='coerce')
            df.index = pd.to_datetime(earnings['quarter_date'])
            df.index.name = None

            # Revenue is not in defeatbeta earnings — try from income statement
            # Set Revenue to NaN (some yfinance quarterly_earnings also lack it)
            df['Revenue'] = np.nan

            return df

        except Exception as e:
            logger.error(f"[DataProvider] defeatbeta earnings fallback failed for {self.ticker}: {e}")
            return pd.DataFrame()

    # ──────────────────────────────────────────────
    # .options property (yfinance only — defeatbeta doesn't support options)
    # ──────────────────────────────────────────────
    @property
    def options(self):
        """Returns available option expiration dates. yfinance only."""
        try:
            return self._get_yf().options
        except Exception:
            return ()

    # ──────────────────────────────────────────────
    # .option_chain() method (yfinance only)
    # ──────────────────────────────────────────────
    def option_chain(self, date):
        """Returns option chain for a specific date. yfinance only."""
        try:
            return self._get_yf().option_chain(date)
        except Exception:
            return None

    # ──────────────────────────────────────────────
    # .fast_info property
    # ──────────────────────────────────────────────
    @property
    def fast_info(self):
        """Returns fast_info. yfinance only, degrade gracefully."""
        try:
            return self._get_yf().fast_info
        except Exception:
            return None

    # ──────────────────────────────────────────────
    # .calendar property
    # ──────────────────────────────────────────────
    @property
    def calendar(self):
        """Returns calendar data. yfinance only, degrade gracefully."""
        try:
            return self._get_yf().calendar
        except Exception:
            return None

    # ──────────────────────────────────────────────
    # Utility
    # ──────────────────────────────────────────────
    @staticmethod
    def _safe_float(val) -> Optional[float]:
        """Safely convert a value to float, returning None for NaN/None."""
        if val is None:
            return None
        try:
            result = float(val)
            if pd.isna(result):
                return None
            return result
        except (ValueError, TypeError):
            return None


def data_provider_download(ticker: str, period: str = '6mo', progress: bool = False) -> pd.DataFrame:
    """
    Drop-in replacement for yf.download() with defeatbeta fallback.
    Returns a DataFrame with OHLCV data.
    """
    try:
        result = yf.download(ticker, period=period, progress=progress)
        if result is not None and not result.empty:
            return result
    except Exception as e:
        if _is_rate_limit_error(e):
            logger.warning(f"[DataProvider] yf.download rate limited for {ticker}, trying defeatbeta")
        else:
            raise

    # Fallback to defeatbeta via DataProvider
    if _is_index_or_macro_ticker(ticker):
        return pd.DataFrame()

    provider = DataProvider(ticker)
    provider._yf_failed = True  # Force defeatbeta path
    return provider.history(period=period)

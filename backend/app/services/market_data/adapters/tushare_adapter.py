"""
Tushare Data Provider Adapter

Provides access to Tushare API for A-share (China stock market) data:
- Real-time and historical stock quotes
- Company info and fundamentals
- Index data

Requires TUSHARE_TOKEN environment variable.
Tushare Pro API: https://tushare.pro/document/2

Note: Some APIs require higher permission levels (积分).
This adapter will try multiple methods and fallback gracefully.
"""

import os
import logging
from typing import Optional, List
from datetime import date, datetime, timedelta
import pandas as pd

from ..interfaces import (
    DataProviderAdapter, DataType, Market, ProviderStatus,
    QuoteData, FundamentalsData, CompanyInfo, HistoryData
)
from ..config import get_timezone_for_market
from .base import BaseAdapter, safe_float, safe_int, safe_str

logger = logging.getLogger(__name__)

# Try to import tushare
try:
    import tushare as ts
    TUSHARE_AVAILABLE = True
except ImportError:
    ts = None
    TUSHARE_AVAILABLE = False


class TushareAdapter(BaseAdapter, DataProviderAdapter):
    """
    Tushare API data provider adapter.

    Provides A-share stock data including quotes, historical data,
    company info, and fundamentals.

    Requires API token from environment variable TUSHARE_TOKEN.

    Note: Tushare has a tiered permission system. Some APIs require
    higher permission levels (积分). This adapter tries multiple
    fallback methods to maximize compatibility.
    """

    def __init__(self):
        # Tushare Pro has rate limits based on account level
        # Free tier: ~200 requests/minute
        super().__init__(cooldown_seconds=60, max_failures=5)
        self._token = os.environ.get("TUSHARE_TOKEN", "")
        self._pro: Optional[object] = None
        self._initialized = False
        self._permission_error_logged = False

        if TUSHARE_AVAILABLE and self._token:
            try:
                ts.set_token(self._token)
                self._pro = ts.pro_api()
                self._initialized = True
                logger.info("[Tushare] Adapter initialized successfully")
            except Exception as e:
                logger.warning(f"[Tushare] Failed to initialize: {e}")

    @property
    def name(self) -> str:
        return "tushare"

    @property
    def supported_data_types(self) -> List[DataType]:
        return [
            DataType.QUOTE,
            DataType.HISTORY,
            DataType.INFO,
            DataType.FUNDAMENTALS,
        ]

    @property
    def supported_markets(self) -> List[Market]:
        return [Market.CN]  # A-share only

    def supports_symbol(self, symbol: str) -> bool:
        """
        Tushare supports A-share stocks.

        Supported formats:
        - 600xxx.SH / 600xxx.SS (Shanghai main board)
        - 000xxx.SZ (Shenzhen main board)
        - 002xxx.SZ (Shenzhen SME board)
        - 300xxx.SZ (Shenzhen ChiNext/创业板)
        - 688xxx.SH (Shanghai STAR/科创板)
        """
        symbol_upper = symbol.upper()
        # Must have market suffix
        if symbol_upper.endswith('.SH') or symbol_upper.endswith('.SS'):
            return True
        if symbol_upper.endswith('.SZ'):
            return True
        # Also accept pure numeric codes (will be auto-converted)
        if symbol.isdigit() and len(symbol) == 6:
            return True
        return False

    def _normalize_symbol(self, symbol: str) -> str:
        """
        Normalize symbol to Tushare format (XXXXXX.SH or XXXXXX.SZ).

        Converts:
        - 600000 -> 600000.SH
        - 000001 -> 000001.SZ
        - 600000.SS -> 600000.SH (SS is yfinance format)
        """
        symbol_upper = symbol.upper()

        # Already in correct format
        if symbol_upper.endswith('.SH') or symbol_upper.endswith('.SZ'):
            return symbol_upper

        # Convert .SS (yfinance format) to .SH (tushare format)
        if symbol_upper.endswith('.SS'):
            return symbol_upper.replace('.SS', '.SH')

        # Pure numeric - determine exchange by code prefix
        if symbol.isdigit() and len(symbol) == 6:
            prefix = symbol[:1]
            if prefix in ['6', '5', '9']:  # Shanghai
                return f"{symbol}.SH"
            else:  # Shenzhen (0, 3, 2)
                return f"{symbol}.SZ"

        return symbol_upper

    def _get_stock_code(self, ts_symbol: str) -> str:
        """Extract numeric stock code from ts_symbol (e.g., 600519.SH -> 600519)."""
        return ts_symbol.split('.')[0]

    def _is_available(self) -> bool:
        """Check if Tushare is available and configured."""
        return TUSHARE_AVAILABLE and self._initialized and self._pro is not None

    def _is_permission_error(self, e: Exception) -> bool:
        """Check if exception is a permission error."""
        error_msg = str(e)
        return '没有接口访问权限' in error_msg or '权限' in error_msg

    def _log_permission_hint(self):
        """Log a hint about permission requirements (only once)."""
        if not self._permission_error_logged:
            logger.warning(
                "[Tushare] Some APIs require higher permission levels (积分). "
                "Visit https://tushare.pro/document/1?doc_id=108 for details. "
                "Using fallback methods where available."
            )
            self._permission_error_logged = True

    def get_quote(self, symbol: str) -> Optional[QuoteData]:
        """
        Get quote data.

        Tries multiple methods:
        1. pro_bar (often works with basic permissions)
        2. daily (requires 120 points)
        """
        if self.is_rate_limited():
            return None

        if not self._is_available():
            return None

        ts_symbol = self._normalize_symbol(symbol)
        stock_code = self._get_stock_code(ts_symbol)

        # Method 1: Try pro_bar (more accessible)
        try:
            df = ts.pro_bar(
                ts_code=ts_symbol,
                adj='qfq',  # 前复权
                start_date=(datetime.now() - timedelta(days=10)).strftime('%Y%m%d'),
                end_date=datetime.now().strftime('%Y%m%d'),
            )

            if df is not None and not df.empty:
                latest = df.iloc[0]
                current_price = safe_float(latest.get('close'))
                if current_price is not None:
                    self._handle_success()
                    return QuoteData(
                        symbol=symbol,
                        current_price=current_price,
                        previous_close=safe_float(latest.get('pre_close')),
                        open_price=safe_float(latest.get('open')),
                        day_high=safe_float(latest.get('high')),
                        day_low=safe_float(latest.get('low')),
                        volume=safe_int(latest.get('vol')),
                        timestamp=datetime.now(),
                        source=self.name,
                    )
        except Exception as e:
            if self._is_permission_error(e):
                self._log_permission_hint()
            logger.debug(f"[Tushare] pro_bar failed for {symbol}: {e}")

        # Method 2: Try daily API
        try:
            df = self._pro.daily(
                ts_code=ts_symbol,
                start_date=(datetime.now() - timedelta(days=10)).strftime('%Y%m%d'),
                end_date=datetime.now().strftime('%Y%m%d')
            )

            if df is not None and not df.empty:
                latest = df.iloc[0]
                current_price = safe_float(latest.get('close'))
                if current_price is not None:
                    self._handle_success()
                    return QuoteData(
                        symbol=symbol,
                        current_price=current_price,
                        previous_close=safe_float(latest.get('pre_close')),
                        open_price=safe_float(latest.get('open')),
                        day_high=safe_float(latest.get('high')),
                        day_low=safe_float(latest.get('low')),
                        volume=safe_int(latest.get('vol')),
                        timestamp=datetime.now(),
                        source=self.name,
                    )
        except Exception as e:
            if self._is_permission_error(e):
                self._log_permission_hint()
            logger.debug(f"[Tushare] daily failed for {symbol}: {e}")

        # All methods failed
        self._handle_error(Exception("All quote methods failed"), symbol)
        return None

    def get_history(
        self,
        symbol: str,
        period: Optional[str] = None,
        start: Optional[date] = None,
        end: Optional[date] = None
    ) -> Optional[HistoryData]:
        """
        Get historical OHLCV data.

        Tries multiple methods:
        1. pro_bar (often works with basic permissions)
        2. daily (requires 120 points)
        """
        if self.is_rate_limited():
            return None

        if not self._is_available():
            return None

        ts_symbol = self._normalize_symbol(symbol)

        # Calculate date range
        end_date = end if end else datetime.now().date()
        if start:
            start_date = start
        elif period:
            start_date = self._period_to_start_date(period, end_date)
        else:
            start_date = end_date - timedelta(days=30)

        # Format dates for Tushare (YYYYMMDD)
        start_str = start_date.strftime('%Y%m%d') if isinstance(start_date, (date, datetime)) else start_date
        end_str = end_date.strftime('%Y%m%d') if isinstance(end_date, (date, datetime)) else end_date

        df = None

        # Method 1: Try pro_bar
        try:
            df = ts.pro_bar(
                ts_code=ts_symbol,
                adj='qfq',  # 前复权
                start_date=start_str,
                end_date=end_str,
            )
        except Exception as e:
            if self._is_permission_error(e):
                self._log_permission_hint()
            logger.debug(f"[Tushare] pro_bar failed for history {symbol}: {e}")

        # Method 2: Try daily
        if df is None or df.empty:
            try:
                df = self._pro.daily(
                    ts_code=ts_symbol,
                    start_date=start_str,
                    end_date=end_str
                )
            except Exception as e:
                if self._is_permission_error(e):
                    self._log_permission_hint()
                logger.debug(f"[Tushare] daily failed for history {symbol}: {e}")

        if df is None or df.empty:
            self._handle_error(Exception("All history methods failed"), symbol)
            return None

        try:
            # Convert to standard format
            df = df.rename(columns={
                'trade_date': 'Date',
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'vol': 'Volume',  # In hands (手)
            })

            # Convert volume from hands to shares (1手 = 100股)
            if 'Volume' in df.columns:
                df['Volume'] = df['Volume'] * 100

            # Parse date and set as index
            df['Date'] = pd.to_datetime(df['Date'], format='%Y%m%d')
            df = df.set_index('Date')
            df = df.sort_index()

            # Keep only OHLCV columns
            available_cols = [c for c in ['Open', 'High', 'Low', 'Close', 'Volume'] if c in df.columns]
            df = df[available_cols]

            # Add timezone
            if df.index.tz is None:
                df.index = df.index.tz_localize('Asia/Shanghai')

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

    def _period_to_start_date(self, period: str, end_date: date) -> date:
        """Convert period string to start date."""
        period_map = {
            '1d': timedelta(days=1),
            '5d': timedelta(days=5),
            '1mo': timedelta(days=30),
            '3mo': timedelta(days=90),
            '6mo': timedelta(days=180),
            '1y': timedelta(days=365),
            '2y': timedelta(days=730),
            '5y': timedelta(days=1825),
            'max': timedelta(days=3650),  # ~10 years
        }
        delta = period_map.get(period, timedelta(days=30))
        if isinstance(end_date, datetime):
            end_date = end_date.date()
        return end_date - delta

    def get_info(self, symbol: str) -> Optional[CompanyInfo]:
        """
        Get company information.

        Uses stock_basic API which is accessible with basic permissions.
        """
        if self.is_rate_limited():
            return None

        if not self._is_available():
            return None

        try:
            ts_symbol = self._normalize_symbol(symbol)
            stock_code = self._get_stock_code(ts_symbol)

            # Get stock basic info - try with ts_code filter first
            df = None
            try:
                df = self._pro.stock_basic(
                    ts_code=ts_symbol,
                    fields='ts_code,symbol,name,area,industry,market,list_date,exchange'
                )
            except Exception as e:
                if self._is_permission_error(e):
                    self._log_permission_hint()
                logger.debug(f"[Tushare] stock_basic with ts_code failed: {e}")

            # Fallback: get all stocks and filter
            if df is None or df.empty:
                try:
                    all_stocks = self._pro.stock_basic(
                        exchange='',
                        list_status='L',
                        fields='ts_code,symbol,name,area,industry,market,list_date,exchange'
                    )
                    if all_stocks is not None and not all_stocks.empty:
                        df = all_stocks[all_stocks['ts_code'] == ts_symbol]
                except Exception as e:
                    logger.debug(f"[Tushare] stock_basic fallback failed: {e}")

            if df is None or df.empty:
                return None

            info = df.iloc[0]

            # Map exchange code to name
            exchange_map = {
                'SSE': 'Shanghai Stock Exchange',
                'SZSE': 'Shenzhen Stock Exchange',
            }
            exchange = exchange_map.get(safe_str(info.get('exchange')), safe_str(info.get('exchange')))

            self._handle_success()
            return CompanyInfo(
                symbol=symbol,
                name=safe_str(info.get('name')) or symbol,
                sector=None,  # Tushare doesn't provide sector classification in basic info
                industry=safe_str(info.get('industry')),
                country='China',
                description=None,  # Would need separate API call
                employees=None,
                website=None,
                currency='CNY',
                exchange=exchange,
                source=self.name,
            )

        except Exception as e:
            self._handle_error(e, symbol)
            return None

    def get_fundamentals(self, symbol: str) -> Optional[FundamentalsData]:
        """
        Get fundamental metrics.

        Uses daily_basic API (requires 120 points) with fallback.
        """
        if self.is_rate_limited():
            return None

        if not self._is_available():
            return None

        ts_symbol = self._normalize_symbol(symbol)

        # Get daily basic indicators (PE, PB, etc.)
        today = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=10)).strftime('%Y%m%d')

        df = None

        # Try daily_basic
        try:
            df = self._pro.daily_basic(
                ts_code=ts_symbol,
                start_date=start_date,
                end_date=today,
                fields='ts_code,trade_date,pe,pe_ttm,pb,ps,ps_ttm,dv_ratio,dv_ttm,total_mv,circ_mv'
            )
        except Exception as e:
            if self._is_permission_error(e):
                self._log_permission_hint()
            logger.debug(f"[Tushare] daily_basic failed for {symbol}: {e}")

        if df is None or df.empty:
            # Return minimal fundamentals without valuation data
            self._handle_success()
            return FundamentalsData(
                symbol=symbol,
                source=self.name,
            )

        # Get the most recent data
        latest = df.iloc[0]

        # Try to get financial indicators (requires higher permissions)
        roe = None
        roa = None
        profit_margin = None
        try:
            fina_df = self._pro.fina_indicator(
                ts_code=ts_symbol,
                fields='ts_code,ann_date,roe,roa,netprofit_margin,grossprofit_margin'
            )
            if fina_df is not None and not fina_df.empty:
                fina = fina_df.iloc[0]
                roe = safe_float(fina.get('roe'))
                roa = safe_float(fina.get('roa'))
                profit_margin = safe_float(fina.get('netprofit_margin'))
        except Exception as e:
            logger.debug(f"[Tushare] fina_indicator failed for {symbol}: {e}")

        self._handle_success()
        return FundamentalsData(
            symbol=symbol,
            pe_ratio=safe_float(latest.get('pe_ttm')),  # Use TTM PE
            forward_pe=safe_float(latest.get('pe')),    # Static PE as proxy
            pb_ratio=safe_float(latest.get('pb')),
            ps_ratio=safe_float(latest.get('ps_ttm')),
            peg_ratio=None,  # Not directly available
            ev_ebitda=None,  # Not directly available
            profit_margin=profit_margin,
            operating_margin=None,
            roe=roe,
            roa=roa,
            revenue_growth=None,  # Would need time series comparison
            earnings_growth=None,
            beta=None,  # Not directly available
            dividend_yield=safe_float(latest.get('dv_ttm')),  # TTM dividend yield
            eps_trailing=None,  # Would need separate call
            eps_forward=None,
            target_high=None,  # No analyst targets in Tushare
            target_low=None,
            target_mean=None,
            recommendation=None,
            source=self.name,
        )

    def get_options_expirations(self, symbol: str) -> Optional[List[str]]:
        """Tushare doesn't provide options data for A-shares."""
        return None

    def get_options_chain(self, symbol: str, expiry: str):
        """Tushare doesn't provide options data for A-shares."""
        return None

    def health_check(self) -> ProviderStatus:
        """Check provider health."""
        if not self._is_available():
            return ProviderStatus.UNAVAILABLE
        return super().health_check()


# Test the adapter if run directly
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    adapter = TushareAdapter()

    print("Testing Tushare Adapter...")
    print(f"Available: {adapter._is_available()}")

    if adapter._is_available():
        # Test with a popular A-share stock (Kweichow Moutai)
        symbol = "600519.SH"
        print(f"\nTesting with {symbol} (贵州茅台)...")

        quote = adapter.get_quote(symbol)
        if quote:
            print(f"  Quote: {quote.current_price} CNY")
        else:
            print("  Quote: Failed")

        info = adapter.get_info(symbol)
        if info:
            print(f"  Company: {info.name}")
            print(f"  Industry: {info.industry}")
        else:
            print("  Info: Failed")

        history = adapter.get_history(symbol, period="1mo")
        if history and not history.empty:
            print(f"  History: {len(history.df)} days of data")
            print(f"  Latest close: {history.df['Close'].iloc[-1]}")
        else:
            print("  History: Failed")

        fundamentals = adapter.get_fundamentals(symbol)
        if fundamentals:
            print(f"  PE (TTM): {fundamentals.pe_ratio}")
            print(f"  PB: {fundamentals.pb_ratio}")
        else:
            print("  Fundamentals: Failed")
    else:
        print("Set TUSHARE_TOKEN environment variable to test")

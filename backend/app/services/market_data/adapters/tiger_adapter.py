"""
Tiger Open API Data Provider Adapter

Provides access to Tiger Brokers (老虎证券) data:
- Real-time quotes for US, HK, CN markets (get_stock_briefs, get_stock_delay_briefs)
- Historical OHLCV data (get_bars, get_bars_by_page)
- Options chains with Greeks
- Market depth (get_depth_quote)
- Trade ticks (get_trade_ticks)
- Timeline data (get_timeline, get_timeline_history)
- Capital flow (get_capital_flow, get_capital_distribution)
- Warrant data (get_warrant_filter, get_warrant_briefs)

Best for options data and HK/CN markets when yfinance is rate limited.
"""

import logging
import os
from typing import Optional, List, Dict, Any
from datetime import date, datetime, timedelta
import pandas as pd

from ..interfaces import (
    DataProviderAdapter, DataType, Market, ProviderStatus,
    QuoteData, FundamentalsData, CompanyInfo, HistoryData, OptionsChainData
)
from ..config import get_timezone_for_market, get_market_for_symbol
from .base import BaseAdapter, safe_float, safe_int

logger = logging.getLogger(__name__)

# Import Tiger API
try:
    from tigeropen.common.consts import Language, Market as TigerMarket, BarPeriod
    from tigeropen.tiger_open_config import TigerOpenClientConfig
    from tigeropen.quote.quote_client import QuoteClient
    TIGER_AVAILABLE = True
except ImportError:
    TIGER_AVAILABLE = False
    TigerMarket = None
    BarPeriod = None


class TigerAdapter(BaseAdapter, DataProviderAdapter):
    """
    Tiger Open API data provider adapter.

    Supports US, HK, and CN markets with good options coverage.
    Requires Tiger API credentials configured via properties file.
    """

    def __init__(self):
        super().__init__(cooldown_seconds=60, max_failures=3)
        self._quote_client: Optional[object] = None
        self._initialized = False

    @property
    def name(self) -> str:
        return "tiger"

    @property
    def supported_data_types(self) -> List[DataType]:
        return [
            DataType.QUOTE,
            DataType.HISTORY,
            DataType.OPTIONS_CHAIN,
            DataType.OPTIONS_EXPIRATIONS,
        ]

    @property
    def supported_markets(self) -> List[Market]:
        return [Market.US, Market.HK, Market.CN]

    def supports_symbol(self, symbol: str) -> bool:
        """
        Tiger API supports regular stocks but not indices/futures.

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

    def _get_tiger_market(self, market: Market) -> object:
        """Convert our Market enum to Tiger's Market."""
        if not TIGER_AVAILABLE:
            return None
        return {
            Market.US: TigerMarket.US,
            Market.HK: TigerMarket.HK,
            Market.CN: TigerMarket.CN,
        }.get(market, TigerMarket.US)

    def _ensure_initialized(self) -> bool:
        """Ensure Tiger client is initialized."""
        if self._initialized and self._quote_client is not None:
            return True

        if not TIGER_AVAILABLE:
            return False

        try:
            # Look for Tiger config file in standard locations
            config_paths = [
                os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'tiger_openapi_config.properties'),
                os.path.join(os.path.dirname(__file__), '..', '..', '..', 'tiger_openapi_config.properties'),
                os.path.join(os.path.dirname(__file__), '..', '..', 'tiger_openapi_config.properties'),
                '/etc/tiger/tiger_openapi_config.properties',
            ]

            config_file = None
            for path in config_paths:
                abs_path = os.path.abspath(path)
                if os.path.exists(abs_path):
                    config_file = abs_path
                    break

            if not config_file:
                logger.warning("[Tiger] Config file not found")
                return False

            client_config = TigerOpenClientConfig(props_path=config_file)
            client_config.language = Language.zh_CN

            self._quote_client = QuoteClient(client_config)
            self._initialized = True
            logger.info(f"[Tiger] Initialized with Tiger ID: {client_config.tiger_id}")
            return True

        except Exception as e:
            logger.warning(f"[Tiger] Initialization failed: {e}")
            return False

    def get_quote(self, symbol: str) -> Optional[QuoteData]:
        """Get real-time quote."""
        if self.is_rate_limited():
            return None

        if not self._ensure_initialized():
            return None

        try:
            briefs = self._quote_client.get_stock_briefs([symbol])

            if briefs is None or briefs.empty:
                return None

            row = briefs.iloc[0]

            current_price = safe_float(row.get('latest_price'))
            if current_price is None:
                return None

            self._handle_success()
            return QuoteData(
                symbol=symbol,
                current_price=current_price,
                previous_close=safe_float(row.get('pre_close')),
                open_price=safe_float(row.get('open')),
                day_high=safe_float(row.get('high')),
                day_low=safe_float(row.get('low')),
                volume=safe_int(row.get('volume')),
                market_cap=safe_float(row.get('market_cap')),
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
        if self.is_rate_limited():
            return None

        if not self._ensure_initialized():
            return None

        try:
            # Calculate time range
            end_time = int(datetime.now().timestamp() * 1000)
            limit = self._period_to_limit(period) if period else 60

            # Note: get_bars doesn't accept market param - it infers from symbol
            bars = self._quote_client.get_bars(
                symbols=[symbol],
                period=BarPeriod.DAY,
                end_time=end_time,
                limit=limit,
            )

            if bars is None or bars.empty:
                return None

            # Transform to standard format
            df = bars.copy()

            # Rename columns
            column_map = {
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume',
            }
            df = df.rename(columns=column_map)

            # Set time as index
            if 'time' in df.columns:
                df['Date'] = pd.to_datetime(df['time'], unit='ms')
                df = df.set_index('Date')

            # Filter columns
            columns_to_keep = ['Open', 'High', 'Low', 'Close', 'Volume']
            df = df[[c for c in columns_to_keep if c in df.columns]]

            # Sort by date
            df = df.sort_index()

            # Apply date filters
            if start:
                df = df[df.index >= pd.Timestamp(start)]
            if end:
                df = df[df.index <= pd.Timestamp(end)]

            if df.empty:
                return None

            # Add timezone
            tz = get_timezone_for_market(market)
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

    def _period_to_limit(self, period: str) -> int:
        """Convert period string to bar count limit."""
        limit_map = {
            '1d': 1,
            '5d': 5,
            '1wk': 7,
            '1mo': 22,
            '3mo': 66,
            '6mo': 132,
            '1y': 252,
            '2y': 504,
            '5y': 1260,
        }
        return limit_map.get(period, 60)

    def get_info(self, symbol: str) -> Optional[CompanyInfo]:
        """Tiger API doesn't provide company info."""
        return None

    def get_fundamentals(self, symbol: str) -> Optional[FundamentalsData]:
        """Tiger API doesn't provide fundamental data."""
        return None

    def get_options_expirations(self, symbol: str) -> Optional[List[str]]:
        """Get available option expiration dates."""
        if self.is_rate_limited():
            return None

        if not self._ensure_initialized():
            return None

        try:
            market = get_market_for_symbol(symbol)
            tiger_market = self._get_tiger_market(market)

            expirations = self._quote_client.get_option_expirations(
                symbols=[symbol],
                market=tiger_market
            )

            if expirations is None or expirations.empty:
                return None

            # Extract expiry dates
            if 'expiry' in expirations.columns:
                dates = expirations['expiry'].tolist()
            elif 'date' in expirations.columns:
                dates = expirations['date'].tolist()
            else:
                dates = expirations.iloc[:, 0].tolist()

            # Convert to string format YYYY-MM-DD
            result = []
            for d in dates:
                if isinstance(d, str):
                    result.append(d)
                elif hasattr(d, 'strftime'):
                    result.append(d.strftime('%Y-%m-%d'))
                else:
                    result.append(str(d))

            self._handle_success()
            return result if result else None
        except Exception as e:
            self._handle_error(e, symbol)
            return None

    def get_options_chain(self, symbol: str, expiry: str) -> Optional[OptionsChainData]:
        """Get options chain for an expiry."""
        if self.is_rate_limited():
            return None

        if not self._ensure_initialized():
            return None

        try:
            market = get_market_for_symbol(symbol)
            tiger_market = self._get_tiger_market(market)

            # Get underlying price
            briefs = self._quote_client.get_stock_briefs([symbol])
            underlying_price = None
            if briefs is not None and not briefs.empty:
                underlying_price = safe_float(briefs.iloc[0].get('latest_price'))

            if underlying_price is None:
                return None

            # Get option chain
            chain = self._quote_client.get_option_chain(
                symbol=symbol,
                expiry=expiry,
                market=tiger_market,
                return_greek_value=True
            )

            if chain is None or chain.empty:
                return None

            # Split into calls and puts
            if 'put_call' in chain.columns:
                calls = chain[chain['put_call'] == 'CALL'].copy()
                puts = chain[chain['put_call'] == 'PUT'].copy()
            elif 'right' in chain.columns:
                calls = chain[chain['right'] == 'CALL'].copy()
                puts = chain[chain['right'] == 'PUT'].copy()
            else:
                return None

            # Rename columns to match yfinance format
            column_map = {
                'strike_price': 'strike',
                'latest_price': 'lastPrice',
                'bid_price': 'bid',
                'ask_price': 'ask',
                'open_interest': 'openInterest',
                'implied_volatility': 'impliedVolatility',
                'volatility': 'impliedVolatility',
            }

            for df in [calls, puts]:
                if df is not None:
                    for old_col, new_col in column_map.items():
                        if old_col in df.columns and new_col not in df.columns:
                            df[new_col] = df[old_col]

            self._handle_success()
            return OptionsChainData(
                symbol=symbol,
                expiry_date=expiry,
                underlying_price=underlying_price,
                calls=calls if not calls.empty else pd.DataFrame(),
                puts=puts if not puts.empty else pd.DataFrame(),
                source=self.name,
            )
        except Exception as e:
            self._handle_error(e, symbol)
            return None

    def health_check(self) -> ProviderStatus:
        """Check provider health."""
        if not TIGER_AVAILABLE:
            return ProviderStatus.UNAVAILABLE
        if not self._ensure_initialized():
            return ProviderStatus.UNAVAILABLE
        return super().health_check()

    # ─────────────────────────────────────────────────────────────────────────
    # Extended Tiger API Methods
    # ─────────────────────────────────────────────────────────────────────────

    def get_delay_quote(self, symbol: str) -> Optional[QuoteData]:
        """
        Get 15-minute delayed quote (free, no permissions required).
        Useful as fallback when real-time quotes are unavailable.
        """
        if not self._ensure_initialized():
            return None

        try:
            briefs = self._quote_client.get_stock_delay_briefs([symbol])

            if briefs is None or briefs.empty:
                return None

            row = briefs.iloc[0]
            current_price = safe_float(row.get('latest_price'))
            if current_price is None:
                return None

            return QuoteData(
                symbol=symbol,
                current_price=current_price,
                previous_close=safe_float(row.get('pre_close')),
                open_price=safe_float(row.get('open')),
                day_high=safe_float(row.get('high')),
                day_low=safe_float(row.get('low')),
                volume=safe_int(row.get('volume')),
                source=f"{self.name}_delayed",
            )
        except Exception as e:
            logger.warning(f"[Tiger] get_delay_quote failed for {symbol}: {e}")
            return None

    def get_market_status(self, market: Market = Market.US) -> Optional[Dict[str, Any]]:
        """
        Get market trading status.

        Returns:
            Dict with market, status (NOT_YET_OPEN, PRE_HOUR_TRADING, TRADING, etc.),
            and open_time.
        """
        if not self._ensure_initialized():
            return None

        try:
            tiger_market = self._get_tiger_market(market)
            status = self._quote_client.get_market_status(market=tiger_market)

            if status is None or status.empty:
                return None

            row = status.iloc[0]
            return {
                "market": str(row.get("market", market.value)),
                "status": str(row.get("status", "UNKNOWN")),
                "open_time": row.get("open_time"),
            }
        except Exception as e:
            logger.warning(f"[Tiger] get_market_status failed: {e}")
            return None

    def get_depth_quote(self, symbol: str, market: Optional[Market] = None) -> Optional[Dict[str, Any]]:
        """
        Get order book depth data (bid/ask levels).

        Returns:
            Dict with 'bids' and 'asks' lists, each containing [price, volume, order_count]
        """
        if not self._ensure_initialized():
            return None

        try:
            if market is None:
                market = get_market_for_symbol(symbol)
            tiger_market = self._get_tiger_market(market)

            depth = self._quote_client.get_depth_quote(
                symbols=[symbol],
                market=tiger_market
            )

            if depth is None or depth.empty:
                return None

            # Parse depth data
            result = {"symbol": symbol, "bids": [], "asks": []}

            for _, row in depth.iterrows():
                if row.get("symbol") == symbol:
                    # Extract bid/ask arrays
                    bids = row.get("bids", [])
                    asks = row.get("asks", [])

                    if isinstance(bids, list):
                        result["bids"] = bids
                    if isinstance(asks, list):
                        result["asks"] = asks

            return result if result["bids"] or result["asks"] else None

        except Exception as e:
            logger.warning(f"[Tiger] get_depth_quote failed for {symbol}: {e}")
            return None

    def get_trade_ticks(
        self,
        symbol: str,
        limit: int = 100,
        begin_index: int = 0
    ) -> Optional[pd.DataFrame]:
        """
        Get tick-by-tick trade data.

        Returns:
            DataFrame with columns: time, price, volume, direction
        """
        if not self._ensure_initialized():
            return None

        try:
            market = get_market_for_symbol(symbol)
            tiger_market = self._get_tiger_market(market)

            ticks = self._quote_client.get_trade_ticks(
                symbols=[symbol],
                market=tiger_market,
                limit=limit,
                begin_index=begin_index
            )

            if ticks is None or ticks.empty:
                return None

            return ticks

        except Exception as e:
            logger.warning(f"[Tiger] get_trade_ticks failed for {symbol}: {e}")
            return None

    def get_timeline(self, symbol: str) -> Optional[pd.DataFrame]:
        """
        Get intraday minute-level data for the current/most recent trading day.

        Returns:
            DataFrame with columns: time, price, avg_price, volume
        """
        if not self._ensure_initialized():
            return None

        try:
            market = get_market_for_symbol(symbol)
            tiger_market = self._get_tiger_market(market)

            timeline = self._quote_client.get_timeline(
                symbols=[symbol],
                market=tiger_market,
                include_hour_trading=True
            )

            if timeline is None or timeline.empty:
                return None

            return timeline

        except Exception as e:
            logger.warning(f"[Tiger] get_timeline failed for {symbol}: {e}")
            return None

    def get_capital_flow(self, symbol: str, period: str = "intraday") -> Optional[Dict[str, Any]]:
        """
        Get capital flow data (net inflow by size segment).

        Args:
            symbol: Stock symbol
            period: "intraday", "day", "week", "month"

        Returns:
            Dict with net_inflow values by segment (super_large, large, medium, small)
        """
        if not self._ensure_initialized():
            return None

        try:
            market = get_market_for_symbol(symbol)
            tiger_market = self._get_tiger_market(market)

            flow = self._quote_client.get_capital_flow(
                symbol=symbol,
                market=tiger_market,
                period=period
            )

            if flow is None or flow.empty:
                return None

            row = flow.iloc[0]
            return {
                "symbol": symbol,
                "period": period,
                "net_inflow": safe_float(row.get("net_inflow")),
                "super_large_net": safe_float(row.get("super_large_net")),
                "large_net": safe_float(row.get("large_net")),
                "medium_net": safe_float(row.get("medium_net")),
                "small_net": safe_float(row.get("small_net")),
            }

        except Exception as e:
            logger.warning(f"[Tiger] get_capital_flow failed for {symbol}: {e}")
            return None

    def get_capital_distribution(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get capital distribution by size segment.

        Returns:
            Dict with in/out amounts by segment
        """
        if not self._ensure_initialized():
            return None

        try:
            market = get_market_for_symbol(symbol)
            tiger_market = self._get_tiger_market(market)

            dist = self._quote_client.get_capital_distribution(
                symbol=symbol,
                market=tiger_market
            )

            if dist is None or dist.empty:
                return None

            row = dist.iloc[0]
            return {
                "symbol": symbol,
                "super_large_in": safe_float(row.get("super_large_in")),
                "super_large_out": safe_float(row.get("super_large_out")),
                "large_in": safe_float(row.get("large_in")),
                "large_out": safe_float(row.get("large_out")),
                "medium_in": safe_float(row.get("medium_in")),
                "medium_out": safe_float(row.get("medium_out")),
                "small_in": safe_float(row.get("small_in")),
                "small_out": safe_float(row.get("small_out")),
            }

        except Exception as e:
            logger.warning(f"[Tiger] get_capital_distribution failed for {symbol}: {e}")
            return None

    def get_kline_by_page(
        self,
        symbol: str,
        period: str = "day",
        page_token: Optional[str] = None,
        limit: int = 1000
    ) -> Optional[Dict[str, Any]]:
        """
        Get paginated K-line data for extended historical periods.

        Args:
            symbol: Stock symbol
            period: "day", "week", "month", "year", "1min", "5min", etc.
            page_token: Token for next page (from previous response)
            limit: Number of bars per page (max 1200)

        Returns:
            Dict with 'bars' DataFrame and 'next_page_token'
        """
        if not self._ensure_initialized():
            return None

        try:
            # Map period string to BarPeriod
            period_map = {
                "1min": BarPeriod.ONE_MINUTE,
                "5min": BarPeriod.FIVE_MINUTES,
                "15min": BarPeriod.FIFTEEN_MINUTES,
                "30min": BarPeriod.HALF_HOUR,
                "1hour": BarPeriod.ONE_HOUR,
                "day": BarPeriod.DAY,
                "week": BarPeriod.WEEK,
                "month": BarPeriod.MONTH,
                "year": BarPeriod.YEAR,
            }
            bar_period = period_map.get(period, BarPeriod.DAY)

            # Note: get_bars_by_page doesn't accept market param - infers from symbol
            result = self._quote_client.get_bars_by_page(
                symbol=symbol,
                period=bar_period,
                page_token=page_token,
                limit=min(limit, 1200)
            )

            if result is None:
                return None

            bars_df = result.get("bars")
            next_token = result.get("next_page_token")

            if bars_df is None or bars_df.empty:
                return None

            return {
                "bars": bars_df,
                "next_page_token": next_token,
                "has_more": next_token is not None
            }

        except Exception as e:
            logger.warning(f"[Tiger] get_kline_by_page failed for {symbol}: {e}")
            return None

    def get_warrant_filter(
        self,
        underlying_symbol: str,
        page: int = 0,
        page_size: int = 50,
        sort_field: str = "expireDate",
        sort_asc: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Get filtered warrant/CBBC list for an underlying stock.
        (Hong Kong market)

        Returns:
            Dict with 'items' DataFrame, 'total_count', 'total_page'
        """
        if not self._ensure_initialized():
            return None

        try:
            from tigeropen.common.consts import SortDirection

            result = self._quote_client.get_warrant_filter(
                symbol=underlying_symbol,
                page=page,
                page_size=page_size,
                sort_field_name=sort_field,
                sort_dir=SortDirection.ASC if sort_asc else SortDirection.DESC
            )

            if result is None:
                return None

            return {
                "items": result.items if hasattr(result, 'items') else pd.DataFrame(),
                "total_count": getattr(result, 'total_count', 0),
                "total_page": getattr(result, 'total_page', 0),
                "page": page,
            }

        except Exception as e:
            logger.warning(f"[Tiger] get_warrant_filter failed for {underlying_symbol}: {e}")
            return None

    def get_warrant_briefs(self, warrant_symbols: List[str]) -> Optional[pd.DataFrame]:
        """
        Get real-time warrant quotes.

        Args:
            warrant_symbols: List of warrant codes (max 50)

        Returns:
            DataFrame with warrant data including strike, expiry, implied_volatility, delta, etc.
        """
        if not self._ensure_initialized():
            return None

        if len(warrant_symbols) > 50:
            warrant_symbols = warrant_symbols[:50]

        try:
            briefs = self._quote_client.get_warrant_briefs(symbols=warrant_symbols)

            if briefs is None or briefs.empty:
                return None

            return briefs

        except Exception as e:
            logger.warning(f"[Tiger] get_warrant_briefs failed: {e}")
            return None

    def get_trading_calendar(
        self,
        market: Market = Market.US,
        begin_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """
        Get trading calendar with open/close times.

        Returns:
            DataFrame with trading dates and market hours
        """
        if not self._ensure_initialized():
            return None

        try:
            tiger_market = self._get_tiger_market(market)

            calendar = self._quote_client.get_trading_calendar(
                market=tiger_market,
                begin_date=begin_date,
                end_date=end_date
            )

            if calendar is None or calendar.empty:
                return None

            return calendar

        except Exception as e:
            logger.warning(f"[Tiger] get_trading_calendar failed: {e}")
            return None

    def get_all_symbols(self, market: Market = Market.US, include_otc: bool = False) -> Optional[List[str]]:
        """
        Get all available symbols for a market.

        Returns:
            List of symbol strings
        """
        if not self._ensure_initialized():
            return None

        try:
            tiger_market = self._get_tiger_market(market)

            symbols = self._quote_client.get_symbols(
                market=tiger_market,
                include_otc=include_otc
            )

            if symbols is None or symbols.empty:
                return None

            if 'symbol' in symbols.columns:
                return symbols['symbol'].tolist()
            return symbols.iloc[:, 0].tolist()

        except Exception as e:
            logger.warning(f"[Tiger] get_all_symbols failed: {e}")
            return None

    def get_margin_rate(self, symbol: str, market: Optional[Market] = None) -> Optional[float]:
        """
        Get margin requirement rate for a symbol.

        Returns:
            Margin rate as a decimal (e.g., 0.25 for 25% margin requirement),
            or None if unavailable.
        """
        if not self._ensure_initialized():
            return None

        if market is None:
            market = get_market_for_symbol(symbol)

        try:
            stock_data = self._quote_client.get_stock_briefs([symbol])

            if stock_data is not None and not stock_data.empty:
                # Try margin_rate column first
                if 'margin_rate' in stock_data.columns:
                    margin_rate = stock_data['margin_rate'].iloc[0]
                    if pd.notna(margin_rate) and margin_rate > 0:
                        return float(margin_rate)
                # Try margin_requirement column as fallback
                elif 'margin_requirement' in stock_data.columns:
                    margin_req = stock_data['margin_requirement'].iloc[0]
                    if pd.notna(margin_req):
                        # Convert percentage to decimal if needed
                        if margin_req > 1:
                            return float(margin_req) / 100.0
                        return float(margin_req)
            return None

        except Exception as e:
            logger.warning(f"[Tiger] get_margin_rate failed for {symbol}: {e}")
            return None

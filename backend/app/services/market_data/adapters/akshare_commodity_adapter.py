"""
AkShare Commodity Options Adapter

Provides commodity futures options data via akshare (Sina API backend).
Supports: Au(黄金), Ag(白银), Cu(沪铜), Al(沪铝), M(豆粕)

Core akshare functions used:
- option_commodity_contract_sina(symbol)  → contract list
- option_commodity_contract_table_sina(symbol, contract)  → options chain
- option_commodity_hist_sina(symbol)  → historical data
"""

import logging
import re
from datetime import datetime, date
from typing import Optional, List, Dict, Any

import pandas as pd

from .base import BaseAdapter
from ..interfaces import (
    DataProviderAdapter, DataType, Market, ProviderStatus,
    QuoteData, FundamentalsData, CompanyInfo, HistoryData,
    OptionsChainData, EarningsData,
)

logger = logging.getLogger(__name__)


class AkShareCommodityAdapter(BaseAdapter, DataProviderAdapter):
    """
    Adapter for commodity futures options data via akshare (Sina API).

    Supports 5 commodity products:
    - au (黄金期权) - SHFE, multiplier 1000g
    - ag (白银期权) - SHFE, multiplier 15kg
    - cu (沪铜期权) - SHFE, multiplier 5t
    - al (沪铝期权) - SHFE, multiplier 5t
    - m  (豆粕期权) - DCE, multiplier 10t
    """

    # Product code → akshare Chinese name parameter
    PRODUCT_CN_MAP = {
        'au': '黄金期权',
        'ag': '白银期权',
        'cu': '沪铜期权',
        'al': '沪铝期权',
        'm': '豆粕期权',
    }

    # Product code → contract multiplier
    PRODUCT_MULTIPLIER = {
        'au': 1000,
        'ag': 15,
        'cu': 5,
        'al': 5,
        'm': 10,
    }

    # Product code → exchange
    PRODUCT_EXCHANGE = {
        'au': 'SHFE',
        'ag': 'SHFE',
        'cu': 'SHFE',
        'al': 'SHFE',
        'm': 'DCE',
    }

    # Product code → Chinese display name
    PRODUCT_DISPLAY_NAME = {
        'au': '黄金',
        'ag': '白银',
        'cu': '沪铜',
        'al': '沪铝',
        'm': '豆粕',
    }

    def __init__(self):
        super().__init__(cooldown_seconds=60, max_failures=5)
        self._ak = None
        self._init_error = None
        try:
            import akshare as ak
            self._ak = ak
            logger.info("[AkShareCommodity] akshare loaded successfully")
        except ImportError:
            self._init_error = "akshare not installed"
            logger.warning("[AkShareCommodity] akshare not available")

    @property
    def name(self) -> str:
        return "akshare_commodity"

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
        return [Market.COMMODITY]

    def supports_symbol(self, symbol: str) -> bool:
        """Check if this adapter supports the given symbol."""
        product = self._extract_product(symbol)
        return product in self.PRODUCT_CN_MAP

    # ─────────────────────────────────────────────────────────────
    # Symbol parsing helpers
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_product(symbol: str) -> str:
        """Extract product code from symbol. E.g. 'au2604' → 'au', 'SHFE.au2604' → 'au'."""
        s = symbol.lower().strip()
        if '.' in s:
            parts = s.split('.')
            if parts[0] in ('shfe', 'dce', 'czce', 'ine'):
                s = parts[1]
        return ''.join(c for c in s if c.isalpha())

    @staticmethod
    def _extract_contract(symbol: str) -> Optional[str]:
        """Extract contract code from symbol. E.g. 'au2604' → 'au2604', 'au' → None."""
        s = symbol.lower().strip()
        if '.' in s:
            parts = s.split('.')
            if parts[0] in ('shfe', 'dce', 'czce', 'ine'):
                s = parts[1]
        # Must contain digits to be a specific contract
        if any(c.isdigit() for c in s):
            return s
        return None

    # ─────────────────────────────────────────────────────────────
    # Options Expirations (contract list)
    # ─────────────────────────────────────────────────────────────

    def get_options_expirations(self, symbol: str) -> Optional[List[str]]:
        """
        Get available contract months for a commodity product.

        Returns contract codes (e.g. ['au2506', 'au2507', ...]) sorted by
        open interest descending (first = dominant contract).
        """
        if not self._ak or self.is_rate_limited():
            return None

        product = self._extract_product(symbol)
        cn_name = self.PRODUCT_CN_MAP.get(product)
        if not cn_name:
            return None

        try:
            df = self._ak.option_commodity_contract_sina(symbol=cn_name)
            if df is None or df.empty:
                return None

            # df has columns ['序号', '合约'] — use '合约' column for contract codes
            if '合约' in df.columns:
                contracts = df['合约'].tolist()
            else:
                # Fallback: use last column (skip sequence number column)
                contracts = df.iloc[:, -1].tolist() if len(df.columns) >= 1 else []
            contracts = [str(c).strip() for c in contracts if c]

            if not contracts:
                return None

            self._handle_success()
            logger.info(f"[AkShareCommodity] {product}: {len(contracts)} contracts found")
            return contracts

        except Exception as e:
            self._handle_error(e, symbol)
            logger.warning(f"[AkShareCommodity] get_options_expirations failed for {symbol}: {e}")
            return None

    # ─────────────────────────────────────────────────────────────
    # Options Chain
    # ─────────────────────────────────────────────────────────────

    def get_options_chain(self, symbol: str, expiry: str) -> Optional[OptionsChainData]:
        """
        Get options chain for a specific contract.

        Args:
            symbol: Product symbol (e.g. 'au')
            expiry: Contract code (e.g. 'au2604') - acts as "expiry" for commodity options

        Returns:
            OptionsChainData with standardized calls and puts DataFrames
        """
        if not self._ak or self.is_rate_limited():
            return None

        product = self._extract_product(symbol)
        cn_name = self.PRODUCT_CN_MAP.get(product)
        if not cn_name:
            return None

        # expiry is the contract code for commodity options
        contract = expiry

        try:
            df = self._ak.option_commodity_contract_table_sina(symbol=cn_name, contract=contract)
            if df is None or df.empty:
                return None

            calls_df, puts_df, underlying_price = self._parse_option_table(df, product)

            self._handle_success()
            logger.info(
                f"[AkShareCommodity] {contract}: "
                f"{len(calls_df)} calls, {len(puts_df)} puts, "
                f"underlying≈{underlying_price}"
            )

            return OptionsChainData(
                symbol=product,
                expiry_date=contract,  # contract code serves as expiry identifier
                underlying_price=underlying_price,
                calls=calls_df,
                puts=puts_df,
                source="akshare_commodity",
            )

        except Exception as e:
            self._handle_error(e, symbol)
            logger.warning(f"[AkShareCommodity] get_options_chain failed for {contract}: {e}")
            return None

    def _parse_option_table(self, df: pd.DataFrame, product: str):
        """
        Parse the akshare option table into standardized calls/puts DataFrames.

        The akshare table has columns like:
        看涨合约-买量, 看涨合约-买价, 看涨合约-最新价, 看涨合约-卖价, 看涨合约-卖量,
        看涨合约-持仓量, 看涨合约-涨跌, 看涨合约-看涨期权合约,
        行权价,
        看跌合约-买量, 看跌合约-买价, 看跌合约-最新价, 看跌合约-卖价, 看跌合约-卖量,
        看跌合约-持仓量, 看跌合约-涨跌, 看跌合约-看跌期权合约
        """
        columns = list(df.columns)

        # Find strike column
        strike_col = None
        for col in columns:
            if '行权价' in str(col):
                strike_col = col
                break

        if strike_col is None:
            logger.warning("[AkShareCommodity] Cannot find strike column in data")
            return pd.DataFrame(), pd.DataFrame(), 0.0

        # Build calls DataFrame
        calls_data = []
        puts_data = []

        for _, row in df.iterrows():
            strike = self._safe_float(row.get(strike_col))
            if strike is None or strike <= 0:
                continue

            # Parse call side
            call_entry = self._parse_option_side(row, columns, '看涨', strike)
            if call_entry:
                calls_data.append(call_entry)

            # Parse put side
            put_entry = self._parse_option_side(row, columns, '看跌', strike)
            if put_entry:
                puts_data.append(put_entry)

        calls_df = pd.DataFrame(calls_data) if calls_data else pd.DataFrame()
        puts_df = pd.DataFrame(puts_data) if puts_data else pd.DataFrame()

        # Estimate underlying price from ATM strike (where call ≈ put price)
        underlying_price = self._estimate_underlying_price(calls_data, puts_data)

        return calls_df, puts_df, underlying_price

    def _parse_option_side(self, row, columns: list, side_prefix: str, strike: float) -> Optional[Dict]:
        """Parse one side (call or put) of the option table row."""
        def find_col(keyword: str) -> Optional[str]:
            for col in columns:
                col_str = str(col)
                if side_prefix in col_str and keyword in col_str:
                    return col
            return None

        bid_col = find_col('买价')
        ask_col = find_col('卖价')
        last_col = find_col('最新价')
        bid_vol_col = find_col('买量')
        ask_vol_col = find_col('卖量')
        oi_col = find_col('持仓量')
        contract_col = find_col('期权合约')

        bid = self._safe_float(row.get(bid_col)) if bid_col else None
        ask = self._safe_float(row.get(ask_col)) if ask_col else None
        last_price = self._safe_float(row.get(last_col)) if last_col else None
        bid_vol = self._safe_int(row.get(bid_vol_col)) if bid_vol_col else 0
        ask_vol = self._safe_int(row.get(ask_vol_col)) if ask_vol_col else 0
        open_interest = self._safe_int(row.get(oi_col)) if oi_col else 0
        contract_name = str(row.get(contract_col, '')) if contract_col else ''

        # Volume = bid_vol + ask_vol
        volume = (bid_vol or 0) + (ask_vol or 0)

        return {
            'strike': strike,
            'bid': bid or 0.0,
            'ask': ask or 0.0,
            'lastPrice': last_price or 0.0,
            'volume': volume,
            'openInterest': open_interest or 0,
            'contractName': contract_name,
        }

    def _estimate_underlying_price(self, calls_data: list, puts_data: list) -> float:
        """Estimate underlying futures price from options data (put-call parity at ATM)."""
        if not calls_data or not puts_data:
            return 0.0

        # Find the strike where |call_price - put_price| is minimized (ATM)
        calls_by_strike = {c['strike']: c['lastPrice'] for c in calls_data if c['lastPrice'] > 0}
        puts_by_strike = {p['strike']: p['lastPrice'] for p in puts_data if p['lastPrice'] > 0}

        min_diff = float('inf')
        atm_strike = 0.0

        for strike in calls_by_strike:
            if strike in puts_by_strike:
                diff = abs(calls_by_strike[strike] - puts_by_strike[strike])
                if diff < min_diff:
                    min_diff = diff
                    atm_strike = strike

        if atm_strike > 0:
            # Approximate: underlying ≈ strike + call - put
            call_p = calls_by_strike.get(atm_strike, 0)
            put_p = puts_by_strike.get(atm_strike, 0)
            return atm_strike + call_p - put_p

        # Fallback: use median strike
        all_strikes = [c['strike'] for c in calls_data if c['strike'] > 0]
        if all_strikes:
            return sorted(all_strikes)[len(all_strikes) // 2]

        return 0.0

    # ─────────────────────────────────────────────────────────────
    # Quote (underlying futures price)
    # ─────────────────────────────────────────────────────────────

    def get_quote(self, symbol: str) -> Optional[QuoteData]:
        """
        Get quote for the commodity underlying via its dominant contract.
        """
        if not self._ak or self.is_rate_limited():
            return None

        product = self._extract_product(symbol)
        cn_name = self.PRODUCT_CN_MAP.get(product)
        if not cn_name:
            return None

        try:
            # Get contracts and use first (dominant) contract
            contracts = self.get_options_expirations(symbol)
            if not contracts:
                return None

            dominant = contracts[0]
            chain = self.get_options_chain(symbol, dominant)
            if chain is None or chain.underlying_price <= 0:
                return None

            return QuoteData(
                symbol=product,
                current_price=chain.underlying_price,
                source="akshare_commodity",
            )

        except Exception as e:
            self._handle_error(e, symbol)
            logger.warning(f"[AkShareCommodity] get_quote failed for {symbol}: {e}")
            return None

    # ─────────────────────────────────────────────────────────────
    # History
    # ─────────────────────────────────────────────────────────────

    def get_history(
        self,
        symbol: str,
        period: Optional[str] = None,
        start: Optional[date] = None,
        end: Optional[date] = None,
    ) -> Optional[HistoryData]:
        """Get historical data for a commodity option product."""
        if not self._ak or self.is_rate_limited():
            return None

        product = self._extract_product(symbol)
        cn_name = self.PRODUCT_CN_MAP.get(product)
        if not cn_name:
            return None

        try:
            df = self._ak.option_commodity_hist_sina(symbol=cn_name)
            if df is None or df.empty:
                return None

            # Normalize column names
            col_map = {}
            for col in df.columns:
                col_lower = str(col).lower()
                if '日期' in str(col) or 'date' in col_lower:
                    col_map[col] = 'Date'
                elif '开盘' in str(col) or 'open' in col_lower:
                    col_map[col] = 'Open'
                elif '最高' in str(col) or 'high' in col_lower:
                    col_map[col] = 'High'
                elif '最低' in str(col) or 'low' in col_lower:
                    col_map[col] = 'Low'
                elif '收盘' in str(col) or 'close' in col_lower:
                    col_map[col] = 'Close'
                elif '成交量' in str(col) or 'volume' in col_lower:
                    col_map[col] = 'Volume'

            if col_map:
                df = df.rename(columns=col_map)

            # Set date index if available
            if 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'])
                df = df.set_index('Date')
                df = df.sort_index()

            # Ensure numeric columns
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            self._handle_success()
            return HistoryData(
                symbol=product,
                df=df,
                period=period,
                source="akshare_commodity",
            )

        except Exception as e:
            self._handle_error(e, symbol)
            logger.warning(f"[AkShareCommodity] get_history failed for {symbol}: {e}")
            return None

    # ─────────────────────────────────────────────────────────────
    # Not supported for commodities
    # ─────────────────────────────────────────────────────────────

    def get_info(self, symbol: str) -> Optional[CompanyInfo]:
        product = self._extract_product(symbol)
        display_name = self.PRODUCT_DISPLAY_NAME.get(product, product)
        exchange = self.PRODUCT_EXCHANGE.get(product, '')
        return CompanyInfo(
            symbol=product,
            name=f"{display_name}期权",
            sector="Commodities",
            industry="Futures Options",
            country="China",
            currency="CNY",
            exchange=exchange,
            source="akshare_commodity",
        )

    def get_fundamentals(self, symbol: str) -> Optional[FundamentalsData]:
        return None

    def get_earnings(self, symbol: str) -> Optional[EarningsData]:
        return None

    # ─────────────────────────────────────────────────────────────
    # Utility
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def _safe_float(val) -> Optional[float]:
        if val is None:
            return None
        try:
            f = float(val)
            if pd.isna(f):
                return None
            return f
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _safe_int(val) -> int:
        if val is None:
            return 0
        try:
            i = int(float(val))
            return i if not pd.isna(float(val)) else 0
        except (ValueError, TypeError):
            return 0

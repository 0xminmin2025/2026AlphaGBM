"""
Mock market data fixtures for MarketDataService testing.

Provides:
- Mock DataProviderAdapter implementations for unit testing
- Pre-configured MarketDataService with mock adapters
- Macro / market-level data fixtures (VIX, Treasury yields, indices)
- Multi-market sample data (US, HK, CN)
"""
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from typing import Optional, List
from unittest.mock import MagicMock

from tests.fixtures.mock_stock_data import (
    AAPL_QUOTE, AAPL_FUNDAMENTALS, AAPL_INFO,
    make_aapl_history_df,
)


# ---------------------------------------------------------------------------
# Macro / index data
# ---------------------------------------------------------------------------

VIX_DATA = {
    'symbol': '^VIX',
    'current_price': 16.45,
    'previous_close': 15.92,
    'day_high': 17.10,
    'day_low': 15.80,
    'timestamp': datetime(2026, 2, 7, 16, 0, 0),
}

TREASURY_10Y = {
    'symbol': '^TNX',
    'current_price': 4.28,
    'previous_close': 4.25,
    'day_high': 4.32,
    'day_low': 4.22,
    'timestamp': datetime(2026, 2, 7, 16, 0, 0),
}

SP500_DATA = {
    'symbol': '^GSPC',
    'current_price': 5025.40,
    'previous_close': 4998.30,
    'open_price': 5002.10,
    'day_high': 5032.80,
    'day_low': 4995.60,
    'volume': 3_800_000_000,
    'timestamp': datetime(2026, 2, 7, 16, 0, 0),
}

NASDAQ_DATA = {
    'symbol': '^IXIC',
    'current_price': 15_832.50,
    'previous_close': 15_705.20,
    'open_price': 15_720.00,
    'day_high': 15_860.30,
    'day_low': 15_690.40,
    'volume': 5_200_000_000,
    'timestamp': datetime(2026, 2, 7, 16, 0, 0),
}


# ---------------------------------------------------------------------------
# Multi-market sample symbols
# ---------------------------------------------------------------------------

HK_TENCENT_QUOTE = {
    'symbol': '0700.HK',
    'current_price': 368.60,
    'previous_close': 365.20,
    'open_price': 366.00,
    'day_high': 370.40,
    'day_low': 364.80,
    'volume': 12_500_000,
    'market_cap': 3_470_000_000_000,
    'timestamp': datetime(2026, 2, 7, 16, 0, 0),
    'source': 'test',
}

HK_TENCENT_INFO = {
    'symbol': '0700.HK',
    'name': 'Tencent Holdings Limited',
    'sector': 'Communication Services',
    'industry': 'Internet Content & Information',
    'country': 'China',
    'currency': 'HKD',
    'exchange': 'HKG',
    'source': 'test',
}

CN_MOUTAI_QUOTE = {
    'symbol': '600519.SS',
    'current_price': 1680.00,
    'previous_close': 1672.50,
    'open_price': 1675.00,
    'day_high': 1690.00,
    'day_low': 1670.00,
    'volume': 3_200_000,
    'market_cap': 2_110_000_000_000,
    'timestamp': datetime(2026, 2, 7, 15, 0, 0),
    'source': 'test',
}

CN_MOUTAI_INFO = {
    'symbol': '600519.SS',
    'name': 'Kweichow Moutai Co., Ltd.',
    'sector': 'Consumer Staples',
    'industry': 'Beverages - Wineries & Distilleries',
    'country': 'China',
    'currency': 'CNY',
    'exchange': 'SSE',
    'source': 'test',
}


# ---------------------------------------------------------------------------
# Mock DataProviderAdapter for testing
# ---------------------------------------------------------------------------

def make_mock_adapter(
    name: str = 'mock_provider',
    supported_markets: list = None,
    supported_data_types: list = None,
    healthy: bool = True,
    rate_limited: bool = False,
    quote_data: dict = None,
    fundamentals_data: dict = None,
    info_data: dict = None,
    history_df: pd.DataFrame = None,
):
    """
    Create a MagicMock that conforms to the DataProviderAdapter interface.

    This allows plugging mock adapters into MarketDataService for isolated testing.

    Args:
        name: Provider name.
        supported_markets: List of Market enums.
        supported_data_types: List of DataType enums.
        healthy: Whether health_check returns HEALTHY.
        rate_limited: Whether is_rate_limited returns True.
        quote_data: Dict to build QuoteData return value (None -> returns None).
        fundamentals_data: Dict to build FundamentalsData return value.
        info_data: Dict to build CompanyInfo return value.
        history_df: DataFrame to build HistoryData return value.

    Returns:
        MagicMock conforming to DataProviderAdapter.
    """
    from app.services.market_data.interfaces import (
        DataType, Market, ProviderStatus,
        QuoteData, FundamentalsData, CompanyInfo, HistoryData,
    )

    if supported_markets is None:
        supported_markets = [Market.US]
    if supported_data_types is None:
        supported_data_types = [
            DataType.QUOTE, DataType.HISTORY,
            DataType.INFO, DataType.FUNDAMENTALS,
        ]

    adapter = MagicMock()
    adapter.name = name
    adapter.supported_markets = supported_markets
    adapter.supported_data_types = supported_data_types
    adapter.is_rate_limited.return_value = rate_limited
    adapter.supports_symbol.return_value = True

    if healthy:
        adapter.health_check.return_value = ProviderStatus.HEALTHY
    else:
        adapter.health_check.return_value = ProviderStatus.UNAVAILABLE

    # Quote
    if quote_data:
        adapter.get_quote.return_value = QuoteData(**quote_data)
    else:
        adapter.get_quote.return_value = None

    # Fundamentals
    if fundamentals_data:
        adapter.get_fundamentals.return_value = FundamentalsData(**fundamentals_data)
    else:
        adapter.get_fundamentals.return_value = None

    # Info
    if info_data:
        adapter.get_info.return_value = CompanyInfo(**info_data)
    else:
        adapter.get_info.return_value = None

    # History
    if history_df is not None:
        adapter.get_history.return_value = HistoryData(
            symbol=quote_data['symbol'] if quote_data else 'AAPL',
            df=history_df,
            period='30d',
            source=name,
        )
    else:
        adapter.get_history.return_value = None

    # Options (default: None)
    adapter.get_options_expirations.return_value = None
    adapter.get_options_chain.return_value = None
    adapter.get_earnings.return_value = None

    return adapter


def make_aapl_mock_adapter(name: str = 'mock_yfinance') -> MagicMock:
    """Convenience: create a mock adapter pre-loaded with AAPL data."""
    return make_mock_adapter(
        name=name,
        quote_data=AAPL_QUOTE,
        fundamentals_data=AAPL_FUNDAMENTALS,
        info_data=AAPL_INFO,
        history_df=make_aapl_history_df(30),
    )


def make_failing_adapter(name: str = 'failing_provider', error_msg: str = 'Provider unavailable'):
    """
    Create a mock adapter that raises exceptions for all data fetch methods.
    Useful for testing fallback/failover behavior.
    """
    from app.services.market_data.interfaces import DataType, Market, ProviderStatus

    adapter = MagicMock()
    adapter.name = name
    adapter.supported_markets = [Market.US]
    adapter.supported_data_types = [
        DataType.QUOTE, DataType.HISTORY,
        DataType.INFO, DataType.FUNDAMENTALS,
    ]
    adapter.is_rate_limited.return_value = False
    adapter.supports_symbol.return_value = True
    adapter.health_check.return_value = ProviderStatus.UNAVAILABLE

    error = Exception(error_msg)
    adapter.get_quote.side_effect = error
    adapter.get_history.side_effect = error
    adapter.get_info.side_effect = error
    adapter.get_fundamentals.side_effect = error
    adapter.get_options_expirations.side_effect = error
    adapter.get_options_chain.side_effect = error
    adapter.get_earnings.side_effect = error

    return adapter


def make_rate_limited_adapter(name: str = 'rate_limited_provider'):
    """Create a mock adapter that reports itself as rate-limited."""
    from app.services.market_data.interfaces import DataType, Market, ProviderStatus

    adapter = MagicMock()
    adapter.name = name
    adapter.supported_markets = [Market.US]
    adapter.supported_data_types = [
        DataType.QUOTE, DataType.HISTORY,
        DataType.INFO, DataType.FUNDAMENTALS,
    ]
    adapter.is_rate_limited.return_value = True
    adapter.supports_symbol.return_value = True
    adapter.health_check.return_value = ProviderStatus.RATE_LIMITED

    # Even though rate-limited, the service may still try as last resort
    adapter.get_quote.return_value = None
    adapter.get_history.return_value = None
    adapter.get_info.return_value = None
    adapter.get_fundamentals.return_value = None

    return adapter


# ---------------------------------------------------------------------------
# Market summary / snapshot for dashboard tests
# ---------------------------------------------------------------------------

MARKET_SUMMARY = {
    'timestamp': datetime(2026, 2, 7, 16, 30, 0).isoformat(),
    'indices': {
        'SP500': {'price': 5025.40, 'change_pct': 0.54},
        'NASDAQ': {'price': 15832.50, 'change_pct': 0.81},
        'DOW': {'price': 38520.10, 'change_pct': 0.32},
        'RUSSELL2000': {'price': 2045.80, 'change_pct': 0.15},
    },
    'volatility': {
        'VIX': 16.45,
        'VIX_change': 0.53,
        'VIX_level': 'low',
    },
    'treasuries': {
        '10Y': 4.28,
        '2Y': 4.55,
        'spread_2_10': -0.27,
    },
    'sentiment': {
        'fear_greed_index': 62,
        'label': 'Greed',
    },
}


# ---------------------------------------------------------------------------
# Provider status snapshots (for metrics/monitoring tests)
# ---------------------------------------------------------------------------

PROVIDER_STATUS_HEALTHY = {
    'yfinance': {
        'health': 'healthy',
        'enabled': True,
        'priority': 10,
        'rate_limited': False,
    },
    'defeatbeta': {
        'health': 'healthy',
        'enabled': True,
        'priority': 20,
        'rate_limited': False,
    },
    'tiger': {
        'health': 'healthy',
        'enabled': True,
        'priority': 15,
        'rate_limited': False,
    },
}

PROVIDER_STATUS_DEGRADED = {
    'yfinance': {
        'health': 'rate_limited',
        'enabled': True,
        'priority': 10,
        'rate_limited': True,
    },
    'defeatbeta': {
        'health': 'healthy',
        'enabled': True,
        'priority': 20,
        'rate_limited': False,
    },
    'tiger': {
        'health': 'degraded',
        'enabled': True,
        'priority': 15,
        'rate_limited': False,
    },
}

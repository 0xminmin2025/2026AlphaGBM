"""
Test script for DataProvider (yfinance + defeatbeta-api fallback).

Tests:
1. Normal yfinance path works
2. Forced defeatbeta fallback produces compatible data
3. History data format matches between both sources
4. Info dict has required fields for stock analysis
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.data_provider import DataProvider, data_provider_download
import yfinance as yf
import pandas as pd

TICKER = 'AAPL'


def test_info_normal():
    """Test .info via normal yfinance path."""
    print("=" * 60)
    print("TEST 1: DataProvider .info (yfinance primary)")
    print("=" * 60)
    dp = DataProvider(TICKER)
    info = dp.info

    critical_fields = [
        'currentPrice', 'regularMarketPrice', 'previousClose',
        'trailingPE', 'forwardPE', 'beta', 'marketCap',
        'sector', 'industry', 'profitMargins'
    ]

    for field in critical_fields:
        val = info.get(field)
        status = 'OK' if val is not None else 'MISSING'
        print(f"  {field}: {val} [{status}]")

    assert info.get('currentPrice') or info.get('regularMarketPrice'), "No price data!"
    print("  PASSED\n")


def test_info_defeatbeta():
    """Test .info via forced defeatbeta fallback."""
    print("=" * 60)
    print("TEST 2: DataProvider .info (forced defeatbeta fallback)")
    print("=" * 60)
    dp = DataProvider(TICKER)
    dp._yf_failed = True  # Force defeatbeta path
    info = dp.info

    print(f"  Total fields: {len(info)}")

    critical_fields = [
        'currentPrice', 'regularMarketPrice', 'previousClose',
        'trailingPE', 'forwardPE', 'beta', 'marketCap',
        'sector', 'industry', 'profitMargins',
        'operatingMargins', 'returnOnEquity', 'returnOnAssets',
        'revenueGrowth', 'totalRevenue', 'priceToBook',
        'priceToSalesTrailing12Months', 'fiftyTwoWeekHigh', 'fiftyTwoWeekLow',
    ]

    for field in critical_fields:
        val = info.get(field)
        status = 'OK' if val is not None else 'MISSING (gap)'
        print(f"  {field}: {val} [{status}]")

    assert info.get('currentPrice') or info.get('regularMarketPrice'), "No price from defeatbeta!"
    assert info.get('trailingPE'), "No PE from defeatbeta!"
    assert info.get('sector'), "No sector from defeatbeta!"
    print("  PASSED\n")


def test_history_normal():
    """Test .history() via normal yfinance path."""
    print("=" * 60)
    print("TEST 3: DataProvider .history() (yfinance primary)")
    print("=" * 60)
    dp = DataProvider(TICKER)
    hist = dp.history(period='1mo')

    print(f"  Shape: {hist.shape}")
    print(f"  Columns: {hist.columns.tolist()}")
    print(f"  Index type: {type(hist.index)}")
    print(f"  Last 3 rows:")
    print(hist.tail(3))

    assert not hist.empty, "History is empty!"
    assert 'Close' in hist.columns, "No Close column!"
    assert 'Volume' in hist.columns, "No Volume column!"
    print("  PASSED\n")


def test_history_defeatbeta():
    """Test .history() via forced defeatbeta fallback."""
    print("=" * 60)
    print("TEST 4: DataProvider .history() (forced defeatbeta fallback)")
    print("=" * 60)
    dp = DataProvider(TICKER)
    dp._yf_failed = True  # Force defeatbeta path
    hist = dp.history(period='1mo')

    print(f"  Shape: {hist.shape}")
    print(f"  Columns: {hist.columns.tolist()}")
    print(f"  Index type: {type(hist.index)}")
    print(f"  Last 3 rows:")
    print(hist.tail(3))

    assert not hist.empty, "defeatbeta history is empty!"
    assert 'Close' in hist.columns, "No Close column from defeatbeta!"
    assert 'Volume' in hist.columns, "No Volume column from defeatbeta!"
    print("  PASSED\n")


def test_history_with_dates():
    """Test .history() with start/end dates via defeatbeta."""
    print("=" * 60)
    print("TEST 5: DataProvider .history(start, end) (forced defeatbeta)")
    print("=" * 60)
    from datetime import datetime, timedelta

    dp = DataProvider(TICKER)
    dp._yf_failed = True

    end = datetime.now()
    start = end - timedelta(days=60)
    hist = dp.history(start=start, end=end)

    print(f"  Shape: {hist.shape}")
    print(f"  Date range: {hist.index.min()} to {hist.index.max()}")

    assert not hist.empty, "Dated history is empty!"
    assert len(hist) > 20, f"Expected >20 rows for 60 days, got {len(hist)}"
    print("  PASSED\n")


def test_quarterly_earnings():
    """Test .quarterly_earnings via defeatbeta fallback."""
    print("=" * 60)
    print("TEST 6: DataProvider .quarterly_earnings (forced defeatbeta)")
    print("=" * 60)
    dp = DataProvider(TICKER)
    dp._yf_failed = True
    earnings = dp.quarterly_earnings

    print(f"  Shape: {earnings.shape}")
    print(f"  Columns: {earnings.columns.tolist()}")
    print(earnings.tail(5))

    assert not earnings.empty, "Earnings is empty!"
    assert 'Earnings' in earnings.columns, "No Earnings column!"
    print("  PASSED\n")


def test_macro_ticker():
    """Test that macro tickers (^VIX, ^TNX) gracefully degrade."""
    print("=" * 60)
    print("TEST 7: Macro tickers (^VIX) — degrade gracefully")
    print("=" * 60)
    dp = DataProvider('^VIX')
    dp._yf_failed = True  # Force defeatbeta (which doesn't support indices)

    info = dp.info
    hist = dp.history(period='5d')

    print(f"  ^VIX info (forced defeatbeta): {len(info)} fields (expected: 0 or empty)")
    print(f"  ^VIX history (forced defeatbeta): {len(hist)} rows (expected: 0)")

    # Should NOT crash, just return empty
    print("  PASSED (no crash)\n")


def test_data_provider_download():
    """Test the yf.download replacement."""
    print("=" * 60)
    print("TEST 8: data_provider_download (yf.download replacement)")
    print("=" * 60)

    result = data_provider_download(TICKER, period='3mo')
    print(f"  Shape: {result.shape}")
    print(f"  Columns: {result.columns.tolist()}")

    assert not result.empty, "Download result is empty!"
    assert 'Close' in result.columns, "No Close column!"
    print("  PASSED\n")


def test_compare_info_fields():
    """Compare key info fields between yfinance and defeatbeta."""
    print("=" * 60)
    print("TEST 9: Compare info fields (yfinance vs defeatbeta)")
    print("=" * 60)

    # Get yfinance data
    yf_info = yf.Ticker(TICKER).info

    # Get defeatbeta data
    dp = DataProvider(TICKER)
    dp._yf_failed = True
    db_info = dp.info

    compare_fields = [
        'currentPrice', 'trailingPE', 'forwardPE', 'beta',
        'marketCap', 'sector', 'industry', 'profitMargins',
        'returnOnEquity', 'priceToBook',
    ]

    print(f"  {'Field':<35} {'yfinance':>15} {'defeatbeta':>15} {'Match':>8}")
    print(f"  {'-'*35} {'-'*15} {'-'*15} {'-'*8}")

    for field in compare_fields:
        yf_val = yf_info.get(field)
        db_val = db_info.get(field)

        # Check if values are close enough (within 5% for numeric)
        if isinstance(yf_val, (int, float)) and isinstance(db_val, (int, float)) and yf_val != 0:
            diff_pct = abs(yf_val - db_val) / abs(yf_val) * 100
            match = 'CLOSE' if diff_pct < 5 else f'{diff_pct:.1f}%'
        elif yf_val == db_val:
            match = 'EXACT'
        elif yf_val is None or db_val is None:
            match = 'GAP'
        else:
            match = 'DIFF'

        yf_str = f"{yf_val}" if yf_val is not None else "None"
        db_str = f"{db_val}" if db_val is not None else "None"

        # Truncate long values
        yf_str = yf_str[:15]
        db_str = db_str[:15]

        print(f"  {field:<35} {yf_str:>15} {db_str:>15} {match:>8}")

    print("  PASSED (comparison complete)\n")


if __name__ == '__main__':
    print("\nDataProvider Test Suite")
    print("=" * 60)
    print(f"Testing with ticker: {TICKER}\n")

    tests = [
        test_info_normal,
        test_info_defeatbeta,
        test_history_normal,
        test_history_defeatbeta,
        test_history_with_dates,
        test_quarterly_earnings,
        test_macro_ticker,
        test_data_provider_download,
        test_compare_info_fields,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  FAILED: {e}\n")
            failed += 1

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("=" * 60)

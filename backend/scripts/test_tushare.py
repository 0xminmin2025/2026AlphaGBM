#!/usr/bin/env python3
"""
Test script to verify Tushare integration for A-shares.
Run this script to diagnose A-share data retrieval issues.

Usage: python scripts/test_tushare.py
"""

import os
import sys

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

def main():
    print("=" * 60)
    print("Tushare Integration Test")
    print("=" * 60)

    # 1. Check environment variable
    token = os.environ.get("TUSHARE_TOKEN", "")
    print(f"\n[1] TUSHARE_TOKEN: {'✓ Set (' + token[:10] + '...)' if token else '✗ NOT SET'}")

    if not token:
        print("    → Please set TUSHARE_TOKEN in .env or environment")
        return False

    # 2. Check tushare module
    print("\n[2] Tushare module:")
    try:
        import tushare as ts
        print(f"    ✓ Installed (version: {ts.__version__})")
    except ImportError as e:
        print(f"    ✗ NOT INSTALLED: {e}")
        print("    → Run: pip install tushare")
        return False

    # 3. Initialize Tushare
    print("\n[3] Tushare initialization:")
    try:
        ts.set_token(token)
        pro = ts.pro_api()
        print("    ✓ Initialized successfully")
    except Exception as e:
        print(f"    ✗ Failed: {e}")
        return False

    # 4. Test A-share data retrieval
    test_stocks = [
        ("002475.SZ", "立讯精密"),
        ("600519.SH", "贵州茅台"),
        ("000001.SZ", "平安银行"),
    ]

    print("\n[4] Testing A-share data retrieval:")
    for ts_code, name in test_stocks:
        print(f"\n    Testing {ts_code} ({name}):")
        try:
            # Try daily data
            df = pro.daily(ts_code=ts_code, limit=1)
            if df is not None and not df.empty:
                row = df.iloc[0]
                print(f"      ✓ Daily: close={row['close']}, vol={row['vol']}, date={row['trade_date']}")
            else:
                print(f"      ✗ Daily: No data returned")
        except Exception as e:
            print(f"      ✗ Daily failed: {e}")

        try:
            # Try basic info
            df = pro.stock_basic(ts_code=ts_code, fields='ts_code,name,industry,market')
            if df is not None and not df.empty:
                row = df.iloc[0]
                print(f"      ✓ Info: name={row.get('name', 'N/A')}, industry={row.get('industry', 'N/A')}")
            else:
                print(f"      ✗ Info: No data returned")
        except Exception as e:
            print(f"      ✗ Info failed: {e}")

    # 5. Check TushareAdapter
    print("\n[5] TushareAdapter status:")
    try:
        from app.services.market_data.adapters.tushare_adapter import TushareAdapter, TUSHARE_AVAILABLE
        print(f"    TUSHARE_AVAILABLE: {TUSHARE_AVAILABLE}")

        adapter = TushareAdapter()
        print(f"    Adapter initialized: {adapter._initialized}")
        print(f"    Adapter name: {adapter.name}")
        print(f"    Supported markets: {adapter.supported_markets}")

        if adapter._initialized:
            # Test get_quote
            quote = adapter.get_quote("002475.SZ")
            if quote:
                print(f"    ✓ get_quote(002475.SZ): price={quote.current_price}")
            else:
                print(f"    ✗ get_quote(002475.SZ): returned None")
    except Exception as e:
        print(f"    ✗ Error: {e}")

    # 6. Check MarketDataService
    print("\n[6] MarketDataService status:")
    try:
        from app.services.market_data import get_market_data_service
        service = get_market_data_service()

        # Check registered adapters
        print(f"    Registered adapters: {list(service._adapters.keys())}")

        # Check tushare adapter in service
        tushare_adapter = service._adapters.get('tushare')
        if tushare_adapter:
            print(f"    Tushare in service: ✓ (initialized={tushare_adapter._initialized})")
        else:
            print(f"    Tushare in service: ✗ NOT REGISTERED")

        # Test full data retrieval
        print("\n    Testing full data retrieval for 002475.SZ:")
        data = service.get_ticker_data("002475.SZ")
        if data and data.get('currentPrice'):
            print(f"      ✓ Success: price={data.get('currentPrice')}, name={data.get('shortName')}")
        else:
            print(f"      ✗ Failed: {data}")
    except Exception as e:
        print(f"    ✗ Error: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("Test completed")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

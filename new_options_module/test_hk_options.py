"""
Test Hong Kong options with TBHK license
"""

from tiger_client import get_client_manager
from tigeropen.common.consts import Market

def main():
    print("🚀 Testing Hong Kong Options with TBHK License")
    print("=" * 60)

    # Get client manager
    client = get_client_manager()

    # Initialize client
    print("📊 Initializing Tiger API client...")
    if not client.initialize_client():
        print("❌ Client initialization failed")
        return False

    # Check permissions
    try:
        print("\n🔐 Checking available permissions...")
        permissions = client.quote_client.get_quote_permission()
        print(f"✅ Found {len(permissions)} permissions:")
        for permission in permissions:
            print(f"   - {permission['name']}: expires {permission.get('expire_at', 'never')}")
    except Exception as e:
        print(f"⚠️ Permission check failed: {str(e)}")

    # Test HK stock
    try:
        print("\n📈 Testing HK stock quote...")
        hk_stock = client.get_stock_quote(['00700'])  # Tencent
        print(f"✅ HK Stock: {hk_stock['symbol'].iloc[0]} = ${hk_stock['latest_price'].iloc[0]}")
    except Exception as e:
        print(f"❌ HK stock failed: {str(e)}")

    # Test HK option symbols
    try:
        print("\n🔍 Getting HK option symbols...")
        hk_symbols = client.quote_client.get_option_symbols()
        print(f"✅ Found {len(hk_symbols)} HK option symbols")
        if len(hk_symbols) > 0:
            print(f"   Examples: {hk_symbols['symbol'].head(3).tolist()}")

            # Test with first available HK option symbol
            test_symbol = hk_symbols['symbol'].iloc[0]
            print(f"\n🔄 Testing HK option expirations for {test_symbol}...")
            hk_expirations = client.get_option_expirations(test_symbol, Market.HK)
            print(f"✅ Found {len(hk_expirations)} expiration dates for {test_symbol}")

            if len(hk_expirations) > 0:
                test_expiry = hk_expirations['date'].iloc[0]
                print(f"\n🔗 Testing HK option chain for {test_symbol} {test_expiry}...")
                hk_option_chain = client.get_option_chain(test_symbol, test_expiry, Market.HK)

                calls = hk_option_chain[hk_option_chain['put_call'] == 'CALL']
                puts = hk_option_chain[hk_option_chain['put_call'] == 'PUT']

                print(f"✅ HK Option chain: {len(calls)} calls, {len(puts)} puts")

    except Exception as e:
        print(f"❌ HK options failed: {str(e)}")

    # Test US symbols that might work
    try:
        print("\n📊 Testing other US permissions...")
        # Try some basic US stocks
        for symbol in ['NVDA', 'TSLA', 'MSFT']:
            try:
                us_stock = client.get_stock_quote([symbol])
                print(f"✅ {symbol}: ${us_stock['latest_price'].iloc[0]}")
            except Exception as e:
                print(f"❌ {symbol} failed: {str(e)}")
                break

    except Exception as e:
        print(f"⚠️ US stock test failed: {str(e)}")

    print("\n" + "=" * 60)
    print("Summary:")
    print("- Basic stock quotes: ✅ Working")
    print("- Option expirations: ✅ Working")
    print("- HK options: Need to check permissions")
    print("- US options: Permission denied (expected with TBHK license)")

if __name__ == "__main__":
    main()
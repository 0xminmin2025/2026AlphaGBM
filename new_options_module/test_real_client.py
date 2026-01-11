"""
Test real Tiger API client for option service
"""

from tiger_client import get_client_manager
from tigeropen.common.consts import Market

def main():
    print("🚀 Testing Real Tiger API Client for Option Service")
    print("=" * 60)

    # Get client manager
    client = get_client_manager()

    # Initialize client
    print("📊 Initializing Tiger API client...")
    if not client.initialize_client():
        print("❌ Client initialization failed")
        return False

    # Test stock quote
    try:
        print("\n📈 Testing stock quote...")
        stock_data = client.get_stock_quote(['AAPL'])
        print(f"✅ Stock quote: {stock_data['symbol'].iloc[0]} = ${stock_data['latest_price'].iloc[0]}")
        print(f"   Volume: {stock_data['volume'].iloc[0]:,}")
    except Exception as e:
        print(f"❌ Stock quote failed: {str(e)}")
        return False

    # Test option expirations
    try:
        print("\n🔄 Testing option expirations...")
        expirations = client.get_option_expirations('AAPL', Market.US)
        print(f"✅ Found {len(expirations)} expiration dates for AAPL")
        if len(expirations) > 0:
            print(f"   Next expiry: {expirations['date'].iloc[0]}")
            print(f"   Period: {expirations['period_tag'].iloc[0]}")
    except Exception as e:
        print(f"❌ Option expirations failed: {str(e)}")
        return False

    # Test option chain (with first available expiry)
    try:
        if len(expirations) > 0:
            test_expiry = expirations['date'].iloc[0]
            print(f"\n🔗 Testing option chain for {test_expiry}...")
            option_chain = client.get_option_chain('AAPL', test_expiry, Market.US)

            calls = option_chain[option_chain['put_call'] == 'CALL']
            puts = option_chain[option_chain['put_call'] == 'PUT']

            print(f"✅ Option chain loaded: {len(calls)} calls, {len(puts)} puts")

            if len(calls) > 0:
                print(f"   Sample CALL: Strike ${calls['strike'].iloc[0]} = ${calls['latest_price'].iloc[0]}")
            if len(puts) > 0:
                print(f"   Sample PUT: Strike ${puts['strike'].iloc[0]} = ${puts['latest_price'].iloc[0]}")
    except Exception as e:
        print(f"❌ Option chain failed: {str(e)}")
        return False

    print("\n🎉 ALL TESTS PASSED! Tiger API client ready for option service.")
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ Ready to use real Tiger API data in option service!")
    else:
        print("\n❌ Issues detected, may need to fall back to mock data")
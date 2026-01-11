"""
Test real Tiger API Hong Kong option data
"""

from tiger_client import get_client_manager
from tigeropen.common.consts import Market

def main():
    print("🚀 Testing Real Tiger API Hong Kong Option Data")
    print("=" * 60)

    # Get client manager
    client = get_client_manager()

    # Initialize client
    print("📊 Initializing Tiger API client...")
    if not client.initialize_client():
        print("❌ Client initialization failed")
        return False

    # Get HK option symbols first
    try:
        print("\n🔍 Getting HK option symbols...")
        hk_symbols = client.quote_client.get_option_symbols(market=Market.HK)
        print(f"✅ Found {len(hk_symbols)} HK option symbols")

        if len(hk_symbols) > 0:
            # Test with first available symbol
            test_symbol = hk_symbols['symbol'].iloc[0]
            underlying = hk_symbols['underlying_symbol'].iloc[0]
            print(f"📍 Testing with: {test_symbol} (underlying: {underlying})")

            # Get expirations
            print(f"\n📅 Getting {test_symbol} option expirations...")
            expirations = client.get_option_expirations(test_symbol, Market.HK)
            print(f"✅ Found {len(expirations)} expiration dates")

            if len(expirations) > 0:
                test_expiry = expirations['date'].iloc[0]
                print(f"📍 Testing with expiry: {test_expiry}")

                # Test real HK option chain
                print(f"\n🔗 Getting real HK option chain for {test_symbol} {test_expiry}...")
                try:
                    option_chain = client.get_option_chain(test_symbol, test_expiry, Market.HK)

                    print(f"📈 SUCCESS! Retrieved {len(option_chain)} HK option contracts")

                    # Display sample data
                    print(f"\nOption Chain Columns: {list(option_chain.columns)}")

                    if 'put_call' in option_chain.columns:
                        calls = option_chain[option_chain['put_call'] == 'CALL']
                        puts = option_chain[option_chain['put_call'] == 'PUT']
                        print(f"Found: {len(calls)} CALL options, {len(puts)} PUT options")

                        if len(calls) > 0:
                            print(f"\n📈 Sample HK CALL option:")
                            call_sample = calls.iloc[0]
                            print(f"   Identifier: {call_sample.get('identifier', 'N/A')}")
                            print(f"   Strike: {call_sample.get('strike', 'N/A')}")
                            print(f"   Latest Price: {call_sample.get('latest_price', 'N/A')}")
                            print(f"   Bid: {call_sample.get('bid_price', 'N/A')}")
                            print(f"   Ask: {call_sample.get('ask_price', 'N/A')}")
                            print(f"   Volume: {call_sample.get('volume', 'N/A')}")
                            print(f"   Open Interest: {call_sample.get('open_interest', 'N/A')}")
                            if 'delta' in call_sample:
                                print(f"   Delta: {call_sample.get('delta', 'N/A')}")
                            if 'gamma' in call_sample:
                                print(f"   Gamma: {call_sample.get('gamma', 'N/A')}")

                    print(f"\n🎉 REAL HK OPTION DATA WORKING!")
                    return True

                except Exception as option_error:
                    print(f"❌ HK option chain failed: {str(option_error)}")
                    return False

        else:
            print("❌ No HK option symbols found")
            return False

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ Hong Kong option data working! Service can use real HK options.")
    else:
        print("\n⚠️ HK option permissions also limited, service will use mock data with real stock prices")
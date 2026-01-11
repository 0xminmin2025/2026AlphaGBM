"""
Test real Tiger API option data
"""

from tiger_client import get_client_manager
from tigeropen.common.consts import Market

def main():
    print("🚀 Testing Real Tiger API Option Chain Data")
    print("=" * 60)

    # Get client manager
    client = get_client_manager()

    # Initialize client
    print("📊 Initializing Tiger API client...")
    if not client.initialize_client():
        print("❌ Client initialization failed")
        return False

    # Get AAPL expirations
    try:
        print("\n📅 Getting AAPL option expirations...")
        expirations = client.get_option_expirations('AAPL', Market.US)
        print(f"✅ Found {len(expirations)} expiration dates")

        if len(expirations) > 0:
            test_expiry = expirations['date'].iloc[0]
            print(f"📍 Testing with expiry: {test_expiry}")

            # Test real option chain
            print(f"\n🔗 Getting real option chain for AAPL {test_expiry}...")
            try:
                option_chain = client.get_option_chain('AAPL', test_expiry, Market.US)

                print(f"📈 SUCCESS! Retrieved {len(option_chain)} option contracts")

                # Display sample data
                print(f"\nOption Chain Columns: {list(option_chain.columns)}")

                if 'put_call' in option_chain.columns:
                    calls = option_chain[option_chain['put_call'] == 'CALL']
                    puts = option_chain[option_chain['put_call'] == 'PUT']
                    print(f"Found: {len(calls)} CALL options, {len(puts)} PUT options")

                    if len(calls) > 0:
                        print(f"\n📈 Sample CALL option:")
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
                        if 'theta' in call_sample:
                            print(f"   Theta: {call_sample.get('theta', 'N/A')}")
                        if 'vega' in call_sample:
                            print(f"   Vega: {call_sample.get('vega', 'N/A')}")

                print(f"\n🎉 REAL OPTION DATA WORKING!")
                return True

            except Exception as option_error:
                print(f"❌ Option chain failed: {str(option_error)}")
                return False

        else:
            print("❌ No expiration dates found")
            return False

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ Ready to use real Tiger API option data!")
    else:
        print("\n⚠️ Option permissions may be limited, service will fall back to mock data")
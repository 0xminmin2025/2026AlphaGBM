"""
Simple test script for Tiger client setup
"""

from tiger_client import get_client_manager
from tigeropen.common.consts import Market

def main():
    print("🚀 Testing Tiger Client Setup")
    print("=" * 40)

    # Get client manager
    client = get_client_manager()

    # Initialize client
    print("📊 Initializing client...")
    if not client.initialize_client():
        print("❌ Client initialization failed")
        return False

    # Test permissions (optional)
    print("\n🔐 Checking permissions...")
    client.test_permissions()

    # Test basic functionality
    try:
        print("\n📈 Testing basic quote...")
        # Test with a simple stock quote first
        stock_data = client.get_stock_quote(['00700'])  # Tencent
        print(f"✅ Stock quote successful: {stock_data['symbol'].iloc[0]} = {stock_data['latest_price'].iloc[0]}")

    except Exception as e:
        print(f"⚠️ Stock quote test failed: {str(e)}")

    # Test option functionality
    try:
        print("\n🔄 Testing option expirations...")
        expirations = client.get_option_expirations('AAPL', Market.US)
        if len(expirations) > 0:
            print(f"✅ Found {len(expirations)} expiration dates for AAPL")
            print(f"   Next expiry: {expirations['date'].iloc[0]}")
        else:
            print("⚠️ No expiration dates found")

    except Exception as e:
        print(f"⚠️ Option expiration test failed: {str(e)}")

    print("\n" + "=" * 40)
    print("🎉 Client setup test completed!")
    return True

if __name__ == "__main__":
    main()
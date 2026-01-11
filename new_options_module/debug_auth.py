"""
Debug Tiger API authentication step by step
"""

import os
from tigeropen.common.consts import Language, Market
from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.quote.quote_client import QuoteClient
from tigeropen.common.util.signature_utils import read_private_key

def test_config_method_1():
    """Test using properties file configuration"""
    print("=" * 60)
    print("🧪 METHOD 1: Properties file configuration")
    print("=" * 60)

    try:
        client_config = TigerOpenClientConfig(props_path='.')
        print(f"✅ Config loaded from properties file")
        print(f"   Tiger ID: {client_config.tiger_id}")
        print(f"   License: {client_config.license}")
        print(f"   Account: '{client_config.account}'")

        # Try to add an account if empty
        if not client_config.account:
            # For HK license, try a demo account format
            client_config.account = '20241201000000000'  # Demo account format
            print(f"   Added demo account: {client_config.account}")

        client_config.language = Language.zh_CN

        # Test quote client
        quote_client = QuoteClient(client_config, is_grab_permission=False)
        print("✅ QuoteClient created successfully")

        # Try a simple permission check
        permissions = quote_client.get_quote_permission()
        print(f"✅ Got {len(permissions)} permissions")
        for p in permissions:
            print(f"   - {p['name']}")

        return quote_client

    except Exception as e:
        print(f"❌ Method 1 failed: {str(e)}")
        return None

def test_config_method_2():
    """Test manual configuration with PKCS#1 key"""
    print("\n" + "=" * 60)
    print("🧪 METHOD 2: Manual config with PKCS#1 private key")
    print("=" * 60)

    try:
        client_config = TigerOpenClientConfig()

        # Use the PKCS#1 private key directly from config
        pkcs1_key = """MIICWwIBAAKBgQCYkouInOtYRtCw53x+Z18XeKPcqEDxli2enPkwGLKbgGGmxIUQfO6IvcM95OZND3E03TzLBpm7WRN506T4VLAUXH7W17UGEmpsS3q67ip4wbm9TtVBx8d6bBOgNNzXi9GBoueXCYX0pxO6wjX+8RkfKWojHKTlPu2BCrDSpw5cmwIDAQABAoGAZQswo8Igzu7fSTmVpnU5cebwxrMbh6PJBLG7ClJg/0Ev6u1dnsTOiPr78eLFbyWZ+MPIfkEZ0Qy2LEmxiNE1ZtDEkcQjbhp2T/rTR5kUXvNvtZsvnBjWSiugEa+LwdciiwSSPx1ZQ5Okw68o6MfYWWZay8y4fwc+ON8btl8QRGECQQDM8Y74b4e7opZkH/2SUhZ/3m50On+M2h8qWMRJf1uxJlqOsMag1Ds1Fm2cCrLo7lNtIeM2AAKyFpxrZ7wZEX0rAkEAvpT5ii1EpLGJqCFIYKD+WT69YxH0NwIr1Gq/a+h8ETB5khYUtOujrO8ky0Mt4DS+oyYXmG6cchDjtL7iYuRGUQJAezs4u7vcgv/VrGjsAUKo0sR96BeQwLIbkUwE4yjYiqHETA6RsP1MiLRuvihUwekkcvewdrT06f7cmVyr5ur0NwJAQmJJ+aODAYsF1Bajy2TIs/VyqouacX7EHZ2BR+kXLjWgYw5l8A8UWCyEuHiSBkLZFKM0HNiKjgDsEA1ddezlwQJAIijgOcJG5F8pZGMWwM+IqqUTaGwR6p1GqG5R0p8A02XnNWg7HrAbeAruHVV59HQclFFwHYVZT4gjK0g/Y3hFDA=="""

        client_config.private_key = pkcs1_key
        client_config.tiger_id = '20155915'
        client_config.account = '20241201000000000'  # Demo account
        client_config.license = 'TBHK'
        client_config.language = Language.zh_CN

        print(f"✅ Manual config created")
        print(f"   Tiger ID: {client_config.tiger_id}")
        print(f"   License: {client_config.license}")
        print(f"   Account: {client_config.account}")
        print(f"   Private key length: {len(client_config.private_key)}")

        # Test quote client
        quote_client = QuoteClient(client_config, is_grab_permission=False)
        print("✅ QuoteClient created successfully")

        # Try a simple permission check
        permissions = quote_client.get_quote_permission()
        print(f"✅ Got {len(permissions)} permissions")
        for p in permissions:
            print(f"   - {p['name']}")

        return quote_client

    except Exception as e:
        print(f"❌ Method 2 failed: {str(e)}")
        return None

def test_config_method_3():
    """Test with PEM file"""
    print("\n" + "=" * 60)
    print("🧪 METHOD 3: Manual config with PEM file")
    print("=" * 60)

    try:
        client_config = TigerOpenClientConfig()

        # Use the PEM file we created
        client_config.private_key = read_private_key('./private_key.pem')
        client_config.tiger_id = '20155915'
        client_config.account = '20241201000000000'  # Demo account
        client_config.license = 'TBHK'
        client_config.language = Language.zh_CN

        print(f"✅ Config with PEM file created")
        print(f"   Tiger ID: {client_config.tiger_id}")
        print(f"   License: {client_config.license}")
        print(f"   Account: {client_config.account}")

        # Test quote client
        quote_client = QuoteClient(client_config, is_grab_permission=False)
        print("✅ QuoteClient created successfully")

        # Try a simple permission check
        permissions = quote_client.get_quote_permission()
        print(f"✅ Got {len(permissions)} permissions")
        for p in permissions:
            print(f"   - {p['name']}")

        return quote_client

    except Exception as e:
        print(f"❌ Method 3 failed: {str(e)}")
        return None

def test_quote_functionality(quote_client):
    """Test basic quote functionality"""
    if not quote_client:
        return False

    print("\n" + "=" * 60)
    print("🧪 TESTING QUOTE FUNCTIONALITY")
    print("=" * 60)

    try:
        # Test basic stock quote
        print("Testing basic stock quote...")
        stock_data = quote_client.get_stock_briefs(['00700'])  # Tencent
        print(f"✅ Stock quote: {stock_data['symbol'].iloc[0]} = {stock_data['latest_price'].iloc[0]}")

        # Test option expirations
        print("Testing option expirations...")
        expirations = quote_client.get_option_expirations(['AAPL'], Market.US)
        print(f"✅ Found {len(expirations)} expiration dates for AAPL")
        if len(expirations) > 0:
            print(f"   First expiry: {expirations['date'].iloc[0]}")

        return True

    except Exception as e:
        print(f"❌ Quote functionality test failed: {str(e)}")
        return False

def main():
    """Main debug function"""
    print("🚀 Tiger API Authentication Debug")
    print("Starting comprehensive authentication testing...\n")

    working_client = None

    # Try different configuration methods
    methods = [
        ("Properties File", test_config_method_1),
        ("Manual PKCS#1", test_config_method_2),
        ("PEM File", test_config_method_3)
    ]

    for method_name, test_func in methods:
        try:
            client = test_func()
            if client:
                print(f"🎉 SUCCESS: {method_name} method worked!")
                working_client = client
                break
        except Exception as e:
            print(f"💥 EXCEPTION in {method_name}: {str(e)}")

    if working_client:
        # Test actual functionality
        test_quote_functionality(working_client)
        print("\n🎉 AUTHENTICATION SUCCESSFUL! Ready to use real Tiger API data.")
        return working_client
    else:
        print("\n❌ ALL AUTHENTICATION METHODS FAILED")
        print("Need to check:")
        print("1. Tiger ID and license are correct")
        print("2. Private key format and content")
        print("3. Account permissions")
        print("4. API environment settings")
        return None

if __name__ == "__main__":
    result = main()
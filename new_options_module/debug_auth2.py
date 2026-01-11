"""
Tiger API Authentication Debug - Round 2
Testing different configurations based on TBHK license
"""

import os
from tigeropen.common.consts import Language, Market
from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.quote.quote_client import QuoteClient
from tigeropen.common.util.signature_utils import read_private_key

def test_empty_account():
    """Test with empty account - sometimes needed for quote-only"""
    print("=" * 60)
    print("🧪 TEST: Empty account (quote-only mode)")
    print("=" * 60)

    try:
        client_config = TigerOpenClientConfig()
        client_config.private_key = """MIICWwIBAAKBgQCYkouInOtYRtCw53x+Z18XeKPcqEDxli2enPkwGLKbgGGmxIUQfO6IvcM95OZND3E03TzLBpm7WRN506T4VLAUXH7W17UGEmpsS3q67ip4wbm9TtVBx8d6bBOgNNzXi9GBoueXCYX0pxO6wjX+8RkfKWojHKTlPu2BCrDSpw5cmwIDAQABAoGAZQswo8Igzu7fSTmVpnU5cebwxrMbh6PJBLG7ClJg/0Ev6u1dnsTOiPr78eLFbyWZ+MPIfkEZ0Qy2LEmxiNE1ZtDEkcQjbhp2T/rTR5kUXvNvtZsvnBjWSiugEa+LwdciiwSSPx1ZQ5Okw68o6MfYWWZay8y4fwc+ON8btl8QRGECQQDM8Y74b4e7opZkH/2SUhZ/3m50On+M2h8qWMRJf1uxJlqOsMag1Ds1Fm2cCrLo7lNtIeM2AAKyFpxrZ7wZEX0rAkEAvpT5ii1EpLGJqCFIYKD+WT69YxH0NwIr1Gq/a+h8ETB5khYUtOujrO8ky0Mt4DS+oyYXmG6cchDjtL7iYuRGUQJAezs4u7vcgv/VrGjsAUKo0sR96BeQwLIbkUwE4yjYiqHETA6RsP1MiLRuvihUwekkcvewdrT06f7cmVyr5ur0NwJAQmJJ+aODAYsF1Bajy2TIs/VyqouacX7EHZ2BR+kXLjWgYw5l8A8UWCyEuHiSBkLZFKM0HNiKjgDsEA1ddezlwQJAIijgOcJG5F8pZGMWwM+IqqUTaGwR6p1GqG5R0p8A02XnNWg7HrAbeAruHVV59HQclFFwHYVZT4gjK0g/Y3hFDA=="""
        client_config.tiger_id = '20155915'
        client_config.account = ''  # Empty account
        client_config.license = 'TBHK'
        client_config.language = Language.zh_CN

        print(f"Config: Tiger ID={client_config.tiger_id}, Account='{client_config.account}', License={client_config.license}")

        quote_client = QuoteClient(client_config, is_grab_permission=False)
        permissions = quote_client.get_quote_permission()
        print(f"✅ SUCCESS: Got {len(permissions)} permissions")
        return quote_client

    except Exception as e:
        print(f"❌ Failed: {str(e)}")
        return None

def test_sandbox_env():
    """Test with sandbox environment"""
    print("\n" + "=" * 60)
    print("🧪 TEST: Sandbox environment")
    print("=" * 60)

    try:
        client_config = TigerOpenClientConfig()
        client_config.private_key = """MIICWwIBAAKBgQCYkouInOtYRtCw53x+Z18XeKPcqEDxli2enPkwGLKbgGGmxIUQfO6IvcM95OZND3E03TzLBpm7WRN506T4VLAUXH7W17UGEmpsS3q67ip4wbm9TtVBx8d6bBOgNNzXi9GBoueXCYX0pxO6wjX+8RkfKWojHKTlPu2BCrDSpw5cmwIDAQABAoGAZQswo8Igzu7fSTmVpnU5cebwxrMbh6PJBLG7ClJg/0Ev6u1dnsTOiPr78eLFbyWZ+MPIfkEZ0Qy2LEmxiNE1ZtDEkcQjbhp2T/rTR5kUXvNvtZsvnBjWSiugEa+LwdciiwSSPx1ZQ5Okw68o6MfYWWZay8y4fwc+ON8btl8QRGECQQDM8Y74b4e7opZkH/2SUhZ/3m50On+M2h8qWMRJf1uxJlqOsMag1Ds1Fm2cCrLo7lNtIeM2AAKyFpxrZ7wZEX0rAkEAvpT5ii1EpLGJqCFIYKD+WT69YxH0NwIr1Gq/a+h8ETB5khYUtOujrO8ky0Mt4DS+oyYXmG6cchDjtL7iYuRGUQJAezs4u7vcgv/VrGjsAUKo0sR96BeQwLIbkUwE4yjYiqHETA6RsP1MiLRuvihUwekkcvewdrT06f7cmVyr5ur0NwJAQmJJ+aODAYsF1Bajy2TIs/VyqouacX7EHZ2BR+kXLjWgYw5l8A8UWCyEuHiSBkLZFKM0HNiKjgDsEA1ddezlwQJAIijgOcJG5F8pZGMWwM+IqqUTaGwR6p1GqG5R0p8A02XnNWg7HrAbeAruHVV59HQclFFwHYVZT4gjK0g/Y3hFDA=="""
        client_config.tiger_id = '20155915'
        client_config.account = '20241201000000000'
        client_config.license = 'TBHK'
        client_config.sandbox = True  # Try sandbox mode
        client_config.language = Language.zh_CN

        print(f"Config: Tiger ID={client_config.tiger_id}, Sandbox=True")

        quote_client = QuoteClient(client_config, is_grab_permission=False)
        permissions = quote_client.get_quote_permission()
        print(f"✅ SUCCESS: Got {len(permissions)} permissions")
        return quote_client

    except Exception as e:
        print(f"❌ Failed: {str(e)}")
        return None

def test_different_license():
    """Test with different license formats"""
    print("\n" + "=" * 60)
    print("🧪 TEST: Different license variations")
    print("=" * 60)

    licenses_to_try = ['TBHK', 'TB_HK', 'HK', 'TBSG']

    for license_val in licenses_to_try:
        try:
            print(f"Trying license: {license_val}")
            client_config = TigerOpenClientConfig()
            client_config.private_key = """MIICWwIBAAKBgQCYkouInOtYRtCw53x+Z18XeKPcqEDxli2enPkwGLKbgGGmxIUQfO6IvcM95OZND3E03TzLBpm7WRN506T4VLAUXH7W17UGEmpsS3q67ip4wbm9TtVBx8d6bBOgNNzXi9GBoueXCYX0pxO6wjX+8RkfKWojHKTlPu2BCrDSpw5cmwIDAQABAoGAZQswo8Igzu7fSTmVpnU5cebwxrMbh6PJBLG7ClJg/0Ev6u1dnsTOiPr78eLFbyWZ+MPIfkEZ0Qy2LEmxiNE1ZtDEkcQjbhp2T/rTR5kUXvNvtZsvnBjWSiugEa+LwdciiwSSPx1ZQ5Okw68o6MfYWWZay8y4fwc+ON8btl8QRGECQQDM8Y74b4e7opZkH/2SUhZ/3m50On+M2h8qWMRJf1uxJlqOsMag1Ds1Fm2cCrLo7lNtIeM2AAKyFpxrZ7wZEX0rAkEAvpT5ii1EpLGJqCFIYKD+WT69YxH0NwIr1Gq/a+h8ETB5khYUtOujrO8ky0Mt4DS+oyYXmG6cchDjtL7iYuRGUQJAezs4u7vcgv/VrGjsAUKo0sR96BeQwLIbkUwE4yjYiqHETA6RsP1MiLRuvihUwekkcvewdrT06f7cmVyr5ur0NwJAQmJJ+aODAYsF1Bajy2TIs/VyqouacX7EHZ2BR+kXLjWgYw5l8A8UWCyEuHiSBkLZFKM0HNiKjgDsEA1ddezlwQJAIijgOcJG5F8pZGMWwM+IqqUTaGwR6p1GqG5R0p8A02XnNWg7HrAbeAruHVV59HQclFFwHYVZT4gjK0g/Y3hFDA=="""
            client_config.tiger_id = '20155915'
            client_config.account = '20241201000000000'
            client_config.license = license_val
            client_config.language = Language.zh_CN

            quote_client = QuoteClient(client_config, is_grab_permission=False)
            permissions = quote_client.get_quote_permission()
            print(f"✅ SUCCESS with license {license_val}: Got {len(permissions)} permissions")
            return quote_client

        except Exception as e:
            print(f"❌ Failed with license {license_val}: {str(e)}")
            continue

    return None

def test_props_file_variations():
    """Test different properties file configurations"""
    print("\n" + "=" * 60)
    print("🧪 TEST: Properties file with modifications")
    print("=" * 60)

    try:
        # Try using props_path with current directory
        client_config = TigerOpenClientConfig(props_path='.')
        client_config.language = Language.zh_CN
        # Don't modify any existing values

        print(f"Using unmodified props file config")
        print(f"Tiger ID: {client_config.tiger_id}")
        print(f"License: {client_config.license}")
        print(f"Account: '{client_config.account}'")

        quote_client = QuoteClient(client_config, is_grab_permission=False)
        permissions = quote_client.get_quote_permission()
        print(f"✅ SUCCESS: Got {len(permissions)} permissions")
        return quote_client

    except Exception as e:
        print(f"❌ Failed: {str(e)}")
        return None

def test_simple_quote_only():
    """Test most basic configuration for quote only"""
    print("\n" + "=" * 60)
    print("🧪 TEST: Minimal configuration for quotes")
    print("=" * 60)

    try:
        client_config = TigerOpenClientConfig()
        # Use only the essential fields
        client_config.private_key = """MIICWwIBAAKBgQCYkouInOtYRtCw53x+Z18XeKPcqEDxli2enPkwGLKbgGGmxIUQfO6IvcM95OZND3E03TzLBpm7WRN506T4VLAUXH7W17UGEmpsS3q67ip4wbm9TtVBx8d6bBOgNNzXi9GBoueXCYX0pxO6wjX+8RkfKWojHKTlPu2BCrDSpw5cmwIDAQABAoGAZQswo8Igzu7fSTmVpnU5cebwxrMbh6PJBLG7ClJg/0Ev6u1dnsTOiPr78eLFbyWZ+MPIfkEZ0Qy2LEmxiNE1ZtDEkcQjbhp2T/rTR5kUXvNvtZsvnBjWSiugEa+LwdciiwSSPx1ZQ5Okw68o6MfYWWZay8y4fwc+ON8btl8QRGECQQDM8Y74b4e7opZkH/2SUhZ/3m50On+M2h8qWMRJf1uxJlqOsMag1Ds1Fm2cCrLo7lNtIeM2AAKyFpxrZ7wZEX0rAkEAvpT5ii1EpLGJqCFIYKD+WT69YxH0NwIr1Gq/a+h8ETB5khYUtOujrO8ky0Mt4DS+oyYXmG6cchDjtL7iYuRGUQJAezs4u7vcgv/VrGjsAUKo0sR96BeQwLIbkUwE4yjYiqHETA6RsP1MiLRuvihUwekkcvewdrT06f7cmVyr5ur0NwJAQmJJ+aODAYsF1Bajy2TIs/VyqouacX7EHZ2BR+kXLjWgYw5l8A8UWCyEuHiSBkLZFKM0HNiKjgDsEA1ddezlwQJAIijgOcJG5F8pZGMWwM+IqqUTaGwR6p1GqG5R0p8A02XnNWg7HrAbeAruHVV59HQclFFwHYVZT4gjK0g/Y3hFDA=="""
        client_config.tiger_id = '20155915'
        client_config.license = 'TBHK'
        # Try without account at all

        print(f"Minimal config: Only tiger_id, private_key, license")

        # Try without creating QuoteClient, just test config loading
        print("Testing basic config creation...")
        print(f"✅ Config created successfully")

        # Now try quote client without permissions
        quote_client = QuoteClient(client_config, is_grab_permission=False)
        print("✅ QuoteClient created successfully")

        # Skip permission check, try direct stock quote
        print("Testing direct stock quote (bypass permissions)...")
        stock_data = quote_client.get_stock_briefs(['00700'])
        print(f"✅ SUCCESS: Stock quote retrieved!")
        return quote_client

    except Exception as e:
        print(f"❌ Failed: {str(e)}")
        return None

def main():
    """Main debug function"""
    print("🚀 Tiger API Authentication Debug - Round 2")
    print("Testing TBHK-specific configurations...\n")

    working_client = None

    # Test different approaches
    tests = [
        ("Empty Account", test_empty_account),
        ("Sandbox Environment", test_sandbox_env),
        ("License Variations", test_different_license),
        ("Props File Unmodified", test_props_file_variations),
        ("Minimal Config", test_simple_quote_only)
    ]

    for test_name, test_func in tests:
        try:
            print(f"\n🧪 Running: {test_name}")
            client = test_func()
            if client:
                print(f"🎉 SUCCESS: {test_name} worked!")
                working_client = client
                break
        except Exception as e:
            print(f"💥 EXCEPTION in {test_name}: {str(e)}")

    if working_client:
        print("\n🎉 AUTHENTICATION SUCCESSFUL!")
        print("Testing full functionality...")
        try:
            # Test stock quote
            stock_data = working_client.get_stock_briefs(['00700'])
            print(f"✅ Stock quote: {stock_data['symbol'].iloc[0]} = ${stock_data['latest_price'].iloc[0]}")

            # Test option data
            expirations = working_client.get_option_expirations(['AAPL'], Market.US)
            print(f"✅ Option expirations: Found {len(expirations)} dates for AAPL")

        except Exception as e:
            print(f"⚠️ Some functionality failed: {str(e)}")

        return working_client
    else:
        print("\n❌ ALL TESTS FAILED")
        print("\nPossible issues:")
        print("1. The Tiger ID and private key don't match")
        print("2. The account lacks API permissions")
        print("3. The license configuration is incorrect")
        print("4. The environment (PROD vs sandbox) is wrong")
        print("5. Additional authentication fields are required")
        return None

if __name__ == "__main__":
    result = main()
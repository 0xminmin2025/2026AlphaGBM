"""
Tests for Market Detection Module

Tests the unified market detection logic for US, CN (A-share), and HK markets.
"""

import pytest
from ..market_detector import (
    detect_market,
    detect_market_with_exchange,
    normalize_symbol,
    get_market_name,
    is_a_share,
    is_hk_stock,
    is_us_stock,
)
from ..interfaces import Market


class TestDetectMarket:
    """Test cases for detect_market function."""

    # US Stocks
    def test_us_stock_simple(self):
        """US stocks without suffix should return US."""
        assert detect_market("AAPL") == Market.US
        assert detect_market("MSFT") == Market.US
        assert detect_market("GOOGL") == Market.US
        assert detect_market("TSLA") == Market.US

    def test_us_stock_lowercase(self):
        """Lowercase symbols should work."""
        assert detect_market("aapl") == Market.US
        assert detect_market("msft") == Market.US

    def test_us_stock_with_spaces(self):
        """Symbols with spaces should be trimmed."""
        assert detect_market(" AAPL ") == Market.US
        assert detect_market("  MSFT  ") == Market.US

    # Hong Kong Stocks
    def test_hk_stock_with_suffix(self):
        """HK stocks with .HK suffix should return HK."""
        assert detect_market("0700.HK") == Market.HK  # Tencent
        assert detect_market("9988.HK") == Market.HK  # Alibaba
        assert detect_market("1299.HK") == Market.HK  # AIA
        assert detect_market("0005.HK") == Market.HK  # HSBC

    def test_hk_stock_lowercase_suffix(self):
        """HK suffix should be case-insensitive."""
        assert detect_market("0700.hk") == Market.HK
        assert detect_market("9988.Hk") == Market.HK

    # A-Share Stocks (China)
    def test_cn_stock_with_ss_suffix(self):
        """Shanghai stocks with .SS suffix should return CN."""
        assert detect_market("600519.SS") == Market.CN  # Moutai
        assert detect_market("601318.SS") == Market.CN  # Ping An
        assert detect_market("688111.SS") == Market.CN  # STAR Market

    def test_cn_stock_with_sz_suffix(self):
        """Shenzhen stocks with .SZ suffix should return CN."""
        assert detect_market("000001.SZ") == Market.CN  # Ping An Bank
        assert detect_market("300750.SZ") == Market.CN  # CATL

    def test_cn_stock_with_sh_suffix(self):
        """Shanghai stocks with .SH (alternative) suffix should return CN."""
        assert detect_market("600519.SH") == Market.CN

    def test_cn_stock_without_suffix_shanghai_main(self):
        """6-digit Shanghai main board codes (60*) without suffix."""
        assert detect_market("600519") == Market.CN  # Moutai
        assert detect_market("601318") == Market.CN  # Ping An

    def test_cn_stock_without_suffix_shanghai_star(self):
        """6-digit Shanghai STAR market codes (68*) without suffix."""
        assert detect_market("688111") == Market.CN
        assert detect_market("688599") == Market.CN

    def test_cn_stock_without_suffix_shenzhen_main(self):
        """6-digit Shenzhen main board codes (00*) without suffix."""
        assert detect_market("000001") == Market.CN  # Ping An Bank
        assert detect_market("000002") == Market.CN  # Vanke

    def test_cn_stock_without_suffix_shenzhen_chinext(self):
        """6-digit Shenzhen ChiNext codes (30*) without suffix."""
        assert detect_market("300750") == Market.CN  # CATL
        assert detect_market("300059") == Market.CN

    # Edge Cases
    def test_5_digit_number_is_us(self):
        """5-digit numbers should default to US."""
        assert detect_market("12345") == Market.US

    def test_7_digit_number_is_us(self):
        """7-digit numbers should default to US."""
        assert detect_market("1234567") == Market.US

    def test_non_matching_6_digit_is_us(self):
        """6-digit codes not matching CN prefixes should be US."""
        assert detect_market("123456") == Market.US  # Not 60/68/00/30 prefix
        assert detect_market("999999") == Market.US

    def test_empty_string(self):
        """Empty string should return US (default)."""
        assert detect_market("") == Market.US


class TestDetectMarketWithExchange:
    """Test cases for detect_market_with_exchange function."""

    def test_us_stock(self):
        """US stocks should return (US, None)."""
        market, exchange = detect_market_with_exchange("AAPL")
        assert market == Market.US
        assert exchange is None

    def test_hk_stock(self):
        """HK stocks should return (HK, 'HK')."""
        market, exchange = detect_market_with_exchange("0700.HK")
        assert market == Market.HK
        assert exchange == 'HK'

    def test_cn_shanghai_with_suffix(self):
        """Shanghai stocks with suffix should return (CN, 'SS')."""
        market, exchange = detect_market_with_exchange("600519.SS")
        assert market == Market.CN
        assert exchange == 'SS'

    def test_cn_shenzhen_with_suffix(self):
        """Shenzhen stocks with suffix should return (CN, 'SZ')."""
        market, exchange = detect_market_with_exchange("000001.SZ")
        assert market == Market.CN
        assert exchange == 'SZ'

    def test_cn_shanghai_without_suffix(self):
        """Shanghai stocks without suffix should return (CN, 'SS')."""
        market, exchange = detect_market_with_exchange("600519")
        assert market == Market.CN
        assert exchange == 'SS'

    def test_cn_shenzhen_without_suffix(self):
        """Shenzhen stocks without suffix should return (CN, 'SZ')."""
        market, exchange = detect_market_with_exchange("000001")
        assert market == Market.CN
        assert exchange == 'SZ'


class TestNormalizeSymbol:
    """Test cases for normalize_symbol function."""

    def test_us_stock_unchanged(self):
        """US stocks should be uppercased but otherwise unchanged."""
        assert normalize_symbol("aapl") == "AAPL"
        assert normalize_symbol("MSFT") == "MSFT"

    def test_hk_stock_unchanged(self):
        """HK stocks with suffix should be unchanged."""
        assert normalize_symbol("0700.hk") == "0700.HK"

    def test_cn_shanghai_with_suffix(self):
        """Shanghai stocks with suffix should be unchanged."""
        assert normalize_symbol("600519.ss") == "600519.SS"

    def test_cn_shanghai_without_suffix(self):
        """Shanghai stocks without suffix should add .SS."""
        assert normalize_symbol("600519") == "600519.SS"
        assert normalize_symbol("688111") == "688111.SS"

    def test_cn_shenzhen_without_suffix(self):
        """Shenzhen stocks without suffix should add .SZ."""
        assert normalize_symbol("000001") == "000001.SZ"
        assert normalize_symbol("300750") == "300750.SZ"


class TestMarketHelpers:
    """Test cases for helper functions."""

    def test_is_a_share(self):
        """Test is_a_share function."""
        assert is_a_share("600519") is True
        assert is_a_share("600519.SS") is True
        assert is_a_share("000001.SZ") is True
        assert is_a_share("AAPL") is False
        assert is_a_share("0700.HK") is False

    def test_is_hk_stock(self):
        """Test is_hk_stock function."""
        assert is_hk_stock("0700.HK") is True
        assert is_hk_stock("9988.HK") is True
        assert is_hk_stock("AAPL") is False
        assert is_hk_stock("600519") is False

    def test_is_us_stock(self):
        """Test is_us_stock function."""
        assert is_us_stock("AAPL") is True
        assert is_us_stock("MSFT") is True
        assert is_us_stock("0700.HK") is False
        assert is_us_stock("600519") is False

    def test_get_market_name_english(self):
        """Test English market names."""
        assert get_market_name(Market.US, 'en') == 'US Market'
        assert get_market_name(Market.CN, 'en') == 'China A-Share'
        assert get_market_name(Market.HK, 'en') == 'Hong Kong'

    def test_get_market_name_chinese(self):
        """Test Chinese market names."""
        assert get_market_name(Market.US, 'zh') == '美股'
        assert get_market_name(Market.CN, 'zh') == 'A股'
        assert get_market_name(Market.HK, 'zh') == '港股'


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])

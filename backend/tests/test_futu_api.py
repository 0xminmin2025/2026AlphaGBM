#!/usr/bin/env python3
"""
Futu OpenD API Test Suite

Tests Futu API connectivity and data access for:
- Real-time quotes
- Historical K-line data
- Stock fundamentals
- Options data

Prerequisites:
1. Install futu-api: pip install futu-api
2. Run FutuOpenD gateway locally (default: localhost:11111)
3. Login to Futu account in FutuOpenD

Usage:
    python -m tests.test_futu_api
    python -m tests.test_futu_api --host 127.0.0.1 --port 11111
    python -m tests.test_futu_api --symbol AAPL --market US
"""

import sys
import argparse
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

# Check if futu-api is installed
try:
    from futu import (
        OpenQuoteContext,
        RET_OK, RET_ERROR,
        KLType, KL_FIELD, AuType,
        SubType, Market,
        SysConfig
    )
    FUTU_AVAILABLE = True
except ImportError:
    FUTU_AVAILABLE = False
    print("=" * 60)
    print("ERROR: futu-api not installed")
    print("Install with: pip install futu-api")
    print("=" * 60)


# ═══════════════════════════════════════════════════════════════
# Test Result Classes
# ═══════════════════════════════════════════════════════════════

@dataclass
class TestResult:
    """Single test result"""
    name: str
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    elapsed_ms: float = 0
    error: Optional[str] = None


class Colors:
    """ANSI colors for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'

    @staticmethod
    def enabled():
        return sys.stdout.isatty()


def c(text: str, color: str) -> str:
    """Apply color if terminal supports it"""
    if Colors.enabled():
        return f"{color}{text}{Colors.RESET}"
    return text


def emoji(symbol: str) -> str:
    """Return emoji if terminal supports it"""
    return symbol if Colors.enabled() else ""


# ═══════════════════════════════════════════════════════════════
# Futu API Tester
# ═══════════════════════════════════════════════════════════════

class FutuApiTester:
    """Test Futu OpenD API functionality"""

    def __init__(self, host: str = "127.0.0.1", port: int = 11111):
        self.host = host
        self.port = port
        self.quote_ctx: Optional[OpenQuoteContext] = None
        self.results: List[TestResult] = []

    def connect(self) -> bool:
        """Establish connection to FutuOpenD"""
        print(f"\n{emoji('🔌')} Connecting to FutuOpenD at {self.host}:{self.port}...")

        try:
            self.quote_ctx = OpenQuoteContext(host=self.host, port=self.port)
            print(c(f"   {emoji('✅')} Connected successfully!", Colors.GREEN))
            return True
        except Exception as e:
            print(c(f"   {emoji('❌')} Connection failed: {e}", Colors.RED))
            print(f"\n   {emoji('💡')} Make sure FutuOpenD is running:")
            print("      1. Download from: https://www.futunn.com/download/openAPI")
            print("      2. Run FutuOpenD application")
            print("      3. Login to your Futu account")
            return False

    def disconnect(self):
        """Close connection"""
        if self.quote_ctx:
            self.quote_ctx.close()
            print(f"\n{emoji('🔌')} Disconnected from FutuOpenD")

    def _record_result(self, result: TestResult):
        """Record test result"""
        self.results.append(result)

        status = c(f"{emoji('✅')} PASS", Colors.GREEN) if result.success else c(f"{emoji('❌')} FAIL", Colors.RED)
        print(f"   {status} {result.name} ({result.elapsed_ms:.0f}ms)")

        if result.success and result.message:
            print(c(f"      └─ {result.message}", Colors.DIM))
        elif not result.success and result.error:
            print(c(f"      └─ Error: {result.error}", Colors.RED))

    # ─────────────────────────────────────────────────────────
    # Test: Get Global State
    # ─────────────────────────────────────────────────────────
    def test_global_state(self) -> TestResult:
        """Test getting global market state"""
        start = time.time()
        try:
            ret, data = self.quote_ctx.get_global_state()
            elapsed = (time.time() - start) * 1000

            if ret == RET_OK:
                result = TestResult(
                    name="Global State",
                    success=True,
                    message=f"Market: {data.get('market_sz', 'N/A')}, Server Ver: {data.get('server_ver', 'N/A')}",
                    data=data,
                    elapsed_ms=elapsed
                )
            else:
                result = TestResult(
                    name="Global State",
                    success=False,
                    message="",
                    error=str(data),
                    elapsed_ms=elapsed
                )
        except Exception as e:
            result = TestResult(
                name="Global State",
                success=False,
                message="",
                error=str(e),
                elapsed_ms=(time.time() - start) * 1000
            )

        self._record_result(result)
        return result

    # ─────────────────────────────────────────────────────────
    # Test: Real-time Quote
    # ─────────────────────────────────────────────────────────
    def test_realtime_quote(self, symbol: str) -> TestResult:
        """Test getting real-time quote"""
        start = time.time()
        try:
            # Subscribe to quote first
            ret, err = self.quote_ctx.subscribe([symbol], [SubType.QUOTE])
            if ret != RET_OK:
                raise Exception(f"Subscribe failed: {err}")

            time.sleep(0.5)  # Wait for subscription

            # Get quote
            ret, data = self.quote_ctx.get_stock_quote([symbol])
            elapsed = (time.time() - start) * 1000

            if ret == RET_OK and len(data) > 0:
                row = data.iloc[0]
                price = row.get('last_price', 0)
                change_pct = row.get('price_change_rate', 0)
                volume = row.get('volume', 0)

                result = TestResult(
                    name=f"Quote: {symbol}",
                    success=True,
                    message=f"Price: ${price:.2f}, Change: {change_pct:.2f}%, Vol: {volume:,}",
                    data=row.to_dict(),
                    elapsed_ms=elapsed
                )
            else:
                result = TestResult(
                    name=f"Quote: {symbol}",
                    success=False,
                    message="",
                    error=str(data) if ret != RET_OK else "No data returned",
                    elapsed_ms=elapsed
                )
        except Exception as e:
            result = TestResult(
                name=f"Quote: {symbol}",
                success=False,
                message="",
                error=str(e),
                elapsed_ms=(time.time() - start) * 1000
            )

        self._record_result(result)
        return result

    # ─────────────────────────────────────────────────────────
    # Test: Historical K-line
    # ─────────────────────────────────────────────────────────
    def test_kline(self, symbol: str, kl_type: str = "K_DAY", count: int = 30) -> TestResult:
        """Test getting historical K-line data"""
        start = time.time()
        try:
            # Map string to KLType
            kl_type_map = {
                "K_1M": KLType.K_1M,
                "K_5M": KLType.K_5M,
                "K_15M": KLType.K_15M,
                "K_30M": KLType.K_30M,
                "K_60M": KLType.K_60M,
                "K_DAY": KLType.K_DAY,
                "K_WEEK": KLType.K_WEEK,
                "K_MON": KLType.K_MON,
            }
            kl = kl_type_map.get(kl_type, KLType.K_DAY)

            # Subscribe to K-line
            ret, err = self.quote_ctx.subscribe([symbol], [SubType.K_DAY])
            if ret != RET_OK:
                raise Exception(f"Subscribe failed: {err}")

            time.sleep(0.3)

            # Get K-line data
            ret, data, _ = self.quote_ctx.request_history_kline(
                symbol,
                ktype=kl,
                max_count=count
            )
            elapsed = (time.time() - start) * 1000

            if ret == RET_OK and len(data) > 0:
                latest = data.iloc[-1]
                first = data.iloc[0]

                result = TestResult(
                    name=f"K-line ({kl_type}): {symbol}",
                    success=True,
                    message=f"{len(data)} bars, {first['time_key'][:10]} to {latest['time_key'][:10]}, Close: ${latest['close']:.2f}",
                    data={"rows": len(data), "latest": latest.to_dict()},
                    elapsed_ms=elapsed
                )
            else:
                result = TestResult(
                    name=f"K-line ({kl_type}): {symbol}",
                    success=False,
                    message="",
                    error=str(data) if ret != RET_OK else "No data returned",
                    elapsed_ms=elapsed
                )
        except Exception as e:
            result = TestResult(
                name=f"K-line ({kl_type}): {symbol}",
                success=False,
                message="",
                error=str(e),
                elapsed_ms=(time.time() - start) * 1000
            )

        self._record_result(result)
        return result

    # ─────────────────────────────────────────────────────────
    # Test: Stock Basic Info
    # ─────────────────────────────────────────────────────────
    def test_stock_basicinfo(self, symbol: str) -> TestResult:
        """Test getting stock basic info"""
        start = time.time()
        try:
            # Determine market from symbol
            if symbol.startswith("US."):
                market = Market.US
            elif symbol.startswith("HK."):
                market = Market.HK
            elif symbol.startswith("SH.") or symbol.startswith("SZ."):
                market = Market.SH if symbol.startswith("SH.") else Market.SZ
            else:
                market = Market.US

            ret, data = self.quote_ctx.get_stock_basicinfo(market, code_list=[symbol])
            elapsed = (time.time() - start) * 1000

            if ret == RET_OK and len(data) > 0:
                row = data.iloc[0]
                name = row.get('name', 'N/A')
                lot_size = row.get('lot_size', 0)
                stock_type = row.get('stock_type', 'N/A')

                result = TestResult(
                    name=f"Basic Info: {symbol}",
                    success=True,
                    message=f"Name: {name}, Lot Size: {lot_size}, Type: {stock_type}",
                    data=row.to_dict(),
                    elapsed_ms=elapsed
                )
            else:
                result = TestResult(
                    name=f"Basic Info: {symbol}",
                    success=False,
                    message="",
                    error=str(data) if ret != RET_OK else "No data returned",
                    elapsed_ms=elapsed
                )
        except Exception as e:
            result = TestResult(
                name=f"Basic Info: {symbol}",
                success=False,
                message="",
                error=str(e),
                elapsed_ms=(time.time() - start) * 1000
            )

        self._record_result(result)
        return result

    # ─────────────────────────────────────────────────────────
    # Test: Market Snapshot
    # ─────────────────────────────────────────────────────────
    def test_market_snapshot(self, symbols: List[str]) -> TestResult:
        """Test getting market snapshot for multiple symbols"""
        start = time.time()
        try:
            ret, data = self.quote_ctx.get_market_snapshot(symbols)
            elapsed = (time.time() - start) * 1000

            if ret == RET_OK and len(data) > 0:
                summary = []
                for _, row in data.iterrows():
                    code = row.get('code', 'N/A')
                    price = row.get('last_price', 0)
                    summary.append(f"{code}: ${price:.2f}")

                result = TestResult(
                    name=f"Market Snapshot ({len(symbols)} symbols)",
                    success=True,
                    message=", ".join(summary[:3]) + ("..." if len(summary) > 3 else ""),
                    data={"count": len(data)},
                    elapsed_ms=elapsed
                )
            else:
                result = TestResult(
                    name=f"Market Snapshot ({len(symbols)} symbols)",
                    success=False,
                    message="",
                    error=str(data) if ret != RET_OK else "No data returned",
                    elapsed_ms=elapsed
                )
        except Exception as e:
            result = TestResult(
                name=f"Market Snapshot ({len(symbols)} symbols)",
                success=False,
                message="",
                error=str(e),
                elapsed_ms=(time.time() - start) * 1000
            )

        self._record_result(result)
        return result

    # ─────────────────────────────────────────────────────────
    # Test: Order Book (Bid/Ask)
    # ─────────────────────────────────────────────────────────
    def test_orderbook(self, symbol: str) -> TestResult:
        """Test getting order book (bid/ask)"""
        start = time.time()
        try:
            # Subscribe to order book
            ret, err = self.quote_ctx.subscribe([symbol], [SubType.ORDER_BOOK])
            if ret != RET_OK:
                raise Exception(f"Subscribe failed: {err}")

            time.sleep(0.5)

            ret, data = self.quote_ctx.get_order_book(symbol)
            elapsed = (time.time() - start) * 1000

            if ret == RET_OK and 'Bid' in data and 'Ask' in data:
                bid_data = data['Bid']
                ask_data = data['Ask']

                best_bid = bid_data[0] if len(bid_data) > 0 else (0, 0, 0)
                best_ask = ask_data[0] if len(ask_data) > 0 else (0, 0, 0)

                result = TestResult(
                    name=f"Order Book: {symbol}",
                    success=True,
                    message=f"Bid: ${best_bid[0]:.2f} x {best_bid[1]}, Ask: ${best_ask[0]:.2f} x {best_ask[1]}",
                    data={"bid_levels": len(bid_data), "ask_levels": len(ask_data)},
                    elapsed_ms=elapsed
                )
            else:
                result = TestResult(
                    name=f"Order Book: {symbol}",
                    success=False,
                    message="",
                    error=str(data) if ret != RET_OK else "No data returned",
                    elapsed_ms=elapsed
                )
        except Exception as e:
            result = TestResult(
                name=f"Order Book: {symbol}",
                success=False,
                message="",
                error=str(e),
                elapsed_ms=(time.time() - start) * 1000
            )

        self._record_result(result)
        return result

    # ─────────────────────────────────────────────────────────
    # Test: Broker Queue
    # ─────────────────────────────────────────────────────────
    def test_broker_queue(self, symbol: str) -> TestResult:
        """Test getting broker queue (HK stocks only)"""
        start = time.time()
        try:
            # Subscribe to broker
            ret, err = self.quote_ctx.subscribe([symbol], [SubType.BROKER])
            if ret != RET_OK:
                raise Exception(f"Subscribe failed: {err}")

            time.sleep(0.5)

            ret, bid_data, ask_data = self.quote_ctx.get_broker_queue(symbol)
            elapsed = (time.time() - start) * 1000

            if ret == RET_OK:
                result = TestResult(
                    name=f"Broker Queue: {symbol}",
                    success=True,
                    message=f"Bid brokers: {len(bid_data)}, Ask brokers: {len(ask_data)}",
                    data={"bid_count": len(bid_data), "ask_count": len(ask_data)},
                    elapsed_ms=elapsed
                )
            else:
                result = TestResult(
                    name=f"Broker Queue: {symbol}",
                    success=False,
                    message="",
                    error=str(bid_data),
                    elapsed_ms=elapsed
                )
        except Exception as e:
            result = TestResult(
                name=f"Broker Queue: {symbol}",
                success=False,
                message="",
                error=str(e),
                elapsed_ms=(time.time() - start) * 1000
            )

        self._record_result(result)
        return result

    # ─────────────────────────────────────────────────────────
    # Run All Tests
    # ─────────────────────────────────────────────────────────
    def run_all_tests(self, us_symbol: str = "US.AAPL", hk_symbol: str = "HK.00700"):
        """Run comprehensive test suite"""
        print("\n" + "=" * 70)
        print(c(f" {emoji('🧪')} FUTU OPEND API TEST SUITE", Colors.BOLD + Colors.CYAN))
        print("=" * 70)
        print(f" Host: {self.host}:{self.port}")
        print(f" Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)

        if not self.connect():
            return

        try:
            # Global State
            print(f"\n{emoji('📡')} " + c("CONNECTIVITY TESTS", Colors.BOLD))
            print("-" * 50)
            self.test_global_state()

            # US Market Tests
            print(f"\n{emoji('🇺🇸')} " + c(f"US MARKET TESTS ({us_symbol})", Colors.BOLD))
            print("-" * 50)
            self.test_stock_basicinfo(us_symbol)
            self.test_realtime_quote(us_symbol)
            self.test_kline(us_symbol, "K_DAY", 30)
            self.test_orderbook(us_symbol)

            # HK Market Tests
            print(f"\n{emoji('🇭🇰')} " + c(f"HK MARKET TESTS ({hk_symbol})", Colors.BOLD))
            print("-" * 50)
            self.test_stock_basicinfo(hk_symbol)
            self.test_realtime_quote(hk_symbol)
            self.test_kline(hk_symbol, "K_DAY", 30)
            self.test_broker_queue(hk_symbol)

            # Batch Tests
            print(f"\n{emoji('📊')} " + c("BATCH DATA TESTS", Colors.BOLD))
            print("-" * 50)
            self.test_market_snapshot([us_symbol, hk_symbol, "US.TSLA", "US.MSFT"])

        finally:
            self.disconnect()

        # Print Summary
        self._print_summary()

    def _print_summary(self):
        """Print test summary"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.success)
        failed = total - passed

        print("\n" + "=" * 70)
        print(c(f" {emoji('📋')} TEST SUMMARY", Colors.BOLD + Colors.CYAN))
        print("=" * 70)

        print(f" Total Tests: {total}")
        print(f" {emoji('✅')} Passed: " + c(str(passed), Colors.GREEN))
        print(f" {emoji('❌')} Failed: " + c(str(failed), Colors.RED if failed > 0 else Colors.DIM))

        pass_rate = (passed / total * 100) if total > 0 else 0
        bar_width = 40
        filled = int(bar_width * pass_rate / 100)
        bar = c("█" * filled, Colors.GREEN) + c("░" * (bar_width - filled), Colors.DIM)
        print(f"\n {bar} {pass_rate:.1f}%")

        if failed > 0:
            print(f"\n{emoji('⚠️')} " + c("FAILED TESTS:", Colors.YELLOW))
            for r in self.results:
                if not r.success:
                    print(f"   - {r.name}: {r.error}")

        print("\n" + "=" * 70)


# ═══════════════════════════════════════════════════════════════
# Main Entry Point
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description='Futu OpenD API Test Suite',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m tests.test_futu_api
  python -m tests.test_futu_api --host 192.168.1.100 --port 11111
  python -m tests.test_futu_api --us-symbol US.TSLA --hk-symbol HK.09988

Prerequisites:
  1. Install futu-api: pip install futu-api
  2. Download and run FutuOpenD: https://www.futunn.com/download/openAPI
  3. Login to your Futu account in FutuOpenD

Symbol Format:
  - US stocks: US.AAPL, US.TSLA, US.MSFT
  - HK stocks: HK.00700 (Tencent), HK.09988 (Alibaba)
  - A-shares: SH.600519 (Moutai), SZ.000001 (Ping An)
        """
    )

    parser.add_argument('--host', default='127.0.0.1', help='FutuOpenD host (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=11111, help='FutuOpenD port (default: 11111)')
    parser.add_argument('--us-symbol', default='US.AAPL', help='US stock symbol to test (default: US.AAPL)')
    parser.add_argument('--hk-symbol', default='HK.00700', help='HK stock symbol to test (default: HK.00700)')

    args = parser.parse_args()

    if not FUTU_AVAILABLE:
        print("\nInstall futu-api to run tests: pip install futu-api")
        sys.exit(1)

    tester = FutuApiTester(host=args.host, port=args.port)
    tester.run_all_tests(us_symbol=args.us_symbol, hk_symbol=args.hk_symbol)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Market Data Provider Test Runner

Comprehensive test suite that shows:
- Which provider is being tried (in priority order)
- Success/failure status with clear indicators
- Fallback chain visualization
- Response times and data summaries
- Provider health dashboard

Usage:
    python -m app.services.market_data.tests.test_runner AAPL TSLA
    python -m app.services.market_data.tests.test_runner --all
    python -m app.services.market_data.tests.test_runner --symbols AAPL,MSFT,GOOGL
"""

import sys
import os

# ═══════════════════════════════════════════════════════════════════════════════
# Suppress noisy output during imports (defeatbeta banner, nltk downloads, etc.)
# Uses OS-level file descriptor redirect to catch direct writes
# ═══════════════════════════════════════════════════════════════════════════════

import io
import warnings
warnings.filterwarnings('ignore')

# Save real file descriptors
_saved_stdout_fd = os.dup(1)
_saved_stderr_fd = os.dup(2)

# Open /dev/null and redirect stdout/stderr to it
_devnull = os.open(os.devnull, os.O_WRONLY)
os.dup2(_devnull, 1)
os.dup2(_devnull, 2)

# Also redirect Python's sys.stdout/stderr
_real_stdout = sys.stdout
_real_stderr = sys.stderr
sys.stdout = io.StringIO()
sys.stderr = io.StringIO()

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

# Pre-import noisy modules to catch their banners/downloads
try:
    import logging
    logging.disable(logging.CRITICAL)

    # Import defeatbeta completely
    import defeatbeta_api
    from defeatbeta_api.data.ticker import Ticker as _DBTicker

    # Also pre-import other noisy modules
    import nltk
    import yfinance
except ImportError:
    pass

# Restore file descriptors
os.dup2(_saved_stdout_fd, 1)
os.dup2(_saved_stderr_fd, 2)
os.close(_devnull)
os.close(_saved_stdout_fd)
os.close(_saved_stderr_fd)

# Restore Python's sys.stdout/stderr
sys.stdout = _real_stdout
sys.stderr = _real_stderr
logging.disable(logging.NOTSET)

# Now import the rest
import time
import argparse
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field

# Import market detection for dynamic provider ordering
from ..config import get_market_for_symbol
from ..interfaces import Market


def get_adapter_order_for_symbol(symbol: str, include_options: bool = False) -> List[str]:
    """
    Get the provider order based on market type.
    A-shares use tushare as primary, others use yfinance.
    """
    market = get_market_for_symbol(symbol)

    if include_options:
        # Options: only tiger and yfinance support options
        return ['tiger', 'yfinance']

    if market == Market.CN:
        # A-share: tushare first, then tiger (also supports CN)
        return ['tushare', 'tiger', 'yfinance', 'defeatbeta', 'alpha_vantage']
    elif market == Market.HK:
        # Hong Kong: tiger first, then yfinance
        return ['tiger', 'yfinance', 'defeatbeta', 'alpha_vantage', 'tushare']
    else:
        # US market: yfinance first
        return ['yfinance', 'tiger', 'defeatbeta', 'alpha_vantage', 'tushare']


# ═══════════════════════════════════════════════════════════════════════════════
# Logging Control - Suppress noisy output during tests
# ═══════════════════════════════════════════════════════════════════════════════

import io
import contextlib
import warnings

class OutputCapture:
    """Capture and suppress all output during tests (logs, stdout, stderr)."""

    def __init__(self):
        self._original_handlers = {}
        self._original_levels = {}
        self._original_stdout = None
        self._original_stderr = None
        self._dev_null = None
        self._suppressed_loggers = [
            '',  # root logger
            'yfinance',
            'tiger_openapi',
            'app.services.market_data',
            'app.services.market_data.adapters',
            'urllib3',
            'requests',
            'defeatbeta',
            'nltk',
        ]

    def start(self):
        """Start suppressing all output."""
        # Suppress warnings
        warnings.filterwarnings('ignore')

        # Suppress logging
        for logger_name in self._suppressed_loggers:
            logger = logging.getLogger(logger_name)
            self._original_handlers[logger_name] = logger.handlers.copy()
            self._original_levels[logger_name] = logger.level
            logger.handlers = [logging.NullHandler()]
            logger.setLevel(logging.CRITICAL + 1)

        # Redirect stdout/stderr to devnull
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        self._dev_null = io.StringIO()

    def suppress_output(self):
        """Temporarily redirect stdout/stderr (call during actual API calls)."""
        sys.stdout = self._dev_null
        sys.stderr = self._dev_null

    def restore_output(self):
        """Restore stdout/stderr for printing test results."""
        sys.stdout = self._original_stdout
        sys.stderr = self._original_stderr

    def stop(self):
        """Restore everything."""
        # Restore stdout/stderr
        if self._original_stdout:
            sys.stdout = self._original_stdout
        if self._original_stderr:
            sys.stderr = self._original_stderr

        # Restore logging
        for logger_name in self._suppressed_loggers:
            logger = logging.getLogger(logger_name)
            if logger_name in self._original_handlers:
                logger.handlers = self._original_handlers[logger_name]
            if logger_name in self._original_levels:
                logger.setLevel(self._original_levels[logger_name])


output_capture = OutputCapture()


@contextlib.contextmanager
def quiet_call():
    """Context manager to suppress output during API calls."""
    output_capture.suppress_output()
    try:
        yield
    finally:
        output_capture.restore_output()


# ═══════════════════════════════════════════════════════════════════════════════
# Colors and Emojis
# ═══════════════════════════════════════════════════════════════════════════════

class Style:
    """ANSI color codes and emojis for terminal output."""
    # Colors
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    WHITE = '\033[97m'
    GRAY = '\033[90m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'

    @classmethod
    def c(cls, text: str, *colors: str) -> str:
        """Apply colors to text if terminal supports it."""
        if sys.stdout.isatty():
            return ''.join(colors) + str(text) + cls.RESET
        return str(text)


# Emojis
E_SUCCESS = '🟢'
E_FAILED = '🔴'
E_WARNING = '🟡'
E_SKIPPED = '⚪'
E_QUOTE = '📊'
E_HISTORY = '📈'
E_FUND = '💰'
E_OPTIONS = '📋'
E_MACRO = '🌍'
E_CHECK = '✅'
E_CROSS = '❌'
E_ARROW = '→'
E_CLOCK = '⏱️'
E_ROCKET = '🚀'
E_WARN = '⚠️'
E_PROVIDER = '🔌'


# ═══════════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ProviderAttempt:
    """Result of attempting to fetch data from a single provider."""
    provider: str
    success: bool
    elapsed_ms: float
    data_summary: str = ""
    error: str = ""
    error_type: str = ""  # RATE_LIMITED, UNAVAILABLE, NOT_SUPPORTED, NO_DATA, ERROR


@dataclass
class TestResult:
    """Result of a complete data type test (with fallbacks)."""
    data_type: str
    emoji: str
    attempts: List[ProviderAttempt] = field(default_factory=list)
    final_provider: str = ""
    final_success: bool = False
    final_data: str = ""
    fallback_used: bool = False


# ═══════════════════════════════════════════════════════════════════════════════
# Output Formatting
# ═══════════════════════════════════════════════════════════════════════════════

def print_header():
    """Print test suite header."""
    print()
    print(Style.c("╔═════════════════════════════════════════════════════════════════════════╗", Style.CYAN))
    print(Style.c("║", Style.CYAN) + Style.c(f"  {E_ROCKET} Market Data Provider Test Suite                                   ", Style.BOLD) + Style.c("║", Style.CYAN))
    print(Style.c("║", Style.CYAN) + Style.c(f"     Priority: yfinance {E_ARROW} tiger {E_ARROW} defeatbeta {E_ARROW} alpha_vantage              ", Style.DIM) + Style.c("║", Style.CYAN))
    print(Style.c("╚═════════════════════════════════════════════════════════════════════════╝", Style.CYAN))
    print()


def print_symbol_header(symbol: str):
    """Print symbol test header."""
    print()
    print(Style.c(f"{'━' * 77}", Style.GRAY))
    print(f" {E_ROCKET} {Style.c('Testing:', Style.BOLD)} {Style.c(symbol, Style.CYAN, Style.BOLD)}")
    print(Style.c(f"{'━' * 77}", Style.GRAY))


def print_data_type_header(emoji: str, name: str):
    """Print data type section header."""
    print()
    print(f"  {emoji} {Style.c(name.upper(), Style.BOLD)}")
    print(Style.c(f"  {'─' * 55}", Style.GRAY))


def get_provider_number_emoji(index: int) -> str:
    """Get numbered emoji for provider order."""
    emojis = ['1️⃣ ', '2️⃣ ', '3️⃣ ', '4️⃣ ', '5️⃣ ']
    return emojis[index] if index < len(emojis) else f"[{index + 1}]"


def format_provider_attempt(attempt: ProviderAttempt, index: int) -> str:
    """Format a single provider attempt line."""
    num = get_provider_number_emoji(index)
    provider_name = f"{attempt.provider:12}"

    if attempt.success:
        status = Style.c(f"{E_SUCCESS} SUCCESS", Style.GREEN)
        details = Style.c(attempt.data_summary, Style.GREEN)
        time_str = Style.c(f"({attempt.elapsed_ms:.0f}ms)", Style.DIM)
        return f"  │ {num}{provider_name} {E_ARROW} {status} {details} {time_str}"
    else:
        if attempt.error_type == 'RATE_LIMITED':
            status = Style.c(f"{E_WARNING} RATE LIMITED", Style.YELLOW)
        elif attempt.error_type == 'UNAVAILABLE':
            status = Style.c(f"{E_FAILED} UNAVAILABLE", Style.RED)
        elif attempt.error_type == 'NOT_SUPPORTED':
            status = Style.c(f"{E_SKIPPED} NOT SUPPORTED", Style.GRAY)
        elif attempt.error_type == 'NO_DATA':
            status = Style.c(f"{E_FAILED} NO DATA", Style.RED)
        else:
            status = Style.c(f"{E_FAILED} ERROR", Style.RED)

        error_msg = Style.c(f"({attempt.error})", Style.DIM) if attempt.error else ""
        return f"  │ {num}{provider_name} {E_ARROW} {status} {error_msg}"


def print_test_result(result: TestResult):
    """Print complete test result with all attempts."""
    print_data_type_header(result.emoji, result.data_type)

    # Print each provider attempt
    for i, attempt in enumerate(result.attempts):
        print(format_provider_attempt(attempt, i))

    # Print final result
    print(Style.c(f"  {'─' * 55}", Style.GRAY))
    if result.final_success:
        fallback_note = Style.c(" (fallback)", Style.YELLOW) if result.fallback_used else ""
        print(f"  │ {E_CHECK} {Style.c('Result:', Style.BOLD)} {result.final_provider}{fallback_note} {E_ARROW} {Style.c(result.final_data, Style.GREEN)}")
    else:
        print(f"  │ {E_CROSS} {Style.c('Result:', Style.BOLD)} {Style.c('All providers failed', Style.RED)}")


def print_summary(all_results: Dict[str, List[TestResult]], provider_status: Dict):
    """Print comprehensive test summary."""
    print()
    print(Style.c("═" * 77, Style.CYAN))
    print(Style.c(f"  {E_QUOTE} TEST SUMMARY", Style.BOLD))
    print(Style.c("═" * 77, Style.CYAN))

    # Count results
    total = 0
    passed = 0
    fallback_count = 0
    provider_success_count = {}

    for symbol, results in all_results.items():
        for result in results:
            total += 1
            if result.final_success:
                passed += 1
                provider_success_count[result.final_provider] = provider_success_count.get(result.final_provider, 0) + 1
            if result.fallback_used:
                fallback_count += 1

    pass_rate = (passed / total * 100) if total > 0 else 0

    # Statistics
    print()
    print(f"  {Style.c('Test Results:', Style.BOLD)}")
    print(f"    • Total:      {total}")
    print(f"    • Passed:     {Style.c(str(passed), Style.GREEN)} ({pass_rate:.0f}%)")
    print(f"    • Failed:     {Style.c(str(total - passed), Style.RED if total > passed else Style.GREEN)}")
    print(f"    • Fallbacks:  {Style.c(str(fallback_count), Style.YELLOW)} times")

    # Provider success breakdown
    if provider_success_count:
        print()
        print(f"  {Style.c('Data Sources Used:', Style.BOLD)}")
        max_count = max(provider_success_count.values()) if provider_success_count else 1
        for provider, count in sorted(provider_success_count.items(), key=lambda x: -x[1]):
            bar_len = int(count / max_count * 20)
            bar = Style.c('█' * bar_len, Style.GREEN) + Style.c('░' * (20 - bar_len), Style.GRAY)
            print(f"    • {provider:12} {bar} {count}")

    # Provider health dashboard
    print()
    print(f"  {Style.c('Provider Health:', Style.BOLD)}")
    for name, status in provider_status.items():
        health = status.get('health', 'unknown')
        if health == 'healthy':
            icon = E_SUCCESS
            health_str = Style.c("HEALTHY", Style.GREEN)
        elif health == 'rate_limited':
            icon = E_WARNING
            health_str = Style.c("RATE LIMITED", Style.YELLOW)
        elif health == 'degraded':
            icon = E_WARNING
            health_str = Style.c("DEGRADED", Style.YELLOW)
        else:
            icon = E_FAILED
            health_str = Style.c("UNAVAILABLE", Style.RED)

        print(f"    {icon} {name:12} {health_str}")

    print()
    print(Style.c("═" * 77, Style.CYAN))
    print()


# ═══════════════════════════════════════════════════════════════════════════════
# Test Functions
# ═══════════════════════════════════════════════════════════════════════════════

def classify_error(e: Exception, provider: str) -> Tuple[str, str]:
    """Classify an error into type and message."""
    error_msg = str(e)

    if 'Too Many Requests' in error_msg or '429' in error_msg or 'Rate' in error_msg.lower():
        return 'RATE_LIMITED', '429 Too Many Requests'
    elif 'token' in error_msg.lower() or 'auth' in error_msg.lower() or 'expired' in error_msg.lower():
        return 'UNAVAILABLE', 'Token expired/invalid'
    elif 'not support' in error_msg.lower():
        return 'NOT_SUPPORTED', 'Not supported'
    elif 'No data' in error_msg or 'empty' in error_msg.lower():
        return 'NO_DATA', 'No data returned'
    else:
        # Truncate long error messages
        return 'ERROR', error_msg[:50] if len(error_msg) > 50 else error_msg


def test_quote(service, symbol: str, adapters: Dict) -> TestResult:
    """Test quote data from all providers."""
    result = TestResult(data_type="Quote", emoji=E_QUOTE)

    # Test each adapter in priority order (market-aware)
    adapter_order = get_adapter_order_for_symbol(symbol)
    first_success = None

    for provider_name in adapter_order:
        adapter = adapters.get(provider_name)
        if not adapter:
            continue

        attempt = ProviderAttempt(provider=provider_name, success=False, elapsed_ms=0)

        # Check if provider supports this symbol
        if not adapter.supports_symbol(symbol):
            attempt.error_type = 'NOT_SUPPORTED'
            attempt.error = f"Symbol {symbol}"
            result.attempts.append(attempt)
            continue

        try:
            start = time.time()
            with quiet_call():
                quote = adapter.get_quote(symbol)
            elapsed = (time.time() - start) * 1000
            attempt.elapsed_ms = elapsed

            if quote and quote.current_price is not None:
                attempt.success = True
                attempt.data_summary = f"${quote.current_price:.2f}"
                if first_success is None:
                    first_success = (provider_name, f"${quote.current_price:.2f}", len(result.attempts) > 0)
            else:
                attempt.error_type = 'NO_DATA'
                attempt.error = 'No data returned'
        except Exception as e:
            attempt.error_type, attempt.error = classify_error(e, provider_name)

        result.attempts.append(attempt)

    # Set final result
    if first_success:
        result.final_success = True
        result.final_provider = first_success[0]
        result.final_data = first_success[1]
        result.fallback_used = first_success[2]

    return result


def test_history(service, symbol: str, adapters: Dict) -> TestResult:
    """Test history data from all providers."""
    result = TestResult(data_type="History (1mo)", emoji=E_HISTORY)

    # Market-aware provider ordering
    adapter_order = get_adapter_order_for_symbol(symbol)
    first_success = None

    for provider_name in adapter_order:
        adapter = adapters.get(provider_name)
        if not adapter:
            continue

        attempt = ProviderAttempt(provider=provider_name, success=False, elapsed_ms=0)

        if not adapter.supports_symbol(symbol):
            attempt.error_type = 'NOT_SUPPORTED'
            attempt.error = f"Symbol {symbol}"
            result.attempts.append(attempt)
            continue

        try:
            start = time.time()
            with quiet_call():
                history = adapter.get_history(symbol, period="1mo")
            elapsed = (time.time() - start) * 1000
            attempt.elapsed_ms = elapsed

            if history and not history.empty:
                attempt.success = True
                attempt.data_summary = f"{len(history.df)} rows"
                if first_success is None:
                    first_success = (provider_name, f"{len(history.df)} rows", len(result.attempts) > 0)
            else:
                attempt.error_type = 'NO_DATA'
                attempt.error = 'No data returned'
        except Exception as e:
            attempt.error_type, attempt.error = classify_error(e, provider_name)

        result.attempts.append(attempt)

    if first_success:
        result.final_success = True
        result.final_provider = first_success[0]
        result.final_data = first_success[1]
        result.fallback_used = first_success[2]

    return result


def test_fundamentals(service, symbol: str, adapters: Dict) -> TestResult:
    """Test fundamentals data from all providers."""
    result = TestResult(data_type="Fundamentals", emoji=E_FUND)

    # Market-aware provider ordering
    adapter_order = get_adapter_order_for_symbol(symbol)
    first_success = None

    for provider_name in adapter_order:
        adapter = adapters.get(provider_name)
        if not adapter:
            continue

        attempt = ProviderAttempt(provider=provider_name, success=False, elapsed_ms=0)

        if not adapter.supports_symbol(symbol):
            attempt.error_type = 'NOT_SUPPORTED'
            attempt.error = f"Symbol {symbol}"
            result.attempts.append(attempt)
            continue

        try:
            start = time.time()
            with quiet_call():
                fundamentals = adapter.get_fundamentals(symbol)
            elapsed = (time.time() - start) * 1000
            attempt.elapsed_ms = elapsed

            if fundamentals:
                pe = f"PE={fundamentals.pe_ratio:.1f}" if fundamentals.pe_ratio else "PE=N/A"
                pb = f"PB={fundamentals.pb_ratio:.1f}" if fundamentals.pb_ratio else "PB=N/A"
                attempt.success = True
                attempt.data_summary = f"{pe}, {pb}"
                if first_success is None:
                    first_success = (provider_name, f"{pe}, {pb}", len(result.attempts) > 0)
            else:
                attempt.error_type = 'NO_DATA'
                attempt.error = 'No data returned'
        except Exception as e:
            attempt.error_type, attempt.error = classify_error(e, provider_name)

        result.attempts.append(attempt)

    if first_success:
        result.final_success = True
        result.final_provider = first_success[0]
        result.final_data = first_success[1]
        result.fallback_used = first_success[2]

    return result


def test_options(service, symbol: str, adapters: Dict) -> TestResult:
    """Test options data from all providers."""
    from ..interfaces import DataType

    result = TestResult(data_type="Options", emoji=E_OPTIONS)

    # Options: only tiger and yfinance support options data
    adapter_order = get_adapter_order_for_symbol(symbol, include_options=True)
    first_success = None

    for provider_name in adapter_order:
        adapter = adapters.get(provider_name)
        if not adapter:
            continue

        attempt = ProviderAttempt(provider=provider_name, success=False, elapsed_ms=0)

        # Check if adapter supports options
        if DataType.OPTIONS_CHAIN not in adapter.supported_data_types:
            attempt.error_type = 'NOT_SUPPORTED'
            attempt.error = 'No options support'
            result.attempts.append(attempt)
            continue

        try:
            start = time.time()
            with quiet_call():
                expirations = adapter.get_options_expirations(symbol)

            if not expirations:
                attempt.error_type = 'NO_DATA'
                attempt.error = 'No expirations'
                attempt.elapsed_ms = (time.time() - start) * 1000
                result.attempts.append(attempt)
                continue

            with quiet_call():
                chain = adapter.get_options_chain(symbol, expirations[0])
            elapsed = (time.time() - start) * 1000
            attempt.elapsed_ms = elapsed

            if chain and not chain.empty:
                calls = len(chain.calls) if chain.calls is not None else 0
                puts = len(chain.puts) if chain.puts is not None else 0
                attempt.success = True
                attempt.data_summary = f"{calls}C/{puts}P ({expirations[0]})"
                if first_success is None:
                    first_success = (provider_name, f"{calls} calls, {puts} puts", len(result.attempts) > 0)
            else:
                attempt.error_type = 'NO_DATA'
                attempt.error = 'Empty chain'
        except Exception as e:
            attempt.error_type, attempt.error = classify_error(e, provider_name)

        result.attempts.append(attempt)

    if first_success:
        result.final_success = True
        result.final_provider = first_success[0]
        result.final_data = first_success[1]
        result.fallback_used = first_success[2]

    return result


def test_macro(service, symbol: str, adapters: Dict) -> TestResult:
    """Test macro ticker (^VIX, etc.)."""
    result = TestResult(data_type=f"Macro ({symbol})", emoji=E_MACRO)

    # Macro tickers: market-aware provider ordering
    adapter_order = get_adapter_order_for_symbol(symbol)
    first_success = None

    for provider_name in adapter_order:
        adapter = adapters.get(provider_name)
        if not adapter:
            continue

        attempt = ProviderAttempt(provider=provider_name, success=False, elapsed_ms=0)

        if not adapter.supports_symbol(symbol):
            attempt.error_type = 'NOT_SUPPORTED'
            attempt.error = 'Index not supported'
            result.attempts.append(attempt)
            continue

        try:
            start = time.time()
            with quiet_call():
                quote = adapter.get_quote(symbol)
            elapsed = (time.time() - start) * 1000
            attempt.elapsed_ms = elapsed

            if quote and quote.current_price is not None:
                attempt.success = True
                attempt.data_summary = f"{quote.current_price:.2f}"
                if first_success is None:
                    first_success = (provider_name, f"{quote.current_price:.2f}", len(result.attempts) > 0)
            else:
                attempt.error_type = 'NO_DATA'
                attempt.error = 'No data returned'
        except Exception as e:
            attempt.error_type, attempt.error = classify_error(e, provider_name)

        result.attempts.append(attempt)

    if first_success:
        result.final_success = True
        result.final_provider = first_success[0]
        result.final_data = first_success[1]
        result.fallback_used = first_success[2]

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# Main Test Runner
# ═══════════════════════════════════════════════════════════════════════════════

def run_tests(symbols: List[str], include_macro: bool = False):
    """Run all tests for given symbols."""
    # Start output capture to suppress noisy output
    output_capture.start()

    # Also use OS-level fd redirect for stubborn libraries
    saved_stdout_fd = os.dup(1)
    saved_stderr_fd = os.dup(2)
    devnull_fd = os.open(os.devnull, os.O_WRONLY)

    try:
        # Import service (with fully suppressed output)
        os.dup2(devnull_fd, 1)
        os.dup2(devnull_fd, 2)
        output_capture.suppress_output()

        from ..service import market_data_service
        adapters = market_data_service._adapters

        # Restore output
        os.dup2(saved_stdout_fd, 1)
        os.dup2(saved_stderr_fd, 2)
        output_capture.restore_output()

        print_header()

        all_results: Dict[str, List[TestResult]] = {}

        for symbol in symbols:
            print_symbol_header(symbol)
            symbol_results = []

            # Test quote
            result = test_quote(market_data_service, symbol, adapters)
            print_test_result(result)
            symbol_results.append(result)

            # Test history
            result = test_history(market_data_service, symbol, adapters)
            print_test_result(result)
            symbol_results.append(result)

            # Test fundamentals
            result = test_fundamentals(market_data_service, symbol, adapters)
            print_test_result(result)
            symbol_results.append(result)

            # Test options (skip for macro tickers)
            if not symbol.startswith('^'):
                result = test_options(market_data_service, symbol, adapters)
                print_test_result(result)
                symbol_results.append(result)

            all_results[symbol] = symbol_results

        # Test macro ticker if requested
        if include_macro:
            symbol = "^VIX"
            print_symbol_header(symbol)
            result = test_macro(market_data_service, symbol, adapters)
            print_test_result(result)
            all_results[symbol] = [result]

        # Print summary
        with quiet_call():
            provider_status = market_data_service.get_provider_status()
            stats = market_data_service.get_stats()

        print_summary(all_results, provider_status)

        # Print cache stats
        print(f"  {Style.c(E_CLOCK + ' Cache Stats:', Style.DIM)} L1 Hit Rate: {stats['cache']['l1_hit_rate']:.1%}")
        print(f"  {Style.c(E_PROVIDER + ' Dedup Stats:', Style.DIM)} {stats['deduplication']['deduplicated']} deduplicated / {stats['deduplication']['requests']} requests")
        print()

    finally:
        # Restore everything
        try:
            os.close(devnull_fd)
            os.close(saved_stdout_fd)
            os.close(saved_stderr_fd)
        except:
            pass
        output_capture.stop()


def main():
    parser = argparse.ArgumentParser(
        description='Market Data Provider Test Runner',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m app.services.market_data.tests.test_runner AAPL TSLA
  python -m app.services.market_data.tests.test_runner --symbols AAPL,MSFT,GOOGL
  python -m app.services.market_data.tests.test_runner --all
  python -m app.services.market_data.tests.test_runner AAPL --macro
        """
    )
    parser.add_argument('symbols', nargs='*', help='Symbols to test')
    parser.add_argument('--symbols', '-s', dest='symbol_list', help='Comma-separated list of symbols')
    parser.add_argument('--all', '-a', action='store_true', help='Test all default symbols')
    parser.add_argument('--macro', '-m', action='store_true', help='Include macro ticker test (^VIX)')

    args = parser.parse_args()

    # Determine symbols to test
    if args.all:
        symbols = ['AAPL', 'TSLA', 'MSFT', 'GOOGL', 'NVDA']
    elif args.symbol_list:
        symbols = [s.strip().upper() for s in args.symbol_list.split(',')]
    elif args.symbols:
        symbols = [s.upper() for s in args.symbols]
    else:
        # Default
        symbols = ['AAPL']

    run_tests(symbols, include_macro=args.macro)


if __name__ == '__main__':
    main()

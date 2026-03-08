# Market Data Service

The Market Data Service is the core data abstraction layer for the AlphaGBM platform. It provides unified access to market data from multiple providers with automatic failover, caching, request deduplication, and comprehensive metrics tracking.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Application Layer                            │
│   (stock_analysis, options_service, recommendation_service, etc.)   │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     MarketDataService (Singleton)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │   Request    │  │  Multi-Level │  │     Metrics Collector    │  │
│  │ Deduplicator │  │    Cache     │  │   (per-call tracking)    │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
     ┌───────────────────────────┼───────────────────────────┐
     │                           │                           │
     ▼                           ▼                           ▼
┌────────────┐            ┌────────────┐            ┌────────────────┐
│  YFinance  │            │   Tiger    │            │   DefeatBeta   │
│  Adapter   │            │  Adapter   │            │    Adapter     │
│ (priority 10)           │(priority 15)            │ (priority 20)  │
└────────────┘            └────────────┘            └────────────────┘
                                 │
                                 ▼
                          ┌────────────────┐
                          │ Alpha Vantage  │
                          │    Adapter     │
                          │ (priority 25)  │
                          └────────────────┘
```

## Key Features

- **Multi-Provider Fallback**: Automatic failover between data providers
- **Request Deduplication**: Prevents duplicate API calls within configurable time window
- **Multi-Level Caching**: In-memory LRU cache with per-provider TTL configuration
- **Metrics & Monitoring**: Comprehensive tracking of success rates, latency, and errors
- **Thread-Safe**: All operations are thread-safe for concurrent access

## Quick Start

```python
from app.services.market_data import market_data_service

# Get real-time quote
quote = market_data_service.get_quote("AAPL")
print(f"Price: ${quote.current_price}")

# Get historical data
history = market_data_service.get_history("AAPL", period="1mo")
print(f"Data points: {len(history.df)}")

# Get options chain
chain = market_data_service.get_options_chain("AAPL", "2024-03-15")
print(f"Calls: {len(chain.calls)}, Puts: {len(chain.puts)}")

# Get service statistics
stats = market_data_service.get_stats()
print(f"Cache hit rate: {stats['cache']['l1_hit_rate']:.1%}")
```

## Data Providers

### Provider Priority and Capabilities

| Provider | Priority | Quote | History | Info | Fundamentals | Options | Earnings | Markets |
|----------|----------|-------|---------|------|--------------|---------|----------|---------|
| yfinance | 10 (Primary) | Yes | Yes | Yes | Yes | Yes | Yes | US, HK |
| tiger | 15 | Yes | Yes | No | No | Yes (Priority) | No | US, HK, CN |
| defeatbeta | 20 | Yes | Yes | Yes | Yes | No | Yes | US |
| alpha_vantage | 25 | Yes | Yes | Yes | Yes | No | No | US |

### Provider-Specific Notes

#### yfinance (Primary)
- Free tier with reasonable rate limits
- Comprehensive data coverage
- Used as primary for most data types

#### Tiger API (Options Priority)
- **Preferred source for options data**
- Real-time options chain with Greeks
- Supports US, HK, and China markets
- Requires API key configuration

#### DefeatBeta (Local DuckDB)
- Local database with historical US stock data
- No rate limits
- Used as fallback for stock data
- Does not support options

#### Alpha Vantage
- Rate limited (5 requests/minute on free tier)
- Used as final fallback
- Longer cache TTL to maximize cache hits

## API Reference

### get_quote(symbol, market=None)
Get real-time quote for a symbol.

**Returns**: `QuoteData` with fields:
- `current_price`: Current stock price
- `previous_close`: Previous day's close
- `open_price`: Day's open price
- `day_high`, `day_low`: Day's high/low
- `volume`: Trading volume
- `market_cap`: Market capitalization
- `source`: Which provider returned this data

**Data Sources**: yfinance → tiger → defeatbeta → alpha_vantage

---

### get_history(symbol, period=None, start=None, end=None, market=None)
Get historical OHLCV data.

**Parameters**:
- `period`: Period string (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max)
- `start`, `end`: Alternative to period, specify date range

**Returns**: `HistoryData` with:
- `df`: DataFrame with DatetimeIndex, columns: Open, High, Low, Close, Volume
- `source`: Which provider returned this data

**Data Sources**: yfinance → tiger → defeatbeta → alpha_vantage

---

### get_info(symbol, market=None)
Get company information.

**Returns**: `CompanyInfo` with fields:
- `name`: Company name
- `sector`, `industry`: Classification
- `country`: Country of incorporation
- `description`: Business summary
- `employees`: Full-time employees
- `website`: Company website
- `source`: Data source

**Data Sources**: yfinance → defeatbeta → alpha_vantage

---

### get_fundamentals(symbol, market=None)
Get fundamental metrics.

**Returns**: `FundamentalsData` with fields:
- Valuation: `pe_ratio`, `forward_pe`, `pb_ratio`, `ps_ratio`, `peg_ratio`, `ev_ebitda`
- Profitability: `profit_margin`, `operating_margin`, `roe`, `roa`
- Growth: `revenue_growth`, `earnings_growth`
- Other: `beta`, `dividend_yield`, `eps_trailing`, `eps_forward`
- Analyst: `target_high`, `target_low`, `target_mean`, `recommendation`

**Data Sources**: yfinance → defeatbeta → alpha_vantage

---

### get_options_expirations(symbol, market=None)
Get available option expiration dates.

**Returns**: `List[str]` of expiry dates in YYYY-MM-DD format

**Data Sources**: tiger (priority) → yfinance

---

### get_options_chain(symbol, expiry, market=None)
Get options chain for a specific expiry.

**Returns**: `OptionsChainData` with:
- `expiry_date`: Expiration date
- `underlying_price`: Current stock price
- `calls`: DataFrame with call options
- `puts`: DataFrame with put options
- Each row includes: strike, bid, ask, last, volume, oi, iv, delta, gamma, theta, vega

**Data Sources**: tiger (priority) → yfinance

---

### get_earnings(symbol, market=None)
Get quarterly earnings data.

**Returns**: `EarningsData` with:
- `quarterly_earnings`: DataFrame with Date index, Earnings, Revenue columns

**Data Sources**: yfinance → defeatbeta

---

### get_ticker_data(symbol)
Get comprehensive ticker data (backward compatible).

**Returns**: Dict with all fields from quote, info, and fundamentals combined.
Compatible with code expecting `yf.Ticker().info` format.

## Cache Configuration

### Per-Provider Cache TTL (seconds)

| Data Type | yfinance | tiger | defeatbeta | alpha_vantage |
|-----------|----------|-------|------------|---------------|
| quote | 60 | 60 | 120 | 300 |
| history | 300 | 300 | 600 | 900 |
| fundamentals | 3600 | 3600 | 7200 | 7200 |
| info | 86400 | 86400 | 172800 | 172800 |
| options_chain | 120 | 90 | 120 | 300 |
| options_expirations | 300 | 180 | 300 | 300 |
| earnings | 3600 | 3600 | 7200 | 7200 |
| macro | 60 | 60 | 120 | 300 |

**Design Rationale**:
- **Tiger**: Shorter TTL for options (90s) since it's the priority source and we want fresh data
- **DefeatBeta**: Longer TTLs since local data is reliable and doesn't have rate limits
- **Alpha Vantage**: Longest TTLs to minimize API calls due to rate limiting

## Metrics & Monitoring

### Accessing Metrics

```python
# Get comprehensive statistics
stats = market_data_service.get_stats()

# Get detailed metrics
metrics = market_data_service.get_metrics()

# Get provider health
health = market_data_service.get_provider_health("tiger")

# Get latency percentiles
latency = market_data_service.get_latency_percentiles(provider="yfinance")
# Returns: {'p50': 150.2, 'p90': 320.5, 'p95': 450.1, 'p99': 890.3}

# Get recent calls (with filtering)
recent = market_data_service.get_recent_calls(
    limit=50,
    data_type=DataType.OPTIONS_CHAIN,
    errors_only=True
)
```

### Metrics Structure

```python
{
    "uptime": {
        "start_time": "2024-01-15T10:30:00",
        "uptime_seconds": 3600
    },
    "totals": {
        "total_calls": 1500,
        "cache_hits": 800,
        "cache_hit_rate": 53.33,
        "failures": 25,
        "failure_rate": 1.67,
        "fallback_used": 50,
        "fallback_rate": 3.33
    },
    "by_provider": {
        "yfinance": {
            "total_calls": 700,
            "successful_calls": 680,
            "success_rate": 97.14,
            "avg_latency_ms": 180.5,
            "min_latency_ms": 50.2,
            "max_latency_ms": 890.3,
            "last_error": "HTTPError",
            "last_error_time": "2024-01-15T11:20:00"
        },
        "tiger": {...},
        "defeatbeta": {...}
    },
    "by_data_type": {
        "quote": {
            "total_calls": 500,
            "cache_hits": 300,
            "cache_hit_rate": 60.0,
            "fallback_used": 10,
            "failures": 5
        },
        "options_chain": {...}
    },
    "recent_errors": [...]
}
```

### JSON Logging

The MetricsCollector automatically logs structured JSON for ops visibility:

```json
{
    "event": "market_data_call",
    "timestamp": "2024-01-15T11:25:30.123456",
    "data_type": "quote",
    "symbol": "AAPL",
    "providers_tried": ["yfinance"],
    "provider_used": "yfinance",
    "result": "success",
    "cache_hit": false,
    "latency_ms": 145.32,
    "fallback_used": false
}
```

## Error Handling

### Fallback Behavior

When a provider fails:
1. Error is logged with details
2. Next provider in priority order is attempted
3. If all providers fail, `None` is returned
4. Metrics record the failure and fallback usage

### Provider Health States

- `HEALTHY`: Success rate >= 95%
- `DEGRADED`: Success rate >= 80%
- `UNHEALTHY`: Success rate < 80%
- `RATE_LIMITED`: Provider is currently rate-limited

### Automatic Recovery

Providers automatically recover after cooldown:
- yfinance: 60s cooldown, 3 consecutive failures to mark unhealthy
- tiger: 60s cooldown, 3 consecutive failures
- defeatbeta: 30s cooldown, 5 consecutive failures
- alpha_vantage: 120s cooldown, 2 consecutive failures

## Thread Safety

All components are thread-safe:
- `MarketDataService`: Singleton with lock protection
- `MultiLevelCache`: Thread-safe LRU cache with locks
- `RequestDeduplicator`: Thread-safe request grouping
- `MetricsCollector`: Thread-safe metrics aggregation

## Configuration

### Environment Variables

```bash
# Tiger API (optional, will auto-disable if not set)
TIGER_ID=your_tiger_id
TIGER_PRIVATE_KEY_PATH=/path/to/key.pem

# Alpha Vantage (optional)
ALPHA_VANTAGE_API_KEY=your_api_key
```

### Custom Provider Configuration

```python
from app.services.market_data.config import ProviderConfig, ProviderCacheTTL

# Create custom cache TTL
custom_ttl = ProviderCacheTTL(
    quote=30,      # 30 seconds for quotes
    history=180,   # 3 minutes for history
    # ... other data types
)

# Create custom provider config
custom_config = ProviderConfig(
    name="custom_provider",
    priority=5,  # Higher priority than yfinance
    requests_per_minute=120,
    cache_ttl=custom_ttl,
)
```

## Directory Structure

```
market_data/
├── __init__.py           # Module exports
├── service.py            # MarketDataService (main entry point)
├── interfaces.py         # Data classes and abstract adapter
├── config.py             # Provider configs and cache TTL
├── cache.py              # Multi-level LRU cache
├── deduplicator.py       # Request deduplication
├── metrics.py            # Metrics collection and monitoring
├── adapters/             # Provider implementations
│   ├── __init__.py
│   ├── base.py
│   ├── yfinance_adapter.py
│   ├── tiger_adapter.py
│   ├── defeatbeta_adapter.py
│   └── alpha_vantage_adapter.py
├── tests/                # Unit tests
│   ├── test_adapters.py
│   ├── test_service.py
│   ├── test_cache.py
│   └── test_metrics.py
└── README.md             # This file
```

## Performance Considerations

1. **Cache First**: Always checks cache before making API calls
2. **Deduplication**: Concurrent requests for same data share single API call
3. **Provider Priority**: Faster/more reliable providers have higher priority
4. **Per-Provider TTL**: Rate-limited providers have longer cache TTL

## Extending with New Providers

To add a new data provider:

1. Create adapter class extending `DataProviderAdapter`
2. Implement required methods (`get_quote`, `get_history`, etc.)
3. Add provider configuration to `config.py`
4. Register adapter in `MarketDataService._register_default_adapters()`

```python
from app.services.market_data.interfaces import DataProviderAdapter

class NewProviderAdapter(DataProviderAdapter):
    @property
    def name(self) -> str:
        return "new_provider"

    @property
    def supported_data_types(self) -> List[DataType]:
        return [DataType.QUOTE, DataType.HISTORY]

    # Implement other required methods...
```

## Troubleshooting

### Common Issues

1. **All providers failing**: Check network connectivity and API keys
2. **High fallback rate**: Primary provider may be rate-limited
3. **Cache not working**: Verify `memory_enabled=True` in CacheConfig
4. **Options data missing**: Ensure Tiger API is configured correctly

### Debug Logging

Enable debug logging to see detailed operation:

```python
import logging
logging.getLogger("app.services.market_data").setLevel(logging.DEBUG)
```

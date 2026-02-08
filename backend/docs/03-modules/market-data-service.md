# Market Data Service 模块

## 1. 模块概述

Market Data Service 是行情数据的统一入口层，为整个应用提供股票行情、历史数据、基本面、期权链等数据获取能力。

**核心架构决策：**

- **多数据源统一接口** — 5 个 adapter 实现相同的 `DataProviderAdapter` 抽象基类，上层无需感知底层数据源
- **自动 failover** — 按 market + data_type 自动选择 adapter 优先级链，主力源失败后切换备用源
- **多级缓存** — 内存 LRU (L1) + 数据库 (L2)，不同数据类型使用不同 TTL
- **请求去重** — 500ms 窗口内相同请求合并为一次 API 调用，避免浪费 rate limit
- **单例模式 (thread-safe)** — `__new__()` + `threading.Lock` 保证全局唯一实例

**请求处理流程：**

```
get_quote("AAPL")
  ├─ MultiLevelCache 命中 → 直接返回 (metrics 记录 cache_hit)
  └─ Cache 未命中
       ├─ RequestDeduplicator: 500ms 窗口内有 in-flight → 等待共享结果
       ├─ market_detector: AAPL → Market.US
       ├─ _get_providers_for_data_type(): [yfinance(10), tiger(15), defeatbeta(20)]
       ├─ 遍历 provider 链: 成功 → 写入 cache 并返回; 失败 → 尝试下一个
       └─ metrics_collector 记录延迟、provider_used、fallback 情况
```

---

## 2. MarketDataService 核心类

**文件：** `app/services/market_data/service.py`（846 行）

### 2.1 单例 + 初始化

```python
class MarketDataService:
    _instance = None
    _lock = Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized: return
        self._adapters: Dict[str, DataProviderAdapter] = {}
        self._configs = PROVIDER_CONFIGS.copy()
        self._cache = MultiLevelCache(CacheConfig())
        self._deduplicator = RequestDeduplicator(window_ms=500)
        self._register_default_adapters()  # 注册 5 个 adapter
        self._initialized = True
```

### 2.2 Provider 路由

`_get_providers_for_data_type(data_type, market, symbol)` 路由逻辑：

1. 过滤：`config.enabled` + `data_type in supported_data_types` + `market in supported_markets`
2. 符号级过滤：`adapter.supports_symbol(symbol)`
3. 被 rate limit 的 provider 优先级 +1000（降级但不排除）
4. 按 `config.priority` 升序排序（数值越小优先级越高）

### 2.3 公开 API

| 方法 | 返回类型 | 说明 |
|------|---------|------|
| `get_quote(symbol, market?)` | `Optional[QuoteData]` | 实时行情 |
| `get_history(symbol, ...)` | `Optional[HistoryData]` | 历史 OHLCV |
| `get_info(symbol)` | `Optional[CompanyInfo]` | 公司信息 |
| `get_fundamentals(symbol)` | `Optional[FundamentalsData]` | 基本面指标 |
| `get_options_chain(symbol, expiry)` | `Optional[OptionsChainData]` | 期权链 |
| `get_earnings(symbol)` | `Optional[EarningsData]` | 季度财报 |
| `get_ticker_data(symbol)` | `dict` | 兼容 yf.Ticker().info |

每个方法内部均遵循：cache check → dedup → provider chain → cache write → metrics record。

---

## 3. 适配器接口

**文件：** `app/services/market_data/interfaces.py`（372 行）

### 3.1 DataProviderAdapter 抽象基类

必须实现的抽象方法：

- `name` (property) — provider 名称
- `supported_data_types` (property) — 支持的数据类型列表
- `supported_markets` (property) — 支持的市场列表
- `get_quote(symbol)` → `Optional[QuoteData]`
- `get_history(symbol, period?, start?, end?)` → `Optional[HistoryData]`
- `get_info(symbol)` → `Optional[CompanyInfo]`
- `get_fundamentals(symbol)` → `Optional[FundamentalsData]`
- `health_check()` → `ProviderStatus`
- `is_rate_limited()` → `bool`

可选覆写（默认返回 None）：`get_options_expirations()`, `get_options_chain()`, `get_earnings()`

设计原则：不可用数据返回 `None`，不抛异常；只有不可恢复的错误才 raise。

### 3.2 枚举类型

| 枚举 | 值 |
|------|---|
| `DataType` | QUOTE, HISTORY, INFO, FUNDAMENTALS, OPTIONS_CHAIN, OPTIONS_EXPIRATIONS, EARNINGS, MACRO |
| `Market` | US, HK, CN |
| `ProviderStatus` | HEALTHY, DEGRADED, RATE_LIMITED, UNAVAILABLE |

### 3.3 标准化数据类

| 类名 | 核心字段 |
|------|---------|
| `QuoteData` | symbol, current_price, previous_close, volume, market_cap |
| `FundamentalsData` | pe_ratio, forward_pe, pb_ratio, roe, profit_margin, beta |
| `CompanyInfo` | symbol, name, sector, industry, country, exchange |
| `HistoryData` | symbol, df (DataFrame: OHLCV), period, source |
| `OptionsChainData` | symbol, expiry_date, underlying_price, calls (df), puts (df) |
| `EarningsData` | symbol, quarterly_earnings (DataFrame) |
| `DataFetchResult` | success, data, source, fallback_used, error, cached |

所有数据类提供 `.to_dict()` 方法，兼容旧版 yfinance 字段命名（如 `current_price` → `currentPrice`）。

---

## 4. 五个适配器详解

### 4.1 YFinanceAdapter — 默认/美股主力

**文件：** `adapters/yfinance_adapter.py`（351 行）
**priority:** 10 | **市场:** US, HK
**支持:** QUOTE, HISTORY, INFO, FUNDAMENTALS, OPTIONS_CHAIN, OPTIONS_EXPIRATIONS, EARNINGS, MACRO
**底层:** `yfinance` (非官方 Yahoo Finance API) | **rate limit:** 100 req/min, 2000 req/day
**限制:** 非官方 API，高频调用可能被限流

### 4.2 DefeatBetaAdapter — 美股备用

**文件：** `adapters/defeatbeta_adapter.py`（439 行）
**priority:** 20 | **市场:** US only
**支持:** QUOTE, HISTORY, INFO, FUNDAMENTALS, EARNINGS
**底层:** 本地 DuckDB 数据源 | **rate limit:** 1000 req/min（本地，几乎无限制）
**限制:** 不支持期权链，数据可能有延迟

### 4.3 TigerAdapter — 港股主力 / 期权优先

**文件：** `adapters/tiger_adapter.py`（894 行）
**priority:** 15 | **市场:** US, HK, CN
**支持:** QUOTE, HISTORY, OPTIONS_CHAIN, OPTIONS_EXPIRATIONS
**底层:** Tiger Open API | **rate limit:** 60 req/min, 5000 req/day
**需要:** 环境变量 `TIGER_ID` + `TIGER_PRIVATE_KEY`
**优势:** 港股实时行情，期权链含更好的 IV/Greeks 数据

### 4.4 AlphaVantageAdapter — 历史数据备用

**文件：** `adapters/alphavantage_adapter.py`（380 行）
**priority:** 25 | **市场:** US only
**支持:** QUOTE, HISTORY, INFO, FUNDAMENTALS
**底层:** Alpha Vantage REST API | **rate limit:** 5 req/min, 500 req/day（免费层）
**策略:** cache TTL 较长（quote 5min, info 48h）以减少调用

### 4.5 TushareAdapter — A 股主力

**文件：** `adapters/tushare_adapter.py`（584 行）
**priority:** 10 (CN 市场最高) | **市场:** CN only
**支持:** QUOTE, HISTORY, INFO, FUNDAMENTALS
**底层:** Tushare Pro API | **rate limit:** 200 req/min, 10000 req/day
**需要:** 环境变量 `TUSHARE_TOKEN`
**特色:** A 股行情、基本面、资金流、行业分类数据

### 4.6 Base Adapter 公共基类

**文件：** `adapters/base.py`

- `ConcurrencyLimiter` — Semaphore 控制最大并发请求数（默认 10）
- Circuit breaker 模式 — 连续失败超过阈值后自动熔断
- Rate limit 检测与追踪
- 健康状态管理（`last_success`, `last_failure` 时间戳）

---

## 5. 缓存策略

**文件：** `app/services/market_data/cache.py`（291 行）

### 5.1 MultiLevelCache 架构

```
请求 → L1 内存 LRU → 命中? → 返回
                        └─ 未命中 → L2 数据库 → 命中? → 回填 L1, 返回
                                                  └─ 未命中 → 调用 API
```

**L1 实现：** 基于 `OrderedDict` 的 LRU Cache，thread-safe（`threading.Lock`），最大 1000 条目。

### 5.2 默认 TTL 配置

| 数据类型 | 默认 TTL | 说明 |
|---------|---------|------|
| QUOTE | 60s | 实时价格，短缓存 |
| HISTORY | 300s | 历史数据变动频率低 |
| FUNDAMENTALS | 3600s | PE/PB 等日内变化小 |
| INFO | 86400s | 公司名称/行业极少变动 |
| OPTIONS_CHAIN | 120s | 期权价格波动大 |
| EARNINGS | 3600s | 财报按季度更新 |
| MACRO | 60s | VIX 等需要实时性 |

各 adapter 可通过 `ProviderCacheTTL` 覆写默认值。例如 AlphaVantage 的 quote TTL 为 300s。

---

## 6. 请求去重

**文件：** `app/services/market_data/deduplicator.py`（188 行）

`RequestDeduplicator` 解决多线程同时查询同一 ticker 时的重复 API 调用问题：

```
Thread A: get_quote("AAPL") → 首次请求，发起 API 调用
Thread B: get_quote("AAPL") → 500ms 内，等待 Thread A 结果
Thread C: get_quote("AAPL") → 同上
                                └─ API 返回 → A/B/C 三个线程共享同一结果
```

核心机制：
- `InFlightRequest` dataclass + `threading.Event` 实现等待/通知
- 请求 key 由 `(data_type, symbol, params)` 经 `hashlib` 生成
- 去重窗口默认 500ms（`window_ms` 参数可配）

---

## 7. 指标收集

**文件：** `app/services/market_data/metrics.py`（569 行）

全局 `metrics_collector` 单例自动记录每次 API 调用：

| 字段 | 类型 | 说明 |
|------|-----|------|
| `timestamp` | `datetime` | 调用时间 |
| `data_type` | `DataType` | 数据类型 |
| `symbol` | `str` | 股票代码 |
| `providers_tried` | `List[str]` | 尝试过的 provider |
| `provider_used` | `Optional[str]` | 最终成功的 provider |
| `result` | `CallResult` | SUCCESS / CACHE_HIT / FALLBACK / FAILURE / TIMEOUT / RATE_LIMITED |

存储方式：内存 ring buffer（`deque`）+ 结构化 JSON 日志，通过 `get_stats()` 暴露给 API 端点。

---

## 8. 市场检测

**文件：** `app/services/market_data/market_detector.py`（225 行）

### 8.1 detect_market(symbol) 规则

| 优先级 | 规则 | 示例 | 结果 |
|--------|-----|------|------|
| 1 | 后缀 `.HK` | `0700.HK` | `Market.HK` |
| 2 | 后缀 `.SS`/`.SZ`/`.SH` | `600519.SS` | `Market.CN` |
| 3 | 6 位纯数字 + A 股前缀 | `600519` | `Market.CN` |
| 4 | 默认 | `AAPL` | `Market.US` |

### 8.2 A 股代码前缀规则

| 前缀 | 交易所 | 板块 |
|------|--------|-----|
| `60` | 上海 (.SS) | 主板 |
| `68` | 上海 (.SS) | 科创板 |
| `00` | 深圳 (.SZ) | 主板 |
| `30` | 深圳 (.SZ) | 创业板 |

特殊 ticker：`MACRO_TICKERS`（`^GSPC`, `^VIX` 等）和 `INDEX_ETFS`（`SPY`, `QQQ` 等）在 `config.py` 中定义。

---

## 9. Failover 链

根据 `config.py` 中各 provider 的 `priority` 和 `supported_markets`：

**美股 (US):** yfinance(10) → Tiger(15) → DefeatBeta(20) → AlphaVantage(25)
**港股 (HK):** yfinance(10) → Tiger(15)
**A 股 (CN):** Tushare(10) → Tiger(15)

**降级机制：**
- 被 rate limit 的 provider：priority 临时 +1000（降至最后但不排除）
- 连续失败超过 `max_consecutive_failures` 次 → 标记 UNAVAILABLE
- `cooldown_on_error_seconds` 后自动恢复（`auto_recover=True`）

---

## 10. DataProvider 门面类

**文件：** `app/services/data_provider.py`（258 行）

`DataProvider` 是对 `MarketDataService` 的门面封装，提供与 `yfinance.Ticker` 兼容的接口：

```python
# 旧代码                           # 新代码（接口完全兼容）
stock = yf.Ticker("AAPL")          stock = DataProvider("AAPL")
price = stock.info["currentPrice"]  price = stock.info["currentPrice"]
hist = stock.history(period="1mo")  hist = stock.history(period="1mo")
```

| 接口 | 类型 | 底层调用 |
|------|-----|---------|
| `.info` | property | `market_data_service.get_ticker_data()` |
| `.history(period, start, end)` | method | `market_data_service.get_history()` |
| `.quarterly_earnings` | property | `market_data_service.get_earnings()` |
| `.options` | property | `get_options_expirations()` |
| `.option_chain(date)` | method | `get_options_chain()` |
| `.fast_info` | property | `market_data_service.get_quote()` |
| `.get_margin_rate()` | method | 保证金比率查询 |

**推荐：** 新代码直接使用 `market_data_service` 单例：

```python
from app.services.market_data import market_data_service
quote = market_data_service.get_quote("AAPL")
```

---

## 11. 文件路径清单

```
backend/app/services/market_data/
├── __init__.py                     # 模块入口，导出 market_data_service 单例
├── service.py                      # MarketDataService 核心类 (846 行)
├── interfaces.py                   # 抽象接口 + 数据类定义 (372 行)
├── config.py                       # Provider 配置、优先级、cache TTL
├── cache.py                        # MultiLevelCache 多级缓存 (291 行)
├── deduplicator.py                 # RequestDeduplicator 请求去重 (188 行)
├── metrics.py                      # metrics_collector 指标收集 (569 行)
├── market_detector.py              # detect_market() 市场检测 (225 行)
├── adapters/
│   ├── __init__.py                 # 适配器导出
│   ├── base.py                     # 公共基类: ConcurrencyLimiter, circuit breaker
│   ├── yfinance_adapter.py         # YFinanceAdapter (351 行)
│   ├── defeatbeta_adapter.py       # DefeatBetaAdapter (439 行)
│   ├── tiger_adapter.py            # TigerAdapter (894 行)
│   ├── alphavantage_adapter.py     # AlphaVantageAdapter (380 行)
│   └── tushare_adapter.py          # TushareAdapter (584 行)
└── tests/
    ├── test_cache.py               # 缓存单元测试
    ├── test_market_detector.py     # 市场检测单元测试
    ├── test_metrics.py             # 指标收集单元测试
    └── test_runner.py              # 测试运行入口

backend/app/services/
└── data_provider.py                # DataProvider 门面类 (258 行)
```

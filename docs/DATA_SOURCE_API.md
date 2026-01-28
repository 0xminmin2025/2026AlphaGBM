# Data Source & API Reference

This document catalogs every external data source and API used in the AlphaGBM system for stock analysis and options analysis, including what data we need, which APIs currently provide it, and what fallback strategies are in place.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Data Needs Summary](#2-data-needs-summary)
3. [API Source: yfinance](#3-api-source-yfinance)
4. [API Source: Tiger API (tigeropen)](#4-api-source-tiger-api-tigeropen)
5. [API Source: defeatbeta-api](#5-api-source-defeatbeta-api)
6. [API Source: AkShare](#6-api-source-akshare)
7. [API Source: Google Gemini](#7-api-source-google-gemini)
8. [API Source: ExchangeRate-API](#8-api-source-exchangerate-api)
9. [API Source: Alpha Vantage (Unused)](#9-api-source-alpha-vantage-unused)
10. [Market Alerts & Macro Data Sources (市场预警)](#10-market-alerts--macro-data-sources-市场预警)
11. [Fallback Chain per Data Type](#11-fallback-chain-per-data-type)
12. [defeatbeta-api: Unused Methods Available](#12-defeatbeta-api-unused-methods-available)
13. [Stability Improvement Opportunities](#13-stability-improvement-opportunities)

---

## 1. Architecture Overview

```
                      +-----------------+
                      |   Frontend UI   |
                      +--------+--------+
                               |
                      +--------v--------+
                      |   Backend API   |
                      +--------+--------+
                               |
          +--------------------+--------------------+
          |                    |                    |
  +-------v-------+   +-------v-------+   +-------v-------+
  | Stock Analysis |   |Options Analysis|  |  Scheduler /  |
  |   Engine       |   |   Engine       |  |  Services     |
  +-------+-------+   +-------+-------+   +-------+-------+
          |                    |                    |
          +--------------------+--------------------+
                               |
               +---------------+---------------+
               |               |               |
       +-------v---+   +------v------+  +-----v------+
       |  yfinance  |   | Tiger API   |  | defeatbeta |
       | (Primary)  |   | (Options)   |  | (Fallback) |
       +------------+   +-------------+  +------------+
```

**Key Principle**: Multi-source fallback for resilience. Each data type has a primary source and one or more fallbacks.

---

## 2. Data Needs Summary

This table maps every data type we need to the APIs that currently provide it.

### Stock Analysis Data Needs

| # | Data Need | Primary API | Fallback API | Used By |
|---|-----------|-------------|--------------|---------|
| 1 | Current stock price | yfinance `ticker.info` | defeatbeta `price()` | Stock analysis, scheduler, options |
| 2 | Historical OHLCV (daily) | yfinance `ticker.history()` | defeatbeta `price()` | Technical analysis, charting |
| 3 | Market cap | yfinance `ticker.info['marketCap']` | defeatbeta `summary()` | Valuation, scoring |
| 4 | PE ratio (trailing/forward) | yfinance `ticker.info` | defeatbeta `summary()` | Valuation scoring |
| 5 | EPS (trailing/forward) | yfinance `ticker.info` | defeatbeta `summary()` | Earnings analysis |
| 6 | Beta | yfinance `ticker.info` | defeatbeta `summary()` | Risk scoring |
| 7 | Sector / Industry | yfinance `ticker.info` | defeatbeta `info()` | Sector comparison |
| 8 | Revenue YoY growth | yfinance `ticker.info` | defeatbeta `quarterly_revenue_yoy_growth()` | Growth scoring |
| 9 | Earnings YoY growth | yfinance `ticker.info` | defeatbeta `quarterly_net_income_yoy_growth()` | Growth scoring |
| 10 | Net margin | yfinance `ticker.info` | defeatbeta `quarterly_net_margin()` | Profitability scoring |
| 11 | Operating margin | yfinance `ticker.info` | defeatbeta `quarterly_operating_margin()` | Profitability scoring |
| 12 | ROE | yfinance `ticker.info` | defeatbeta `roe()` | Profitability scoring |
| 13 | ROA | yfinance `ticker.info` | defeatbeta `roa()` | Profitability scoring |
| 14 | P/B ratio | yfinance `ticker.info` | defeatbeta `pb_ratio()` | Valuation scoring |
| 15 | P/S ratio | yfinance `ticker.info` | defeatbeta `ps_ratio()` | Valuation scoring |
| 16 | TTM revenue | yfinance `ticker.info` | defeatbeta `ttm_revenue()` | Valuation scoring |
| 17 | Dividend history | yfinance `ticker.info` | defeatbeta `dividends()` | Income scoring |
| 18 | Quarterly earnings (EPS history) | yfinance `ticker.quarterly_earnings` | defeatbeta `earnings()` | PE percentile analysis |
| 19 | 5-year historical data | yfinance `ticker.history(period="5y")` | defeatbeta `price()` | PE percentile, long-term analysis |
| 20 | 10-year Treasury yield (^TNX) | yfinance `Ticker('^TNX').info` | Hardcoded 4.5% default | Risk-free rate |
| 21 | Index prices (^GSPC, ^IXIC, etc.) | yfinance `Ticker(index).info` | None | Market benchmark |
| 22 | Currency (for portfolio) | ExchangeRate-API | Hardcoded rates | Portfolio P/L |
| 23 | A-share lockup data | AkShare | None | A-share analysis |

### Options Analysis Data Needs

| # | Data Need | Primary API | Fallback API | Used By |
|---|-----------|-------------|--------------|---------|
| 24 | Option expiration dates | Tiger API `get_option_expirations()` | yfinance `ticker.options` | Options chain display |
| 25 | Option chain (calls/puts) | Tiger API `get_option_chain()` | yfinance `ticker.option_chain()` | Options scoring |
| 26 | Option Greeks (delta, gamma, theta, vega) | Tiger API (with `return_greek_value=True`) | yfinance (partial) / Mock | Options scoring |
| 27 | Implied volatility | Tiger API `implied_vol` | yfinance `impliedVolatility` | IV analysis |
| 28 | Open interest | Tiger API `open_interest` | yfinance `openInterest` | Liquidity scoring |
| 29 | Bid/ask spread | Tiger API `bid_price/ask_price` | yfinance `bid/ask` | Liquidity scoring |
| 30 | Real-time stock quote | Tiger API `get_stock_briefs()` | yfinance `ticker.info` | Options pricing |
| 31 | Margin rate | Tiger API `get_stock_briefs()['margin_rate']` | None | Cost analysis |
| 32 | Stock history (60-day for options) | Tiger API `get_bars()` | yfinance `ticker.history()` | Trend/volatility |
| 33 | 3-month OHLCV (for technical indicators) | yfinance `ticker.history(period="3mo")` | None | RSI, MACD, Bollinger |
| 34 | Screenshot OCR (option params) | Google Gemini Vision | None | Reverse scoring |

### Market Alerts & Macro Indicator Data Needs (市场预警)

| # | Data Need | Primary API | Fallback | Used By |
|---|-----------|-------------|----------|---------|
| 35 | VIX (恐慌指数) | yfinance `Ticker('^VIX').history()` | None | Market warnings, geopolitical risk, sentiment scoring |
| 36 | 10-Year Treasury Yield (美债收益率) | yfinance `Ticker('^TNX').history()` | Hardcoded 4.5% | Market warnings, PEG threshold, sentiment scoring |
| 37 | Gold Price (黄金价格) | yfinance `Ticker('GC=F').history()` | None | Market warnings, geopolitical risk proxy |
| 38 | Crude Oil Price (原油价格) | yfinance `Ticker('CL=F').history()` | None | Market warnings, geopolitical risk proxy |
| 39 | US Dollar Index (美元指数) | yfinance `Ticker('DX-Y.NYB').history()` | yfinance `Ticker('^DXY')` | Geopolitical risk proxy, sentiment scoring |
| 40 | Put/Call Ratio | yfinance `ticker.option_chain()` → compute | None | Market warnings, sentiment scoring |
| 41 | Fed Meeting Dates (美联储会议) | **Hardcoded calendar** | None | Market warnings (经济事件提醒) |
| 42 | US CPI Release Dates | **Computed** (~12th of month) | None | Market warnings (经济事件提醒) |
| 43 | China PBOC Meetings (央行会议) | **Hardcoded** (Jan/Apr/Jul/Oct 20th) | None | Market warnings (中国经济事件) |
| 44 | China CPI/PPI Release | **Computed** (~10th of month) | None | Market warnings (中国经济事件) |
| 45 | China GDP Release | **Hardcoded** (Apr/Jul/Oct/Jan 18th) | None | Market warnings (中国经济事件) |
| 46 | China PMI Release | **Computed** (1st of month) | None | Market warnings (中国经济事件) |
| 47 | Options Expiration Dates (期权到期日) | **Computed** (3rd Friday of month) | None | Market warnings |
| 48 | Earnings Date (财报日期) | yfinance `ticker.calendar['Earnings Date']` | yfinance `ticker.info['earningsTimestamp']` | Market warnings, options risk |
| 49 | Geopolitical Risk Index (地缘政治风险) | **Computed** from Gold/VIX/DXY/Oil | None | Market warnings, sentiment scoring |
| 50 | Polymarket Predictions (预测市场) | Polymarket API `clob.polymarket.com` | None | Market warnings, sentiment scoring |

---

## 3. API Source: yfinance

| | |
|---|---|
| **Library** | `yfinance==0.2.63` |
| **Data Source** | Yahoo Finance (unofficial API wrapper) |
| **Rate Limits** | Aggressive; ~2000 requests/hour, can be throttled at ~100/min |
| **Cost** | Free |
| **Reliability** | Medium - frequent rate limiting, occasional data gaps |

### Methods Used

| Method | Return Type | Data Fields | Files Using It |
|--------|------------|-------------|----------------|
| `yf.Ticker(symbol)` | `Ticker` object | N/A (constructor) | All data fetchers |
| `ticker.info` | `dict` | `regularMarketPrice`, `previousClose`, `open`, `dayHigh`, `dayLow`, `volume`, `marketCap`, `currency`, `currentPrice`, `trailingPE`, `forwardPE`, `trailingEps`, `forwardEps`, `beta`, `profitMargins`, `returnOnEquity`, `returnOnAssets`, `revenueGrowth`, `earningsGrowth`, `sector`, `industry`, `dividendYield`, `bookValue`, `priceToBook`, `priceToSalesTrailing12Months` | `stock/data_fetcher.py:109`, `options/data_fetcher.py:145`, `options_service.py:465`, `recommendation_service.py:294`, `scheduler.py:67`, `analysis_engine.py:29` |
| `ticker.history(period=)` | `DataFrame` | `Open`, `High`, `Low`, `Close`, `Volume` | `options/data_fetcher.py:148`, `options_service.py:500`, `recommendation_service.py:116` |
| `ticker.history(start=, end=)` | `DataFrame` | `Open`, `High`, `Low`, `Close`, `Volume` | `stock/data_fetcher.py:209`, `options_service.py:311` |
| `ticker.options` | `tuple[str]` | List of expiry date strings (e.g. `('2025-01-31', '2025-02-07', ...)`) | `options/data_fetcher.py:151,260`, `recommendation_service.py:306` |
| `ticker.option_chain(expiry)` | `OptionChain` | `.calls` / `.puts` DataFrames: `strike`, `bid`, `ask`, `lastPrice`, `volume`, `openInterest`, `impliedVolatility`, `delta`, `gamma`, `theta`, `vega`, `inTheMoney` | `options/data_fetcher.py:274`, `recommendation_service.py:331` |
| `ticker.quarterly_earnings` | `DataFrame` | `Earnings` (EPS), earnings dates | `analysis_engine.py:176` |
| `ticker.calendar` | `dict` | `Earnings Date` (list of datetime) | `analysis_engine.py:946-953` |

### Macro/Index Tickers Fetched via yfinance

These are special yfinance tickers used for macro indicators, not individual stocks.

| Ticker Symbol | Data | Method | Code Location |
|---------------|------|--------|---------------|
| `^VIX` | CBOE Volatility Index (恐慌指数) | `history(period='5d')` → `Close` | `analysis_engine.py:2290-2297` |
| `^TNX` | 10-Year Treasury Yield (美债收益率) | `history(period='5d')` → `Close` | `analysis_engine.py:1929-1936` |
| `GC=F` | Gold Futures (黄金价格) | `history(period='5d')` → `Close` | `analysis_engine.py:1960-1967` |
| `CL=F` | Crude Oil Futures (原油价格) | `history(period='5d')` → `Close` | `analysis_engine.py:1973-1980` |
| `DX-Y.NYB` | US Dollar Index (美元指数) | `history(period='5d')` → `Close` | `analysis_engine.py:1942-1954` |
| `^DXY` | US Dollar Index (backup ticker) | `history(period='5d')` → `Close` | `analysis_engine.py:1946` |
| `^GSPC` | S&P 500 Index | `info['regularMarketPrice']` | `stock/data_fetcher.py:308` |
| `^IXIC` | NASDAQ Composite | `info['regularMarketPrice']` | `stock/data_fetcher.py:308` |
| `^DJI` | Dow Jones Industrial | `info['regularMarketPrice']` | `stock/data_fetcher.py:308` |

### Error Handling

- **Rate limit detection**: Catches `YFRateLimitError`, HTTP 429, "Too Many Requests", "Rate limited"
- **Retry strategy**: 3 attempts with 2-second exponential backoff
- **Fallback**: Routes to `DataProvider` (defeatbeta-api) on rate limit

---

## 4. API Source: Tiger API (tigeropen)

| | |
|---|---|
| **Library** | `tigeropen==3.4.3` |
| **Data Source** | Tiger Brokers (official SDK) |
| **Rate Limits** | Generous for licensed users |
| **Cost** | Requires Tiger Brokers account |
| **Reliability** | High - direct broker feed, but requires API key config |

### Configuration

- Config file: `tiger_openapi_config.properties`
- Language: `zh_CN`
- Markets supported: `Market.US`, `Market.HK`

### Methods Used

| Method | Return Type | Data Fields | Files Using It |
|--------|------------|-------------|----------------|
| `QuoteClient(config)` | `QuoteClient` | N/A (constructor) | `tiger_client.py:53` |
| `quote_client.get_option_expirations(symbols, market)` | `DataFrame` | `date`, `timestamp`, `period_tag` | `tiger_client.py:65`, `options_service.py:183` |
| `quote_client.get_option_chain(symbol, expiry, market, return_greek_value=True)` | `DataFrame` | `identifier`, `symbol`, `strike`, `put_call`, `bid_price`, `ask_price`, `latest_price`, `volume`, `open_interest`, `implied_vol`, `delta`, `gamma`, `theta`, `vega` | `tiger_client.py:71`, `options_service.py:219` |
| `quote_client.get_stock_briefs(symbols)` | `DataFrame` | `latest_price`, `change`, `change_percent`, `volume`, `margin_rate` | `tiger_client.py:81`, `options_service.py:238,286,353` |
| `quote_client.get_bars(symbols, period, end_time, limit, market)` | `DataFrame` | `time`, `open`, `high`, `low`, `close`, `volume` | `tiger_client.py:116`, `options_service.py:390` |

### Error Handling

- Returns `None` if client not initialized
- Catches generic exceptions; logs warning and returns None/empty
- Options analysis falls back to yfinance then mock data if Tiger fails

---

## 5. API Source: defeatbeta-api

| | |
|---|---|
| **Library** | `defeatbeta-api==0.0.33` |
| **Data Source** | HuggingFace dataset (`bwzheng2010/yahoo-finance-data`) via DuckDB |
| **Rate Limits** | None (local DuckDB queries against cached Parquet files) |
| **Cost** | Free / open-source |
| **Reliability** | High for fundamentals, but data may lag real-time by days |

### Integration Point

Used via `DataProvider` class (`backend/app/services/data_provider.py`) as a **fallback** when yfinance is rate-limited.

### Methods Currently Used

| Method | Return Type | Data Fields | Mapped To (yfinance equivalent) |
|--------|------------|-------------|--------------------------------|
| `Ticker(symbol)` | `Ticker` object | N/A | `yf.Ticker()` |
| `ticker.price()` | `DataFrame` | `report_date`, `open`, `high`, `low`, `close`, `volume` | `ticker.history()` → OHLCV |
| `ticker.summary()` | `DataFrame` | `market_cap`, `enterprise_value`, `shares_outstanding`, `beta`, `trailing_pe`, `forward_pe`, `trailing_eps`, `forward_eps`, `enterprise_to_ebitda`, `enterprise_to_revenue`, `peg_ratio`, `currency` | `ticker.info` (valuation fields) |
| `ticker.info()` | `DataFrame` | `sector`, `industry`, `symbol`, `country` | `ticker.info` (profile fields) |
| `ticker.quarterly_net_margin()` | `DataFrame` | Net margin % by quarter | `ticker.info['profitMargins']` |
| `ticker.quarterly_operating_margin()` | `DataFrame` | Operating margin % by quarter | `ticker.info['operatingMargins']` |
| `ticker.roe()` | `DataFrame` | Return on equity by quarter | `ticker.info['returnOnEquity']` |
| `ticker.roa()` | `DataFrame` | Return on assets by quarter | `ticker.info['returnOnAssets']` |
| `ticker.quarterly_revenue_yoy_growth()` | `DataFrame` | Revenue YoY growth % | `ticker.info['revenueGrowth']` |
| `ticker.quarterly_net_income_yoy_growth()` | `DataFrame` | Net income YoY growth % | `ticker.info['earningsGrowth']` |
| `ticker.ttm_revenue()` | `DataFrame` | Trailing 12-month revenue | `ticker.info['totalRevenue']` |
| `ticker.pb_ratio()` | `DataFrame` | Price-to-Book ratio | `ticker.info['priceToBook']` |
| `ticker.ps_ratio()` | `DataFrame` | Price-to-Sales ratio | `ticker.info['priceToSalesTrailing12Months']` |
| `ticker.dividends()` | `DataFrame` | Dividend payment history | `ticker.dividends` |
| `ticker.earnings()` | `DataFrame` | Historical EPS data | `ticker.quarterly_earnings` |

### Data Mapping Logic

`DataProvider` converts defeatbeta responses into yfinance-compatible dict format:

```python
# Example from data_provider.py
info['regularMarketPrice'] = float(latest_price['close'])
info['marketCap'] = float(summary['market_cap'])
info['trailingPE'] = float(summary['trailing_pe'])
# ... etc
```

---

## 6. API Source: AkShare

| | |
|---|---|
| **Library** | `akshare==1.17.26` |
| **Data Source** | China A-share market data (EastMoney, etc.) |
| **Rate Limits** | Moderate |
| **Cost** | Free / open-source |
| **Reliability** | Medium |

### Methods Used

| Method | Data Fields | Files Using It |
|--------|-------------|----------------|
| `ak.stock_restricted_shares_summary_em(symbol=cn_code)` | Lockup expiry date, lockup shares, lockup ratio, lockup type | `analysis_engine.py:395-450` |

### Notes

- Only used for A-share (Chinese stock) analysis
- Optional import with `ImportError` fallback
- Symbol format conversion: `AAPL` -> `600519` (Chinese stock code)

---

## 7. API Source: Google Gemini

| | |
|---|---|
| **Library** | `google-generativeai==0.8.5` + direct HTTP |
| **Endpoint** | `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent` |
| **Auth** | API Key (`GOOGLE_API_KEY` env var) |
| **Cost** | Free tier available; pay-per-use beyond |
| **Reliability** | High |

### Methods Used

| Method | Input | Output | Files Using It |
|--------|-------|--------|----------------|
| `POST /generateContent` | Base64 image + OCR prompt | JSON: `symbol`, `option_type`, `strike`, `expiry_date`, `option_price`, `implied_volatility`, `confidence` | `image_recognition_service.py:98` |

### Configuration

```python
payload = {
    "generationConfig": {
        "temperature": 0.1,
        "topK": 1,
        "topP": 1,
        "maxOutputTokens": 1024
    }
}
```

### Error Handling

- HTTP 429/5xx: Returns error message
- JSON parse failure: Returns format error
- Timeout: 30 seconds
- Missing fields: Reports which fields could not be recognized

---

## 8. API Source: ExchangeRate-API

| | |
|---|---|
| **Endpoint** | `https://api.exchangerate-api.com/v4/latest/USD` |
| **Auth** | None (free tier) |
| **Cost** | Free |
| **Reliability** | High |

### Methods Used

| Method | Data Fields | Files Using It |
|--------|-------------|----------------|
| `GET /v4/latest/USD` | `rates.HKD`, `rates.CNY` | `scheduler.py:38` |

### Caching & Fallback

- **Cache duration**: 1 hour
- **Fallback rates**: USD→HKD: 7.8, USD→CNY: 7.2

---

## 9. API Source: Alpha Vantage (Unused)

| | |
|---|---|
| **Library** | `alpha_vantage==3.0.0` (in requirements.txt) |
| **Status** | **INSTALLED BUT NOT ACTIVE** |

Listed in dependencies and referenced in `analysis_engine.py` with `ImportError` handling, but no active code paths use it. Available for future integration as an additional fallback.

---

## 10. Market Alerts & Macro Data Sources (市场预警)

All code in this section is located in `backend/app/services/analysis_engine.py`.

### 10.1 Data Flow

```
analyze_stock()                              (line ~2518)
  │
  ├─→ get_macro_market_data()                (line 1902)
  │     ├─→ yfinance ^TNX    → treasury_10y        (line 1929)
  │     ├─→ yfinance DX-Y.NYB → dxy                (line 1942)
  │     ├─→ yfinance GC=F    → gold                (line 1960)
  │     ├─→ yfinance CL=F    → oil                 (line 1973)
  │     ├─→ get_fed_meeting_dates()                 (line 1986) ← HARDCODED
  │     ├─→ get_cpi_release_dates()                 (line 1992) ← COMPUTED
  │     ├─→ get_options_expiration_dates()           (line 1998) ← COMPUTED
  │     └─→ get_china_economic_events()              (line 2004) ← HARDCODED + COMPUTED
  │
  ├─→ get_options_market_data(ticker)        (line 2273)
  │     ├─→ yfinance ^VIX    → vix                  (line 2290)
  │     └─→ yfinance option_chain → put_call_ratio   (line 2315)
  │
  ├─→ get_polymarket_data()                  (line 2569)
  │     └─→ Polymarket API   → predictions           (line 2033)
  │
  ├─→ calculate_geopolitical_risk()          (line 2574)
  │     └─→ Composite of gold/VIX/DXY/oil (NO external API)
  │
  └─→ get_market_warnings()                  (line 2577)
        └─→ Generates alerts from ALL above data
```

### 10.2 重要经济事件提醒 (Economic Event Reminders)

These are the calendar-based event sources. Most use **NO external API**.

#### Fed Meeting Dates (美联储会议) — `get_fed_meeting_dates()` (line 1216)

| | |
|---|---|
| **Data Source** | **HARDCODED** — manually coded dates per year |
| **Fallback** | None |
| **Maintenance** | Must be manually updated each year |

```
Current hardcoded dates:
  2025: Jan 28, Mar 18*, May 6, Jun 17*, Jul 29, Sep 16*, Oct 28, Dec 9*
  2026: Jan 28, Mar 18*
  (* = includes dot plot / 含点阵图)
```

Returns the next 3 meetings within 90 days. Used in `get_market_warnings()` (line 1554) to generate alerts:
- 0-3 days before: **HIGH** alert
- 4-7 days before: **MEDIUM** alert
- 8-14 days before: **LOW** alert

#### US CPI Release Dates (美国CPI发布) — `get_cpi_release_dates()` (line 1257)

| | |
|---|---|
| **Data Source** | **COMPUTED** — rule: ~12th of each month, adjusted for weekends |
| **Fallback** | None |
| **Maintenance** | Self-maintaining (approximate; actual dates may vary by 1-2 days) |

Returns the next 3 CPI release dates. Used in `get_market_warnings()` (line 1583).

#### China Economic Events (中国经济事件) — `get_china_economic_events()` (line 1288)

| Event | Source Type | Schedule Rule |
|-------|-----------|---------------|
| 央行货币政策会议 (PBOC) | **Hardcoded** | Jan 20, Apr 20, Jul 20, Oct 20 |
| CPI/PPI发布 | **Computed** | ~10th of each month (weekend adjusted) |
| GDP发布 | **Hardcoded** | Apr 18, Jul 18, Oct 18, Jan 18 |
| PMI发布 | **Computed** | 1st of each month (weekend adjusted) |

Returns top 10 events within 90 days. Used in `get_market_warnings()` (line 1607).

#### Options Expiration Dates (期权到期日) — `get_options_expiration_dates()` (line 1378)

| | |
|---|---|
| **Data Source** | **COMPUTED** — 3rd Friday of each month |
| **Fallback** | None |
| **Maintenance** | Self-maintaining |

Also identifies Quadruple Witching dates (3月/6月/9月/12月). Returns next 3 expiration dates. Used in `get_market_warnings()` (line 1648).

### 10.3 财报日期提醒 (Earnings Date Reminders) — line 946

| | |
|---|---|
| **Data Source** | **EXTERNAL API** — yfinance |
| **Primary** | `yfinance ticker.calendar['Earnings Date']` (line 953) |
| **Fallback** | `yfinance ticker.info['earningsTimestamp']` (line 960) |
| **Limitation** | defeatbeta-api does NOT provide earnings dates |

Stores the 2 most recent earnings dates in `data['earnings_dates']` (line 1107).

**Where earnings dates are consumed:**

| Location | Line | Usage |
|----------|------|-------|
| `get_market_warnings()` | 1689-1711 | Generates HIGH (0-3 days) / MEDIUM (4-7 days) alerts |
| Options risk analysis | 3483-3496 | Flags earnings volatility risk for options strategies |
| AI service prompt | 359-390 | Included in AI analysis context |

### 10.4 地缘政治风险指数 (Geopolitical Risk Index) — `calculate_geopolitical_risk()` (line 1819)

| | |
|---|---|
| **Data Source** | **NO direct geopolitical API** — computed from market proxies |
| **Fallback** | None |

This is an **inferred score** (0-10), not real geopolitical data. It uses observable market behavior as proxies:

| Indicator | Weight | Source Ticker | High Risk Signal | Score |
|-----------|--------|---------------|------------------|-------|
| Gold price change (黄金) | 40% | `GC=F` (line 1829) | > 3% daily change | 8.0 |
| VIX level (恐慌指数) | 30% | `^VIX` (line 1845) | > 30 | 8.5 |
| US Dollar Index (美元) | 20% | `DX-Y.NYB` (line 1865) | > 105 + rising | 7.5 |
| Oil price volatility (原油) | 10% | `CL=F` (line 1884) | |change| > 5% | 7.0 |

The final score feeds into `get_market_warnings()` (line 1734) and sentiment scoring (line 2574).

### 10.5 Polymarket Predictions (预测市场) — `get_polymarket_data()` (line 2014)

| | |
|---|---|
| **Data Source** | **EXTERNAL API** — Polymarket public API |
| **Endpoint** | `https://clob.polymarket.com/graphql` (line 2057) |
| **Fallback endpoint** | `https://clob.polymarket.com/markets` REST (line 2136) |
| **Auth** | None (public API) |
| **Timeout** | 10 seconds |

**Data retrieved:** Top 20 active prediction markets by volume, categorized by keyword matching:

| Category | Keywords Matched |
|----------|-----------------|
| `election_predictions` | election, president, senate, house, vote |
| `economic_predictions` | gdp, inflation, cpi, unemployment, recession |
| `fed_policy_predictions` | fed, federal reserve, interest rate, fomc, rate cut/hike |
| `geopolitical_predictions` | war, conflict, sanction, trade, russia, china, iran |
| `market_event_predictions` | market, crash, rally, sp500, dow, nasdaq |

**Where Polymarket data is consumed:**

| Location | Line | Usage |
|----------|------|-------|
| `get_market_warnings()` | 1752-1802 | Generates alerts for key events, economic, and Fed predictions |
| Sentiment scoring | 2791-2799 | Adds 3% weight to overall sentiment score |

### 10.6 Complete Market Warnings Alert Table

Summary of all alert types generated by `get_market_warnings()` (line 1448):

| Alert Type | Trigger Condition | Severity | Data Source | Line |
|------------|-------------------|----------|-------------|------|
| VIX恐慌 | VIX >= 30 | HIGH | yfinance `^VIX` | 1462 |
| VIX接近危险 | VIX >= 25 | MEDIUM | yfinance `^VIX` | 1469 |
| VIX快速上升 | VIX change > 10% | MEDIUM | yfinance `^VIX` | 1476 |
| VIX中等偏高 | VIX >= 20 | LOW | yfinance `^VIX` | 1483 |
| 美债收益率飙升 | 10Y >= 5.0% | HIGH | yfinance `^TNX` | 1509 |
| 美债收益率上升 | 10Y >= 4.5% | MEDIUM | yfinance `^TNX` | 1516 |
| 黄金暴涨 | Gold change > 3% | HIGH | yfinance `GC=F` | 1536 |
| 黄金显著上涨 | Gold change > 1.5% | MEDIUM | yfinance `GC=F` | 1543 |
| 美联储会议 (0-3天) | Meeting in 0-3 days | HIGH | Hardcoded calendar | 1557 |
| 美联储会议 (4-7天) | Meeting in 4-7 days | MEDIUM | Hardcoded calendar | 1565 |
| 美联储会议 (8-14天) | Meeting in 8-14 days | LOW | Hardcoded calendar | 1573 |
| CPI发布 (0-3天) | CPI in 0-3 days | MEDIUM | Computed dates | 1586 |
| CPI发布 (4-7天) | CPI in 4-7 days | LOW | Computed dates | 1594 |
| 中国经济事件 | Event in 0-7 days | LOW-MEDIUM | Hardcoded + computed | 1608 |
| 期权到期 (0-3天) | Expiry in 0-3 days | HIGH | Computed (3rd Friday) | 1651 |
| 期权到期 (4-7天) | Expiry in 4-7 days | MEDIUM | Computed (3rd Friday) | 1659 |
| 期权到期 (8-14天) | Expiry in 8-14 days | LOW | Computed (3rd Friday) | 1667 |
| 财报发布 (0-3天) | Earnings in 0-3 days | HIGH | yfinance calendar | 1697 |
| 财报发布 (4-7天) | Earnings in 4-7 days | MEDIUM | yfinance calendar | 1705 |
| 地缘政治风险 | Risk score >= 7 | HIGH | Computed proxy | 1737 |
| 地缘政治风险 | Risk score >= 6 | MEDIUM | Computed proxy | 1742 |
| Polymarket关键事件 | Key events exist | MEDIUM | Polymarket API | 1756 |
| Polymarket经济预测 | Economic predictions | LOW | Polymarket API | 1783 |
| Polymarket美联储预测 | Fed predictions | LOW | Polymarket API | 1796 |

---

## 11. Fallback Chain per Data Type

This shows the complete resilience path for each data type when the primary source fails.

### Stock Price Data

```
yfinance ticker.info['regularMarketPrice']
    │ (rate limited?)
    ▼
defeatbeta ticker.price() → latest row['close']
    │ (failed?)
    ▼
ERROR: No price available
```

### Historical OHLCV

```
yfinance ticker.history(start, end)
    │ (rate limited?)
    ▼
defeatbeta ticker.price() → filter by date range
    │ (failed?)
    ▼
ERROR: No historical data
```

### Fundamental Data (PE, margins, growth, etc.)

```
yfinance ticker.info (all-in-one dict)
    │ (rate limited?)
    ▼
defeatbeta individual methods:
  - summary()       → PE, EPS, beta, market cap
  - info()          → sector, industry
  - roe(), roa()    → profitability
  - quarterly_*()   → margins, growth rates
  - pb_ratio(), ps_ratio() → valuation
    │ (failed?)
    ▼
ERROR: No fundamental data
```

### Options Chain

```
Tiger API get_option_chain() [with Greeks]
    │ (client not available?)
    ▼
yfinance ticker.option_chain(expiry) [Greeks partial/missing]
    │ (failed?)
    ▼
Mock data generator (estimated Greeks via Black-Scholes)
```

### Options Expiration Dates

```
Tiger API get_option_expirations()
    │ (client not available?)
    ▼
yfinance ticker.options
    │ (failed?)
    ▼
ERROR: No options data
```

### Currency Conversion

```
ExchangeRate-API GET /v4/latest/USD
    │ (failed / timeout?)
    ▼
Hardcoded defaults: USD/HKD=7.8, USD/CNY=7.2
```

### A-Share Lockup Data

```
AkShare stock_restricted_shares_summary_em()
    │ (not installed / failed?)
    ▼
Empty lockup data (skip analysis)
```

### Image Recognition

```
Google Gemini Vision API
    │ (failed?)
    ▼
ERROR: No fallback (feature unavailable)
```

### Macro Indicators (VIX, Treasury, Gold, Oil, DXY)

```
yfinance Ticker('^VIX' / '^TNX' / 'GC=F' / 'CL=F' / 'DX-Y.NYB').history()
    │ (failed?)
    ▼
None (field stays null, alert skipped)
```

### Economic Event Calendars

```
Hardcoded/Computed dates (no API)
    │ (never fails — always returns data)
    ▼
N/A
```

### Earnings Dates

```
yfinance ticker.calendar['Earnings Date']
    │ (missing?)
    ▼
yfinance ticker.info['earningsTimestamp']
    │ (missing?)
    ▼
Empty list (no earnings alert generated)
```

### Polymarket Predictions

```
Polymarket GraphQL API (clob.polymarket.com/graphql)
    │ (failed?)
    ▼
Polymarket REST API (clob.polymarket.com/markets)
    │ (failed?)
    ▼
Empty predictions (feature silently unavailable)
```

---

## 12. defeatbeta-api: Unused Methods Available

These methods exist in the defeatbeta-api library but are **NOT currently used** in our codebase. They represent opportunities for richer analysis or additional fallback coverage.

### Financial Statements (full breakdown)

| Method | Description | Potential Use |
|--------|-------------|---------------|
| `quarterly_income_statement()` | Full income statement | Detailed financial analysis |
| `annual_income_statement()` | Annual income statement | Year-over-year comparison |
| `quarterly_balance_sheet()` | Full balance sheet | Debt analysis, book value |
| `annual_balance_sheet()` | Annual balance sheet | Long-term health |
| `quarterly_cash_flow()` | Cash flow statement | FCF analysis |
| `annual_cash_flow()` | Annual cash flow | Capital allocation |

### Additional Metrics

| Method | Description | Potential Use |
|--------|-------------|---------------|
| `roic()` | Return on invested capital | Quality scoring |
| `wacc()` | Weighted avg cost of capital | DCF valuation |
| `peg_ratio()` | PE / growth rate | Growth-adjusted valuation |
| `equity_multiplier()` | ROE / ROA | Leverage analysis |
| `asset_turnover()` | ROA / net margin | Efficiency analysis |
| `ttm_pe()` | TTM P/E time series | Historical PE chart |
| `ttm_eps()` | TTM EPS time series | Earnings trend |
| `market_capitalization()` | Market cap time series | Historical size tracking |

### Margin Variants (quarterly + annual)

| Method | Description |
|--------|-------------|
| `quarterly_gross_margin()` / `annual_gross_margin()` | Gross profitability |
| `quarterly_ebitda_margin()` / `annual_ebitda_margin()` | EBITDA profitability |
| `quarterly_fcf_margin()` / `annual_fcf_margin()` | Free cash flow margin |

### Growth Variants

| Method | Description |
|--------|-------------|
| `quarterly_operating_income_yoy_growth()` | Operating income growth |
| `quarterly_ebitda_yoy_growth()` | EBITDA growth |
| `quarterly_fcf_yoy_growth()` | Free cash flow growth |
| `quarterly_eps_yoy_growth()` | EPS growth |
| All above have `annual_*` variants too | |

### Revenue Breakdown

| Method | Description |
|--------|-------------|
| `revenue_by_segment()` | Revenue by business segment |
| `revenue_by_geography()` | Revenue by region |
| `revenue_by_product()` | Revenue by product line |

### Industry Comparisons

| Method | Description |
|--------|-------------|
| `industry_ttm_pe()` | Industry-wide P/E |
| `industry_ps_ratio()` | Industry-wide P/S |
| `industry_pb_ratio()` | Industry-wide P/B |
| `industry_roe()` | Industry-wide ROE |
| `industry_roa()` | Industry-wide ROA |
| `industry_quarterly_gross_margin()` | Industry-wide gross margin |
| `industry_quarterly_net_margin()` | Industry-wide net margin |

### Other Data

| Method | Description |
|--------|-------------|
| `news()` | Financial news articles |
| `earning_call_transcripts()` | Earnings call transcripts (with AI analysis) |
| `sec_filing()` | SEC filing documents |
| `officers()` | Company executives |
| `calendar()` | Earnings calendar dates |
| `shares()` | Shares outstanding history |
| `splits()` | Stock split history |
| `currency(symbol)` | Exchange rate data |
| `earnings_forecast()` | Analyst EPS estimates |
| `revenue_forecast()` | Analyst revenue estimates |

---

## 13. Stability Improvement Opportunities

### Current Single Points of Failure

| Data Type | Risk | Suggestion |
|-----------|------|------------|
| Options Greeks | Tiger-only accurate source; yfinance Greeks often missing | Add Tradier or Polygon as secondary |
| Real-time stock quote | yfinance rate limits; Tiger requires account | Add Finnhub or Twelve Data free tier |
| Index/benchmark prices | yfinance only | Add defeatbeta or FRED |
| Image recognition | Google Gemini only | Add OpenAI Vision as fallback |
| Currency rates | Single free API | Add Fixer.io or Open Exchange Rates |
| A-share data | AkShare only | Add Tushare as fallback |
| Macro indicators (VIX, Gold, Oil, DXY, TNX) | yfinance only; no fallback if rate limited | Add FRED, Finnhub, or Twelve Data |
| Fed meeting dates | Hardcoded; must update manually each year | Use FRED API or economic calendar API |
| CPI/economic event dates | Approximate computation; can be off by 1-2 days | Use BLS API or economic calendar API |
| Earnings dates | yfinance only; defeatbeta has `calendar()` but not wired up | Wire up defeatbeta `calendar()` as fallback |
| Polymarket predictions | Single API; GraphQL endpoint may change | Monitor API stability; add fallback prediction source |

### Priority Actions

1. **High**: Add a second real-time options data source (reduce Tiger dependency)
2. **High**: Wire up defeatbeta `earnings()` and `calendar()` as fallback for earnings dates
3. **High**: Add fallback for macro indicators (VIX/Gold/Oil/TNX) — currently no fallback when yfinance is rate-limited
4. **Medium**: Replace hardcoded Fed meeting dates with an API (e.g., FRED, Finnhub economic calendar)
5. **Medium**: Use defeatbeta `industry_*` methods for sector comparison scoring
6. **Medium**: Add a second real-time quote provider for stock prices
7. **Low**: Integrate `news()` and `earning_call_transcripts()` for sentiment analysis
8. **Low**: Use `wacc()` and `roic()` for more advanced valuation scoring

---

*Last updated: 2026-01-28*

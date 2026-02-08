# 数据源与 API 参考

> 迁移自 `docs/DATA_SOURCE_API.md` | 原始日期: 2026-01-28 | 迁移日期: 2026-02-08

本文档编录 AlphaGBM 系统中使用的所有外部数据源和 API，包括数据需求、提供方、以及 Fallback 策略。

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
| 35 | VIX (恐慌指数) | yfinance `Ticker('^VIX').history()` | None | Market warnings, sentiment scoring |
| 36 | 10-Year Treasury Yield (美债收益率) | yfinance `Ticker('^TNX').history()` | Hardcoded 4.5% | Market warnings, sentiment scoring |
| 37 | Gold Price (黄金价格) | yfinance `Ticker('GC=F').history()` | None | Market warnings, geopolitical risk proxy |
| 38 | Crude Oil Price (原油价格) | yfinance `Ticker('CL=F').history()` | None | Market warnings, geopolitical risk proxy |
| 39 | US Dollar Index (美元指数) | yfinance `Ticker('DX-Y.NYB').history()` | yfinance `Ticker('^DXY')` | Geopolitical risk proxy |
| 40 | Put/Call Ratio | yfinance `ticker.option_chain()` compute | None | Market warnings, sentiment scoring |
| 41 | Fed Meeting Dates (美联储会议) | **Hardcoded calendar** | None | Market warnings |
| 42 | US CPI Release Dates | **Computed** (~12th of month) | None | Market warnings |
| 43-46 | China Economic Events | **Hardcoded + Computed** | None | Market warnings |
| 47 | Options Expiration Dates | **Computed** (3rd Friday) | None | Market warnings |
| 48 | Earnings Date (财报日期) | yfinance `ticker.calendar` | yfinance `ticker.info['earningsTimestamp']` | Market warnings, options risk |
| 49 | Geopolitical Risk Index | **Computed** from Gold/VIX/DXY/Oil | None | Sentiment scoring |
| 50 | Polymarket Predictions | Polymarket API | None | Market warnings, sentiment |

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
| `ticker.info` | `dict` | `regularMarketPrice`, `previousClose`, `marketCap`, `trailingPE`, `forwardPE`, `beta`, `sector`, `industry`, etc. | `stock/data_fetcher.py`, `options/data_fetcher.py`, `recommendation_service.py` |
| `ticker.history(period=)` | `DataFrame` | `Open`, `High`, `Low`, `Close`, `Volume` | `options/data_fetcher.py`, `options_service.py` |
| `ticker.options` | `tuple[str]` | List of expiry date strings | `options/data_fetcher.py`, `recommendation_service.py` |
| `ticker.option_chain(expiry)` | `OptionChain` | `.calls` / `.puts` DataFrames | `options/data_fetcher.py`, `recommendation_service.py` |
| `ticker.quarterly_earnings` | `DataFrame` | `Earnings` (EPS) | `analysis_engine.py` |
| `ticker.calendar` | `dict` | `Earnings Date` | `analysis_engine.py` |

### Macro/Index Tickers

| Ticker Symbol | Data | Usage |
|---------------|------|-------|
| `^VIX` | CBOE Volatility Index | Market warnings, geopolitical risk |
| `^TNX` | 10-Year Treasury Yield | Market warnings, PEG threshold |
| `GC=F` | Gold Futures | Market warnings, geopolitical risk proxy |
| `CL=F` | Crude Oil Futures | Market warnings, geopolitical risk proxy |
| `DX-Y.NYB` | US Dollar Index | Geopolitical risk proxy |
| `^GSPC`, `^IXIC`, `^DJI` | Market Indices | Benchmark comparison |

### Error Handling

- **Rate limit detection**: Catches `YFRateLimitError`, HTTP 429
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
| **Reliability** | High |

### Methods Used

| Method | Data Fields |
|--------|-------------|
| `get_option_expirations(symbols, market)` | `date`, `timestamp`, `period_tag` |
| `get_option_chain(symbol, expiry, market, return_greek_value=True)` | `strike`, `put_call`, `bid_price`, `ask_price`, `implied_vol`, `delta`, `gamma`, `theta`, `vega` |
| `get_stock_briefs(symbols)` | `latest_price`, `change`, `volume`, `margin_rate` |
| `get_bars(symbols, period, end_time, limit, market)` | `time`, `open`, `high`, `low`, `close`, `volume` |

---

## 5. API Source: defeatbeta-api

| | |
|---|---|
| **Library** | `defeatbeta-api==0.0.33` |
| **Data Source** | HuggingFace dataset via DuckDB |
| **Rate Limits** | None (local queries) |
| **Cost** | Free / open-source |
| **Reliability** | High for fundamentals, data may lag by days |

Used via `DataProvider` class as a **fallback** when yfinance is rate-limited. Converts defeatbeta responses into yfinance-compatible dict format.

### Methods Used

| Method | Mapped To (yfinance equivalent) |
|--------|--------------------------------|
| `ticker.price()` | `ticker.history()` |
| `ticker.summary()` | `ticker.info` (valuation) |
| `ticker.info()` | `ticker.info` (profile) |
| `ticker.quarterly_net_margin()` | `ticker.info['profitMargins']` |
| `ticker.quarterly_operating_margin()` | `ticker.info['operatingMargins']` |
| `ticker.roe()` / `ticker.roa()` | `ticker.info['returnOnEquity/Assets']` |
| `ticker.quarterly_revenue_yoy_growth()` | `ticker.info['revenueGrowth']` |
| `ticker.pb_ratio()` / `ticker.ps_ratio()` | `ticker.info['priceToBook/Sales']` |
| `ticker.dividends()` | `ticker.dividends` |
| `ticker.earnings()` | `ticker.quarterly_earnings` |

---

## 6. API Source: AkShare

| | |
|---|---|
| **Library** | `akshare==1.17.26` |
| **Usage** | A-share lockup data only |
| **Method** | `ak.stock_restricted_shares_summary_em(symbol=cn_code)` |

---

## 7. API Source: Google Gemini

| | |
|---|---|
| **Endpoint** | `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent` |
| **Auth** | API Key (`GOOGLE_API_KEY`) |
| **Usage** | Screenshot OCR for option parameters |
| **Timeout** | 30 seconds |

---

## 8. API Source: ExchangeRate-API

| | |
|---|---|
| **Endpoint** | `https://api.exchangerate-api.com/v4/latest/USD` |
| **Cache** | 1 hour |
| **Fallback** | USD/HKD=7.8, USD/CNY=7.2 |

---

## 9. API Source: Alpha Vantage (Unused)

Listed in dependencies (`alpha_vantage==3.0.0`) but no active code paths use it. Available for future integration.

---

## 10. Market Alerts & Macro Data Sources (市场预警)

### Data Flow

```
analyze_stock()
  ├── get_macro_market_data()
  │     ├── yfinance ^TNX    → treasury_10y
  │     ├── yfinance DX-Y.NYB → dxy
  │     ├── yfinance GC=F    → gold
  │     ├── yfinance CL=F    → oil
  │     ├── get_fed_meeting_dates()         ← HARDCODED
  │     ├── get_cpi_release_dates()         ← COMPUTED
  │     ├── get_options_expiration_dates()  ← COMPUTED
  │     └── get_china_economic_events()     ← HARDCODED + COMPUTED
  ├── get_options_market_data(ticker)
  │     ├── yfinance ^VIX    → vix
  │     └── option_chain → put_call_ratio
  ├── get_polymarket_data()
  ├── calculate_geopolitical_risk()
  └── get_market_warnings()
```

### Complete Alert Table

| Alert Type | Trigger | Severity | Data Source |
|------------|---------|----------|-------------|
| VIX恐慌 | VIX >= 30 | HIGH | yfinance `^VIX` |
| VIX接近危险 | VIX >= 25 | MEDIUM | yfinance `^VIX` |
| 美债收益率飙升 | 10Y >= 5.0% | HIGH | yfinance `^TNX` |
| 美债收益率上升 | 10Y >= 4.5% | MEDIUM | yfinance `^TNX` |
| 黄金暴涨 | Gold change > 3% | HIGH | yfinance `GC=F` |
| 美联储会议 (0-3天) | Meeting in 0-3 days | HIGH | Hardcoded calendar |
| 美联储会议 (4-7天) | Meeting in 4-7 days | MEDIUM | Hardcoded calendar |
| CPI发布 (0-3天) | CPI in 0-3 days | MEDIUM | Computed dates |
| 期权到期 (0-3天) | Expiry in 0-3 days | HIGH | Computed (3rd Friday) |
| 财报发布 (0-3天) | Earnings in 0-3 days | HIGH | yfinance calendar |
| 地缘政治风险 | Risk score >= 7 | HIGH | Computed proxy |
| Polymarket关键事件 | Key events exist | MEDIUM | Polymarket API |

---

## 11. Fallback Chain per Data Type

| Data Type | Chain |
|-----------|-------|
| Stock Price | yfinance → defeatbeta → ERROR |
| Historical OHLCV | yfinance → defeatbeta → ERROR |
| Fundamentals | yfinance → defeatbeta (multiple methods) → ERROR |
| Options Chain | Tiger API → yfinance → Mock data |
| Options Expirations | Tiger API → yfinance → ERROR |
| Currency | ExchangeRate-API → Hardcoded defaults |
| A-Share Lockup | AkShare → Skip |
| Image Recognition | Gemini → ERROR (no fallback) |
| Macro Indicators | yfinance → None (skip alert) |
| Economic Events | Hardcoded/Computed (never fails) |
| Earnings Dates | yfinance calendar → yfinance info → Empty |
| Polymarket | GraphQL → REST → Empty |

---

## 12. defeatbeta-api: Unused Methods Available

可用于未来扩展的方法（详见原始文档 `docs/DATA_SOURCE_API.md`）：

- **Financial Statements**: `quarterly/annual_income_statement()`, `quarterly/annual_balance_sheet()`, `quarterly/annual_cash_flow()`
- **Additional Metrics**: `roic()`, `wacc()`, `peg_ratio()`, `equity_multiplier()`, `asset_turnover()`
- **Margin Variants**: `quarterly/annual_gross_margin()`, `ebitda_margin()`, `fcf_margin()`
- **Growth Variants**: `quarterly/annual_operating_income_yoy_growth()`, `ebitda_yoy_growth()`, `fcf_yoy_growth()`, `eps_yoy_growth()`
- **Revenue Breakdown**: `revenue_by_segment()`, `revenue_by_geography()`, `revenue_by_product()`
- **Industry Comparisons**: `industry_ttm_pe()`, `industry_ps_ratio()`, `industry_pb_ratio()`, `industry_roe()`, `industry_roa()`
- **Other**: `news()`, `earning_call_transcripts()`, `sec_filing()`, `officers()`, `calendar()`, `earnings_forecast()`, `revenue_forecast()`

---

## 13. Stability Improvement Opportunities

### Priority Actions

1. **High**: Add a second real-time options data source (reduce Tiger dependency)
2. **High**: Wire up defeatbeta `earnings()` and `calendar()` as fallback for earnings dates
3. **High**: Add fallback for macro indicators (VIX/Gold/Oil/TNX)
4. **Medium**: Replace hardcoded Fed meeting dates with an API
5. **Medium**: Use defeatbeta `industry_*` methods for sector comparison
6. **Low**: Integrate `news()` and `earning_call_transcripts()` for sentiment analysis
7. **Low**: Use `wacc()` and `roic()` for more advanced valuation scoring

---

*原始文档: docs/DATA_SOURCE_API.md (2026-01-28)*
*迁移日期: 2026-02-08*

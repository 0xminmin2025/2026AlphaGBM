# Formula Tester API Documentation

Base URL: `http://localhost:8100`

Interactive API Docs: `http://localhost:8100/docs`

## Data Fetching Endpoints

### GET /api/stock/{symbol}
Fetch comprehensive stock data including price, technicals, and fundamentals.

**Parameters:**
- `symbol` (path): Stock symbol (e.g., AAPL, TSLA)

**Response:**
```json
{
  "success": true,
  "symbol": "AAPL",
  "fetched_at": "2026-01-31T10:00:00",
  "data_source": "yfinance|defeatbeta",
  "price_data": {
    "current_price": 258.28,
    "prev_close": 256.44,
    "change": 1.84,
    "change_percent": 0.72,
    "high_52w": 288.62,
    "low_52w": 202.16,
    "volume": 67253000,
    "avg_volume_20d": 48743375
  },
  "technical_levels": {
    "resistance_1": 274.34,
    "resistance_2": 285.06,
    "support_1": 244.43,
    "support_2": 246.25,
    "ma_5": 255.29,
    "ma_20": 258.27,
    "ma_50": 268.45,
    "ma_200": null
  },
  "volatility": {
    "daily_volatility": 1.406,
    "annualized_volatility": 22.32,
    "beta": 1.09
  },
  "fundamentals": {
    "pe_ratio": 32.85,
    "forward_pe": 28.03,
    "peg_ratio": null,
    "pb_ratio": 51.49,
    "dividend_yield": 0.4,
    "market_cap": 3834168213504,
    "debt_to_equity": null,
    "roe": 39.36,
    "gross_margin": null,
    "revenue_growth": 7.94,
    "earnings_growth": 86.39
  },
  "history": {
    "dates": ["2025-11-03", ...],
    "open": [220.1, ...],
    "high": [222.5, ...],
    "low": [219.8, ...],
    "close": [221.2, ...],
    "volume": [45000000, ...]
  }
}
```

### GET /api/options/{symbol}
Fetch options chain data (yfinance only, no defeatbeta fallback).

**Parameters:**
- `symbol` (path): Stock symbol
- `expiry` (query, optional): Expiration date YYYY-MM-DD

**Response:**
```json
{
  "success": true,
  "symbol": "AAPL",
  "current_price": 258.28,
  "expiration": "2026-02-21",
  "days_to_expiry": 21,
  "available_expirations": ["2026-02-07", "2026-02-14", ...],
  "weighted_iv": 28.5,
  "atm_iv": 27.2,
  "calls": [
    {
      "strike": 255.0,
      "bid": 5.10,
      "ask": 5.25,
      "last": 5.15,
      "volume": 1234,
      "open_interest": 5678,
      "implied_volatility": 27.5,
      "delta": 0.55,
      "in_the_money": true
    }
  ],
  "puts": [...],
  "summary": {
    "total_calls": 50,
    "total_puts": 50,
    "call_volume": 12345,
    "put_volume": 9876,
    "call_oi": 45678,
    "put_oi": 34567
  }
}
```

### GET /api/history/{symbol}
Fetch historical OHLCV data.

**Parameters:**
- `symbol` (path): Stock symbol
- `period` (query): Data period - 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y (default: 6mo)
- `interval` (query): Data interval - 1m, 5m, 15m, 1h, 1d, 1wk (default: 1d)

---

## Technical Indicator Endpoints

### POST /api/calculate/atr
Calculate Average True Range.

**Request:**
```json
{
  "high": [100, 102, 101, ...],
  "low": [98, 99, 98, ...],
  "close": [99, 101, 100, ...],
  "period": 14
}
```

### POST /api/calculate/atr-stop-loss
Calculate ATR-based stop loss.

**Request:**
```json
{
  "buy_price": 100.0,
  "atr": 2.5,
  "atr_multiplier": 2.5,
  "min_stop_loss_pct": 0.15,
  "beta": 1.2
}
```

### POST /api/calculate/rsi
Calculate Relative Strength Index.

**Request:**
```json
{
  "prices": [100, 101, 99, 102, ...],
  "period": 14
}
```

### POST /api/calculate/volatility
Calculate historical volatility.

**Request:**
```json
{
  "prices": [100, 101, 99, ...],
  "period": 30
}
```

### POST /api/calculate/liquidity
Calculate options liquidity score.

**Request:**
```json
{
  "volume": 1000,
  "open_interest": 5000,
  "bid": 2.50,
  "ask": 2.60
}
```

---

## Stock Analysis Endpoints

### POST /api/calculate/risk-score
Calculate comprehensive risk score.

**Request:**
```json
{
  "volatility": 0.25,
  "pe_ratio": 25.0,
  "debt_to_equity": 0.5,
  "market_cap": 1000000000000,
  "sector": "technology"
}
```

### POST /api/calculate/sentiment
Calculate market sentiment.

**Request:**
```json
{
  "prices": [100, 101, 99, ...],
  "volumes": [1000000, 1200000, ...]
}
```

### POST /api/calculate/growth-score
Calculate growth stock score.

**Request:**
```json
{
  "revenue_growth": 0.25,
  "earnings_growth": 0.30,
  "peg_ratio": 1.5
}
```

### POST /api/calculate/value-score
Calculate value stock score.

**Request:**
```json
{
  "pe_ratio": 15.0,
  "pb_ratio": 2.0,
  "dividend_yield": 0.03
}
```

### POST /api/calculate/quality-score
Calculate quality stock score.

**Request:**
```json
{
  "roe": 0.25,
  "gross_margin": 0.40,
  "debt_to_equity": 0.3
}
```

---

## Options Analysis Endpoints

### POST /api/calculate/vrp
Calculate Volatility Risk Premium.

**Request:**
```json
{
  "implied_volatility": 0.35,
  "historical_volatility": 0.25,
  "atm_iv": 0.33
}
```

**Response:**
```json
{
  "success": true,
  "vrp_absolute": 10.0,
  "vrp_relative_pct": 40.0,
  "volatility_ratio": 1.4,
  "signal_strength": "very_strong_positive",
  "vrp_level": "very_high",
  "strategy_bias": "seller",
  "suggested_strategies": ["sell_put", "sell_call", "iron_condor"]
}
```

### POST /api/calculate/sell-put-score
Calculate comprehensive Sell Put score.

**Request:**
```json
{
  "current_price": 100.0,
  "strike": 95.0,
  "bid": 1.50,
  "ask": 1.60,
  "days_to_expiry": 30,
  "implied_volatility": 0.30,
  "volume": 500,
  "open_interest": 2000,
  "atr": 2.0,
  "support_1": 94.0,
  "support_2": 90.0,
  "ma_50": 98.0,
  "ma_200": 95.0,
  "low_52w": 80.0,
  "trend": "uptrend",
  "trend_strength": 0.7
}
```

### POST /api/calculate/sell-call-score
Calculate comprehensive Sell Call score.

**Request:**
```json
{
  "current_price": 100.0,
  "strike": 105.0,
  "bid": 1.20,
  "ask": 1.30,
  "days_to_expiry": 30,
  "implied_volatility": 0.28,
  "volume": 400,
  "open_interest": 1800,
  "atr": 2.0,
  "resistance_1": 106.0,
  "resistance_2": 110.0,
  "ma_50": 98.0,
  "ma_200": 95.0,
  "high_52w": 115.0,
  "is_covered": true,
  "change_percent": 1.5,
  "trend": "sideways",
  "trend_strength": 0.4
}
```

### POST /api/calculate/buy-call-score
Calculate Buy Call score.

**Request:**
```json
{
  "current_price": 100.0,
  "strike": 105.0,
  "bid": 2.50,
  "ask": 2.70,
  "days_to_expiry": 45,
  "implied_volatility": 0.30,
  "historical_volatility": 0.35,
  "delta": 0.40,
  "volume": 800,
  "open_interest": 3000,
  "change_percent": 2.5,
  "resistance_1": 108.0,
  "resistance_2": 112.0,
  "high_52w": 120.0,
  "low_52w": 75.0
}
```

### POST /api/calculate/buy-put-score
Calculate Buy Put score.

**Request:**
```json
{
  "current_price": 100.0,
  "strike": 95.0,
  "bid": 2.00,
  "ask": 2.20,
  "days_to_expiry": 45,
  "implied_volatility": 0.32,
  "historical_volatility": 0.28,
  "delta": -0.35,
  "volume": 600,
  "open_interest": 2500,
  "change_percent": -1.5,
  "support_1": 94.0,
  "support_2": 88.0,
  "high_52w": 115.0,
  "low_52w": 80.0
}
```

### POST /api/calculate/risk-return-profile
Calculate risk-return profile for options strategy.

**Request:**
```json
{
  "strategy": "sell_put",
  "current_price": 100.0,
  "strike": 95.0,
  "premium": 1.50,
  "days_to_expiry": 30,
  "implied_volatility": 0.30,
  "vrp_level": "high"
}
```

---

## Health Check

### GET /api/health
Returns API health status.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

---

## Notes

1. **Data Sources**: Stock and history data first tries yfinance, then falls back to defeatbeta-api if rate limited.
2. **Options Data**: Only available from yfinance (no defeatbeta fallback).
3. **Rate Limiting**: If you see 404 errors, it's likely due to yfinance rate limiting. Wait a few seconds and try again.
4. **Interactive Docs**: Visit `http://localhost:8100/docs` for Swagger UI with try-it-out functionality.

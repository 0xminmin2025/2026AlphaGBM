# Formula Tester

Interactive web application for testing AlphaGBM stock and options analysis formulas.

## Features

- **Stock Analysis Calculators**
  - Risk Score Calculator
  - Target Price Calculator
  - Market Sentiment Calculator
  - Style Scores (Growth/Value/Quality)

- **Options Scoring Calculators**
  - VRP (Volatility Risk Premium) Calculator
  - Trend Alignment Score Calculator
  - Sell Put Score Calculator
  - Sell Call Score Calculator
  - Risk-Return Profile Calculator

- **Technical Indicators**
  - ATR (Average True Range) Calculator
  - ATR-based Stop Loss Calculator
  - RSI Calculator
  - Liquidity Score Calculator
  - ATR Safety Margin Calculator

- **Raw Data Display**
  - Fetch real-time stock data via yfinance
  - Fetch options chain data
  - Price history charts

## Setup

### Backend

```bash
cd formula-tester/backend
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8100
```

### Frontend

Simply open `formula-tester/frontend/index.html` in a web browser, or serve it with any static file server.

For development, you can use Python's built-in server:

```bash
cd formula-tester/frontend
python -m http.server 8080
```

Then open http://localhost:8080 in your browser.

## API Endpoints

### Data Fetching
- `GET /api/stock/{symbol}` - Fetch stock data
- `GET /api/options/{symbol}` - Fetch options chain
- `GET /api/history/{symbol}` - Fetch historical OHLCV

### Technical Indicators
- `POST /api/calculate/atr` - Calculate ATR
- `POST /api/calculate/atr-stop-loss` - Calculate ATR-based stop loss
- `POST /api/calculate/rsi` - Calculate RSI
- `POST /api/calculate/volatility` - Calculate historical volatility
- `POST /api/calculate/liquidity` - Calculate liquidity score
- `POST /api/calculate/atr-safety` - Calculate ATR safety margin

### Stock Analysis
- `POST /api/calculate/risk-score` - Calculate risk score
- `POST /api/calculate/sentiment` - Calculate market sentiment
- `POST /api/calculate/target-price` - Calculate target price
- `POST /api/calculate/growth-score` - Calculate growth score
- `POST /api/calculate/value-score` - Calculate value score
- `POST /api/calculate/quality-score` - Calculate quality score

### Options Analysis
- `POST /api/calculate/vrp` - Calculate VRP
- `POST /api/calculate/trend-alignment` - Calculate trend alignment
- `POST /api/calculate/sell-put-score` - Calculate sell put score
- `POST /api/calculate/sell-call-score` - Calculate sell call score
- `POST /api/calculate/buy-call-score` - Calculate buy call score
- `POST /api/calculate/buy-put-score` - Calculate buy put score
- `POST /api/calculate/risk-return-profile` - Calculate risk-return profile

## Usage

1. Start the backend server on port 8100
2. Open the frontend in a browser
3. Enter a stock symbol (e.g., AAPL) and click "Fetch Data"
4. Use the calculators with pre-populated data or adjust values manually
5. Click "Calculate" to see formula results

## Notes

- The backend fetches real market data from Yahoo Finance
- yfinance may have rate limits; if you get errors, wait a few seconds
- All calculators work independently; you can test formulas without fetching data
- Formula details can be viewed by clicking "Show Formula" on each calculator

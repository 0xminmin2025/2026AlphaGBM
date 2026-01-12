import yfinance as yf
import sys

def test_ticker(ticker="AAPL"):
    print(f"Testing ticker: {ticker}")
    try:
        stock = yf.Ticker(ticker)
        print("Getting info...")
        # Try fast info first
        try:
             print(f"Fast Info Price: {stock.fast_info.last_price}")
        except Exception as e:
             print(f"Fast Info failed: {e}")

        info = stock.info
        print(f"Info loaded. Keys: {len(info)}")
        print(f"Current Price: {info.get('currentPrice')}")
        
        print("Getting history...")
        hist = stock.history(period="1mo")
        print(f"History loaded. Rows: {len(hist)}")
        if len(hist) > 0:
            print(f"Last close: {hist['Close'].iloc[-1]}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    test_ticker(ticker)

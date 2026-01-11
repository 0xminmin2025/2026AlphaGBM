# Option Query Service

A complete full-stack application for querying stock option data using Tiger Open API.

## 🚀 Features

- **Backend API Service**: FastAPI-based REST API for option data
- **Frontend Web Interface**: Modern, responsive HTML/CSS/JavaScript interface
- **Option Chain Data**: Complete CALL and PUT option information
- **Expiration Dates**: Dynamic loading of available option expiration dates
- **Mock Data Support**: Works with mock data while API authentication is being resolved
- **Real-time Ready**: Structured for easy integration with Tiger Open API

## 📁 Project Structure

```
tiger/
├── venv/                          # Python virtual environment
├── option_service.py              # FastAPI backend service
├── frontend.html                  # Web interface
├── tiger_client.py                # Tiger API client wrapper
├── test_simple.py                 # Client configuration test
├── test_client.py                 # Detailed client test (legacy)
├── private_key.pem               # RSA private key for Tiger API
├── tiger_openapi_config.properties  # Tiger API configuration
├── tiger_openapi_token.properties   # Tiger API token
├── CLAUDE.md                     # Tiger API documentation
├── option.md                     # Option API documentation
├── quotelist.md                  # Quote API documentation
└── README.md                     # This file
```

## 🛠️ Setup Instructions

### Prerequisites

- Python 3.8+
- Tiger Brokers account with API access
- Valid Tiger API credentials

### Installation

1. **Clone or navigate to the project directory**

2. **Create and activate virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install required packages**
   ```bash
   pip install tigeropen fastapi uvicorn jinja2 python-multipart aiofiles
   ```

4. **Configure Tiger API credentials**
   - Ensure `tiger_openapi_config.properties` contains your Tiger API credentials
   - Verify `tiger_openapi_token.properties` has your API token
   - Check that `private_key.pem` contains your private key in PKCS#1 format

## 🚀 Running the Application

### Start the Backend Service

```bash
# Activate virtual environment
source venv/bin/activate

# Start the FastAPI server
uvicorn option_service:app --host 127.0.0.1 --port 8000 --reload
```

The service will be available at:
- **Frontend Interface**: http://127.0.0.1:8000
- **API Documentation**: http://127.0.0.1:8000/docs
- **Health Check**: http://127.0.0.1:8000/health

### Test the Client Configuration

```bash
# Test Tiger API client setup
python test_simple.py
```

## 📡 API Endpoints

### REST API

- `GET /` - Frontend web interface
- `GET /expirations/{symbol}` - Get option expiration dates
- `GET /options/{symbol}/{expiry_date}` - Get complete option chain
- `GET /quote/{symbol}` - Get basic stock quote
- `GET /config` - Get current service configuration
- `POST /config/data-source/{source}` - Set data source (mock/real)
- `GET /health` - Health check endpoint
- `GET /docs` - Interactive API documentation

### Configuration API

The service supports both mock and real Tiger API data. You can switch between modes:

```bash
# Check current configuration
curl http://127.0.0.1:8000/config

# Switch to mock data (safe, always works)
curl -X POST http://127.0.0.1:8000/config/data-source/mock

# Switch to real Tiger API data (requires valid credentials)
curl -X POST http://127.0.0.1:8000/config/data-source/real
```

### Example API Usage

```bash
# Get expiration dates for AAPL
curl http://127.0.0.1:8000/expirations/AAPL

# Get option chain for AAPL expiring 2024-01-19
curl http://127.0.0.1:8000/options/AAPL/2024-01-19

# Get basic quote for AAPL
curl http://127.0.0.1:8000/quote/AAPL
```

## 🖥️ Frontend Interface

The web interface provides:

- **Symbol Input**: Enter any stock symbol
- **Dynamic Expiration Loading**: Automatically loads available expiration dates
- **Option Chain Display**: Side-by-side CALL and PUT options
- **Detailed Information**: Strike prices, bid/ask, volume, Greeks, etc.
- **Responsive Design**: Works on desktop and mobile devices

### How to Use

1. Open http://127.0.0.1:8000 in your browser
2. Enter a stock symbol (e.g., AAPL)
3. Click "Load Dates" to get available expiration dates
4. Select an expiration date from the dropdown
5. Click "Query Options" to load the complete option chain

## 🔧 Technical Details

### Backend Architecture

- **FastAPI**: Modern, fast web framework for building APIs
- **Pydantic**: Data validation and serialization
- **CORS Enabled**: Allows frontend-backend communication
- **Mock Data**: Currently uses realistic mock data
- **Tiger API Ready**: Structure prepared for real API integration

### Data Models

- **OptionData**: Individual option contract information
- **OptionChainResponse**: Complete option chain with calls and puts
- **ExpirationResponse**: Available expiration dates
- **StockQuote**: Basic stock quote information

### Frontend Technology

- **Pure HTML/CSS/JavaScript**: No external dependencies
- **Responsive Design**: CSS Grid and Flexbox
- **Modern UI**: Clean, professional interface
- **Error Handling**: User-friendly error messages
- **Loading States**: Visual feedback during data loading

## 🔐 Tiger API Integration

### Current Status

- ✅ Configuration files setup
- ✅ Client wrapper implemented
- ⚠️ Authentication issues (signature verification)
- ✅ Mock data system working
- ✅ API structure ready for real data

### Authentication Issues

Currently experiencing signature verification errors with Tiger API:
```
code=1000 msg=common param error(failed to verify signature, please make sure you use the correct rsa private key, if you use python sdk, the private key is in pkcs#1 format)
```

This error typically indicates:
- **Private key doesn't match Tiger ID**: The private key and Tiger ID are not paired correctly
- **Incorrect Tiger ID**: The Tiger ID in the configuration may be wrong
- **Private key format**: Despite using PKCS#1 format, the key may be corrupted

### Troubleshooting Authentication

1. **Verify Tiger ID and Private Key Match**:
   - Double-check the Tiger ID in `tiger_openapi_config.properties`
   - Ensure the private key corresponds to this exact Tiger ID
   - Download fresh credentials from Tiger developer portal

2. **Test with Debugging Scripts**:
   ```bash
   # Run comprehensive authentication tests
   python debug_auth.py
   python debug_auth2.py
   ```

3. **Manual Configuration Check**:
   - Verify `tiger_openapi_config.properties` contains correct values
   - Check `tiger_openapi_token.properties` for HK license
   - Ensure `private_key.pem` file is properly formatted

### Next Steps for Real API Integration

✅ **Service Architecture**: Complete and ready for real data
✅ **Mock/Real Toggle**: Easy switching between data sources
✅ **Error Handling**: Graceful fallback to mock data
⚠️ **Authentication**: Needs credential verification

Once authentication is resolved:
1. Set `USE_MOCK_DATA = False` in `option_service.py`, or
2. Use the API: `POST /config/data-source/real`
3. Service will automatically use real Tiger API data

## 📊 Option Data Fields

The service provides comprehensive option information:

| Field | Description |
|-------|-------------|
| Strike | Option strike price |
| Last Price | Most recent option price |
| Bid/Ask | Current bid and ask prices |
| Volume | Trading volume |
| Open Interest (OI) | Number of outstanding contracts |
| Implied Volatility (IV) | Market's forecast of volatility |
| Delta | Price sensitivity to underlying |
| Gamma | Rate of change of delta |
| Theta | Time decay |
| Vega | Volatility sensitivity |

## 🛡️ Error Handling

The application includes comprehensive error handling:

- **API Errors**: Proper HTTP status codes and error messages
- **Client Errors**: User-friendly frontend error displays
- **Network Issues**: Timeout and connection error handling
- **Data Validation**: Input validation and sanitization

## 📱 Mobile Support

The frontend is fully responsive and works on:

- Desktop computers
- Tablets
- Mobile phones
- Different screen orientations

## 🧪 Testing

Run tests to verify functionality:

```bash
# Test client configuration
python test_simple.py

# Test API endpoints
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/expirations/AAPL
```

## 📈 Example Option Chain

The service returns data in this format:

```json
{
  "symbol": "AAPL",
  "expiry_date": "2024-01-19",
  "calls": [
    {
      "identifier": "AAPL 20240119C00150000",
      "symbol": "AAPL",
      "strike": 150.0,
      "put_call": "CALL",
      "latest_price": 5.25,
      "bid_price": 5.20,
      "ask_price": 5.30,
      "volume": 1250,
      "open_interest": 5600,
      "implied_vol": 0.234,
      "delta": 0.52,
      "gamma": 0.012,
      "theta": -0.08,
      "vega": 12.5
    }
  ],
  "puts": [...]
}
```

## 🚀 Future Enhancements

- Real Tiger API integration
- Real-time option pricing
- Historical option data
- Option strategy analysis
- Price alerts and notifications
- Portfolio tracking
- Advanced filtering and sorting
- Export functionality

## 📞 Support

For issues with:
- **Tiger API Authentication**: Check credentials and private key format
- **Backend Service**: Check server logs and API documentation
- **Frontend Issues**: Check browser console for JavaScript errors

---

**Note**: This application currently uses mock data due to Tiger API authentication issues. The complete infrastructure is ready for real API integration once authentication is resolved.
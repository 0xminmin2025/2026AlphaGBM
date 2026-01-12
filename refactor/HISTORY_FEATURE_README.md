# Analysis History Feature Implementation

This document outlines the implementation of analysis history tracking for both stock and option analysis.

## 🚀 New Features

### 1. **Stock Analysis Credit Consumption & History**
- ✅ **Credit System**: Stock analysis now properly consumes credits
- ✅ **Database History**: Complete analysis results stored in `stock_analysis_history` table
- ✅ **History UI**: View, search, and re-analyze past stock analyses
- ✅ **Pagination**: Efficient browsing of analysis history

### 2. **Option Analysis History**
- ✅ **Browser Cache**: Option analysis stored in localStorage (no database)
- ✅ **History UI**: View and manage option analysis history
- ✅ **Auto-saving**: Automatically saves when option chain analysis is performed

### 3. **Enhanced User Experience**
- ✅ **Tab Navigation**: Clean tabs interface for Analysis vs History
- ✅ **Smart Filtering**: Filter history by ticker/symbol
- ✅ **Quick Actions**: Re-analyze from history with one click
- ✅ **Detailed Views**: Full analysis data in modal dialogs

## 📊 Database Tables

### Current Tables Overview:

1. **User** - Core user management with Supabase UUID integration
2. **AnalysisRequest** - Basic analysis request tracking (legacy)
3. **Feedback** - User feedback collection
4. **DailyQueryCount** - Daily query limits management
5. **PortfolioHolding** - User's stock holdings
6. **DailyProfitLoss** - Daily P&L aggregation
7. **StyleProfit** - Style-specific profit tracking
8. **Subscription** - Stripe subscription management (Plus/Pro plans)
9. **Transaction** - Payment transaction records
10. **CreditLedger** - Credit allocation tracking by service type
11. **UsageLog** - Service usage logging and credit consumption
12. **🆕 StockAnalysisHistory** - Complete stock analysis results storage

### StockAnalysisHistory Table Schema:

```sql
CREATE TABLE stock_analysis_history (
    id INTEGER PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,  -- Supabase UUID
    ticker VARCHAR(20) NOT NULL,
    style VARCHAR(20) NOT NULL,

    -- Market Data
    current_price FLOAT,
    target_price FLOAT,
    stop_loss_price FLOAT,
    market_sentiment FLOAT,

    -- Risk Analysis
    risk_score FLOAT,
    risk_level VARCHAR(20),
    position_size FLOAT,

    -- EV Model Results
    ev_score FLOAT,
    ev_weighted_pct FLOAT,
    recommendation_action VARCHAR(20),
    recommendation_confidence VARCHAR(20),

    -- AI Analysis
    ai_summary TEXT,

    -- Full Data (JSON)
    full_analysis_data JSON,

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    -- Indexes
    INDEX idx_user_ticker (user_id, ticker),
    INDEX idx_created_at (created_at)
);
```

## 🛠️ Installation & Setup

### 1. Database Migration

```bash
cd /path/to/AlphaG/refactor/backend
python3 create_history_table.py
```

This will:
- Create the `stock_analysis_history` table
- Verify table creation
- Display table structure

### 2. Backend Changes

**Credit Consumption**: Stock analysis endpoint now uses `@check_quota` decorator:
```python
@stock_bp.route('/analyze', methods=['POST'])
@check_quota(service_type=ServiceType.STOCK_ANALYSIS.value, amount=1)
def analyze_stock():
    # Analysis logic...
    # Automatically saves to history after successful analysis
```

**New API Endpoints**:
- `GET /api/stock/history` - Get paginated analysis history
- `GET /api/stock/history/<id>` - Get detailed analysis by ID

### 3. Frontend Components

**New Components**:
- `StockAnalysisHistory.tsx` - Stock history management
- `OptionAnalysisHistory.tsx` - Option history management (localStorage)
- `historyStorage.ts` - Browser storage utility

**Updated Pages**:
- `Home.tsx` - Added tabs for Analysis/History
- `Options.tsx` - Added tabs for Analysis/History + auto-save

## 📱 User Interface

### Stock Analysis Page (`/`)
```
┌─────────────────────────────────────┐
│  [股票分析]  [分析历史]             │
├─────────────────────────────────────┤
│  Stock Analysis Form               │
│  ┌─────────────────────────────────┐  │
│  │ Ticker: [AAPL]  Style: [Quality] │ │
│  │ [分析] Button                   │ │
│  └─────────────────────────────────┘  │
│                                     │
│  Analysis Results...                │
└─────────────────────────────────────┘

History Tab:
┌─────────────────────────────────────┐
│  Search: [AAPL] [🔍]               │
├─────────────────────────────────────┤
│  📊 AAPL - Quality - 2024-01-12    │
│  Price: $150.00 → Target: $165.00  │
│  Risk: Medium | Action: Buy         │
│  [重新分析] [查看详情]              │
├─────────────────────────────────────┤
│  📊 MSFT - Growth - 2024-01-11     │
│  ...                               │
└─────────────────────────────────────┘
```

### Option Analysis Page (`/options`)
```
┌─────────────────────────────────────┐
│  [期权分析]  [分析历史]             │
├─────────────────────────────────────┤
│  Option Chain Analysis Form        │
│  ┌─────────────────────────────────┐  │
│  │ Symbol: [AAPL] Expiry: [...]    │ │
│  │ [加载期权链] Button              │ │
│  └─────────────────────────────────┘  │
│                                     │
│  Option Chain Results...            │
└─────────────────────────────────────┘

History Tab (Browser Storage):
┌─────────────────────────────────────┐
│  Search: [AAPL] [🔍] [清空历史]    │
├─────────────────────────────────────┤
│  📈 AAPL - 2024-02-16 - 期权链分析 │
│  Analysis: Chain | 2024-01-12      │
│  [重新分析] [查看详情] [🗑️]        │
├─────────────────────────────────────┤
│  📈 TSLA - 2024-01-19 - 增强分析   │
│  ...                               │
└─────────────────────────────────────┘
```

## ⚡ Credit System

### How It Works:
1. **Daily Free Quota**:
   - Stock Analysis: 2 free analyses/day
   - Option Analysis: 1 free analysis/day
   - Deep Reports: 0 free (premium only)

2. **Subscription Credits**:
   - Plus Plan: 1,000/month or 12,000/year
   - Pro Plan: 5,000/month or 60,000/year
   - Credits stored as `stock_analysis` type but usable for all services

3. **Credit Consumption Order**:
   - First: Use daily free quota (if available)
   - Then: Deduct from subscription credits (FIFO basis)
   - If insufficient: Return 402 error with remaining credits

### API Response Format:
```json
{
  "success": true,
  "data": { ... },
  "remaining_credits": 150
}

// Or on insufficient credits:
{
  "error": "额度不足，请充值或明天再来",
  "remaining_credits": 0,
  "code": "INSUFFICIENT_CREDITS"
}
```

## 🔧 Configuration

### Environment Variables:
```bash
# Existing Stripe configuration
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Price IDs for subscription plans
STRIPE_PRICE_PLUS_MONTHLY=price_...
STRIPE_PRICE_PLUS_YEARLY=price_...
STRIPE_PRICE_PRO_MONTHLY=price_...
STRIPE_PRICE_PRO_YEARLY=price_...
STRIPE_PRICE_TOPUP_100=price_...
```

### Database Configuration:
- Ensure your database supports JSON columns (PostgreSQL/MySQL 5.7+)
- Run migration script before starting the backend

## 🐛 Troubleshooting

### Common Issues:

1. **Table doesn't exist**:
   ```bash
   python3 create_history_table.py
   ```

2. **Credit consumption not working**:
   - Check `@check_quota` decorator is applied
   - Verify PaymentService configuration
   - Check user authentication

3. **History not saving**:
   - Check database permissions
   - Verify user_id is properly set in Flask globals
   - Check error logs for JSON serialization issues

4. **Option history not working**:
   - Ensure localStorage is available
   - Check browser console for errors
   - Verify HistoryStorage import

### Debug Commands:

```bash
# Check table structure
python3 -c "
from app import create_app
from sqlalchemy import inspect
app = create_app()
with app.app_context():
    from app.models import db
    inspector = inspect(db.engine)
    print(inspector.get_columns('stock_analysis_history'))
"

# Check credit balance
python3 -c "
from app import create_app
from app.services.payment_service import PaymentService
app = create_app()
with app.app_context():
    credits = PaymentService.get_total_credits('USER_UUID_HERE')
    print(f'Credits: {credits}')
"
```

## 📈 Future Enhancements

### Potential Improvements:
1. **Advanced Filtering**: Date ranges, risk levels, performance
2. **Export Features**: CSV/PDF export of history
3. **Performance Analytics**: Track prediction accuracy
4. **History Sync**: Option to save option history to database
5. **Bulk Operations**: Delete multiple history items
6. **Search Enhancement**: Full-text search in AI summaries

### Database Optimizations:
1. **Partitioning**: Partition history table by date for better performance
2. **Archival**: Move old records to archive table
3. **Indexing**: Add composite indexes for common queries
4. **Compression**: Compress JSON data for storage efficiency

## 🔐 Security Considerations

1. **Data Isolation**: All queries filtered by user_id
2. **Input Validation**: Ticker symbols validated
3. **Rate Limiting**: Credit system prevents abuse
4. **Data Retention**: Consider implementing data retention policies
5. **Privacy**: Option history stored locally (user controls deletion)

---

**Happy Analyzing! 📊🚀**
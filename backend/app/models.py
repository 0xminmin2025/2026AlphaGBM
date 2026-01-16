from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import enum

db = SQLAlchemy()

# Enums
class ServiceType(enum.Enum):
    STOCK_ANALYSIS = 'stock_analysis'
    OPTION_ANALYSIS = 'option_analysis'
    DEEP_REPORT = 'deep_report'

class CreditSource(enum.Enum):
    SUBSCRIPTION = 'subscription'
    TOP_UP = 'top_up'
    REFERRAL = 'referral'
    SYSTEM_GRANT = 'system_grant'
    REFUND = 'refund'

class PlanTier(enum.Enum):
    FREE = 'free'
    PLUS = 'plus'
    PRO = 'pro'

class SubscriptionStatus(enum.Enum):
    ACTIVE = 'active'
    CANCELED = 'canceled'
    PAST_DUE = 'past_due'
    UNPAID = 'unpaid'
    TRIALING = 'trialing'

class TransactionStatus(enum.Enum):
    PENDING = 'pending'
    SUCCEEDED = 'succeeded'
    FAILED = 'failed'

class TaskType(enum.Enum):
    STOCK_ANALYSIS = 'stock_analysis'
    OPTION_ANALYSIS = 'option_analysis'
    ENHANCED_OPTION_ANALYSIS = 'enhanced_option_analysis'

class TaskStatus(enum.Enum):
    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'


# Core Models
class User(db.Model):
    # Supabase uses UUID for user ID
    id = db.Column(db.String(36), primary_key=True) 
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    username = db.Column(db.String(80), nullable=True) 
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Payment Related
    stripe_customer_id = db.Column(db.String(255), index=True, nullable=True)
    referrer_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=True)
    
    # Relationships
    referrer = db.relationship('User', remote_side=[id], backref='referrals')
    analysis_requests = db.relationship('AnalysisRequest', backref='user', lazy=True)
    feedbacks = db.relationship('Feedback', backref='user', lazy=True)
    daily_queries = db.relationship('DailyQueryCount', backref='user', lazy=True)

class AnalysisRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=True, index=True)
    ticker = db.Column(db.String(20), nullable=False)
    style = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='success')
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False, index=True)
    type = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    ticker = db.Column(db.String(20), nullable=True)
    ip_address = db.Column(db.String(50), nullable=True)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

class DailyQueryCount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False)
    query_count = db.Column(db.Integer, default=0)
    max_queries = db.Column(db.Integer, default=5)
    reset_time = db.Column(db.DateTime, nullable=False)

class PortfolioHolding(db.Model):
    __tablename__ = 'portfolio_holdings'
    
    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(20), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    shares = db.Column(db.Integer, nullable=False)
    buy_price = db.Column(db.Float, nullable=False)
    style = db.Column(db.String(20), nullable=False, index=True)
    user_id = db.Column(db.String(36), nullable=True, index=True)
    currency = db.Column(db.String(3), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DailyProfitLoss(db.Model):
    __tablename__ = 'daily_profit_loss'
    
    id = db.Column(db.Integer, primary_key=True)
    trading_date = db.Column(db.Date, nullable=False, index=True)
    total_actual_investment = db.Column(db.Float, nullable=False)
    total_market_value = db.Column(db.Float, nullable=False)
    total_profit_loss = db.Column(db.Float, nullable=False)
    total_profit_loss_percent = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.String(36), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class StyleProfit(db.Model):
    __tablename__ = 'style_profits'
    
    id = db.Column(db.Integer, primary_key=True)
    trading_date = db.Column(db.Date, nullable=False, index=True)
    style = db.Column(db.String(20), nullable=False)
    style_investment = db.Column(db.Float, nullable=False)
    style_market_value = db.Column(db.Float, nullable=False)
    style_profit_loss = db.Column(db.Float, nullable=False)
    style_profit_loss_percent = db.Column(db.Float, nullable=False)

class PortfolioRebalance(db.Model):
    __tablename__ = 'portfolio_rebalances'
    """
    Record portfolio rebalancing history (every 2 weeks)
    Stores changes: added, removed, adjusted holdings
    """
    id = db.Column(db.Integer, primary_key=True)
    rebalance_date = db.Column(db.Date, nullable=False, index=True)
    rebalance_number = db.Column(db.Integer, nullable=False)  # 1st, 2nd, 3rd rebalance...
    
    # Changes summary
    holdings_added = db.Column(db.Integer, default=0)  # Number of new holdings
    holdings_removed = db.Column(db.Integer, default=0)  # Number of removed holdings
    holdings_adjusted = db.Column(db.Integer, default=0)  # Number of adjusted holdings
    
    # Portfolio value after rebalance
    total_investment = db.Column(db.Float, nullable=False)
    total_market_value = db.Column(db.Float, nullable=False)
    total_profit_loss = db.Column(db.Float, nullable=False)
    total_profit_loss_percent = db.Column(db.Float, nullable=False)
    
    # Style-specific stats after rebalance
    style_stats = db.Column(db.JSON, nullable=True)  # {style: {investment, market_value, profit_loss, profit_loss_percent}}
    
    # Detailed changes (JSON format)
    # {added: [{ticker, name, shares, buy_price, style}], 
    #  removed: [{ticker, name, shares, style}],
    #  adjusted: [{ticker, name, old_shares, new_shares, old_price, new_price, style}]}
    changes_detail = db.Column(db.JSON, nullable=True)
    
    notes = db.Column(db.Text, nullable=True)  # Optional notes about the rebalance
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Payment Models (Consolidated)
class Subscription(db.Model):
    __tablename__ = 'subscriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False, index=True)
    stripe_subscription_id = db.Column(db.String(255), unique=True, nullable=False)
    plan_tier = db.Column(db.String(50), nullable=False) # plus, pro
    status = db.Column(db.String(50), nullable=False) # active, canceled, etc.
    current_period_start = db.Column(db.DateTime, default=datetime.utcnow)
    current_period_end = db.Column(db.DateTime)
    cancel_at_period_end = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Transaction(db.Model):
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False, index=True)
    stripe_payment_intent_id = db.Column(db.String(255), unique=True, nullable=True)
    stripe_checkout_session_id = db.Column(db.String(255), unique=True, nullable=True)
    amount = db.Column(db.Integer, nullable=False) # In cents
    currency = db.Column(db.String(10), nullable=False, default='cny')
    status = db.Column(db.String(50), nullable=False) # succeeded, pending, failed
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CreditLedger(db.Model):
    """额度台账 - 记录每一笔额度的来源和去向"""
    __tablename__ = 'credit_ledger'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False, index=True)
    service_type = db.Column(db.String(50), nullable=False, default=ServiceType.STOCK_ANALYSIS.value)
    source = db.Column(db.String(50), nullable=False) # subscription, top_up, referral, system_grant
    amount_initial = db.Column(db.Integer, nullable=False) # 初始额度
    amount_remaining = db.Column(db.Integer, nullable=False) # 剩余额度
    expires_at = db.Column(db.DateTime, nullable=True) # 过期时间，None表示永久有效
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscriptions.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class UsageLog(db.Model):
    """使用日志 - 记录每一次消耗"""
    __tablename__ = 'usage_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False, index=True)
    credit_ledger_id = db.Column(db.Integer, db.ForeignKey('credit_ledger.id'), nullable=True) # 如果使用了特定额度包
    service_type = db.Column(db.String(50), nullable=False)
    ticker = db.Column(db.String(20), nullable=True)
    amount_used = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class StockAnalysisHistory(db.Model):
    """股票分析历史记录"""
    __tablename__ = 'stock_analysis_history'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False, index=True)
    ticker = db.Column(db.String(20), nullable=False, index=True)
    style = db.Column(db.String(20), nullable=False)

    # Market Data
    current_price = db.Column(db.Float, nullable=True)
    target_price = db.Column(db.Float, nullable=True)
    stop_loss_price = db.Column(db.Float, nullable=True)
    market_sentiment = db.Column(db.Float, nullable=True)

    # Risk Analysis Results
    risk_score = db.Column(db.Float, nullable=True)
    risk_level = db.Column(db.String(20), nullable=True)
    position_size = db.Column(db.Float, nullable=True)

    # EV Model Results
    ev_score = db.Column(db.Float, nullable=True)
    ev_weighted_pct = db.Column(db.Float, nullable=True)
    recommendation_action = db.Column(db.String(20), nullable=True)
    recommendation_confidence = db.Column(db.String(20), nullable=True)

    # AI Analysis
    ai_summary = db.Column(db.Text, nullable=True)

    # Store full JSON data for reference
    full_analysis_data = db.Column(db.JSON, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class OptionsAnalysisHistory(db.Model):
    """期权分析历史记录"""
    __tablename__ = 'options_analysis_history'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False, index=True)
    symbol = db.Column(db.String(20), nullable=False, index=True)
    option_identifier = db.Column(db.String(100), nullable=True)  # For enhanced analysis
    expiry_date = db.Column(db.String(20), nullable=True)

    # Analysis Type
    analysis_type = db.Column(db.String(50), nullable=False)  # 'basic_chain', 'enhanced_analysis'

    # Basic chain analysis results
    strike_price = db.Column(db.Float, nullable=True)
    option_type = db.Column(db.String(10), nullable=True)  # 'call' or 'put'
    option_score = db.Column(db.Float, nullable=True)
    iv_rank = db.Column(db.Float, nullable=True)

    # Enhanced analysis results
    vrp_analysis = db.Column(db.JSON, nullable=True)
    risk_analysis = db.Column(db.JSON, nullable=True)

    # AI Summary for options
    ai_summary = db.Column(db.Text, nullable=True)

    # Store full JSON data for reference
    full_analysis_data = db.Column(db.JSON, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class AnalysisTask(db.Model):
    """异步分析任务队列"""
    __tablename__ = 'analysis_tasks'

    id = db.Column(db.String(36), primary_key=True)  # UUID for task ID
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False, index=True)

    # Task details
    task_type = db.Column(db.String(50), nullable=False, index=True)  # stock_analysis, option_analysis, etc.
    status = db.Column(db.String(20), nullable=False, default='pending', index=True)
    priority = db.Column(db.Integer, nullable=False, default=100)  # Lower number = higher priority

    # Input parameters (stored as JSON)
    input_params = db.Column(db.JSON, nullable=False)  # ticker, style, options params, etc.

    # Progress tracking
    progress_percent = db.Column(db.Integer, nullable=False, default=0)
    current_step = db.Column(db.Text, nullable=True)  # Changed from String(500) to Text to support longer error messages

    # Results
    result_data = db.Column(db.JSON, nullable=True)  # Complete analysis result
    error_message = db.Column(db.Text, nullable=True)

    # Timing
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    related_history_id = db.Column(db.Integer, nullable=True)  # Link to StockAnalysisHistory/OptionsAnalysisHistory
    related_history_type = db.Column(db.String(50), nullable=True)  # 'stock' or 'options'

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'user_id': self.user_id,  # Fixed: Added missing user_id field
            'task_type': self.task_type,
            'status': self.status,
            'progress_percent': self.progress_percent,
            'current_step': self.current_step,
            'input_params': self.input_params,
            'result_data': self.result_data,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'related_history_id': self.related_history_id,
            'related_history_type': self.related_history_type
        }

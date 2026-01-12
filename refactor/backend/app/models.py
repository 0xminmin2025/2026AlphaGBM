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

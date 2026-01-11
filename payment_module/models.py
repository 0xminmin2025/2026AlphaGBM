"""
支付模块数据库模型
基于点数/额度（Credits）的账本系统
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import enum

# 服务类型枚举
class ServiceType(enum.Enum):
    STOCK_ANALYSIS = "stock_analysis"      # 股票分析
    OPTION_ANALYSIS = "option_analysis"   # 期权分析
    DEEP_REPORT = "deep_report"           # 深度研报

# 额度来源类型
class CreditSource(enum.Enum):
    SUBSCRIPTION = "subscription"  # 订阅每月发放
    TOP_UP = "top_up"              # 单独购买（充值）
    REFERRAL = "referral"          # 邀请赠送
    FREE_DAILY = "free_daily"      # 每日免费额度

# 订阅计划类型
class PlanTier(enum.Enum):
    FREE = "free"      # 免费版
    PLUS = "plus"      # Plus会员
    PRO = "pro"         # Pro会员

# 订阅状态
class SubscriptionStatus(enum.Enum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    UNPAID = "unpaid"
    TRIALING = "trialing"

# 交易状态
class TransactionStatus(enum.Enum):
    SUCCEEDED = "succeeded"
    PENDING = "pending"
    FAILED = "failed"
    REFUNDED = "refunded"


def create_payment_models(db):
    """
    创建支付相关的数据库模型
    需要在app.py中调用，传入db实例
    """
    
    class Subscription(db.Model):
        """订阅记录表"""
        __tablename__ = 'subscriptions'
        
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False, index=True)
        stripe_subscription_id = db.Column(db.String(255), unique=True, index=True)
        plan_tier = db.Column(db.String(50), nullable=False)  # 'plus', 'pro'
        status = db.Column(db.String(50), nullable=False)  # 'active', 'past_due', 'canceled'
        current_period_start = db.Column(db.DateTime, nullable=True)
        current_period_end = db.Column(db.DateTime, nullable=True)  # 本期结束时间
        cancel_at_period_end = db.Column(db.Boolean, default=False)  # 是否在周期结束时取消
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
        
        # 关联
        user = db.relationship('User', backref=db.backref('subscriptions', lazy='dynamic'))
        
        def __repr__(self):
            return f'<Subscription {self.id} - User {self.user_id} - {self.plan_tier}>'
    
    class Transaction(db.Model):
        """支付流水表（幂等性控制核心）"""
        __tablename__ = 'transactions'
        
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False, index=True)
        stripe_payment_intent_id = db.Column(db.String(255), unique=True, index=True)  # 幂等键
        stripe_checkout_session_id = db.Column(db.String(255), unique=True, index=True, nullable=True)
        amount = db.Column(db.Integer, nullable=False)  # 单位：分
        currency = db.Column(db.String(10), default='cny')  # cny, usd
        status = db.Column(db.String(50), nullable=False)  # 'succeeded', 'pending', 'failed'
        description = db.Column(db.String(255), nullable=True)  # 交易描述
        created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
        
        # 关联
        user = db.relationship('User', backref=db.backref('transactions', lazy='dynamic'))
        
        def __repr__(self):
            return f'<Transaction {self.id} - {self.amount} {self.currency} - {self.status}>'
    
    class CreditLedger(db.Model):
        """额度账本（处理过期和消耗）"""
        __tablename__ = 'credit_ledger'
        
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False, index=True)
        service_type = db.Column(db.String(50), default=ServiceType.STOCK_ANALYSIS.value)
        source = db.Column(db.String(50), nullable=False)  # subscription, top_up, referral, free_daily
        
        amount_initial = db.Column(db.Integer, nullable=False)  # 初始获得额度
        amount_remaining = db.Column(db.Integer, nullable=False)  # 剩余额度
        
        expires_at = db.Column(db.DateTime, nullable=True, index=True)  # 过期时间（None表示永久有效）
        created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
        
        # 关联到订阅（如果是订阅发放的额度）
        subscription_id = db.Column(db.Integer, db.ForeignKey('subscriptions.id'), nullable=True)
        
        # 关联
        user = db.relationship('User', backref=db.backref('credit_ledgers', lazy='dynamic'))
        subscription = db.relationship('Subscription', backref=db.backref('credit_ledgers', lazy='dynamic'))
        
        # 索引优化查询（查找有效额度时使用）
        __table_args__ = (
            db.Index('idx_user_service_valid', 'user_id', 'service_type', 'amount_remaining', 'expires_at'),
        )
        
        def is_valid(self):
            """检查额度是否有效（未过期且有剩余）"""
            if self.amount_remaining <= 0:
                return False
            if self.expires_at and self.expires_at < datetime.utcnow():
                return False
            return True
        
        def __repr__(self):
            return f'<CreditLedger {self.id} - User {self.user_id} - {self.amount_remaining}/{self.amount_initial}>'
    
    class UsageLog(db.Model):
        """消耗流水表"""
        __tablename__ = 'usage_logs'
        
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False, index=True)
        credit_ledger_id = db.Column(db.Integer, db.ForeignKey('credit_ledger.id'), nullable=True)
        service_type = db.Column(db.String(50), nullable=False)
        amount_used = db.Column(db.Integer, default=1)  # 消耗的额度数量
        ticker = db.Column(db.String(20), nullable=True)  # 使用的股票代码（如果有）
        created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
        
        # 关联
        user = db.relationship('User', backref=db.backref('usage_logs', lazy='dynamic'))
        credit_ledger = db.relationship('CreditLedger', backref=db.backref('usage_logs', lazy='dynamic'))
        
        def __repr__(self):
            return f'<UsageLog {self.id} - User {self.user_id} - {self.service_type}>'
    
    return {
        'Subscription': Subscription,
        'Transaction': Transaction,
        'CreditLedger': CreditLedger,
        'UsageLog': UsageLog
    }

"""
支付服务核心逻辑
处理Stripe支付、额度发放、额度扣减等业务逻辑
"""
import os
import stripe
from datetime import datetime, timedelta
from functools import wraps
from flask import jsonify, request
from sqlalchemy import and_, or_, func
try:
    from sqlalchemy.orm import with_for_update
except ImportError:
    # SQLAlchemy 2.0+ 使用不同的方式
    with_for_update = None

# 导入模型枚举
from .models import ServiceType, CreditSource, PlanTier, SubscriptionStatus, TransactionStatus

# 配置Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', '')



class PaymentService:
    """支付服务类"""
    
    # 类属性：价格配置
    PRICES = {
        'plus_monthly': os.getenv('STRIPE_PRICE_PLUS_MONTHLY', ''),
        'plus_yearly': os.getenv('STRIPE_PRICE_PLUS_YEARLY', ''),
        'pro_monthly': os.getenv('STRIPE_PRICE_PRO_MONTHLY', ''),
        'pro_yearly': os.getenv('STRIPE_PRICE_PRO_YEARLY', ''),
        'topup_100': os.getenv('STRIPE_PRICE_TOPUP_100', ''),  # 仅支持100次，3个月有效
    }
    
    # 类属性：订阅计划配置
    PLAN_CONFIG = {
        'plus': {
            'monthly_credits': 1000,
            'yearly_credits': 12000,
        },
        'pro': {
            'monthly_credits': 5000,
            'yearly_credits': 60000,
        }
    }
    
    # 类属性：每日免费额度配置
    DAILY_FREE_QUOTA = {
        ServiceType.STOCK_ANALYSIS.value: 2,
        ServiceType.OPTION_ANALYSIS.value: 1,
        ServiceType.DEEP_REPORT.value: 0,
    }
    
    def __init__(self, db, User, Subscription, Transaction, CreditLedger, UsageLog, DailyQueryCount):
        """
        初始化支付服务
        
        Args:
            db: SQLAlchemy数据库实例
            User: User模型类
            Subscription: Subscription模型类
            Transaction: Transaction模型类
            CreditLedger: CreditLedger模型类
            UsageLog: UsageLog模型类
            DailyQueryCount: DailyQueryCount模型类（用于每日免费额度）
        """
        self.db = db
        self.User = User
        self.Subscription = Subscription
        self.Transaction = Transaction
        self.CreditLedger = CreditLedger
        self.UsageLog = UsageLog
        self.DailyQueryCount = DailyQueryCount
    
    def create_checkout_session(self, user_id, price_key, success_url, cancel_url, email=None):
        """
        创建Stripe Checkout Session
        
        Args:
            user_id: 用户ID
            price_key: 价格键（如'plus_monthly', 'topup_100'）
            success_url: 支付成功后的跳转URL
            cancel_url: 取消支付后的跳转URL
        
        Returns:
            (checkout_session对象, None) 或 (None, 错误信息)
        """
        if not stripe.api_key:
            return None, "Stripe未配置，请设置STRIPE_SECRET_KEY环境变量"
        
        user = self.User.query.get(user_id)
        if not user:
            # Lazy creation if email is provided (Supabase Sync)
            if email:
                try:
                    user = self.User(
                        id=user_id,
                        email=email,
                        username=email.split('@')[0],
                        last_login=datetime.now()
                    )
                    self.db.session.add(user)
                    self.db.session.commit()
                except Exception as e:
                    self.db.session.rollback()
                    return None, f"自动创建用户失败: {str(e)}"
            else:
                return None, "用户不存在且未提供邮箱"
        
        # 获取或创建Stripe Customer
        stripe_customer_id = getattr(user, 'stripe_customer_id', None)
        if not stripe_customer_id:
            try:
                customer = stripe.Customer.create(
                    email=user.email,
                    metadata={'user_id': user.id}
                )
                user.stripe_customer_id = customer.id
                self.db.session.commit()
            except Exception as e:
                return None, f"创建Stripe客户失败: {str(e)}"
        
        # 确定支付模式
        mode = 'payment' if 'topup' in price_key else 'subscription'
        
        if price_key not in self.PRICES or not self.PRICES[price_key]:
            return None, f"价格配置不存在: {price_key}"
        
        try:
            checkout_session = stripe.checkout.Session.create(
                customer=stripe_customer_id,
                payment_method_types=['card'],  # 支持支付宝/微信
                line_items=[{
                    'price': self.PRICES[price_key],
                    'quantity': 1,
                }],
                mode=mode,
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    'user_id': str(user.id),
                    'price_key': price_key,
                    'type': mode
                },
                # 支持中文
                locale='zh',
            )
            return checkout_session, None
        except Exception as e:
            return None, f"创建支付会话失败: {str(e)}"
    
    def handle_checkout_completed(self, session):
        """
        处理支付完成（Webhook回调）
        
        Args:
            session: Stripe Checkout Session对象
        
        Returns:
            (success: bool, message: str)
        """
        user_id = int(session['metadata']['user_id'])
        price_key = session['metadata']['price_key']
        payment_intent_id = session.get('payment_intent')
        subscription_id = session.get('subscription')
        
        # 幂等性检查：检查该支付是否已处理
        if payment_intent_id:
            existing = self.Transaction.query.filter_by(
                stripe_payment_intent_id=payment_intent_id
            ).first()
            if existing:
                return True, "支付已处理（幂等性检查）"
        
        try:
            # 1. 记录交易流水
            transaction = self.Transaction(
                user_id=user_id,
                stripe_payment_intent_id=payment_intent_id,
                stripe_checkout_session_id=session['id'],
                amount=session['amount_total'],
                currency=session['currency'],
                status=TransactionStatus.SUCCEEDED.value,
                description=f"购买: {price_key}"
            )
            self.db.session.add(transaction)
            
            # 2. 发放额度
            if 'topup' in price_key:
                # 一次性充值（仅支持100次，3个月有效）
                amount = 100
                self.add_credits(
                    user_id=user_id,
                    amount=amount,
                    source=CreditSource.TOP_UP.value,
                    service_type=ServiceType.STOCK_ANALYSIS.value,
                    days_valid=90  # 3个月有效
                )
            else:
                # 订阅逻辑
                self.handle_new_subscription(user_id, subscription_id, price_key)
            
            self.db.session.commit()
            return True, "处理成功"
            
        except Exception as e:
            self.db.session.rollback()
            return False, f"处理失败: {str(e)}"
    
    def handle_new_subscription(self, user_id, stripe_subscription_id, price_key):
        """
        处理新订阅
        
        Args:
            user_id: 用户ID
            stripe_subscription_id: Stripe订阅ID
            price_key: 价格键（如'plus_monthly'）
        """
        # 解析计划类型和周期
        plan_tier = 'plus' if 'plus' in price_key else 'pro'
        is_yearly = 'yearly' in price_key
        
        # 获取额度配置
        credits = self.PLAN_CONFIG[plan_tier]['yearly_credits' if is_yearly else 'monthly_credits']
        
        # 计算有效期（订阅周期）
        days_valid = 365 if is_yearly else 30
        
        # 获取Stripe订阅信息
        try:
            stripe_sub = stripe.Subscription.retrieve(stripe_subscription_id)
            current_period_end = datetime.fromtimestamp(stripe_sub.current_period_end)
        except:
            current_period_end = datetime.utcnow() + timedelta(days=days_valid)
        
        # 记录/更新订阅表
        subscription = self.Subscription.query.filter_by(
            stripe_subscription_id=stripe_subscription_id
        ).first()
        
        if not subscription:
            subscription = self.Subscription(
                user_id=user_id,
                stripe_subscription_id=stripe_subscription_id,
                plan_tier=plan_tier,
                status=SubscriptionStatus.ACTIVE.value,
                current_period_end=current_period_end
            )
            self.db.session.add(subscription)
        else:
            subscription.status = SubscriptionStatus.ACTIVE.value
            subscription.current_period_end = current_period_end
        
        # 发放本月额度
        self.add_credits(
            user_id=user_id,
            amount=credits,
            source=CreditSource.SUBSCRIPTION.value,
            service_type=ServiceType.STOCK_ANALYSIS.value,
            days_valid=days_valid,
            subscription_id=subscription.id
        )
        
        # 邀请奖励逻辑
        user = self.User.query.get(user_id)
        if hasattr(user, 'referrer_id') and user.referrer_id:
            # 给邀请人发100个查询，有效期90天
            self.add_credits(
                user_id=user.referrer_id,
                amount=100,
                source=CreditSource.REFERRAL.value,
                service_type=ServiceType.STOCK_ANALYSIS.value,
                days_valid=90
            )
    
    def handle_subscription_renewal(self, invoice):
        """
        处理订阅续费（Webhook回调）
        
        Args:
            invoice: Stripe Invoice对象
        """
        subscription_id = invoice['subscription']
        
        subscription = self.Subscription.query.filter_by(
            stripe_subscription_id=subscription_id
        ).first()
        
        if not subscription:
            return False, "订阅不存在"
        
        # 更新订阅信息
        try:
            stripe_sub = stripe.Subscription.retrieve(subscription_id)
            subscription.current_period_end = datetime.fromtimestamp(stripe_sub.current_period_end)
            subscription.status = stripe_sub.status
        except:
            pass
        
        # 发放新周期额度
        plan_tier = subscription.plan_tier
        is_yearly = subscription.current_period_end and \
                   (subscription.current_period_end - subscription.current_period_start).days > 60
        
        credits = PLAN_CONFIG[plan_tier]['yearly_credits' if is_yearly else 'monthly_credits']
        days_valid = 365 if is_yearly else 30
        
        self.add_credits(
            user_id=subscription.user_id,
            amount=credits,
            source=CreditSource.SUBSCRIPTION.value,
            service_type=ServiceType.STOCK_ANALYSIS.value,
            days_valid=days_valid,
            subscription_id=subscription.id
        )
        
        self.db.session.commit()
        return True, "续费处理成功"
    
    def add_credits(self, user_id, amount, source, service_type, days_valid=None, subscription_id=None):
        """
        通用发放额度函数
        
        Args:
            user_id: 用户ID
            amount: 额度数量
            source: 来源（subscription, top_up, referral, free_daily）
            service_type: 服务类型
            days_valid: 有效期天数（None表示永久有效）
            subscription_id: 关联的订阅ID（如果有）
        """
        expiry = None
        if days_valid:
            expiry = datetime.utcnow() + timedelta(days=days_valid)
        
        ledger = self.CreditLedger(
            user_id=user_id,
            service_type=service_type,
            source=source,
            amount_initial=amount,
            amount_remaining=amount,
            expires_at=expiry,
            subscription_id=subscription_id
        )
        self.db.session.add(ledger)
        return ledger
    
    def check_and_deduct_credits(self, user_id, service_type=ServiceType.STOCK_ANALYSIS.value, amount=1):
        """
        检查并扣减额度（FIFO - 先进先出）
        
        Args:
            user_id: 用户ID
            service_type: 服务类型
            amount: 消耗数量（默认1）
        
        Returns:
            (success: bool, message: str, remaining_credits: int)
        """
        # 1. 检查每日免费额度
        if self.check_daily_free_quota(user_id, service_type):
            # 使用免费额度，记录日志但不创建CreditLedger
            usage_log = self.UsageLog(
                user_id=user_id,
                service_type=service_type,
                amount_used=amount
            )
            self.db.session.add(usage_log)
            self.db.session.commit()
            return True, "使用每日免费额度", self.get_total_credits(user_id, service_type)
        
        # 2. 查找有效额度（FIFO：先过期的先用）
        query = self.CreditLedger.query.filter(
            and_(
                self.CreditLedger.user_id == user_id,
                self.CreditLedger.service_type == service_type,
                self.CreditLedger.amount_remaining > 0,
                or_(
                    self.CreditLedger.expires_at == None,
                    self.CreditLedger.expires_at > datetime.utcnow()
                )
            )
        ).order_by(
            self.CreditLedger.expires_at.asc().nullslast()  # 先过期的先用，永久有效的最后
        )
        
        # 行锁防止并发（with_for_update是Query对象的方法，不是导入的）
        try:
            valid_credits = query.with_for_update().first()
        except (AttributeError, TypeError):
            # 如果with_for_update不可用，直接查询（生产环境建议使用数据库级别的锁）
            valid_credits = query.first()
        
        if not valid_credits:
            total = self.get_total_credits(user_id, service_type)
            return False, "额度不足，请充值或明天再来", total
        
        # 3. 扣减额度（原子操作）
        try:
            valid_credits.amount_remaining -= amount
            if valid_credits.amount_remaining < 0:
                valid_credits.amount_remaining = 0
            
            # 记录使用日志
            usage_log = self.UsageLog(
                user_id=user_id,
                credit_ledger_id=valid_credits.id,
                service_type=service_type,
                amount_used=amount
            )
            self.db.session.add(usage_log)
            
            self.db.session.commit()
            
            remaining = self.get_total_credits(user_id, service_type)
            return True, "扣减成功", remaining
            
        except Exception as e:
            self.db.session.rollback()
            return False, f"扣减失败: {str(e)}", 0
    
    def check_daily_free_quota(self, user_id, service_type):
        """
        检查每日免费额度
        
        Args:
            user_id: 用户ID
            service_type: 服务类型
        
        Returns:
            bool: 是否可以使用免费额度
        """
        free_quota = self.DAILY_FREE_QUOTA.get(service_type, 0)
        if free_quota == 0:
            return False
        
        # 使用DailyQueryCount表记录每日使用情况
        today = datetime.now().date()
        daily_count = self.DailyQueryCount.query.filter_by(
            user_id=user_id,
            date=today
        ).first()
        
        if not daily_count:
            return True  # 今天还没使用过，可以使用免费额度
        
        # 检查是否超过免费额度
        # 注意：这里需要根据service_type分别统计，但DailyQueryCount是通用的
        # 如果不同服务类型需要分开统计，需要扩展DailyQueryCount表或创建新表
        return daily_count.query_count < free_quota
    
    def get_total_credits(self, user_id, service_type=ServiceType.STOCK_ANALYSIS.value):
        """
        获取用户总剩余额度
        
        Args:
            user_id: 用户ID
            service_type: 服务类型
        
        Returns:
            int: 总剩余额度
        """
        total = self.db.session.query(
            func.sum(self.CreditLedger.amount_remaining)
        ).filter(
            and_(
                self.CreditLedger.user_id == user_id,
                self.CreditLedger.service_type == service_type,
                self.CreditLedger.amount_remaining > 0,
                or_(
                    self.CreditLedger.expires_at == None,
                    self.CreditLedger.expires_at > datetime.utcnow()
                )
            )
        ).scalar()
        
        return int(total) if total else 0
    
    def get_user_subscription_info(self, user_id):
        """
        获取用户订阅信息
        
        Args:
            user_id: 用户ID
        
        Returns:
            dict: 订阅信息
        """
        subscription = self.Subscription.query.filter_by(
            user_id=user_id,
            status=SubscriptionStatus.ACTIVE.value
        ).first()
        
        if not subscription:
            return {
                'has_subscription': False,
                'plan_tier': 'free',
                'status': 'free'
            }
        
        return {
            'has_subscription': True,
            'plan_tier': subscription.plan_tier,
            'status': subscription.status,
            'current_period_end': subscription.current_period_end.isoformat() if subscription.current_period_end else None
        }

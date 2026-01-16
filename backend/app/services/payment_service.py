"""
支付服务核心逻辑
处理Stripe支付、额度发放、额度扣减等业务逻辑
"""
import os
import stripe
from datetime import datetime, timedelta
from sqlalchemy import and_, or_, func
from ..models import db, User, Subscription, Transaction, CreditLedger, UsageLog, DailyQueryCount, ServiceType, CreditSource, PlanTier, SubscriptionStatus, TransactionStatus

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
        'topup_100': os.getenv('STRIPE_PRICE_TOPUP_100', ''),
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
    
    # Remove __init__ dependency injection, use imported models directly
    
    @classmethod
    def create_checkout_session(cls, user_id, price_key, success_url, cancel_url, email=None):
        """创建Stripe Checkout Session"""
        if not stripe.api_key:
            return None, "Stripe未配置，请设置STRIPE_SECRET_KEY环境变量"
        
        user = User.query.get(user_id)
        if not user:
            # Lazy creation if email is provided (Supabase Sync)
            if email:
                try:
                    user = User(
                        id=user_id,
                        email=email,
                        username=email.split('@')[0],
                        last_login=datetime.now()
                    )
                    db.session.add(user)
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
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
                db.session.commit()
            except Exception as e:
                return None, f"创建Stripe客户失败: {str(e)}"
        
        # 确定支付模式
        mode = 'payment' if 'topup' in price_key else 'subscription'
        
        if price_key not in cls.PRICES or not cls.PRICES[price_key]:
            return None, f"价格配置不存在: {price_key}"
        
        try:
            checkout_session = stripe.checkout.Session.create(
                customer=stripe_customer_id,
                payment_method_types=['card'],
                line_items=[{
                    'price': cls.PRICES[price_key],
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
                locale='zh',
            )
            return checkout_session, None
        except Exception as e:
            return None, f"创建支付会话失败: {str(e)}"
    
    @classmethod
    def handle_checkout_completed(cls, session):
        """处理支付完成（Webhook回调）"""
        user_id = session['metadata']['user_id'] # uuid is string
        price_key = session['metadata']['price_key']
        payment_intent_id = session.get('payment_intent')
        subscription_id = session.get('subscription')
        
        # 幂等性检查
        if payment_intent_id:
            existing = Transaction.query.filter_by(
                stripe_payment_intent_id=payment_intent_id
            ).first()
            if existing:
                return True, "支付已处理（幂等性检查）"
        
        try:
            # 1. 记录交易流水
            transaction = Transaction(
                user_id=user_id,
                stripe_payment_intent_id=payment_intent_id,
                stripe_checkout_session_id=session['id'],
                amount=session['amount_total'],
                currency=session['currency'],
                status=TransactionStatus.SUCCEEDED.value,
                description=f"{price_key}"
            )
            db.session.add(transaction)
            
            # 2. 发放额度
            if 'topup' in price_key:
                amount = 100
                cls.add_credits(
                    user_id=user_id,
                    amount=amount,
                    source=CreditSource.TOP_UP.value,
                    service_type=ServiceType.STOCK_ANALYSIS.value,
                    days_valid=90
                )
            else:
                cls.handle_new_subscription(user_id, subscription_id, price_key)
            
            db.session.commit()
            return True, "处理成功"
            
        except Exception as e:
            db.session.rollback()
            return False, f"处理失败: {str(e)}"
    
    @classmethod
    def handle_new_subscription(cls, user_id, stripe_subscription_id, price_key):
        """处理新订阅"""
        plan_tier = 'plus' if 'plus' in price_key else 'pro'
        is_yearly = 'yearly' in price_key
        
        credits = cls.PLAN_CONFIG[plan_tier]['yearly_credits' if is_yearly else 'monthly_credits']
        days_valid = 365 if is_yearly else 30
        
        try:
            stripe_sub = stripe.Subscription.retrieve(stripe_subscription_id)
            current_period_end = datetime.fromtimestamp(stripe_sub.current_period_end)
        except:
            current_period_end = datetime.utcnow() + timedelta(days=days_valid)
        
        subscription = Subscription.query.filter_by(
            stripe_subscription_id=stripe_subscription_id
        ).first()
        
        if not subscription:
            subscription = Subscription(
                user_id=user_id,
                stripe_subscription_id=stripe_subscription_id,
                plan_tier=plan_tier,
                status=SubscriptionStatus.ACTIVE.value,
                current_period_end=current_period_end
            )
            db.session.add(subscription)
        else:
            subscription.status = SubscriptionStatus.ACTIVE.value
            subscription.current_period_end = current_period_end
        
        # Need to commit to get subscription.id if it's new? No, session tracks it.
        # But add_credits uses subscription.id. It might be None if not flushed.
        db.session.flush()

        cls.add_credits(
            user_id=user_id,
            amount=credits,
            source=CreditSource.SUBSCRIPTION.value,
            service_type=ServiceType.STOCK_ANALYSIS.value,
            days_valid=days_valid,
            subscription_id=subscription.id
        )
        
        # 邀请奖励逻辑
        user = User.query.get(user_id)
        if hasattr(user, 'referrer_id') and user.referrer_id:
            cls.add_credits(
                user_id=user.referrer_id,
                amount=100,
                source=CreditSource.REFERRAL.value,
                service_type=ServiceType.STOCK_ANALYSIS.value,
                days_valid=90
            )

    @classmethod
    def handle_subscription_renewal(cls, invoice):
        """处理订阅续费（Webhook回调）"""
        subscription_id = invoice['subscription']
        
        subscription = Subscription.query.filter_by(
            stripe_subscription_id=subscription_id
        ).first()
        
        if not subscription:
            return False, "订阅不存在"
        
        try:
            stripe_sub = stripe.Subscription.retrieve(subscription_id)
            subscription.current_period_end = datetime.fromtimestamp(stripe_sub.current_period_end)
            subscription.status = stripe_sub.status
        except:
            pass
        
        plan_tier = subscription.plan_tier
        is_yearly = subscription.current_period_end and \
                   (subscription.current_period_end - subscription.current_period_start).days > 60
        
        credits = cls.PLAN_CONFIG[plan_tier]['yearly_credits' if is_yearly else 'monthly_credits']
        days_valid = 365 if is_yearly else 30
        
        cls.add_credits(
            user_id=subscription.user_id,
            amount=credits,
            source=CreditSource.SUBSCRIPTION.value,
            service_type=ServiceType.STOCK_ANALYSIS.value,
            days_valid=days_valid,
            subscription_id=subscription.id
        )
        
        db.session.commit()
        return True, "续费处理成功"
    
    @classmethod
    def add_credits(cls, user_id, amount, source, service_type, days_valid=None, subscription_id=None):
        """通用发放额度函数"""
        expiry = None
        if days_valid:
            expiry = datetime.utcnow() + timedelta(days=days_valid)
        
        ledger = CreditLedger(
            user_id=user_id,
            service_type=service_type,
            source=source,
            amount_initial=amount,
            amount_remaining=amount,
            expires_at=expiry,
            subscription_id=subscription_id
        )
        db.session.add(ledger)
        return ledger
    
    @classmethod
    def check_and_deduct_credits(cls, user_id, service_type=ServiceType.STOCK_ANALYSIS.value, amount=1, ticker=None):
        """检查并扣减额度（FIFO）

        Note: Subscription credits are stored as 'stock_analysis' type but can be used for all services.
        We first check daily free quota for the specific service, then check stock_analysis credits (universal).
        """
        # 1. 检查每日免费额度 (specific to service type)
        if cls.check_daily_free_quota(user_id, service_type):
            usage_log = UsageLog(
                user_id=user_id,
                service_type=service_type,
                amount_used=amount,
                ticker=ticker
            )
            db.session.add(usage_log)
            db.session.commit()

            # 添加调试日志
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Created usage log - User: {user_id}, Service: {service_type}, Ticker: {ticker}, Amount: {amount}, ID: {usage_log.id}")

            return True, "使用每日免费额度", cls.get_total_credits(user_id, ServiceType.STOCK_ANALYSIS.value)
        
        # 2. 查找有效额度 - 使用stock_analysis类型 (universal credits from subscription)
        # Subscription credits are added as stock_analysis but can be used for any service
        credit_service_type = ServiceType.STOCK_ANALYSIS.value
        
        query = CreditLedger.query.filter(
            and_(
                CreditLedger.user_id == user_id,
                CreditLedger.service_type == credit_service_type,
                CreditLedger.amount_remaining > 0,
                or_(
                    CreditLedger.expires_at == None,
                    CreditLedger.expires_at > datetime.utcnow()
                )
            )
        ).order_by(
            CreditLedger.expires_at.asc().nullslast()
        )
        
        try:
             # SQLALchemy 2.0+ 
             valid_credits = query.with_for_update().first()
        except:
             valid_credits = query.first()
        
        if not valid_credits:
            total = cls.get_total_credits(user_id, credit_service_type)
            return False, "额度不足，请充值或明天再来", total
        
        # 3. 扣减
        try:
            valid_credits.amount_remaining -= amount
            if valid_credits.amount_remaining < 0:
                valid_credits.amount_remaining = 0

            usage_log = UsageLog(
                user_id=user_id,
                credit_ledger_id=valid_credits.id,
                service_type=service_type,  # Log the actual service used
                amount_used=amount,
                ticker=ticker
            )
            db.session.add(usage_log)
            db.session.commit()

            # 添加调试日志
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Created usage log (paid credits) - User: {user_id}, Service: {service_type}, Ticker: {ticker}, Amount: {amount}, ID: {usage_log.id}")

            remaining = cls.get_total_credits(user_id, credit_service_type)
            return True, "扣减成功", remaining
            
        except Exception as e:
            db.session.rollback()
            return False, f"扣减失败: {str(e)}", 0
            
    @classmethod
    def check_daily_free_quota(cls, user_id, service_type):
        """检查每日免费额度"""
        free_quota = cls.DAILY_FREE_QUOTA.get(service_type, 0)
        if free_quota == 0:
            return False
        
        today = datetime.now().date()
        daily_count = DailyQueryCount.query.filter_by(
            user_id=user_id,
            date=today
        ).first()
        
        if not daily_count:
            return True
        
        return daily_count.query_count < free_quota

    @classmethod
    def get_total_credits(cls, user_id, service_type=ServiceType.STOCK_ANALYSIS.value):
        """获取总额度"""
        total = db.session.query(
            func.sum(CreditLedger.amount_remaining)
        ).filter(
            and_(
                CreditLedger.user_id == user_id,
                CreditLedger.service_type == service_type,
                CreditLedger.amount_remaining > 0,
                or_(
                    CreditLedger.expires_at == None,
                    CreditLedger.expires_at > datetime.utcnow()
                )
            )
        ).scalar()
        
        return int(total) if total else 0
    
    @classmethod
    def get_user_subscription_info(cls, user_id):
        """获取用户订阅信息"""
        subscription = Subscription.query.filter_by(
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

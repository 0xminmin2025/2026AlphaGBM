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
    
    # 类属性：每日免费额度配置（统一为10次）
    DAILY_FREE_QUOTA = {
        ServiceType.STOCK_ANALYSIS.value: 10,
        ServiceType.OPTION_ANALYSIS.value: 10,
        ServiceType.DEEP_REPORT.value: 0,
    }
    
    # Remove __init__ dependency injection, use imported models directly
    
    @classmethod
    def create_checkout_session(cls, user_id, price_key, success_url, cancel_url, email=None):
        """创建Stripe Checkout Session"""
        if not stripe.api_key:
            return None, "Stripe未配置，请设置STRIPE_SECRET_KEY环境变量"

        # 检查是否为订阅类型（非 topup）
        is_subscription = 'topup' not in price_key

        if is_subscription:
            # 检查用户是否已有活跃订阅
            existing_subscription = Subscription.query.filter_by(
                user_id=user_id,
                status=SubscriptionStatus.ACTIVE.value
            ).first()

            if existing_subscription:
                return None, "您已有活跃订阅，请使用升级功能变更订阅计划，或先取消当前订阅"

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
        """
        处理 checkout.session.completed 事件

        订阅类型：
        - 不在这里创建 Transaction（会在 invoice.payment_succeeded 中创建）
        - 只创建 Subscription 记录

        Top-up 类型：
        - 创建 Transaction 和发放额度（因为不会触发 invoice.payment_succeeded）
        """
        import logging
        logger = logging.getLogger(__name__)

        user_id = session['metadata']['user_id']
        price_key = session['metadata']['price_key']
        payment_intent_id = session.get('payment_intent')
        subscription_id = session.get('subscription')

        logger.info(f"[CheckoutCompleted] Processing session {session['id']}, price_key={price_key}, subscription_id={subscription_id}")

        try:
            # 订阅类型：只创建订阅记录，Transaction 和额度在 invoice.payment_succeeded 中处理
            if 'topup' not in price_key and subscription_id:
                plan_tier = 'plus' if 'plus' in price_key else 'pro'
                is_yearly = 'yearly' in price_key
                days_valid = 365 if is_yearly else 30

                try:
                    stripe_sub = stripe.Subscription.retrieve(subscription_id)
                    current_period_end = datetime.fromtimestamp(stripe_sub.current_period_end)
                    current_period_start = datetime.fromtimestamp(stripe_sub.current_period_start)
                except:
                    current_period_end = datetime.utcnow() + timedelta(days=days_valid)
                    current_period_start = datetime.utcnow()

                subscription = Subscription.query.filter_by(
                    stripe_subscription_id=subscription_id
                ).first()

                if not subscription:
                    subscription = Subscription(
                        user_id=user_id,
                        stripe_subscription_id=subscription_id,
                        plan_tier=plan_tier,
                        status=SubscriptionStatus.ACTIVE.value,
                        current_period_start=current_period_start,
                        current_period_end=current_period_end
                    )
                    db.session.add(subscription)
                    logger.info(f"[CheckoutCompleted] Created subscription record for {subscription_id}")

                db.session.commit()
                return True, "订阅记录创建成功，额度将在付款确认后发放"

            # Top-up 类型：创建 Transaction 并发放额度
            if 'topup' in price_key:
                # 幂等性检查
                if payment_intent_id:
                    existing = Transaction.query.filter_by(
                        stripe_payment_intent_id=payment_intent_id
                    ).first()
                    if existing:
                        logger.info(f"[CheckoutCompleted] Top-up already processed (idempotency)")
                        return True, "充值已处理（幂等性检查）"

                # 创建交易记录
                transaction = Transaction(
                    user_id=user_id,
                    stripe_payment_intent_id=payment_intent_id,
                    stripe_checkout_session_id=session['id'],
                    amount=session['amount_total'],
                    currency=session['currency'],
                    status=TransactionStatus.SUCCEEDED.value,
                    description=f"充值 - {price_key}"
                )
                db.session.add(transaction)

                # 发放额度
                cls.add_credits(
                    user_id=user_id,
                    amount=100,
                    source=CreditSource.TOP_UP.value,
                    service_type=ServiceType.STOCK_ANALYSIS.value,
                    days_valid=90
                )

                db.session.commit()
                logger.info(f"[CheckoutCompleted] Top-up processed, added 100 credits for user {user_id}")
                return True, "充值处理成功"

            return True, "处理成功"

        except Exception as e:
            logger.error(f"[CheckoutCompleted] Error: {str(e)}", exc_info=True)
            db.session.rollback()
            return False, f"处理失败: {str(e)}"
    
    @classmethod
    def handle_invoice_payment_succeeded(cls, invoice):
        """
        处理 invoice.payment_succeeded 事件
        这是发放订阅额度的唯一入口！
        包括首次订阅和续费都在这里处理
        """
        import logging
        logger = logging.getLogger(__name__)

        subscription_id = invoice.get('subscription')
        invoice_id = invoice.get('id')
        billing_reason = invoice.get('billing_reason')  # 'subscription_create', 'subscription_cycle', 'subscription_update'

        logger.info(f"[InvoicePayment] Processing invoice {invoice_id}, subscription={subscription_id}, billing_reason={billing_reason}")

        if not subscription_id:
            # 非订阅类型的 invoice（如一次性付款），跳过
            logger.info(f"[InvoicePayment] Skipping non-subscription invoice {invoice_id}")
            return True, "非订阅类型发票，跳过"

        # 升级产生的发票 (subscription_update) 不需要在这里处理
        # 因为 upgrade_subscription 方法已经处理了额度发放和交易记录
        if billing_reason == 'subscription_update':
            logger.info(f"[InvoicePayment] Skipping subscription_update invoice {invoice_id} - handled by upgrade_subscription")
            return True, "升级发票，由升级方法处理"

        # 幂等性检查：按 invoice_id 检查是否已经处理过
        # 每个发票只能处理一次，防止重复发放额度
        existing_transaction = Transaction.query.filter_by(
            stripe_invoice_id=invoice_id
        ).first()

        if existing_transaction:
            logger.info(f"[InvoicePayment] Idempotency check: invoice {invoice_id} already processed")
            return True, "已处理过此发票（幂等性检查）"

        subscription = Subscription.query.filter_by(
            stripe_subscription_id=subscription_id
        ).first()
        logger.info(f"[InvoicePayment] Found subscription record: {subscription is not None}")

        if not subscription:
            # 订阅记录可能还没创建（webhook 顺序问题），尝试从 invoice 获取信息
            logger.info(f"[InvoicePayment] Subscription record not found, creating from Stripe data...")
            try:
                stripe_sub = stripe.Subscription.retrieve(subscription_id)
                logger.info(f"[InvoicePayment] Retrieved Stripe subscription: {stripe_sub.get('id')}")

                # 从 metadata 或 price 推断 plan_tier
                price_id = stripe_sub['items']['data'][0]['price']['id']
                logger.info(f"[InvoicePayment] Price ID: {price_id}")

                # 根据 price_id 判断套餐
                plan_tier = 'plus'  # 默认为 plus
                is_yearly = False
                for key, pid in cls.PRICES.items():
                    if pid == price_id:
                        plan_tier = 'plus' if 'plus' in key else 'pro'
                        is_yearly = 'yearly' in key
                        logger.info(f"[InvoicePayment] Matched price key: {key}, plan_tier={plan_tier}, is_yearly={is_yearly}")
                        break

                # 尝试从 customer 获取 user_id
                customer_id = stripe_sub.get('customer')
                logger.info(f"[InvoicePayment] Customer ID: {customer_id}")
                user = User.query.filter_by(stripe_customer_id=customer_id).first()
                if not user:
                    logger.error(f"[InvoicePayment] User not found for customer_id={customer_id}")
                    return False, f"无法找到用户: customer_id={customer_id}"

                logger.info(f"[InvoicePayment] Found user: {user.id}")

                # 创建订阅记录 - 使用字典访问方式
                period_start = stripe_sub.get('current_period_start')
                period_end = stripe_sub.get('current_period_end')
                logger.info(f"[InvoicePayment] Period: {period_start} - {period_end}")

                subscription = Subscription(
                    user_id=user.id,
                    stripe_subscription_id=subscription_id,
                    plan_tier=plan_tier,
                    status=SubscriptionStatus.ACTIVE.value,
                    current_period_start=datetime.fromtimestamp(period_start) if period_start else datetime.utcnow(),
                    current_period_end=datetime.fromtimestamp(period_end) if period_end else datetime.utcnow() + timedelta(days=30)
                )
                db.session.add(subscription)
                db.session.flush()
                logger.info(f"[InvoicePayment] Created subscription record with id={subscription.id}")

            except Exception as e:
                logger.error(f"[InvoicePayment] Failed to create subscription: {str(e)}", exc_info=True)
                return False, f"订阅不存在且无法创建: {str(e)}"

        try:
            # 更新订阅周期信息
            stripe_sub = stripe.Subscription.retrieve(subscription_id)
            # 使用字典访问方式
            period_start = stripe_sub.get('current_period_start')
            period_end = stripe_sub.get('current_period_end')
            sub_status = stripe_sub.get('status')

            logger.info(f"[InvoicePayment] Stripe subscription status: {sub_status}, period: {period_start} - {period_end}")

            subscription.current_period_start = datetime.fromtimestamp(period_start) if period_start else subscription.current_period_start
            subscription.current_period_end = datetime.fromtimestamp(period_end) if period_end else subscription.current_period_end
            subscription.status = sub_status if sub_status else subscription.status

            # 判断是年付还是月付
            period_days = (subscription.current_period_end - subscription.current_period_start).days
            is_yearly = period_days > 60
            logger.info(f"[InvoicePayment] Period days: {period_days}, is_yearly: {is_yearly}")

            plan_tier = subscription.plan_tier
            if plan_tier not in cls.PLAN_CONFIG:
                logger.error(f"[InvoicePayment] Unknown plan_tier: {plan_tier}, defaulting to 'plus'")
                plan_tier = 'plus'

            credits = cls.PLAN_CONFIG[plan_tier]['yearly_credits' if is_yearly else 'monthly_credits']
            days_valid = 365 if is_yearly else 30
            logger.info(f"[InvoicePayment] Will add {credits} credits for plan_tier={plan_tier}, days_valid={days_valid}")

            # 创建交易记录（用于幂等性检查）
            # 这必须在发放额度之前创建，防止并发重复处理
            invoice_amount = invoice.get('amount_paid', 0)
            invoice_currency = invoice.get('currency', 'usd')
            transaction = Transaction(
                user_id=subscription.user_id,
                stripe_invoice_id=invoice_id,
                amount=invoice_amount,
                currency=invoice_currency,
                status=TransactionStatus.SUCCEEDED.value,
                description=f"订阅{'续费' if billing_reason == 'subscription_cycle' else '首次'} - {plan_tier}"
            )
            db.session.add(transaction)
            db.session.flush()  # 先提交 transaction，确保幂等性
            logger.info(f"[InvoicePayment] Transaction record created for invoice {invoice_id}")

            # 发放额度
            cls.add_credits(
                user_id=subscription.user_id,
                amount=credits,
                source=CreditSource.SUBSCRIPTION.value,
                service_type=ServiceType.STOCK_ANALYSIS.value,
                days_valid=days_valid,
                subscription_id=subscription.id
            )
            logger.info(f"[InvoicePayment] Credits added successfully for user {subscription.user_id}")

            # 首次订阅时检查邀请奖励
            if billing_reason == 'subscription_create':
                user = User.query.get(subscription.user_id)
                if hasattr(user, 'referrer_id') and user.referrer_id:
                    cls.add_credits(
                        user_id=user.referrer_id,
                        amount=100,
                        source=CreditSource.REFERRAL.value,
                        service_type=ServiceType.STOCK_ANALYSIS.value,
                        days_valid=90
                    )
                    logger.info(f"[InvoicePayment] Referral bonus added for user {user.referrer_id}")

            db.session.commit()
            logger.info(f"[InvoicePayment] Successfully processed invoice {invoice_id}, added {credits} credits")
            return True, f"{'首次订阅' if billing_reason == 'subscription_create' else '续费'}处理成功，发放 {credits} 额度"

        except Exception as e:
            logger.error(f"[InvoicePayment] Error adding credits: {str(e)}", exc_info=True)
            db.session.rollback()
            return False, f"处理失败: {str(e)}"

    # 保留旧方法名作为别名，兼容旧代码
    @classmethod
    def handle_subscription_renewal(cls, invoice):
        """旧方法名，重定向到新方法"""
        return cls.handle_invoice_payment_succeeded(invoice)
    
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

        Returns:
            tuple: (success, message, remaining_credits, extra_info)
            extra_info: dict with 'is_free', 'free_remaining', 'free_quota' etc.
        """
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[Deduct] START - User: {user_id[:8]}..., Service: {service_type}, Amount: {amount}, Ticker: {ticker}")

        # 获取免费额度信息
        free_info = cls.get_daily_free_quota_info(user_id, service_type)
        logger.info(f"[Deduct] Free info: quota={free_info['quota']}, used={free_info['used']}, remaining={free_info['remaining']}")

        # 1. 检查每日免费额度 (所有服务共享)
        if cls.check_daily_free_quota(user_id, service_type, amount):
            # 更新每日使用计数（使用行锁防止并发问题）
            today = datetime.now().date()

            # 使用 with_for_update() 获取行锁，防止并发更新问题
            try:
                daily_count = DailyQueryCount.query.filter_by(
                    user_id=user_id,
                    date=today
                ).with_for_update().first()
            except Exception:
                # 如果不支持行锁，fallback 到普通查询
                daily_count = DailyQueryCount.query.filter_by(
                    user_id=user_id,
                    date=today
                ).first()

            if not daily_count:
                # 计算第二天零点作为重置时间
                tomorrow = datetime.combine(today + timedelta(days=1), datetime.min.time())
                daily_count = DailyQueryCount(
                    user_id=user_id,
                    date=today,
                    query_count=amount,
                    reset_time=tomorrow
                )
                db.session.add(daily_count)
                logger.info(f"[Deduct] Created new DailyQueryCount with query_count={amount}")
            else:
                old_count = daily_count.query_count
                daily_count.query_count += amount
                logger.info(f"[Deduct] Updated DailyQueryCount: {old_count} -> {daily_count.query_count}")

            usage_log = UsageLog(
                user_id=user_id,
                service_type=service_type,
                amount_used=amount,
                ticker=ticker
            )
            db.session.add(usage_log)
            db.session.commit()

            # 重新查询获取最新值
            daily_count = DailyQueryCount.query.filter_by(
                user_id=user_id,
                date=today
            ).first()
            new_free_remaining = free_info['quota'] - daily_count.query_count

            logger.info(f"[Deduct] SUCCESS (free) - User: {user_id[:8]}..., Amount: {amount}, DailyCount now: {daily_count.query_count}, Free remaining: {new_free_remaining}")

            return True, "使用每日免费额度", cls.get_total_credits(user_id, ServiceType.STOCK_ANALYSIS.value), {
                'is_free': True,
                'free_used': amount,
                'free_remaining': new_free_remaining,
                'free_quota': free_info['quota']
            }

        # 2. 查找有效额度 - 使用stock_analysis类型 (universal credits from subscription)
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
            valid_credits = query.with_for_update().first()
        except:
            valid_credits = query.first()

        if not valid_credits or valid_credits.amount_remaining < amount:
            total = cls.get_total_credits(user_id, credit_service_type)
            return False, "额度不足，请充值或升级套餐", total, {
                'is_free': False,
                'free_remaining': free_info['remaining'],
                'free_quota': free_info['quota']
            }

        # 3. 扣减付费额度
        try:
            valid_credits.amount_remaining -= amount
            if valid_credits.amount_remaining < 0:
                valid_credits.amount_remaining = 0

            usage_log = UsageLog(
                user_id=user_id,
                credit_ledger_id=valid_credits.id,
                service_type=service_type,
                amount_used=amount,
                ticker=ticker
            )
            db.session.add(usage_log)
            db.session.commit()

            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Used paid credits - User: {user_id}, Service: {service_type}, Amount: {amount}")

            remaining = cls.get_total_credits(user_id, credit_service_type)
            return True, "扣减成功", remaining, {
                'is_free': False,
                'free_remaining': free_info['remaining'],
                'free_quota': free_info['quota']
            }

        except Exception as e:
            db.session.rollback()
            return False, f"扣减失败: {str(e)}", 0, {'is_free': False}
            
    @classmethod
    def check_daily_free_quota(cls, user_id, service_type, amount=1):
        """
        检查每日免费额度是否足够（所有服务共享10次）
        Args:
            user_id: 用户ID
            service_type: 服务类型
            amount: 需要消耗的次数（期权分析时为symbol数量）
        Returns:
            bool: 是否有足够的免费额度
        """
        # 统一使用10次免费额度，所有服务共享
        free_quota = 10

        today = datetime.now().date()
        daily_count = DailyQueryCount.query.filter_by(
            user_id=user_id,
            date=today
        ).first()

        if not daily_count:
            return amount <= free_quota

        return (daily_count.query_count + amount) <= free_quota

    @classmethod
    def get_daily_free_quota_info(cls, user_id, service_type):
        """
        获取每日免费额度详情（所有服务共享）
        Returns:
            dict: {quota: 总额度, used: 已使用, remaining: 剩余}
        """
        # 统一使用10次免费额度
        free_quota = 10

        today = datetime.now().date()
        daily_count = DailyQueryCount.query.filter_by(
            user_id=user_id,
            date=today
        ).first()

        used = daily_count.query_count if daily_count else 0

        return {
            'quota': free_quota,
            'used': used,
            'remaining': max(0, free_quota - used)
        }

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
                'billing_cycle': None,
                'status': 'free'
            }

        # 获取当前的 price_key 以确定 billing_cycle
        current_price_key = cls.get_current_price_key(subscription)
        billing_cycle = 'yearly' if current_price_key and 'yearly' in current_price_key else 'monthly'

        return {
            'has_subscription': True,
            'plan_tier': subscription.plan_tier,
            'billing_cycle': billing_cycle,
            'status': subscription.status,
            'current_period_end': subscription.current_period_end.isoformat() if subscription.current_period_end else None,
            'cancel_at_period_end': subscription.cancel_at_period_end if hasattr(subscription, 'cancel_at_period_end') else False
        }

    # ============ 升级订阅相关方法 ============

    # 价格等级排序（用于判断升级/降级）
    PRICE_TIER_ORDER = {
        'plus_monthly': 1,
        'plus_yearly': 2,
        'pro_monthly': 3,
        'pro_yearly': 4,
    }

    @classmethod
    def get_current_price_key(cls, subscription):
        """根据订阅信息获取当前 price_key"""
        if not subscription:
            return None

        plan_tier = subscription.plan_tier  # 'plus' or 'pro'

        # 判断是年付还是月付
        is_yearly = False

        # 方法1：通过周期长度判断
        if subscription.current_period_start and subscription.current_period_end:
            try:
                period_days = (subscription.current_period_end - subscription.current_period_start).days
                is_yearly = period_days > 60  # 超过60天认为是年付
            except:
                pass

        # 方法2：如果无法通过周期判断，尝试从 Stripe 获取
        if not is_yearly and subscription.stripe_subscription_id:
            try:
                stripe_sub = stripe.Subscription.retrieve(subscription.stripe_subscription_id)
                price_id = stripe_sub['items']['data'][0]['price']['id']
                # 检查是否匹配年付价格
                if price_id == cls.PRICES.get('plus_yearly') or price_id == cls.PRICES.get('pro_yearly'):
                    is_yearly = True
            except:
                pass

        billing_cycle = 'yearly' if is_yearly else 'monthly'
        return f"{plan_tier}_{billing_cycle}"

    @classmethod
    def is_upgrade(cls, current_price_key, new_price_key):
        """判断是否为升级操作"""
        if not current_price_key:
            return True  # 从免费升级到付费

        current_tier = cls.PRICE_TIER_ORDER.get(current_price_key, 0)
        new_tier = cls.PRICE_TIER_ORDER.get(new_price_key, 0)
        return new_tier > current_tier

    @classmethod
    def upgrade_subscription(cls, user_id, new_price_key):
        """
        升级订阅
        - 立即生效
        - 立即扣补差价 (proration_behavior='always_invoice')
        - 刷新额度为新套餐额度

        Stripe 升级逻辑：
        1. 使用 Subscription.modify() 更新 price
        2. proration_behavior='always_invoice' 立即生成差价发票
        3. Stripe 会自动计算旧订阅剩余时间的 credit
        4. 新订阅金额 - credit = 实际收取的差价
        """
        import logging
        logger = logging.getLogger(__name__)

        if not stripe.api_key:
            return None, "Stripe未配置"

        # 1. 获取用户当前订阅
        subscription = Subscription.query.filter_by(
            user_id=user_id,
            status=SubscriptionStatus.ACTIVE.value
        ).first()

        if not subscription:
            return None, "用户没有活跃订阅，请先订阅"

        # 2. 检查是否为升级
        current_price_key = cls.get_current_price_key(subscription)
        logger.info(f"[Upgrade] User {user_id} upgrading from {current_price_key} to {new_price_key}")

        if not cls.is_upgrade(current_price_key, new_price_key):
            return None, "只支持升级操作，不支持降级。如需降级请取消当前订阅后重新订阅。"

        # 3. 检查 price_key 是否有效
        if new_price_key not in cls.PRICES or not cls.PRICES[new_price_key]:
            return None, f"价格配置不存在: {new_price_key}"

        try:
            # 4. 获取 Stripe 订阅详情
            stripe_sub = stripe.Subscription.retrieve(subscription.stripe_subscription_id)
            logger.info(f"[Upgrade] Current Stripe subscription status: {stripe_sub.get('status')}")

            # 检查订阅状态
            if stripe_sub.get('status') != 'active':
                return None, f"Stripe 订阅状态异常: {stripe_sub.get('status')}"

            # 5. 更新订阅到新价格
            # proration_behavior='always_invoice' 会立即生成差价发票
            # payment_behavior='pending_if_incomplete' 确保即使付款失败也能继续
            logger.info(f"[Upgrade] Modifying subscription to new price: {cls.PRICES[new_price_key]}")
            updated_sub = stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                items=[{
                    'id': stripe_sub['items']['data'][0]['id'],
                    'price': cls.PRICES[new_price_key],
                }],
                proration_behavior='always_invoice',  # 立即生成差价发票
                payment_behavior='allow_incomplete',  # 允许不完整付款（发票会尝试收款）
            )
            logger.info(f"[Upgrade] Subscription modified, latest_invoice: {updated_sub.get('latest_invoice')}")

            # 6. 获取最新发票信息
            latest_invoice_id = updated_sub.get('latest_invoice')
            amount_paid = 0
            currency = 'usd'

            if latest_invoice_id:
                try:
                    invoice = stripe.Invoice.retrieve(latest_invoice_id)
                    invoice_status = invoice.get('status')
                    amount_due = invoice.get('amount_due', 0)
                    amount_paid = invoice.get('amount_paid', 0)
                    currency = invoice.get('currency', 'usd')
                    payment_intent_id = invoice.get('payment_intent')

                    logger.info(f"[Upgrade] Invoice {latest_invoice_id}: status={invoice_status}, amount_due={amount_due}, amount_paid={amount_paid}")

                    # 如果发票是 draft 状态，需要 finalize 并尝试收款
                    if invoice_status == 'draft':
                        logger.info(f"[Upgrade] Finalizing draft invoice {latest_invoice_id}")
                        invoice = stripe.Invoice.finalize_invoice(latest_invoice_id)
                        invoice_status = invoice.get('status')

                    # 如果发票是 open 状态，尝试立即收款
                    if invoice_status == 'open' and amount_due > 0:
                        logger.info(f"[Upgrade] Attempting to pay invoice {latest_invoice_id}")
                        try:
                            invoice = stripe.Invoice.pay(latest_invoice_id)
                            amount_paid = invoice.get('amount_paid', 0)
                            payment_intent_id = invoice.get('payment_intent')
                            logger.info(f"[Upgrade] Invoice paid successfully: {amount_paid}")
                        except stripe.error.CardError as e:
                            logger.warning(f"[Upgrade] Card error when paying invoice: {e}")
                        except Exception as e:
                            logger.warning(f"[Upgrade] Failed to pay invoice: {e}")

                    # 记录交易流水（如果有实际付款）
                    if amount_paid > 0:
                        transaction = Transaction(
                            user_id=user_id,
                            stripe_payment_intent_id=payment_intent_id,
                            stripe_checkout_session_id=None,
                            amount=amount_paid,
                            currency=currency,
                            status=TransactionStatus.SUCCEEDED.value,
                            description=f"升级订阅: {current_price_key} -> {new_price_key}"
                        )
                        db.session.add(transaction)
                        logger.info(f"[Upgrade] Transaction recorded: {amount_paid} {currency}")
                    elif amount_due == 0:
                        # 差价为0或负数（credit足够覆盖），记录一条0金额交易
                        logger.info(f"[Upgrade] No payment required (credit covers upgrade)")

                except Exception as e:
                    logger.warning(f"[Upgrade] Failed to process invoice: {e}")

            # 7. 更新本地订阅记录
            new_plan_tier = 'plus' if 'plus' in new_price_key else 'pro'
            is_yearly = 'yearly' in new_price_key

            subscription.plan_tier = new_plan_tier
            if updated_sub.get('current_period_end'):
                subscription.current_period_end = datetime.fromtimestamp(updated_sub['current_period_end'])
            if updated_sub.get('current_period_start'):
                subscription.current_period_start = datetime.fromtimestamp(updated_sub['current_period_start'])

            # 8. 刷新额度为新套餐额度
            # 升级福利：直接给满额度，旧额度保留
            credits = cls.PLAN_CONFIG[new_plan_tier]['yearly_credits' if is_yearly else 'monthly_credits']
            days_valid = 365 if is_yearly else 30

            cls.add_credits(
                user_id=user_id,
                amount=credits,
                source=CreditSource.SUBSCRIPTION.value,
                service_type=ServiceType.STOCK_ANALYSIS.value,
                days_valid=days_valid,
                subscription_id=subscription.id
            )
            logger.info(f"[Upgrade] Added {credits} credits for user {user_id}")

            db.session.commit()
            logger.info(f"[Upgrade] Upgrade completed successfully for user {user_id}")

            return {
                'success': True,
                'new_plan': new_plan_tier,
                'billing_cycle': 'yearly' if is_yearly else 'monthly',
                'credits_added': credits,
                'current_period_end': subscription.current_period_end.isoformat()
            }, None

        except stripe.error.StripeError as e:
            db.session.rollback()
            return None, f"Stripe错误: {str(e)}"
        except Exception as e:
            db.session.rollback()
            return None, f"升级失败: {str(e)}"

    @classmethod
    def cancel_subscription(cls, user_id):
        """
        取消订阅（周期结束后生效，不退款）
        使用 cancel_at_period_end=True
        """
        if not stripe.api_key:
            return None, "Stripe未配置"

        subscription = Subscription.query.filter_by(
            user_id=user_id,
            status=SubscriptionStatus.ACTIVE.value
        ).first()

        if not subscription:
            return None, "用户没有活跃订阅"

        try:
            # 设置为周期结束后取消（不是立即取消）
            updated_sub = stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=True
            )

            subscription.cancel_at_period_end = True
            db.session.commit()

            return {
                'success': True,
                'message': '订阅将在当前周期结束后取消',
                'cancel_at': subscription.current_period_end.isoformat() if subscription.current_period_end else None
            }, None

        except stripe.error.StripeError as e:
            db.session.rollback()
            return None, f"Stripe错误: {str(e)}"
        except Exception as e:
            db.session.rollback()
            return None, f"取消失败: {str(e)}"

    @classmethod
    def get_upgrade_options(cls, user_id):
        """获取用户可升级的选项"""
        subscription = Subscription.query.filter_by(
            user_id=user_id,
            status=SubscriptionStatus.ACTIVE.value
        ).first()

        if not subscription:
            # 未订阅用户，返回所有选项
            return {
                'current_plan': 'free',
                'current_billing_cycle': None,
                'upgrade_options': ['plus_monthly', 'plus_yearly', 'pro_monthly', 'pro_yearly']
            }

        current_price_key = cls.get_current_price_key(subscription)
        current_tier = cls.PRICE_TIER_ORDER.get(current_price_key, 0)

        # 筛选出比当前等级更高的选项
        upgrade_options = [
            key for key, tier in cls.PRICE_TIER_ORDER.items()
            if tier > current_tier
        ]

        return {
            'current_plan': subscription.plan_tier,
            'current_billing_cycle': 'yearly' if 'yearly' in current_price_key else 'monthly',
            'current_period_end': subscription.current_period_end.isoformat() if subscription.current_period_end else None,
            'cancel_at_period_end': subscription.cancel_at_period_end,
            'upgrade_options': upgrade_options
        }

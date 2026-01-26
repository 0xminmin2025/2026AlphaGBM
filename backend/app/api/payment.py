"""
支付模块路由
处理支付相关的API端点
"""
from flask import Blueprint, request, jsonify, g
import os
import stripe
from ..services.payment_service import PaymentService
from ..utils.auth import require_auth
from ..models import db, DailyQueryCount

payment_bp = Blueprint('payment', __name__, url_prefix='/api/payment')

@payment_bp.route('/create-checkout-session', methods=['POST'])
@require_auth
def create_checkout_session():
    """创建支付会话"""
    user_id = g.user_id
    email = getattr(g, 'user_email', None)
    
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400
        
    price_key = data.get('price_key')
    
    if not price_key or price_key not in PaymentService.PRICES:
        return jsonify({'error': '无效的价格键'}), 400
    
    # 获取成功和取消URL
    success_url = data.get('success_url', f"{os.getenv('VITE_FRONTEND_URL', 'http://localhost:5173')}/dashboard?success=true")
    cancel_url = data.get('cancel_url', f"{os.getenv('VITE_FRONTEND_URL', 'http://localhost:5173')}/pricing?canceled=true")
    
    session, error = PaymentService.create_checkout_session(
        user_id=user_id,
        price_key=price_key,
        success_url=success_url,
        cancel_url=cancel_url,
        email=email
    )
    
    if error:
        return jsonify({'error': error}), 400
    
    return jsonify({
        'session_id': session.id,
        'checkout_url': session.url
    }), 200


@payment_bp.route('/webhook', methods=['POST'])
def webhook():
    """Stripe Webhook回调处理"""
    import logging
    logger = logging.getLogger(__name__)

    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = os.getenv('STRIPE_WEBHOOK_SECRET', '')

    if not endpoint_secret:
        logger.error("[Webhook] Webhook密钥未配置")
        return jsonify({'error': 'Webhook密钥未配置'}), 500

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        logger.error(f"[Webhook] Invalid payload: {e}")
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"[Webhook] Invalid signature: {e}")
        return jsonify({'error': 'Invalid signature'}), 400
    except Exception as e:
        logger.error(f"[Webhook] Event construction error: {e}")
        return jsonify({'error': str(e)}), 400

    event_type = event['type']
    event_id = event['id']
    logger.info(f"[Webhook] Received event: {event_type} [{event_id}]")

    # 处理事件
    try:
        if event_type == 'checkout.session.completed':
            session = event['data']['object']
            logger.info(f"[Webhook] Processing checkout.session.completed for session {session.get('id')}")
            success, message = PaymentService.handle_checkout_completed(session)
            logger.info(f"[Webhook] checkout.session.completed result: success={success}, message={message}")
            if not success:
                db.session.rollback()
                return jsonify({'error': message}), 500

        elif event_type == 'invoice.payment_succeeded' or event_type == 'invoice.paid':
            # 处理订阅付款成功 (包括首次订阅和续费)
            invoice = event['data']['object']
            logger.info(f"[Webhook] Processing {event_type} for invoice {invoice.get('id')}, subscription={invoice.get('subscription')}, billing_reason={invoice.get('billing_reason')}")
            success, message = PaymentService.handle_subscription_renewal(invoice)
            logger.info(f"[Webhook] {event_type} result: success={success}, message={message}")
            if not success:
                db.session.rollback()
                return jsonify({'error': message}), 500

        elif event_type == 'customer.subscription.deleted':
            # 订阅取消
            subscription_id = event['data']['object']['id']
            logger.info(f"[Webhook] Processing customer.subscription.deleted for {subscription_id}")
            from ..models import Subscription
            subscription = Subscription.query.filter_by(
                stripe_subscription_id=subscription_id
            ).first()
            if subscription:
                subscription.status = 'canceled'
                db.session.commit()
                logger.info(f"[Webhook] Subscription {subscription_id} marked as canceled")

        elif event_type == 'customer.subscription.created':
            # 订阅创建 - 只记录日志，实际处理在 checkout.session.completed
            logger.info(f"[Webhook] Subscription created: {event['data']['object'].get('id')}")

        elif event_type == 'customer.subscription.updated':
            # 订阅更新 - 只记录日志
            logger.info(f"[Webhook] Subscription updated: {event['data']['object'].get('id')}")

        else:
            logger.info(f"[Webhook] Unhandled event type: {event_type}")

        return jsonify({'status': 'success'}), 200

    except Exception as e:
        logger.error(f"[Webhook] Error processing {event_type}: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@payment_bp.route('/check-quota', methods=['POST'])
@require_auth
def check_quota():
    """
    检查额度是否足够（不扣减）
    用于前端在分析前显示确认弹窗
    """
    user_id = g.user_id
    data = request.get_json() or {}

    service_type = data.get('service_type', 'stock_analysis')
    amount = data.get('amount', 1)  # 期权分析时为 symbol 数量

    # 获取免费额度信息
    free_info = PaymentService.get_daily_free_quota_info(user_id, service_type)

    # 获取付费额度
    total_credits = PaymentService.get_total_credits(user_id, service_type)

    # 检查是否有足够额度
    can_use_free = free_info['remaining'] >= amount
    can_use_paid = total_credits >= amount
    has_enough = can_use_free or can_use_paid

    return jsonify({
        'has_enough': has_enough,
        'will_use_free': can_use_free,
        'free_quota': free_info['quota'],
        'free_used': free_info['used'],
        'free_remaining': free_info['remaining'],
        'paid_credits': total_credits,
        'amount_needed': amount,
        'message': '额度充足' if has_enough else f'额度不足，需要 {amount} 次，剩余免费 {free_info["remaining"]} 次'
    }), 200


@payment_bp.route('/credits', methods=['GET'])
@require_auth
def get_credits():
    """获取用户额度信息"""
    user_id = g.user_id
    service_type = request.args.get('service_type', 'stock_analysis')

    # 获取总剩余额度
    total_credits = PaymentService.get_total_credits(user_id, service_type)
    
    # 获取订阅信息
    subscription_info = PaymentService.get_user_subscription_info(user_id)
    
    # 获取每日免费额度使用情况
    from datetime import datetime
    today = datetime.now().date()
    daily_count = DailyQueryCount.query.filter_by(
        user_id=user_id,
        date=today
    ).first()
    
    free_quota = PaymentService.DAILY_FREE_QUOTA.get(service_type, 0)
    free_used = daily_count.query_count if daily_count else 0
    free_remaining = max(0, free_quota - free_used)
    
    return jsonify({
        'total_credits': total_credits,
        'subscription': subscription_info,
        'daily_free': {
            'quota': free_quota,
            'used': free_used,
            'remaining': free_remaining
        }
    }), 200


@payment_bp.route('/transactions', methods=['GET'])
@require_auth
def get_transactions():
    """获取用户交易历史"""
    user_id = g.user_id
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    from ..models import Transaction
    
    pagination = Transaction.query.filter_by(user_id=user_id)\
        .order_by(Transaction.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
        
    transactions = []
    for t in pagination.items:
        # Stripe 金额以最小货币单位存储（美分/分），需要除以 100 转换为标准单位
        amount_display = float(t.amount) / 100.0
        transactions.append({
            'period_start': '',
            'date': t.created_at.isoformat(),
            'description': t.description,
            'amount': amount_display,
            'currency': t.currency,
            'status': t.status,
            'invoice_pdf': ''
        })
    
    return jsonify({
        'transactions': transactions,
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    }), 200


@payment_bp.route('/usage-history', methods=['GET'])
@require_auth
def get_usage_history():
    """获取用户额度使用历史"""
    user_id = g.user_id
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    from ..models import UsageLog
    
    pagination = UsageLog.query.filter_by(user_id=user_id)\
        .order_by(UsageLog.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    usage_logs = []
    for log in pagination.items:
        usage_logs.append({
            'id': log.id,
            'service_type': log.service_type,
            'amount_used': log.amount_used,
            'created_at': log.created_at.isoformat(),
        })
    
    return jsonify({
        'usage_logs': usage_logs,
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page,
        'per_page': per_page
    }), 200


@payment_bp.route('/pricing', methods=['GET'])
def get_pricing():
    """获取定价信息 - USD 版本"""
    return jsonify({
        'plans': {
            'free': {
                'name': '免费版',
                'price': 0,
                'credits': '每天2次查询',
                'features': ['每日2次', '期权分析', '股票分析']
            },
            'plus': {
                'name': 'Plus会员',
                'monthly': {
                    'price': 58.8,
                    'currency': 'usd',
                    'credits': 1000,
                    'period': 'month'
                },
                'yearly': {
                    'price': 588,
                    'currency': 'usd',
                    'credits': 12000,
                    'period': 'year',
                    'savings': '节省17%'
                },
                'features': ['1000次查询/月', '期权分析', '反向查分', '股票分析']
            },
            'pro': {
                'name': 'Pro会员',
                'monthly': {
                    'price': 99.8,
                    'currency': 'usd',
                    'credits': 5000,
                    'period': 'month'
                },
                'yearly': {
                    'price': 998,
                    'currency': 'usd',
                    'credits': 60000,
                    'period': 'year',
                    'savings': '节省17%'
                },
                'features': ['5000次查询/月', '期权分析', '反向查分', '股票分析', '投资回顾']
            },
            'enterprise': {
                'name': '企业客户',
                'price': None,
                'credits': '定制化',
                'features': ['API接入', '批量期权分析', '定制化策略', '专属客服']
            }
        },
        'topups': {
            '100': {
                'name': '额度加油包（100次）',
                'price': 4.99,
                'currency': 'usd',
                'credits': 100,
                'validity': '3个月有效'
            }
        }
    }), 200


@payment_bp.route('/upgrade', methods=['POST'])
@require_auth
def upgrade_subscription():
    """升级订阅"""
    import logging
    logger = logging.getLogger(__name__)

    user_id = g.user_id
    logger.info(f"[Upgrade] User {user_id} requesting subscription upgrade")

    data = request.get_json() or {}
    new_price_key = data.get('price_key')

    if not new_price_key:
        return jsonify({'error': '请指定升级的套餐'}), 400

    logger.info(f"[Upgrade] User {user_id} upgrading to {new_price_key}")

    result, error = PaymentService.upgrade_subscription(user_id, new_price_key)

    if error:
        logger.error(f"[Upgrade] User {user_id} upgrade failed: {error}")
        return jsonify({'error': error}), 400

    logger.info(f"[Upgrade] User {user_id} upgrade successful: {result}")
    return jsonify(result), 200


@payment_bp.route('/cancel', methods=['POST'])
@require_auth
def cancel_subscription():
    """取消订阅（周期结束后生效）"""
    user_id = g.user_id

    result, error = PaymentService.cancel_subscription(user_id)

    if error:
        return jsonify({'error': error}), 400

    return jsonify(result), 200


@payment_bp.route('/upgrade-options', methods=['GET'])
@require_auth
def get_upgrade_options():
    """获取用户可升级的选项"""
    user_id = g.user_id

    options = PaymentService.get_upgrade_options(user_id)
    return jsonify(options), 200


@payment_bp.route('/customer-portal', methods=['POST'])
@require_auth
def create_customer_portal_session():
    """创建Stripe客户门户会话"""
    user_id = g.user_id

    try:
        # 导入必要的模型
        from ..models import User, Subscription

        # 获取用户信息
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': '用户不存在'}), 404

        # 检查用户是否有Stripe客户ID
        if not user.stripe_customer_id:
            return jsonify({'error': '未找到客户信息，请先创建订阅'}), 400

        # 检查用户是否有有效订阅
        subscription = Subscription.query.filter_by(
            user_id=user_id,
            status='active'
        ).first()

        if not subscription:
            return jsonify({'error': '未找到有效订阅'}), 400

        # 获取返回URL
        data = request.get_json() or {}
        return_url = data.get('return_url', f"{os.getenv('VITE_FRONTEND_URL', 'http://localhost:5173')}/profile")

        # 创建客户门户会话
        portal_session = stripe.billing_portal.Session.create(
            customer=user.stripe_customer_id,
            return_url=return_url
        )

        return jsonify({
            'portal_url': portal_session.url
        }), 200

    except stripe.error.StripeError as e:
        return jsonify({'error': f'Stripe错误: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': f'创建客户门户失败: {str(e)}'}), 500

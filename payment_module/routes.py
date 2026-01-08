"""
支付模块路由
处理支付相关的API端点
"""
from flask import Blueprint, request, jsonify
from functools import wraps
import stripe
import os
from .payment_service import PaymentService

payment_bp = Blueprint('payment', __name__, url_prefix='/api/payment')

# 需要从外部注入
payment_service = None
get_current_user_id = None


def init_payment_routes(service, get_user_func):
    """
    初始化支付路由
    
    Args:
        service: PaymentService实例
        get_user_func: 获取当前用户ID的函数
    """
    global payment_service, get_current_user_id
    payment_service = service
    get_current_user_id = get_user_func


@payment_bp.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    """创建支付会话"""
    if not payment_service:
        return jsonify({'error': '支付服务未初始化'}), 500
    
    user_info = get_current_user_id()
    if not user_info or 'user_id' not in user_info:
        return jsonify({'error': '请先登录'}), 401
    
    user_id = user_info['user_id']
    data = request.json
    price_key = data.get('price_key')
    
    if not price_key or price_key not in payment_service.PRICES:
        return jsonify({'error': '无效的价格键'}), 400
    
    # 获取成功和取消URL
    success_url = data.get('success_url', 'https://alphagbm.com/dashboard?success=true')
    cancel_url = data.get('cancel_url', 'https://alphagbm.com/pricing?canceled=true')
    
    session, error = payment_service.create_checkout_session(
        user_id=user_id,
        price_key=price_key,
        success_url=success_url,
        cancel_url=cancel_url
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
    if not payment_service:
        return jsonify({'error': '支付服务未初始化'}), 500
    
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = os.getenv('STRIPE_WEBHOOK_SECRET', '')
    
    if not endpoint_secret:
        return jsonify({'error': 'Webhook密钥未配置'}), 500
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        return jsonify({'error': 'Invalid signature'}), 400
    
    # 处理事件
    try:
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            success, message = payment_service.handle_checkout_completed(session)
            if not success:
                payment_service.db.session.rollback()
                return jsonify({'error': message}), 500
        
        elif event['type'] == 'invoice.payment_succeeded':
            # 处理订阅续费
            invoice = event['data']['object']
            success, message = payment_service.handle_subscription_renewal(invoice)
            if not success:
                payment_service.db.session.rollback()
                return jsonify({'error': message}), 500
        
        elif event['type'] == 'customer.subscription.deleted':
            # 订阅取消
            subscription_id = event['data']['object']['id']
            subscription = payment_service.Subscription.query.filter_by(
                stripe_subscription_id=subscription_id
            ).first()
            if subscription:
                subscription.status = 'canceled'
                payment_service.db.session.commit()
        
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        payment_service.db.session.rollback()
        return jsonify({'error': str(e)}), 500


@payment_bp.route('/credits', methods=['GET'])
def get_credits():
    """获取用户额度信息"""
    if not payment_service:
        return jsonify({'error': '支付服务未初始化'}), 500
    
    user_info = get_current_user_id()
    if not user_info or 'user_id' not in user_info:
        return jsonify({'error': '请先登录'}), 401
    
    user_id = user_info['user_id']
    service_type = request.args.get('service_type', 'stock_analysis')
    
    # 获取总剩余额度
    total_credits = payment_service.get_total_credits(user_id, service_type)
    
    # 获取订阅信息
    subscription_info = payment_service.get_user_subscription_info(user_id)
    
    # 获取每日免费额度使用情况
    from datetime import datetime
    today = datetime.now().date()
    daily_count = payment_service.DailyQueryCount.query.filter_by(
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


@payment_bp.route('/pricing', methods=['GET'])
def get_pricing():
    """获取定价信息"""
    return jsonify({
        'plans': {
            'free': {
                'name': '免费版',
                'price': 0,
                'credits': '每天2次查询',
                'features': ['基础股票分析', '每日2次免费查询']
            },
            'plus': {
                'name': 'Plus会员',
                'monthly': {
                    'price': 399,
                    'currency': 'cny',
                    'credits': 1000,
                    'period': 'month'
                },
                'yearly': {
                    'price': 3990,
                    'currency': 'cny',
                    'credits': 12000,
                    'period': 'year',
                    'savings': '节省17%'
                },
                'features': ['1000次查询/月', 'AI深度分析', '期权分析', '优先支持']
            },
            'pro': {
                'name': 'Pro会员',
                'monthly': {
                    'price': 999,
                    'currency': 'cny',
                    'credits': 5000,
                    'period': 'month'
                },
                'yearly': {
                    'price': 9990,
                    'currency': 'cny',
                    'credits': 60000,
                    'period': 'year',
                    'savings': '节省17%'
                },
                'features': ['5000次查询/月', '所有功能', '深度研报', '专属支持']
            }
        },
        'topups': {
            '100': {
                'name': '额度加油包（100次）',
                'price': 29,
                'currency': 'cny',
                'credits': 100,
                'validity': '3个月有效'
            }
        }
    }), 200

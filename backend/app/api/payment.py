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
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    
    # 处理事件
    try:
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            success, message = PaymentService.handle_checkout_completed(session)
            if not success:
                db.session.rollback()
                return jsonify({'error': message}), 500
        
        elif event['type'] == 'invoice.payment_succeeded':
            # 处理订阅续费
            invoice = event['data']['object']
            success, message = PaymentService.handle_subscription_renewal(invoice)
            if not success:
                db.session.rollback()
                return jsonify({'error': message}), 500
        
        elif event['type'] == 'customer.subscription.deleted':
            # 订阅取消
            subscription_id = event['data']['object']['id']
            from ..models import Subscription
            subscription = Subscription.query.filter_by(
                stripe_subscription_id=subscription_id
            ).first()
            if subscription:
                subscription.status = 'canceled'
                db.session.commit()
        
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@payment_bp.route('/credits', methods=['GET'])
@require_auth
def get_credits():
    """获取用户额度信息"""
    user_id = g.user_id
    service_type = request.args.get('service_type', 'stock_analysis') # Using literal value 'stock_analysis' or mapping from enum
    # ServiceType enum in models: STOCK_ANALYSIS = 'stock_analysis'
    
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
        transactions.append({
            'period_start': '', # Not applicable for single transaction usually, unless subscription period?
            'date': t.created_at.isoformat(),
            'description': t.description,
            'amount': float(t.amount) / 100.0 if t.currency == 'cny' else t.amount, # Amount is usually in cents for Stripe? My payment service uses amount_total from session.
            # In handle_checkout_completed, amount=session['amount_total']. Stripe amounts are in smallest unit (cents).
            # So I should divide by 100 if currency is cny/usd.
            'currency': t.currency,
            'status': t.status,
            'invoice_pdf': '' # We don't store invoice URL readily in Transaction model yet?
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
    """获取定价信息 - 期权优先版本"""
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
                'features': ['1000次查询/月', '期权分析', '反向查分', '股票分析']
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
                'price': 29,
                'currency': 'cny',
                'credits': 100,
                'validity': '3个月有效'
            }
        }
    }), 200


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

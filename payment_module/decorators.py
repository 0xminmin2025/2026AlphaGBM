"""
支付模块装饰器
用于API的额度检查和扣减
"""
from functools import wraps
from flask import jsonify, request
from .models import ServiceType

# 需要从外部注入
payment_service = None
get_current_user_id = None


def init_decorators(service, get_user_func):
    """
    初始化装饰器
    
    Args:
        service: PaymentService实例
        get_user_func: 获取当前用户ID的函数
    """
    global payment_service, get_current_user_id
    payment_service = service
    get_current_user_id = get_user_func


def check_quota(service_type=ServiceType.STOCK_ANALYSIS.value, amount=1):
    """
    额度检查装饰器
    
    使用方式:
        @check_quota(service_type='stock_analysis', amount=1)
        def analyze_stock():
            ...
    
    Args:
        service_type: 服务类型
        amount: 消耗的额度数量
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not payment_service:
                return jsonify({'error': '支付服务未初始化'}), 500
            
            user_info = get_current_user_id()
            if not user_info or 'user_id' not in user_info:
                return jsonify({'error': '请先登录'}), 401
            
            user_id = user_info['user_id']
            
            # 检查并扣减额度
            success, message, remaining = payment_service.check_and_deduct_credits(
                user_id=user_id,
                service_type=service_type,
                amount=amount
            )
            
            if not success:
                return jsonify({
                    'error': message,
                    'remaining_credits': remaining,
                    'code': 'INSUFFICIENT_CREDITS'
                }), 402  # 402 Payment Required
            
            # 如果使用免费额度，需要更新DailyQueryCount
            if '免费' in message or 'free' in message.lower():
                from datetime import datetime
                today = datetime.now().date()
                daily_count = payment_service.DailyQueryCount.query.filter_by(
                    user_id=user_id,
                    date=today
                ).first()
                
                if not daily_count:
                    daily_count = payment_service.DailyQueryCount(
                        user_id=user_id,
                        date=today,
                        query_count=1,
                        max_queries=payment_service.DAILY_FREE_QUOTA.get(service_type, 0)
                    )
                    payment_service.db.session.add(daily_count)
                else:
                    daily_count.query_count += 1
                
                payment_service.db.session.commit()
            
            # 执行原函数
            response = f(*args, **kwargs)
            
            # 在响应中添加额度信息（如果是JSON响应）
            if isinstance(response, tuple) and len(response) == 2:
                data, status_code = response
                if isinstance(data, dict) or hasattr(data, 'get_json'):
                    if hasattr(data, 'get_json'):
                        json_data = data.get_json()
                    else:
                        json_data = data
                    
                    if json_data and isinstance(json_data, dict):
                        json_data['credits_info'] = {
                            'remaining': remaining,
                            'message': message
                        }
                        return jsonify(json_data), status_code
            
            return response
        return wrapper
    return decorator

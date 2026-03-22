"""API限流中间件"""

from flask import request, jsonify, g
from functools import wraps
import time
from collections import defaultdict

# 简单内存限流（生产环境建议用Redis）
rate_limit_store = defaultdict(list)


def rate_limit(max_requests=60, window_seconds=60):
    """限流装饰器 - 只对API Key用户生效"""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if getattr(g, 'auth_method', None) != 'api_key':
                return f(*args, **kwargs)

            user_id = g.user_id
            now = time.time()

            # 清理过期记录
            rate_limit_store[user_id] = [
                t for t in rate_limit_store[user_id]
                if t > now - window_seconds
            ]

            if len(rate_limit_store[user_id]) >= max_requests:
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'retry_after': window_seconds,
                    'limit': max_requests
                }), 429

            rate_limit_store[user_id].append(now)
            return f(*args, **kwargs)
        return decorated
    return decorator

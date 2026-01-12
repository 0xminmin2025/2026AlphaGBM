import os
import logging
import time
from functools import wraps
from flask import request, jsonify, g
from supabase import create_client, Client
from ..config import Config

logger = logging.getLogger(__name__)

# Token cache to avoid repeated Supabase calls
# Format: {token: {'user_data': user_obj, 'expires_at': timestamp}}
token_cache = {}
CACHE_DURATION = 300  # 5 minutes in seconds

# Initialize Supabase Client
supabase: Client = None
if Config.SUPABASE_URL and Config.SUPABASE_KEY:
    try:
        supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        logger.info("Supabase client initialized")
    except Exception as e:
        logger.error(f"Supabase client initialization failed: {e}")
else:
    logger.warning("Supabase credentials missing in config")

def clean_expired_tokens():
    """Remove expired tokens from cache"""
    current_time = time.time()
    expired_tokens = [token for token, data in token_cache.items()
                     if data['expires_at'] < current_time]

    for token in expired_tokens:
        del token_cache[token]

    if expired_tokens:
        logger.debug(f"Cleaned {len(expired_tokens)} expired tokens from cache")

def get_cached_user(token):
    """Get user data from cache if valid"""
    if token not in token_cache:
        return None

    cached_data = token_cache[token]

    # Check if token is expired
    if time.time() > cached_data['expires_at']:
        del token_cache[token]
        return None

    return cached_data['user_data']

def cache_user_token(token, user_data):
    """Cache user data for a token"""
    # Clean expired tokens periodically (every 50th call)
    if len(token_cache) % 50 == 0:
        clean_expired_tokens()

    expires_at = time.time() + CACHE_DURATION
    token_cache[token] = {
        'user_data': user_data,
        'expires_at': expires_at
    }

    logger.debug(f"Cached token for user {user_data.id if hasattr(user_data, 'id') else 'unknown'}")

def invalidate_token_cache(token=None):
    """Invalidate cache for a specific token or all tokens"""
    if token:
        if token in token_cache:
            del token_cache[token]
            logger.debug("Invalidated specific token from cache")
    else:
        token_cache.clear()
        logger.debug("Cleared entire token cache")

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not supabase:
             return jsonify({'error': 'Supabase client not initialized'}), 500
             
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': 'Missing Authorization header'}), 401
            
        try:
            # Format: "Bearer <token>"
            if len(auth_header.split(' ')) < 2:
                return jsonify({'error': 'Invalid Authorization header format'}), 401

            token = auth_header.split(' ')[1]

            # Try to get user from cache first
            cached_user = get_cached_user(token)
            if cached_user:
                # Use cached user data
                user = cached_user
                logger.debug(f"Using cached user data for {user.id if hasattr(user, 'id') else 'unknown'}")
            else:
                # Cache miss - verify token using Supabase Auth
                logger.debug("Cache miss - fetching user from Supabase")
                user_response = supabase.auth.get_user(token)

                if not user_response or not user_response.user:
                    return jsonify({'error': 'Invalid token'}), 401

                user = user_response.user
                # Cache the user data
                cache_user_token(token, user)

            # Store user info in flask global (g)
            g.user_id = user.id
            if hasattr(user, 'email'):
                g.user_email = user.email

            # Ensure user exists in local database
            from ..models import db, User
            existing_user = User.query.filter_by(id=user.id).first()
            if not existing_user:
                # Create user record if it doesn't exist
                new_user = User(
                    id=user.id,
                    email=user.email if hasattr(user, 'email') else f"{user.id}@unknown.com"
                )
                db.session.add(new_user)
                db.session.commit()
                logger.info(f"Created new user record for {user.id}")
            else:
                # Update last login (only if not from cache to avoid frequent DB updates)
                if not cached_user:
                    from datetime import datetime
                    existing_user.last_login = datetime.utcnow()
                    db.session.commit()
            
        except Exception as e:
            logger.error(f"Auth error: {e}")
            return jsonify({'error': 'Unauthorized'}), 401
            
        return f(*args, **kwargs)
    return decorated

def get_current_user_info():
    """Get current user info from g"""
    try:
        if hasattr(g, 'user_id'):
            info = {'user_id': g.user_id}
            if hasattr(g, 'user_email'):
                info['email'] = g.user_email
            return info
        return None
    except Exception:
        return None

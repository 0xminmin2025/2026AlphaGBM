import os
import logging
from functools import wraps
from flask import request, jsonify, g
from supabase import create_client, Client
from ..config import Config

logger = logging.getLogger(__name__)

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
            # Verify token using Supabase Auth
            user_response = supabase.auth.get_user(token)
            
            if not user_response or not user_response.user:
                return jsonify({'error': 'Invalid token'}), 401
                
            # Store user info in flask global (g)
            g.user_id = user_response.user.id
            if hasattr(user_response.user, 'email'):
                g.user_email = user_response.user.email

            # Ensure user exists in local database
            from ..models import db, User
            existing_user = User.query.filter_by(id=user_response.user.id).first()
            if not existing_user:
                # Create user record if it doesn't exist
                new_user = User(
                    id=user_response.user.id,
                    email=user_response.user.email if hasattr(user_response.user, 'email') else f"{user_response.user.id}@unknown.com"
                )
                db.session.add(new_user)
                db.session.commit()
                logger.info(f"Created new user record for {user_response.user.id}")
            else:
                # Update last login
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

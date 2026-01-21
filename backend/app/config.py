import os
from datetime import timedelta
import logging

from dotenv import load_dotenv

# ../.env
DOTENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../.env')

load_dotenv(DOTENV_PATH)

logger = logging.getLogger(__name__)

class Config:
    # Basic Config
    SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'dev-secret-key')
    
    # Database
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Database Connection Pool Configuration
    # Optimized for PostgreSQL/Supabase performance
    SQLALCHEMY_ENGINE_OPTIONS = {
        # Connection Pool Settings
        'pool_size': 10,                    # Number of connections to maintain in pool
        'max_overflow': 20,                 # Additional connections beyond pool_size
        'pool_timeout': 30,                 # Seconds to wait for connection from pool
        'pool_recycle': 300,                # Recycle connections after 5 minutes (important for Supabase)
        'pool_pre_ping': True,              # Verify connections before use (critical for stale connections)

        # Connection Settings for PostgreSQL/Supabase
        'connect_args': {
            'connect_timeout': 10,          # Connection timeout in seconds
            'application_name': 'AlphaG-Backend',  # App name for monitoring
            'options': '-c statement_timeout=30000',  # Statement timeout (30 seconds)
            'keepalives': 1,                # Enable TCP keepalives
            'keepalives_idle': 60,          # Seconds before sending keepalive
            'keepalives_interval': 10,      # Seconds between keepalives
            'keepalives_count': 5,          # Failed keepalives before connection is dead
        },

        # Echo SQL queries in debug mode
        'echo': os.getenv('DATABASE_DEBUG', 'false').lower() == 'true'
    }
    
    # 优先使用 POSTGRES_URL (Supabase Connection Pooler)
    # 如果没有，尝试使用 SQLALCHEMY_DATABASE_URI
    database_url = os.getenv('POSTGRES_URL') or os.getenv('SQLALCHEMY_DATABASE_URI')

    if database_url:
        # 确保 url scheme 是 postgresql (SQLAlchemy 识别)
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        
        # Remove 'supa' param (invalid for psycopg2)
        try:
            from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
            u = urlparse(database_url)
            q = parse_qs(u.query)
            if 'supa' in q:
                del q['supa']
                u = u._replace(query=urlencode(q, doseq=True))
                database_url = urlunparse(u)
        except Exception as e:
            logger.warning(f"Failed to sanitize database URL: {e}")
        
        SQLALCHEMY_DATABASE_URI = database_url
    else:
        # Fallback for dev
        db_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
        os.makedirs(db_dir, exist_ok=True)
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(db_dir, "alphag.db")}'

        # Override connection pool settings for SQLite (different requirements)
        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_size': 5,                     # Smaller pool for SQLite
            'max_overflow': 10,                 # Limited overflow for SQLite
            'pool_timeout': 20,                 # Shorter timeout for SQLite
            'pool_recycle': 1800,               # 30 minutes for SQLite
            'pool_pre_ping': False,             # SQLite doesn't need pre-ping

            # SQLite-specific settings
            'connect_args': {
                'timeout': 20,                  # SQLite timeout
                'check_same_thread': False,     # Allow SQLite multi-threading
            },

            'echo': os.getenv('DATABASE_DEBUG', 'false').lower() == 'true'
        }
    
    # Supabase
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_ANON_KEY') or os.getenv('SUPABASE_KEY')
    
    # Mail
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', '587'))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', os.getenv('MAIL_USERNAME', ''))
    
    # Business Logic
    REGULAR_USER_DAILY_MAX_QUERIES = int(os.getenv('REGULAR_USER_DAILY_MAX_QUERIES', '5'))
    
    # Stripe
    STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', '')
    STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', '')
    STRIPE_PRICES = {
        'plus_monthly': os.getenv('STRIPE_PRICE_PLUS_MONTHLY', ''),
        'plus_yearly': os.getenv('STRIPE_PRICE_PLUS_YEARLY', ''),
        'pro_monthly': os.getenv('STRIPE_PRICE_PRO_MONTHLY', ''),
        'pro_yearly': os.getenv('STRIPE_PRICE_PRO_YEARLY', ''),
        'topup_100': os.getenv('STRIPE_PRICE_TOPUP_100', '')
    }

    # Google Gemini API (for image recognition)
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', '')

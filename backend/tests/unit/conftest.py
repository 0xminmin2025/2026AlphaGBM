"""
Shared fixtures for unit tests.
Uses SQLite in-memory database and mocks all external dependencies.
"""
import os
import sys
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

# Ensure the backend package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


class TestConfig:
    """Minimal config for testing -- SQLite in-memory, no external services."""
    TESTING = True
    SECRET_KEY = 'test-secret-key'
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {}
    SUPABASE_URL = 'https://fake.supabase.co'
    SUPABASE_KEY = 'fake-key'
    REGULAR_USER_DAILY_MAX_QUERIES = 2
    STRIPE_SECRET_KEY = ''
    STRIPE_WEBHOOK_SECRET = ''
    STRIPE_PRICES = {
        'plus_monthly': 'price_plus_m',
        'plus_yearly': 'price_plus_y',
        'pro_monthly': 'price_pro_m',
        'pro_yearly': 'price_pro_y',
        'topup_100': 'price_topup',
    }
    GOOGLE_API_KEY = ''
    MAIL_SERVER = 'smtp.test.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = ''
    MAIL_PASSWORD = ''
    MAIL_DEFAULT_SENDER = ''


@pytest.fixture(scope='session')
def _supabase_patch():
    """Session-wide patch that prevents the real Supabase client from being
    created when the auth module is first imported."""
    mock_client = MagicMock()
    with patch('supabase.create_client', return_value=mock_client):
        yield mock_client


@pytest.fixture()
def app(_supabase_patch):
    """Create a Flask application configured for testing.

    * Uses SQLite in-memory database.
    * Patches task queue and scheduler initialisation so they never touch
      real infrastructure.
    * Creates all database tables before the test and tears them down
      afterwards.
    """
    with patch('app.services.task_queue.init_task_queue'), \
         patch('app.services.task_queue.shutdown_task_queue'), \
         patch('app.scheduler.init_scheduler', create=True), \
         patch('app.scheduler.shutdown_scheduler', create=True):
        from app import create_app
        application = create_app(config_class=TestConfig)

    yield application


@pytest.fixture()
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture()
def db_session(app):
    """Provide a clean database session that rolls back after each test."""
    from app.models import db
    with app.app_context():
        db.create_all()
        yield db.session
        db.session.rollback()
        db.drop_all()


@pytest.fixture()
def sample_user(db_session):
    """Insert and return a basic User row."""
    from app.models import User
    user = User(
        id='test-user-uuid-1234',
        email='testuser@example.com',
        username='testuser',
        created_at=datetime.utcnow(),
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture()
def mock_supabase_auth():
    """Return a MagicMock that mimics the Supabase auth.get_user response."""
    mock_user = MagicMock()
    mock_user.id = 'test-user-uuid-1234'
    mock_user.email = 'testuser@example.com'
    mock_response = MagicMock()
    mock_response.user = mock_user
    return mock_response


@pytest.fixture()
def auth_headers():
    """Standard Authorization header for test requests."""
    return {'Authorization': 'Bearer fake-valid-token'}

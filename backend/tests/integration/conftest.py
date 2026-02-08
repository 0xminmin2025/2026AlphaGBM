"""
Integration test fixtures for API endpoint testing.

Provides Flask test client, mock authentication, and mock external services
(Supabase, Stripe, Yahoo Finance, data APIs) so tests run entirely offline.
"""
import pytest
import os
import sys
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

# Ensure backend app is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


# ---------------------------------------------------------------------------
# Flask application and test client
# ---------------------------------------------------------------------------

@pytest.fixture(scope='session')
def app():
    """Create Flask test application with SQLite in-memory database."""
    os.environ['TESTING'] = 'true'
    os.environ['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
    os.environ['JWT_SECRET_KEY'] = 'test-secret-key'
    os.environ['STRIPE_SECRET_KEY'] = 'sk_test_fake'
    os.environ['STRIPE_WEBHOOK_SECRET'] = 'whsec_test_fake'
    os.environ['GOOGLE_API_KEY'] = 'test-gemini-key'

    with patch('app.utils.auth.create_client') as mock_create:
        mock_supabase = MagicMock()
        mock_create.return_value = mock_supabase

        from app import create_app
        from app.config import Config

        class TestConfig(Config):
            TESTING = True
            SQLALCHEMY_DATABASE_URI = 'sqlite://'
            SQLALCHEMY_ENGINE_OPTIONS = {
                'pool_pre_ping': False,
                'connect_args': {'check_same_thread': False},
            }
            STRIPE_SECRET_KEY = 'sk_test_fake'
            STRIPE_WEBHOOK_SECRET = 'whsec_test_fake'

        application = create_app(TestConfig)

        with application.app_context():
            from app.models import db
            db.create_all()

        yield application

        with application.app_context():
            db.drop_all()


@pytest.fixture
def client(app):
    """Flask test client for making HTTP requests."""
    return app.test_client()


@pytest.fixture
def db_session(app):
    """Database session with automatic rollback after each test."""
    from app.models import db
    with app.app_context():
        db.session.begin_nested()
        yield db.session
        db.session.rollback()


# ---------------------------------------------------------------------------
# Sample database records
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_user(app):
    """
    Ensure a sample user row exists in the local database.

    Uses get-or-create to avoid UNIQUE constraint errors when
    ``require_auth`` auto-creates the same user during a request.
    """
    from app.models import db, User
    with app.app_context():
        user = User.query.filter_by(id='test-user-uuid-1234').first()
        if not user:
            user = User(
                id='test-user-uuid-1234',
                email='test@example.com',
                username='testuser',
            )
            db.session.add(user)
            db.session.commit()
        yield user


@pytest.fixture
def sample_subscription(app, sample_user):
    """Create an active subscription for the sample user."""
    from app.models import db, Subscription
    with app.app_context():
        sub = Subscription.query.filter_by(
            user_id=sample_user.id, status='active'
        ).first()
        if not sub:
            sub = Subscription(
                user_id=sample_user.id,
                stripe_subscription_id='sub_test_123',
                plan_tier='plus',
                status='active',
                current_period_start=datetime.utcnow(),
                current_period_end=datetime.utcnow() + timedelta(days=30),
            )
            db.session.add(sub)
            db.session.commit()
        yield sub


@pytest.fixture
def sample_credits(app, sample_user, sample_subscription):
    """Create sample credit entries in the ledger."""
    from app.models import db, CreditLedger, ServiceType, CreditSource
    with app.app_context():
        credit = CreditLedger(
            user_id=sample_user.id,
            service_type=ServiceType.STOCK_ANALYSIS.value,
            source=CreditSource.SUBSCRIPTION.value,
            amount_initial=1000,
            amount_remaining=950,
            expires_at=datetime.utcnow() + timedelta(days=30),
            subscription_id=sample_subscription.id,
        )
        db.session.add(credit)
        db.session.commit()
        yield credit
        try:
            db.session.delete(credit)
            db.session.commit()
        except Exception:
            db.session.rollback()


# ---------------------------------------------------------------------------
# Authentication helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def auth_headers():
    """Return HTTP headers containing a fake Bearer token."""
    return {'Authorization': 'Bearer fake-test-token-12345'}


@pytest.fixture
def mock_supabase_auth(app):
    """
    Patch the Supabase client used inside ``require_auth`` and ``check_quota``
    so that token validation succeeds and returns a deterministic user object.
    """
    mock_user = MagicMock()
    mock_user.id = 'test-user-uuid-1234'
    mock_user.email = 'test@example.com'

    mock_response = MagicMock()
    mock_response.user = mock_user

    with patch('app.utils.auth.supabase') as mock_sb:
        mock_sb.auth.get_user.return_value = mock_response
        # Also patch the reference imported inside the decorators module
        with patch('app.utils.decorators.supabase', mock_sb):
            yield mock_sb


# ---------------------------------------------------------------------------
# Stripe mocks
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_stripe():
    """Mock the ``stripe`` module used by the payment service."""
    with patch('app.services.payment_service.stripe') as mock_s:
        mock_session = MagicMock()
        mock_session.id = 'cs_test_123'
        mock_session.url = 'https://checkout.stripe.com/test'
        mock_s.checkout.Session.create.return_value = mock_session

        mock_customer = MagicMock()
        mock_customer.id = 'cus_test_123'
        mock_s.Customer.create.return_value = mock_customer

        yield mock_s


@pytest.fixture
def mock_stripe_webhook():
    """Mock ``stripe.Webhook.construct_event`` for webhook tests."""
    with patch('app.api.payment.stripe') as mock_s:
        yield mock_s

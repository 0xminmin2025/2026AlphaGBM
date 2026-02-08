"""
Global test fixtures for AlphaGBM backend tests.
All external dependencies (Supabase, Stripe, data APIs) are mocked.
"""
import pytest
import os
import sys
from unittest.mock import MagicMock, patch
from datetime import datetime, date, timedelta

# Ensure backend app is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture(scope='session')
def app():
    """Create Flask test application with SQLite in-memory database."""
    # Set test environment variables before importing app
    os.environ['TESTING'] = 'true'
    os.environ['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
    os.environ['JWT_SECRET_KEY'] = 'test-secret-key'
    os.environ['STRIPE_SECRET_KEY'] = 'sk_test_fake'
    os.environ['STRIPE_WEBHOOK_SECRET'] = 'whsec_test_fake'
    os.environ['GOOGLE_API_KEY'] = 'test-gemini-key'

    # Mock supabase before importing app
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
                'connect_args': {'check_same_thread': False}
            }
            STRIPE_SECRET_KEY = 'sk_test_fake'
            STRIPE_WEBHOOK_SECRET = 'whsec_test_fake'

        app = create_app(TestConfig)

        with app.app_context():
            from app.models import db
            db.create_all()

        yield app

        with app.app_context():
            db.drop_all()


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture
def db_session(app):
    """Database session with automatic rollback after each test."""
    from app.models import db
    with app.app_context():
        db.session.begin_nested()
        yield db.session
        db.session.rollback()


@pytest.fixture
def sample_user(app):
    """Create a sample user in the database."""
    from app.models import db, User
    with app.app_context():
        user = User(
            id='test-user-uuid-1234',
            email='test@example.com',
            username='testuser'
        )
        db.session.add(user)
        db.session.commit()
        yield user
        # Cleanup
        try:
            db.session.delete(user)
            db.session.commit()
        except Exception:
            db.session.rollback()


@pytest.fixture
def sample_subscription(app, sample_user):
    """Create a sample subscription."""
    from app.models import db, Subscription
    with app.app_context():
        sub = Subscription(
            user_id=sample_user.id,
            stripe_subscription_id='sub_test_123',
            plan_tier='plus',
            status='active',
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow() + timedelta(days=30)
        )
        db.session.add(sub)
        db.session.commit()
        yield sub
        try:
            db.session.delete(sub)
            db.session.commit()
        except Exception:
            db.session.rollback()


@pytest.fixture
def sample_credits(app, sample_user, sample_subscription):
    """Create sample credits in the ledger."""
    from app.models import db, CreditLedger, ServiceType, CreditSource
    with app.app_context():
        credit = CreditLedger(
            user_id=sample_user.id,
            service_type=ServiceType.STOCK_ANALYSIS.value,
            source=CreditSource.SUBSCRIPTION.value,
            amount_initial=1000,
            amount_remaining=950,
            expires_at=datetime.utcnow() + timedelta(days=30),
            subscription_id=sample_subscription.id
        )
        db.session.add(credit)
        db.session.commit()
        yield credit
        try:
            db.session.delete(credit)
            db.session.commit()
        except Exception:
            db.session.rollback()


@pytest.fixture
def auth_headers():
    """Headers with a fake auth token."""
    return {'Authorization': 'Bearer fake-test-token-12345'}


@pytest.fixture
def mock_supabase_auth(app):
    """Mock Supabase auth to return a valid user."""
    mock_user = MagicMock()
    mock_user.id = 'test-user-uuid-1234'
    mock_user.email = 'test@example.com'

    mock_response = MagicMock()
    mock_response.user = mock_user

    with patch('app.utils.auth.supabase') as mock_sb:
        mock_sb.auth.get_user.return_value = mock_response
        yield mock_sb


@pytest.fixture
def mock_stripe():
    """Mock Stripe API calls."""
    with patch('app.services.payment_service.stripe') as mock_s:
        # Mock checkout session
        mock_session = MagicMock()
        mock_session.id = 'cs_test_123'
        mock_session.url = 'https://checkout.stripe.com/test'
        mock_s.checkout.Session.create.return_value = mock_session

        # Mock customer
        mock_customer = MagicMock()
        mock_customer.id = 'cus_test_123'
        mock_s.Customer.create.return_value = mock_customer

        # Mock subscription
        mock_sub = {
            'id': 'sub_test_123',
            'status': 'active',
            'current_period_start': int(datetime.utcnow().timestamp()),
            'current_period_end': int((datetime.utcnow() + timedelta(days=30)).timestamp()),
            'items': {'data': [{'id': 'si_test', 'price': {'id': 'price_test'}}]},
            'customer': 'cus_test_123'
        }
        mock_sub_obj = MagicMock()
        mock_sub_obj.get = lambda k, d=None: mock_sub.get(k, d)
        mock_sub_obj.__getitem__ = lambda s, k: mock_sub[k]
        mock_s.Subscription.retrieve.return_value = mock_sub_obj
        mock_s.Subscription.modify.return_value = mock_sub_obj

        yield mock_s

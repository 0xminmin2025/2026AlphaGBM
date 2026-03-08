"""
Unit tests for PaymentService class.
All Stripe API calls and database queries are mocked.
"""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime, timedelta


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_stripe():
    """Patch the stripe module imported by payment_service."""
    with patch('app.services.payment_service.stripe') as mock_s:
        mock_s.api_key = 'sk_test_fake'

        # Checkout Session
        mock_session = MagicMock()
        mock_session.id = 'cs_test_session_1'
        mock_session.url = 'https://checkout.stripe.com/test'
        mock_s.checkout.Session.create.return_value = mock_session

        # Customer
        mock_customer = MagicMock()
        mock_customer.id = 'cus_test_abc'
        mock_s.Customer.create.return_value = mock_customer

        # Subscription (dict-like mock)
        now_ts = int(datetime.utcnow().timestamp())
        end_ts = int((datetime.utcnow() + timedelta(days=30)).timestamp())
        sub_data = {
            'id': 'sub_test_123',
            'status': 'active',
            'current_period_start': now_ts,
            'current_period_end': end_ts,
            'items': {'data': [{'id': 'si_item_1', 'price': {'id': 'price_plus_m'}}]},
            'customer': 'cus_test_abc',
            'latest_invoice': 'inv_test_001',
        }
        mock_sub_obj = MagicMock()
        mock_sub_obj.get = lambda k, d=None: sub_data.get(k, d)
        mock_sub_obj.__getitem__ = lambda s, k: sub_data[k]
        mock_s.Subscription.retrieve.return_value = mock_sub_obj
        mock_s.Subscription.modify.return_value = mock_sub_obj

        # Invoice
        mock_invoice = MagicMock()
        inv_data = {
            'id': 'inv_test_001',
            'status': 'paid',
            'amount_due': 999,
            'amount_paid': 999,
            'currency': 'usd',
            'payment_intent': 'pi_test_001',
        }
        mock_invoice.get = lambda k, d=None: inv_data.get(k, d)
        mock_invoice.__getitem__ = lambda s, k: inv_data[k]
        mock_s.Invoice.retrieve.return_value = mock_invoice
        mock_s.Invoice.pay.return_value = mock_invoice

        yield mock_s


@pytest.fixture()
def payment_service(app):
    """Import PaymentService inside app context so models are available."""
    with app.app_context():
        from app.services.payment_service import PaymentService
        yield PaymentService


@pytest.fixture()
def user_with_stripe(db_session, sample_user):
    """Sample user that already has a stripe_customer_id."""
    sample_user.stripe_customer_id = 'cus_test_abc'
    db_session.commit()
    return sample_user


@pytest.fixture()
def active_subscription(db_session, sample_user):
    """Create an active subscription for the sample user."""
    from app.models import Subscription
    sub = Subscription(
        user_id=sample_user.id,
        stripe_subscription_id='sub_test_123',
        plan_tier='plus',
        status='active',
        current_period_start=datetime.utcnow(),
        current_period_end=datetime.utcnow() + timedelta(days=30),
    )
    db_session.add(sub)
    db_session.commit()
    return sub


@pytest.fixture()
def credit_ledger_entries(db_session, sample_user):
    """Create several credit ledger entries with different expiry dates."""
    from app.models import CreditLedger, ServiceType, CreditSource
    old_credit = CreditLedger(
        user_id=sample_user.id,
        service_type=ServiceType.STOCK_ANALYSIS.value,
        source=CreditSource.SUBSCRIPTION.value,
        amount_initial=100,
        amount_remaining=50,
        expires_at=datetime.utcnow() + timedelta(days=5),  # oldest, expires soonest
    )
    new_credit = CreditLedger(
        user_id=sample_user.id,
        service_type=ServiceType.STOCK_ANALYSIS.value,
        source=CreditSource.SUBSCRIPTION.value,
        amount_initial=200,
        amount_remaining=200,
        expires_at=datetime.utcnow() + timedelta(days=25),
    )
    db_session.add_all([old_credit, new_credit])
    db_session.commit()
    return old_credit, new_credit


@pytest.fixture()
def expired_credit(db_session, sample_user):
    """Create an expired credit entry."""
    from app.models import CreditLedger, ServiceType, CreditSource
    credit = CreditLedger(
        user_id=sample_user.id,
        service_type=ServiceType.STOCK_ANALYSIS.value,
        source=CreditSource.SUBSCRIPTION.value,
        amount_initial=500,
        amount_remaining=500,
        expires_at=datetime.utcnow() - timedelta(days=1),  # already expired
    )
    db_session.add(credit)
    db_session.commit()
    return credit


# ===========================================================================
# 1. create_checkout_session
# ===========================================================================

class TestCreateCheckoutSession:

    def test_create_session_success(self, app, db_session, user_with_stripe, mock_stripe, payment_service):
        """Valid params produce a checkout session object."""
        with app.app_context():
            # Set up PRICES so the key is valid
            payment_service.PRICES['plus_monthly'] = 'price_plus_m'
            session, error = payment_service.create_checkout_session(
                user_id=user_with_stripe.id,
                price_key='plus_monthly',
                success_url='https://example.com/success',
                cancel_url='https://example.com/cancel',
            )
            assert error is None
            assert session is not None
            assert session.id == 'cs_test_session_1'
            mock_stripe.checkout.Session.create.assert_called_once()

    def test_create_session_existing_subscription(self, app, db_session, user_with_stripe,
                                                   active_subscription, mock_stripe, payment_service):
        """User with active subscription gets an error for subscription products."""
        with app.app_context():
            payment_service.PRICES['plus_monthly'] = 'price_plus_m'
            session, error = payment_service.create_checkout_session(
                user_id=user_with_stripe.id,
                price_key='plus_monthly',
                success_url='https://example.com/success',
                cancel_url='https://example.com/cancel',
            )
            assert session is None
            assert '已有活跃订阅' in error

    def test_create_session_lazy_user_creation(self, app, db_session, mock_stripe, payment_service):
        """Email provided but user does not exist -> creates user automatically."""
        with app.app_context():
            payment_service.PRICES['topup_100'] = 'price_topup'
            new_user_id = 'brand-new-user-uuid-9999'
            session, error = payment_service.create_checkout_session(
                user_id=new_user_id,
                price_key='topup_100',
                success_url='https://example.com/success',
                cancel_url='https://example.com/cancel',
                email='lazy@example.com',
            )
            assert error is None
            assert session is not None

            # Verify user was created in the database
            from app.models import User
            user = User.query.get(new_user_id)
            assert user is not None
            assert user.email == 'lazy@example.com'

    def test_create_session_invalid_price_key(self, app, db_session, user_with_stripe,
                                               mock_stripe, payment_service):
        """Unknown price key returns an error."""
        with app.app_context():
            session, error = payment_service.create_checkout_session(
                user_id=user_with_stripe.id,
                price_key='nonexistent_plan',
                success_url='https://example.com/success',
                cancel_url='https://example.com/cancel',
            )
            assert session is None
            assert '价格配置不存在' in error

    def test_create_session_no_stripe_key(self, app, db_session, user_with_stripe, payment_service):
        """Empty Stripe API key returns an error."""
        with app.app_context():
            with patch('app.services.payment_service.stripe') as mock_s:
                mock_s.api_key = ''
                session, error = payment_service.create_checkout_session(
                    user_id=user_with_stripe.id,
                    price_key='plus_monthly',
                    success_url='https://example.com/success',
                    cancel_url='https://example.com/cancel',
                )
                assert session is None
                assert 'Stripe未配置' in error


# ===========================================================================
# 2. check_and_deduct_credits
# ===========================================================================

class TestCheckAndDeductCredits:

    def test_deduct_free_quota_success(self, app, db_session, sample_user, payment_service):
        """Free user making first query of the day succeeds with free quota."""
        with app.app_context():
            from app.models import ServiceType
            success, msg, remaining, info = payment_service.check_and_deduct_credits(
                user_id=sample_user.id,
                service_type=ServiceType.STOCK_ANALYSIS.value,
                amount=1,
                ticker='AAPL',
            )
            assert success is True
            assert info['is_free'] is True
            assert info['free_remaining'] >= 0

    def test_deduct_free_quota_exhausted(self, app, db_session, sample_user,
                                         credit_ledger_entries, payment_service):
        """After 2 free queries, falls through to paid credits."""
        with app.app_context():
            from app.models import ServiceType, DailyQueryCount
            today = datetime.now().date()
            # Pre-fill 2 used queries (exhausts free quota of 2)
            dqc = DailyQueryCount(
                user_id=sample_user.id,
                date=today,
                query_count=2,
                reset_time=datetime.combine(today + timedelta(days=1), datetime.min.time()),
            )
            db_session.add(dqc)
            db_session.commit()

            success, msg, remaining, info = payment_service.check_and_deduct_credits(
                user_id=sample_user.id,
                service_type=ServiceType.STOCK_ANALYSIS.value,
                amount=1,
                ticker='TSLA',
            )
            # Should succeed using paid credits
            assert success is True
            assert info['is_free'] is False

    def test_deduct_paid_credits_fifo(self, app, db_session, sample_user,
                                       credit_ledger_entries, payment_service):
        """Uses oldest (soonest expiry) credit first (FIFO by expires_at ASC)."""
        with app.app_context():
            from app.models import ServiceType, DailyQueryCount, CreditLedger
            old_credit, new_credit = credit_ledger_entries

            # Exhaust free quota
            today = datetime.now().date()
            dqc = DailyQueryCount(
                user_id=sample_user.id,
                date=today,
                query_count=2,
                reset_time=datetime.combine(today + timedelta(days=1), datetime.min.time()),
            )
            db_session.add(dqc)
            db_session.commit()

            original_old_remaining = old_credit.amount_remaining

            success, msg, remaining, info = payment_service.check_and_deduct_credits(
                user_id=sample_user.id,
                service_type=ServiceType.STOCK_ANALYSIS.value,
                amount=1,
            )
            assert success is True

            # Re-query from DB (objects may be detached after service commit)
            refreshed_old = CreditLedger.query.get(old_credit.id)
            refreshed_new = CreditLedger.query.get(new_credit.id)
            assert refreshed_old.amount_remaining == original_old_remaining - 1
            assert refreshed_new.amount_remaining == 200  # untouched

    def test_deduct_skip_expired_credits(self, app, db_session, sample_user,
                                          expired_credit, payment_service):
        """Expired ledger entries are skipped; returns insufficient."""
        with app.app_context():
            from app.models import ServiceType, DailyQueryCount
            # Exhaust free quota
            today = datetime.now().date()
            dqc = DailyQueryCount(
                user_id=sample_user.id,
                date=today,
                query_count=2,
                reset_time=datetime.combine(today + timedelta(days=1), datetime.min.time()),
            )
            db_session.add(dqc)
            db_session.commit()

            success, msg, remaining, info = payment_service.check_and_deduct_credits(
                user_id=sample_user.id,
                service_type=ServiceType.STOCK_ANALYSIS.value,
                amount=1,
            )
            assert success is False
            assert '额度不足' in msg
            assert remaining == 0

    def test_deduct_insufficient_credits(self, app, db_session, sample_user, payment_service):
        """No free and no paid credits -> (False, msg, 0)."""
        with app.app_context():
            from app.models import ServiceType, DailyQueryCount
            # Exhaust free quota first
            today = datetime.now().date()
            dqc = DailyQueryCount(
                user_id=sample_user.id,
                date=today,
                query_count=2,
                reset_time=datetime.combine(today + timedelta(days=1), datetime.min.time()),
            )
            db_session.add(dqc)
            db_session.commit()

            success, msg, remaining, info = payment_service.check_and_deduct_credits(
                user_id=sample_user.id,
                service_type=ServiceType.STOCK_ANALYSIS.value,
                amount=1,
            )
            assert success is False
            assert remaining == 0

    def test_deduct_creates_usage_log(self, app, db_session, sample_user, payment_service):
        """A UsageLog record is created after successful deduction."""
        with app.app_context():
            from app.models import ServiceType, UsageLog
            payment_service.check_and_deduct_credits(
                user_id=sample_user.id,
                service_type=ServiceType.STOCK_ANALYSIS.value,
                amount=1,
                ticker='NVDA',
            )
            logs = UsageLog.query.filter_by(user_id=sample_user.id).all()
            assert len(logs) >= 1
            assert logs[0].ticker == 'NVDA'
            assert logs[0].amount_used == 1


# ===========================================================================
# 3. handle_invoice_payment_succeeded
# ===========================================================================

class TestHandleInvoicePaymentSucceeded:

    def _make_invoice(self, invoice_id='inv_new_001', subscription_id='sub_test_123',
                      billing_reason='subscription_create', amount_paid=999):
        return {
            'id': invoice_id,
            'subscription': subscription_id,
            'billing_reason': billing_reason,
            'amount_paid': amount_paid,
            'currency': 'usd',
        }

    def test_subscription_credit_allocation(self, app, db_session, sample_user,
                                             active_subscription, mock_stripe, payment_service):
        """invoice.payment_succeeded creates a Transaction and adds credits."""
        with app.app_context():
            invoice = self._make_invoice()
            success, msg = payment_service.handle_invoice_payment_succeeded(invoice)
            assert success is True

            from app.models import Transaction, CreditLedger
            txn = Transaction.query.filter_by(stripe_invoice_id='inv_new_001').first()
            assert txn is not None
            assert txn.status == 'succeeded'

            credits = CreditLedger.query.filter_by(user_id=sample_user.id).all()
            assert len(credits) >= 1

    def test_idempotency_check(self, app, db_session, sample_user, active_subscription,
                                mock_stripe, payment_service):
        """Duplicate invoice_id skips processing."""
        with app.app_context():
            invoice = self._make_invoice()
            # First call
            payment_service.handle_invoice_payment_succeeded(invoice)
            # Second call with same invoice
            success, msg = payment_service.handle_invoice_payment_succeeded(invoice)
            assert success is True
            assert '幂等性检查' in msg or '已处理' in msg

    def test_plus_monthly_1000_credits(self, app, db_session, sample_user,
                                        active_subscription, mock_stripe, payment_service):
        """Plus monthly subscription allocates 1000 credits."""
        with app.app_context():
            invoice = self._make_invoice()
            payment_service.handle_invoice_payment_succeeded(invoice)

            from app.models import CreditLedger, CreditSource
            credits = CreditLedger.query.filter_by(
                user_id=sample_user.id,
                source=CreditSource.SUBSCRIPTION.value,
            ).all()
            total = sum(c.amount_initial for c in credits)
            assert total == 1000

    def test_pro_yearly_60000_credits(self, app, db_session, sample_user, mock_stripe, payment_service):
        """Pro yearly subscription allocates 60000 credits."""
        with app.app_context():
            from app.models import Subscription
            # Create a pro subscription with a yearly period (> 60 days)
            sub = Subscription(
                user_id=sample_user.id,
                stripe_subscription_id='sub_pro_yearly_1',
                plan_tier='pro',
                status='active',
                current_period_start=datetime.utcnow(),
                current_period_end=datetime.utcnow() + timedelta(days=365),
            )
            db_session.add(sub)
            db_session.commit()

            # Adjust mock to return yearly period
            now_ts = int(datetime.utcnow().timestamp())
            end_ts = int((datetime.utcnow() + timedelta(days=365)).timestamp())
            yearly_sub_data = {
                'id': 'sub_pro_yearly_1',
                'status': 'active',
                'current_period_start': now_ts,
                'current_period_end': end_ts,
                'items': {'data': [{'id': 'si_item_pro', 'price': {'id': 'price_pro_y'}}]},
                'customer': 'cus_test_abc',
            }
            mock_sub_obj = MagicMock()
            mock_sub_obj.get = lambda k, d=None: yearly_sub_data.get(k, d)
            mock_sub_obj.__getitem__ = lambda s, k: yearly_sub_data[k]
            mock_stripe.Subscription.retrieve.return_value = mock_sub_obj

            invoice = self._make_invoice(
                invoice_id='inv_pro_yearly_1',
                subscription_id='sub_pro_yearly_1',
            )
            success, msg = payment_service.handle_invoice_payment_succeeded(invoice)
            assert success is True

            from app.models import CreditLedger, CreditSource
            credits = CreditLedger.query.filter_by(
                user_id=sample_user.id,
                source=CreditSource.SUBSCRIPTION.value,
            ).all()
            total = sum(c.amount_initial for c in credits)
            assert total == 60000

    def test_referral_bonus(self, app, db_session, mock_stripe, payment_service):
        """First subscription with referrer grants 100 bonus credits to referrer."""
        with app.app_context():
            from app.models import User, Subscription, CreditLedger, CreditSource

            # Create referrer
            referrer = User(id='referrer-uuid-1', email='referrer@example.com', username='referrer')
            db_session.add(referrer)
            db_session.commit()

            # Create referred user with referrer_id set
            referred = User(
                id='referred-uuid-1',
                email='referred@example.com',
                username='referred',
                referrer_id='referrer-uuid-1',
                stripe_customer_id='cus_referred',
            )
            db_session.add(referred)
            db_session.commit()

            sub = Subscription(
                user_id='referred-uuid-1',
                stripe_subscription_id='sub_referral_test',
                plan_tier='plus',
                status='active',
                current_period_start=datetime.utcnow(),
                current_period_end=datetime.utcnow() + timedelta(days=30),
            )
            db_session.add(sub)
            db_session.commit()

            invoice = self._make_invoice(
                invoice_id='inv_referral_1',
                subscription_id='sub_referral_test',
                billing_reason='subscription_create',
            )
            success, msg = payment_service.handle_invoice_payment_succeeded(invoice)
            assert success is True

            # Check referrer got 100 bonus credits
            referral_credits = CreditLedger.query.filter_by(
                user_id='referrer-uuid-1',
                source=CreditSource.REFERRAL.value,
            ).all()
            total_bonus = sum(c.amount_initial for c in referral_credits)
            assert total_bonus == 100

    def test_skip_update_billing_reason(self, app, db_session, sample_user,
                                         active_subscription, mock_stripe, payment_service):
        """subscription_update billing_reason is skipped."""
        with app.app_context():
            invoice = self._make_invoice(billing_reason='subscription_update')
            success, msg = payment_service.handle_invoice_payment_succeeded(invoice)
            assert success is True
            assert '升级' in msg or 'update' in msg.lower()


# ===========================================================================
# 4. upgrade_subscription
# ===========================================================================

class TestUpgradeSubscription:

    def test_upgrade_plus_to_pro(self, app, db_session, user_with_stripe,
                                  active_subscription, mock_stripe, payment_service):
        """Valid upgrade from plus_monthly to pro_monthly succeeds."""
        with app.app_context():
            payment_service.PRICES['pro_monthly'] = 'price_pro_m'
            result, error = payment_service.upgrade_subscription(
                user_id=user_with_stripe.id,
                new_price_key='pro_monthly',
            )
            assert error is None
            assert result is not None
            assert result['success'] is True
            assert result['new_plan'] == 'pro'
            assert result['credits_added'] == 5000

    def test_upgrade_no_subscription(self, app, db_session, sample_user,
                                      mock_stripe, payment_service):
        """User without active subscription gets an error."""
        with app.app_context():
            result, error = payment_service.upgrade_subscription(
                user_id=sample_user.id,
                new_price_key='pro_monthly',
            )
            assert result is None
            assert '没有活跃订阅' in error

    def test_downgrade_rejected(self, app, db_session, user_with_stripe, mock_stripe, payment_service):
        """Attempting to downgrade (lower tier) is rejected."""
        with app.app_context():
            from app.models import Subscription
            # Create a pro subscription
            sub = Subscription(
                user_id=user_with_stripe.id,
                stripe_subscription_id='sub_pro_999',
                plan_tier='pro',
                status='active',
                current_period_start=datetime.utcnow(),
                current_period_end=datetime.utcnow() + timedelta(days=30),
            )
            db_session.add(sub)
            db_session.commit()

            payment_service.PRICES['plus_monthly'] = 'price_plus_m'
            result, error = payment_service.upgrade_subscription(
                user_id=user_with_stripe.id,
                new_price_key='plus_monthly',
            )
            assert result is None
            assert '不支持降级' in error or '升级' in error


# ===========================================================================
# 5. cancel_subscription
# ===========================================================================

class TestCancelSubscription:

    def test_cancel_at_period_end(self, app, db_session, user_with_stripe,
                                   active_subscription, mock_stripe, payment_service):
        """Cancellation sets cancel_at_period_end=True."""
        with app.app_context():
            result, error = payment_service.cancel_subscription(user_id=user_with_stripe.id)
            assert error is None
            assert result is not None
            assert result['success'] is True
            mock_stripe.Subscription.modify.assert_called_once_with(
                active_subscription.stripe_subscription_id,
                cancel_at_period_end=True,
            )
            # Verify local record updated (re-query since object may be detached)
            from app.models import Subscription
            refreshed_sub = Subscription.query.filter_by(
                stripe_subscription_id=active_subscription.stripe_subscription_id
            ).first()
            assert refreshed_sub.cancel_at_period_end is True

    def test_cancel_no_subscription(self, app, db_session, sample_user, mock_stripe, payment_service):
        """User without subscription gets an error."""
        with app.app_context():
            result, error = payment_service.cancel_subscription(user_id=sample_user.id)
            assert result is None
            assert '没有活跃订阅' in error

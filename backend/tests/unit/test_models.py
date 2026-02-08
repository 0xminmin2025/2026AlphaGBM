"""
Unit tests for app/models.py

Tests all 18 models and 7 enums.
Uses SQLite in-memory database via the db_session fixture.
"""
import uuid
import pytest
from datetime import datetime, date, timedelta


# ---------------------------------------------------------------------------
# Enum tests
# ---------------------------------------------------------------------------

class TestServiceTypeEnum:
    def test_values(self):
        from app.models import ServiceType
        assert ServiceType.STOCK_ANALYSIS.value == 'stock_analysis'
        assert ServiceType.OPTION_ANALYSIS.value == 'option_analysis'
        assert ServiceType.DEEP_REPORT.value == 'deep_report'

    def test_member_count(self):
        from app.models import ServiceType
        assert len(ServiceType) == 3


class TestCreditSourceEnum:
    def test_values(self):
        from app.models import CreditSource
        assert CreditSource.SUBSCRIPTION.value == 'subscription'
        assert CreditSource.TOP_UP.value == 'top_up'
        assert CreditSource.REFERRAL.value == 'referral'
        assert CreditSource.SYSTEM_GRANT.value == 'system_grant'
        assert CreditSource.REFUND.value == 'refund'

    def test_member_count(self):
        from app.models import CreditSource
        assert len(CreditSource) == 5


class TestPlanTierEnum:
    def test_values(self):
        from app.models import PlanTier
        assert PlanTier.FREE.value == 'free'
        assert PlanTier.PLUS.value == 'plus'
        assert PlanTier.PRO.value == 'pro'

    def test_member_count(self):
        from app.models import PlanTier
        assert len(PlanTier) == 3


class TestSubscriptionStatusEnum:
    def test_values(self):
        from app.models import SubscriptionStatus
        assert SubscriptionStatus.ACTIVE.value == 'active'
        assert SubscriptionStatus.CANCELED.value == 'canceled'
        assert SubscriptionStatus.PAST_DUE.value == 'past_due'
        assert SubscriptionStatus.UNPAID.value == 'unpaid'
        assert SubscriptionStatus.TRIALING.value == 'trialing'

    def test_member_count(self):
        from app.models import SubscriptionStatus
        assert len(SubscriptionStatus) == 5


class TestTransactionStatusEnum:
    def test_values(self):
        from app.models import TransactionStatus
        assert TransactionStatus.PENDING.value == 'pending'
        assert TransactionStatus.SUCCEEDED.value == 'succeeded'
        assert TransactionStatus.FAILED.value == 'failed'

    def test_member_count(self):
        from app.models import TransactionStatus
        assert len(TransactionStatus) == 3


class TestTaskTypeEnum:
    def test_values(self):
        from app.models import TaskType
        assert TaskType.STOCK_ANALYSIS.value == 'stock_analysis'
        assert TaskType.OPTION_ANALYSIS.value == 'option_analysis'
        assert TaskType.ENHANCED_OPTION_ANALYSIS.value == 'enhanced_option_analysis'

    def test_member_count(self):
        from app.models import TaskType
        assert len(TaskType) == 3


class TestTaskStatusEnum:
    def test_values(self):
        from app.models import TaskStatus
        assert TaskStatus.PENDING.value == 'pending'
        assert TaskStatus.PROCESSING.value == 'processing'
        assert TaskStatus.COMPLETED.value == 'completed'
        assert TaskStatus.FAILED.value == 'failed'

    def test_member_count(self):
        from app.models import TaskStatus
        assert len(TaskStatus) == 4


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class TestUserModel:
    def test_create_user(self, db_session):
        from app.models import User
        user = User(
            id='user-001',
            email='alice@example.com',
            username='alice',
        )
        db_session.add(user)
        db_session.commit()

        fetched = User.query.filter_by(id='user-001').first()
        assert fetched is not None
        assert fetched.email == 'alice@example.com'
        assert fetched.username == 'alice'
        assert fetched.created_at is not None

    def test_email_uniqueness(self, db_session):
        from app.models import User
        u1 = User(id='u1', email='dup@example.com')
        u2 = User(id='u2', email='dup@example.com')
        db_session.add(u1)
        db_session.commit()

        db_session.add(u2)
        with pytest.raises(Exception):
            db_session.commit()
        db_session.rollback()

    def test_referral_relationship(self, db_session):
        from app.models import User
        referrer = User(id='ref-001', email='referrer@example.com')
        referee = User(id='ref-002', email='referee@example.com', referrer_id='ref-001')
        db_session.add_all([referrer, referee])
        db_session.commit()

        assert referee.referrer.id == 'ref-001'
        assert referrer.referrals[0].id == 'ref-002'

    def test_nullable_fields(self, db_session):
        from app.models import User
        user = User(id='u-null', email='null@example.com')
        db_session.add(user)
        db_session.commit()

        assert user.username is None
        assert user.last_login is None
        assert user.stripe_customer_id is None
        assert user.referrer_id is None


class TestAnalysisRequestModel:
    def test_create(self, db_session, sample_user):
        from app.models import AnalysisRequest
        req = AnalysisRequest(
            user_id=sample_user.id,
            ticker='AAPL',
            style='aggressive',
            status='success',
        )
        db_session.add(req)
        db_session.commit()

        assert req.id is not None
        assert req.ticker == 'AAPL'
        assert req.style == 'aggressive'
        assert req.status == 'success'
        assert req.created_at is not None

    def test_default_status(self, db_session, sample_user):
        from app.models import AnalysisRequest
        req = AnalysisRequest(
            user_id=sample_user.id,
            ticker='TSLA',
            style='moderate',
        )
        db_session.add(req)
        db_session.commit()

        assert req.status == 'success'

    def test_error_message_nullable(self, db_session, sample_user):
        from app.models import AnalysisRequest
        req = AnalysisRequest(
            user_id=sample_user.id,
            ticker='GOOG',
            style='conservative',
            status='failed',
            error_message='Data not found',
        )
        db_session.add(req)
        db_session.commit()
        assert req.error_message == 'Data not found'


class TestFeedbackModel:
    def test_create(self, db_session, sample_user):
        from app.models import Feedback
        fb = Feedback(
            user_id=sample_user.id,
            type='bug',
            content='Something is broken',
            ticker='AAPL',
            ip_address='127.0.0.1',
        )
        db_session.add(fb)
        db_session.commit()

        assert fb.id is not None
        assert fb.type == 'bug'
        assert fb.content == 'Something is broken'
        assert fb.submitted_at is not None


class TestDailyQueryCountModel:
    def test_create_with_defaults(self, db_session, sample_user):
        from app.models import DailyQueryCount
        dqc = DailyQueryCount(
            user_id=sample_user.id,
            date=date.today(),
        )
        db_session.add(dqc)
        db_session.commit()

        assert dqc.query_count == 0
        assert dqc.max_queries == 5

    def test_default_reset_time(self, db_session, sample_user):
        from app.models import DailyQueryCount, default_reset_time
        reset = default_reset_time()
        today = datetime.utcnow().date()
        tomorrow = datetime.combine(today + timedelta(days=1), datetime.min.time())
        assert reset == tomorrow

    def test_reset_time_auto_populated(self, db_session, sample_user):
        from app.models import DailyQueryCount
        dqc = DailyQueryCount(
            user_id=sample_user.id,
            date=date.today(),
        )
        db_session.add(dqc)
        db_session.commit()

        # reset_time should be set via the default_reset_time callable
        assert dqc.reset_time is not None
        assert dqc.reset_time.hour == 0
        assert dqc.reset_time.minute == 0


class TestPortfolioHoldingModel:
    def test_create(self, db_session):
        from app.models import PortfolioHolding
        h = PortfolioHolding(
            ticker='AAPL',
            name='Apple Inc',
            shares=100,
            buy_price=150.0,
            style='growth',
            currency='USD',
        )
        db_session.add(h)
        db_session.commit()

        assert h.id is not None
        assert h.ticker == 'AAPL'
        assert h.shares == 100
        assert h.buy_price == 150.0
        assert h.currency == 'USD'
        assert h.created_at is not None
        assert h.updated_at is not None


class TestDailyProfitLossModel:
    def test_create(self, db_session):
        from app.models import DailyProfitLoss
        dpl = DailyProfitLoss(
            trading_date=date.today(),
            total_actual_investment=10000.0,
            total_market_value=10500.0,
            total_profit_loss=500.0,
            total_profit_loss_percent=5.0,
        )
        db_session.add(dpl)
        db_session.commit()

        assert dpl.id is not None
        assert dpl.total_profit_loss == 500.0
        assert dpl.created_at is not None


class TestStyleProfitModel:
    def test_create(self, db_session):
        from app.models import StyleProfit
        sp = StyleProfit(
            trading_date=date.today(),
            style='value',
            style_investment=5000.0,
            style_market_value=5300.0,
            style_profit_loss=300.0,
            style_profit_loss_percent=6.0,
        )
        db_session.add(sp)
        db_session.commit()

        assert sp.id is not None
        assert sp.style == 'value'
        assert sp.style_profit_loss_percent == 6.0


class TestPortfolioRebalanceModel:
    def test_create_with_json_fields(self, db_session):
        from app.models import PortfolioRebalance
        changes = {
            'added': [{'ticker': 'MSFT', 'name': 'Microsoft', 'shares': 50, 'buy_price': 400.0, 'style': 'growth'}],
            'removed': [{'ticker': 'IBM', 'name': 'IBM', 'shares': 20, 'style': 'value'}],
            'adjusted': [],
        }
        style_stats = {
            'growth': {'investment': 20000, 'market_value': 21000, 'profit_loss': 1000, 'profit_loss_percent': 5.0}
        }

        rebal = PortfolioRebalance(
            rebalance_date=date.today(),
            rebalance_number=1,
            holdings_added=1,
            holdings_removed=1,
            holdings_adjusted=0,
            total_investment=50000.0,
            total_market_value=52000.0,
            total_profit_loss=2000.0,
            total_profit_loss_percent=4.0,
            style_stats=style_stats,
            changes_detail=changes,
            notes='Quarterly rebalance',
        )
        db_session.add(rebal)
        db_session.commit()

        fetched = PortfolioRebalance.query.first()
        assert fetched.changes_detail['added'][0]['ticker'] == 'MSFT'
        assert fetched.style_stats['growth']['investment'] == 20000
        assert fetched.notes == 'Quarterly rebalance'


class TestSubscriptionModel:
    def test_create(self, db_session, sample_user):
        from app.models import Subscription
        sub = Subscription(
            user_id=sample_user.id,
            stripe_subscription_id='sub_unique_123',
            plan_tier='plus',
            status='active',
        )
        db_session.add(sub)
        db_session.commit()

        assert sub.id is not None
        assert sub.plan_tier == 'plus'
        assert sub.cancel_at_period_end is False

    def test_stripe_subscription_id_unique(self, db_session, sample_user):
        from app.models import Subscription
        s1 = Subscription(
            user_id=sample_user.id,
            stripe_subscription_id='sub_dup_001',
            plan_tier='plus',
            status='active',
        )
        s2 = Subscription(
            user_id=sample_user.id,
            stripe_subscription_id='sub_dup_001',
            plan_tier='pro',
            status='active',
        )
        db_session.add(s1)
        db_session.commit()

        db_session.add(s2)
        with pytest.raises(Exception):
            db_session.commit()
        db_session.rollback()


class TestTransactionModel:
    def test_create(self, db_session, sample_user):
        from app.models import Transaction
        txn = Transaction(
            user_id=sample_user.id,
            stripe_payment_intent_id='pi_unique_001',
            amount=9900,
            currency='cny',
            status='succeeded',
            description='Test payment',
        )
        db_session.add(txn)
        db_session.commit()

        assert txn.id is not None
        assert txn.amount == 9900
        assert txn.currency == 'cny'

    def test_payment_intent_unique(self, db_session, sample_user):
        from app.models import Transaction
        t1 = Transaction(
            user_id=sample_user.id,
            stripe_payment_intent_id='pi_dup',
            amount=100,
            currency='usd',
            status='succeeded',
        )
        t2 = Transaction(
            user_id=sample_user.id,
            stripe_payment_intent_id='pi_dup',
            amount=200,
            currency='usd',
            status='pending',
        )
        db_session.add(t1)
        db_session.commit()

        db_session.add(t2)
        with pytest.raises(Exception):
            db_session.commit()
        db_session.rollback()

    def test_checkout_session_unique(self, db_session, sample_user):
        from app.models import Transaction
        t1 = Transaction(
            user_id=sample_user.id,
            stripe_checkout_session_id='cs_dup',
            amount=100,
            currency='usd',
            status='succeeded',
        )
        t2 = Transaction(
            user_id=sample_user.id,
            stripe_checkout_session_id='cs_dup',
            amount=200,
            currency='usd',
            status='pending',
        )
        db_session.add(t1)
        db_session.commit()

        db_session.add(t2)
        with pytest.raises(Exception):
            db_session.commit()
        db_session.rollback()

    def test_invoice_id_unique(self, db_session, sample_user):
        from app.models import Transaction
        t1 = Transaction(
            user_id=sample_user.id,
            stripe_invoice_id='inv_dup',
            amount=100,
            currency='usd',
            status='succeeded',
        )
        t2 = Transaction(
            user_id=sample_user.id,
            stripe_invoice_id='inv_dup',
            amount=200,
            currency='usd',
            status='pending',
        )
        db_session.add(t1)
        db_session.commit()

        db_session.add(t2)
        with pytest.raises(Exception):
            db_session.commit()
        db_session.rollback()


class TestCreditLedgerModel:
    def test_create_with_expiry(self, db_session, sample_user):
        from app.models import CreditLedger, ServiceType, CreditSource
        expires = datetime.utcnow() + timedelta(days=30)
        ledger = CreditLedger(
            user_id=sample_user.id,
            service_type=ServiceType.STOCK_ANALYSIS.value,
            source=CreditSource.SUBSCRIPTION.value,
            amount_initial=1000,
            amount_remaining=1000,
            expires_at=expires,
        )
        db_session.add(ledger)
        db_session.commit()

        assert ledger.id is not None
        assert ledger.amount_initial == 1000
        assert ledger.expires_at is not None

    def test_create_without_expiry(self, db_session, sample_user):
        from app.models import CreditLedger
        ledger = CreditLedger(
            user_id=sample_user.id,
            service_type='stock_analysis',
            source='system_grant',
            amount_initial=50,
            amount_remaining=50,
            expires_at=None,
        )
        db_session.add(ledger)
        db_session.commit()

        assert ledger.expires_at is None


class TestUsageLogModel:
    def test_create_linked_to_credit_ledger(self, db_session, sample_user):
        from app.models import CreditLedger, UsageLog
        ledger = CreditLedger(
            user_id=sample_user.id,
            service_type='stock_analysis',
            source='subscription',
            amount_initial=100,
            amount_remaining=99,
        )
        db_session.add(ledger)
        db_session.commit()

        log = UsageLog(
            user_id=sample_user.id,
            credit_ledger_id=ledger.id,
            service_type='stock_analysis',
            ticker='AAPL',
            amount_used=1,
        )
        db_session.add(log)
        db_session.commit()

        assert log.id is not None
        assert log.credit_ledger_id == ledger.id

    def test_create_without_ledger(self, db_session, sample_user):
        from app.models import UsageLog
        log = UsageLog(
            user_id=sample_user.id,
            service_type='option_analysis',
            amount_used=1,
        )
        db_session.add(log)
        db_session.commit()

        assert log.credit_ledger_id is None


class TestStockAnalysisHistoryModel:
    def test_create_with_json(self, db_session, sample_user):
        from app.models import StockAnalysisHistory
        full_data = {
            'risk': {'score': 0.7, 'level': 'medium'},
            'ev': {'weighted_pct': 0.15},
        }
        hist = StockAnalysisHistory(
            user_id=sample_user.id,
            ticker='MSFT',
            style='balanced',
            current_price=400.0,
            target_price=450.0,
            risk_score=0.7,
            risk_level='medium',
            ev_score=0.8,
            recommendation_action='buy',
            recommendation_confidence='high',
            full_analysis_data=full_data,
        )
        db_session.add(hist)
        db_session.commit()

        fetched = StockAnalysisHistory.query.first()
        assert fetched.full_analysis_data['risk']['level'] == 'medium'
        assert fetched.ticker == 'MSFT'


class TestOptionsAnalysisHistoryModel:
    def test_create_with_json(self, db_session, sample_user):
        from app.models import OptionsAnalysisHistory
        vrp = {'iv': 0.35, 'hv': 0.28, 'vrp': 0.07}
        risk = {'max_loss': -500, 'probability': 0.3}
        hist = OptionsAnalysisHistory(
            user_id=sample_user.id,
            symbol='AAPL',
            analysis_type='enhanced_analysis',
            option_identifier='AAPL240119C00180000',
            expiry_date='2024-01-19',
            vrp_analysis=vrp,
            risk_analysis=risk,
            full_analysis_data={'chain': 'data'},
        )
        db_session.add(hist)
        db_session.commit()

        fetched = OptionsAnalysisHistory.query.first()
        assert fetched.vrp_analysis['vrp'] == 0.07
        assert fetched.analysis_type == 'enhanced_analysis'


class TestAnalysisTaskModel:
    def test_create(self, db_session, sample_user):
        from app.models import AnalysisTask
        task_id = str(uuid.uuid4())
        task = AnalysisTask(
            id=task_id,
            user_id=sample_user.id,
            task_type='stock_analysis',
            status='pending',
            priority=100,
            input_params={'ticker': 'GOOG', 'style': 'growth'},
        )
        db_session.add(task)
        db_session.commit()

        assert task.id == task_id
        assert task.progress_percent == 0

    def test_to_dict(self, db_session, sample_user):
        from app.models import AnalysisTask
        now = datetime.utcnow()
        task_id = str(uuid.uuid4())
        task = AnalysisTask(
            id=task_id,
            user_id=sample_user.id,
            task_type='option_analysis',
            status='completed',
            priority=50,
            input_params={'symbol': 'TSLA'},
            progress_percent=100,
            current_step='Done',
            result_data={'recommendation': 'sell'},
            error_message=None,
            created_at=now,
            started_at=now,
            completed_at=now,
            related_history_id=42,
            related_history_type='options',
        )
        db_session.add(task)
        db_session.commit()

        d = task.to_dict()
        assert d['id'] == task_id
        assert d['user_id'] == sample_user.id
        assert d['task_type'] == 'option_analysis'
        assert d['status'] == 'completed'
        assert d['progress_percent'] == 100
        assert d['current_step'] == 'Done'
        assert d['input_params'] == {'symbol': 'TSLA'}
        assert d['result_data'] == {'recommendation': 'sell'}
        assert d['error_message'] is None
        assert d['created_at'] == now.isoformat()
        assert d['started_at'] == now.isoformat()
        assert d['completed_at'] == now.isoformat()
        assert d['related_history_id'] == 42
        assert d['related_history_type'] == 'options'

    def test_to_dict_none_timestamps(self, db_session, sample_user):
        from app.models import AnalysisTask
        task = AnalysisTask(
            id=str(uuid.uuid4()),
            user_id=sample_user.id,
            task_type='stock_analysis',
            input_params={},
        )
        db_session.add(task)
        db_session.commit()

        d = task.to_dict()
        assert d['started_at'] is None
        assert d['completed_at'] is None


class TestDailyRecommendationModel:
    def test_create(self, db_session):
        from app.models import DailyRecommendation
        rec = DailyRecommendation(
            recommendation_date=date.today(),
            recommendations=[{'ticker': 'AAPL', 'score': 8.5}],
            market_summary={'trend': 'bullish'},
        )
        db_session.add(rec)
        db_session.commit()

        assert rec.id is not None
        assert rec.recommendations[0]['ticker'] == 'AAPL'

    def test_unique_date_constraint(self, db_session):
        from app.models import DailyRecommendation
        today = date.today()
        r1 = DailyRecommendation(
            recommendation_date=today,
            recommendations=[],
        )
        r2 = DailyRecommendation(
            recommendation_date=today,
            recommendations=[],
        )
        db_session.add(r1)
        db_session.commit()

        db_session.add(r2)
        with pytest.raises(Exception):
            db_session.commit()
        db_session.rollback()


class TestDailyAnalysisCacheModel:
    def test_create(self, db_session):
        from app.models import DailyAnalysisCache
        cache = DailyAnalysisCache(
            ticker='AAPL',
            style='growth',
            analysis_date=date.today(),
            full_analysis_data={'result': 'cached'},
            source_task_id='task-uuid-001',
        )
        db_session.add(cache)
        db_session.commit()

        assert cache.id is not None
        assert cache.to_dict()['ticker'] == 'AAPL'

    def test_unique_constraint_ticker_style_date(self, db_session):
        from app.models import DailyAnalysisCache
        today = date.today()
        c1 = DailyAnalysisCache(
            ticker='MSFT', style='value', analysis_date=today,
            full_analysis_data={},
        )
        c2 = DailyAnalysisCache(
            ticker='MSFT', style='value', analysis_date=today,
            full_analysis_data={},
        )
        db_session.add(c1)
        db_session.commit()

        db_session.add(c2)
        with pytest.raises(Exception):
            db_session.commit()
        db_session.rollback()

    def test_different_style_same_day_ok(self, db_session):
        from app.models import DailyAnalysisCache
        today = date.today()
        c1 = DailyAnalysisCache(
            ticker='MSFT', style='value', analysis_date=today,
            full_analysis_data={},
        )
        c2 = DailyAnalysisCache(
            ticker='MSFT', style='growth', analysis_date=today,
            full_analysis_data={},
        )
        db_session.add_all([c1, c2])
        db_session.commit()

        assert DailyAnalysisCache.query.count() == 2


class TestAnalyticsEventModel:
    def test_create(self, db_session, sample_user):
        from app.models import AnalyticsEvent
        # BigInteger PK requires explicit id on SQLite (no autoincrement for BigInteger)
        event = AnalyticsEvent(
            id=1,
            event_type='page_view',
            session_id='sess-001',
            user_id=sample_user.id,
            user_tier='free',
            properties={'page': '/dashboard'},
            url='https://app.example.com/dashboard',
            referrer='https://google.com',
        )
        db_session.add(event)
        db_session.commit()

        assert event.id == 1
        assert event.event_type == 'page_view'
        assert event.properties['page'] == '/dashboard'
        assert event.created_at is not None

    def test_nullable_user_id(self, db_session):
        from app.models import AnalyticsEvent
        event = AnalyticsEvent(
            id=2,
            event_type='landing_view',
            session_id='sess-anon',
            user_id=None,
            user_tier='guest',
        )
        db_session.add(event)
        db_session.commit()

        assert event.user_id is None

    def test_composite_indexes_exist(self, db_session):
        """Verify the table_args composite indexes are defined."""
        from app.models import AnalyticsEvent
        table_args = AnalyticsEvent.__table_args__
        index_names = {idx.name for idx in table_args if hasattr(idx, 'name')}
        assert 'idx_analytics_type_date' in index_names
        assert 'idx_analytics_user_date' in index_names

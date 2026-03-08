"""
Unit tests for app/utils/decorators.py

Tests check_quota and db_retry decorators.
All external dependencies (Supabase, PaymentService, Stripe) are mocked.
Uses SQLite in-memory database.
"""
import json
import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.exc import OperationalError, DisconnectionError


# ---------------------------------------------------------------------------
# check_quota decorator
# ---------------------------------------------------------------------------

class TestCheckQuotaFreeUserSuccess:
    """Free quota available -- request should pass through."""

    def test_check_quota_free_user_success(self, app, client, db_session, sample_user):
        from app.utils.decorators import check_quota
        from app.models import ServiceType

        @app.route('/test-quota-free-ok', methods=['POST'])
        @check_quota(service_type=ServiceType.STOCK_ANALYSIS.value)
        def protected():
            from flask import g
            return {'user_id': g.user_id, 'quota_info': g.quota_info}

        mock_supa_user = MagicMock()
        mock_supa_user.id = sample_user.id
        mock_supa_user.email = sample_user.email
        mock_response = MagicMock()
        mock_response.user = mock_supa_user

        mock_supa_client = MagicMock()
        mock_supa_client.auth.get_user.return_value = mock_response

        payment_return = (True, 'Free quota used', 0, {
            'is_free': True, 'free_remaining': 1, 'free_quota': 2, 'free_used': 1
        })

        with patch('app.utils.decorators.supabase', mock_supa_client), \
             patch('app.utils.decorators.PaymentService') as MockPS:
            MockPS.check_and_deduct_credits.return_value = payment_return
            resp = client.post('/test-quota-free-ok',
                               data=json.dumps({'ticker': 'AAPL'}),
                               content_type='application/json',
                               headers={'Authorization': 'Bearer qt-free-ok'})

        assert resp.status_code == 200
        data = resp.get_json()
        assert data['quota_info']['is_free'] is True


class TestCheckQuotaFreeExhaustedPaidAvailable:
    """Free quota exhausted but paid credits available -- should still pass."""

    def test_check_quota_free_exhausted_paid_available(self, app, client, db_session, sample_user):
        from app.utils.decorators import check_quota
        from app.models import ServiceType

        @app.route('/test-quota-paid-ok', methods=['POST'])
        @check_quota(service_type=ServiceType.STOCK_ANALYSIS.value)
        def protected():
            from flask import g
            return {'user_id': g.user_id}

        mock_supa_user = MagicMock()
        mock_supa_user.id = sample_user.id
        mock_supa_user.email = sample_user.email
        mock_response = MagicMock()
        mock_response.user = mock_supa_user

        mock_supa_client = MagicMock()
        mock_supa_client.auth.get_user.return_value = mock_response

        payment_return = (True, 'Paid credits used', 99, {
            'is_free': False, 'free_remaining': 0, 'free_quota': 2, 'free_used': 0
        })

        with patch('app.utils.decorators.supabase', mock_supa_client), \
             patch('app.utils.decorators.PaymentService') as MockPS:
            MockPS.check_and_deduct_credits.return_value = payment_return
            resp = client.post('/test-quota-paid-ok',
                               data=json.dumps({'ticker': 'MSFT'}),
                               content_type='application/json',
                               headers={'Authorization': 'Bearer qt-paid-ok'})

        assert resp.status_code == 200


class TestCheckQuotaInsufficientCredits:
    """No free and no paid credits -- should return 402."""

    def test_check_quota_insufficient_credits(self, app, client, db_session, sample_user):
        from app.utils.decorators import check_quota
        from app.models import ServiceType

        @app.route('/test-quota-402', methods=['POST'])
        @check_quota(service_type=ServiceType.STOCK_ANALYSIS.value)
        def protected():
            return {'ok': True}

        mock_supa_user = MagicMock()
        mock_supa_user.id = sample_user.id
        mock_supa_user.email = sample_user.email
        mock_response = MagicMock()
        mock_response.user = mock_supa_user

        mock_supa_client = MagicMock()
        mock_supa_client.auth.get_user.return_value = mock_response

        payment_return = (False, 'Insufficient credits', 0, {
            'is_free': False, 'free_remaining': 0, 'free_quota': 2
        })

        with patch('app.utils.decorators.supabase', mock_supa_client), \
             patch('app.utils.decorators.PaymentService') as MockPS:
            MockPS.check_and_deduct_credits.return_value = payment_return
            resp = client.post('/test-quota-402',
                               data=json.dumps({'ticker': 'GOOG'}),
                               content_type='application/json',
                               headers={'Authorization': 'Bearer qt-402'})

        assert resp.status_code == 402
        data = resp.get_json()
        assert data['code'] == 'INSUFFICIENT_CREDITS'


class TestCheckQuotaExtractsTickerFromJSON:
    """The decorator should extract 'ticker' from JSON body."""

    def test_check_quota_extracts_ticker_from_json(self, app, client, db_session, sample_user):
        from app.utils.decorators import check_quota
        from app.models import ServiceType

        @app.route('/test-quota-json-ticker', methods=['POST'])
        @check_quota(service_type=ServiceType.STOCK_ANALYSIS.value)
        def protected():
            return {'ok': True}

        mock_supa_user = MagicMock()
        mock_supa_user.id = sample_user.id
        mock_supa_user.email = sample_user.email
        mock_response = MagicMock()
        mock_response.user = mock_supa_user

        mock_supa_client = MagicMock()
        mock_supa_client.auth.get_user.return_value = mock_response

        payment_return = (True, 'ok', 10, {
            'is_free': True, 'free_remaining': 1, 'free_quota': 2, 'free_used': 1
        })

        with patch('app.utils.decorators.supabase', mock_supa_client), \
             patch('app.utils.decorators.PaymentService') as MockPS:
            MockPS.check_and_deduct_credits.return_value = payment_return
            resp = client.post('/test-quota-json-ticker',
                               data=json.dumps({'ticker': 'NVDA'}),
                               content_type='application/json',
                               headers={'Authorization': 'Bearer qt-json'})

        assert resp.status_code == 200
        # Verify PaymentService was called with the ticker
        call_kwargs = MockPS.check_and_deduct_credits.call_args
        assert call_kwargs[1].get('ticker') == 'NVDA' or call_kwargs[0][3] == 'NVDA' if len(call_kwargs[0]) > 3 else call_kwargs[1].get('ticker') == 'NVDA'


class TestCheckQuotaExtractsTickerFromURL:
    """The decorator should extract 'symbol' from URL view_args."""

    def test_check_quota_extracts_ticker_from_url(self, app, client, db_session, sample_user):
        from app.utils.decorators import check_quota
        from app.models import ServiceType

        @app.route('/test-quota-url/<symbol>', methods=['GET'])
        @check_quota(service_type=ServiceType.OPTION_ANALYSIS.value)
        def protected(symbol):
            return {'symbol': symbol}

        mock_supa_user = MagicMock()
        mock_supa_user.id = sample_user.id
        mock_supa_user.email = sample_user.email
        mock_response = MagicMock()
        mock_response.user = mock_supa_user

        mock_supa_client = MagicMock()
        mock_supa_client.auth.get_user.return_value = mock_response

        payment_return = (True, 'ok', 5, {
            'is_free': True, 'free_remaining': 1, 'free_quota': 2, 'free_used': 1
        })

        with patch('app.utils.decorators.supabase', mock_supa_client), \
             patch('app.utils.decorators.PaymentService') as MockPS:
            MockPS.check_and_deduct_credits.return_value = payment_return
            resp = client.get('/test-quota-url/TSLA',
                              headers={'Authorization': 'Bearer qt-url'})

        assert resp.status_code == 200
        assert resp.get_json()['symbol'] == 'TSLA'


# ---------------------------------------------------------------------------
# db_retry decorator
# ---------------------------------------------------------------------------

class TestDbRetrySuccessFirstAttempt:
    """No error -- function returns normally on first attempt."""

    def test_db_retry_success_first_attempt(self, app):
        from app.utils.decorators import db_retry

        @db_retry(max_retries=3, retry_delay=0.01)
        def no_error():
            return 'success'

        with app.app_context():
            result = no_error()
        assert result == 'success'


class TestDbRetryRecoverableError:
    """SSL/connection error should be retried and eventually succeed."""

    def test_db_retry_recoverable_error(self, app):
        from app.utils.decorators import db_retry

        call_count = 0

        @db_retry(max_retries=3, retry_delay=0.01)
        def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                # Simulate a recoverable OperationalError
                raise OperationalError(
                    statement='SELECT 1',
                    params={},
                    orig=Exception('SSL connection has been closed unexpectedly'),
                )
            return 'recovered'

        with app.app_context():
            with patch('time.sleep'):
                result = flaky()

        assert result == 'recovered'
        assert call_count == 3


class TestDbRetryExhausted:
    """All retries fail -- should return 503."""

    def test_db_retry_exhausted(self, app):
        from app.utils.decorators import db_retry

        @db_retry(max_retries=2, retry_delay=0.01)
        def always_fail():
            raise OperationalError(
                statement='SELECT 1',
                params={},
                orig=Exception('SSL connection timeout'),
            )

        with app.app_context():
            with patch('time.sleep'):
                result = always_fail()

        # db_retry returns (jsonify(...), 503) tuple
        assert isinstance(result, tuple)
        resp, status_code = result
        assert status_code == 503


class TestDbRetryNonRecoverable:
    """Non-connection OperationalError should be re-raised immediately."""

    def test_db_retry_non_recoverable(self, app):
        from app.utils.decorators import db_retry

        @db_retry(max_retries=3, retry_delay=0.01)
        def bad_sql():
            raise OperationalError(
                statement='SELECT * FROM nonexistent',
                params={},
                orig=Exception('relation "nonexistent" does not exist'),
            )

        with app.app_context():
            with pytest.raises(OperationalError):
                bad_sql()

    def test_db_retry_non_database_error(self, app):
        """Non-database exceptions should be re-raised without retry."""
        from app.utils.decorators import db_retry

        @db_retry(max_retries=3, retry_delay=0.01)
        def value_error():
            raise ValueError('bad value')

        with app.app_context():
            with pytest.raises(ValueError, match='bad value'):
                value_error()

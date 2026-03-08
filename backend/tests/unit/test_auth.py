"""
Unit tests for app/utils/auth.py

All Supabase interactions are mocked. Uses SQLite in-memory database.
"""
import time
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime


class TestRequireAuthNoHeader:
    """Missing Authorization header should return 401."""

    def test_require_auth_no_header(self, app, client, db_session):
        from app.utils.auth import require_auth

        @app.route('/test-auth-no-header')
        @require_auth
        def protected():
            return {'ok': True}

        resp = client.get('/test-auth-no-header')
        assert resp.status_code == 401
        assert 'Missing Authorization header' in resp.get_json()['error']


class TestRequireAuthInvalidFormat:
    """Authorization header without 'Bearer <token>' format should return 401."""

    def test_require_auth_invalid_format(self, app, client, db_session):
        from app.utils.auth import require_auth

        @app.route('/test-auth-bad-format')
        @require_auth
        def protected():
            return {'ok': True}

        resp = client.get('/test-auth-bad-format',
                          headers={'Authorization': 'InvalidHeader'})
        assert resp.status_code == 401
        assert 'Invalid Authorization header format' in resp.get_json()['error']


class TestRequireAuthCacheHit:
    """When the token is already cached, Supabase should NOT be called."""

    def test_require_auth_cache_hit(self, app, client, db_session, sample_user):
        from app.utils import auth as auth_module
        from app.utils.auth import require_auth, token_cache

        # Pre-populate the cache
        mock_user = MagicMock()
        mock_user.id = sample_user.id
        mock_user.email = sample_user.email
        token_cache['cached-token-abc'] = {
            'user_data': mock_user,
            'expires_at': time.time() + 300,
        }

        @app.route('/test-auth-cache-hit')
        @require_auth
        def protected():
            from flask import g
            return {'user_id': g.user_id}

        with patch.object(auth_module, 'supabase') as mock_supa:
            # Supabase client must exist (non-falsy) for the decorator to proceed
            mock_supa.__bool__ = lambda self: True
            resp = client.get('/test-auth-cache-hit',
                              headers={'Authorization': 'Bearer cached-token-abc'})

        assert resp.status_code == 200
        assert resp.get_json()['user_id'] == sample_user.id

        # Cleanup
        token_cache.pop('cached-token-abc', None)


class TestRequireAuthCacheMiss:
    """On cache miss the decorator must call Supabase, cache the result, and proceed."""

    def test_require_auth_cache_miss(self, app, client, db_session, sample_user,
                                     mock_supabase_auth):
        from app.utils import auth as auth_module
        from app.utils.auth import require_auth, token_cache

        @app.route('/test-auth-cache-miss')
        @require_auth
        def protected():
            from flask import g
            return {'user_id': g.user_id}

        mock_supa = MagicMock()
        mock_supa.auth.get_user.return_value = mock_supabase_auth

        with patch.object(auth_module, 'supabase', mock_supa):
            resp = client.get('/test-auth-cache-miss',
                              headers={'Authorization': 'Bearer new-token-xyz'})

        assert resp.status_code == 200
        assert resp.get_json()['user_id'] == sample_user.id
        # Verify it was cached
        assert 'new-token-xyz' in token_cache

        # Cleanup
        token_cache.pop('new-token-xyz', None)


class TestRequireAuthInvalidToken:
    """Supabase returning no user should yield 401."""

    def test_require_auth_invalid_token(self, app, client, db_session):
        from app.utils import auth as auth_module
        from app.utils.auth import require_auth

        @app.route('/test-auth-invalid-token')
        @require_auth
        def protected():
            return {'ok': True}

        mock_supa = MagicMock()
        mock_response = MagicMock()
        mock_response.user = None
        mock_supa.auth.get_user.return_value = mock_response

        with patch.object(auth_module, 'supabase', mock_supa):
            resp = client.get('/test-auth-invalid-token',
                              headers={'Authorization': 'Bearer bad-token'})

        assert resp.status_code == 401


class TestRequireAuthAutoCreatesUser:
    """When the Supabase user does not exist in local DB, it should be auto-created."""

    def test_require_auth_auto_creates_user(self, app, client, db_session):
        from app.utils import auth as auth_module
        from app.utils.auth import require_auth, token_cache
        from app.models import User

        new_id = 'brand-new-user-id'
        new_email = 'newuser@example.com'

        @app.route('/test-auth-auto-create')
        @require_auth
        def protected():
            from flask import g
            return {'user_id': g.user_id}

        mock_user = MagicMock()
        mock_user.id = new_id
        mock_user.email = new_email
        mock_response = MagicMock()
        mock_response.user = mock_user

        mock_supa = MagicMock()
        mock_supa.auth.get_user.return_value = mock_response

        with patch.object(auth_module, 'supabase', mock_supa):
            resp = client.get('/test-auth-auto-create',
                              headers={'Authorization': 'Bearer create-token'})

        assert resp.status_code == 200
        created = User.query.filter_by(id=new_id).first()
        assert created is not None
        assert created.email == new_email

        # Cleanup
        token_cache.pop('create-token', None)


class TestRequireAuthUpdatesLastLogin:
    """On cache miss for an existing user, last_login should be updated."""

    def test_require_auth_updates_last_login(self, app, client, db_session, sample_user,
                                             mock_supabase_auth):
        from app.utils import auth as auth_module
        from app.utils.auth import require_auth, token_cache

        # Ensure the user has no last_login
        sample_user.last_login = None
        db_session.commit()

        @app.route('/test-auth-last-login')
        @require_auth
        def protected():
            return {'ok': True}

        mock_supa = MagicMock()
        mock_supa.auth.get_user.return_value = mock_supabase_auth

        with patch.object(auth_module, 'supabase', mock_supa):
            resp = client.get('/test-auth-last-login',
                              headers={'Authorization': 'Bearer login-token'})

        assert resp.status_code == 200
        from app.models import User
        updated_user = User.query.filter_by(id=sample_user.id).first()
        assert updated_user.last_login is not None

        # Cleanup
        token_cache.pop('login-token', None)


class TestRequireAuthRetryOnNetworkError:
    """SSL/connection errors should be retried before failing."""

    def test_require_auth_retry_on_network_error(self, app, client, db_session,
                                                  sample_user, mock_supabase_auth):
        from app.utils import auth as auth_module
        from app.utils.auth import require_auth, token_cache

        @app.route('/test-auth-retry')
        @require_auth
        def protected():
            from flask import g
            return {'user_id': g.user_id}

        mock_supa = MagicMock()
        # First call fails with SSL error, second call succeeds
        mock_supa.auth.get_user.side_effect = [
            Exception('SSL: CERTIFICATE_VERIFY_FAILED'),
            mock_supabase_auth,
        ]

        with patch.object(auth_module, 'supabase', mock_supa), \
             patch('time.sleep'):  # Skip actual sleep
            resp = client.get('/test-auth-retry',
                              headers={'Authorization': 'Bearer retry-token'})

        assert resp.status_code == 200

        # Cleanup
        token_cache.pop('retry-token', None)


class TestRequireAuth503OnPersistentFailure:
    """If all retries fail with a network error, return 503."""

    def test_require_auth_503_on_persistent_failure(self, app, client, db_session):
        from app.utils import auth as auth_module
        from app.utils.auth import require_auth

        @app.route('/test-auth-503')
        @require_auth
        def protected():
            return {'ok': True}

        mock_supa = MagicMock()
        # All 3 attempts fail with SSL error
        mock_supa.auth.get_user.side_effect = Exception('SSL connection reset')

        with patch.object(auth_module, 'supabase', mock_supa), \
             patch('time.sleep'):
            resp = client.get('/test-auth-503',
                              headers={'Authorization': 'Bearer fail-token'})

        assert resp.status_code == 503
        assert 'temporarily unavailable' in resp.get_json()['error']


class TestTokenCacheExpiry:
    """Expired tokens should be cleaned from the cache."""

    def test_token_cache_expiry(self, app):
        from app.utils.auth import token_cache, clean_expired_tokens

        with app.app_context():
            token_cache['expired-tok'] = {
                'user_data': MagicMock(),
                'expires_at': time.time() - 100,
            }
            token_cache['valid-tok'] = {
                'user_data': MagicMock(),
                'expires_at': time.time() + 300,
            }

            clean_expired_tokens()

            assert 'expired-tok' not in token_cache
            assert 'valid-tok' in token_cache

            # Cleanup
            token_cache.pop('valid-tok', None)


class TestInvalidateTokenCache:
    """invalidate_token_cache should remove specific or all tokens."""

    def test_invalidate_specific_token(self, app):
        from app.utils.auth import token_cache, invalidate_token_cache

        with app.app_context():
            token_cache['tok-a'] = {'user_data': MagicMock(), 'expires_at': time.time() + 300}
            token_cache['tok-b'] = {'user_data': MagicMock(), 'expires_at': time.time() + 300}

            invalidate_token_cache(token='tok-a')

            assert 'tok-a' not in token_cache
            assert 'tok-b' in token_cache

            # Cleanup
            token_cache.pop('tok-b', None)

    def test_invalidate_all_tokens(self, app):
        from app.utils.auth import token_cache, invalidate_token_cache

        with app.app_context():
            token_cache['tok-x'] = {'user_data': MagicMock(), 'expires_at': time.time() + 300}
            token_cache['tok-y'] = {'user_data': MagicMock(), 'expires_at': time.time() + 300}

            invalidate_token_cache()

            assert len(token_cache) == 0


class TestGetUserId:
    """get_user_id reads from Flask g context."""

    def test_get_user_id(self, app):
        from app.utils.auth import get_user_id
        from flask import g

        with app.test_request_context():
            g.user_id = 'test-uid-999'
            assert get_user_id() == 'test-uid-999'

    def test_get_user_id_missing(self, app):
        from app.utils.auth import get_user_id

        with app.test_request_context():
            assert get_user_id() is None


class TestGetCurrentUserInfo:
    """get_current_user_info reads from Flask g context."""

    def test_get_current_user_info_full(self, app):
        from app.utils.auth import get_current_user_info
        from flask import g

        with app.test_request_context():
            g.user_id = 'uid-001'
            g.user_email = 'test@example.com'
            info = get_current_user_info()
            assert info == {'user_id': 'uid-001', 'email': 'test@example.com'}

    def test_get_current_user_info_no_email(self, app):
        from app.utils.auth import get_current_user_info
        from flask import g

        with app.test_request_context():
            g.user_id = 'uid-002'
            info = get_current_user_info()
            assert info == {'user_id': 'uid-002'}

    def test_get_current_user_info_missing(self, app):
        from app.utils.auth import get_current_user_info

        with app.test_request_context():
            assert get_current_user_info() is None

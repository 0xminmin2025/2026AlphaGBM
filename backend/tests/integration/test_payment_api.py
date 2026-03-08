"""
Integration tests for the payment API endpoints.

Endpoints tested:
    POST /api/payment/create-checkout-session
    POST /api/payment/webhook
    GET  /api/payment/credits
    GET  /api/payment/pricing
    GET  /api/payment/upgrade-options
"""
import json
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# POST /api/payment/create-checkout-session
# ---------------------------------------------------------------------------

class TestCreateCheckout:
    """Tests for creating a Stripe checkout session."""

    def test_create_checkout_requires_auth(self, client):
        """POST without auth header should return 401."""
        resp = client.post(
            '/api/payment/create-checkout-session',
            json={'price_key': 'plus_monthly'},
        )
        assert resp.status_code == 401

    def test_create_checkout_success(
        self,
        client,
        auth_headers,
        mock_supabase_auth,
        sample_user,
        mock_stripe,
    ):
        """POST with auth and a valid price_key should return 200 with session info."""
        with patch(
            'app.services.payment_service.PaymentService.create_checkout_session'
        ) as mock_create:
            mock_session = MagicMock()
            mock_session.id = 'cs_test_999'
            mock_session.url = 'https://checkout.stripe.com/test-session'
            mock_create.return_value = (mock_session, None)

            resp = client.post(
                '/api/payment/create-checkout-session',
                json={'price_key': 'plus_monthly'},
                headers=auth_headers,
            )

        assert resp.status_code == 200
        data = resp.get_json()
        assert 'session_id' in data
        assert 'checkout_url' in data

    def test_create_checkout_invalid_price(
        self, client, auth_headers, mock_supabase_auth, sample_user
    ):
        """POST with an unknown price_key should return 400."""
        resp = client.post(
            '/api/payment/create-checkout-session',
            json={'price_key': 'nonexistent_plan'},
            headers=auth_headers,
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert 'error' in data


# ---------------------------------------------------------------------------
# POST /api/payment/webhook
# ---------------------------------------------------------------------------

class TestWebhook:
    """Tests for the Stripe webhook endpoint."""

    def test_webhook_invalid_signature(self, client, mock_stripe_webhook):
        """POST with an invalid Stripe signature should return 400."""
        # Use ValueError because the webhook handler catches it explicitly
        # at line 69 of payment.py (before stripe.error.SignatureVerificationError).
        # Using a generic Exception would fail because the mock replaces
        # stripe.error, making the except clause for
        # stripe.error.SignatureVerificationError impossible to match a real
        # exception class, which causes it to propagate.
        mock_stripe_webhook.Webhook.construct_event.side_effect = ValueError(
            'Invalid payload'
        )

        resp = client.post(
            '/api/payment/webhook',
            data=b'{}',
            headers={
                'Stripe-Signature': 'bad_sig',
                'Content-Type': 'application/json',
            },
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert 'error' in data


# ---------------------------------------------------------------------------
# GET /api/payment/credits
# ---------------------------------------------------------------------------

class TestGetCredits:
    """Tests for retrieving user credit information."""

    def test_get_credits_requires_auth(self, client):
        """GET /api/payment/credits without auth should return 401."""
        resp = client.get('/api/payment/credits')
        assert resp.status_code == 401

    def test_get_credits_success(
        self, client, auth_headers, mock_supabase_auth, sample_user
    ):
        """GET /api/payment/credits with auth should return credit info."""
        with patch(
            'app.services.payment_service.PaymentService.get_total_credits',
            return_value=950,
        ), patch(
            'app.services.payment_service.PaymentService.get_user_subscription_info',
            return_value={'plan_tier': 'plus', 'status': 'active'},
        ):
            resp = client.get('/api/payment/credits', headers=auth_headers)

        assert resp.status_code == 200
        data = resp.get_json()
        assert 'total_credits' in data
        assert 'subscription' in data
        assert 'daily_free' in data
        assert data['total_credits'] == 950


# ---------------------------------------------------------------------------
# GET /api/payment/pricing  (no auth required)
# ---------------------------------------------------------------------------

class TestGetPricing:
    """Tests for the public pricing endpoint."""

    def test_get_pricing_no_auth(self, client):
        """GET /api/payment/pricing should return 200 without auth."""
        resp = client.get('/api/payment/pricing')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'plans' in data
        assert 'free' in data['plans']
        assert 'plus' in data['plans']
        assert 'pro' in data['plans']


# ---------------------------------------------------------------------------
# GET /api/payment/upgrade-options  (auth required)
# ---------------------------------------------------------------------------

class TestUpgradeOptions:
    """Tests for the upgrade options endpoint."""

    def test_upgrade_options_requires_auth(self, client):
        """GET /api/payment/upgrade-options without auth should return 401."""
        resp = client.get('/api/payment/upgrade-options')
        assert resp.status_code == 401

    def test_upgrade_options_success(
        self, client, auth_headers, mock_supabase_auth, sample_user
    ):
        """GET /api/payment/upgrade-options with auth returns options list."""
        mock_options = {
            'current_plan': 'free',
            'available_upgrades': ['plus_monthly', 'plus_yearly', 'pro_monthly', 'pro_yearly'],
        }

        with patch(
            'app.services.payment_service.PaymentService.get_upgrade_options',
            return_value=mock_options,
        ):
            resp = client.get(
                '/api/payment/upgrade-options', headers=auth_headers
            )

        assert resp.status_code == 200
        data = resp.get_json()
        assert 'current_plan' in data
        assert 'available_upgrades' in data

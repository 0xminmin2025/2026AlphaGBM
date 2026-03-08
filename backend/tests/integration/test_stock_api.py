"""
Integration tests for the stock analysis API endpoints.

Endpoints tested:
    GET  /api/stock/search?q=AAPL
    POST /api/stock/analyze
    GET  /api/stock/history
"""
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# GET /api/stock/search  (no auth required)
# ---------------------------------------------------------------------------

class TestStockSearch:
    """Tests for the publicly accessible stock search endpoint."""

    def test_search_no_auth(self, client):
        """GET /api/stock/search?q=AAPL should succeed without auth (200)."""
        with patch('app.api.stock.requests.get') as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json.return_value = {
                'quotes': [
                    {
                        'symbol': 'AAPL',
                        'shortname': 'Apple Inc.',
                        'quoteType': 'EQUITY',
                        'exchange': 'NMS',
                    }
                ]
            }
            mock_get.return_value = mock_resp

            resp = client.get('/api/stock/search?q=AAPL')

        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert isinstance(data['results'], list)
        assert len(data['results']) >= 1
        assert data['results'][0]['ticker'] == 'AAPL'

    def test_search_empty_query(self, client):
        """Empty query should return an empty result list."""
        resp = client.get('/api/stock/search?q=')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert data['results'] == []


# ---------------------------------------------------------------------------
# POST /api/stock/analyze  (auth + quota required)
# ---------------------------------------------------------------------------

class TestStockAnalyze:
    """Tests for the stock analysis endpoint."""

    def test_analyze_requires_auth(self, client):
        """POST /api/stock/analyze without auth header should return 401."""
        resp = client.post(
            '/api/stock/analyze',
            json={'ticker': 'AAPL', 'style': 'quality'},
        )
        # check_quota decorator checks auth first; missing header -> 401
        assert resp.status_code == 401

    def test_analyze_with_auth(
        self, client, auth_headers, mock_supabase_auth, sample_user
    ):
        """
        POST /api/stock/analyze with valid auth should return a task_id
        (the endpoint always creates an async task for full analysis).
        """
        with patch(
            'app.api.stock.create_analysis_task', return_value='task-uuid-001'
        ) as mock_task, patch(
            'app.api.stock.get_cached_analysis', return_value=None
        ), patch(
            'app.api.stock.get_in_progress_task_for_stock', return_value=None
        ), patch(
            'app.services.payment_service.PaymentService.check_and_deduct_credits',
            return_value=(True, 'OK', 999, {'is_free': True, 'free_remaining': 1, 'free_quota': 2, 'free_used': 1}),
        ):
            resp = client.post(
                '/api/stock/analyze',
                json={'ticker': 'AAPL', 'style': 'quality'},
                headers=auth_headers,
            )

        assert resp.status_code == 201
        data = resp.get_json()
        assert data['success'] is True
        assert 'task_id' in data


# ---------------------------------------------------------------------------
# GET /api/stock/history  (auth required)
# ---------------------------------------------------------------------------

class TestStockHistory:
    """Tests for the analysis history endpoint."""

    def test_history_requires_auth(self, client):
        """GET /api/stock/history without auth should return 401."""
        resp = client.get('/api/stock/history')
        assert resp.status_code == 401

    def test_history_with_auth(
        self, client, auth_headers, mock_supabase_auth, sample_user
    ):
        """GET /api/stock/history with auth should return a paginated list."""
        resp = client.get('/api/stock/history', headers=auth_headers)

        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert 'data' in data
        assert 'items' in data['data']
        assert 'pagination' in data['data']
        pagination = data['data']['pagination']
        assert 'page' in pagination
        assert 'per_page' in pagination
        assert 'total' in pagination

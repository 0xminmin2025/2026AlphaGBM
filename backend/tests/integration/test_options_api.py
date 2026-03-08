"""
Integration tests for the options analysis API endpoints.

Endpoints tested:
    GET  /api/options/expirations/<symbol>
    GET  /api/options/recommendations
"""
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# GET /api/options/expirations/<symbol>  (auth required)
# ---------------------------------------------------------------------------

class TestOptionsExpirations:
    """Tests for fetching option expiration dates."""

    def test_expirations_requires_auth(self, client):
        """GET /api/options/expirations/AAPL without auth should return 401."""
        resp = client.get('/api/options/expirations/AAPL')
        assert resp.status_code == 401

    def test_expirations_with_auth(
        self, client, auth_headers, mock_supabase_auth, sample_user
    ):
        """GET /api/options/expirations/AAPL with auth returns expiration data."""
        mock_response = MagicMock()
        mock_response.dict.return_value = {
            'symbol': 'AAPL',
            'expirations': ['2026-02-21', '2026-03-21'],
        }

        with patch(
            'app.api.options.OptionsService.get_expirations',
            return_value=mock_response,
        ):
            resp = client.get(
                '/api/options/expirations/AAPL', headers=auth_headers
            )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data['symbol'] == 'AAPL'
        assert isinstance(data['expirations'], list)


# ---------------------------------------------------------------------------
# GET /api/options/recommendations  (no auth required)
# ---------------------------------------------------------------------------

class TestOptionsRecommendations:
    """Tests for the daily option recommendations endpoint."""

    def test_recommendations_no_auth(self, client):
        """GET /api/options/recommendations should succeed without auth (200)."""
        mock_result = {
            'success': True,
            'recommendations': [
                {'symbol': 'AAPL', 'strategy': 'Buy Call', 'score': 85}
            ],
            'market_summary': {'vix': 18.5},
            'updated_at': '2026-02-08T09:30:00Z',
        }

        # The import happens inside the view function:
        #   from ..services.recommendation_service import recommendation_service
        # so we patch the module-level object.
        with patch(
            'app.services.recommendation_service.recommendation_service'
        ) as mock_svc:
            mock_svc.get_daily_recommendations.return_value = mock_result

            resp = client.get('/api/options/recommendations')

        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert isinstance(data['recommendations'], list)

"""
Integration tests for the sector analysis API endpoints.

Endpoints tested:
    GET /api/sector/rotation/overview
"""
import pytest
from unittest.mock import patch, MagicMock


class TestSectorRotationOverview:
    """Tests for the sector rotation overview endpoint (no auth required)."""

    def test_rotation_overview(self, client):
        """GET /api/sector/rotation/overview should return 200 with sector data."""
        mock_result = {
            'market': 'US',
            'sectors': [
                {
                    'sector': 'Technology',
                    'strength': 85,
                    'momentum': 'strong',
                    'change_1w': 3.2,
                },
                {
                    'sector': 'Healthcare',
                    'strength': 62,
                    'momentum': 'neutral',
                    'change_1w': 0.8,
                },
            ],
            'updated_at': '2026-02-08T10:00:00Z',
        }

        with patch(
            'app.api.sector.get_sector_rotation_service'
        ) as mock_get_svc:
            mock_svc = MagicMock()
            mock_svc.get_rotation_overview.return_value = mock_result
            mock_get_svc.return_value = mock_svc

            resp = client.get('/api/sector/rotation/overview')

        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert 'sectors' in data
        assert isinstance(data['sectors'], list)
        assert len(data['sectors']) >= 1

    def test_rotation_overview_with_market_param(self, client):
        """GET with ?market=HK should pass the market code to the service."""
        mock_result = {
            'market': 'HK',
            'sectors': [],
            'updated_at': '2026-02-08T10:00:00Z',
        }

        with patch(
            'app.api.sector.get_sector_rotation_service'
        ) as mock_get_svc:
            mock_svc = MagicMock()
            mock_svc.get_rotation_overview.return_value = mock_result
            mock_get_svc.return_value = mock_svc

            resp = client.get('/api/sector/rotation/overview?market=HK')

        assert resp.status_code == 200
        data = resp.get_json()
        assert data['market'] == 'HK'

"""
Integration tests for the narrative radar API endpoints.

Endpoints tested:
    GET  /api/narrative/presets
    POST /api/narrative/analyze
"""
import pytest
from unittest.mock import patch, MagicMock


class TestNarrativePresets:
    """Tests for the narrative presets endpoint (no auth required)."""

    def test_get_presets(self, client):
        """GET /api/narrative/presets should return 200 with grouped presets."""
        mock_presets = {
            'buffett': {
                'type': 'person',
                'name': 'Warren Buffett',
                'description': 'Value investing guru',
            },
            'ark_invest': {
                'type': 'institution',
                'name': 'ARK Invest',
                'description': 'Disruptive innovation',
            },
            'ai_revolution': {
                'type': 'theme',
                'name': 'AI Revolution',
                'description': 'Artificial intelligence trend',
            },
        }

        with patch(
            'app.api.narrative_routes.get_preset_narratives',
            return_value=mock_presets,
        ):
            resp = client.get('/api/narrative/presets')

        assert resp.status_code == 200
        data = resp.get_json()
        assert 'person' in data
        assert 'institution' in data
        assert 'theme' in data
        assert isinstance(data['person'], list)
        assert len(data['person']) >= 1


class TestNarrativeAnalyze:
    """Tests for the narrative analysis endpoint (no auth required)."""

    def test_analyze(self, client):
        """POST /api/narrative/analyze should return 200 with analysis results."""
        mock_result = {
            'success': True,
            'concept': 'AI stocks',
            'stocks': [
                {'ticker': 'NVDA', 'name': 'NVIDIA', 'relevance': 95},
                {'ticker': 'MSFT', 'name': 'Microsoft', 'relevance': 88},
            ],
            'options_strategies': [],
        }

        with patch(
            'app.api.narrative_routes.analyze_narrative',
            return_value=mock_result,
        ):
            resp = client.post(
                '/api/narrative/analyze',
                json={'concept': 'AI stocks', 'market': 'US'},
            )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert 'stocks' in data

    def test_analyze_missing_concept(self, client):
        """POST without concept or narrative_key should return 400."""
        resp = client.post(
            '/api/narrative/analyze',
            json={'market': 'US'},
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert 'error' in data

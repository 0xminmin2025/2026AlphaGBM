"""
Integration tests for the feedback API endpoints.

Endpoints tested:
    POST /api/feedback
"""
import pytest
from unittest.mock import patch, MagicMock


class TestFeedbackSubmit:
    """Tests for submitting user feedback."""

    def test_submit_requires_auth(self, client):
        """POST /api/feedback without auth should return 401."""
        resp = client.post(
            '/api/feedback',
            json={
                'type': 'bug',
                'content': 'Something is broken',
            },
        )
        assert resp.status_code == 401

    def test_submit_success(
        self, client, auth_headers, mock_supabase_auth, sample_user
    ):
        """POST /api/feedback with auth and valid body should succeed."""
        resp = client.post(
            '/api/feedback',
            json={
                'type': 'suggestion',
                'content': 'Please add dark mode support.',
                'ticker': 'AAPL',
            },
            headers=auth_headers,
        )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert 'feedback_id' in data

    def test_submit_empty_content(
        self, client, auth_headers, mock_supabase_auth, sample_user
    ):
        """POST /api/feedback with empty content should return 400."""
        resp = client.post(
            '/api/feedback',
            json={
                'type': 'bug',
                'content': '',
            },
            headers=auth_headers,
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['success'] is False

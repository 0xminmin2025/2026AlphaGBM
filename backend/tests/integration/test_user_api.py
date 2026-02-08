"""
Integration tests for the user API endpoints.

Endpoints tested:
    GET /api/user/profile
"""
import pytest
from unittest.mock import patch, MagicMock


class TestUserProfile:
    """Tests for the user profile endpoint."""

    def test_profile_requires_auth(self, client):
        """GET /api/user/profile without auth should return 401."""
        resp = client.get('/api/user/profile')
        assert resp.status_code == 401

    def test_profile_success(
        self, client, auth_headers, mock_supabase_auth, sample_user
    ):
        """GET /api/user/profile with auth should return user info (200)."""
        resp = client.get('/api/user/profile', headers=auth_headers)

        assert resp.status_code == 200
        data = resp.get_json()
        # The endpoint currently returns a simple message
        assert 'message' in data

"""
Integration tests for the task management API endpoints.

Endpoints tested:
    POST /api/tasks/create
    GET  /api/tasks/<task_id>/status
"""
import pytest
from unittest.mock import patch, MagicMock


class TestTaskCreate:
    """Tests for creating an analysis task."""

    def test_create_requires_auth(self, client):
        """POST /api/tasks/create without auth should return 401."""
        resp = client.post(
            '/api/tasks/create',
            json={
                'task_type': 'stock_analysis',
                'input_params': {'ticker': 'AAPL', 'style': 'quality'},
            },
        )
        assert resp.status_code == 401

    def test_create_success(
        self, client, auth_headers, mock_supabase_auth, sample_user
    ):
        """POST /api/tasks/create with auth and valid body should return 201."""
        with patch(
            'app.api.tasks.create_analysis_task',
            return_value='task-uuid-abc',
        ):
            resp = client.post(
                '/api/tasks/create',
                json={
                    'task_type': 'stock_analysis',
                    'input_params': {'ticker': 'TSLA', 'style': 'momentum'},
                },
                headers=auth_headers,
            )

        assert resp.status_code == 201
        data = resp.get_json()
        assert data['task_id'] == 'task-uuid-abc'
        assert 'message' in data

    def test_create_invalid_task_type(
        self, client, auth_headers, mock_supabase_auth, sample_user
    ):
        """POST with an invalid task_type should return 400."""
        resp = client.post(
            '/api/tasks/create',
            json={
                'task_type': 'invalid_type',
                'input_params': {'ticker': 'AAPL'},
            },
            headers=auth_headers,
        )
        assert resp.status_code == 400


class TestTaskStatus:
    """Tests for checking task status."""

    def test_status_requires_auth(self, client):
        """GET /api/tasks/<id>/status without auth should return 401."""
        resp = client.get('/api/tasks/some-task-id/status')
        assert resp.status_code == 401

    def test_status_success(
        self, client, auth_headers, mock_supabase_auth, sample_user
    ):
        """GET /api/tasks/<id>/status with auth should return task details."""
        mock_status = {
            'id': 'task-uuid-abc',
            'user_id': 'test-user-uuid-1234',
            'task_type': 'stock_analysis',
            'status': 'processing',
            'progress_percent': 50,
            'current_step': 'Running AI analysis...',
            'input_params': {'ticker': 'AAPL', 'style': 'quality'},
            'result_data': None,
            'error_message': None,
            'created_at': '2026-02-08T12:00:00',
            'started_at': '2026-02-08T12:00:30',
            'completed_at': None,
            'related_history_id': None,
            'related_history_type': None,
        }

        with patch(
            'app.api.tasks.get_task_status', return_value=mock_status
        ):
            resp = client.get(
                '/api/tasks/task-uuid-abc/status', headers=auth_headers
            )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'processing'
        assert data['progress_percent'] == 50
        # user_id should be stripped from the response
        assert 'user_id' not in data

    def test_status_not_found(
        self, client, auth_headers, mock_supabase_auth, sample_user
    ):
        """GET /api/tasks/<id>/status for a non-existent task returns 404."""
        with patch('app.api.tasks.get_task_status', return_value=None):
            resp = client.get(
                '/api/tasks/nonexistent-id/status', headers=auth_headers
            )

        assert resp.status_code == 404

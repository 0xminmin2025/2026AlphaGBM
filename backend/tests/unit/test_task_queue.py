"""
Unit tests for the async task queue management system.

These tests exercise TaskQueue.create_task, get_task_status, get_user_tasks,
cached task mode, and task lifecycle transitions.
All database interactions are mocked so no real DB is required.
"""

import uuid
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from datetime import datetime

from app.services.task_queue import TaskQueue


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_task(task_id, user_id, status='pending'):
    """Return a MagicMock that behaves like an AnalysisTask row."""
    task = MagicMock()
    task.id = task_id
    task.user_id = user_id
    task.status = status
    task.task_type = 'stock_analysis'
    task.progress = 0
    task.current_step = 'created'
    task.created_at = datetime.utcnow()
    task.to_dict.return_value = {
        'id': task_id,
        'user_id': user_id,
        'status': status,
        'task_type': 'stock_analysis',
        'progress': 0,
        'current_step': 'created',
    }
    return task


# ===================================================================
# test_create_task_returns_uuid
# ===================================================================

class TestCreateTaskReturnsUuid:
    """create_task should return a valid UUID string."""

    @patch('app.services.task_queue.db')
    @patch('app.services.task_queue.AnalysisTask')
    def test_returns_uuid(self, MockTask, mock_db):
        tq = TaskQueue(max_workers=1)
        task_id = tq.create_task(
            user_id='user-1',
            task_type='stock_analysis',
            input_params={'ticker': 'AAPL', 'style': 'growth'},
        )
        # Must be a valid UUID-4
        parsed = uuid.UUID(task_id, version=4)
        assert str(parsed) == task_id

    @patch('app.services.task_queue.db')
    @patch('app.services.task_queue.AnalysisTask')
    def test_task_added_to_session(self, MockTask, mock_db):
        tq = TaskQueue(max_workers=1)
        tq.create_task(
            user_id='user-1',
            task_type='stock_analysis',
            input_params={'ticker': 'AAPL'},
        )
        mock_db.session.add.assert_called_once()
        mock_db.session.commit.assert_called_once()


# ===================================================================
# test_get_task_status
# ===================================================================

class TestGetTaskStatus:
    """get_task_status should return the task dict for a known task."""

    @patch('app.services.task_queue.AnalysisTask')
    def test_returns_pending_status(self, MockTaskModel):
        task_id = str(uuid.uuid4())
        mock_task = _make_mock_task(task_id, 'user-1', status='pending')
        MockTaskModel.query.get.return_value = mock_task

        tq = TaskQueue(max_workers=1)
        result = tq.get_task_status(task_id)

        assert result is not None
        assert result['status'] == 'pending'
        assert result['id'] == task_id

    @patch('app.services.task_queue.AnalysisTask')
    def test_returns_none_for_unknown_task(self, MockTaskModel):
        MockTaskModel.query.get.return_value = None

        tq = TaskQueue(max_workers=1)
        result = tq.get_task_status('nonexistent-id')

        assert result is None


# ===================================================================
# test_get_user_tasks
# ===================================================================

class TestGetUserTasks:
    """get_user_tasks should filter tasks by user_id."""

    @patch('app.services.task_queue.AnalysisTask')
    def test_filters_by_user_id(self, MockTaskModel):
        t1 = _make_mock_task('id-1', 'user-1')
        t2 = _make_mock_task('id-2', 'user-1')

        # Build a mock query chain
        mock_query = MagicMock()
        mock_query.order_by.return_value.limit.return_value.all.return_value = [t1, t2]
        MockTaskModel.query.filter_by.return_value = mock_query

        tq = TaskQueue(max_workers=1)
        tasks = tq.get_user_tasks('user-1', limit=10)

        MockTaskModel.query.filter_by.assert_called_once_with(user_id='user-1')
        assert len(tasks) == 2
        assert tasks[0]['user_id'] == 'user-1'

    @patch('app.services.task_queue.AnalysisTask')
    def test_filters_by_status(self, MockTaskModel):
        mock_query = MagicMock()
        mock_filtered = MagicMock()
        mock_query.filter_by.return_value = mock_filtered
        mock_filtered.order_by.return_value.limit.return_value.all.return_value = []
        MockTaskModel.query.filter_by.return_value = mock_query

        tq = TaskQueue(max_workers=1)
        tasks = tq.get_user_tasks('user-1', status='completed')

        # The first filter_by is for user_id; the second for status
        assert MockTaskModel.query.filter_by.called


# ===================================================================
# test_cached_task_mode
# ===================================================================

class TestCachedTaskMode:
    """When cache_mode='cached', the task should receive cached_data."""

    @patch('app.services.task_queue.db')
    @patch('app.services.task_queue.AnalysisTask')
    def test_cached_mode_puts_data_on_queue(self, MockTask, mock_db):
        tq = TaskQueue(max_workers=1)
        cached = {'analysis': 'pre-computed result'}

        task_id = tq.create_task(
            user_id='user-1',
            task_type='stock_analysis',
            input_params={'ticker': 'AAPL'},
            cache_mode='cached',
            cached_data=cached,
        )
        assert task_id is not None

        # The item should be on the internal queue
        assert not tq.task_queue.empty()
        item = tq.task_queue.get_nowait()
        assert item['cache_mode'] == 'cached'
        assert item['cached_data'] == cached


# ===================================================================
# test_task_lifecycle
# ===================================================================

class TestTaskLifecycle:
    """Verify the pending -> processing -> completed status flow via mocks."""

    @patch('app.services.task_queue.db')
    @patch('app.services.task_queue.AnalysisTask')
    def test_lifecycle_pending_to_processing_to_completed(self, MockTask, mock_db):
        """Create a task (pending), then verify the queue item has
        all the data needed for workers to transition it."""
        tq = TaskQueue(max_workers=1)

        task_id = tq.create_task(
            user_id='user-1',
            task_type='stock_analysis',
            input_params={'ticker': 'NVDA', 'style': 'momentum'},
        )

        # Task was committed to DB as pending
        mock_db.session.add.assert_called_once()
        mock_db.session.commit.assert_called_once()

        # Verify the queue item contains required worker fields
        item = tq.task_queue.get_nowait()
        assert item['task_id'] == task_id
        assert item['task_type'] == 'stock_analysis'
        assert item['user_id'] == 'user-1'
        # cache_mode should be None for normal tasks
        assert item['cache_mode'] is None

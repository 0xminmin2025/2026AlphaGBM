"""
Task Management API Endpoints

This module provides REST API endpoints for managing async analysis tasks.
Handles task creation, status checking, and result retrieval.
"""

from flask import Blueprint, request, jsonify
from ..utils.auth import get_user_id, require_auth
from ..services.task_queue import create_analysis_task, get_task_status, get_user_tasks
from ..models import TaskType, TaskStatus
import logging

logger = logging.getLogger(__name__)

tasks_bp = Blueprint('tasks', __name__, url_prefix='/api/tasks')

@tasks_bp.route('/create', methods=['POST'])
@require_auth
def create_task():
    """
    Create a new analysis task

    Request Body:
    {
        "task_type": "stock_analysis|option_analysis|enhanced_option_analysis",
        "input_params": {
            "ticker": "AAPL",
            "style": "quality"
            // or for options:
            // "symbol": "AAPL",
            // "option_identifier": "AAPL240119C00150000",
            // "expiry_date": "2024-01-19"
        },
        "priority": 100  // optional, lower = higher priority
    }

    Returns:
    {
        "task_id": "uuid-string",
        "message": "Task created successfully"
    }
    """
    try:
        user_id = get_user_id()
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401

        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        # Validate task type
        task_type = data.get('task_type')
        if not task_type or task_type not in [e.value for e in TaskType]:
            return jsonify({
                'error': f'Invalid task_type. Must be one of: {[e.value for e in TaskType]}'
            }), 400

        # Validate input parameters
        input_params = data.get('input_params', {})
        if not input_params:
            return jsonify({'error': 'input_params is required'}), 400

        # Validate specific parameters based on task type
        if task_type == TaskType.STOCK_ANALYSIS.value:
            if 'ticker' not in input_params:
                return jsonify({'error': 'ticker is required for stock analysis'}), 400

        elif task_type in [TaskType.OPTION_ANALYSIS.value, TaskType.ENHANCED_OPTION_ANALYSIS.value]:
            if 'symbol' not in input_params:
                return jsonify({'error': 'symbol is required for options analysis'}), 400

            if task_type == TaskType.ENHANCED_OPTION_ANALYSIS.value and 'option_identifier' not in input_params:
                return jsonify({'error': 'option_identifier is required for enhanced options analysis'}), 400

        priority = data.get('priority', 100)

        # Create the task
        task_id = create_analysis_task(user_id, task_type, input_params, priority)

        logger.info(f"Created task {task_id} for user {user_id}: {task_type}")

        return jsonify({
            'task_id': task_id,
            'message': 'Task created successfully'
        }), 201

    except Exception as e:
        logger.error(f"Failed to create task: {e}")
        return jsonify({'error': 'Failed to create task'}), 500

@tasks_bp.route('/<task_id>/status', methods=['GET'])
@require_auth
def get_task_status_endpoint(task_id):
    """
    Get task status and progress

    Returns:
    {
        "id": "task-uuid",
        "task_type": "stock_analysis",
        "status": "pending|processing|completed|failed",
        "progress_percent": 75,
        "current_step": "Running AI analysis...",
        "input_params": {...},
        "result_data": {...},  // only when completed
        "error_message": "...",  // only when failed
        "created_at": "2024-01-01T12:00:00",
        "started_at": "2024-01-01T12:00:30",
        "completed_at": "2024-01-01T12:02:15",
        "related_history_id": 123,
        "related_history_type": "stock"
    }
    """
    try:
        user_id = get_user_id()
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401

        task_status = get_task_status(task_id)
        if not task_status:
            return jsonify({'error': 'Task not found'}), 404

        # Debug logging for user ID comparison
        task_user_id = task_status.get('user_id')
        logger.info(f"DEBUG: Task status check - Task ID: {task_id}")
        logger.info(f"DEBUG: Task user_id from DB: '{task_user_id}' (type: {type(task_user_id)})")
        logger.info(f"DEBUG: Current user_id from JWT: '{user_id}' (type: {type(user_id)})")
        logger.info(f"DEBUG: User IDs match: {task_user_id == user_id}")

        # Verify task belongs to user
        if task_status.get('user_id') != user_id:
            logger.warning(f"Access denied for task {task_id} - user_id mismatch: task='{task_user_id}' vs jwt='{user_id}'")
            return jsonify({'error': 'Access denied'}), 403

        # Remove user_id from response for security
        task_status.pop('user_id', None)

        return jsonify(task_status)

    except Exception as e:
        logger.error(f"Failed to get task status for {task_id}: {e}")
        return jsonify({'error': 'Failed to get task status'}), 500

@tasks_bp.route('/<task_id>/result', methods=['GET'])
@require_auth
def get_task_result(task_id):
    """
    Get task result (only for completed tasks)

    Returns:
    {
        "task_id": "task-uuid",
        "status": "completed",
        "result_data": {...},
        "related_history_id": 123,
        "related_history_type": "stock"
    }
    """
    try:
        user_id = get_user_id()
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401

        task_status = get_task_status(task_id)
        if not task_status:
            return jsonify({'error': 'Task not found'}), 404

        # Verify task belongs to user
        if task_status.get('user_id') != user_id:
            return jsonify({'error': 'Access denied'}), 403

        # Check if task is completed
        if task_status.get('status') != TaskStatus.COMPLETED.value:
            return jsonify({
                'error': 'Task not completed',
                'current_status': task_status.get('status'),
                'progress_percent': task_status.get('progress_percent', 0)
            }), 400

        # Return only the result data
        return jsonify({
            'task_id': task_id,
            'status': task_status.get('status'),
            'result_data': task_status.get('result_data'),
            'related_history_id': task_status.get('related_history_id'),
            'related_history_type': task_status.get('related_history_type'),
            'completed_at': task_status.get('completed_at')
        })

    except Exception as e:
        logger.error(f"Failed to get task result for {task_id}: {e}")
        return jsonify({'error': 'Failed to get task result'}), 500

@tasks_bp.route('/user', methods=['GET'])
@require_auth
def get_user_tasks_endpoint():
    """
    Get user's tasks with optional filtering

    Query Parameters:
    - limit: Number of tasks to return (default: 10, max: 50)
    - status: Filter by status (pending|processing|completed|failed)

    Returns:
    {
        "tasks": [
            {
                "id": "task-uuid",
                "task_type": "stock_analysis",
                "status": "completed",
                "progress_percent": 100,
                "current_step": "Analysis completed successfully",
                "input_params": {...},
                "created_at": "2024-01-01T12:00:00",
                "completed_at": "2024-01-01T12:02:15"
            },
            ...
        ],
        "total": 25
    }
    """
    try:
        user_id = get_user_id()
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401

        # Parse query parameters
        limit = min(int(request.args.get('limit', 10)), 50)  # Max 50 tasks
        status_filter = request.args.get('status')

        # Validate status filter
        if status_filter and status_filter not in [e.value for e in TaskStatus]:
            return jsonify({
                'error': f'Invalid status. Must be one of: {[e.value for e in TaskStatus]}'
            }), 400

        # Get user's tasks
        tasks = get_user_tasks(user_id, limit, status_filter)

        # Remove sensitive data from response
        for task in tasks:
            task.pop('user_id', None)

        return jsonify({
            'tasks': tasks,
            'total': len(tasks),
            'limit': limit,
            'status_filter': status_filter
        })

    except Exception as e:
        logger.error(f"Failed to get user tasks for {user_id}: {e}")
        return jsonify({'error': 'Failed to get user tasks'}), 500

@tasks_bp.route('/stats', methods=['GET'])
@require_auth
def get_task_stats():
    """
    Get task statistics for the user

    Returns:
    {
        "total_tasks": 25,
        "pending": 2,
        "processing": 1,
        "completed": 20,
        "failed": 2,
        "success_rate": 0.91  // completed / (completed + failed)
    }
    """
    try:
        user_id = get_user_id()
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401

        # Get all user tasks
        all_tasks = get_user_tasks(user_id, limit=1000)  # Get more for stats

        # Calculate statistics
        stats = {
            'total_tasks': len(all_tasks),
            'pending': 0,
            'processing': 0,
            'completed': 0,
            'failed': 0
        }

        for task in all_tasks:
            status = task.get('status')
            if status in stats:
                stats[status] += 1

        # Calculate success rate
        total_finished = stats['completed'] + stats['failed']
        stats['success_rate'] = stats['completed'] / total_finished if total_finished > 0 else 0

        return jsonify(stats)

    except Exception as e:
        logger.error(f"Failed to get task stats for {user_id}: {e}")
        return jsonify({'error': 'Failed to get task stats'}), 500
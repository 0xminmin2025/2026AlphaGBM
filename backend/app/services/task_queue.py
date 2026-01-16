"""
Async Task Queue Management System

This module handles the creation, processing, and management of async analysis tasks.
Supports both stock analysis and options analysis tasks with progress tracking.
"""

import uuid
import logging
import threading
import time
from datetime import datetime
from queue import Queue, Empty
from typing import Optional, Dict, Any
from ..models import db, AnalysisTask, TaskType, TaskStatus, StockAnalysisHistory, OptionsAnalysisHistory
from ..utils.serialization import convert_numpy_types

logger = logging.getLogger(__name__)

class TaskQueue:
    """
    Async task queue management system

    Features:
    - Thread-safe task creation and processing
    - Progress tracking with status updates
    - Result storage in database
    - Error handling and retry logic
    """

    def __init__(self, max_workers: int = 3, app=None):
        self.task_queue = Queue()
        self.max_workers = max_workers
        self.workers = []
        self.is_running = False
        self.processing_tasks = {}  # Track currently processing tasks
        self.app = app  # Flask application for context

    def start(self):
        """Start the task queue workers"""
        if self.is_running:
            return

        self.is_running = True
        logger.info(f"Starting task queue with {self.max_workers} workers...")

        # Start worker threads
        for i in range(self.max_workers):
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"TaskWorker-{i+1}",
                daemon=True
            )
            worker.start()
            self.workers.append(worker)

        logger.info("Task queue workers started successfully")

    def stop(self):
        """Stop the task queue workers"""
        self.is_running = False
        logger.info("Task queue workers stopped")

    def create_task(self, user_id: str, task_type: str, input_params: Dict[str, Any], priority: int = 100) -> str:
        """
        Create a new analysis task

        Args:
            user_id: User ID creating the task
            task_type: Type of analysis (stock_analysis, option_analysis, etc.)
            input_params: Parameters for the analysis
            priority: Task priority (lower = higher priority)

        Returns:
            Task ID (UUID string)
        """
        task_id = str(uuid.uuid4())

        try:
            # Create task record in database
            task = AnalysisTask(
                id=task_id,
                user_id=user_id,
                task_type=task_type,
                status=TaskStatus.PENDING.value,
                priority=priority,
                input_params=input_params,
                current_step="Task created, waiting in queue..."
            )

            db.session.add(task)
            db.session.commit()

            # Add to queue for processing
            self.task_queue.put({
                'task_id': task_id,
                'user_id': user_id,
                'task_type': task_type,
                'input_params': input_params,
                'priority': priority,
                'created_at': datetime.utcnow()
            })

            logger.info(f"Task {task_id} created for user {user_id}: {task_type}")
            return task_id

        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            db.session.rollback()
            raise

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get current task status and progress"""
        try:
            task = AnalysisTask.query.get(task_id)
            if not task:
                return None

            return task.to_dict()

        except Exception as e:
            logger.error(f"Failed to get task status for {task_id}: {e}")
            return None

    def get_user_tasks(self, user_id: str, limit: int = 10, status: Optional[str] = None) -> list:
        """Get tasks for a specific user"""
        try:
            query = AnalysisTask.query.filter_by(user_id=user_id)

            if status:
                query = query.filter_by(status=status)

            tasks = query.order_by(AnalysisTask.created_at.desc()).limit(limit).all()
            return [task.to_dict() for task in tasks]

        except Exception as e:
            logger.error(f"Failed to get user tasks for {user_id}: {e}")
            return []

    def _worker_loop(self):
        """Main worker loop for processing tasks"""
        worker_name = threading.current_thread().name
        logger.info(f"Worker {worker_name} started")

        while self.is_running:
            try:
                # Get task from queue (with timeout)
                try:
                    task_data = self.task_queue.get(timeout=1.0)
                except Empty:
                    continue

                task_id = task_data['task_id']

                try:
                    # Mark task as processing
                    self.processing_tasks[task_id] = worker_name
                    self._update_task_status(task_id, TaskStatus.PROCESSING.value, 0, "Starting analysis...")

                    logger.info(f"Worker {worker_name} processing task {task_id}")

                    # Process the task based on type
                    if task_data['task_type'] == TaskType.STOCK_ANALYSIS.value:
                        self._process_stock_analysis(task_data)
                    elif task_data['task_type'] in [TaskType.OPTION_ANALYSIS.value, TaskType.ENHANCED_OPTION_ANALYSIS.value]:
                        self._process_options_analysis(task_data)
                    else:
                        raise ValueError(f"Unknown task type: {task_data['task_type']}")

                    logger.info(f"Worker {worker_name} completed task {task_id}")

                except Exception as e:
                    logger.error(f"Worker {worker_name} failed to process task {task_id}: {e}")
                    self._update_task_status(
                        task_id,
                        TaskStatus.FAILED.value,
                        0,
                        f"Task failed: {str(e)}",
                        error_message=str(e)
                    )
                finally:
                    # Remove from processing tasks
                    self.processing_tasks.pop(task_id, None)

            except Exception as e:
                logger.error(f"Worker {worker_name} encountered error: {e}")
                time.sleep(1)  # Brief pause before retrying

        logger.info(f"Worker {worker_name} stopped")

    def _update_task_status(self, task_id: str, status: str, progress: int, step: str, error_message: str = None):
        """Update task status in database"""
        if not self.app:
            logger.error("No Flask application context available for database operations")
            return

        with self.app.app_context():
            try:
                task = AnalysisTask.query.get(task_id)
                if not task:
                    logger.error(f"Task {task_id} not found for status update")
                    return

                task.status = status
                task.progress_percent = progress
                task.current_step = step

                if error_message:
                    task.error_message = error_message

                if status == TaskStatus.PROCESSING.value and not task.started_at:
                    task.started_at = datetime.utcnow()
                elif status in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value]:
                    task.completed_at = datetime.utcnow()

                db.session.commit()

            except Exception as e:
                logger.error(f"Failed to update task status for {task_id}: {e}")
                db.session.rollback()

    def _process_stock_analysis(self, task_data: Dict[str, Any]):
        """Process stock analysis task"""
        task_id = task_data['task_id']
        user_id = task_data['user_id']
        params = task_data['input_params']

        ticker = params.get('ticker')
        style = params.get('style', 'quality')

        logger.info(f"Processing stock analysis for {ticker} ({style})")

        try:
            # Step 1: Initialize analysis
            self._update_task_status(task_id, TaskStatus.PROCESSING.value, 10, f"Initializing analysis for {ticker}...")

            # Import the original stock analysis logic
            from ..api.stock import get_stock_analysis_data

            # Step 2: Fetch stock data
            self._update_task_status(task_id, TaskStatus.PROCESSING.value, 30, "Fetching market data...")

            # Step 3: Perform analysis
            self._update_task_status(task_id, TaskStatus.PROCESSING.value, 60, "Running AI analysis...")

            # Get the analysis result
            analysis_result = get_stock_analysis_data(ticker, style)

            if not analysis_result or 'error' in analysis_result:
                raise Exception(f"Stock analysis failed: {analysis_result.get('error', 'Unknown error')}")

            # Step 4: Save to history
            self._update_task_status(task_id, TaskStatus.PROCESSING.value, 90, "Saving analysis results...")

            # Create history record (with app context and fresh session)
            with self.app.app_context():
                # Create new session for this worker thread
                from sqlalchemy.orm import scoped_session, sessionmaker
                from ..models import db as db_instance

                # Get a fresh session for this thread
                session = db_instance.session

                try:
                    history_record = StockAnalysisHistory(
                        user_id=user_id,
                        ticker=ticker,
                        style=style,
                        current_price=analysis_result.get('current_price'),
                        target_price=analysis_result.get('target_price'),
                        stop_loss_price=analysis_result.get('stop_loss_price'),
                        market_sentiment=analysis_result.get('market_sentiment'),
                        risk_score=analysis_result.get('risk_score'),
                        risk_level=analysis_result.get('risk_level'),
                        position_size=analysis_result.get('position_size'),
                        ev_score=analysis_result.get('ev_score'),
                        ev_weighted_pct=analysis_result.get('ev_weighted_pct'),
                        recommendation_action=analysis_result.get('recommendation_action'),
                        recommendation_confidence=analysis_result.get('recommendation_confidence'),
                        ai_summary=analysis_result.get('ai_summary'),
                        full_analysis_data=convert_numpy_types(analysis_result)
                    )

                    session.add(history_record)
                    session.flush()  # Get the ID

                    # Store the history ID before committing
                    history_id = history_record.id

                    # Update task with results
                    task = session.query(AnalysisTask).get(task_id)
                    task.result_data = convert_numpy_types(analysis_result)
                    task.related_history_id = history_id
                    task.related_history_type = 'stock'

                    session.commit()

                except Exception as e:
                    session.rollback()
                    logger.error(f"Failed to save stock analysis history: {e}")
                    raise

            # Step 5: Complete task
            self._update_task_status(task_id, TaskStatus.COMPLETED.value, 100, "Analysis completed successfully")

            logger.info(f"Stock analysis completed for {ticker} - History ID: {history_id}")

        except Exception as e:
            logger.error(f"Stock analysis failed for {ticker}: {e}")
            raise

    def _process_options_analysis(self, task_data: Dict[str, Any]):
        """Process options analysis task"""
        task_id = task_data['task_id']
        user_id = task_data['user_id']
        params = task_data['input_params']

        symbol = params.get('symbol')
        analysis_type = task_data['task_type']

        logger.info(f"Processing options analysis for {symbol} ({analysis_type})")

        try:
            # Step 1: Initialize analysis
            self._update_task_status(task_id, TaskStatus.PROCESSING.value, 10, f"Initializing options analysis for {symbol}...")

            # Import the original options analysis logic
            from ..api.options import get_options_analysis_data

            # Step 2: Fetch options data
            self._update_task_status(task_id, TaskStatus.PROCESSING.value, 40, "Fetching options chain data...")

            # Step 3: Perform analysis
            self._update_task_status(task_id, TaskStatus.PROCESSING.value, 70, "Analyzing options strategies...")

            # Get the analysis result based on type
            if analysis_type == TaskType.ENHANCED_OPTION_ANALYSIS.value:
                # Enhanced analysis with specific option
                option_identifier = params.get('option_identifier')
                analysis_result = get_options_analysis_data(symbol, enhanced=True, option_identifier=option_identifier)
            else:
                # Basic options chain analysis
                expiry_date = params.get('expiry_date')
                logger.info(f"Options task params: {params}")
                logger.info(f"Extracted expiry_date: '{expiry_date}' (type: {type(expiry_date)})")
                analysis_result = get_options_analysis_data(symbol, enhanced=False, expiry_date=expiry_date)

            if not analysis_result or 'error' in analysis_result:
                raise Exception(f"Options analysis failed: {analysis_result.get('error', 'Unknown error')}")

            # Step 4: Save to history
            self._update_task_status(task_id, TaskStatus.PROCESSING.value, 90, "Saving analysis results...")

            # Create history record (with app context and fresh session)
            with self.app.app_context():
                # Create new session for this worker thread
                from sqlalchemy.orm import scoped_session, sessionmaker
                from ..models import db as db_instance

                # Get a fresh session for this thread
                session = db_instance.session

                try:
                    history_record = OptionsAnalysisHistory(
                        user_id=user_id,
                        symbol=symbol,
                        analysis_type=analysis_type,
                        option_identifier=params.get('option_identifier'),
                        expiry_date=params.get('expiry_date'),
                        strike_price=analysis_result.get('strike_price'),
                        option_type=analysis_result.get('option_type'),
                        option_score=analysis_result.get('option_score'),
                        iv_rank=analysis_result.get('iv_rank'),
                        vrp_analysis=analysis_result.get('vrp_analysis'),
                        risk_analysis=analysis_result.get('risk_analysis'),
                        ai_summary=analysis_result.get('ai_summary'),
                        full_analysis_data=convert_numpy_types(analysis_result)
                    )

                    session.add(history_record)
                    session.flush()  # Get the ID

                    # Store the history ID before committing
                    history_id = history_record.id

                    # Update task with results
                    task = session.query(AnalysisTask).get(task_id)
                    task.result_data = convert_numpy_types(analysis_result)
                    task.related_history_id = history_id
                    task.related_history_type = 'options'

                    session.commit()

                except Exception as e:
                    session.rollback()
                    logger.error(f"Failed to save options analysis history: {e}")
                    raise

            # Step 5: Complete task
            self._update_task_status(task_id, TaskStatus.COMPLETED.value, 100, "Options analysis completed successfully")

            logger.info(f"Options analysis completed for {symbol} - History ID: {history_id}")

        except Exception as e:
            logger.error(f"Options analysis failed for {symbol}: {e}")
            raise

# Global task queue instance
task_queue = None

def init_task_queue(app=None):
    """Initialize the global task queue with Flask app context"""
    global task_queue
    task_queue = TaskQueue(max_workers=3, app=app)
    task_queue.start()
    logger.info("Global task queue initialized")

def shutdown_task_queue():
    """Shutdown the global task queue"""
    task_queue.stop()
    logger.info("Global task queue shutdown")

# Convenience functions for external use
def create_analysis_task(user_id: str, task_type: str, input_params: Dict[str, Any], priority: int = 100) -> str:
    """Create a new analysis task"""
    return task_queue.create_task(user_id, task_type, input_params, priority)

def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """Get task status"""
    return task_queue.get_task_status(task_id)

def get_user_tasks(user_id: str, limit: int = 10, status: Optional[str] = None) -> list:
    """Get user's tasks"""
    return task_queue.get_user_tasks(user_id, limit, status)
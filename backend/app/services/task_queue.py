"""
Async Task Queue Management System

This module handles the creation, processing, and management of async analysis tasks.
Supports both stock analysis and options analysis tasks with progress tracking.
"""

import uuid
import logging
import threading
import time
from datetime import datetime, date
from queue import Queue, Empty
from typing import Optional, Dict, Any
from ..models import db, AnalysisTask, TaskType, TaskStatus, StockAnalysisHistory, OptionsAnalysisHistory, DailyAnalysisCache
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

    def create_task(self, user_id: str, task_type: str, input_params: Dict[str, Any], priority: int = 100,
                    cache_mode: str = None, cached_data: Dict = None, source_task_id: str = None) -> str:
        """
        Create a new analysis task

        Args:
            user_id: User ID creating the task
            task_type: Type of analysis (stock_analysis, option_analysis, etc.)
            input_params: Parameters for the analysis
            priority: Task priority (lower = higher priority)
            cache_mode: None for normal, 'cached' for fake progress with cached data,
                        'waiting' for waiting on another task to finish
            cached_data: Pre-computed analysis data (for cache_mode='cached')
            source_task_id: Task ID to wait for (for cache_mode='waiting')

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

            # Build task data for queue
            task_data = {
                'task_id': task_id,
                'user_id': user_id,
                'task_type': task_type,
                'input_params': input_params,
                'priority': priority,
                'created_at': datetime.utcnow(),
                'cache_mode': cache_mode,
                'cached_data': cached_data,
                'source_task_id': source_task_id,
            }

            # Add to queue for processing
            self.task_queue.put(task_data)

            logger.info(f"Task {task_id} created for user {user_id}: {task_type} (cache_mode={cache_mode})")
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

                    # Check cache mode first
                    cache_mode = task_data.get('cache_mode')

                    if cache_mode == 'cached':
                        # Fake progress with cached data
                        self._process_cached_task(task_data)
                    elif cache_mode == 'waiting':
                        # Wait for another task to finish, then use cached result
                        self._process_waiting_task(task_data)
                    elif task_data['task_type'] == TaskType.STOCK_ANALYSIS.value:
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
                
                # Truncate step message if too long (for display purposes, keep it concise)
                # Full error details should go to error_message field
                if step and len(step) > 1000:
                    task.current_step = step[:997] + "..."
                else:
                    task.current_step = step

                # Store full error message (can be long)
                if error_message:
                    # Truncate error message if extremely long (keep first 5000 chars)
                    if len(error_message) > 5000:
                        task.error_message = error_message[:4997] + "..."
                    else:
                        task.error_message = error_message
                elif status == TaskStatus.FAILED.value and step:
                    # If no explicit error_message but status is FAILED, use step as error
                    if len(step) > 5000:
                        task.error_message = step[:4997] + "..."
                    else:
                        task.error_message = step

                if status == TaskStatus.PROCESSING.value and not task.started_at:
                    task.started_at = datetime.utcnow()
                elif status in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value]:
                    task.completed_at = datetime.utcnow()

                db.session.commit()

            except Exception as e:
                logger.error(f"Failed to update task status for {task_id}: {e}")
                db.session.rollback()

    def _process_cached_task(self, task_data: Dict[str, Any]):
        """
        Process a task with cached data — simulate progress over ~10 seconds,
        then deliver the pre-computed result.
        """
        task_id = task_data['task_id']
        user_id = task_data['user_id']
        cached_data = task_data['cached_data']
        params = task_data['input_params']
        ticker = params.get('ticker', params.get('symbol', ''))

        logger.info(f"Processing cached task {task_id} for {ticker}")

        # Simulate realistic progress steps over ~10 seconds
        fake_steps = [
            (10, "Initializing analysis...", 1.5),
            (30, "Fetching market data...", 2.0),
            (55, "Calculating risk metrics...", 2.0),
            (75, "Running AI analysis...", 2.5),
            (90, "Generating report...", 1.5),
        ]

        for progress, step_msg, delay in fake_steps:
            self._update_task_status(task_id, TaskStatus.PROCESSING.value, progress, step_msg)
            time.sleep(delay)

        # Save history record and complete the task
        self._update_task_status(task_id, TaskStatus.PROCESSING.value, 95, "Saving analysis results...")

        with self.app.app_context():
            session = db.session
            try:
                # Save user's history record from cached data
                history_id = self._save_stock_history_from_cached(session, user_id, params, cached_data)

                # Update task with results
                task = session.query(AnalysisTask).get(task_id)
                task.result_data = cached_data
                task.related_history_id = history_id
                task.related_history_type = 'stock'
                session.commit()

            except Exception as e:
                session.rollback()
                logger.error(f"Failed to save cached task result: {e}")
                raise

        self._update_task_status(task_id, TaskStatus.COMPLETED.value, 100, "Analysis completed successfully")
        logger.info(f"Cached task {task_id} completed for {ticker}")

    def _process_waiting_task(self, task_data: Dict[str, Any]):
        """
        Wait for another in-progress task to complete, then use its cached result.
        Creates a separate task record for this user but shares the analysis result.
        """
        task_id = task_data['task_id']
        user_id = task_data['user_id']
        source_task_id = task_data['source_task_id']
        params = task_data['input_params']
        ticker = params.get('ticker', '')
        style = params.get('style', 'quality')

        logger.info(f"Waiting task {task_id} waiting for source task {source_task_id}")

        # Show initial progress while waiting
        self._update_task_status(task_id, TaskStatus.PROCESSING.value, 10, "Initializing analysis...")
        time.sleep(1.0)
        self._update_task_status(task_id, TaskStatus.PROCESSING.value, 20, "Fetching market data...")

        # Poll for the source task to complete (max 5 minutes)
        max_wait = 300  # seconds
        poll_interval = 2  # seconds
        waited = 0
        cached_data = None

        while waited < max_wait:
            with self.app.app_context():
                # First check if cache entry exists now (source task may have completed)
                cache_entry = DailyAnalysisCache.query.filter_by(
                    ticker=ticker, style=style, analysis_date=date.today()
                ).first()

                if cache_entry:
                    cached_data = cache_entry.full_analysis_data
                    logger.info(f"Waiting task {task_id} found cache entry for {ticker}/{style}")
                    break

                # Also check if source task failed
                source_task = AnalysisTask.query.get(source_task_id)
                if source_task and source_task.status == TaskStatus.FAILED.value:
                    raise Exception(f"Source task {source_task_id} failed: {source_task.error_message}")

            # Simulate gradual progress while waiting
            progress = min(20 + int(waited / max_wait * 50), 70)
            step_msgs = ["Fetching market data...", "Calculating risk metrics...", "Running AI analysis..."]
            step_msg = step_msgs[min(waited // 20, len(step_msgs) - 1)]
            self._update_task_status(task_id, TaskStatus.PROCESSING.value, progress, step_msg)

            time.sleep(poll_interval)
            waited += poll_interval

        if not cached_data:
            raise Exception(f"Timed out waiting for source task {source_task_id} to complete")

        # Simulate final steps
        self._update_task_status(task_id, TaskStatus.PROCESSING.value, 80, "Generating report...")
        time.sleep(1.5)
        self._update_task_status(task_id, TaskStatus.PROCESSING.value, 95, "Saving analysis results...")

        # Save history and complete
        with self.app.app_context():
            session = db.session
            try:
                history_id = self._save_stock_history_from_cached(session, user_id, params, cached_data)

                task = session.query(AnalysisTask).get(task_id)
                task.result_data = cached_data
                task.related_history_id = history_id
                task.related_history_type = 'stock'
                session.commit()

            except Exception as e:
                session.rollback()
                logger.error(f"Failed to save waiting task result: {e}")
                raise

        self._update_task_status(task_id, TaskStatus.COMPLETED.value, 100, "Analysis completed successfully")
        logger.info(f"Waiting task {task_id} completed for {ticker}")

    def _save_stock_history_from_cached(self, session, user_id: str, params: Dict, cached_data: Dict) -> int:
        """
        Save a StockAnalysisHistory record from cached analysis data.
        Returns the history record ID.
        """
        ticker = params.get('ticker', '')
        style = params.get('style', 'quality')

        # Extract fields from the cached full analysis data
        market_data = cached_data.get('data', {})
        risk_result = cached_data.get('risk', {})
        ev_result = market_data.get('ev_model', {})
        ai_report = cached_data.get('report', '')

        ai_summary = None
        if isinstance(ai_report, dict):
            ai_summary = ai_report.get('summary', '')[:1000] if ai_report.get('summary') else None
        elif isinstance(ai_report, str):
            ai_summary = ai_report[:1000] if ai_report else None

        history_record = StockAnalysisHistory(
            user_id=user_id,
            ticker=ticker,
            style=style,
            current_price=market_data.get('price'),
            target_price=market_data.get('target_price'),
            stop_loss_price=market_data.get('stop_loss_price'),
            market_sentiment=market_data.get('market_sentiment'),
            risk_score=risk_result.get('score'),
            risk_level=risk_result.get('level'),
            position_size=risk_result.get('suggested_position'),
            ev_score=ev_result.get('ev_score'),
            ev_weighted_pct=ev_result.get('ev_weighted_pct'),
            recommendation_action=ev_result.get('recommendation', {}).get('action'),
            recommendation_confidence=ev_result.get('recommendation', {}).get('confidence'),
            ai_summary=ai_summary,
            full_analysis_data=cached_data
        )

        session.add(history_record)
        session.flush()

        return history_record.id

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

            # Step 4: Save to history and cache
            self._update_task_status(task_id, TaskStatus.PROCESSING.value, 90, "Saving analysis results...")

            # Create history record and cache entry (with app context)
            with self.app.app_context():
                from ..models import db as db_instance

                session = db_instance.session

                try:
                    # Convert numpy types for JSON storage
                    clean_result = convert_numpy_types(analysis_result)

                    # Save user's analysis history
                    history_id = self._save_stock_history_from_cached(session, user_id, params, clean_result)

                    # Save to daily analysis cache (INSERT ... ON CONFLICT DO NOTHING equivalent)
                    try:
                        cache_entry = DailyAnalysisCache(
                            ticker=ticker,
                            style=style,
                            analysis_date=date.today(),
                            full_analysis_data=clean_result,
                            source_task_id=task_id
                        )
                        session.add(cache_entry)
                        session.flush()
                        logger.info(f"Saved analysis to daily cache: {ticker}/{style}")
                    except Exception as cache_err:
                        # Unique constraint violation — another task already cached this
                        session.rollback()
                        logger.info(f"Cache entry already exists for {ticker}/{style} today, skipping: {cache_err}")
                        # Re-save history since rollback cleared it
                        history_id = self._save_stock_history_from_cached(session, user_id, params, clean_result)

                    # Update task with results
                    task = session.query(AnalysisTask).get(task_id)
                    task.result_data = clean_result
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
                    # Map task_type to analysis_type for database storage
                    # TaskType.OPTION_ANALYSIS -> 'basic_chain'
                    # TaskType.ENHANCED_OPTION_ANALYSIS -> 'enhanced_analysis'
                    db_analysis_type = 'basic_chain' if analysis_type == TaskType.OPTION_ANALYSIS.value else 'enhanced_analysis'
                    
                    history_record = OptionsAnalysisHistory(
                        user_id=user_id,
                        symbol=symbol,
                        analysis_type=db_analysis_type,
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
def create_analysis_task(user_id: str, task_type: str, input_params: Dict[str, Any], priority: int = 100,
                         cache_mode: str = None, cached_data: Dict = None, source_task_id: str = None) -> str:
    """Create a new analysis task"""
    return task_queue.create_task(user_id, task_type, input_params, priority,
                                  cache_mode=cache_mode, cached_data=cached_data,
                                  source_task_id=source_task_id)

def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """Get task status"""
    return task_queue.get_task_status(task_id)

def get_user_tasks(user_id: str, limit: int = 10, status: Optional[str] = None) -> list:
    """Get user's tasks"""
    return task_queue.get_user_tasks(user_id, limit, status)
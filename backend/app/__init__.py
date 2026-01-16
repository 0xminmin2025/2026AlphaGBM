from flask import Flask
from flask_cors import CORS
import os
import logging
import atexit
from .config import Config

# Initialize extensions
# db = SQLAlchemy() # Will be initialized in models

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Configure Logging
    log_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # File handler - saves to logs/backend.log
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    file_handler = logging.FileHandler(os.path.join(log_dir, 'backend.log'))
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(log_formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(log_formatter)

    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        handlers=[file_handler, console_handler]
    )

    # CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Initialize Extensions
    from .models import db
    db.init_app(app)

    # Initialize Task Queue (always needed for API endpoints)
    from .services.task_queue import init_task_queue, shutdown_task_queue
    with app.app_context():
        init_task_queue(app)
    atexit.register(shutdown_task_queue)

    # Initialize Scheduler (only in production/normal mode, not in debug reloader)
    if not os.environ.get('WERKZEUG_RUN_MAIN'):
        from .scheduler import init_scheduler, shutdown_scheduler

        # Initialize scheduler immediately during app creation
        with app.app_context():
            init_scheduler(app)

        # Ensure scheduler shuts down properly
        atexit.register(shutdown_scheduler)

    # Register Blueprints
    from .api.auth import auth_bp
    from .api.user import user_bp
    from .api.stock import stock_bp
    from .api.options import options_bp
    from .api.payment import payment_bp
    from .api.portfolio import portfolio_bp
    from .api.tasks import tasks_bp
    from .docs import docs_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(stock_bp)
    app.register_blueprint(options_bp)
    app.register_blueprint(payment_bp)
    app.register_blueprint(portfolio_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(docs_bp)

    @app.route('/health')
    def health():
        return {'status': 'ok'}

    # Add manual scheduler trigger endpoint for testing
    @app.route('/api/admin/trigger-profit-calculation')
    def trigger_profit_calculation():
        try:
            from .scheduler import calculate_daily_profit_loss
            calculate_daily_profit_loss()
            return {'success': True, 'message': 'Profit/loss calculation completed'}
        except Exception as e:
            return {'success': False, 'error': str(e)}, 500

    return app

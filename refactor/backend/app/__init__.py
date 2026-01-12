from flask import Flask
from flask_cors import CORS
import os
import logging
from .config import Config

# Initialize extensions
# db = SQLAlchemy() # Will be initialized in models

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Configure Logging
    logging.basicConfig(level=logging.INFO)
    
    # CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # Initialize Extensions
    from .models import db
    db.init_app(app)
    
    # Register Blueprints
    from .api.auth import auth_bp
    from .api.user import user_bp
    from .api.stock import stock_bp
    from .api.options import options_bp
    from .api.payment import payment_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(stock_bp)
    app.register_blueprint(options_bp)
    app.register_blueprint(payment_bp)
    
    @app.route('/health')
    def health():
        return {'status': 'ok'}
        
    return app

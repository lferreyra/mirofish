"""
MiroFish Backend - Flask application factory
"""

import os
import warnings

# Suppress multiprocessing resource_tracker warnings (from third-party libs like transformers)
warnings.filterwarnings("ignore", message=".*resource_tracker.*")

from flask import Flask, request, jsonify
from flask_cors import CORS

from .config import Config
from .utils.logger import setup_logger, get_logger


def create_app(config_class=Config):
    """Flask application factory."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # JSON encoding: allow non-ASCII characters to display directly
    if hasattr(app, 'json') and hasattr(app.json, 'ensure_ascii'):
        app.json.ensure_ascii = False

    # Setup logging
    logger = setup_logger('mirofish')

    # Only log startup info once (avoid double-logging in debug reloader)
    is_reloader_process = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
    debug_mode = app.config.get('DEBUG', False)
    should_log_startup = not debug_mode or is_reloader_process

    if should_log_startup:
        logger.info("=" * 50)
        logger.info("MiroFish Backend starting...")
        logger.info("=" * 50)

    # Initialize database
    from .database import Database
    db = Database(app.config.get('DB_PATH', Config.DB_PATH))
    db.init_db()

    # CORS - configurable origins (defaults to '*' for local dev)
    allowed_origins = os.environ.get('CORS_ORIGINS', '*').split(',')
    CORS(app, resources={r"/api/*": {"origins": [o.strip() for o in allowed_origins]}})

    # Register simulation process cleanup
    from .services.simulation_runner import SimulationRunner
    SimulationRunner.register_cleanup()
    if should_log_startup:
        logger.info("Registered simulation process cleanup handler")

    # --- Authentication middleware ---
    @app.before_request
    def check_auth():
        # Skip auth for health check and non-API routes
        if request.path == '/health' or not request.path.startswith('/api/'):
            return None

        api_key = os.environ.get('MIROFISH_API_KEY')
        if not api_key:
            return None  # Auth disabled when no key configured

        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
        else:
            token = request.headers.get('X-API-Key', '')

        if token != api_key:
            return jsonify({"success": False, "error": "Unauthorized"}), 401

    # --- Request logging middleware (no body logging for security) ---
    @app.before_request
    def log_request():
        req_logger = get_logger('mirofish.request')
        req_logger.debug(f"Request: {request.method} {request.path}")

    @app.after_request
    def log_response(response):
        req_logger = get_logger('mirofish.request')
        req_logger.debug(f"Response: {response.status_code}")
        return response

    # --- Security headers ---
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response

    # Register blueprints
    from .api import graph_bp, simulation_bp, report_bp
    app.register_blueprint(graph_bp, url_prefix='/api/graph')
    app.register_blueprint(simulation_bp, url_prefix='/api/simulation')
    app.register_blueprint(report_bp, url_prefix='/api/report')

    # Health check
    @app.route('/health')
    def health():
        return {'status': 'ok', 'service': 'MiroFish Backend'}

    if should_log_startup:
        logger.info("MiroFish Backend started successfully")

    return app

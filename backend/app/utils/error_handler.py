"""
Centralized API error handler.
Logs full traceback server-side, returns generic error to clients.
"""

import uuid
import traceback
from flask import jsonify, current_app

from .logger import get_logger

logger = get_logger('mirofish.error')


def handle_api_error(e, context=""):
    """Handle an API error: log full trace, return safe response."""
    error_id = uuid.uuid4().hex[:8]
    logger.error(f"[{error_id}] API error [{context}]: {str(e)}")
    logger.debug(traceback.format_exc())

    if current_app.config.get('DEBUG'):
        return jsonify({
            "success": False,
            "error": str(e),
            "error_id": error_id,
            "traceback": traceback.format_exc()
        }), 500

    return jsonify({
        "success": False,
        "error": "Internal server error",
        "error_id": error_id
    }), 500

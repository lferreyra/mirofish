import importlib.util
from pathlib import Path

from flask import Flask, jsonify


def load_module(module_name: str, relative_path: str):
    module_path = Path(__file__).resolve().parents[1] / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


error_response_module = load_module('mirofish_error_response_for_test', 'app/utils/error_response.py')
sanitize_error_payload = error_response_module.sanitize_error_payload
sanitize_json_error_response = error_response_module.sanitize_json_error_response


def test_sanitize_error_payload_removes_traceback_for_server_errors():
    payload = {
        'success': False,
        'error': 'boom',
        'traceback': 'sensitive stack'
    }

    sanitized = sanitize_error_payload(payload, status_code=500, debug_mode=False)

    assert 'traceback' not in sanitized
    assert sanitized['error'] == 'boom'


def test_sanitize_error_payload_keeps_traceback_in_debug_mode():
    payload = {
        'success': False,
        'error': 'boom',
        'traceback': 'sensitive stack'
    }

    sanitized = sanitize_error_payload(payload, status_code=500, debug_mode=True)

    assert sanitized == payload


def test_sanitize_json_error_response_preserves_non_server_responses():
    app = Flask(__name__)

    with app.app_context():
        response = jsonify({
            'success': False,
            'error': 'bad request',
            'traceback': 'validation details'
        })
        response.status_code = 400

        sanitize_json_error_response(response, debug_mode=False)

        assert response.get_json()['traceback'] == 'validation details'

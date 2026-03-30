from flask import Blueprint, jsonify
from app.i18n import get_all_patterns, get_language

config_bp = Blueprint('config', __name__)

@config_bp.route('/language', methods=['GET'])
def get_lang():
    return jsonify({'language': get_language()})

@config_bp.route('/patterns', methods=['GET'])
def get_patterns():
    return jsonify({'patterns': get_all_patterns()})

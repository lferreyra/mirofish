"""
AUGUR — Autenticação JWT
Requer: pip install flask-jwt-extended --break-system-packages

Uso:
  1. POST /api/auth/register → {email, password, name}
  2. POST /api/auth/login → {email, password} → retorna {token}
  3. Rotas protegidas: adicionar @jwt_required() no endpoint
"""
import os
import json
import hashlib
import secrets
import logging
from datetime import timedelta
from functools import wraps

from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

try:
    from flask_jwt_extended import (
        JWTManager, create_access_token, jwt_required, 
        get_jwt_identity, get_jwt
    )
    HAS_JWT = True
except ImportError:
    HAS_JWT = False
    logger.warning("flask-jwt-extended não instalado. Auth desabilitado.")
    # Stubs para não quebrar imports
    def jwt_required(optional=False):
        def decorator(fn):
            @wraps(fn)
            def wrapper(*args, **kwargs):
                return fn(*args, **kwargs)
            return wrapper
        return decorator
    def get_jwt_identity():
        return None

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# ═══ Storage simples (JSON file) — substituir por DB real em produção ═══
USERS_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'users.json')


def _ensure_data_dir():
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w') as f:
            json.dump([], f)


def _load_users() -> list:
    _ensure_data_dir()
    with open(USERS_FILE, 'r') as f:
        return json.load(f)


def _save_users(users: list):
    _ensure_data_dir()
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def _hash_password(password: str, salt: str = None) -> tuple:
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
    return hashed, salt


def _verify_password(password: str, hashed: str, salt: str) -> bool:
    check, _ = _hash_password(password, salt)
    return check == hashed


def init_jwt(app):
    """Inicializa JWT no app Flask."""
    if not HAS_JWT:
        logger.warning("JWT não configurado — flask-jwt-extended não instalado")
        return None
    
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', secrets.token_hex(32))
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=7)
    app.config['JWT_TOKEN_LOCATION'] = ['headers']
    
    jwt = JWTManager(app)
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({"success": False, "error": "Token expirado. Faça login novamente."}), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({"success": False, "error": "Token inválido."}), 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({"success": False, "error": "Token não fornecido. Faça login."}), 401
    
    logger.info("JWT configurado com sucesso")
    return jwt


# ═══ ENDPOINTS ═══

@auth_bp.route('/register', methods=['POST'])
def register():
    """Registrar novo usuário."""
    data = request.get_json()
    email = (data.get('email') or '').strip().lower()
    password = data.get('password', '')
    name = data.get('name', '').strip()
    
    if not email or not password:
        return jsonify({"success": False, "error": "Email e senha são obrigatórios."}), 400
    
    if len(password) < 6:
        return jsonify({"success": False, "error": "Senha deve ter no mínimo 6 caracteres."}), 400
    
    users = _load_users()
    if any(u['email'] == email for u in users):
        return jsonify({"success": False, "error": "Email já registrado."}), 409
    
    hashed, salt = _hash_password(password)
    user = {
        "id": secrets.token_hex(8),
        "email": email,
        "name": name or email.split("@")[0],
        "password_hash": hashed,
        "password_salt": salt,
        "created_at": __import__('datetime').datetime.utcnow().isoformat()
    }
    users.append(user)
    _save_users(users)
    
    if HAS_JWT:
        token = create_access_token(identity=user['id'], additional_claims={"email": email, "name": user['name']})
    else:
        token = "jwt-not-configured"
    
    return jsonify({
        "success": True,
        "data": {
            "token": token,
            "user": {"id": user['id'], "email": email, "name": user['name']}
        }
    }), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    """Login."""
    data = request.get_json()
    email = (data.get('email') or '').strip().lower()
    password = data.get('password', '')
    
    if not email or not password:
        return jsonify({"success": False, "error": "Email e senha são obrigatórios."}), 400
    
    users = _load_users()
    user = next((u for u in users if u['email'] == email), None)
    
    if not user or not _verify_password(password, user['password_hash'], user['password_salt']):
        return jsonify({"success": False, "error": "Email ou senha inválidos."}), 401
    
    if HAS_JWT:
        token = create_access_token(identity=user['id'], additional_claims={"email": email, "name": user['name']})
    else:
        token = "jwt-not-configured"
    
    return jsonify({
        "success": True,
        "data": {
            "token": token,
            "user": {"id": user['id'], "email": email, "name": user['name']}
        }
    })


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    """Dados do usuário logado."""
    user_id = get_jwt_identity()
    users = _load_users()
    user = next((u for u in users if u['id'] == user_id), None)
    
    if not user:
        return jsonify({"success": False, "error": "Usuário não encontrado."}), 404
    
    return jsonify({
        "success": True,
        "data": {"id": user['id'], "email": user['email'], "name": user['name']}
    })

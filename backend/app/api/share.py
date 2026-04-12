"""
AUGUR — Link público para clientes
Gera código de acesso e serve relatório público sem login.
"""
import os
import json
import uuid
import hashlib
import logging
from datetime import datetime
from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

share_bp = Blueprint('share', __name__, url_prefix='/api/share')

SHARE_DIR = os.environ.get('SHARE_DATA_DIR', '/app/data/shares')


def _ensure_dir():
    os.makedirs(SHARE_DIR, exist_ok=True)


def _share_path(code):
    return os.path.join(SHARE_DIR, f"{code}.json")


@share_bp.route('/create', methods=['POST'])
def create_share():
    """
    Gerar link público para um relatório.
    Body: { "report_id": "xxx", "client_name": "Empresa ABC" }
    Returns: { "code": "abc123", "url": "/relatorio-publico/abc123" }
    """
    _ensure_dir()
    data = request.get_json() or {}
    report_id = data.get('report_id', '')
    client_name = data.get('client_name', '')

    if not report_id:
        return jsonify({"success": False, "error": "report_id obrigatório"}), 400

    # Gerar código curto (6 chars)
    raw = f"{report_id}-{uuid.uuid4().hex[:8]}"
    code = hashlib.sha256(raw.encode()).hexdigest()[:8].upper()

    share_data = {
        "code": code,
        "report_id": report_id,
        "client_name": client_name,
        "created_at": datetime.utcnow().isoformat(),
        "views": 0,
        "active": True
    }

    with open(_share_path(code), 'w') as f:
        json.dump(share_data, f, indent=2)

    logger.info(f"Share created: {code} for report {report_id}")

    return jsonify({
        "success": True,
        "data": {
            "code": code,
            "url": f"/relatorio-publico/{code}",
            "report_id": report_id,
            "client_name": client_name
        }
    })


@share_bp.route('/<code>', methods=['GET'])
def get_shared_report(code):
    """
    Acessar relatório público pelo código.
    Retorna os mesmos dados de /api/report/:id mas sem autenticação.
    """
    _ensure_dir()
    spath = _share_path(code.upper())

    if not os.path.exists(spath):
        return jsonify({"success": False, "error": "Código inválido ou expirado"}), 404

    with open(spath) as f:
        share_data = json.load(f)

    if not share_data.get('active', True):
        return jsonify({"success": False, "error": "Link desativado"}), 403

    # Incrementar views
    share_data['views'] = share_data.get('views', 0) + 1
    share_data['last_viewed'] = datetime.utcnow().isoformat()
    with open(spath, 'w') as f:
        json.dump(share_data, f, indent=2)

    # Carregar relatório real
    report_id = share_data.get('report_id', '')
    try:
        from ..services.report_agent import ReportManager
        report = ReportManager.get_report(report_id)
        if not report:
            return jsonify({"success": False, "error": "Relatório não encontrado"}), 404

        report_dict = report.to_dict()
        report_dict['client_name'] = share_data.get('client_name', '')
        report_dict['share_code'] = code
        report_dict['share_views'] = share_data['views']

        return jsonify({"success": True, "data": report_dict})

    except Exception as e:
        logger.error(f"Share access error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@share_bp.route('/<code>/deactivate', methods=['POST'])
def deactivate_share(code):
    """Desativar link público."""
    _ensure_dir()
    spath = _share_path(code.upper())
    if not os.path.exists(spath):
        return jsonify({"success": False, "error": "Não encontrado"}), 404

    with open(spath) as f:
        share_data = json.load(f)
    share_data['active'] = False
    with open(spath, 'w') as f:
        json.dump(share_data, f, indent=2)

    return jsonify({"success": True, "message": "Link desativado"})

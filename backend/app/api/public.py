"""
AUGUR Public API
Endpoints públicos para compartilhar relatórios via token.
Não requer autenticação.
"""

import uuid
import json
import os
import logging
from flask import Blueprint, jsonify, request
from ..services.report_agent import ReportManager
from ..config import Config

logger = logging.getLogger(__name__)

public_bp = Blueprint('public', __name__)


def _get_report_by_token(token: str):
    """Busca relatório pelo public_token."""
    reports_dir = os.path.join(Config.UPLOAD_FOLDER, 'reports')
    if not os.path.exists(reports_dir):
        return None
    
    for report_id in os.listdir(reports_dir):
        meta_path = os.path.join(reports_dir, report_id, 'meta.json')
        if not os.path.exists(meta_path):
            # Formato antigo
            meta_path = os.path.join(reports_dir, f"{report_id}.json")
            if not os.path.exists(meta_path):
                continue
        
        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if data.get('public_token') == token:
                return ReportManager.get_report(report_id)
        except Exception:
            continue
    
    return None


@public_bp.route('/report/<token>', methods=['GET'])
def get_public_report(token: str):
    """Obter relatório público via token."""
    report = _get_report_by_token(token)
    if not report:
        return jsonify({"success": False, "error": "Relatório não encontrado ou link expirado"}), 404
    
    data = report.to_dict()
    # Remover campos sensíveis
    data.pop('graph_id', None)
    
    return jsonify({"success": True, "data": data})


@public_bp.route('/report/<token>/chat', methods=['POST'])
def public_chat(token: str):
    """Chat com ReportAgent via link público."""
    report = _get_report_by_token(token)
    if not report:
        return jsonify({"success": False, "error": "Relatório não encontrado"}), 404
    
    body = request.get_json() or {}
    message = body.get('message', '')
    chat_history = body.get('chat_history', [])
    
    if not message:
        return jsonify({"success": False, "error": "Mensagem obrigatória"}), 400
    
    # Proxy para o chat existente
    from ..api.report import _do_chat
    try:
        response = _do_chat(report.simulation_id, message, chat_history)
        return jsonify({"success": True, "data": {"response": response}})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@public_bp.route('/report/<token>/interview', methods=['POST'])
def public_interview(token: str):
    """Entrevista com agente via link público."""
    report = _get_report_by_token(token)
    if not report:
        return jsonify({"success": False, "error": "Relatório não encontrado"}), 404
    
    body = request.get_json() or {}
    
    # Proxy para interview existente
    from ..api.simulation import _do_interview
    try:
        response = _do_interview(
            report.simulation_id,
            body.get('agent_id'),
            body.get('prompt', ''),
            body.get('platform', 'twitter')
        )
        return jsonify({"success": True, "data": response})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@public_bp.route('/report/<token>/analytics', methods=['GET'])
def public_analytics(token: str):
    """Analytics da simulação via link público."""
    report = _get_report_by_token(token)
    if not report:
        return jsonify({"success": False, "error": "Relatório não encontrado"}), 404
    
    from ..api.analytics import get_analytics
    # Inject simulation_id into the request context
    try:
        from flask import g
        return get_analytics(report.simulation_id)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ═══ Utility: gerar token para relatório ═══

@public_bp.route('/report/<report_id>/share', methods=['POST'])
def generate_share_link(report_id: str):
    """Gerar link público para um relatório."""
    report = ReportManager.get_report(report_id)
    if not report:
        return jsonify({"success": False, "error": "Relatório não encontrado"}), 404
    
    # Verificar se já tem token
    meta_path = os.path.join(Config.UPLOAD_FOLDER, 'reports', report_id, 'meta.json')
    if not os.path.exists(meta_path):
        meta_path = os.path.join(Config.UPLOAD_FOLDER, 'reports', f"{report_id}.json")
    
    with open(meta_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if not data.get('public_token'):
        data['public_token'] = str(uuid.uuid4())[:12]
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    token = data['public_token']
    
    return jsonify({
        "success": True,
        "data": {
            "token": token,
            "url": f"/r/{token}"
        }
    })

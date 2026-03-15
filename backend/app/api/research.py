"""
Research-mode API routes.

These endpoints define the first stable backend surface for bottleneck-focused
research projects, without changing the existing simulation flow.
"""

import traceback

from flask import jsonify, request

from . import research_bp
from ..models.research_project import ResearchProjectManager
from ..services import build_research_ontology_spec
from ..utils.logger import get_logger

logger = get_logger("mirofish.api.research")


@research_bp.route("/ontology", methods=["GET"])
def get_research_ontology():
    """Return the canonical research ontology specification."""
    return jsonify({
        "success": True,
        "data": build_research_ontology_spec(),
    })


@research_bp.route("/project", methods=["POST"])
def create_research_project():
    """Create a research-mode project."""
    try:
        data = request.get_json() or {}
        project = ResearchProjectManager.create_project(
            name=data.get("name", "Unnamed Research Project"),
            ontology_name=data.get("ontology_name", "bottleneck_research"),
            ontology_version=data.get("ontology_version", "v1"),
            thesis_intake=data.get("thesis_intake"),
            tags=data.get("tags"),
            focus_areas=data.get("focus_areas"),
        )

        return jsonify({
            "success": True,
            "data": project.to_dict(),
        }), 201
    except Exception as e:
        logger.error(f"创建研究项目失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
        }), 500


@research_bp.route("/project/list", methods=["GET"])
def list_research_projects():
    """List research-mode projects."""
    limit = request.args.get("limit", 50, type=int)
    projects = ResearchProjectManager.list_projects(limit=limit)
    return jsonify({
        "success": True,
        "data": [project.to_dict() for project in projects],
        "count": len(projects),
    })


@research_bp.route("/project/<research_project_id>", methods=["GET"])
def get_research_project(research_project_id: str):
    """Fetch a single research project."""
    project = ResearchProjectManager.get_project(research_project_id)
    if not project:
        return jsonify({
            "success": False,
            "error": f"研究项目不存在: {research_project_id}",
        }), 404

    return jsonify({
        "success": True,
        "data": project.to_dict(),
    })


@research_bp.route("/project/<research_project_id>", methods=["DELETE"])
def delete_research_project(research_project_id: str):
    """Delete a research project and its artifacts."""
    success = ResearchProjectManager.delete_project(research_project_id)
    if not success:
        return jsonify({
            "success": False,
            "error": f"研究项目不存在或删除失败: {research_project_id}",
        }), 404

    return jsonify({
        "success": True,
        "message": f"研究项目已删除: {research_project_id}",
    })


@research_bp.route("/project/<research_project_id>/artifacts", methods=["GET"])
def get_research_project_artifacts(research_project_id: str):
    """Return the current persisted artifact bundle."""
    try:
        return jsonify({
            "success": True,
            "data": ResearchProjectManager.get_artifacts(research_project_id),
        })
    except ValueError as e:
        return jsonify({
            "success": False,
            "error": str(e),
        }), 404


@research_bp.route("/project/<research_project_id>/thesis-intake", methods=["POST"])
def save_thesis_intake(research_project_id: str):
    """Persist thesis-intake data for a research project."""
    try:
        thesis_intake = request.get_json() or {}
        project = ResearchProjectManager.save_thesis_intake(
            research_project_id, thesis_intake
        )
        return jsonify({
            "success": True,
            "data": {
                "research_project": project.to_dict(),
                "thesis_intake": thesis_intake,
            },
        })
    except ValueError as e:
        return jsonify({
            "success": False,
            "error": str(e),
        }), 404
    except Exception as e:
        logger.error(f"保存 thesis intake 失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
        }), 500


@research_bp.route("/project/<research_project_id>/claims-audit", methods=["POST"])
def save_claims_audit(research_project_id: str):
    """Persist structured claims-audit rows for a research project."""
    try:
        payload = request.get_json() or {}
        claims_audit = payload.get("rows")
        if claims_audit is None:
            claims_audit = payload if isinstance(payload, list) else []
        if not isinstance(claims_audit, list):
            return jsonify({
                "success": False,
                "error": "claims audit payload must be a list or {\"rows\": [...]}",
            }), 400

        project = ResearchProjectManager.save_claims_audit(
            research_project_id, claims_audit
        )
        return jsonify({
            "success": True,
            "data": {
                "research_project": project.to_dict(),
                "claims_audit_count": len(claims_audit),
            },
        })
    except ValueError as e:
        return jsonify({
            "success": False,
            "error": str(e),
        }), 404
    except Exception as e:
        logger.error(f"保存 claims audit 失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
        }), 500


@research_bp.route("/project/<research_project_id>/scorecards", methods=["POST"])
def save_scorecards(research_project_id: str):
    """Persist scorecard rows for a research project."""
    try:
        payload = request.get_json() or {}
        scorecards = payload.get("rows")
        if scorecards is None:
            scorecards = payload if isinstance(payload, list) else []
        if not isinstance(scorecards, list):
            return jsonify({
                "success": False,
                "error": "scorecards payload must be a list or {\"rows\": [...]}",
            }), 400

        project = ResearchProjectManager.save_scorecards(
            research_project_id, scorecards
        )
        return jsonify({
            "success": True,
            "data": {
                "research_project": project.to_dict(),
                "scorecard_count": len(scorecards),
            },
        })
    except ValueError as e:
        return jsonify({
            "success": False,
            "error": str(e),
        }), 404
    except Exception as e:
        logger.error(f"保存 scorecards 失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
        }), 500


@research_bp.route("/project/<research_project_id>/summary", methods=["POST"])
def save_summary(research_project_id: str):
    """Persist summary/report metadata for a research project."""
    try:
        summary = request.get_json() or {}
        project = ResearchProjectManager.save_summary(research_project_id, summary)
        return jsonify({
            "success": True,
            "data": {
                "research_project": project.to_dict(),
                "summary": summary,
            },
        })
    except ValueError as e:
        return jsonify({
            "success": False,
            "error": str(e),
        }), 404
    except Exception as e:
        logger.error(f"保存 summary 失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
        }), 500

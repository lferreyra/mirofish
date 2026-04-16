"""
Private Impact API routes.

Exposes the /api/private-impact endpoints for the Private Impact simulation mode.
Follows the same error handling and JSON response format as graph/simulation/report blueprints.
"""

import json
import os
import traceback
import threading
import uuid
from datetime import datetime

from flask import request, jsonify

from . import private_bp
from ..config import Config
from ..services.private_impact_profile_generator import PrivateImpactProfileGenerator
from ..services.private_impact_config_generator import PrivateImpactConfigGenerator
from ..services.private_impact_runner import PrivateImpactRunner
from ..services.zep_entity_reader import ZepEntityReader
from ..services.report_agent import ReportAgent, ReportManager, ReportStatus
from ..models.task import TaskManager, TaskStatus
from ..models.project import ProjectManager
from ..utils.logger import get_logger
from ..utils.locale import t, get_locale, set_locale

logger = get_logger('mirofish.api.private')

# Simulation data directory (same root as PrivateImpactRunner.RUN_STATE_DIR)
_SIM_DIR = os.path.join(os.path.dirname(__file__), '../../uploads/simulations')

# Relational entity types recognised by PrivateImpactProfileGenerator
_RELATIONAL_ENTITY_TYPES = [
    "employee", "manager", "client", "competitor",
    "partner", "familymember", "colleague", "investor",
]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _sim_dir(sim_id: str) -> str:
    """Return absolute path to the simulation directory."""
    return os.path.join(_SIM_DIR, sim_id)


def _meta_path(sim_id: str) -> str:
    return os.path.join(_sim_dir(sim_id), "private_meta.json")


def _read_meta(sim_id: str) -> dict:
    """Load private_meta.json; return empty dict if missing."""
    path = _meta_path(sim_id)
    if not os.path.exists(path):
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _write_meta(sim_id: str, meta: dict) -> None:
    """Persist private_meta.json to disk."""
    os.makedirs(_sim_dir(sim_id), exist_ok=True)
    with open(_meta_path(sim_id), 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


# ── POST /api/private-impact/prepare ──────────────────────────────────────────

@private_bp.route('/private-impact/prepare', methods=['POST'])
def prepare_private_simulation():
    """
    Prepare a Private Impact simulation.

    Reads relational entities from the Zep graph, generates RelationalAgentProfile
    instances via PrivateImpactProfileGenerator, then generates the full
    PrivateSimulationParameters via PrivateImpactConfigGenerator.
    Saves private_agents.json and private_simulation_config.json in the sim dir.

    Request (JSON):
        {
            "graph_id": "mirofish_xxxx",          // Required (or project_id)
            "project_id": "proj_xxxx",            // Optional — used to resolve graph_id / sim_requirement
            "simulation_requirement": "...",      // Required if no project_id
            "decision_context": "...",            // Optional
            "use_llm": true,                      // Optional, default true
            "entity_types": ["employee", ...],    // Optional filter (defaults to all relational types)
            "sim_id": "private_xxxx"              // Optional — reuse an existing sim_id
        }

    Returns:
        { "success": true, "data": { "sim_id": "...", "agent_count": N, "status": "prepared" } }
    """
    try:
        data = request.get_json() or {}

        # Resolve graph_id and simulation_requirement
        project_id = data.get('project_id')
        graph_id = data.get('graph_id')
        simulation_requirement = data.get('simulation_requirement', '')
        decision_context = data.get('decision_context', '')

        if project_id:
            project = ProjectManager.get_project(project_id)
            if not project:
                return jsonify({
                    "success": False,
                    "error": t('api.projectNotFound', id=project_id)
                }), 404
            graph_id = graph_id or project.graph_id
            simulation_requirement = simulation_requirement or project.simulation_requirement or ''

        if not graph_id:
            return jsonify({
                "success": False,
                "error": "graph_id is required"
            }), 400

        if not simulation_requirement:
            return jsonify({
                "success": False,
                "error": "simulation_requirement is required"
            }), 400

        if not Config.ZEP_API_KEY:
            return jsonify({
                "success": False,
                "error": t('api.zepApiKeyMissing')
            }), 500

        # Create or reuse sim_id
        sim_id = data.get('sim_id') or f"private_{uuid.uuid4().hex[:12]}"
        os.makedirs(_sim_dir(sim_id), exist_ok=True)

        use_llm = data.get('use_llm', True)
        entity_types = data.get('entity_types') or _RELATIONAL_ENTITY_TYPES

        # Read relational entities from Zep
        reader = ZepEntityReader()
        all_entities = []
        for etype in entity_types:
            try:
                found = reader.get_entities_by_type(
                    graph_id=graph_id,
                    entity_type=etype,
                    enrich_with_edges=True,
                )
                all_entities.extend(found)
                logger.info(f"[PRIVATE] {len(found)} '{etype}' entities read")
            except Exception as e:
                logger.warning(f"[PRIVATE] Could not read '{etype}' entities: {e}")

        if not all_entities:
            return jsonify({
                "success": False,
                "error": "No relational entities found in the graph for the given entity types."
            }), 404

        # Generate RelationalAgentProfile instances
        profile_generator = PrivateImpactProfileGenerator()
        profiles_path = os.path.join(_sim_dir(sim_id), "private_agents.json")
        profiles = profile_generator.generate_profiles_from_entities(
            entities=all_entities,
            use_llm=use_llm,
            graph_id=graph_id,
            realtime_output_path=profiles_path,
        )

        # Serialize profiles for config generator
        agent_dicts = [p.to_private_format() for p in profiles]

        # Save profiles file (final)
        with open(profiles_path, 'w', encoding='utf-8') as f:
            json.dump(agent_dicts, f, ensure_ascii=False, indent=2)

        # Generate PrivateSimulationParameters
        config_generator = PrivateImpactConfigGenerator()
        params = config_generator.generate_config(
            agent_profiles=agent_dicts,
            simulation_requirement=simulation_requirement,
            decision_context=decision_context,
        )

        # Save private_simulation_config.json (consumed by PrivateImpactRunner)
        config_path = os.path.join(_sim_dir(sim_id), "private_simulation_config.json")
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(params.to_dict(), f, ensure_ascii=False, indent=2)

        # Persist metadata for subsequent endpoints
        _write_meta(sim_id, {
            "sim_id": sim_id,
            "project_id": project_id,
            "graph_id": graph_id,
            "simulation_requirement": simulation_requirement,
            "decision_context": decision_context,
            "agent_count": len(profiles),
            "created_at": datetime.now().isoformat(),
            "status": "prepared",
        })

        logger.info(
            f"[PRIVATE] Simulation prepared: {sim_id}, "
            f"agents={len(profiles)}, graph_id={graph_id}"
        )

        return jsonify({
            "success": True,
            "data": {
                "sim_id": sim_id,
                "agent_count": len(profiles),
                "status": "prepared",
            }
        })

    except Exception as e:
        logger.error(f"[PRIVATE] Prepare failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ── POST /api/private-impact/start ────────────────────────────────────────────

@private_bp.route('/private-impact/start', methods=['POST'])
def start_private_simulation():
    """
    Launch a prepared Private Impact simulation.

    Request (JSON):
        {
            "sim_id": "private_xxxx",              // Required
            "max_rounds": null,                    // Optional
            "enable_graph_memory_update": false,   // Optional
            "graph_id": null                       // Optional (required if enable_graph_memory_update)
        }

    Returns:
        { "success": true, "data": { "sim_id": "...", "status": "running" } }
    """
    try:
        data = request.get_json() or {}

        sim_id = data.get('sim_id')
        if not sim_id:
            return jsonify({
                "success": False,
                "error": "sim_id is required"
            }), 400

        max_rounds = data.get('max_rounds')
        enable_graph_memory = data.get('enable_graph_memory_update', False)
        graph_id = data.get('graph_id')

        # Resolve graph_id from meta if needed
        if enable_graph_memory and not graph_id:
            meta = _read_meta(sim_id)
            graph_id = meta.get('graph_id')

        state = PrivateImpactRunner.start_simulation(
            simulation_id=sim_id,
            max_rounds=max_rounds,
            enable_graph_memory_update=enable_graph_memory,
            graph_id=graph_id,
        )

        return jsonify({
            "success": True,
            "data": {
                "sim_id": sim_id,
                "status": state.runner_status.value,
            }
        })

    except ValueError as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400
    except Exception as e:
        logger.error(f"[PRIVATE] Start failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ── GET /api/private-impact/status/<sim_id> ───────────────────────────────────

@private_bp.route('/private-impact/status/<sim_id>', methods=['GET'])
def get_private_status(sim_id: str):
    """
    Return the current run state of a Private Impact simulation.

    Returns:
        { "success": true, "data": PrivateSimulationRunState.to_dict() }
    """
    try:
        state = PrivateImpactRunner.get_status(sim_id)

        if not state:
            return jsonify({
                "success": False,
                "error": f"No private simulation found for sim_id: {sim_id}"
            }), 404

        return jsonify({
            "success": True,
            "data": state.to_detail_dict()
        })

    except Exception as e:
        logger.error(f"[PRIVATE] Get status failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ── POST /api/private-impact/stop/<sim_id> ────────────────────────────────────

@private_bp.route('/private-impact/stop/<sim_id>', methods=['POST'])
def stop_private_simulation(sim_id: str):
    """
    Stop a running Private Impact simulation.

    Returns:
        { "success": true, "data": { "sim_id": "...", "status": "stopped" } }
    """
    try:
        state = PrivateImpactRunner.stop_simulation(sim_id)

        return jsonify({
            "success": True,
            "data": {
                "sim_id": sim_id,
                "status": state.runner_status.value,
            }
        })

    except ValueError as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400
    except Exception as e:
        logger.error(f"[PRIVATE] Stop failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ── GET /api/private-impact/actions/<sim_id> ──────────────────────────────────

@private_bp.route('/private-impact/actions/<sim_id>', methods=['GET'])
def get_private_actions(sim_id: str):
    """
    Return the full private action log for a simulation.

    Query params:
        agent_id: Filter by agent ID (optional, int)
        round_num: Filter by round number (optional, int)

    Returns:
        { "success": true, "data": [...], "count": N }
    """
    try:
        agent_id_raw = request.args.get('agent_id')
        round_num_raw = request.args.get('round_num')

        agent_id = int(agent_id_raw) if agent_id_raw is not None else None
        round_num = int(round_num_raw) if round_num_raw is not None else None

        actions = PrivateImpactRunner.get_all_actions(
            simulation_id=sim_id,
            agent_id=agent_id,
            round_num=round_num,
        )

        return jsonify({
            "success": True,
            "data": [a.to_dict() for a in actions],
            "count": len(actions)
        })

    except Exception as e:
        logger.error(f"[PRIVATE] Get actions failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ── POST /api/private-impact/report/<sim_id> ──────────────────────────────────

@private_bp.route('/private-impact/report/<sim_id>', methods=['POST'])
def generate_private_report(sim_id: str):
    """
    Generate an analysis report for a Private Impact simulation.

    Reuses ReportAgent from report_agent.py with the private simulation actions.
    Launches the generation in a background thread and returns a task_id immediately.

    Request (JSON):
        { "force_regenerate": false }   // Optional

    Returns:
        { "success": true, "data": { "sim_id": "...", "report_id": "...", "task_id": "..." } }
    """
    try:
        data = request.get_json() or {}
        force_regenerate = data.get('force_regenerate', False)

        meta = _read_meta(sim_id)
        graph_id = meta.get('graph_id')
        simulation_requirement = meta.get('simulation_requirement', '')

        if not graph_id:
            return jsonify({
                "success": False,
                "error": f"No metadata found for sim_id: {sim_id}. Run /prepare first."
            }), 404

        # Check for an existing completed report
        if not force_regenerate:
            existing = ReportManager.get_report_by_simulation(sim_id)
            if existing and existing.status == ReportStatus.COMPLETED:
                return jsonify({
                    "success": True,
                    "data": {
                        "sim_id": sim_id,
                        "report_id": existing.report_id,
                        "status": "completed",
                        "already_generated": True,
                    }
                })

        # Pre-generate report_id so the frontend can track immediately
        report_id = f"report_{uuid.uuid4().hex[:12]}"

        task_manager = TaskManager()
        task_id = task_manager.create_task(
            task_type="private_report_generate",
            metadata={
                "sim_id": sim_id,
                "graph_id": graph_id,
                "report_id": report_id,
            }
        )

        current_locale = get_locale()

        def run_generate():
            set_locale(current_locale)
            try:
                task_manager.update_task(
                    task_id,
                    status=TaskStatus.PROCESSING,
                    progress=0,
                    message="Initialising Report Agent for private simulation..."
                )

                agent = ReportAgent(
                    graph_id=graph_id,
                    simulation_id=sim_id,
                    simulation_requirement=simulation_requirement,
                )

                def progress_callback(stage, progress, message):
                    task_manager.update_task(
                        task_id,
                        progress=progress,
                        message=f"[{stage}] {message}"
                    )

                report = agent.generate_report(
                    progress_callback=progress_callback,
                    report_id=report_id,
                )
                ReportManager.save_report(report)

                if report.status == ReportStatus.COMPLETED:
                    task_manager.complete_task(
                        task_id,
                        result={
                            "report_id": report.report_id,
                            "sim_id": sim_id,
                            "status": "completed",
                        }
                    )
                else:
                    task_manager.fail_task(task_id, report.error or "Report generation failed")

            except Exception as exc:
                logger.error(f"[PRIVATE] Report generation failed: {exc}")
                task_manager.fail_task(task_id, str(exc))

        thread = threading.Thread(target=run_generate, daemon=True)
        thread.start()

        return jsonify({
            "success": True,
            "data": {
                "sim_id": sim_id,
                "report_id": report_id,
                "task_id": task_id,
                "status": "generating",
                "already_generated": False,
            }
        })

    except Exception as e:
        logger.error(f"[PRIVATE] Report trigger failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ── DELETE /api/private-impact/cleanup/<sim_id> ───────────────────────────────

@private_bp.route('/private-impact/cleanup/<sim_id>', methods=['DELETE'])
def cleanup_private_simulation(sim_id: str):
    """
    Remove Private Impact simulation artifacts to allow a fresh restart.

    Deletes run_state.json, simulation.log, private_simulation.db, private/ directory.
    Does NOT delete private_simulation_config.json or profile files.

    Returns:
        { "success": true, "data": { "sim_id": "...", "cleaned_files": [...] } }
    """
    try:
        result = PrivateImpactRunner.cleanup(sim_id)

        return jsonify({
            "success": result["success"],
            "data": {
                "sim_id": sim_id,
                "cleaned_files": result["cleaned_files"],
                "errors": result["errors"],
            }
        })

    except Exception as e:
        logger.error(f"[PRIVATE] Cleanup failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

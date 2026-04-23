"""
Agent-scoped read endpoints introduced in Phase 2.

    GET  /api/agents/<agent_id>/reflections?simulation_id=...&limit=50
    GET  /api/agents/<agent_id>/conflicts?simulation_id=...&limit=50
    POST /api/agents/<agent_id>/retrieve    (body: {simulation_id, query, top_k, weights})

All three delegate to the per-simulation MemoryManager held by
ZepGraphMemoryManager. If the simulation has no manager yet (caller is
reading a completed run), we hydrate one on demand.
"""

from __future__ import annotations

from flask import jsonify, request

from ..services.zep_graph_memory_updater import ZepGraphMemoryManager
from . import agents_bp


def _require_sim_id() -> str:
    sim_id = request.args.get("simulation_id") or (request.get_json(silent=True) or {}).get("simulation_id")
    if not sim_id:
        raise _BadRequest("simulation_id is required")
    return sim_id


class _BadRequest(Exception):
    pass


@agents_bp.errorhandler(_BadRequest)
def _handle_bad_request(exc: _BadRequest):
    return jsonify({"error": str(exc)}), 400


@agents_bp.route("/<int:agent_id>/reflections", methods=["GET"])
def get_reflections(agent_id: int):
    """Return the agent's reflections (newest first) for a given simulation."""
    sim_id = _require_sim_id()
    limit = int(request.args.get("limit", 50))

    manager = ZepGraphMemoryManager.get_memory_manager(sim_id)
    reflections = manager.list_reflections(agent_id=agent_id, limit=limit)

    return jsonify({
        "simulation_id": sim_id,
        "agent_id": agent_id,
        "count": len(reflections),
        "reflections": [
            {
                "id": r.id,
                "content": r.content,
                "round_num": r.round_num,
                "ts": r.ts,
                "importance": r.importance,
                "source_ids": r.source_ids,
            }
            for r in reflections
        ],
    })


@agents_bp.route("/<int:agent_id>/conflicts", methods=["GET"])
def get_conflicts(agent_id: int):
    """Return the agent's contradiction edges (newest first)."""
    sim_id = _require_sim_id()
    limit = int(request.args.get("limit", 50))

    manager = ZepGraphMemoryManager.get_memory_manager(sim_id)
    conflicts = manager.list_conflicts(agent_id=agent_id, limit=limit)

    return jsonify({
        "simulation_id": sim_id,
        "agent_id": agent_id,
        "count": len(conflicts),
        "conflicts": [
            {
                "id": c.id,
                "from_id": c.from_id,
                "to_id": c.to_id,
                "ts": c.ts,
                "reason": c.reason,
            }
            for c in conflicts
        ],
    })


@agents_bp.route("/<int:agent_id>/retrieve", methods=["POST"])
def retrieve_for_agent(agent_id: int):
    """Preview what the agent would retrieve for a given query — useful for
    debugging persona / stance / memory-weighting tuning."""
    body = request.get_json() or {}
    sim_id = body.get("simulation_id")
    if not sim_id:
        raise _BadRequest("simulation_id is required")
    query = body.get("query", "")
    top_k = int(body.get("top_k", 10))
    include_public = bool(body.get("include_public", True))
    weights = body.get("weights") or {}
    alpha = float(weights.get("recency", 1.0))
    beta = float(weights.get("importance", 1.0))
    gamma = float(weights.get("relevance", 1.0))

    manager = ZepGraphMemoryManager.get_memory_manager(sim_id)
    records = manager.retrieve_for_agent(
        agent_id=agent_id, query=query, include_public=include_public,
        top_k=top_k, alpha=alpha, beta=beta, gamma=gamma,
    )

    return jsonify({
        "simulation_id": sim_id,
        "agent_id": agent_id,
        "query": query,
        "count": len(records),
        "records": [
            {
                "id": r.id,
                "namespace": r.namespace,
                "kind": r.kind.value,
                "content": r.content,
                "round_num": r.round_num,
                "importance": r.importance,
                "scores": {
                    "relevance": r.relevance_score,
                    "recency": r.recency_score,
                    "combined": r.combined_score,
                },
            }
            for r in records
        ],
    })

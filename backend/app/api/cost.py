"""
`POST /api/simulation/estimate-cost` — pre-flight cost estimate.

Body:
    {"agent_count": 100, "rounds": 20, "user_cap_usd": 20.0 (optional)}

Response:
    {
      "agent_count": 100, "rounds": 20,
      "total_usd": 12.40, "total_tokens": 4_800_000,
      "approval_required": false,
      "roles": {"fast": {...}, "balanced": {...}, ...},
      "note": ""
    }

Attached to the simulation blueprint so it lives under /api/simulation/* with
the other per-sim endpoints.
"""

from __future__ import annotations

from flask import jsonify, request

from ..cost import estimate_simulation_cost
from . import simulation_bp


@simulation_bp.route("/estimate-cost", methods=["POST"])
def estimate_cost():
    body = request.get_json(silent=True) or {}
    try:
        agent_count = int(body.get("agent_count", 0))
        rounds = int(body.get("rounds", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "agent_count and rounds must be integers"}), 400
    if agent_count <= 0 or rounds <= 0:
        return jsonify({"error": "agent_count and rounds must be positive"}), 400

    cap = body.get("user_cap_usd")
    cap = float(cap) if cap is not None else None

    estimate = estimate_simulation_cost(
        agent_count=agent_count, rounds=rounds, user_cap_usd=cap,
    )
    return jsonify(estimate.to_dict())

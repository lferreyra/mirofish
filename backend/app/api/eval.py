"""
Eval results dashboard endpoint.

    GET /api/eval/results?limit=50[&case=<name>]

Returns:
    {
      "count": N,
      "results": [<record>, ...]   # newest-first
    }

Records are whatever `eval.runner` wrote via `eval.storage.append_result`.
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from eval.storage import read_results  # absolute — `backend/` is on sys.path

eval_bp = Blueprint("eval", __name__)


@eval_bp.route("/results", methods=["GET"])
def get_results():
    limit_param = request.args.get("limit")
    try:
        limit = int(limit_param) if limit_param is not None else 50
    except ValueError:
        limit = 50
    case = request.args.get("case")
    rows = read_results(limit=limit, case=case)
    return jsonify({
        "count": len(rows),
        "results": rows,
    })

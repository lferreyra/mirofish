"""
Checkpoint / restore REST endpoints. Mounted under /api/simulation/<sim_id>.

    POST /api/simulation/<sim_id>/checkpoint
         body: {"round_num": 10, "config": {...}, "oasis_state": {...}}
         -> {"path": "<file>", "bytes": 1234}

    POST /api/simulation/<sim_id>/restore
         body: {"path": "<file>"}   OR   {"round_num": 10}
         -> {"restored_round": 10, "records_written": N, "conflicts_written": M}

    GET  /api/simulation/<sim_id>/checkpoints
         -> list of checkpoint files with metadata
"""

from __future__ import annotations

import os
from typing import Any, Dict

from flask import jsonify, request

from ..checkpoint.archiver import (
    default_archive_path,
    restore_checkpoint,
    save_checkpoint,
)
from ..checkpoint.serializer import collect_checkpoint, restore_into
from ..config import Config
from ..services.zep_graph_memory_updater import ZepGraphMemoryManager
from . import simulation_bp


def _sim_dir(sim_id: str) -> str:
    base = Config.OASIS_SIMULATION_DATA_DIR
    sim_dir = os.path.join(base, sim_id)
    os.makedirs(sim_dir, exist_ok=True)
    return sim_dir


@simulation_bp.route('/<simulation_id>/checkpoint', methods=['POST'])
def create_checkpoint(simulation_id: str):
    body: Dict[str, Any] = request.get_json() or {}
    round_num = int(body.get("round_num", 0))
    config = body.get("config") or {}
    oasis_state = body.get("oasis_state") or {}
    action_log_offset = int(body.get("action_log_offset", 0))

    manager = ZepGraphMemoryManager.get_memory_manager(simulation_id)
    snapshot = collect_checkpoint(
        manager=manager,
        round_num=round_num,
        action_log_offset=action_log_offset,
        oasis_state=oasis_state,
        config=config,
    )
    sim_dir = _sim_dir(simulation_id)
    path = save_checkpoint(snapshot, simulation_dir=sim_dir)
    size = os.path.getsize(path)
    return jsonify({
        "simulation_id": simulation_id,
        "round_num": round_num,
        "path": path,
        "bytes": size,
        "records": sum(len(v) for v in snapshot.records_by_namespace.values()),
        "conflicts": sum(len(v) for v in snapshot.conflicts_by_namespace.values()),
    })


@simulation_bp.route('/<simulation_id>/restore', methods=['POST'])
def restore_checkpoint_endpoint(simulation_id: str):
    body: Dict[str, Any] = request.get_json() or {}
    path = body.get("path")
    round_num = body.get("round_num")
    if not path and round_num is None:
        return jsonify({"error": "either 'path' or 'round_num' is required"}), 400
    if not path:
        path = default_archive_path(
            simulation_dir=_sim_dir(simulation_id),
            round_num=int(round_num),
        )
    if not os.path.exists(path):
        return jsonify({"error": f"checkpoint not found: {path}"}), 404

    snapshot = restore_checkpoint(path)
    manager = ZepGraphMemoryManager.get_memory_manager(simulation_id)
    restore_into(snapshot, manager=manager)
    return jsonify({
        "simulation_id": simulation_id,
        "restored_round": snapshot.round_num,
        "records_written": sum(len(v) for v in snapshot.records_by_namespace.values()),
        "conflicts_written": sum(len(v) for v in snapshot.conflicts_by_namespace.values()),
        "source": path,
    })


@simulation_bp.route('/<simulation_id>/checkpoints', methods=['GET'])
def list_checkpoints(simulation_id: str):
    sim_dir = _sim_dir(simulation_id)
    ck_dir = os.path.join(sim_dir, "checkpoints")
    if not os.path.exists(ck_dir):
        return jsonify({"simulation_id": simulation_id, "checkpoints": []})
    items = []
    for name in sorted(os.listdir(ck_dir)):
        if not (name.endswith(".tar.zst") or name.endswith(".tar.gz")):
            continue
        path = os.path.join(ck_dir, name)
        try:
            stat = os.stat(path)
        except OSError:
            continue
        items.append({
            "name": name,
            "path": path,
            "bytes": stat.st_size,
            "mtime": stat.st_mtime,
        })
    return jsonify({"simulation_id": simulation_id, "checkpoints": items})

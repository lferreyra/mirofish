"""
Collects a point-in-time state snapshot from a running simulation.

`collect_checkpoint` returns a `CheckpointData` dataclass. `restore_into`
writes that data back into a MemoryManager. Both sides are plain Python —
archiving lives in the sibling module so the two concerns stay separable.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from ..memory.base import Namespace, Observation, Reflection
from ..memory.manager import MemoryManager


CHECKPOINT_FORMAT_VERSION = 1


@dataclass
class CheckpointData:
    """Serializable snapshot. All fields are JSON-safe primitives."""
    format_version: int
    simulation_id: str
    round_num: int
    action_log_offset: int
    oasis_state: Dict[str, Any]
    agents_seen: List[int]
    records_by_namespace: Dict[str, List[Dict[str, Any]]]
    conflicts_by_namespace: Dict[str, List[Dict[str, Any]]]
    config: Dict[str, Any]
    created_ts: float

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, raw: str) -> "CheckpointData":
        data = json.loads(raw)
        return cls(**data)


def _serialize_record(record) -> Dict[str, Any]:
    """Observation / Reflection -> dict. Drops transient score fields so two
    checkpoints of the same state hash identically."""
    base = {
        "id": record.id,
        "kind": record.kind.value,
        "namespace": record.namespace,
        "content": record.content,
        "round_num": record.round_num,
        "ts": record.ts,
        "importance": record.importance,
        "embedding": record.embedding,
        "metadata": record.metadata,
    }
    if isinstance(record, Reflection):
        base["source_ids"] = list(record.source_ids)
    elif isinstance(record, Observation):
        base["action_type"] = record.action_type
        base["author_id"] = record.author_id
    return base


def _hydrate_record(data: Dict[str, Any]):
    kind = data.get("kind", "observation")
    common = dict(
        id=data["id"],
        namespace=data["namespace"],
        content=data["content"],
        round_num=int(data["round_num"]),
        ts=float(data["ts"]),
        importance=float(data["importance"]),
        embedding=data.get("embedding"),
        metadata=data.get("metadata", {}) or {},
    )
    if kind == "reflection":
        return Reflection(source_ids=list(data.get("source_ids", [])), **common)
    return Observation(
        action_type=data.get("action_type"),
        author_id=data.get("author_id"),
        **common,
    )


def collect_checkpoint(
    *,
    manager: MemoryManager,
    round_num: int,
    action_log_offset: int = 0,
    oasis_state: Optional[Dict[str, Any]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> CheckpointData:
    """Walk every known namespace (each agent + public timeline) and snapshot
    every record. Conflicts are captured separately so they can be re-linked
    on restore."""
    agents = sorted(manager._agents_seen.keys())  # noqa: SLF001 — intentional
    namespaces: List[Namespace] = [Namespace.public_timeline(manager.simulation_id)]
    namespaces.extend(Namespace.for_agent(manager.simulation_id, a) for a in agents)

    records_by_ns: Dict[str, List[Dict[str, Any]]] = {}
    conflicts_by_ns: Dict[str, List[Dict[str, Any]]] = {}
    for ns in namespaces:
        # summarize_window(top_k=huge) pulls every record in that namespace,
        # respecting ordering but not filtering.
        records = manager._backend.summarize_window(namespace=ns, top_k=10_000)  # noqa: SLF001
        records_by_ns[ns.key] = [_serialize_record(r) for r in records]
        conflicts = manager._backend.list_conflicts(namespace=ns, limit=10_000)  # noqa: SLF001
        conflicts_by_ns[ns.key] = [
            {
                "id": c.id, "from_id": c.from_id, "to_id": c.to_id,
                "ts": c.ts, "reason": c.reason,
            }
            for c in conflicts
        ]

    return CheckpointData(
        format_version=CHECKPOINT_FORMAT_VERSION,
        simulation_id=manager.simulation_id,
        round_num=round_num,
        action_log_offset=action_log_offset,
        oasis_state=oasis_state or {},
        agents_seen=agents,
        records_by_namespace=records_by_ns,
        conflicts_by_namespace=conflicts_by_ns,
        config=config or {},
        created_ts=time.time(),
    )


def restore_into(
    checkpoint: CheckpointData,
    *,
    manager: MemoryManager,
) -> None:
    """Replay records + conflicts into a fresh MemoryManager. Expects the
    backend to be empty; on a backend with existing state, records are
    simply added alongside (IDs are unique)."""
    from ..memory.base import ConflictEdge

    if checkpoint.format_version != CHECKPOINT_FORMAT_VERSION:
        raise ValueError(
            f"unsupported checkpoint format_version={checkpoint.format_version}; "
            f"this build expects {CHECKPOINT_FORMAT_VERSION}"
        )
    if checkpoint.simulation_id != manager.simulation_id:
        # Allow a rename (useful for forking a run); surface as a warning.
        import logging
        logging.getLogger("mirofish.checkpoint").warning(
            "restoring simulation_id=%r into manager with simulation_id=%r",
            checkpoint.simulation_id, manager.simulation_id,
        )

    backend = manager._backend  # noqa: SLF001

    # Write observations first so reflection source_ids resolve.
    for ns_key, raw_records in checkpoint.records_by_namespace.items():
        for raw in raw_records:
            if raw.get("kind") == "reflection":
                continue
            backend.write_observation(_hydrate_record(raw))
    for ns_key, raw_records in checkpoint.records_by_namespace.items():
        for raw in raw_records:
            if raw.get("kind") == "reflection":
                backend.write_reflection(_hydrate_record(raw))

    for ns_key, raw_edges in checkpoint.conflicts_by_namespace.items():
        for raw in raw_edges:
            backend.write_conflict_edge(ConflictEdge(
                id=raw["id"], from_id=raw["from_id"], to_id=raw["to_id"],
                ts=float(raw["ts"]), reason=raw.get("reason"),
            ))

    # Restore the agents-seen map so future reflections fire for the right set.
    for agent_id in checkpoint.agents_seen:
        manager._agents_seen[int(agent_id)] = True  # noqa: SLF001

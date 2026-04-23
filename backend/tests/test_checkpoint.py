"""Tests for checkpoint serializer + tar.zst archive roundtrip.

This also covers the Phase-3 acceptance criterion: checkpoint at round N,
restore into a fresh MemoryManager, verify no state loss.
"""

import os

import pytest

from app.checkpoint.archiver import (
    default_archive_path,
    restore_checkpoint,
    save_checkpoint,
)
from app.checkpoint.serializer import collect_checkpoint, restore_into
from app.memory.base import ConflictEdge, Namespace, Observation, Reflection
from app.memory.in_memory import InMemoryBackend
from app.memory.manager import MemoryManager


class _NoopRouter:
    """Router stub — checkpoint tests don't exercise LLM calls."""

    def chat(self, *args, **kwargs):
        from app.llm.base import LLMResponse
        return LLMResponse(text="5", model="noop", backend="noop")

    def embed(self, texts, **kwargs):
        from app.llm.base import EmbeddingResponse
        return EmbeddingResponse(vectors=[[0.0] * 3 for _ in texts], model="noop", backend="noop")


def _seed_manager(manager: MemoryManager) -> None:
    """Populate a manager with observations, a reflection, and a conflict edge."""
    o1 = manager.record_agent_action(
        agent_id=1, round_num=1, content="agent 1 first action",
        action_type="CREATE_POST", public=True,
    )
    o2 = manager.record_agent_action(
        agent_id=1, round_num=2, content="agent 1 second action",
        action_type="CREATE_POST",
    )
    manager.record_agent_action(
        agent_id=2, round_num=2, content="agent 2 speaks up",
        action_type="CREATE_POST", public=True,
    )
    # Add a reflection manually (cadence may not fire yet)
    ns = Namespace.for_agent("sim-check", 1)
    manager._backend.write_reflection(Reflection(  # noqa: SLF001
        id="r1", namespace=ns.key,
        content="I believe I should speak up more.", round_num=2, ts=o2.ts,
        source_ids=[o1.id, o2.id],
    ))
    # Add a conflict edge
    manager._backend.write_conflict_edge(ConflictEdge(  # noqa: SLF001
        id="c1", from_id=o2.id, to_id=o1.id, ts=o2.ts, reason="sentiment_flip",
    ))


def test_checkpoint_captures_all_records(tmp_path):
    manager = MemoryManager(
        simulation_id="sim-check",
        backend=InMemoryBackend(),
        llm_router=_NoopRouter(),
        enable_reflection=False, enable_contradiction=False, enable_importance=False,
    )
    _seed_manager(manager)

    snapshot = collect_checkpoint(manager=manager, round_num=2)

    # Agent-1 private + agent-2 private + public timeline all captured
    agent1_ns = Namespace.for_agent("sim-check", 1).key
    agent2_ns = Namespace.for_agent("sim-check", 2).key
    public_ns = Namespace.public_timeline("sim-check").key
    assert agent1_ns in snapshot.records_by_namespace
    assert agent2_ns in snapshot.records_by_namespace
    assert public_ns in snapshot.records_by_namespace
    # Agent 1 has 2 observations + 1 reflection in its private namespace
    assert len(snapshot.records_by_namespace[agent1_ns]) == 3
    # Agent 1's conflict edge
    assert len(snapshot.conflicts_by_namespace[agent1_ns]) == 1


def test_checkpoint_archive_roundtrip(tmp_path):
    """Save to disk (tar.zst or tar.gz), read it back, verify it equals the original."""
    sim_dir = str(tmp_path / "sim-check")
    os.makedirs(sim_dir, exist_ok=True)

    manager = MemoryManager(
        simulation_id="sim-check", backend=InMemoryBackend(),
        llm_router=_NoopRouter(),
        enable_reflection=False, enable_contradiction=False, enable_importance=False,
    )
    _seed_manager(manager)

    snapshot = collect_checkpoint(manager=manager, round_num=2, config={"seed": 1})
    path = save_checkpoint(snapshot, simulation_dir=sim_dir)
    assert os.path.exists(path)
    assert path.endswith(".tar.zst") or path.endswith(".tar.gz")

    loaded = restore_checkpoint(path)
    assert loaded.simulation_id == snapshot.simulation_id
    assert loaded.round_num == snapshot.round_num
    assert loaded.config == {"seed": 1}
    # Record counts match
    for ns, recs in snapshot.records_by_namespace.items():
        assert len(loaded.records_by_namespace.get(ns, [])) == len(recs)


def test_restore_into_fresh_manager_reproduces_state(tmp_path):
    """Phase-3 acceptance: checkpoint at round N, spin up a fresh manager,
    restore, verify observations/reflections/conflicts all come back."""
    manager_a = MemoryManager(
        simulation_id="sim-check", backend=InMemoryBackend(),
        llm_router=_NoopRouter(),
        enable_reflection=False, enable_contradiction=False, enable_importance=False,
    )
    _seed_manager(manager_a)
    snapshot = collect_checkpoint(manager=manager_a, round_num=2)

    # Fresh manager with a brand-new backend
    manager_b = MemoryManager(
        simulation_id="sim-check", backend=InMemoryBackend(),
        llm_router=_NoopRouter(),
        enable_reflection=False, enable_contradiction=False, enable_importance=False,
    )
    restore_into(snapshot, manager=manager_b)

    # Agent-1 reflections + conflicts should appear
    reflections_b = manager_b.list_reflections(agent_id=1)
    assert len(reflections_b) == 1
    assert reflections_b[0].source_ids  # source refs rehydrated

    conflicts_b = manager_b.list_conflicts(agent_id=1)
    assert len(conflicts_b) == 1

    # Public timeline also rehydrated (posts were public=True on write)
    public_records = manager_b._backend.summarize_window(  # noqa: SLF001
        namespace=Namespace.public_timeline("sim-check"), top_k=20,
    )
    assert len(public_records) >= 2  # agent-1 post + agent-2 post


def test_restore_refuses_mismatched_format_version(tmp_path):
    from app.checkpoint.serializer import CheckpointData

    bogus = CheckpointData(
        format_version=999,  # intentional mismatch
        simulation_id="x", round_num=0, action_log_offset=0, oasis_state={},
        agents_seen=[], records_by_namespace={}, conflicts_by_namespace={},
        config={}, created_ts=0.0,
    )
    manager = MemoryManager(
        simulation_id="x", backend=InMemoryBackend(), llm_router=_NoopRouter(),
        enable_reflection=False, enable_contradiction=False, enable_importance=False,
    )
    with pytest.raises(ValueError) as exc_info:
        restore_into(bogus, manager=manager)
    assert "format_version" in str(exc_info.value)


def test_default_archive_path_includes_round_number(tmp_path):
    """Path layout makes it obvious which round a checkpoint represents."""
    path = default_archive_path(simulation_dir=str(tmp_path), round_num=42)
    assert "round-00042" in path
    assert path.endswith(".tar.zst") or path.endswith(".tar.gz")

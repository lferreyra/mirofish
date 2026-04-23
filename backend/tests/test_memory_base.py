"""Tests for memory/base.py — dataclasses, namespace helpers, scoring helpers."""

import pytest

from app.memory.base import (
    ConflictEdge,
    MemoryBackend,
    MemoryBackendError,
    Namespace,
    Observation,
    RecordKind,
    Reflection,
)


def test_namespace_agent_factory_produces_expected_key():
    ns = Namespace.for_agent("sim-42", 7)
    assert ns.key == "agent:sim-42:7"
    assert ns.is_public is False
    assert ns.simulation_id == "sim-42"
    assert ns.agent_id == 7


def test_namespace_public_timeline_factory():
    ns = Namespace.public_timeline("sim-42")
    assert ns.key == "public:sim-42:timeline"
    assert ns.is_public is True
    assert ns.agent_id is None


def test_observation_defaults_to_observation_kind():
    obs = Observation(
        id="x", namespace="agent:a:1", content="c", round_num=0,
        ts=0.0,
    )
    assert obs.kind == RecordKind.OBSERVATION


def test_reflection_stores_source_ids_and_overrides_kind():
    ref = Reflection(
        id="x", namespace="agent:a:1", content="c", round_num=0,
        ts=0.0, source_ids=["s1", "s2"],
    )
    assert ref.kind == RecordKind.REFLECTION
    assert ref.source_ids == ["s1", "s2"]


def test_conflict_edge_new_id_is_unique():
    a = ConflictEdge.new_id()
    b = ConflictEdge.new_id()
    assert a != b
    assert len(a) == 32  # uuid4 hex


def test_recency_score_decays_with_age():
    """Half-life behavior: score should be 0.5 at age == half_life."""
    now = 1000.0
    ts = now - 3600.0  # exactly one half-life by default
    score = MemoryBackend._recency_score(ts, now, half_life_s=3600.0)
    assert score == pytest.approx(0.5, rel=1e-6)


def test_importance_score_maps_1_10_to_0_1():
    assert MemoryBackend._importance_score(1.0) == pytest.approx(0.0)
    assert MemoryBackend._importance_score(10.0) == pytest.approx(1.0)
    assert MemoryBackend._importance_score(5.5) == pytest.approx(0.5, rel=1e-6)


def test_cosine_returns_zero_for_zero_vector():
    assert MemoryBackend._cosine([0.0, 0.0, 0.0], [1.0, 1.0, 1.0]) == 0.0


def test_cosine_returns_one_for_parallel_vectors():
    assert MemoryBackend._cosine([1.0, 2.0, 3.0], [2.0, 4.0, 6.0]) == pytest.approx(1.0, rel=1e-6)


def test_cosine_returns_zero_for_orthogonal():
    assert MemoryBackend._cosine([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_memory_backend_error_stringifies_with_backend_name():
    exc = MemoryBackendError("bad_thing", "details", backend="neo4j")
    assert "neo4j" in str(exc)
    assert "bad_thing" in str(exc)

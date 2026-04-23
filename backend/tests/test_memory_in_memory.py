"""Tests for the in-memory reference backend."""

import pytest

from app.memory.base import (
    ConflictEdge,
    MemoryBackendError,
    Namespace,
    Observation,
    RecordKind,
    Reflection,
)
from app.memory.in_memory import InMemoryBackend


@pytest.fixture
def backend():
    return InMemoryBackend()


def _obs(agent_ns, content, *, round_num=0, importance=5.0, embedding=None, ts=0.0):
    return Observation(
        id=Observation.new_id(), namespace=agent_ns.key,
        content=content, round_num=round_num, ts=ts,
        importance=importance, embedding=embedding,
    )


def test_rejects_invalid_namespace_prefix(backend):
    """Namespaces must use the documented `agent:` or `public:` prefix."""
    bogus = Observation(
        id="x", namespace="nope:sim:1", content="c", round_num=0, ts=0.0,
    )
    with pytest.raises(MemoryBackendError) as exc_info:
        backend.write_observation(bogus)
    assert exc_info.value.code == "invalid_namespace"


def test_retrieve_ranks_by_combined_score(backend):
    """recency + importance + relevance — fresh, high-importance, query-overlap wins."""
    ns = Namespace.for_agent("sim", 1)
    now = 1000.0
    # Low importance, long-ago, unrelated
    backend.write_observation(_obs(ns, "cats are nice", ts=now - 3600, importance=2.0))
    # High importance, recent, query-matching
    winner = _obs(ns, "biden won the debate", ts=now, importance=9.0)
    backend.write_observation(winner)
    # Mid importance, recent, unrelated
    backend.write_observation(_obs(ns, "random noise", ts=now, importance=5.0))

    result = backend.retrieve(
        namespace=ns, query="biden debate",
        top_k=1, alpha=1.0, beta=1.0, gamma=1.0, now_ts=now,
    )
    assert result.records[0].id == winner.id


def test_retrieve_in_different_namespace_returns_empty(backend):
    """Each namespace is isolated — a write to agent:1 is not visible to agent:2."""
    ns1 = Namespace.for_agent("sim", 1)
    ns2 = Namespace.for_agent("sim", 2)
    backend.write_observation(_obs(ns1, "private to agent 1"))

    result = backend.retrieve(namespace=ns2, query="private", top_k=5)
    assert result.records == []


def test_nearest_ranks_by_cosine_similarity(backend):
    """nearest() is pure vector KNN — no recency / importance weighting.

    `fresh_high` is high-importance and recent but its vector is orthogonal to
    the query; `close_match` is low-importance and old but its vector aligns.
    nearest() must pick `close_match`.
    """
    ns = Namespace.for_agent("sim", 1)
    # Orthogonal-ish to the query (cosine ~ 0.1)
    backend.write_observation(_obs(ns, "fresh_high", importance=10.0, ts=9999.0,
                                    embedding=[0.1, 1.0, 0.0]))
    # Closely aligned with the query (cosine ~ 0.99)
    close = _obs(ns, "close_match", importance=3.0, ts=0.0,
                 embedding=[1.0, 0.1, 0.0])
    backend.write_observation(close)

    neighbors = backend.nearest(namespace=ns, query_embedding=[1.0, 0.0, 0.0], top_k=1)
    assert neighbors[0].id == close.id


def test_write_reflection_validates_source_ids_exist(backend):
    """Dangling source_ids should raise — catches typos in reflection batches."""
    ns = Namespace.for_agent("sim", 1)
    backend.write_observation(_obs(ns, "real_source"))  # not the id referenced below

    dangling = Reflection(
        id="r1", namespace=ns.key, content="belief",
        round_num=0, ts=0.0, source_ids=["ghost-id-does-not-exist"],
    )
    with pytest.raises(MemoryBackendError) as exc_info:
        backend.write_reflection(dangling)
    assert exc_info.value.code == "dangling_source"


def test_list_reflections_newest_first(backend):
    ns = Namespace.for_agent("sim", 1)
    obs = _obs(ns, "source")
    backend.write_observation(obs)
    r1 = Reflection(id="r1", namespace=ns.key, content="early belief",
                    round_num=1, ts=1.0, source_ids=[obs.id])
    r2 = Reflection(id="r2", namespace=ns.key, content="late belief",
                    round_num=5, ts=5.0, source_ids=[obs.id])
    backend.write_reflection(r1)
    backend.write_reflection(r2)

    reflections = backend.list_reflections(namespace=ns, limit=10)
    assert reflections[0].id == "r2"
    assert reflections[1].id == "r1"


def test_conflict_edge_roundtrips(backend):
    ns = Namespace.for_agent("sim", 1)
    a = _obs(ns, "post A");  backend.write_observation(a)
    b = _obs(ns, "post B");  backend.write_observation(b)

    edge = ConflictEdge(
        id=ConflictEdge.new_id(), from_id=a.id, to_id=b.id, ts=0.0,
        reason="sentiment_flip",
    )
    backend.write_conflict_edge(edge)

    conflicts = backend.list_conflicts(namespace=ns)
    assert len(conflicts) == 1
    assert conflicts[0].from_id == a.id
    assert conflicts[0].to_id == b.id


def test_conflict_edge_with_unknown_endpoints_raises(backend):
    """A conflict between two ghost ids should fail loudly — otherwise conflict
    reads would return dangling links."""
    ghost = ConflictEdge(
        id=ConflictEdge.new_id(), from_id="x", to_id="y", ts=0.0,
    )
    with pytest.raises(MemoryBackendError) as exc_info:
        backend.write_conflict_edge(ghost)
    assert exc_info.value.code == "unknown_endpoint"


def test_summarize_window_sorts_by_importance(backend):
    """summarize_window returns window-filtered results sorted by importance desc."""
    ns = Namespace.for_agent("sim", 1)
    backend.write_observation(_obs(ns, "r1 low", round_num=1, importance=1.0))
    backend.write_observation(_obs(ns, "r1 hi", round_num=1, importance=9.0))
    backend.write_observation(_obs(ns, "r2 mid", round_num=2, importance=5.0))
    # Outside window
    backend.write_observation(_obs(ns, "r9", round_num=9, importance=10.0))

    summary = backend.summarize_window(namespace=ns, since_round=1, until_round=2, top_k=10)
    assert [r.content for r in summary] == ["r1 hi", "r2 mid", "r1 low"]

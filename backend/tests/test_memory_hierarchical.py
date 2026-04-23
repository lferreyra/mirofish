"""Tests for hierarchical services. LLM calls are stubbed — no network."""

import json
from types import SimpleNamespace

import pytest

from app.llm.base import EmbeddingResponse, LLMResponse
from app.memory.base import Namespace, Observation, RecordKind
from app.memory.hierarchical import (
    ContradictionDetector,
    ImportanceScorer,
    ReflectionScheduler,
)
from app.memory.in_memory import InMemoryBackend


class FakeRouter:
    """Router stub. Pass a list of canned texts; calls pop from the front."""

    def __init__(self, responses=None):
        self._responses = list(responses or [])
        self.calls = []

    def chat(self, role, messages, **kwargs):
        self.calls.append({"role": role, "messages": messages, "kwargs": kwargs})
        text = self._responses.pop(0) if self._responses else ""
        return LLMResponse(text=text, model="fake", backend="fake", latency_ms=0.0)

    def embed(self, texts, **kwargs):
        # Deterministic bag-of-tokens embedding — good enough for tests.
        def _emb(s):
            v = [0.0] * 8
            for i, ch in enumerate(s[:8]):
                v[i] = float(ord(ch) % 7)
            return v
        return EmbeddingResponse(
            vectors=[_emb(t) for t in texts], model="fake-emb", backend="fake",
        )


# ---- ImportanceScorer ------------------------------------------------------


def test_importance_scorer_parses_single_integer():
    router = FakeRouter(["7"])
    scorer = ImportanceScorer(router=router)
    assert scorer.score("some observation") == 7


def test_importance_scorer_handles_verbose_reply():
    """Some models preamble before the integer; we should still extract it."""
    router = FakeRouter(["I'd rate that around 8 because..."])
    scorer = ImportanceScorer(router=router)
    assert scorer.score("x") == 8


def test_importance_scorer_falls_back_to_default_on_llm_error():
    class _ErrRouter(FakeRouter):
        def chat(self, *args, **kwargs):
            raise RuntimeError("boom")

    scorer = ImportanceScorer(router=_ErrRouter(), default=5)
    # Should not raise; should return the default.
    assert scorer.score("x") == 5


# ---- ReflectionScheduler ---------------------------------------------------


def _pre_seed_observations(backend, ns, count, round_num=0):
    for i in range(count):
        obs = Observation(
            id=Observation.new_id(), namespace=ns.key,
            content=f"obs {i}: seen something #{i}",
            round_num=round_num, ts=float(round_num), importance=7.0,
        )
        backend.write_observation(obs)


def test_reflection_scheduler_writes_beliefs_back(monkeypatch):
    """With >=min_new observations, the scheduler queries the LLM and persists beliefs."""
    backend = InMemoryBackend()
    ns = Namespace.for_agent("sim", 3)
    _pre_seed_observations(backend, ns, count=5, round_num=4)

    beliefs_json = json.dumps({"beliefs": [
        "I believe the university is defensive.",
        "I've noticed opposition is gaining steam.",
    ]})
    router = FakeRouter([beliefs_json])
    scheduler = ReflectionScheduler(backend, router, every_n_rounds=5, top_k_sources=5)

    result = scheduler.maybe_reflect(simulation_id="sim", agent_id=3, round_num=4)
    assert result is not None
    assert len(result.reflections) == 2
    # Beliefs should be persisted and findable via list_reflections.
    persisted = backend.list_reflections(namespace=ns)
    assert len(persisted) == 2
    assert {r.content for r in persisted} == {
        "I believe the university is defensive.",
        "I've noticed opposition is gaining steam.",
    }


def test_reflection_scheduler_skips_when_cadence_not_reached():
    backend = InMemoryBackend()
    ns = Namespace.for_agent("sim", 3)
    _pre_seed_observations(backend, ns, count=10)

    router = FakeRouter([])  # no calls expected
    scheduler = ReflectionScheduler(backend, router, every_n_rounds=5)

    # First call at round 2 — below cadence from -1 start? -1+5=4, so 2 < 4 -> skip.
    assert scheduler.maybe_reflect(simulation_id="sim", agent_id=3, round_num=2) is None
    assert router.calls == []


def test_reflection_scheduler_skips_with_too_few_observations():
    """Below `min_new_observations`, don't burn an LLM call on noise."""
    backend = InMemoryBackend()
    ns = Namespace.for_agent("sim", 3)
    _pre_seed_observations(backend, ns, count=1, round_num=4)

    router = FakeRouter([])
    scheduler = ReflectionScheduler(
        backend, router, every_n_rounds=5, min_new_observations=3,
    )
    assert scheduler.maybe_reflect(simulation_id="sim", agent_id=3, round_num=5) is None
    assert router.calls == []


# ---- ContradictionDetector ------------------------------------------------


def test_contradiction_detector_writes_edge_on_positive_match():
    backend = InMemoryBackend()
    ns = Namespace.for_agent("sim", 1)
    neighbor = Observation(
        id=Observation.new_id(), namespace=ns.key, content="The policy is great.",
        round_num=0, ts=0.0, embedding=[1.0, 0.0, 0.0],
    )
    backend.write_observation(neighbor)
    fresh = Observation(
        id=Observation.new_id(), namespace=ns.key, content="The policy is terrible.",
        round_num=1, ts=1.0, embedding=[0.9, 0.1, 0.0],
    )
    backend.write_observation(fresh)

    router = FakeRouter([json.dumps({"contradicts": True, "reason": "sentiment_flip"})])
    detector = ContradictionDetector(backend, router, neighbors_to_check=3)

    edges = detector.check(fresh)
    assert len(edges) == 1
    assert edges[0].from_id == fresh.id
    assert edges[0].to_id == neighbor.id

    conflicts = backend.list_conflicts(namespace=ns)
    assert len(conflicts) == 1


def test_contradiction_detector_skips_without_embedding():
    """No embedding = no semantic neighbors = no detector call."""
    backend = InMemoryBackend()
    ns = Namespace.for_agent("sim", 1)
    fresh = Observation(
        id=Observation.new_id(), namespace=ns.key, content="no vector here",
        round_num=0, ts=0.0, embedding=None,
    )
    backend.write_observation(fresh)

    router = FakeRouter([])
    detector = ContradictionDetector(backend, router)
    assert detector.check(fresh) == []
    assert router.calls == []


def test_contradiction_detector_no_edge_when_llm_says_no():
    backend = InMemoryBackend()
    ns = Namespace.for_agent("sim", 1)
    neighbor = Observation(
        id=Observation.new_id(), namespace=ns.key, content="A",
        round_num=0, ts=0.0, embedding=[1.0, 0.0],
    )
    backend.write_observation(neighbor)
    fresh = Observation(
        id=Observation.new_id(), namespace=ns.key, content="B",
        round_num=1, ts=1.0, embedding=[0.95, 0.05],
    )
    backend.write_observation(fresh)

    router = FakeRouter([json.dumps({"contradicts": False, "reason": "unrelated"})])
    detector = ContradictionDetector(backend, router)

    edges = detector.check(fresh)
    assert edges == []
    assert backend.list_conflicts(namespace=ns) == []

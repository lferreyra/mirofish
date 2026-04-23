"""Tests for MemoryManager — the integration object simulation code holds."""

import json

import pytest

from app.llm.base import EmbeddingResponse, LLMResponse
from app.memory.base import Namespace
from app.memory.in_memory import InMemoryBackend
from app.memory.manager import MemoryManager


class ScriptedRouter:
    """Returns scripted LLM responses by cache_key (so we can distinguish
    importance vs contradiction vs reflection calls)."""

    def __init__(self, scripts=None, embeddings=None):
        # cache_key -> list of reply strings (popped left to right)
        self._scripts = {k: list(v) for k, v in (scripts or {}).items()}
        self._embeddings = list(embeddings or [])
        self.calls = []

    def chat(self, role, messages, **kwargs):
        key = kwargs.get("cache_key")
        self.calls.append({"role": role, "cache_key": key})
        queue = self._scripts.get(key, [])
        text = queue.pop(0) if queue else "5"  # "5" = default importance
        return LLMResponse(text=text, model="fake", backend="fake")

    def embed(self, texts, **kwargs):
        if self._embeddings:
            vecs = [self._embeddings.pop(0) for _ in texts]
        else:
            # Zero vectors — retrieval falls back to token overlap.
            vecs = [[0.0] * 4 for _ in texts]
        return EmbeddingResponse(vectors=vecs, model="fake-emb", backend="fake")


def test_record_agent_action_writes_to_private_namespace():
    backend = InMemoryBackend()
    router = ScriptedRouter(scripts={"memory.importance": ["8"]})
    manager = MemoryManager(
        simulation_id="sim", backend=backend, llm_router=router,
        enable_contradiction=False, enable_reflection=False,
    )

    obs = manager.record_agent_action(
        agent_id=5, round_num=1, content="I posted about Biden",
        action_type="CREATE_POST",
    )
    assert obs.namespace == "agent:sim:5"
    assert obs.importance == 8.0


def test_record_agent_action_mirrors_public_posts():
    """`public=True` writes should land in BOTH the agent and public namespaces."""
    backend = InMemoryBackend()
    router = ScriptedRouter(scripts={"memory.importance": ["5", "5"]})  # once per write
    manager = MemoryManager(
        simulation_id="sim", backend=backend, llm_router=router,
        enable_contradiction=False, enable_reflection=False,
    )

    manager.record_agent_action(
        agent_id=5, round_num=1, content="hello world",
        action_type="CREATE_POST", public=True,
    )
    # Pull both namespaces directly
    private = backend.retrieve(namespace=Namespace.for_agent("sim", 5), query="hello")
    public = backend.retrieve(namespace=Namespace.public_timeline("sim"), query="hello")
    assert len(private.records) == 1
    assert len(public.records) == 1


def test_retrieve_for_agent_merges_private_and_public():
    backend = InMemoryBackend()
    router = ScriptedRouter()
    manager = MemoryManager(
        simulation_id="sim", backend=backend, llm_router=router,
        enable_contradiction=False, enable_reflection=False, enable_importance=False,
    )

    # Another agent posts publicly
    manager.record_agent_action(
        agent_id=2, round_num=1, content="public fact A",
        action_type="CREATE_POST", public=True,
    )
    # Our agent has a private note
    manager.record_agent_action(
        agent_id=5, round_num=1, content="my private thought B",
        action_type="DO_NOTHING",
    )

    results = manager.retrieve_for_agent(
        agent_id=5, query="public fact A", include_public=True, top_k=5,
    )
    contents = {r.content for r in results}
    assert "public fact A" in contents
    assert "my private thought B" in contents


def test_retrieve_for_agent_does_not_see_other_agents_private():
    backend = InMemoryBackend()
    router = ScriptedRouter()
    manager = MemoryManager(
        simulation_id="sim", backend=backend, llm_router=router,
        enable_contradiction=False, enable_reflection=False, enable_importance=False,
    )

    # Agent 2 writes privately
    manager.record_agent_action(
        agent_id=2, round_num=1, content="agent 2 secret",
        action_type="CREATE_POST", public=False,
    )
    results = manager.retrieve_for_agent(agent_id=5, query="secret", include_public=True)
    assert all("secret" not in r.content for r in results)


def test_on_round_complete_triggers_reflection_after_cadence():
    backend = InMemoryBackend()
    beliefs = json.dumps({"beliefs": [
        "I believe the topic is polarizing.",
        "I've noticed a shift in sentiment.",
    ]})
    router = ScriptedRouter(scripts={
        "memory.importance": ["6"] * 20,
        "memory.reflection": [beliefs],
    })
    manager = MemoryManager(
        simulation_id="sim", backend=backend, llm_router=router,
        every_n_rounds=3,  # reflect every 3 rounds
        enable_contradiction=False,
    )

    # Write 5 observations across rounds 1..3
    for r in range(1, 4):
        manager.record_agent_action(
            agent_id=1, round_num=r, content=f"round {r} observation",
            action_type="CREATE_POST",
        )
    # Round 1: last_reflected=-1, 1-(-1)=2 < 3 -> no reflect
    manager.on_round_complete(1)
    assert backend.list_reflections(namespace=Namespace.for_agent("sim", 1)) == []

    # Round 3: 3-(-1)=4 >= 3 -> reflect (but only 1 obs with round<=3 for this agent 1)
    # Actually agent 1 has 3 observations. Should reflect.
    manager.on_round_complete(3)
    reflections = backend.list_reflections(namespace=Namespace.for_agent("sim", 1))
    assert len(reflections) == 2


def test_stance_flip_creates_conflict_edge_end_to_end():
    """Phase-2 acceptance: when an agent's stance visibly flips, a contradiction
    edge between the two observations appears in the manager's conflicts view."""
    backend = InMemoryBackend()
    # Fixed embeddings so the second observation is the nearest neighbor of the first
    embeddings = [[1.0, 0.0, 0.0], [0.95, 0.1, 0.0]]
    router = ScriptedRouter(
        scripts={
            "memory.importance": ["7", "7"],
            "memory.contradiction": [json.dumps({"contradicts": True, "reason": "flip"})],
        },
        embeddings=embeddings,
    )
    manager = MemoryManager(
        simulation_id="sim", backend=backend, llm_router=router,
        enable_reflection=False,
    )

    manager.record_agent_action(
        agent_id=9, round_num=1, content="The new policy is excellent.",
        action_type="CREATE_POST",
    )
    manager.record_agent_action(
        agent_id=9, round_num=2, content="Actually, the new policy is terrible.",
        action_type="CREATE_POST",
    )

    conflicts = manager.list_conflicts(agent_id=9)
    assert len(conflicts) == 1
    # The edge should connect the two observations (order: from=newer, to=older).
    assert conflicts[0].from_id != conflicts[0].to_id


def test_manager_close_releases_backend():
    """Calling `close()` should propagate to the backend."""
    calls = []

    class _TrackingBackend(InMemoryBackend):
        def close(self) -> None:
            calls.append("close")

    backend = _TrackingBackend()
    manager = MemoryManager(simulation_id="sim", backend=backend, llm_router=ScriptedRouter())
    manager.close()
    assert calls == ["close"]

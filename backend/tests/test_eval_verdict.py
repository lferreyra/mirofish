"""Tests for the Verdict extractor."""

import pytest

from eval.verdict import verdict_from_public_timeline, verdict_from_report
from app.memory.base import Namespace, Observation
from app.memory.in_memory import InMemoryBackend
from app.memory.manager import MemoryManager
from app.personas.schema import Archetype, StructuredPersona


class _NoopRouter:
    def chat(self, *a, **k):
        from app.llm.base import LLMResponse
        return LLMResponse(text="5", model="noop", backend="noop")

    def embed(self, texts, **k):
        from app.llm.base import EmbeddingResponse
        return EmbeddingResponse(vectors=[[0.0] * 4 for _ in texts], model="noop", backend="noop")


def _manager():
    return MemoryManager(
        simulation_id="v",
        backend=InMemoryBackend(),
        llm_router=_NoopRouter(),
        enable_importance=False, enable_reflection=False, enable_contradiction=False,
    )


def _post(manager, agent_id, round_num, valence):
    """Write a public post whose text carries support/oppose tokens so the
    verdict extractor's fallback classifier can infer valence."""
    if valence > 0.2:
        content = "I support this positive change — great idea"
    elif valence < -0.2:
        content = "I oppose this, it's a bad and negative decision"
    else:
        content = "Discussion of the topic in neutral terms"
    obs = manager.record_agent_action(
        agent_id=agent_id, round_num=round_num, content=content,
        action_type="CREATE_POST", public=True,
    )
    return obs


def test_empty_timeline_returns_neutral_zero_confidence():
    manager = _manager()
    v = verdict_from_public_timeline(manager)
    assert v.direction == "neutral"
    assert v.magnitude == 0.0
    assert v.confidence == 0.0


def test_timeline_with_consistent_positive_valence_maps_to_positive():
    manager = _manager()
    personas = {i: StructuredPersona(agent_id=i, credibility=0.5) for i in range(1, 6)}
    for i in range(1, 6):
        _post(manager, i, 1, +0.7)
    v = verdict_from_public_timeline(manager, personas=personas)
    assert v.direction == "positive"
    assert v.magnitude > 0.5
    assert v.support_ratio > 0.0
    assert v.agent_count == 5


def test_credibility_tips_a_split_vote():
    """Two opposing posts at tied volume: the high-credibility author wins."""
    manager = _manager()
    personas = {
        1: StructuredPersona(agent_id=1, credibility=0.9, archetype=Archetype.EXPERT),
        2: StructuredPersona(agent_id=2, credibility=0.1),
    }
    _post(manager, 1, 1, +0.8)   # expert says positive
    _post(manager, 2, 1, -0.8)   # low-cred says negative
    v = verdict_from_public_timeline(manager, personas=personas)
    assert v.direction == "positive"
    assert v.support_ratio > 0.0


def test_verdict_from_report_parses_clean_json():
    payload = '{"direction": "negative", "magnitude": 0.6, "confidence": 0.8}'
    v = verdict_from_report(payload)
    assert v is not None
    assert v.direction == "negative"
    assert v.magnitude == pytest.approx(0.6)


def test_verdict_from_report_strips_code_fences():
    payload = '```json\n{"direction": "positive", "magnitude": 0.3, "confidence": 0.5}\n```'
    v = verdict_from_report(payload)
    assert v is not None
    assert v.direction == "positive"


def test_verdict_from_report_returns_none_on_garbage():
    assert verdict_from_report("not json at all") is None
    assert verdict_from_report('{"foo": "bar"}') is None  # missing direction

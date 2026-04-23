"""Tests for the deterministic MockRouter."""

import json

from eval.mocks import MockRouter
from app.llm.base import Role


def test_mock_router_chat_same_inputs_same_output():
    """Determinism: same prompt + same seed -> same text, byte-identical."""
    r1 = MockRouter(seed=42)
    r2 = MockRouter(seed=42)
    msgs = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hello"},
    ]
    a = r1.chat(Role.FAST, msgs, cache_key="memory.importance")
    b = r2.chat(Role.FAST, msgs, cache_key="memory.importance")
    assert a.text == b.text


def test_mock_router_importance_returns_valid_integer():
    router = MockRouter(seed=0)
    msgs = [{"role": "user", "content": "some observation content"}]
    text = router.chat(Role.FAST, msgs, cache_key="memory.importance").text
    assert text.isdigit()
    assert 1 <= int(text) <= 10


def test_mock_router_reflection_returns_three_beliefs_as_json():
    router = MockRouter(seed=0)
    text = router.chat(
        Role.BALANCED, [{"role": "user", "content": "stuff"}],
        cache_key="memory.reflection",
        response_format={"type": "json_object"},
    ).text
    parsed = json.loads(text)
    assert "beliefs" in parsed
    assert len(parsed["beliefs"]) == 3


def test_mock_router_contradiction_yields_mixed_signals():
    """Not always True, not always False — realistic distribution under
    different prompts."""
    router = MockRouter(seed=0)
    outcomes = []
    for i in range(20):
        msgs = [{"role": "user", "content": f"post {i}"}]
        text = router.chat(
            Role.FAST, msgs, cache_key="memory.contradiction",
            response_format={"type": "json_object"},
        ).text
        outcomes.append(json.loads(text)["contradicts"])
    # Should see both True and False across 20 varied prompts.
    assert any(outcomes) and not all(outcomes)


def test_mock_router_embed_is_deterministic_given_seed():
    r1 = MockRouter(seed=7)
    r2 = MockRouter(seed=7)
    v1 = r1.embed(["alpha", "beta"]).vectors
    v2 = r2.embed(["alpha", "beta"]).vectors
    assert v1 == v2


def test_mock_router_persona_generation_produces_valid_schema():
    router = MockRouter(seed=0)
    text = router.chat(
        Role.BALANCED,
        [{"role": "user", "content": "Entity: Dr. Chen (Expert)"}],
        cache_key="personas.generate",
        response_format={"type": "json_object"},
    ).text
    parsed = json.loads(text)
    # Must have every field StructuredPersona.from_dict expects
    assert "big_five" in parsed
    assert all(k in parsed["big_five"] for k in
               ("openness", "conscientiousness", "extraversion",
                "agreeableness", "neuroticism"))
    assert "conviction" in parsed
    assert "credibility" in parsed
    assert "background" in parsed
    assert "initial_stance" in parsed
    assert "valence" in parsed["initial_stance"]

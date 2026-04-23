"""Tests for PersonaGenerator. LLM is stubbed — no network needed."""

import json

from app.llm.base import LLMResponse
from app.personas.generator import PersonaGenerator
from app.personas.schema import Archetype


class _Router:
    def __init__(self, text: str):
        self._text = text
        self.calls = []

    def chat(self, role, messages, **kwargs):
        self.calls.append({"role": role, "kwargs": kwargs})
        return LLMResponse(text=self._text, model="fake", backend="fake")

    def embed(self, texts, **kwargs):
        raise NotImplementedError


def test_generator_assembles_persona_from_llm_json():
    payload = json.dumps({
        "big_five": {
            "openness": 0.8, "conscientiousness": 0.6,
            "extraversion": 0.4, "agreeableness": 0.7, "neuroticism": 0.3,
        },
        "conviction": 0.7,
        "credibility": 0.85,
        "background": "Dr. Patel, infectious disease epidemiologist, 15y exp",
        "initial_stance": {"label": "supports mandate", "valence": 0.6},
    })
    gen = PersonaGenerator(router=_Router(payload))

    persona = gen.generate(
        agent_id=11,
        entity_name="Dr. Sanjay Patel",
        entity_type="Expert",
        topic_summary="COVID-19 vaccine policy",
        archetype=Archetype.EXPERT,
    )
    assert persona.agent_id == 11
    assert persona.archetype == Archetype.EXPERT
    assert persona.big_five.openness == 0.8
    assert persona.credibility == 0.85
    assert persona.initial_stance.valence == 0.6


def test_generator_strips_code_fences_from_json_output():
    """Some models still wrap JSON in ``` fences even in JSON mode."""
    payload = (
        "```json\n"
        '{"big_five": {"openness": 0.5, "conscientiousness": 0.5, '
        '"extraversion": 0.5, "agreeableness": 0.5, "neuroticism": 0.5}, '
        '"conviction": 0.4, "credibility": 0.3, "background": "x", '
        '"initial_stance": {"label": "neutral", "valence": 0.0}}\n'
        "```"
    )
    gen = PersonaGenerator(router=_Router(payload))
    persona = gen.generate(
        agent_id=1, entity_name="X", entity_type="E", topic_summary="T",
    )
    assert persona.conviction == 0.4


def test_generator_falls_back_to_procedural_on_llm_error():
    """A broken LLM should not crash persona generation — we downgrade to a
    rule-based persona so the simulation keeps moving."""

    class _ErrRouter:
        def chat(self, *args, **kwargs):
            raise RuntimeError("kaboom")

    gen = PersonaGenerator(router=_ErrRouter())
    persona = gen.generate(
        agent_id=5, entity_name="Alice", entity_type="Person", topic_summary="t",
    )
    # Procedural fallback produces a NORMAL persona with neutral stance.
    assert persona.agent_id == 5
    assert persona.archetype == Archetype.NORMAL
    assert abs(persona.initial_stance.valence) <= 0.3


def test_generator_caps_background_length():
    """LLM might ignore the 200-char cap — schema-side truncation catches it."""
    long_bg = "A" * 500
    payload = json.dumps({
        "big_five": {"openness": 0.5, "conscientiousness": 0.5,
                     "extraversion": 0.5, "agreeableness": 0.5, "neuroticism": 0.5},
        "conviction": 0.5, "credibility": 0.5,
        "background": long_bg,
        "initial_stance": {"label": "x", "valence": 0.0},
    })
    gen = PersonaGenerator(router=_Router(payload))
    persona = gen.generate(
        agent_id=1, entity_name="X", entity_type="E", topic_summary="t",
    )
    assert len(persona.background) == 200


def test_generator_enforces_archetype_floors_for_bots_from_llm():
    """If an LLM returns a bot persona with odd credibility, we clamp."""
    payload = json.dumps({
        "big_five": {"openness": 0.5, "conscientiousness": 0.5,
                     "extraversion": 0.5, "agreeableness": 0.5, "neuroticism": 0.5},
        "conviction": 0.3,     # too low for a bot
        "credibility": 0.95,   # too high for a bot
        "background": "x",
        "initial_stance": {"label": "x", "valence": 0.0},
    })
    gen = PersonaGenerator(router=_Router(payload))
    persona = gen.generate(
        agent_id=1, entity_name="X", entity_type="E", topic_summary="t",
        archetype=Archetype.BOT,
    )
    # Conviction was clamped UP; credibility was clamped DOWN.
    assert persona.conviction >= 1.0
    assert persona.credibility <= 0.2

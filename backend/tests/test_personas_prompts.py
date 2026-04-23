"""Tests for the persona prompt-block template.

The ordering (stable prefix first, volatile content last) is load-bearing
for prefix caching — if it changes, cached-prefix hit rates collapse.
"""

from app.personas.prompts import persona_system_block
from app.personas.schema import Archetype, BigFive, StanceVector, StructuredPersona


def _base_persona(**overrides) -> StructuredPersona:
    kwargs = dict(
        agent_id=7,
        archetype=Archetype.NORMAL,
        big_five=BigFive(openness=0.7, conscientiousness=0.4,
                         extraversion=0.6, agreeableness=0.5, neuroticism=0.3),
        conviction=0.6,
        credibility=0.5,
        background="40yo teacher in Ohio",
        initial_stance=StanceVector(label="moderate", valence=+0.2),
    )
    kwargs.update(overrides)
    return StructuredPersona(**kwargs)


def test_stable_prefix_identical_across_agents():
    """Two agents with different volatile sections must share the same prefix
    up to the `--- YOUR PERSONA ---` marker. Without this, prefix caching
    doesn't kick in."""
    a = persona_system_block(_base_persona(agent_id=1))
    b = persona_system_block(_base_persona(agent_id=2))
    marker = "--- YOUR PERSONA ---"
    # Everything before the marker should be byte-identical.
    assert a.split(marker)[0] == b.split(marker)[0]


def test_bot_archetype_embeds_narrative():
    persona = _base_persona(
        archetype=Archetype.BOT,
        extras={"narrative": "Buy MiroCoin"},
    )
    block = persona_system_block(persona)
    assert "bot_narrative" in block
    assert "Buy MiroCoin" in block


def test_troll_archetype_embeds_tone():
    persona = _base_persona(archetype=Archetype.TROLL, extras={"tone": "dismissive"})
    block = persona_system_block(persona)
    assert "troll_tone" in block
    assert "dismissive" in block


def test_conviction_appears_in_volatile_section():
    """Agents should see their own conviction + derived opposing-posts count."""
    persona = _base_persona(conviction=0.8)
    block = persona_system_block(persona)
    assert "conviction: 0.80" in block
    # ceil(8.0) = 8 opposing posts needed
    assert "8 convincingly opposing posts" in block


def test_topic_summary_appended_when_provided():
    persona = _base_persona()
    block = persona_system_block(persona, topic_summary="Policy X debate")
    assert "topic_context: Policy X debate" in block


def test_archetype_rules_differ_per_archetype():
    """The one-sentence archetype rule must vary — otherwise bots and experts
    get the same behavior bias."""
    a = persona_system_block(_base_persona(archetype=Archetype.EXPERT))
    b = persona_system_block(_base_persona(archetype=Archetype.BOT))
    assert "subject-matter expert" in a
    assert "promotional bot" in b
    assert a != b

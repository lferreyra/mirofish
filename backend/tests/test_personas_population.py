"""Tests for population-level archetype assignment."""

import random

import pytest

from app.personas.population import (
    build_bot_persona,
    build_population,
    build_troll_persona,
)
from app.personas.schema import Archetype


def test_population_default_is_all_normal():
    """Default Phase-4 config: no bots, no trolls — every agent is NORMAL."""
    pop = build_population(agent_ids=list(range(20)))
    assert pop.bot_count == 0
    assert pop.troll_count == 0
    assert pop.normal_count == 20
    assert all(a == Archetype.NORMAL for a in pop.assignments.values())


def test_population_percentages_round_down():
    """`ceil`-style rounding would over-allocate. We floor so remainder -> NORMAL."""
    # 10% of 7 = 0.7 -> floor to 0 bots; all 7 -> NORMAL
    pop = build_population(agent_ids=list(range(7)), bot_pct=10.0)
    assert pop.bot_count == 0
    assert pop.normal_count == 7


def test_population_exact_percentages_allocate_correctly():
    pop = build_population(
        agent_ids=list(range(100)),
        bot_pct=10.0, troll_pct=5.0,
        media_pct=2.0, expert_pct=3.0,
        rng=random.Random(42),
    )
    assert pop.bot_count == 10
    assert pop.troll_count == 5
    assert pop.media_count == 2
    assert pop.expert_count == 3
    assert pop.normal_count == 80


def test_population_seed_is_deterministic():
    """Same seed -> same assignment. Crucial for reproducible eval runs."""
    pop_a = build_population(
        agent_ids=list(range(50)), bot_pct=10.0, rng=random.Random(7),
    )
    pop_b = build_population(
        agent_ids=list(range(50)), bot_pct=10.0, rng=random.Random(7),
    )
    assert pop_a.assignments == pop_b.assignments


def test_population_rejects_over_100_total():
    with pytest.raises(ValueError):
        build_population(
            agent_ids=[1, 2, 3],
            bot_pct=60.0, troll_pct=50.0,
        )


def test_population_rejects_negative_percent():
    with pytest.raises(ValueError):
        build_population(agent_ids=[1], bot_pct=-1.0)


def test_bot_persona_has_fixed_narrative_in_extras():
    p = build_bot_persona(agent_id=7, narrative="Buy MiroCoin now")
    assert p.archetype == Archetype.BOT
    assert p.extras["narrative"] == "Buy MiroCoin now"
    # Bots are immovable
    assert p.conviction == 1.0
    # Bots are noise — low credibility
    assert p.credibility <= 0.2


def test_troll_persona_carries_tone():
    p = build_troll_persona(agent_id=9, tone="sarcastic")
    assert p.archetype == Archetype.TROLL
    assert p.extras["tone"] == "sarcastic"

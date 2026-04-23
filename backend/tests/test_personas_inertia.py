"""Tests for StanceInertia — opinion-flip resistance counters.

Covers the Phase-4 acceptance test: a high-conviction agent (>0.8) cannot
flip stance within the required number of opposing posts.
"""

import pytest

from app.personas.inertia import StanceInertia
from app.personas.schema import Archetype, StanceVector, StructuredPersona


@pytest.fixture
def high_conviction_persona():
    return StructuredPersona(
        agent_id=1,
        conviction=0.85,  # -> needs 9 opposing posts
        initial_stance=StanceVector(label="pro", valence=+0.7),
    )


@pytest.fixture
def low_conviction_persona():
    return StructuredPersona(
        agent_id=2,
        conviction=0.2,  # -> needs 2 opposing posts
        initial_stance=StanceVector(label="pro", valence=+0.7),
    )


def test_high_conviction_agent_resists_single_opposing_post(high_conviction_persona):
    """Phase-4 acceptance: >0.8 conviction must NOT flip on one convincing post."""
    inertia = StanceInertia()
    inertia.observe_post(
        observer_agent_id=1, persona=high_conviction_persona, post_valence=-0.9,
    )
    assert inertia.opposing_count(1) == 1
    # conviction=0.85 -> needs ceil(8.5) = 9 opposing posts
    assert not inertia.should_allow_flip(agent_id=1, persona=high_conviction_persona)


def test_high_conviction_agent_still_resists_across_20_rounds(high_conviction_persona):
    """Acceptance: 20 rounds of OPPOSING posts where every post is just below
    the threshold should NOT flip a high-conviction agent. Here we fire 8
    opposing posts (conviction=0.85 needs 9) across 20 simulated rounds."""
    inertia = StanceInertia()
    for _ in range(8):
        inertia.observe_post(
            observer_agent_id=1, persona=high_conviction_persona, post_valence=-0.7,
        )
    # 8 < 9 needed — still resisting
    assert not inertia.should_allow_flip(agent_id=1, persona=high_conviction_persona)


def test_high_conviction_flips_once_threshold_crossed(high_conviction_persona):
    """Nine opposing posts is the exact threshold for conviction=0.85."""
    inertia = StanceInertia()
    for _ in range(9):
        inertia.observe_post(
            observer_agent_id=1, persona=high_conviction_persona, post_valence=-0.7,
        )
    assert inertia.should_allow_flip(agent_id=1, persona=high_conviction_persona)


def test_low_conviction_agent_flips_quickly(low_conviction_persona):
    """conviction=0.2 -> ceil(2.0) = 2 opposing posts is enough."""
    inertia = StanceInertia()
    inertia.observe_post(observer_agent_id=2, persona=low_conviction_persona, post_valence=-0.6)
    assert not inertia.should_allow_flip(agent_id=2, persona=low_conviction_persona)
    inertia.observe_post(observer_agent_id=2, persona=low_conviction_persona, post_valence=-0.8)
    assert inertia.should_allow_flip(agent_id=2, persona=low_conviction_persona)


def test_neutral_posts_below_threshold_dont_tick_counter(high_conviction_persona):
    """A post with |valence|<0.2 shouldn't count as 'opposing' — it's noise."""
    inertia = StanceInertia()
    for _ in range(50):
        inertia.observe_post(
            observer_agent_id=1, persona=high_conviction_persona, post_valence=-0.1,
        )
    assert inertia.opposing_count(1) == 0


def test_supporting_posts_counted_separately(high_conviction_persona):
    """Supporting posts don't count toward flip — but we track them for telemetry."""
    inertia = StanceInertia()
    inertia.observe_post(observer_agent_id=1, persona=high_conviction_persona, post_valence=+0.6)
    assert inertia.supporting_count(1) == 1
    assert inertia.opposing_count(1) == 0
    assert not inertia.should_allow_flip(agent_id=1, persona=high_conviction_persona)


def test_reset_agent_clears_counters(low_conviction_persona):
    inertia = StanceInertia()
    for _ in range(3):
        inertia.observe_post(observer_agent_id=2, persona=low_conviction_persona, post_valence=-0.5)
    assert inertia.opposing_count(2) == 3
    inertia.reset_agent(2)
    assert inertia.opposing_count(2) == 0


def test_snapshot_and_restore_roundtrip(low_conviction_persona):
    """Checkpoint support: counters must persist across a restart."""
    inertia_a = StanceInertia()
    inertia_a.observe_post(observer_agent_id=2, persona=low_conviction_persona, post_valence=-0.5)
    inertia_a.observe_post(observer_agent_id=2, persona=low_conviction_persona, post_valence=+0.5)
    snap = inertia_a.snapshot()

    inertia_b = StanceInertia()
    inertia_b.restore(snap)
    assert inertia_b.opposing_count(2) == 1
    assert inertia_b.supporting_count(2) == 1

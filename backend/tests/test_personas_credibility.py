"""Tests for credibility-weighted retrieval re-ranking."""

from app.memory.base import Observation
from app.personas.credibility import CredibilityWeighter
from app.personas.schema import Archetype, StructuredPersona


def _obs(author_id, content, combined_score):
    o = Observation(
        id=f"o-{author_id}-{content}", namespace="public:s:timeline",
        content=content, round_num=0, ts=0.0,
    )
    o.author_id = author_id
    o.combined_score = combined_score
    return o


def test_high_credibility_author_boosts_score_above_low_credibility():
    """A CDC-tier author should outrank a rando with the same base score."""
    personas = {
        1: StructuredPersona(agent_id=1, credibility=0.9, archetype=Archetype.EXPERT),
        2: StructuredPersona(agent_id=2, credibility=0.2),
    }
    weighter = CredibilityWeighter(personas, weight=1.0)
    records = [
        _obs(1, "expert post", combined_score=0.5),
        _obs(2, "rando post", combined_score=0.5),  # tied base score
    ]
    reranked = weighter.reweight(records)
    # Expert (credibility 0.9, multiplier 1.4) should now outrank rando
    assert reranked[0].author_id == 1
    assert reranked[0].combined_score > reranked[1].combined_score


def test_credibility_multiplier_formula():
    """Score = base * (1 + weight*(credibility - 0.5)).

    With weight=1.0, credibility=1.0 -> 1.5x; credibility=0.0 -> 0.5x.
    """
    personas = {1: StructuredPersona(agent_id=1, credibility=1.0)}
    weighter = CredibilityWeighter(personas, weight=1.0)
    [r] = weighter.reweight([_obs(1, "x", 0.4)])
    # 0.4 * 1.5 == 0.6
    assert abs(r.combined_score - 0.6) < 1e-6


def test_weighter_zero_weight_is_noop_on_score():
    """weight=0.0 disables the re-weighting; combined scores are unchanged."""
    personas = {1: StructuredPersona(agent_id=1, credibility=0.0)}  # would otherwise crash to 0
    weighter = CredibilityWeighter(personas, weight=0.0)
    [r] = weighter.reweight([_obs(1, "x", 0.75)])
    assert abs(r.combined_score - 0.75) < 1e-6


def test_unknown_author_uses_neutral_credibility():
    """If we don't know an author, don't silently drop their post."""
    weighter = CredibilityWeighter({}, weight=1.0)
    # author_id=99 is not in persona_store -> neutral (0.5) -> 1.0x multiplier
    [r] = weighter.reweight([_obs(99, "orphan post", 0.4)])
    assert abs(r.combined_score - 0.4) < 1e-6


def test_weighter_returns_new_list_without_mutating_original():
    """Callers should be able to keep the original list around."""
    personas = {1: StructuredPersona(agent_id=1, credibility=0.9)}
    weighter = CredibilityWeighter(personas, weight=1.0)
    originals = [_obs(1, "x", 0.5)]
    reranked = weighter.reweight(originals)
    assert originals[0].combined_score == 0.5  # untouched
    assert reranked[0].combined_score != 0.5

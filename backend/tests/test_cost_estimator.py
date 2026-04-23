"""Tests for the pre-flight cost estimator."""

import pytest

from app.cost.estimator import (
    ApprovalRequired,
    CostEstimate,
    DEFAULT_BUDGETS,
    RoleBudget,
    estimate_simulation_cost,
    require_approval,
)


def test_estimate_scales_linearly_with_agents_and_rounds():
    """Doubling agents × rounds should ~double the cost + tokens."""
    small = estimate_simulation_cost(
        agent_count=10, rounds=5,
        role_models={
            "fast": ("openai", "gpt-4o-mini"),
            "balanced": ("openai", "gpt-4o-mini"),
            "heavy": ("openai", "gpt-4o-mini"),
            "embed": ("openai", "text-embedding-3-large"),
        },
    )
    big = estimate_simulation_cost(
        agent_count=20, rounds=10,
        role_models={
            "fast": ("openai", "gpt-4o-mini"),
            "balanced": ("openai", "gpt-4o-mini"),
            "heavy": ("openai", "gpt-4o-mini"),
            "embed": ("openai", "text-embedding-3-large"),
        },
    )
    # 4x agents*rounds -> cost should be ~4x
    assert big.total_usd == pytest.approx(small.total_usd * 4, rel=1e-6)
    assert big.total_tokens == small.total_tokens * 4


def test_unknown_provider_yields_zero_cost_and_note():
    """Unknown models shouldn't crash — they report cost_usd=0 + a note."""
    estimate = estimate_simulation_cost(
        agent_count=5, rounds=2,
        role_models={"balanced": ("obscure_vendor", "unknown-model-x")},
    )
    assert estimate.total_usd == 0.0
    assert "no pricing data" in estimate.note


def test_cached_fraction_discounts_input_cost():
    """Higher cached fraction -> lower USD when cached rate < input rate."""
    low_cache_budget = {
        "fast": RoleBudget("fast", calls_per_agent_per_round=1.0,
                            tokens_in_per_call=1000, tokens_out_per_call=0,
                            cached_fraction=0.0),
    }
    high_cache_budget = {
        "fast": RoleBudget("fast", calls_per_agent_per_round=1.0,
                            tokens_in_per_call=1000, tokens_out_per_call=0,
                            cached_fraction=0.9),
    }
    low = estimate_simulation_cost(
        agent_count=10, rounds=10,
        role_models={"fast": ("openai", "gpt-4o-mini")},
        budgets=low_cache_budget,
    )
    high = estimate_simulation_cost(
        agent_count=10, rounds=10,
        role_models={"fast": ("openai", "gpt-4o-mini")},
        budgets=high_cache_budget,
    )
    # Both use gpt-4o-mini whose cached rate is half the input rate.
    assert high.total_usd < low.total_usd


def test_approval_required_flag_when_over_cap():
    estimate = estimate_simulation_cost(
        agent_count=500, rounds=50,
        role_models={
            "fast": ("openai", "gpt-4o-mini"),
            "balanced": ("openai", "gpt-4o-mini"),
            "heavy": ("openai", "gpt-4o"),
            "embed": ("openai", "text-embedding-3-large"),
        },
        user_cap_usd=0.50,
    )
    assert estimate.approval_required is True


def test_require_approval_raises_over_cap():
    estimate = CostEstimate(
        agent_count=1, rounds=1, roles={}, total_usd=50.0, total_tokens=0,
    )
    with pytest.raises(ApprovalRequired) as exc_info:
        require_approval(estimate, user_cap_usd=10.0)
    assert exc_info.value.cap_usd == 10.0
    assert exc_info.value.estimate.total_usd == 50.0


def test_require_approval_zero_cap_is_disabled():
    """user_cap_usd=0 means 'no cap' — matches the Phase-1 pricing-table '0 = unlimited' convention."""
    estimate = CostEstimate(
        agent_count=1, rounds=1, roles={}, total_usd=99999.0, total_tokens=0,
    )
    require_approval(estimate, user_cap_usd=0.0)  # must not raise


def test_estimate_breakdown_per_role_is_present():
    estimate = estimate_simulation_cost(
        agent_count=10, rounds=5,
        role_models={"fast": ("openai", "gpt-4o-mini")},
    )
    # All four default roles should have an entry even when only one has
    # pricing data — the estimator still records token counts.
    assert set(estimate.roles.keys()) == {"fast", "balanced", "heavy", "embed"}


def test_env_overrides_merge_into_budgets(monkeypatch):
    """COST_BUDGET_FAST_CALLS=2.0 doubles fast-role call volume."""
    monkeypatch.setenv("COST_BUDGET_FAST_CALLS", "2.0")
    monkeypatch.setenv("COST_BUDGET_FAST_IN", "800")
    estimate = estimate_simulation_cost(
        agent_count=10, rounds=10,
        role_models={"fast": ("openai", "gpt-4o-mini")},
    )
    fast = estimate.roles["fast"]
    # 10 agents * 10 rounds * 2.0 calls = 200 calls
    assert fast.total_calls == 200.0
    # 200 calls * 800 tokens_in = 160_000 tokens_in
    assert fast.total_tokens_in == 160_000

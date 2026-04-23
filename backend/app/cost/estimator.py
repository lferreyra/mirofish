"""
Pre-flight cost estimator.

Per-agent, per-round token budget defaults (tuned against observed Phase-1
runs on Aliyun DashScope qwen-plus):
    fast       1 call, 400 tokens in, 80 out
    balanced   2 calls, 800 tokens in, 200 out        (post + comment pass)
    heavy      0.2 calls, 4000 tokens in, 1000 out     (report synthesis runs 1x
                                                        per simulation, amortized)
    embed      1 call,  200 tokens in

Operators override by passing a custom `{role: RoleBudget}` dict or via env
(`COST_BUDGET_<ROLE>_IN`, `COST_BUDGET_<ROLE>_OUT`, `COST_BUDGET_<ROLE>_CALLS`).

The estimator is deliberately conservative — actual runs should come in at
or below the estimate. A Phase-6 acceptance bar is that the estimate stays
within 20% of actual observed cost.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, Iterable, Optional

# Reuse the Phase-1 pricing table so ops don't maintain two copies.
from ..llm.accounting import _PRICING  # noqa: SLF001 — intentional internal re-use


@dataclass
class RoleBudget:
    """Per-agent, per-round budget for one role."""
    role: str
    calls_per_agent_per_round: float
    tokens_in_per_call: int
    tokens_out_per_call: int
    cached_fraction: float = 0.0   # fraction of input tokens expected to be prefix-cached


DEFAULT_BUDGETS: Dict[str, RoleBudget] = {
    "fast": RoleBudget(
        role="fast",
        calls_per_agent_per_round=1.0,
        tokens_in_per_call=400,
        tokens_out_per_call=80,
        cached_fraction=0.5,
    ),
    "balanced": RoleBudget(
        role="balanced",
        calls_per_agent_per_round=2.0,
        tokens_in_per_call=800,
        tokens_out_per_call=200,
        cached_fraction=0.3,
    ),
    # Heavy runs roughly once per simulation; spread across all agent-rounds
    # as 0.2 calls/agent/round so the math stays linear in (agents * rounds).
    "heavy": RoleBudget(
        role="heavy",
        calls_per_agent_per_round=0.2,
        tokens_in_per_call=4000,
        tokens_out_per_call=1000,
        cached_fraction=0.0,
    ),
    "embed": RoleBudget(
        role="embed",
        calls_per_agent_per_round=1.0,
        tokens_in_per_call=200,
        tokens_out_per_call=0,
        cached_fraction=0.0,
    ),
}


@dataclass
class RoleEstimate:
    role: str
    total_calls: float
    total_tokens_in: int
    total_tokens_out: int
    total_tokens_cached: int
    cost_usd: float
    provider: Optional[str] = None
    model: Optional[str] = None


@dataclass
class CostEstimate:
    agent_count: int
    rounds: int
    roles: Dict[str, RoleEstimate]
    total_usd: float
    total_tokens: int
    approval_required: bool = False
    user_cap_usd: Optional[float] = None
    note: str = ""

    def to_dict(self) -> dict:
        return {
            "agent_count": self.agent_count,
            "rounds": self.rounds,
            "total_usd": self.total_usd,
            "total_tokens": self.total_tokens,
            "approval_required": self.approval_required,
            "user_cap_usd": self.user_cap_usd,
            "note": self.note,
            "roles": {
                r: {
                    "role": e.role,
                    "total_calls": e.total_calls,
                    "total_tokens_in": e.total_tokens_in,
                    "total_tokens_out": e.total_tokens_out,
                    "total_tokens_cached": e.total_tokens_cached,
                    "cost_usd": e.cost_usd,
                    "provider": e.provider,
                    "model": e.model,
                }
                for r, e in self.roles.items()
            },
        }


class ApprovalRequired(Exception):
    """Raised by `require_approval` when the estimate exceeds the user cap."""

    def __init__(self, estimate: CostEstimate, cap_usd: float):
        super().__init__(
            f"estimated ${estimate.total_usd:.2f} exceeds user cap "
            f"${cap_usd:.2f}; approval required"
        )
        self.estimate = estimate
        self.cap_usd = cap_usd


# --------------------------------------------------------------------------
# public API
# --------------------------------------------------------------------------

def estimate_simulation_cost(
    *,
    agent_count: int,
    rounds: int,
    role_models: Optional[Dict[str, tuple[str, str]]] = None,  # role -> (provider, model)
    budgets: Optional[Dict[str, RoleBudget]] = None,
    user_cap_usd: Optional[float] = None,
) -> CostEstimate:
    """Return a breakdown of expected token usage + USD cost.

    `role_models` maps each role to (provider, model). When unset we look at
    env (`LLM_ROLE_<ROLE>_PROVIDER`, `LLM_ROLE_<ROLE>_MODEL`) and fall back
    to ("unknown", <role>). Unknown (provider, model) pairs have no entry
    in the pricing table and therefore show as cost_usd=0 — the estimate
    note flags this case.
    """
    budgets = _merge_env_overrides(budgets or DEFAULT_BUDGETS)
    role_models = role_models or _role_models_from_env()
    total_usd = 0.0
    total_tokens = 0
    roles: Dict[str, RoleEstimate] = {}
    missing_pricing: list[str] = []

    for role_name, budget in budgets.items():
        calls = agent_count * rounds * budget.calls_per_agent_per_round
        tokens_in = int(calls * budget.tokens_in_per_call)
        tokens_out = int(calls * budget.tokens_out_per_call)
        tokens_cached = int(tokens_in * budget.cached_fraction)
        uncached_in = tokens_in - tokens_cached

        provider, model = role_models.get(role_name, ("unknown", role_name))
        rates = _lookup_rates(provider, model)
        if rates is None:
            missing_pricing.append(f"{provider}:{model}")
            cost = 0.0
        else:
            input_rate, output_rate, cached_rate = rates
            cost = (
                uncached_in * input_rate
                + tokens_cached * cached_rate
                + tokens_out * output_rate
            ) / 1_000_000.0

        roles[role_name] = RoleEstimate(
            role=role_name, total_calls=calls,
            total_tokens_in=tokens_in, total_tokens_out=tokens_out,
            total_tokens_cached=tokens_cached, cost_usd=cost,
            provider=provider, model=model,
        )
        total_usd += cost
        total_tokens += tokens_in + tokens_out

    note = ""
    if missing_pricing:
        note = "no pricing data for: " + ", ".join(sorted(set(missing_pricing)))

    approval = False
    if user_cap_usd is not None and total_usd > user_cap_usd:
        approval = True

    return CostEstimate(
        agent_count=agent_count, rounds=rounds, roles=roles,
        total_usd=total_usd, total_tokens=total_tokens,
        approval_required=approval, user_cap_usd=user_cap_usd, note=note,
    )


def require_approval(estimate: CostEstimate, user_cap_usd: float) -> None:
    """Raise `ApprovalRequired` if the estimate exceeds the cap."""
    if user_cap_usd <= 0:
        return
    if estimate.total_usd > user_cap_usd:
        raise ApprovalRequired(estimate, user_cap_usd)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _role_models_from_env() -> Dict[str, tuple[str, str]]:
    out: Dict[str, tuple[str, str]] = {}
    for role in ("fast", "balanced", "heavy", "embed"):
        provider = os.environ.get(f"LLM_ROLE_{role.upper()}_PROVIDER")
        model = (
            os.environ.get(f"LLM_ROLE_{role.upper()}_MODEL")
            or os.environ.get("LLM_MODEL_NAME")
        )
        if provider and model:
            out[role] = (provider.lower(), model)
    return out


def _lookup_rates(provider: str, model: str):
    """Return (input_per_mtok, output_per_mtok, cached_input_per_mtok) or None."""
    p = (provider or "").lower()
    return _PRICING.get((p, model)) or _PRICING.get((p, "*"))


def _merge_env_overrides(budgets: Dict[str, RoleBudget]) -> Dict[str, RoleBudget]:
    """Apply COST_BUDGET_<ROLE>_{CALLS,IN,OUT,CACHED} overrides."""
    merged: Dict[str, RoleBudget] = {}
    for role, budget in budgets.items():
        up = role.upper()
        merged[role] = RoleBudget(
            role=role,
            calls_per_agent_per_round=_float_env(f"COST_BUDGET_{up}_CALLS",
                                                  budget.calls_per_agent_per_round),
            tokens_in_per_call=_int_env(f"COST_BUDGET_{up}_IN",
                                          budget.tokens_in_per_call),
            tokens_out_per_call=_int_env(f"COST_BUDGET_{up}_OUT",
                                           budget.tokens_out_per_call),
            cached_fraction=_float_env(f"COST_BUDGET_{up}_CACHED",
                                        budget.cached_fraction),
        )
    return merged


def _int_env(name: str, default: int) -> int:
    try:
        v = os.environ.get(name)
        return int(v) if v is not None else default
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    try:
        v = os.environ.get(name)
        return float(v) if v is not None else default
    except ValueError:
        return default

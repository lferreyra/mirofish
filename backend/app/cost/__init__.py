"""
Pre-flight cost estimator.

    estimate_simulation_cost(agent_count, rounds, pricing)
        -> CostEstimate(per_role_breakdown, total_usd, ...)

Estimates are bucketed by role (fast/balanced/heavy/embed) using per-role
token budgets. Pricing is read from the same table the Phase-1 LLM
accounting layer uses (`LLM_PRICING_JSON` override honored).

The simulation API calls `require_approval(estimate, user_cap_usd)` before
spending real tokens; the frontend shows a dialog with the estimate.
"""

from .estimator import (
    CostEstimate,
    RoleBudget,
    estimate_simulation_cost,
    require_approval,
)

__all__ = [
    "CostEstimate",
    "RoleBudget",
    "estimate_simulation_cost",
    "require_approval",
]

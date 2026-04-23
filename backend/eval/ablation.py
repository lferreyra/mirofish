"""
CLI: python -m backend.eval.ablation --case <path> [--deterministic] [--mock-llm]

For one case, runs the eval N times with different feature-flag combos:

    baseline               -- all Phase-2 + Phase-4 features ON
    no_importance          -- importance scoring disabled
    no_reflection          -- reflection scheduler disabled
    no_contradiction       -- contradiction detector disabled
    no_credibility         -- credibility re-ranking disabled
    no_conviction          -- inertia counter disabled
    no_phase2              -- all three Phase-2 features off
    no_phase4              -- all three Phase-4 features off

Prints a comparison table showing each variant's composite score and the
marginal delta vs baseline. The Phase-5 acceptance criterion asks for this
table in the final PR description.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
from typing import Dict, List, Optional

# Same sys.path guard as runner.py — see that file for rationale.
_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.dirname(_HERE)
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from .determinism import deterministic_run
from .mocks import MockRouter
from .pipeline import DatasetCase, FeatureFlags, RunConfig, run_case
from .runner import _resolve_case_path
from .scoring import score_verdict


def _build_variants() -> Dict[str, FeatureFlags]:
    """Map variant_name -> FeatureFlags."""
    baseline = FeatureFlags()
    variants: Dict[str, FeatureFlags] = {"baseline": baseline}
    for flag in (
        "enable_importance", "enable_reflection", "enable_contradiction",
        "enable_credibility", "enable_conviction",
    ):
        f = dataclasses.replace(baseline, **{flag: False})
        variants[f"no_{flag.replace('enable_', '')}"] = f

    variants["no_phase2"] = dataclasses.replace(
        baseline,
        enable_importance=False, enable_reflection=False,
        enable_contradiction=False,
    )
    variants["no_phase4"] = dataclasses.replace(
        baseline,
        enable_credibility=False, enable_conviction=False,
    )
    return variants


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="backend.eval.ablation",
        description="Run ablation sweep for one case; print composite-score table.",
    )
    parser.add_argument("--case", required=True)
    parser.add_argument("--deterministic", action="store_true")
    parser.add_argument("--mock-llm", action="store_true")
    parser.add_argument("--num-agents", type=int, default=20)
    parser.add_argument("--num-rounds", type=int, default=10)
    parser.add_argument("--seed", type=int, default=1234)
    parser.add_argument("--output-json", action="store_true")
    args = parser.parse_args(argv)

    case = DatasetCase.load(_resolve_case_path(args.case))
    variants = _build_variants()

    rows: List[Dict] = []
    for name, flags in variants.items():
        cfg = RunConfig(
            num_agents=args.num_agents,
            num_rounds=args.num_rounds,
            seed=args.seed,
            flags=flags,
        )
        router = MockRouter(seed=args.seed) if args.mock_llm else None
        ctx = deterministic_run(seed=args.seed) if args.deterministic else _nullctx()
        with ctx:
            result = run_case(case, config=cfg, router=router)
        score = score_verdict(result.verdict, result.truth)
        rows.append({
            "variant": name,
            "composite": score.composite,
            "directional": score.directional,
            "magnitude_error": score.magnitude_error,
            "calibration": score.calibration,
            "verdict_direction": result.verdict.direction,
            "verdict_magnitude": result.verdict.magnitude,
            "reflections": result.reflections_written,
            "conflicts": result.conflicts_written,
        })

    # Baseline delta
    baseline_score = next(r["composite"] for r in rows if r["variant"] == "baseline")
    for r in rows:
        r["delta_vs_baseline"] = r["composite"] - baseline_score

    if args.output_json:
        print(json.dumps({"case": case.name, "rows": rows}, indent=2, sort_keys=True))
    else:
        _print_table(case.name, rows)
    return 0


def _print_table(case_name: str, rows: List[Dict]) -> None:
    print(f"Ablation table for case: {case_name}")
    print(f"{'variant':<20} {'composite':>10} {'Δ vs base':>10} "
          f"{'dir':>5} {'mag_err':>8} {'calib':>6} {'refs':>5} {'conf':>5}")
    print("-" * 75)
    for r in rows:
        print(
            f"{r['variant']:<20} "
            f"{r['composite']:>10.3f} "
            f"{r['delta_vs_baseline']:>+10.3f} "
            f"{r['directional']:>5.2f} "
            f"{r['magnitude_error']:>8.2f} "
            f"{r['calibration']:>6.2f} "
            f"{r['reflections']:>5d} "
            f"{r['conflicts']:>5d}"
        )


class _nullctx:
    def __enter__(self): return None
    def __exit__(self, *exc): return False


if __name__ == "__main__":
    sys.exit(main())

"""
CLI: python -m backend.eval.runner --case <path> [--deterministic] [--mock-llm]

Acceptance criterion (Phase 5):
    python -m backend.eval.runner --case datasets/<case> --deterministic
    produces a NUMERIC score.
    Running it twice produces IDENTICAL output (when --mock-llm is also
    set; a live LLM can't be guaranteed byte-identical).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Optional

# Ensure `backend/` is on sys.path so absolute `import app.*` works both under
# `python -m backend.eval.runner` (CWD = repo root) and pytest invocations.
_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.dirname(_HERE)
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from .determinism import DETERMINISTIC_VERSION, deterministic_run
from .mocks import MockRouter
from .pipeline import DatasetCase, RunConfig, run_case
from .scoring import score_verdict
from .storage import append_result


def _resolve_case_path(case_arg: str) -> str:
    """Accept either an absolute path or a name under `datasets/`."""
    if os.path.isdir(case_arg):
        return os.path.abspath(case_arg)
    here = os.path.dirname(os.path.abspath(__file__))
    rel = os.path.join(here, "datasets", case_arg)
    if os.path.isdir(rel):
        return rel
    raise FileNotFoundError(f"case not found: {case_arg}")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="backend.eval.runner",
        description="Run a MiroFish eval case and score it.",
    )
    parser.add_argument("--case", required=True,
                        help="dataset case dir or name (under eval/datasets/)")
    parser.add_argument("--deterministic", action="store_true",
                        help="pin seeds + temperature; pairs with --mock-llm for byte-identical output")
    parser.add_argument("--mock-llm", action="store_true",
                        help="use the deterministic MockRouter (no network)")
    parser.add_argument("--num-agents", type=int, default=20)
    parser.add_argument("--num-rounds", type=int, default=10)
    parser.add_argument("--seed", type=int, default=1234)
    parser.add_argument("--bot-pct", type=float, default=0.0)
    parser.add_argument("--troll-pct", type=float, default=0.0)
    parser.add_argument("--persist", action="store_true",
                        help="append the scored result to the jsonl store")
    parser.add_argument("--output-json", action="store_true",
                        help="emit the full run record as JSON on stdout")
    args = parser.parse_args(argv)

    case = DatasetCase.load(_resolve_case_path(args.case))

    config = RunConfig(
        num_agents=args.num_agents,
        num_rounds=args.num_rounds,
        seed=args.seed,
    )
    config.flags.bot_pct = args.bot_pct
    config.flags.troll_pct = args.troll_pct

    # Determinism block pins seeds + now_ts so verdict + timestamps are stable.
    ctx = deterministic_run(seed=args.seed) if args.deterministic else _nullctx()

    # When --deterministic is set we *require* --mock-llm for the acceptance
    # criterion. Without it, a live LLM can silently inject nondeterminism.
    if args.deterministic and not args.mock_llm:
        print(
            "[eval.runner] warning: --deterministic without --mock-llm "
            "cannot guarantee byte-identical output. Did you mean to pass "
            "both?", file=sys.stderr,
        )

    router = MockRouter(seed=args.seed) if args.mock_llm else None

    with ctx:
        result = run_case(case, config=config, router=router)

    score = score_verdict(result.verdict, result.truth)

    record = {
        "case": case.name,
        "deterministic": bool(args.deterministic),
        "mock_llm": bool(args.mock_llm),
        "determinism_version": DETERMINISTIC_VERSION,
        "run": result.to_dict(),
        "score": score.to_dict(),
    }

    if args.persist:
        append_result(record)

    if args.output_json:
        print(json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        _print_summary(record)

    # Exit code: 0 on composite >= 0.5, 1 otherwise. CI smoke test uses this
    # as a regression guard on the deterministic fixture case.
    return 0 if score.composite >= 0.5 else 1


def _print_summary(record: dict) -> None:
    run = record["run"]
    score = record["score"]
    truth = run["truth"]
    verdict = run["verdict"]
    print(f"case: {record['case']}   (determinism_version={record['determinism_version']})")
    print(f"  truth:   direction={truth['direction']} magnitude={truth['magnitude']:.2f} "
          f"confidence={truth.get('confidence', 1.0):.2f}")
    print(f"  verdict: direction={verdict['direction']} magnitude={verdict['magnitude']:.2f} "
          f"confidence={verdict['confidence']:.2f} "
          f"(support_ratio={verdict['support_ratio']:+.3f}, agents={verdict['agent_count']})")
    print(f"  score:   directional={score['directional']:.2f} "
          f"magnitude_error={score['magnitude_error']:.2f} "
          f"calibration={score['calibration']:.2f} "
          f"composite={score['composite']:.3f}")
    print(f"  pipeline: reflections={run['reflections_written']} "
          f"conflicts={run['conflicts_written']} posts/round={run['round_posts']}")


class _nullctx:
    def __enter__(self): return None
    def __exit__(self, *exc): return False


if __name__ == "__main__":
    sys.exit(main())

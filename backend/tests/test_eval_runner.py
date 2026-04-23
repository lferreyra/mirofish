"""End-to-end tests for the eval runner + ablation CLIs.

Covers the Phase-5 acceptance criteria:
  1. `python -m backend.eval.runner --case <c> --deterministic` produces a
     numeric score.
  2. Running it twice in --deterministic --mock-llm mode produces IDENTICAL
     output.
  3. The ablation tool produces a table showing marginal contribution of
     features.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
CASE = "sample_policy_carbon_tax"


def _run(argv):
    """Run the runner CLI and return (exit_code, stdout)."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    env["EVAL_RESULTS_PATH"] = str(REPO_ROOT / "backend" / "data" / "test-eval-results.jsonl")
    result = subprocess.run(
        [sys.executable, "-m", "backend.eval.runner"] + list(argv),
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env=env,
        timeout=120,
    )
    return result.returncode, result.stdout, result.stderr


def _run_ablation(argv):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    result = subprocess.run(
        [sys.executable, "-m", "backend.eval.ablation"] + list(argv),
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env=env,
        timeout=120,
    )
    return result.returncode, result.stdout, result.stderr


def test_runner_produces_numeric_score_in_deterministic_mode():
    """Phase-5 acceptance #1: runner produces a numeric score."""
    rc, out, err = _run(["--case", CASE, "--deterministic", "--mock-llm",
                         "--output-json"])
    # Exit code may be 0 or 1 depending on whether the mock-derived verdict
    # matches truth; what matters is that a JSON document with a numeric
    # composite score is emitted.
    assert rc in (0, 1), f"unexpected exit: stdout={out!r} stderr={err!r}"
    payload = json.loads(out)
    assert "score" in payload
    assert isinstance(payload["score"]["composite"], float)
    assert 0.0 <= payload["score"]["composite"] <= 1.0


def test_runner_is_byte_identical_across_two_runs():
    """Phase-5 acceptance #2: two --deterministic --mock-llm runs produce
    identical output."""
    rc1, out1, _ = _run(["--case", CASE, "--deterministic", "--mock-llm",
                         "--output-json"])
    rc2, out2, _ = _run(["--case", CASE, "--deterministic", "--mock-llm",
                         "--output-json"])
    assert rc1 == rc2
    assert out1 == out2, "deterministic runs diverged — determinism broken"


def test_runner_warns_when_deterministic_without_mock():
    """Documented behavior: --deterministic alone can't guarantee byte-identical
    output; the runner should warn."""
    rc, out, err = _run(["--case", CASE, "--deterministic", "--output-json"])
    assert rc in (0, 1)
    assert "warning" in err.lower()


def test_ablation_table_is_emitted():
    """Phase-5 acceptance #3: ablation produces a comparison table."""
    rc, out, err = _run_ablation([
        "--case", CASE, "--deterministic", "--mock-llm",
    ])
    assert rc == 0, f"ablation failed: stderr={err!r}"
    # Table header must be present + every variant name must appear
    assert "variant" in out
    assert "composite" in out
    for variant in (
        "baseline",
        "no_importance", "no_reflection", "no_contradiction",
        "no_credibility", "no_conviction",
        "no_phase2", "no_phase4",
    ):
        assert variant in out, f"ablation table missing variant {variant!r}"


def test_ablation_json_mode_is_parseable():
    """--output-json on ablation returns a valid document for programmatic use."""
    rc, out, _ = _run_ablation([
        "--case", CASE, "--deterministic", "--mock-llm", "--output-json",
    ])
    assert rc == 0
    data = json.loads(out)
    assert data["case"] == CASE
    baseline = next(r for r in data["rows"] if r["variant"] == "baseline")
    assert baseline["delta_vs_baseline"] == 0.0

#!/usr/bin/env python3
"""
Generate ranked market picks from a structured scan batch.

This script is opinionated on purpose. It forces a final expression choice:
- `shares`
- `leaps_call`
- `reject`

That keeps the workflow focused on pick generation rather than open-ended notes.
"""

from __future__ import annotations

import argparse
import json
import sys
import types
from dataclasses import asdict, dataclass
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any, Dict, List


DEFAULT_STOCK_FIT_WEIGHTS: Dict[str, float] = {
    "market_accessibility": 0.10,
    "implementation_simplicity": 0.12,
    "balance_sheet_resilience": 0.14,
    "dilution_risk_inverse": 0.12,
    "thesis_linearity": 0.18,
    "duration_tolerance": 0.22,
    "listing_quality": 0.12,
}

DEFAULT_LEAPS_BIAS_WEIGHTS: Dict[str, float] = {
    "iv_cheapness": 0.24,
    "surface_staleness": 0.18,
    "pre_expiration_repricing_potential": 0.24,
    "stock_vs_call_convexity_advantage": 0.24,
    "long_dated_liquidity_quality": 0.10,
}


ASYMMETRY_SIGNAL_WEIGHTS: Dict[str, float] = {
    "hiddenness": 0.18,
    "crowding_inverse": 0.16,
    "valuation_nonlinearity": 0.18,
    "ecosystem_centrality": 0.18,
    "downstream_valuation_gap": 0.16,
    "microcap_rerating_potential": 0.14,
}


def _load_screening_module():
    services_root = Path(__file__).resolve().parents[1] / "backend" / "app" / "services"

    app_pkg = types.ModuleType("app")
    app_pkg.__path__ = []
    services_pkg = types.ModuleType("app.services")
    services_pkg.__path__ = [str(services_root)]
    sys.modules["app"] = app_pkg
    sys.modules["app.services"] = services_pkg

    for name in ["chokepoint_scoring", "mispricing_screening"]:
        full_name = f"app.services.{name}"
        if full_name in sys.modules:
            continue
        spec = spec_from_file_location(full_name, services_root / f"{name}.py")
        module = module_from_spec(spec)
        sys.modules[full_name] = module
        assert spec.loader is not None
        spec.loader.exec_module(module)

    return sys.modules["app.services.mispricing_screening"]


def _load_rows(path: Path) -> List[Dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("rows"), list):
        return payload["rows"]
    raise ValueError("input must be a list or object with a 'rows' list")


def _validate_weights(weights: Dict[str, float]) -> Dict[str, float]:
    total = sum(float(value) for value in weights.values())
    if total <= 0:
        raise ValueError("weights must sum to a positive number")
    return {key: float(value) / total for key, value in weights.items()}


def _clamp_signal(value: float) -> float:
    return max(0.0, min(5.0, float(value)))


@dataclass
class StockExpressionSignals:
    market_accessibility: float
    implementation_simplicity: float
    balance_sheet_resilience: float
    dilution_risk_inverse: float
    thesis_linearity: float
    duration_tolerance: float
    listing_quality: float

    def normalized(self) -> Dict[str, float]:
        return {key: _clamp_signal(value) for key, value in asdict(self).items()}


@dataclass
class LeapsBiasSignals:
    iv_cheapness: float
    surface_staleness: float
    pre_expiration_repricing_potential: float
    stock_vs_call_convexity_advantage: float
    long_dated_liquidity_quality: float

    def normalized(self) -> Dict[str, float]:
        return {key: _clamp_signal(value) for key, value in asdict(self).items()}


def _score_stock_fit(signals: StockExpressionSignals) -> Dict[str, Any]:
    normalized_weights = _validate_weights(DEFAULT_STOCK_FIT_WEIGHTS)
    signal_map = signals.normalized()
    weighted = {
        key: signal_map[key] * normalized_weights[key]
        for key in normalized_weights
    }
    score = (sum(weighted.values()) / 5.0) * 100.0
    strongest = sorted(weighted.items(), key=lambda item: item[1], reverse=True)[:3]
    weakest = list(reversed(sorted(weighted.items(), key=lambda item: item[1])[:2]))
    return {
        "score_0_to_100": round(score, 2),
        "weighted_signals": {key: round(value, 4) for key, value in weighted.items()},
        "strongest_drivers": [(key, round(value, 4)) for key, value in strongest],
        "weakest_drivers": [(key, round(value, 4)) for key, value in weakest],
    }


def _score_leaps_bias(signals: LeapsBiasSignals) -> Dict[str, Any]:
    normalized_weights = _validate_weights(DEFAULT_LEAPS_BIAS_WEIGHTS)
    signal_map = signals.normalized()
    weighted = {
        key: signal_map[key] * normalized_weights[key]
        for key in normalized_weights
    }
    score = (sum(weighted.values()) / 5.0) * 100.0
    strongest = sorted(weighted.items(), key=lambda item: item[1], reverse=True)[:3]
    weakest = list(reversed(sorted(weighted.items(), key=lambda item: item[1])[:2]))
    return {
        "score_0_to_100": round(score, 2),
        "weighted_signals": {key: round(value, 4) for key, value in weighted.items()},
        "strongest_drivers": [(key, round(value, 4)) for key, value in strongest],
        "weakest_drivers": [(key, round(value, 4)) for key, value in weakest],
    }


def _choose_expression(
    mispricing_score: float,
    options_fit_score: float,
    stock_fit_score: float,
    leaps_bias_score: float,
) -> str:
    if mispricing_score < 60:
        return "reject"
    if (
        mispricing_score >= 80
        and options_fit_score >= 68
        and leaps_bias_score >= 78
    ):
        return "leaps_call"
    if (
        options_fit_score >= 62
        and leaps_bias_score >= 68
        and ((options_fit_score * 0.45) + (leaps_bias_score * 0.55)) >= stock_fit_score - 1
    ):
        return "leaps_call"
    if stock_fit_score >= 60 and stock_fit_score >= options_fit_score + 10:
        return "shares"
    if options_fit_score >= 58 and leaps_bias_score >= 60 and options_fit_score >= stock_fit_score + 6:
        return "leaps_call"
    if stock_fit_score >= 60 and options_fit_score < 60:
        return "shares"
    if options_fit_score >= 58 and leaps_bias_score >= 60 and stock_fit_score < 60:
        return "leaps_call"
    if stock_fit_score >= 60 and options_fit_score >= 58:
        if leaps_bias_score >= 70 and options_fit_score >= stock_fit_score - 4:
            return "leaps_call"
        return "shares"
    return "reject"


def _asymmetry_bonus(mispricing_signal_map: Dict[str, float], asymmetry_signal_map: Dict[str, float] | None = None) -> float:
    normalized_weights = _validate_weights(ASYMMETRY_SIGNAL_WEIGHTS)
    blended_signals = {
        "hiddenness": _clamp_signal(mispricing_signal_map.get("hiddenness", 0.0)),
        "crowding_inverse": _clamp_signal(mispricing_signal_map.get("crowding_inverse", 0.0)),
        "valuation_nonlinearity": _clamp_signal(mispricing_signal_map.get("valuation_nonlinearity", 0.0)),
        "ecosystem_centrality": _clamp_signal((asymmetry_signal_map or {}).get("ecosystem_centrality", 0.0)),
        "downstream_valuation_gap": _clamp_signal((asymmetry_signal_map or {}).get("downstream_valuation_gap", 0.0)),
        "microcap_rerating_potential": _clamp_signal((asymmetry_signal_map or {}).get("microcap_rerating_potential", 0.0)),
    }
    weighted_total = sum(blended_signals[key] * normalized_weights[key] for key in normalized_weights)
    return round((weighted_total / 5.0) * 12.0, 2)


def _pick_score(
    mispricing_score: float,
    stock_fit_score: float,
    options_fit_score: float,
    leaps_bias_score: float,
    expression: str,
    asymmetry_bonus: float,
) -> float:
    expression_bonus = {
        "shares": 2.0,
        "leaps_call": 3.0,
        "reject": -8.0,
    }[expression]
    expression_strength = max(stock_fit_score, (options_fit_score * 0.55) + (leaps_bias_score * 0.45))
    return round((mispricing_score * 0.54) + (expression_strength * 0.26) + asymmetry_bonus + expression_bonus, 2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate ranked picks from a structured scan batch")
    parser.add_argument("input_json", help="Path to scan batch JSON")
    parser.add_argument("--output-json", required=True, help="Where to write ranked picks JSON")
    args = parser.parse_args()

    module = _load_screening_module()
    aggressive_mispricing_weights = getattr(module, "AGGRESSIVE_MISPRICING_WEIGHTS", None)
    rows = _load_rows(Path(args.input_json))

    ranked = []
    for row in rows:
        candidate = module.MispricingCandidate(
            name=row["name"],
            thesis=row["thesis"],
            underlying=row["underlying"],
            mispricing_type=row["mispricing_type"],
            posture="candidate_generation",
            preferred_expression="undecided",
            time_horizon=row["time_horizon"],
            mispricing_signals=module.MispricingSignals(**row["mispricing_signals"]),
            options_expression_signals=module.OptionsExpressionSignals(
                **row["options_expression_signals"]
            ),
            linked_companies=row.get("linked_companies", []),
            catalysts=row.get("catalysts", []),
            invalidations=row.get("invalidations", []),
            structural_reference={
                "market_theme": row.get("market_theme"),
                "bottleneck_layer": row.get("bottleneck_layer"),
                "value_capture_layer": row.get("value_capture_layer"),
                "why_missed": row.get("why_missed", []),
            },
            notes=row.get("notes", []),
        )
        mispricing_scorecard = module.score_mispricing_candidate(
            candidate,
            mispricing_weights=aggressive_mispricing_weights,
        )
        stock_fit = _score_stock_fit(StockExpressionSignals(**row["stock_expression_signals"]))
        leaps_bias = _score_leaps_bias(
            LeapsBiasSignals(
                **row.get(
                    "leaps_bias_signals",
                    {
                        "iv_cheapness": 0.0,
                        "surface_staleness": 0.0,
                        "pre_expiration_repricing_potential": 0.0,
                        "stock_vs_call_convexity_advantage": 0.0,
                        "long_dated_liquidity_quality": 0.0,
                    },
                )
            )
        )
        mispricing_score = mispricing_scorecard.mispricing.score_0_to_100
        options_fit_score = mispricing_scorecard.options_fit.score_0_to_100
        stock_fit_score = stock_fit["score_0_to_100"]
        leaps_bias_score = leaps_bias["score_0_to_100"]
        final_expression = _choose_expression(
            mispricing_score,
            options_fit_score,
            stock_fit_score,
            leaps_bias_score,
        )
        asymmetry_bonus = _asymmetry_bonus(
            row["mispricing_signals"],
            row.get("asymmetry_signals"),
        )
        ranked.append(
            {
                "name": row["name"],
                "underlying": row["underlying"],
                "market_theme": row.get("market_theme"),
                "promotion_status": row.get("promotion_status"),
                "promotion_score_0_to_100": row.get("promotion_score_0_to_100"),
                "thesis": row["thesis"],
                "bottleneck_layer": row.get("bottleneck_layer"),
                "value_capture_layer": row.get("value_capture_layer"),
                "why_missed": row.get("why_missed", []),
                "catalysts": row.get("catalysts", []),
                "invalidations": row.get("invalidations", []),
                "asymmetry_signals": row.get("asymmetry_signals", {}),
                "mispricing": mispricing_scorecard.mispricing.to_dict(),
                "options_fit": mispricing_scorecard.options_fit.to_dict(),
                "leaps_bias": leaps_bias,
                "stock_fit": stock_fit,
                "final_expression": final_expression,
                "asymmetry_bonus": asymmetry_bonus,
                "pick_score": _pick_score(
                    mispricing_score,
                    stock_fit_score,
                    options_fit_score,
                    leaps_bias_score,
                    final_expression,
                    asymmetry_bonus,
                ),
            }
        )

    ranked.sort(key=lambda row: row["pick_score"], reverse=True)
    output = {
        "method": "market scan -> mispricing score -> stock-vs-LEAPS choice -> ranked picks",
        "rows": ranked,
    }
    out_path = Path(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

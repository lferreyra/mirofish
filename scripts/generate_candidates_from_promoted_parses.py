#!/usr/bin/env python3
"""
Generate pick-pipeline candidate rows from graduated structural parses.

Only promoted parses are eligible:
- watchlist_candidate
- pick_candidate
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


STATUS_ORDER = {
    "exploratory_only": 0,
    "watchlist_candidate": 1,
    "pick_candidate": 2,
}


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_rows(payload: Dict[str, Any] | List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("rows"), list):
        return payload["rows"]
    raise ValueError("manifest must be a list or an object with a 'rows' list")


def _status_allowed(status: str, minimum_status: str) -> bool:
    return STATUS_ORDER.get(status, -1) >= STATUS_ORDER[minimum_status]


def _find_entities(structural_parse: Dict[str, Any], entity_type: str) -> List[Dict[str, Any]]:
    return [
        entity for entity in structural_parse.get("entities", [])
        if entity.get("entity_type") == entity_type
    ]


def _find_relationships(structural_parse: Dict[str, Any], relationship_type: str) -> List[Dict[str, Any]]:
    return [
        relationship for relationship in structural_parse.get("relationships", [])
        if relationship.get("relationship_type") == relationship_type
    ]


def _entity_map(structural_parse: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        entity["entity_id"]: entity for entity in structural_parse.get("entities", [])
    }


def _first_expression(structural_parse: Dict[str, Any]) -> Dict[str, Any] | None:
    expressions = _find_entities(structural_parse, "ExpressionCandidate")
    if not expressions:
        return None
    expressions.sort(key=lambda entity: entity.get("canonical_name", ""))
    return expressions[0]


def _extract_underlying(expression: Dict[str, Any] | None, structural_parse: Dict[str, Any]) -> str:
    if expression:
        name = expression.get("canonical_name", "")
        if ":" in name:
            maybe = name.split(":", 1)[1].strip()
            if maybe:
                return maybe
    companies = _find_entities(structural_parse, "PublicCompany")
    if companies:
        companies.sort(key=lambda entity: entity.get("canonical_name", ""))
        return companies[0].get("canonical_name", "")
    return "UNKNOWN"


def _choose_theme(structural_parse: Dict[str, Any], expression: Dict[str, Any] | None) -> str:
    entities = _entity_map(structural_parse)
    if expression:
        for relationship in _find_relationships(structural_parse, "CANDIDATE_EXPRESSION_FOR"):
            if relationship.get("source_entity_id") == expression.get("entity_id"):
                target = entities.get(relationship.get("target_entity_id"))
                if target and target.get("entity_type") in {"Theme", "BottleneckLayer", "ProcessLayer"}:
                    return target.get("canonical_name", "")
    themes = _find_entities(structural_parse, "Theme")
    if themes:
        return themes[0].get("canonical_name", "")
    return ""


def _choose_bottleneck_layer(structural_parse: Dict[str, Any], underlying: str) -> str:
    entities = _entity_map(structural_parse)
    process_layers = _find_entities(structural_parse, "ProcessLayer")
    if not process_layers:
        return ""

    scores: Dict[str, int] = {entity["entity_id"]: 0 for entity in process_layers}
    for relationship in structural_parse.get("relationships", []):
        rel_type = relationship.get("relationship_type")
        source_id = relationship.get("source_entity_id")
        target_id = relationship.get("target_entity_id")
        source = entities.get(source_id, {})
        target = entities.get(target_id, {})

        if source_id in scores and rel_type in {"AFFECTED_BY_EVENT", "SUPPLIED_BY", "EXPANDS_CAPACITY_FOR"}:
            scores[source_id] += 2
        if target_id in scores and rel_type in {"DEPENDS_ON", "CANDIDATE_EXPRESSION_FOR"}:
            scores[target_id] += 2
        if source.get("entity_type") == "ProcessLayer" and target.get("entity_type") == "PublicCompany":
            if target.get("canonical_name") == underlying:
                scores[source_id] += 4
        if source.get("entity_type") == "Component" and target.get("entity_type") == "ProcessLayer":
            scores[target_id] += 1

    best_id = max(scores, key=lambda entity_id: scores[entity_id])
    return entities[best_id].get("canonical_name", "")


def _choose_value_capture_layer(structural_parse: Dict[str, Any], underlying: str) -> str:
    entities = _entity_map(structural_parse)
    for relationship in _find_relationships(structural_parse, "SUPPLIED_BY"):
        target = entities.get(relationship.get("target_entity_id"), {})
        source = entities.get(relationship.get("source_entity_id"), {})
        if target.get("canonical_name") == underlying and source.get("entity_type") == "ProcessLayer":
            return source.get("canonical_name", "")
    return _choose_bottleneck_layer(structural_parse, underlying)


def _choose_catalysts(structural_parse: Dict[str, Any], expression: Dict[str, Any] | None) -> List[str]:
    entities = _entity_map(structural_parse)
    catalysts: List[str] = []
    if expression:
        for relationship in _find_relationships(structural_parse, "REPRICES_VIA"):
            if relationship.get("source_entity_id") == expression.get("entity_id"):
                target = entities.get(relationship.get("target_entity_id"))
                if target:
                    catalysts.append(target.get("canonical_name", ""))
    if not catalysts:
        for event in _find_entities(structural_parse, "Event"):
            catalysts.append(event.get("canonical_name", ""))
    deduped = []
    for catalyst in catalysts:
        if catalyst and catalyst not in deduped:
            deduped.append(catalyst)
    return deduped[:5]


def _choose_invalidations(graduation: Dict[str, Any], structural_parse: Dict[str, Any]) -> List[str]:
    inferences = structural_parse.get("inferences", [])
    if inferences:
        falsifiers = inferences[0].get("falsifiers", [])
        if falsifiers:
            return falsifiers[:5]
    return [
        "independent corroboration fails to improve",
        "market-miss thesis loses structural support",
    ]


def _market_miss_statement(structural_parse: Dict[str, Any]) -> str:
    inferences = structural_parse.get("inferences", [])
    if inferences:
        return inferences[0].get("statement", "")
    claims = structural_parse.get("claims", [])
    if claims:
        return claims[0].get("claim_text", "")
    return ""


def _why_missed_from_statement(statement: str, graduation_status: str) -> List[str]:
    reasons = ["market framing appears stale relative to the structural role"]
    lowered = statement.lower()
    if "upstream" in lowered:
        reasons.append("upstream supplier role is not obvious from headline narratives")
    if "mining story" in lowered:
        reasons.append("the market may still anchor on an outdated business description")
    if graduation_status == "watchlist_candidate":
        reasons.append("the thesis still needs more independent corroboration")
    return reasons


def _rescale(score: float) -> float:
    return round(max(0.5, min(5.0, score / 20.0)), 1)


def _build_signal_blocks(
    graduation: Dict[str, Any], structural_parse: Dict[str, Any]
) -> Dict[str, Dict[str, float]]:
    source_mix = graduation["dimensions"]["source_mix"]["score_0_to_100"]
    structure_quality = graduation["dimensions"]["structure_quality"]["score_0_to_100"]
    market_miss_quality = graduation["dimensions"]["market_miss_quality"]["score_0_to_100"]
    expression_readiness = graduation["dimensions"]["expression_readiness"]["score_0_to_100"]

    market_miss_detail = graduation["dimensions"]["market_miss_quality"]["detail"]
    expression_names = graduation["dimensions"]["expression_readiness"]["detail"].get("expression_names", [])
    expression_name = expression_names[0] if expression_names else ""

    is_shares = expression_name.lower().startswith("shares:")
    source_classes = graduation["dimensions"]["source_mix"]["detail"].get("source_classes", [])
    company_heavy = source_classes and all(source_class == "company_release" for source_class in source_classes)

    mispricing_signals = {
        "hiddenness": _rescale((market_miss_quality + (100 - source_mix)) / 2),
        "recognition_gap": _rescale(market_miss_quality),
        "catalyst_clarity": _rescale(expression_readiness),
        "propagation_asymmetry": _rescale(structure_quality),
        "duration_mismatch": _rescale((structure_quality + market_miss_quality) / 2),
        "evidence_quality": _rescale(source_mix),
        "crowding_inverse": _rescale(70 if company_heavy else 82),
        "valuation_nonlinearity": _rescale(85 if graduation["graduation_status"] != "exploratory_only" else 60),
    }

    asymmetry_signals = {
        "ecosystem_centrality": _rescale(structure_quality),
        "downstream_valuation_gap": _rescale(market_miss_quality),
        "microcap_rerating_potential": _rescale(80 if company_heavy else 65),
    }

    options_expression_signals = {
        "convexity_need": _rescale(55 if is_shares else 70),
        "tenor_alignment": _rescale(expression_readiness),
        "vol_expansion_potential": _rescale(50 if is_shares else 75),
        "downside_definedness": _rescale(45),
        "liquidity_path": _rescale(25 if is_shares else 60),
        "implementation_simplicity": _rescale(85),
        "catalyst_timing_specificity": _rescale(expression_readiness),
    }

    stock_expression_signals = {
        "market_accessibility": _rescale(85),
        "implementation_simplicity": _rescale(85),
        "balance_sheet_resilience": _rescale(source_mix if not company_heavy else source_mix - 10),
        "dilution_risk_inverse": _rescale(source_mix if not company_heavy else source_mix - 15),
        "thesis_linearity": _rescale(structure_quality),
        "duration_tolerance": _rescale(market_miss_quality),
        "listing_quality": _rescale(80),
    }

    leaps_bias_signals = {
        "iv_cheapness": _rescale(20 if is_shares else 75),
        "surface_staleness": _rescale(20 if is_shares else 70),
        "pre_expiration_repricing_potential": _rescale(45 if is_shares else 75),
        "stock_vs_call_convexity_advantage": _rescale(15 if is_shares else 70),
        "long_dated_liquidity_quality": _rescale(15 if is_shares else 70),
    }

    return {
        "mispricing_signals": mispricing_signals,
        "asymmetry_signals": asymmetry_signals,
        "options_expression_signals": options_expression_signals,
        "stock_expression_signals": stock_expression_signals,
        "leaps_bias_signals": leaps_bias_signals,
    }


def _candidate_name(underlying: str, theme: str, graduation_status: str) -> str:
    suffix = {
        "pick_candidate": "promoted structural pick",
        "watchlist_candidate": "structural watchlist",
    }.get(graduation_status, "structural thesis")
    return f"{underlying} {suffix} on {theme}"


def build_candidate_row(
    source_bundle: Dict[str, Any],
    structural_parse: Dict[str, Any],
    graduation: Dict[str, Any],
) -> Dict[str, Any]:
    expression = _first_expression(structural_parse)
    underlying = _extract_underlying(expression, structural_parse)
    theme = _choose_theme(structural_parse, expression)
    bottleneck_layer = _choose_bottleneck_layer(structural_parse, underlying)
    value_capture_layer = _choose_value_capture_layer(structural_parse, underlying)
    thesis = _market_miss_statement(structural_parse)
    catalysts = _choose_catalysts(structural_parse, expression)
    invalidations = _choose_invalidations(graduation, structural_parse)
    linked_companies = [
        entity.get("canonical_name")
        for entity in _find_entities(structural_parse, "PublicCompany")
    ]
    signal_blocks = _build_signal_blocks(graduation, structural_parse)
    time_horizon = "12-24m"
    preferred_expression = expression.get("attributes", {}).get("expression_type") if expression else None
    if preferred_expression == "shares":
        mispricing_type = "structural_information_arbitrage"
    else:
        mispricing_type = "hidden_bottleneck"

    return {
        "name": _candidate_name(underlying, theme or bottleneck_layer or "theme", graduation["graduation_status"]),
        "market_theme": theme,
        "thesis": thesis,
        "underlying": underlying,
        "mispricing_type": mispricing_type,
        "time_horizon": time_horizon,
        "linked_companies": linked_companies,
        "bottleneck_layer": bottleneck_layer,
        "value_capture_layer": value_capture_layer,
        "why_missed": _why_missed_from_statement(thesis, graduation["graduation_status"]),
        "catalysts": catalysts,
        "invalidations": invalidations,
        "promotion_status": graduation["graduation_status"],
        "promotion_score_0_to_100": graduation["weighted_score_0_to_100"],
        **signal_blocks,
        "notes": [
            f"Auto-generated from promoted structural parse.",
            f"Promotion status: {graduation['graduation_status']}.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="JSON list/object describing parse bundles")
    parser.add_argument("--output-json", required=True, type=Path)
    parser.add_argument(
        "--min-status",
        choices=sorted(STATUS_ORDER, key=STATUS_ORDER.get),
        default="watchlist_candidate",
        help="Minimum graduation status allowed into output rows.",
    )
    args = parser.parse_args()

    manifest = _normalize_rows(_load_json(args.manifest))
    rows: List[Dict[str, Any]] = []

    for item in manifest:
        source_bundle = _load_json(Path(item["source_bundle"]))
        structural_parse = _load_json(Path(item["structural_parse"]))
        graduation = _load_json(Path(item["graduation"]))
        if not _status_allowed(graduation["graduation_status"], args.min_status):
            continue
        rows.append(build_candidate_row(source_bundle, structural_parse, graduation))

    output = {
        "method": "promoted structural parses -> auto-generated pick candidates",
        "minimum_status": args.min_status,
        "rows": rows,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""
Chokepoint scoring utilities for bottleneck-focused research.

This module is intentionally independent from the simulation stack so it can be
used by future research workflows, scripts, or API endpoints.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Dict, List, Tuple


DEFAULT_SEVERITY_WEIGHTS: Dict[str, float] = {
    "supplier_concentration": 0.22,
    "qualification_friction": 0.16,
    "capacity_lead_time": 0.16,
    "geopolitical_exposure": 0.14,
    "demand_acceleration": 0.14,
    "substitutability_inverse": 0.12,
    "pricing_power_evidence": 0.06,
}

DEFAULT_VALUE_CAPTURE_WEIGHTS: Dict[str, float] = {
    "pricing_power_realization": 0.22,
    "listed_vehicle_purity": 0.18,
    "margin_leverage": 0.16,
    "balance_sheet_capacity": 0.14,
    "scarcity_duration": 0.14,
    "competitive_retention": 0.10,
    "state_support_independence": 0.06,
}


def _clamp_signal(value: float) -> float:
    """Clamp a signal to the expected 0-5 range."""
    return max(0.0, min(5.0, float(value)))


def validate_weights(weights: Dict[str, float]) -> Dict[str, float]:
    """Validate and normalize signal weights."""
    if not weights:
        raise ValueError("weights must not be empty")

    total = sum(float(v) for v in weights.values())
    if total <= 0:
        raise ValueError("weights must sum to a positive number")

    return {key: float(value) / total for key, value in weights.items()}


@dataclass
class ChokepointSeveritySignals:
    """
    Severity signals for a bottleneck candidate.

    Each field should be scored from 0 to 5:
    0 = negligible / absent
    5 = extreme / highly material
    """

    supplier_concentration: float
    qualification_friction: float
    capacity_lead_time: float
    geopolitical_exposure: float
    demand_acceleration: float
    substitutability_inverse: float
    pricing_power_evidence: float = 0.0

    def normalized(self) -> Dict[str, float]:
        """Return clamped signal values."""
        return {
            key: _clamp_signal(value)
            for key, value in asdict(self).items()
        }


@dataclass
class ValueCaptureSignals:
    """
    Value-capture signals for a bottleneck candidate.

    Each field should be scored from 0 to 5:
    0 = weak / poor expression quality
    5 = strong / highly investable expression quality
    """

    pricing_power_realization: float
    listed_vehicle_purity: float
    margin_leverage: float
    balance_sheet_capacity: float
    scarcity_duration: float
    competitive_retention: float
    state_support_independence: float = 0.0

    def normalized(self) -> Dict[str, float]:
        """Return clamped signal values."""
        return {
            key: _clamp_signal(value)
            for key, value in asdict(self).items()
        }


@dataclass
class ChokepointCandidate:
    """Structured bottleneck candidate."""

    name: str
    layer: str
    description: str
    severity_signals: ChokepointSeveritySignals
    value_capture_signals: ValueCaptureSignals
    public_companies: List[str] = field(default_factory=list)
    source_urls: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        """Serialize the candidate."""
        return {
            "name": self.name,
            "layer": self.layer,
            "description": self.description,
            "severity_signals": self.severity_signals.normalized(),
            "value_capture_signals": self.value_capture_signals.normalized(),
            "public_companies": list(self.public_companies),
            "source_urls": list(self.source_urls),
            "notes": list(self.notes),
        }


@dataclass
class ScoreBreakdown:
    """Single score breakdown result."""

    candidate_name: str
    score_type: str
    score_0_to_100: float
    band: str
    weighted_signals: Dict[str, float]
    strongest_drivers: List[Tuple[str, float]]
    weakest_drivers: List[Tuple[str, float]]
    explanation: str

    def to_dict(self) -> Dict[str, object]:
        """Serialize the scoring result."""
        return {
            "candidate_name": self.candidate_name,
            "score_type": self.score_type,
            "score_0_to_100": round(self.score_0_to_100, 2),
            "band": self.band,
            "weighted_signals": {
                key: round(value, 4) for key, value in self.weighted_signals.items()
            },
            "strongest_drivers": [
                (key, round(value, 4)) for key, value in self.strongest_drivers
            ],
            "weakest_drivers": [
                (key, round(value, 4)) for key, value in self.weakest_drivers
            ],
            "explanation": self.explanation,
        }


@dataclass
class ChokepointScorecard:
    """Full candidate scorecard with separate severity and value-capture scores."""

    candidate_name: str
    severity: ScoreBreakdown
    value_capture: ScoreBreakdown

    def to_dict(self) -> Dict[str, object]:
        return {
            "candidate_name": self.candidate_name,
            "severity": self.severity.to_dict(),
            "value_capture": self.value_capture.to_dict(),
        }


def classify_score(score_0_to_100: float) -> str:
    """Map a numeric score into a qualitative band."""
    if score_0_to_100 >= 80:
        return "critical"
    if score_0_to_100 >= 65:
        return "high"
    if score_0_to_100 >= 45:
        return "moderate"
    if score_0_to_100 >= 25:
        return "emerging"
    return "low"


def score_candidate_severity(
    candidate: ChokepointCandidate,
    weights: Dict[str, float] | None = None,
) -> ScoreBreakdown:
    """Compute the weighted chokepoint-severity score."""
    normalized_weights = validate_weights(weights or DEFAULT_SEVERITY_WEIGHTS)
    signals = candidate.severity_signals.normalized()

    missing = set(normalized_weights) - set(signals)
    if missing:
        raise ValueError(f"missing signals for weights: {sorted(missing)}")

    weighted_signals = {
        key: signals[key] * normalized_weights[key]
        for key in normalized_weights
    }
    weighted_total = sum(weighted_signals.values())
    score_0_to_100 = (weighted_total / 5.0) * 100.0
    band = classify_score(score_0_to_100)

    ordered = sorted(
        weighted_signals.items(),
        key=lambda item: item[1],
        reverse=True,
    )
    strongest = ordered[:3]
    weakest = list(reversed(ordered[-2:]))

    explanation = _build_explanation(
        candidate=candidate,
        score_type="severity",
        band=band,
        score_0_to_100=score_0_to_100,
        strongest=strongest,
        weakest=weakest,
    )

    return ScoreBreakdown(
        candidate_name=candidate.name,
        score_type="severity",
        score_0_to_100=score_0_to_100,
        band=band,
        weighted_signals=weighted_signals,
        strongest_drivers=strongest,
        weakest_drivers=weakest,
        explanation=explanation,
    )


def score_candidate_value_capture(
    candidate: ChokepointCandidate,
    weights: Dict[str, float] | None = None,
) -> ScoreBreakdown:
    """Compute the weighted value-capture score."""
    normalized_weights = validate_weights(weights or DEFAULT_VALUE_CAPTURE_WEIGHTS)
    signals = candidate.value_capture_signals.normalized()

    missing = set(normalized_weights) - set(signals)
    if missing:
        raise ValueError(f"missing signals for weights: {sorted(missing)}")

    weighted_signals = {
        key: signals[key] * normalized_weights[key]
        for key in normalized_weights
    }
    weighted_total = sum(weighted_signals.values())
    score_0_to_100 = (weighted_total / 5.0) * 100.0
    band = classify_score(score_0_to_100)

    ordered = sorted(
        weighted_signals.items(),
        key=lambda item: item[1],
        reverse=True,
    )
    strongest = ordered[:3]
    weakest = list(reversed(ordered[-2:]))

    explanation = _build_explanation(
        candidate=candidate,
        score_type="value_capture",
        band=band,
        score_0_to_100=score_0_to_100,
        strongest=strongest,
        weakest=weakest,
    )

    return ScoreBreakdown(
        candidate_name=candidate.name,
        score_type="value_capture",
        score_0_to_100=score_0_to_100,
        band=band,
        weighted_signals=weighted_signals,
        strongest_drivers=strongest,
        weakest_drivers=weakest,
        explanation=explanation,
    )


def score_candidate(
    candidate: ChokepointCandidate,
    severity_weights: Dict[str, float] | None = None,
    value_capture_weights: Dict[str, float] | None = None,
) -> ChokepointScorecard:
    """Compute both severity and value-capture scores for a candidate."""
    severity = score_candidate_severity(candidate, severity_weights)
    value_capture = score_candidate_value_capture(candidate, value_capture_weights)
    return ChokepointScorecard(
        candidate_name=candidate.name,
        severity=severity,
        value_capture=value_capture,
    )


def _pretty_signal_name(signal_name: str) -> str:
    return signal_name.replace("_", " ")


def _build_explanation(
    candidate: ChokepointCandidate,
    score_type: str,
    band: str,
    score_0_to_100: float,
    strongest: List[Tuple[str, float]],
    weakest: List[Tuple[str, float]],
) -> str:
    strongest_text = ", ".join(_pretty_signal_name(name) for name, _ in strongest)
    weakest_text = ", ".join(_pretty_signal_name(name) for name, _ in weakest)

    if score_type == "severity":
        return (
            f"{candidate.name} scores {score_0_to_100:.1f}/100 ({band}) on "
            f"chokepoint severity. The strongest weighted drivers are "
            f"{strongest_text}. The least supportive signals are {weakest_text}. "
            f"This score should be treated as a structural ranking aid, not as a "
            f"trading decision on its own."
        )

    return (
        f"{candidate.name} scores {score_0_to_100:.1f}/100 ({band}) on "
        f"value-capture potential. The strongest weighted drivers are "
        f"{strongest_text}. The least supportive signals are {weakest_text}. "
        f"This score is intended to complement severity, not replace it."
    )

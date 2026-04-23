"""
Scoring primitives — pure functions over a `Verdict` and a `Truth`.

Three components, each in [0, 1]:
  directional_accuracy : 1 if signs match (incl. both "neutral"), else 0
  magnitude_error      : |verdict.magnitude - truth.magnitude| clipped to [0,1]
  calibration          : 1 - |confidence - outcome|, where outcome is
                         1 if direction was right, 0 if wrong

Composite:
  score = 0.5 * directional + 0.3 * (1 - magnitude_error) + 0.2 * calibration

Weights live in `DEFAULT_WEIGHTS`; callers can pass their own. Any change
to the weights is a behavior change — bump DETERMINISTIC_VERSION.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


DEFAULT_WEIGHTS: dict[str, float] = {
    "directional": 0.5,
    "magnitude":   0.3,
    "calibration": 0.2,
}


_NEUTRAL_BAND = 0.15   # |valence| below this is considered neutral for direction


@dataclass
class Verdict:
    """What a simulation run *concluded* about the seed question."""
    direction: str       # "positive" | "negative" | "neutral"
    magnitude: float     # [0, 1], strength of the prediction
    confidence: float    # [0, 1], how confident the agent population is
    rationale: Optional[str] = None   # free-form human-readable summary
    # Raw signals — useful for the dashboard to show "what the sim actually saw"
    support_ratio: float = 0.0
    agent_count: int = 0

    def to_dict(self) -> dict:
        return {
            "direction": self.direction,
            "magnitude": self.magnitude,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "support_ratio": self.support_ratio,
            "agent_count": self.agent_count,
        }


@dataclass
class Truth:
    """Ground truth for a dataset case. Mirrors Verdict shape so the scorer
    can compare fields directly."""
    direction: str
    magnitude: float
    confidence: float = 1.0   # how strong is the historical signal
    notes: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "Truth":
        return cls(
            direction=str(data.get("direction", "neutral")).lower(),
            magnitude=float(data.get("magnitude", 0.0)),
            confidence=float(data.get("confidence", 1.0)),
            notes=data.get("notes"),
        )


@dataclass
class Score:
    """Full breakdown. `composite` is the number to rank runs by."""
    directional: float
    magnitude_error: float
    calibration: float
    composite: float
    weights: dict = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))

    def to_dict(self) -> dict:
        return {
            "directional": self.directional,
            "magnitude_error": self.magnitude_error,
            "calibration": self.calibration,
            "composite": self.composite,
            "weights": self.weights,
        }


# ---- public API -----------------------------------------------------------

def directional_accuracy(v: Verdict, t: Truth) -> float:
    """1.0 if signs agree (treating near-zero as neutral), else 0.0."""
    return 1.0 if _direction_sign(v.direction) == _direction_sign(t.direction) else 0.0


def magnitude_error(v: Verdict, t: Truth) -> float:
    """Absolute gap, clipped to [0, 1]."""
    gap = abs(_clamp01(v.magnitude) - _clamp01(t.magnitude))
    return _clamp01(gap)


def calibration(v: Verdict, t: Truth) -> float:
    """1 if confidence matched the outcome, 0 if wildly miscalibrated.

    outcome = 1 when direction was right, 0 when wrong.
    calibration = 1 - |confidence - outcome|.
    """
    outcome = directional_accuracy(v, t)
    return _clamp01(1.0 - abs(_clamp01(v.confidence) - outcome))


def score_verdict(
    verdict: Verdict,
    truth: Truth,
    *,
    weights: Optional[dict] = None,
) -> Score:
    """Combine the three components into a single composite score."""
    w = dict(DEFAULT_WEIGHTS)
    if weights:
        w.update({k: float(v) for k, v in weights.items()})
    dir_ = directional_accuracy(verdict, truth)
    mag = magnitude_error(verdict, truth)
    cal = calibration(verdict, truth)
    composite = (
        w["directional"] * dir_
        + w["magnitude"] * (1.0 - mag)
        + w["calibration"] * cal
    )
    return Score(
        directional=dir_,
        magnitude_error=mag,
        calibration=cal,
        composite=_clamp01(composite),
        weights=w,
    )


# ---- helpers --------------------------------------------------------------

def _direction_sign(label: str) -> int:
    s = (label or "").strip().lower()
    if s in ("positive", "pos", "up", "yes", "support"):
        return +1
    if s in ("negative", "neg", "down", "no", "oppose"):
        return -1
    return 0


def _clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return float(x)

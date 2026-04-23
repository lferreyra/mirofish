"""
Extract a `Verdict` from a completed simulation's public timeline.

Two strategies:
  * `verdict_from_public_timeline` — purely numeric; aggregates the valence
    of public posts, weights by author credibility, produces a signed score
    that becomes the Verdict. This is what deterministic / mock runs use.
  * `verdict_from_report` — parses a ReportAgent JSON payload when it's
    available. Returns None when the payload can't be parsed; callers then
    fall back to the numeric method.

Why two: the ReportAgent can hallucinate under temp=0 with a weak model,
and CI needs a scoring path that is fully deterministic over the pipeline's
internal state. The numeric method gives us that floor.
"""

from __future__ import annotations

import json
import math
import re
from typing import Dict, List, Optional

from app.memory.base import MemoryRecord, Namespace
from app.memory.manager import MemoryManager
from app.personas.schema import StructuredPersona
from .scoring import Verdict


def verdict_from_public_timeline(
    manager: MemoryManager,
    *,
    personas: Optional[Dict[int, StructuredPersona]] = None,
    now_ts: Optional[float] = None,
) -> Verdict:
    """Aggregate public_timeline posts into a signed support_ratio, then
    map that to (direction, magnitude, confidence).

    Per-post contribution:
        weight = author.credibility   (fallback 0.5 when unknown)
        sign   = +1 if post looks supportive, -1 if opposing, 0 if neutral

    Support is inferred heuristically from the post content for the mock
    path — the real simulation attaches an explicit `valence` in the
    observation metadata (see `pipeline.py`).
    """
    timeline_ns = Namespace.public_timeline(manager.simulation_id)
    # Pull every public post; no top_k limit here — the dataset is tiny.
    records: List[MemoryRecord] = manager._backend.summarize_window(  # noqa: SLF001
        namespace=timeline_ns, top_k=10_000,
    )
    if not records:
        return Verdict(direction="neutral", magnitude=0.0, confidence=0.0)

    personas = personas or {}
    weighted_sum = 0.0
    total_weight = 0.0
    unique_agents: set[int] = set()
    for rec in records:
        valence = _post_valence(rec)
        author_id = getattr(rec, "author_id", None)
        unique_agents.add(author_id if author_id is not None else -1)
        credibility = 0.5
        if author_id is not None and author_id in personas:
            credibility = personas[author_id].credibility
        weighted_sum += valence * credibility
        total_weight += credibility

    support_ratio = weighted_sum / total_weight if total_weight > 0 else 0.0
    direction = (
        "positive" if support_ratio > 0.15
        else "negative" if support_ratio < -0.15
        else "neutral"
    )
    magnitude = min(1.0, abs(support_ratio))
    # Confidence scales with sample size + consensus strength. A 3-post
    # simulation is low-confidence even if all 3 agree.
    consensus = abs(support_ratio)
    sample_weight = 1.0 - math.exp(-len(records) / 20.0)
    confidence = min(1.0, consensus * sample_weight)

    return Verdict(
        direction=direction,
        magnitude=magnitude,
        confidence=confidence,
        support_ratio=support_ratio,
        agent_count=len(unique_agents),
    )


def verdict_from_report(report_payload: str) -> Optional[Verdict]:
    """Parse a ReportAgent JSON string into a Verdict, or return None if
    the payload doesn't look like our schema."""
    cleaned = re.sub(r"^```(?:json)?\s*", "", report_payload.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or "direction" not in data:
        return None
    return Verdict(
        direction=str(data.get("direction", "neutral")).lower(),
        magnitude=float(data.get("magnitude", 0.0)),
        confidence=float(data.get("confidence", 0.0)),
        rationale=data.get("rationale"),
    )


# ---- helpers --------------------------------------------------------------

_SUPPORT_TOKENS = {"support", "favor", "agree", "yes", "good", "positive", "pro",
                   "love", "great", "excited", "approve"}
_OPPOSE_TOKENS = {"oppose", "against", "disagree", "no", "bad", "negative", "con",
                  "hate", "terrible", "concerned", "reject"}


def _post_valence(record: MemoryRecord) -> float:
    """Return a signed valence in [-1, 1] for a post.

    1. If `metadata["valence"]` is present (set by the mock pipeline), use it.
    2. Otherwise, do a simple token-overlap classifier — good enough for the
       heuristic verdict path; a live simulation would embed valence via the
       structured persona's post instructions.
    """
    meta = getattr(record, "metadata", None) or {}
    if "valence" in meta:
        try:
            return _clamp(float(meta["valence"]), -1.0, 1.0)
        except (TypeError, ValueError):
            pass
    content = (record.content or "").lower()
    tokens = set(re.findall(r"[a-z]+", content))
    pos = len(tokens & _SUPPORT_TOKENS)
    neg = len(tokens & _OPPOSE_TOKENS)
    if pos == 0 and neg == 0:
        return 0.0
    return (pos - neg) / (pos + neg)


def _clamp(x: float, lo: float, hi: float) -> float:
    if x < lo:
        return lo
    if x > hi:
        return hi
    return x

"""
Deterministic relevance scoring for Federal Register documents.

Scores each document against a profile's thematic focus using positive and
negative keyword markers.  The scorer is pure-functional with no side effects
and no network calls.

Relevance classes:
  - directly_relevant: score >= 50
  - adjacent:          score >= 20
  - noise:             score < 20
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

# ---------------------------------------------------------------------------
# Default marker sets (used when a profile does not supply its own)
# ---------------------------------------------------------------------------

DEFAULT_POSITIVE_MARKERS: List[str] = [
    "critical mineral",
    "critical minerals",
    "rare earth",
    "processed critical mineral",
    "section 232",
    "stockpile",
    "entity list",
    "export administration regulations",
    "bureau of industry and security",
    "bis",
    "domestic processing",
    "refining",
    "separation",
    "mining",
    "smelting",
    "cobalt",
    "lithium",
    "neodymium",
    "gallium",
    "germanium",
    "titanium",
    "manganese",
    "tungsten",
    "semiconductor",
    "advanced computing",
    "export control",
    "industrial base",
    "supply chain",
    "national security",
]

DEFAULT_NEGATIVE_MARKERS: List[str] = [
    "marine mammal",
    "marine mammals",
    "wildlife",
    "endangered species",
    "threatened species",
    "species status",
    "consumer furnace",
    "consumer furnaces",
    "energy conservation standard",
    "incidental take",
    "fisheries",
    "fishery",
    "habitat",
    "biological opinion",
    "migratory bird",
    "critical habitat",
    "whale",
    "dolphin",
    "manatee",
    "sea turtle",
]

# ---------------------------------------------------------------------------
# Process-layer marker mapping
# ---------------------------------------------------------------------------

# Maps a process-layer name to keywords that must appear in the document text
# for that layer to be assigned.  If a layer is not listed here it is never
# auto-assigned (the caller must explicitly request it).

PROCESS_LAYER_MARKERS: Dict[str, List[str]] = {
    "Rare Earth Mining": ["rare earth", "mining", "ore", "mine"],
    "Rare Earth Separation": ["rare earth", "separation", "solvent extraction"],
    "Neodymium Processing": ["neodymium", "ndfeb", "magnet", "rare earth processing"],
    "Cobalt Refining": ["cobalt", "refining", "refinery", "battery material"],
    "Lithium Processing": ["lithium", "brine", "spodumene", "lithium processing"],
    "Wafer Fabrication": ["wafer", "fabrication", "fab", "foundry"],
    "Chip Design": ["chip design", "eda", "electronic design", "integrated circuit"],
    "EDA Tools": ["eda", "electronic design automation", "synopsys", "cadence"],
    "Semiconductor Equipment": ["semiconductor equipment", "lithography", "etching", "deposition"],
    "Advanced Packaging": ["advanced packaging", "chiplet", "interposer", "3d stacking"],
    "Servo Motor Manufacturing": ["servo", "motor", "actuator", "motion control"],
    "Precision Gear Production": ["precision gear", "gear production", "gearbox", "reducer"],
    "Industrial Robot Assembly": ["robot", "robotics", "industrial robot", "automation"],
}


def _build_searchable_text(document: Dict[str, Any]) -> str:
    """Concatenate all relevant text fields into a single lower-case string."""
    parts: List[str] = []
    for key in ("title", "abstract", "summary"):
        value = document.get(key)
        if value:
            parts.append(str(value))
    for excerpt in (document.get("excerpts") or []):
        if excerpt:
            # Strip HTML highlight spans from FR API excerpts
            parts.append(re.sub(r"<[^>]+>", " ", str(excerpt)))
    for topic in (document.get("topics") or []):
        if topic:
            parts.append(str(topic))
    return " ".join(parts).lower()


def _count_marker_hits(
    text: str,
    markers: List[str],
) -> Tuple[int, List[str]]:
    """Return (hit_count, matched_markers)."""
    hits: List[str] = []
    for marker in markers:
        if marker.lower() in text:
            hits.append(marker)
    return len(hits), hits


def score_document_relevance(
    document: Dict[str, Any],
    *,
    positive_markers: List[str] | None = None,
    negative_markers: List[str] | None = None,
) -> Dict[str, Any]:
    """Score a single Federal Register API result document.

    Returns::

        {
            "relevance_score": int,       # 0-100
            "relevance_class": str,       # directly_relevant | adjacent | noise
            "positive_markers": [str],
            "negative_markers": [str],
        }
    """
    pos_markers = positive_markers or DEFAULT_POSITIVE_MARKERS
    neg_markers = negative_markers or DEFAULT_NEGATIVE_MARKERS

    text = _build_searchable_text(document)

    pos_count, pos_hits = _count_marker_hits(text, pos_markers)
    neg_count, neg_hits = _count_marker_hits(text, neg_markers)

    # Raw score: each positive hit adds points, each negative hit subtracts.
    # Scale so that 3+ positive hits with 0 negatives ≈ 60-80 range.
    raw = (pos_count * 20) - (neg_count * 25)
    score = max(0, min(100, raw))

    if score >= 50:
        relevance_class = "directly_relevant"
    elif score >= 20:
        relevance_class = "adjacent"
    else:
        relevance_class = "noise"

    return {
        "relevance_score": score,
        "relevance_class": relevance_class,
        "positive_markers": pos_hits,
        "negative_markers": neg_hits,
    }


def match_process_layers(
    document: Dict[str, Any],
    candidate_layers: List[str],
) -> List[str]:
    """Return only those *candidate_layers* whose markers appear in *document*.

    If a candidate layer has no entry in ``PROCESS_LAYER_MARKERS``, it is
    silently excluded (conservative default: require evidence).
    """
    text = _build_searchable_text(document)
    matched: List[str] = []
    for layer in candidate_layers:
        markers = PROCESS_LAYER_MARKERS.get(layer)
        if not markers:
            continue
        if any(m.lower() in text for m in markers):
            matched.append(layer)
    return matched


def filter_documents_by_relevance(
    documents: List[Dict[str, Any]],
    *,
    minimum_score: int = 20,
    include_adjacent: bool = True,
    positive_markers: List[str] | None = None,
    negative_markers: List[str] | None = None,
) -> List[Dict[str, Any]]:
    """Score and filter a list of Federal Register API result documents.

    Each document in the returned list gets an additional
    ``_relevance`` key with the scoring output.

    If *include_adjacent* is ``False``, only ``directly_relevant`` documents
    pass the filter.
    """
    filtered: List[Dict[str, Any]] = []
    for doc in documents:
        scoring = score_document_relevance(
            doc,
            positive_markers=positive_markers,
            negative_markers=negative_markers,
        )
        if scoring["relevance_score"] < minimum_score:
            continue
        if not include_adjacent and scoring["relevance_class"] == "adjacent":
            continue
        doc_copy = dict(doc)
        doc_copy["_relevance"] = scoring
        filtered.append(doc_copy)
    return filtered

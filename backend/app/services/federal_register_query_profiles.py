"""
Curated Federal Register query profiles by theme.

Each profile defines default query terms and metadata hints so that callers
(CLI, API, services) can request a focused Federal Register fetch by name
instead of hand-assembling parameters every time.

Profiles are plain dicts and deliberately have no side effects.  The
``resolve_query_profile`` function merges a profile's defaults with any
explicit overrides the caller provides, so explicit parameters always win.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Known agency slugs accepted by the Federal Register API
# (conditions[agencies][] parameter).  The API returns HTTP 400 if a value
# is not a recognised slug.
# ---------------------------------------------------------------------------

KNOWN_AGENCY_SLUGS: Dict[str, str] = {
    # canonical slug -> slug  (identity mapping for lookup)
    "bureau-of-industry-and-security": "bureau-of-industry-and-security",
    "commerce-department": "commerce-department",
    "defense-department": "defense-department",
    "energy-department": "energy-department",
    "interior-department": "interior-department",
    "international-trade-administration": "international-trade-administration",
    "state-department": "state-department",
    "treasury-department": "treasury-department",
    "environmental-protection-agency": "environmental-protection-agency",
    "geological-survey": "geological-survey",
    "national-science-foundation": "national-science-foundation",
    "nuclear-regulatory-commission": "nuclear-regulatory-commission",
    # common aliases / abbreviations -> canonical slug
    "bis": "bureau-of-industry-and-security",
    "doc": "commerce-department",
    "dod": "defense-department",
    "doe": "energy-department",
    "doi": "interior-department",
    "ita": "international-trade-administration",
    "epa": "environmental-protection-agency",
    "usgs": "geological-survey",
    "nsf": "national-science-foundation",
    "nrc": "nuclear-regulatory-commission",
}


def validate_agency_slug(raw: str) -> Optional[str]:
    """Return a valid Federal Register API agency slug, or ``None``.

    Accepts a canonical slug, a known abbreviation, or a lower-cased slug.
    Returns ``None`` when the input cannot be resolved so the caller can
    decide whether to skip or warn.
    """
    key = raw.strip().lower()
    if key in KNOWN_AGENCY_SLUGS:
        return KNOWN_AGENCY_SLUGS[key]
    # Try slugifying free-form text: "Bureau of Industry and Security"
    slugified = key.replace(" ", "-").replace("_", "-")
    if slugified in KNOWN_AGENCY_SLUGS:
        return KNOWN_AGENCY_SLUGS[slugified]
    return None


def validate_agency_slugs(raw_list: List[str]) -> List[str]:
    """Return only the valid slugs from *raw_list*, preserving order."""
    validated: List[str] = []
    seen: set[str] = set()
    for raw in raw_list:
        slug = validate_agency_slug(raw)
        if slug and slug not in seen:
            validated.append(slug)
            seen.add(slug)
    return validated


# ---------------------------------------------------------------------------
# Query profiles
# ---------------------------------------------------------------------------

QUERY_PROFILES: Dict[str, Dict[str, Any]] = {
    "critical_materials": {
        "query": "critical minerals rare earth strategic materials",
        "target_themes": ["critical_materials", "supply_chain_risk"],
        "focus_process_layers": [
            "Rare Earth Mining",
            "Rare Earth Separation",
            "Neodymium Processing",
            "Cobalt Refining",
            "Lithium Processing",
        ],
        "focus_geographies": ["China", "DRC", "Australia", "Canada"],
        "ticker_refs": ["MP", "UUUU", "LAC", "ALB", "LTHM"],
        "document_types": ["RULE", "PRORULE", "NOTICE"],
        "agencies": ["commerce-department", "interior-department", "energy-department"],
        "policy_scope": ["export_control", "stockpile", "industrial_policy"],
        "topic_hints": [
            "critical minerals",
            "rare earth elements",
            "strategic stockpile",
            "mineral security",
        ],
    },
    # --- Narrower decomposed profiles ---
    "rare_earths": {
        "query": "rare earth elements neodymium magnet separation",
        "target_themes": ["critical_materials", "rare_earths"],
        "focus_process_layers": [
            "Rare Earth Mining",
            "Rare Earth Separation",
            "Neodymium Processing",
        ],
        "focus_geographies": ["China", "Australia", "Canada"],
        "ticker_refs": ["MP", "UUUU"],
        "document_types": ["RULE", "PRORULE", "NOTICE"],
        "agencies": ["commerce-department", "interior-department"],
        "policy_scope": ["export_control", "industrial_policy"],
        "positive_markers": [
            "rare earth", "neodymium", "ndfeb", "magnet",
            "separation", "mining", "ore processing",
            "critical mineral", "critical minerals",
        ],
        "negative_markers": [
            "marine mammal", "wildlife", "endangered species",
            "consumer furnace", "incidental take", "fisheries", "habitat",
        ],
    },
    "processed_critical_minerals": {
        "query": "critical mineral processing refining smelting cobalt lithium",
        "target_themes": ["critical_materials", "mineral_processing"],
        "focus_process_layers": [
            "Cobalt Refining",
            "Lithium Processing",
            "Neodymium Processing",
        ],
        "focus_geographies": ["China", "DRC", "Chile", "Australia"],
        "ticker_refs": ["LAC", "ALB", "LTHM", "MP"],
        "document_types": ["RULE", "PRORULE", "NOTICE"],
        "agencies": ["commerce-department", "interior-department", "energy-department"],
        "policy_scope": ["industrial_policy", "stockpile"],
        "positive_markers": [
            "refining", "smelting", "processing", "cobalt", "lithium",
            "battery material", "critical mineral", "domestic processing",
            "mineral security",
        ],
        "negative_markers": [
            "marine mammal", "wildlife", "endangered species",
            "consumer furnace", "incidental take", "fisheries", "habitat",
        ],
    },
    "stockpile_and_section232": {
        "query": "stockpile section 232 national defense strategic reserve",
        "target_themes": ["critical_materials", "national_security"],
        "focus_process_layers": [
            "Rare Earth Mining",
            "Cobalt Refining",
            "Lithium Processing",
        ],
        "focus_geographies": ["China", "DRC", "Canada"],
        "ticker_refs": ["MP", "UUUU"],
        "document_types": ["RULE", "PRORULE", "NOTICE", "PRESDOCU"],
        "agencies": ["commerce-department", "defense-department"],
        "policy_scope": ["stockpile", "national_security", "section_232"],
        "positive_markers": [
            "stockpile", "section 232", "national defense",
            "strategic reserve", "defense production act",
            "critical mineral", "industrial base",
        ],
        "negative_markers": [
            "marine mammal", "wildlife", "endangered species",
            "consumer furnace", "incidental take", "fisheries", "habitat",
        ],
    },
    "entity_list_export_controls": {
        "query": "entity list export control BIS EAR",
        "target_themes": ["export_control", "entity_list"],
        "focus_process_layers": [
            "Rare Earth Separation",
            "Neodymium Processing",
            "Wafer Fabrication",
            "Semiconductor Equipment",
        ],
        "focus_geographies": ["China", "Russia", "Iran"],
        "ticker_refs": ["MP", "NVDA", "ASML", "INTC"],
        "document_types": ["RULE", "NOTICE"],
        "agencies": ["bureau-of-industry-and-security", "commerce-department"],
        "policy_scope": ["export_control", "entity_list"],
        "positive_markers": [
            "entity list", "export administration regulations", "EAR",
            "bureau of industry and security", "bis",
            "export control", "denied persons", "unverified list",
            "military end use",
        ],
        "negative_markers": [
            "marine mammal", "wildlife", "endangered species",
            "consumer furnace", "incidental take", "fisheries", "habitat",
        ],
    },
    "semiconductors": {
        "query": "semiconductor chip advanced computing export control",
        "target_themes": ["semiconductors", "advanced_computing", "export_control"],
        "focus_process_layers": [
            "Wafer Fabrication",
            "Chip Design",
            "EDA Tools",
            "Semiconductor Equipment",
            "Advanced Packaging",
        ],
        "focus_geographies": ["China", "Taiwan", "South Korea", "Japan", "Netherlands"],
        "ticker_refs": ["NVDA", "ASML", "TSM", "INTC", "AMD", "LRCX", "AMAT", "KLAC"],
        "document_types": ["RULE", "PRORULE", "NOTICE"],
        "agencies": [
            "bureau-of-industry-and-security",
            "commerce-department",
        ],
        "policy_scope": ["export_control", "entity_list", "industrial_policy"],
        "topic_hints": [
            "semiconductor",
            "advanced computing",
            "chip export",
            "EAR",
            "entity list",
        ],
    },
    "robotics": {
        "query": "robotics automation advanced manufacturing",
        "target_themes": ["robotics_supply_chain", "advanced_manufacturing"],
        "focus_process_layers": [
            "Servo Motor Manufacturing",
            "Precision Gear Production",
            "Industrial Robot Assembly",
            "Neodymium Processing",
        ],
        "focus_geographies": ["China", "Japan", "Germany", "South Korea"],
        "ticker_refs": ["FANUY", "ABB", "ROK", "ISRG", "MP"],
        "document_types": ["RULE", "PRORULE", "NOTICE"],
        "agencies": [
            "bureau-of-industry-and-security",
            "commerce-department",
            "defense-department",
        ],
        "policy_scope": ["export_control", "industrial_policy", "defense_procurement"],
        "topic_hints": [
            "robotics",
            "automation",
            "advanced manufacturing",
            "industrial base",
        ],
    },
}


def list_query_profiles() -> List[str]:
    """Return sorted profile names."""
    return sorted(QUERY_PROFILES.keys())


def get_query_profile(name: str) -> Optional[Dict[str, Any]]:
    """Return a deep copy of the named profile, or ``None``."""
    profile = QUERY_PROFILES.get(name)
    if profile is None:
        return None
    return deepcopy(profile)


def resolve_query_profile(
    profile_name: Optional[str] = None,
    *,
    overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Merge a named profile with explicit overrides.

    Explicit overrides always win.  If *profile_name* is ``None`` or unknown,
    only the overrides (if any) are returned.

    The returned dict uses the same keys as
    ``fetch_federal_register_policy_feed`` kwargs, so callers can
    ``**resolve_query_profile(...)`` directly.
    """
    base: Dict[str, Any] = {}
    if profile_name:
        profile = get_query_profile(profile_name)
        if profile is not None:
            base = profile

    if overrides:
        for key, value in overrides.items():
            if value is not None:
                base[key] = value

    # Validate agency slugs in the resolved result so that invalid values
    # never reach the Federal Register API.
    if "agencies" in base and base["agencies"]:
        base["agencies"] = validate_agency_slugs(
            [str(a) for a in base["agencies"]]
        )

    return base

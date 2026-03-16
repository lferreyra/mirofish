"""
Normalize policy-feed documents into source-bundle artifacts.

This connector is designed for early policy-spine sources such as:

- Federal Register
- BIS

The output is a regular `source_bundle` so the existing structural parser,
graduation flow, decomposition layer, and ranking layers can consume it without
special handling.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import re
from typing import Any, Dict, Iterable, List


DEFAULT_RETRIEVED_AT = "2026-03-16T00:00:00Z"


def _slugify(value: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "_", str(value).strip().lower())
    return text.strip("_") or "unknown"


def _normalize_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _normalize_source(document: Dict[str, Any]) -> Dict[str, Any]:
    document_id = document.get("document_id") or f"doc_{_slugify(document.get('title', 'policy_notice'))}"
    source_id = document.get("source_id") or f"src_{_slugify(document_id)}"
    publisher = document.get("publisher") or document.get("source_target_name") or "Policy Feed"
    source_class = document.get("source_class") or "government_policy_enforcement"
    return {
        "source_id": source_id,
        "source_class": source_class,
        "title": document.get("title", "Untitled Policy Notice"),
        "canonical_url": document.get("canonical_url", ""),
        "publisher": publisher,
        "published_at": document.get("published_at", ""),
        "retrieved_at": document.get("retrieved_at", DEFAULT_RETRIEVED_AT),
        "language": document.get("language", "en"),
        "jurisdiction": document.get("jurisdiction", "US"),
        "ticker_refs": [str(value).upper() for value in _normalize_list(document.get("ticker_refs"))],
        "theme_refs": [str(value) for value in _normalize_list(document.get("theme_refs"))],
        "source_quality": document.get("source_quality", "high"),
        "source_reliability_score": float(document.get("source_reliability_score", 0.92)),
        "usage_mode": document.get("usage_mode", "evidence"),
        "attachment_type": document.get("attachment_type", "html"),
        "notes": list(_normalize_list(document.get("notes"))),
        "source_target_id": document.get("source_target_id"),
        "source_target_name": document.get("source_target_name"),
        "policy_scope": document.get("policy_scope", []),
        "document_id": document_id,
    }


def _normalize_fragment(document: Dict[str, Any], source_id: str) -> Dict[str, Any]:
    document_id = document.get("document_id") or source_id
    summary = document.get("summary", "")
    excerpt = document.get("excerpt") or summary
    fragment_id = document.get("fragment_id") or f"frag_{_slugify(document_id)}"
    return {
        "fragment_id": fragment_id,
        "source_id": source_id,
        "fragment_type": document.get("fragment_type", "policy_notice_excerpt"),
        "section_label": document.get("section_label", document.get("publisher", "Policy Notice")),
        "excerpt": excerpt,
        "contains_claim_candidate": bool(
            document.get("contains_claim_candidate", True)
        ),
        "research_tags": deepcopy(document.get("research_tags", {})),
        "entity_hints": deepcopy(_normalize_list(document.get("entity_hints"))),
        "relationship_hints": deepcopy(_normalize_list(document.get("relationship_hints"))),
        "claim_candidates": deepcopy(_normalize_list(document.get("claim_candidates"))),
        "inference_candidates": deepcopy(_normalize_list(document.get("inference_candidates"))),
        "event_candidates": deepcopy(_normalize_list(document.get("event_candidates"))),
        "summary": summary,
    }


def _dedupe_by_key(rows: Iterable[Dict[str, Any]], key: str) -> List[Dict[str, Any]]:
    deduped: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        row_key = str(row.get(key, ""))
        if not row_key:
            continue
        deduped[row_key] = row
    return list(deduped.values())


def merge_source_bundles(
    base_bundle: Dict[str, Any] | None,
    incoming_bundle: Dict[str, Any],
) -> Dict[str, Any]:
    base_bundle = deepcopy(base_bundle or {})
    merged = {
        "name": incoming_bundle.get("name") or base_bundle.get("name") or "merged_source_bundle",
        "theme": incoming_bundle.get("theme") or base_bundle.get("theme") or "",
        "notes": list(base_bundle.get("notes", [])),
        "sources": list(base_bundle.get("sources", [])),
        "fragments": list(base_bundle.get("fragments", [])),
        "connector_metadata": deepcopy(base_bundle.get("connector_metadata", {})),
    }

    for note in incoming_bundle.get("notes", []):
        if note not in merged["notes"]:
            merged["notes"].append(note)
    merged["sources"].extend(incoming_bundle.get("sources", []))
    merged["fragments"].extend(incoming_bundle.get("fragments", []))
    merged["sources"] = _dedupe_by_key(merged["sources"], "source_id")
    merged["fragments"] = _dedupe_by_key(merged["fragments"], "fragment_id")

    incoming_metadata = incoming_bundle.get("connector_metadata", {})
    merged["connector_metadata"] = {
        "connector_family": "policy_feed",
        "connector_versions": sorted({
            *(_normalize_list(merged["connector_metadata"].get("connector_versions"))),
            *(_normalize_list(incoming_metadata.get("connector_versions"))),
        }),
        "source_targets": sorted({
            *(_normalize_list(merged["connector_metadata"].get("source_targets"))),
            *(_normalize_list(incoming_metadata.get("source_targets"))),
        }),
        "document_count": len(merged["sources"]),
        "merged_at": datetime.now(timezone.utc).isoformat(),
    }
    return merged


def build_policy_feed_source_bundle(
    policy_feed_payload: Dict[str, Any],
    *,
    existing_source_bundle: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    feed_documents = list(_normalize_list(policy_feed_payload.get("feed_documents")))
    bundle = {
        "name": policy_feed_payload.get("name", "policy_feed_source_bundle"),
        "theme": policy_feed_payload.get("theme", ""),
        "notes": list(_normalize_list(policy_feed_payload.get("notes"))),
        "sources": [],
        "fragments": [],
        "connector_metadata": {
            "connector_family": "policy_feed",
            "connector_versions": ["federal_register_bis_v1"],
            "source_targets": sorted({
                document.get("source_target_name")
                for document in feed_documents
                if document.get("source_target_name")
            }),
            "document_count": len(feed_documents),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "synthetic_sample": bool(policy_feed_payload.get("synthetic_sample", False)),
        },
    }

    if policy_feed_payload.get("synthetic_sample"):
        bundle["notes"].append(
            "Synthetic sample payload used to validate the Federal Register/BIS policy-feed connector."
        )

    for document in feed_documents:
        source = _normalize_source(document)
        fragment = _normalize_fragment(document, source["source_id"])
        bundle["sources"].append(source)
        bundle["fragments"].append(fragment)

    bundle["sources"] = _dedupe_by_key(bundle["sources"], "source_id")
    bundle["fragments"] = _dedupe_by_key(bundle["fragments"], "fragment_id")

    if existing_source_bundle:
        return merge_source_bundles(existing_source_bundle, bundle)
    return bundle


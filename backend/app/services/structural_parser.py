"""
Deterministic structural parser for research-mode source bundles.

This is intentionally narrow. It converts curated source-bundle artifacts with
fragment-level hints into normalized structural parse objects:

- entities
- relationships
- claims
- evidence links
- inferences

The goal is to make the structural-arbitrage workflow executable before we
depend on a full LLM extraction layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .research_ontology import (
    RESEARCH_ENTITY_TYPES,
    RESEARCH_RELATIONSHIP_TYPES,
)


SUPPORTED_ENTITY_TYPES = {entity.name for entity in RESEARCH_ENTITY_TYPES}
SUPPORTED_RELATIONSHIP_TYPES = {
    relationship.name for relationship in RESEARCH_RELATIONSHIP_TYPES
}

TAG_TO_ENTITY_TYPE = {
    "themes": "Theme",
    "systems": "System",
    "subsystems": "Subsystem",
    "components": "Component",
    "materials": "MaterialInput",
    "process_layers": "ProcessLayer",
    "public_companies": "PublicCompany",
    "geographies": "Geography",
    "events": "Event",
    "expressions": "ExpressionCandidate",
}


def _slugify(value: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower())
    return text.strip("_") or "unknown"


def _normalize_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


@dataclass
class EntityRef:
    entity_id: str
    entity_type: str
    canonical_name: str


class StructuralParser:
    """Convert curated source bundles into normalized structural parses."""

    def __init__(self) -> None:
        self._entities_by_key: Dict[Tuple[str, str], EntityRef] = {}
        self._entity_payloads: Dict[str, Dict[str, Any]] = {}
        self._relationships_by_key: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
        self._claims_by_key: Dict[str, Dict[str, Any]] = {}
        self._evidence_links_by_key: Dict[Tuple[str, str, str], Dict[str, Any]] = {}

    def build(self, source_bundle: Dict[str, Any]) -> Dict[str, Any]:
        sources = _normalize_list(source_bundle.get("sources"))
        source_map = {
            source.get("source_id"): source
            for source in sources
            if source.get("source_id")
        }

        fragments = _normalize_list(source_bundle.get("fragments"))
        for fragment in fragments:
            self._ingest_fragment_entities(fragment)

        for fragment in fragments:
            self._ingest_fragment_relationships(fragment)

        claims: List[Dict[str, Any]] = []
        for fragment in fragments:
            claims.extend(self._ingest_fragment_claims(fragment))

        inferences: List[Dict[str, Any]] = []
        for fragment in fragments:
            inferences.extend(self._ingest_fragment_inferences(fragment))

        entities = sorted(
            self._entity_payloads.values(),
            key=lambda entity: (entity["entity_type"], entity["canonical_name"]),
        )
        relationships = sorted(
            self._relationships_by_key.values(),
            key=lambda rel: (
                rel["relationship_type"],
                rel["source_entity_id"],
                rel["target_entity_id"],
            ),
        )
        evidence_links = sorted(
            self._evidence_links_by_key.values(),
            key=lambda link: (
                link["supports_object_type"],
                link["supports_object_id"],
                link["fragment_id"],
            ),
        )

        return {
            "parser_version": "deterministic_v1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_ids": sorted(source_map),
            "entities": entities,
            "relationships": relationships,
            "claims": claims,
            "evidence_links": evidence_links,
            "inferences": inferences,
            "summary": {
                "entity_count": len(entities),
                "relationship_count": len(relationships),
                "claim_count": len(claims),
                "evidence_link_count": len(evidence_links),
                "inference_count": len(inferences),
            },
        }

    def _ensure_entity(
        self,
        entity_type: str,
        canonical_name: str,
        *,
        aliases: Optional[Iterable[str]] = None,
        description: str = "",
        attributes: Optional[Dict[str, Any]] = None,
        confidence: str = "medium",
    ) -> EntityRef:
        if entity_type not in SUPPORTED_ENTITY_TYPES:
            raise ValueError(f"unsupported entity type: {entity_type}")

        key = (entity_type, canonical_name.strip().lower())
        existing = self._entities_by_key.get(key)
        if existing:
            payload = self._entity_payloads[existing.entity_id]
            merged_aliases = set(payload.get("aliases", []))
            merged_aliases.update(alias for alias in aliases or [] if alias)
            payload["aliases"] = sorted(merged_aliases)
            if attributes:
                payload.setdefault("attributes", {}).update(attributes)
            if description and not payload.get("description"):
                payload["description"] = description
            if confidence == "high" or (
                confidence == "medium" and payload.get("confidence") == "low"
            ):
                payload["confidence"] = confidence
            return existing

        entity_id = f"ent_{_slugify(entity_type)}_{_slugify(canonical_name)}"
        ref = EntityRef(
            entity_id=entity_id,
            entity_type=entity_type,
            canonical_name=canonical_name,
        )
        self._entities_by_key[key] = ref
        self._entity_payloads[entity_id] = {
            "entity_id": entity_id,
            "entity_type": entity_type,
            "canonical_name": canonical_name,
            "aliases": sorted({alias for alias in aliases or [] if alias}),
            "description": description,
            "attributes": attributes or {},
            "confidence": confidence,
        }
        return ref

    def _extract_entity_hints(self, fragment: Dict[str, Any]) -> List[Dict[str, Any]]:
        hints = list(_normalize_list(fragment.get("entity_hints")))
        research_tags = fragment.get("research_tags", {}) or {}

        for tag_key, entity_type in TAG_TO_ENTITY_TYPE.items():
            for value in _normalize_list(research_tags.get(tag_key)):
                if isinstance(value, dict):
                    hint = {"entity_type": entity_type, **value}
                    hint.setdefault("canonical_name", value.get("canonical_name"))
                else:
                    hint = {
                        "entity_type": entity_type,
                        "canonical_name": str(value),
                    }
                hints.append(hint)

        for ticker in _normalize_list(fragment.get("ticker_refs")):
            hints.append(
                {
                    "entity_type": "PublicCompany",
                    "canonical_name": str(ticker).upper(),
                    "attributes": {"ticker": str(ticker).upper()},
                }
            )
        return hints

    def _ingest_fragment_entities(self, fragment: Dict[str, Any]) -> None:
        for hint in self._extract_entity_hints(fragment):
            entity_type = hint.get("entity_type")
            canonical_name = hint.get("canonical_name")
            if not entity_type or not canonical_name:
                continue
            self._ensure_entity(
                entity_type,
                canonical_name,
                aliases=_normalize_list(hint.get("aliases")),
                description=hint.get("description", ""),
                attributes=hint.get("attributes", {}),
                confidence=hint.get("confidence", "medium"),
            )

    def _resolve_entity_from_hint(self, hint: Dict[str, Any]) -> EntityRef:
        entity_type = hint.get("entity_type") or hint.get("type")
        canonical_name = hint.get("canonical_name") or hint.get("name")
        if not entity_type or not canonical_name:
            raise ValueError(f"entity hint missing type or name: {hint}")
        return self._ensure_entity(
            entity_type,
            canonical_name,
            aliases=_normalize_list(hint.get("aliases")),
            description=hint.get("description", ""),
            attributes=hint.get("attributes", {}),
            confidence=hint.get("confidence", "medium"),
        )

    def _make_relationship_key(
        self, relationship_type: str, source_id: str, target_id: str
    ) -> Tuple[str, str, str]:
        return (relationship_type, source_id, target_id)

    def _link_evidence(
        self,
        *,
        fragment_id: str,
        source_id: str,
        supports_object_type: str,
        supports_object_id: str,
        support_mode: str = "supporting",
        strength: str = "direct",
    ) -> str:
        key = (fragment_id, supports_object_type, supports_object_id)
        existing = self._evidence_links_by_key.get(key)
        if existing:
            return existing["evidence_link_id"]

        evidence_link_id = (
            f"ev_{_slugify(fragment_id)}_{supports_object_type}_{_slugify(supports_object_id)}"
        )
        payload = {
            "evidence_link_id": evidence_link_id,
            "source_id": source_id,
            "fragment_id": fragment_id,
            "supports_object_type": supports_object_type,
            "supports_object_id": supports_object_id,
            "support_mode": support_mode,
            "strength": strength,
        }
        self._evidence_links_by_key[key] = payload
        return evidence_link_id

    def _ingest_fragment_relationships(self, fragment: Dict[str, Any]) -> None:
        fragment_id = fragment.get("fragment_id")
        source_id = fragment.get("source_id")
        if not fragment_id or not source_id:
            return

        for hint in _normalize_list(fragment.get("relationship_hints")):
            relationship_type = hint.get("relationship_type")
            if relationship_type not in SUPPORTED_RELATIONSHIP_TYPES:
                continue

            source_ref = self._resolve_entity_from_hint(
                {
                    "entity_type": hint.get("source_type"),
                    "canonical_name": hint.get("source_name"),
                }
            )
            target_ref = self._resolve_entity_from_hint(
                {
                    "entity_type": hint.get("target_type"),
                    "canonical_name": hint.get("target_name"),
                }
            )

            relationship_key = self._make_relationship_key(
                relationship_type, source_ref.entity_id, target_ref.entity_id
            )
            payload = self._relationships_by_key.get(relationship_key)
            if not payload:
                relationship_id = hint.get("relationship_id") or (
                    f"rel_{_slugify(relationship_type)}_{_slugify(source_ref.entity_id)}_{_slugify(target_ref.entity_id)}"
                )
                payload = {
                    "relationship_id": relationship_id,
                    "relationship_type": relationship_type,
                    "source_entity_id": source_ref.entity_id,
                    "target_entity_id": target_ref.entity_id,
                    "direction": "source_to_target",
                    "relationship_strength": hint.get("relationship_strength", "medium"),
                    "causal_role": hint.get("causal_role", ""),
                    "confidence": hint.get("confidence", "medium"),
                    "evidence_refs": [],
                    "notes": _normalize_list(hint.get("notes")),
                    "relationship_key": hint.get("key") or relationship_id,
                }
                self._relationships_by_key[relationship_key] = payload

            evidence_link_id = self._link_evidence(
                fragment_id=fragment_id,
                source_id=source_id,
                supports_object_type="relationship",
                supports_object_id=payload["relationship_id"],
                support_mode=hint.get("support_mode", "supporting"),
                strength=hint.get("strength", "direct"),
            )
            if evidence_link_id not in payload["evidence_refs"]:
                payload["evidence_refs"].append(evidence_link_id)

    def _resolve_relationship_ids(
        self, relationship_keys: Iterable[str]
    ) -> List[str]:
        resolved: List[str] = []
        for relationship in self._relationships_by_key.values():
            if relationship.get("relationship_key") in relationship_keys:
                resolved.append(relationship["relationship_id"])
        return sorted(set(resolved))

    def _resolve_entity_ids_by_name(self, entity_names: Iterable[str]) -> List[str]:
        resolved: List[str] = []
        requested = {name.strip().lower() for name in entity_names if name}
        for (entity_type, canonical_name), ref in self._entities_by_key.items():
            if canonical_name in requested:
                resolved.append(ref.entity_id)
        return sorted(set(resolved))

    def _ingest_fragment_claims(self, fragment: Dict[str, Any]) -> List[Dict[str, Any]]:
        fragment_id = fragment.get("fragment_id")
        source_id = fragment.get("source_id")
        claims: List[Dict[str, Any]] = []
        if not fragment_id or not source_id:
            return claims

        for index, hint in enumerate(_normalize_list(fragment.get("claim_candidates"))):
            claim_key = hint.get("claim_key") or f"{fragment_id}_claim_{index + 1}"
            if claim_key in self._claims_by_key:
                claim = self._claims_by_key[claim_key]
            else:
                claim_id = f"claim_{_slugify(claim_key)}"
                claim = {
                    "claim_id": claim_id,
                    "claim_type": hint.get("claim_type", "bottleneck_assertion"),
                    "claim_text": hint.get("claim_text", ""),
                    "claim_status": hint.get("claim_status", "supported"),
                    "claim_kind": hint.get("claim_kind", "inferential"),
                    "confidence": hint.get("confidence", "medium"),
                    "entity_refs": self._resolve_entity_ids_by_name(
                        _normalize_list(hint.get("entity_names"))
                    ),
                    "relationship_refs": self._resolve_relationship_ids(
                        _normalize_list(hint.get("relationship_keys"))
                    ),
                    "source_ids": [source_id],
                    "fragment_ids": [fragment_id],
                    "notes": _normalize_list(hint.get("notes")),
                    "claim_key": claim_key,
                }
                self._claims_by_key[claim_key] = claim

            evidence_link_id = self._link_evidence(
                fragment_id=fragment_id,
                source_id=source_id,
                supports_object_type="claim",
                supports_object_id=claim["claim_id"],
                support_mode=hint.get("support_mode", "supporting"),
                strength=hint.get("strength", "direct"),
            )
            claim.setdefault("evidence_refs", [])
            if evidence_link_id not in claim["evidence_refs"]:
                claim["evidence_refs"].append(evidence_link_id)
            claims.append(claim)
        return claims

    def _resolve_claim_ids(self, claim_keys: Iterable[str]) -> List[str]:
        resolved: List[str] = []
        for claim in self._claims_by_key.values():
            if claim.get("claim_key") in claim_keys:
                resolved.append(claim["claim_id"])
        return sorted(set(resolved))

    def _ingest_fragment_inferences(
        self, fragment: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        fragment_id = fragment.get("fragment_id")
        source_id = fragment.get("source_id")
        inferences: List[Dict[str, Any]] = []
        if not fragment_id or not source_id:
            return inferences

        for index, hint in enumerate(
            _normalize_list(fragment.get("inference_candidates"))
        ):
            inference_key = hint.get("inference_key") or f"{fragment_id}_inf_{index + 1}"
            inference_id = f"inf_{_slugify(inference_key)}"
            payload = {
                "inference_id": inference_id,
                "inference_type": hint.get("inference_type", "market_miss"),
                "statement": hint.get("statement", ""),
                "derived_from_claim_ids": self._resolve_claim_ids(
                    _normalize_list(hint.get("claim_keys"))
                ),
                "derived_from_relationship_ids": self._resolve_relationship_ids(
                    _normalize_list(hint.get("relationship_keys"))
                ),
                "confidence": hint.get("confidence", "medium"),
                "falsifiers": _normalize_list(hint.get("falsifiers")),
                "notes": _normalize_list(hint.get("notes")),
            }
            evidence_link_id = self._link_evidence(
                fragment_id=fragment_id,
                source_id=source_id,
                supports_object_type="inference",
                supports_object_id=inference_id,
                support_mode=hint.get("support_mode", "supporting"),
                strength=hint.get("strength", "contextual"),
            )
            payload["evidence_refs"] = [evidence_link_id]
            inferences.append(payload)
        return inferences


def build_structural_parse_from_source_bundle(
    source_bundle: Dict[str, Any]
) -> Dict[str, Any]:
    """Public helper used by API routes and local scripts."""
    return StructuralParser().build(source_bundle)

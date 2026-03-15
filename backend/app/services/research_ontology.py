"""
Canonical ontology definition for bottleneck-focused research mode.

This is intentionally separate from the social-simulation ontology generator.
It defines the stable entity and relationship vocabulary that future research
projects, API endpoints, and prompt templates should target.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class OntologyAttribute:
    name: str
    description: str
    field_type: str = "text"

    def to_dict(self) -> Dict[str, str]:
        return {
            "name": self.name,
            "type": self.field_type,
            "description": self.description,
        }


@dataclass(frozen=True)
class OntologyEntityType:
    name: str
    description: str
    attributes: List[OntologyAttribute] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "description": self.description,
            "attributes": [attribute.to_dict() for attribute in self.attributes],
        }


@dataclass(frozen=True)
class OntologyRelationshipType:
    name: str
    description: str
    source_targets: List[Dict[str, str]]
    attributes: List[OntologyAttribute] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "description": self.description,
            "source_targets": list(self.source_targets),
            "attributes": [attribute.to_dict() for attribute in self.attributes],
        }


@dataclass(frozen=True)
class EvidenceRequirement:
    claim_type: str
    minimum_sources: int
    required_source_classes: List[str]
    notes: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


ONTOLOGY_NAME = "bottleneck_research"
ONTOLOGY_VERSION = "v1"

SUPPORTED_SOURCE_CLASSES: List[str] = [
    "filing",
    "government",
    "industry_body",
    "company_release",
    "policy_tracker",
    "analysis",
]

SUPPORTED_CLAIM_TYPES: List[str] = [
    "market_share_or_concentration",
    "capacity_expansion_or_ramp",
    "export_control_or_policy",
    "demand_acceleration",
    "bottleneck_assertion",
    "value_capture_assertion",
]


RESEARCH_ENTITY_TYPES: List[OntologyEntityType] = [
    OntologyEntityType(
        name="Theme",
        description="Top-level research theme or bottleneck narrative.",
        attributes=[
            OntologyAttribute("title", "Short research theme title"),
            OntologyAttribute("scope", "Thematic scope and boundaries"),
        ],
    ),
    OntologyEntityType(
        name="MarketDriver",
        description="Demand-side force increasing system stress or adoption.",
        attributes=[
            OntologyAttribute("driver_type", "Demand, policy, regulatory, or technology driver"),
            OntologyAttribute("time_horizon", "Expected time horizon of impact"),
        ],
    ),
    OntologyEntityType(
        name="EndMarket",
        description="Demand destination consuming the system or component.",
        attributes=[
            OntologyAttribute("market_name", "Name of the end market"),
            OntologyAttribute("growth_profile", "Expected growth or adoption profile"),
        ],
    ),
    OntologyEntityType(
        name="SystemLayer",
        description="Top-level deployed system or infrastructure layer.",
        attributes=[
            OntologyAttribute("layer_name", "Name of the system layer"),
            OntologyAttribute("functional_role", "Role in the full chain"),
        ],
    ),
    OntologyEntityType(
        name="Component",
        description="Intermediate component, module, or subsystem in the chain.",
        attributes=[
            OntologyAttribute("component_name", "Component or subsystem name"),
            OntologyAttribute("qualification_level", "Qualification or switching difficulty"),
        ],
    ),
    OntologyEntityType(
        name="MaterialInput",
        description="Raw material, substrate, refined input, or specialty consumable.",
        attributes=[
            OntologyAttribute("material_name", "Material or refined input name"),
            OntologyAttribute("processing_stage", "Mining, refining, separation, substrate, or other stage"),
        ],
    ),
    OntologyEntityType(
        name="BottleneckLayer",
        description="Specific layer identified as constrained or strategically important.",
        attributes=[
            OntologyAttribute("layer_name", "Human-readable bottleneck layer name"),
            OntologyAttribute("severity_band", "Low, emerging, moderate, high, or critical"),
            OntologyAttribute("value_capture_band", "Low, emerging, moderate, high, or critical"),
        ],
    ),
    OntologyEntityType(
        name="PublicCompany",
        description="Listed company exposed to the bottleneck theme.",
        attributes=[
            OntologyAttribute("ticker", "Primary ticker or market symbol"),
            OntologyAttribute("exposure_type", "Pure-play, adjacent, diversified, or enabling"),
        ],
    ),
    OntologyEntityType(
        name="Facility",
        description="Physical plant, fab, refinery, line, or manufacturing site.",
        attributes=[
            OntologyAttribute("facility_name", "Facility or project name"),
            OntologyAttribute("capacity_stage", "Operating, ramping, announced, or planned"),
        ],
    ),
    OntologyEntityType(
        name="Geography",
        description="Country, region, or location relevant to concentration or policy risk.",
        attributes=[
            OntologyAttribute("geo_name", "Country or regional name"),
            OntologyAttribute("risk_profile", "Strategic, diversified, constrained, or policy-sensitive"),
        ],
    ),
    OntologyEntityType(
        name="PolicyAction",
        description="Export control, subsidy, standard, or industrial-policy action.",
        attributes=[
            OntologyAttribute("policy_name", "Policy or action name"),
            OntologyAttribute("policy_type", "Export control, subsidy, standard, grant, or regulation"),
        ],
    ),
    OntologyEntityType(
        name="CapacityExpansion",
        description="Project or investment intended to add qualified supply.",
        attributes=[
            OntologyAttribute("project_name", "Expansion project name"),
            OntologyAttribute("expected_start", "Expected start or ramp date"),
        ],
    ),
    OntologyEntityType(
        name="Claim",
        description="Structured research claim to be audited against sources.",
        attributes=[
            OntologyAttribute("claim_text", "Structured factual or inferential claim"),
            OntologyAttribute("status", "Supported, unverified, or unsupported"),
            OntologyAttribute("confidence", "Low, medium, or high"),
        ],
    ),
    OntologyEntityType(
        name="Source",
        description="Primary or secondary source supporting a claim.",
        attributes=[
            OntologyAttribute("source_url", "Canonical source URL"),
            OntologyAttribute("source_class", "Filing, company release, government, industry body, or analysis"),
        ],
    ),
]


RESEARCH_RELATIONSHIP_TYPES: List[OntologyRelationshipType] = [
    OntologyRelationshipType(
        name="DRIVEN_BY",
        description="Theme or system is driven by a market or policy force.",
        source_targets=[
            {"source": "Theme", "target": "MarketDriver"},
            {"source": "BottleneckLayer", "target": "MarketDriver"},
        ],
    ),
    OntologyRelationshipType(
        name="USED_IN",
        description="Component, material, or bottleneck layer is used in a system or end market.",
        source_targets=[
            {"source": "MaterialInput", "target": "Component"},
            {"source": "Component", "target": "SystemLayer"},
            {"source": "SystemLayer", "target": "EndMarket"},
            {"source": "BottleneckLayer", "target": "EndMarket"},
        ],
    ),
    OntologyRelationshipType(
        name="DEPENDS_ON",
        description="A layer or system depends on another layer or input.",
        source_targets=[
            {"source": "SystemLayer", "target": "Component"},
            {"source": "Component", "target": "MaterialInput"},
            {"source": "BottleneckLayer", "target": "MaterialInput"},
            {"source": "BottleneckLayer", "target": "Component"},
            {"source": "BottleneckLayer", "target": "SystemLayer"},
        ],
    ),
    OntologyRelationshipType(
        name="SUPPLIED_BY",
        description="A bottleneck layer, component, or material is supplied by a public company.",
        source_targets=[
            {"source": "MaterialInput", "target": "PublicCompany"},
            {"source": "Component", "target": "PublicCompany"},
            {"source": "BottleneckLayer", "target": "PublicCompany"},
        ],
    ),
    OntologyRelationshipType(
        name="LOCATED_IN",
        description="Facility, company, or layer has important concentration in a geography.",
        source_targets=[
            {"source": "Facility", "target": "Geography"},
            {"source": "PublicCompany", "target": "Geography"},
            {"source": "BottleneckLayer", "target": "Geography"},
        ],
    ),
    OntologyRelationshipType(
        name="CONSTRAINED_BY",
        description="A layer is constrained by policy, qualification, or capacity expansion timing.",
        source_targets=[
            {"source": "BottleneckLayer", "target": "PolicyAction"},
            {"source": "BottleneckLayer", "target": "CapacityExpansion"},
            {"source": "PublicCompany", "target": "PolicyAction"},
        ],
    ),
    OntologyRelationshipType(
        name="EXPANDS_CAPACITY_FOR",
        description="A facility or expansion project adds capacity for a layer or company.",
        source_targets=[
            {"source": "CapacityExpansion", "target": "BottleneckLayer"},
            {"source": "CapacityExpansion", "target": "PublicCompany"},
            {"source": "Facility", "target": "BottleneckLayer"},
        ],
    ),
    OntologyRelationshipType(
        name="SUPPORTS_CLAIM",
        description="A source supports or challenges a research claim.",
        source_targets=[
            {"source": "Source", "target": "Claim"},
        ],
        attributes=[
            OntologyAttribute("support_type", "supporting, contradictory, or contextual"),
        ],
    ),
    OntologyRelationshipType(
        name="DESCRIBES",
        description="A claim describes a specific theme, layer, company, or policy action.",
        source_targets=[
            {"source": "Claim", "target": "Theme"},
            {"source": "Claim", "target": "BottleneckLayer"},
            {"source": "Claim", "target": "PublicCompany"},
            {"source": "Claim", "target": "PolicyAction"},
        ],
    ),
    OntologyRelationshipType(
        name="ALTERNATIVE_TO",
        description="A layer, component, or material competes with or substitutes for another.",
        source_targets=[
            {"source": "Component", "target": "Component"},
            {"source": "MaterialInput", "target": "MaterialInput"},
            {"source": "BottleneckLayer", "target": "BottleneckLayer"},
        ],
    ),
]

RESEARCH_EDGE_TYPES: List[OntologyRelationshipType] = RESEARCH_RELATIONSHIP_TYPES


EVIDENCE_REQUIREMENTS: List[EvidenceRequirement] = [
    EvidenceRequirement(
        claim_type="market_share_or_concentration",
        minimum_sources=1,
        required_source_classes=["filing", "government", "industry_body"],
        notes="Prefer filings or government/industry-body data over media summaries.",
    ),
    EvidenceRequirement(
        claim_type="capacity_expansion_or_ramp",
        minimum_sources=1,
        required_source_classes=["company_release", "filing", "government"],
        notes="Company releases are acceptable, but filings or government corroboration are preferred when available.",
    ),
    EvidenceRequirement(
        claim_type="export_control_or_policy",
        minimum_sources=1,
        required_source_classes=["government", "policy_tracker", "filing"],
        notes="Must be grounded in a policy or government source, or a filing that quotes the policy directly.",
    ),
    EvidenceRequirement(
        claim_type="demand_acceleration",
        minimum_sources=1,
        required_source_classes=["filing", "government", "company_release"],
        notes="Use company or government demand statements, but treat pure narrative extrapolation as insufficient.",
    ),
    EvidenceRequirement(
        claim_type="bottleneck_assertion",
        minimum_sources=2,
        required_source_classes=["government", "industry_body", "filing"],
        notes="At least one source should describe the constraint directly rather than only implying it.",
    ),
    EvidenceRequirement(
        claim_type="value_capture_assertion",
        minimum_sources=2,
        required_source_classes=["filing", "company_release"],
        notes="Requires evidence of pricing, margin leverage, scarcity duration, or listed-vehicle purity.",
    ),
]


CASE_STUDY_TO_ONTOLOGY_MAPPING: Dict[str, Dict[str, List[str]]] = {
    "thesis-intake": {
        "Theme": ["title", "why this matters"],
        "MarketDriver": ["raw claims", "why it might be mispriced"],
        "EndMarket": ["initial dependency chain"],
        "BottleneckLayer": ["raw claims", "expression candidates"],
    },
    "claims-audit": {
        "Claim": ["claim_text", "status", "confidence"],
        "Source": ["source_url", "source_type"],
    },
    "chokepoint-scores": {
        "BottleneckLayer": ["severity_signals", "value_capture_signals"],
        "PublicCompany": ["public_companies"],
    },
    "case-study-summary": {
        "Theme": ["objective", "interpretation"],
        "BottleneckLayer": ["scoring output", "follow-up questions"],
        "PolicyAction": ["claims audit and interpretation"],
        "CapacityExpansion": ["claims audit and interpretation"],
    },
}


def build_research_ontology_spec() -> Dict[str, object]:
    """Return the canonical bottleneck-research ontology specification."""
    spec = {
        "ontology_name": ONTOLOGY_NAME,
        "ontology_version": ONTOLOGY_VERSION,
        "entity_types": [entity.to_dict() for entity in RESEARCH_ENTITY_TYPES],
        "edge_types": [relationship.to_dict() for relationship in RESEARCH_EDGE_TYPES],
        "relationship_types": [
            relationship.to_dict() for relationship in RESEARCH_RELATIONSHIP_TYPES
        ],
        "evidence_requirements": [
            requirement.to_dict() for requirement in EVIDENCE_REQUIREMENTS
        ],
        "artifact_mapping": CASE_STUDY_TO_ONTOLOGY_MAPPING,
        "score_dimensions": ["severity", "value_capture"],
        "supported_source_classes": list(SUPPORTED_SOURCE_CLASSES),
        "supported_claim_types": list(SUPPORTED_CLAIM_TYPES),
    }
    validate_research_ontology_spec(spec)
    return spec


def build_research_graph_ontology() -> Dict[str, object]:
    """
    Return the ontology payload compatible with the current graph builder.

    The existing graph stack expects `entity_types` and `edge_types`, while the
    broader research spec also exposes richer metadata.
    """
    spec = build_research_ontology_spec()
    return {
        "ontology_name": spec["ontology_name"],
        "ontology_version": spec["ontology_version"],
        "entity_types": spec["entity_types"],
        "edge_types": spec["edge_types"],
    }


def validate_research_ontology_spec(spec: Dict[str, object]) -> None:
    """Validate the stable research ontology contract."""
    required_keys = {
        "ontology_name",
        "ontology_version",
        "entity_types",
        "edge_types",
        "relationship_types",
        "evidence_requirements",
        "artifact_mapping",
        "score_dimensions",
        "supported_source_classes",
        "supported_claim_types",
    }
    missing = required_keys - set(spec)
    if missing:
        raise ValueError(f"ontology spec missing keys: {sorted(missing)}")

    entity_types = spec["entity_types"]
    edge_types = spec["edge_types"]
    relationship_types = spec["relationship_types"]
    evidence_requirements = spec["evidence_requirements"]
    artifact_mapping = spec["artifact_mapping"]
    score_dimensions = spec["score_dimensions"]
    supported_source_classes = set(spec["supported_source_classes"])
    supported_claim_types = set(spec["supported_claim_types"])

    if not isinstance(entity_types, list) or not entity_types:
        raise ValueError("entity_types must be a non-empty list")
    if not isinstance(edge_types, list) or not edge_types:
        raise ValueError("edge_types must be a non-empty list")
    if not isinstance(relationship_types, list) or not relationship_types:
        raise ValueError("relationship_types must be a non-empty list")
    if edge_types != relationship_types:
        raise ValueError("edge_types and relationship_types must match exactly")
    if list(score_dimensions) != ["severity", "value_capture"]:
        raise ValueError("score_dimensions must be ['severity', 'value_capture']")

    entity_names = [entity["name"] for entity in entity_types]
    relationship_names = [relationship["name"] for relationship in relationship_types]

    if len(entity_names) != len(set(entity_names)):
        raise ValueError("entity type names must be unique")
    if len(relationship_names) != len(set(relationship_names)):
        raise ValueError("relationship type names must be unique")

    required_entity_names = {
        "Theme",
        "BottleneckLayer",
        "PublicCompany",
        "Claim",
        "Source",
    }
    required_relationship_names = {
        "DEPENDS_ON",
        "SUPPLIED_BY",
        "SUPPORTS_CLAIM",
        "DESCRIBES",
    }

    if not required_entity_names.issubset(set(entity_names)):
        raise ValueError("required entity types are missing from ontology")
    if not required_relationship_names.issubset(set(relationship_names)):
        raise ValueError("required relationship types are missing from ontology")

    expected_artifacts = {
        "thesis-intake",
        "claims-audit",
        "chokepoint-scores",
        "case-study-summary",
    }
    if set(artifact_mapping) != expected_artifacts:
        raise ValueError("artifact_mapping must cover the canonical case-study files")

    for entity in entity_types:
        for attribute in entity.get("attributes", []):
            if "type" not in attribute:
                raise ValueError("entity attribute definitions must include `type`")

    for relationship in relationship_types:
        if not relationship.get("source_targets"):
            raise ValueError("every relationship type must declare source_targets")
        for attribute in relationship.get("attributes", []):
            if "type" not in attribute:
                raise ValueError("relationship attribute definitions must include `type`")

    for requirement in evidence_requirements:
        claim_type = requirement["claim_type"]
        source_classes = set(requirement["required_source_classes"])

        if claim_type not in supported_claim_types:
            raise ValueError(f"unsupported evidence claim_type: {claim_type}")
        if not source_classes:
            raise ValueError("evidence requirements must declare source classes")
        if not source_classes.issubset(supported_source_classes):
            raise ValueError(
                f"unsupported source class in evidence requirement: {claim_type}"
            )

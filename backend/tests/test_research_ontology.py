import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "app" / "services" / "research_ontology.py"
)
MODULE_SPEC = spec_from_file_location("research_ontology", MODULE_PATH)
research_ontology = module_from_spec(MODULE_SPEC)
assert MODULE_SPEC.loader is not None
sys.modules[MODULE_SPEC.name] = research_ontology
MODULE_SPEC.loader.exec_module(research_ontology)


def test_build_research_ontology_spec_is_stable_and_valid():
    spec = research_ontology.build_research_ontology_spec()

    assert spec["ontology_name"] == "bottleneck_research"
    assert spec["ontology_version"] == "v1"
    assert spec["score_dimensions"] == ["severity", "value_capture"]
    assert spec["edge_types"] == spec["relationship_types"]

    entity_names = {entity["name"] for entity in spec["entity_types"]}
    relationship_names = {
        relationship["name"] for relationship in spec["relationship_types"]
    }

    assert {"Theme", "BottleneckLayer", "PublicCompany", "Claim", "Source"}.issubset(
        entity_names
    )
    assert {"DEPENDS_ON", "SUPPLIED_BY", "SUPPORTS_CLAIM", "DESCRIBES"}.issubset(
        relationship_names
    )

    research_ontology.validate_research_ontology_spec(spec)


def test_build_research_graph_ontology_matches_existing_graph_contract():
    graph_ontology = research_ontology.build_research_graph_ontology()

    assert set(graph_ontology) == {
        "ontology_name",
        "ontology_version",
        "entity_types",
        "edge_types",
    }
    assert graph_ontology["entity_types"]
    assert graph_ontology["edge_types"]


def test_entity_and_relationship_attributes_include_explicit_types():
    spec = research_ontology.build_research_ontology_spec()

    for entity in spec["entity_types"]:
        for attribute in entity["attributes"]:
            assert attribute["type"] == "text"

    for relationship in spec["relationship_types"]:
        for attribute in relationship["attributes"]:
            assert attribute["type"] == "text"


def test_evidence_requirements_only_reference_supported_claims_and_sources():
    spec = research_ontology.build_research_ontology_spec()
    supported_claim_types = set(spec["supported_claim_types"])
    supported_source_classes = set(spec["supported_source_classes"])

    for requirement in spec["evidence_requirements"]:
        assert requirement["claim_type"] in supported_claim_types
        assert set(requirement["required_source_classes"]).issubset(
            supported_source_classes
        )

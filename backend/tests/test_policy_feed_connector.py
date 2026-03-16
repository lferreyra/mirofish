import json
import sys
import types
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SERVICES_ROOT = Path(__file__).resolve().parents[1] / "app" / "services"

app_pkg = types.ModuleType("app")
app_pkg.__path__ = []
services_pkg = types.ModuleType("app.services")
services_pkg.__path__ = [str(SERVICES_ROOT)]
sys.modules["app"] = app_pkg
sys.modules["app.services"] = services_pkg

full_name = "app.services.policy_feed_connector"
spec = spec_from_file_location(full_name, SERVICES_ROOT / "policy_feed_connector.py")
module = module_from_spec(spec)
sys.modules[full_name] = module
assert spec.loader is not None
spec.loader.exec_module(module)

structural_full_name = "app.services.structural_parser"
ontology_full_name = "app.services.research_ontology"
ontology_spec = spec_from_file_location(ontology_full_name, SERVICES_ROOT / "research_ontology.py")
ontology_module = module_from_spec(ontology_spec)
sys.modules[ontology_full_name] = ontology_module
assert ontology_spec.loader is not None
ontology_spec.loader.exec_module(ontology_module)

structural_spec = spec_from_file_location(structural_full_name, SERVICES_ROOT / "structural_parser.py")
structural_module = module_from_spec(structural_spec)
sys.modules[structural_full_name] = structural_module
assert structural_spec.loader is not None
structural_spec.loader.exec_module(structural_module)


def _load_json(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_build_policy_feed_source_bundle_normalizes_documents():
    payload = module.build_policy_feed_source_bundle(
        _load_json("research/templates/federal-register-bis-policy-feed-template-v1.json")
    )

    assert payload["connector_metadata"]["connector_family"] == "policy_feed"
    assert payload["connector_metadata"]["document_count"] == 2
    assert payload["connector_metadata"]["synthetic_sample"] is True
    assert len(payload["sources"]) == 2
    assert len(payload["fragments"]) == 2

    sources = {source["publisher"]: source for source in payload["sources"]}
    assert sources["Federal Register"]["source_class"] == "government_policy_enforcement"
    assert sources["Bureau of Industry and Security"]["source_target_name"] == "Bureau of Industry and Security (BIS), U.S. Department of Commerce"

    first_fragment = payload["fragments"][0]
    assert first_fragment["fragment_type"] == "policy_notice_excerpt"
    assert first_fragment["contains_claim_candidate"] is True
    assert first_fragment["claim_candidates"]


def test_merge_source_bundles_preserves_existing_and_dedupes():
    existing = {
        "name": "existing_bundle",
        "theme": "critical_materials",
        "notes": ["existing note"],
        "sources": [
            {"source_id": "src_existing", "title": "Existing", "source_class": "government_policy_enforcement"}
        ],
        "fragments": [
            {"fragment_id": "frag_existing", "source_id": "src_existing", "excerpt": "Existing"}
        ],
        "connector_metadata": {"connector_versions": ["legacy"], "source_targets": ["Existing Source"]},
    }
    incoming = module.build_policy_feed_source_bundle(
        _load_json("research/templates/federal-register-bis-policy-feed-template-v1.json")
    )

    merged = module.merge_source_bundles(existing, incoming)

    assert merged["name"] == incoming["name"]
    assert len(merged["sources"]) == 3
    assert len(merged["fragments"]) == 3
    assert "existing note" in merged["notes"]
    assert "legacy" in merged["connector_metadata"]["connector_versions"]
    assert "Federal Register Notices" in merged["connector_metadata"]["source_targets"]


def test_policy_feed_source_bundle_parses_into_structural_graph():
    payload = module.build_policy_feed_source_bundle(
        _load_json("research/templates/federal-register-bis-policy-feed-template-v1.json")
    )
    structural_parse = structural_module.build_structural_parse_from_source_bundle(payload)

    assert structural_parse["summary"]["entity_count"] >= 8
    assert structural_parse["summary"]["claim_count"] == 2
    assert structural_parse["summary"]["inference_count"] == 1
    relationship_types = {relationship["relationship_type"] for relationship in structural_parse["relationships"]}
    assert "AFFECTED_BY_EVENT" in relationship_types
    assert "CONSTRAINED_BY" in relationship_types

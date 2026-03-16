import sys
import types
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


SERVICES_ROOT = Path(__file__).resolve().parents[1] / "app" / "services"

app_pkg = types.ModuleType("app")
app_pkg.__path__ = []
services_pkg = types.ModuleType("app.services")
services_pkg.__path__ = [str(SERVICES_ROOT)]
sys.modules["app"] = app_pkg
sys.modules["app.services"] = services_pkg

for module_name in ["research_ontology", "structural_parser"]:
    full_name = f"app.services.{module_name}"
    if full_name not in sys.modules:
        module_spec = spec_from_file_location(full_name, SERVICES_ROOT / f"{module_name}.py")
        module = module_from_spec(module_spec)
        sys.modules[full_name] = module
        assert module_spec.loader is not None
        module_spec.loader.exec_module(module)

structural_parser = sys.modules["app.services.structural_parser"]


def test_build_structural_parse_from_curated_bundle():
    payload = {
        "sources": [
            {
                "source_id": "src_1",
                "source_class": "investor_post",
                "usage_mode": "hypothesis_seed",
            }
        ],
        "fragments": [
            {
                "fragment_id": "frag_1",
                "source_id": "src_1",
                "entity_hints": [
                    {"entity_type": "Theme", "canonical_name": "Robotics Supply Chain"},
                    {"entity_type": "System", "canonical_name": "Humanoid Robot"},
                    {"entity_type": "Subsystem", "canonical_name": "Actuation / Motion"},
                    {"entity_type": "Component", "canonical_name": "Permanent Magnet Motor"},
                    {"entity_type": "MaterialInput", "canonical_name": "Neodymium"},
                    {"entity_type": "ProcessLayer", "canonical_name": "Neodymium Processing"},
                    {
                        "entity_type": "PublicCompany",
                        "canonical_name": "MP",
                        "attributes": {"ticker": "MP"},
                    },
                ],
                "relationship_hints": [
                    {
                        "key": "actuation_part_of_robot",
                        "relationship_type": "PART_OF",
                        "source_type": "Subsystem",
                        "source_name": "Actuation / Motion",
                        "target_type": "System",
                        "target_name": "Humanoid Robot",
                    },
                    {
                        "key": "motor_part_of_actuation",
                        "relationship_type": "PART_OF",
                        "source_type": "Component",
                        "source_name": "Permanent Magnet Motor",
                        "target_type": "Subsystem",
                        "target_name": "Actuation / Motion",
                    },
                    {
                        "key": "motor_depends_on_neodymium",
                        "relationship_type": "DEPENDS_ON",
                        "source_type": "Component",
                        "source_name": "Permanent Magnet Motor",
                        "target_type": "MaterialInput",
                        "target_name": "Neodymium",
                    },
                    {
                        "key": "neodymium_processed_by_processing",
                        "relationship_type": "PROCESSED_BY",
                        "source_type": "MaterialInput",
                        "source_name": "Neodymium",
                        "target_type": "ProcessLayer",
                        "target_name": "Neodymium Processing",
                    },
                    {
                        "key": "processing_supplied_by_mp",
                        "relationship_type": "SUPPLIED_BY",
                        "source_type": "ProcessLayer",
                        "source_name": "Neodymium Processing",
                        "target_type": "PublicCompany",
                        "target_name": "MP",
                    },
                ],
                "claim_candidates": [
                    {
                        "claim_key": "robotics_ndpr_chain",
                        "claim_type": "material_or_processing_dependency",
                        "claim_text": "Actuation depends on permanent magnet motors, which depend on neodymium processing.",
                        "claim_kind": "inferential",
                        "entity_names": [
                            "Actuation / Motion",
                            "Permanent Magnet Motor",
                            "Neodymium",
                            "Neodymium Processing",
                        ],
                        "relationship_keys": [
                            "actuation_part_of_robot",
                            "motor_part_of_actuation",
                            "motor_depends_on_neodymium",
                            "neodymium_processed_by_processing",
                        ],
                    }
                ],
                "inference_candidates": [
                    {
                        "inference_key": "market_miss_processing",
                        "inference_type": "market_miss",
                        "statement": "The market may underweight neodymium processing relative to downstream robotics excitement.",
                        "claim_keys": ["robotics_ndpr_chain"],
                        "relationship_keys": [
                            "motor_depends_on_neodymium",
                            "neodymium_processed_by_processing",
                            "processing_supplied_by_mp",
                        ],
                    }
                ],
            }
        ],
    }

    output = structural_parser.build_structural_parse_from_source_bundle(payload)

    assert output["summary"]["entity_count"] >= 6
    assert output["summary"]["relationship_count"] == 5
    assert output["summary"]["claim_count"] == 1
    assert output["summary"]["evidence_link_count"] == 7
    assert output["summary"]["inference_count"] == 1

    entity_names = {entity["canonical_name"] for entity in output["entities"]}
    assert "Humanoid Robot" in entity_names
    assert "Neodymium Processing" in entity_names

    relationship_types = {rel["relationship_type"] for rel in output["relationships"]}
    assert {"PART_OF", "DEPENDS_ON", "PROCESSED_BY", "SUPPLIED_BY"}.issubset(
        relationship_types
    )

    claim = output["claims"][0]
    assert claim["claim_type"] == "material_or_processing_dependency"
    assert claim["relationship_refs"]

    inference = output["inferences"][0]
    assert inference["inference_type"] == "market_miss"
    assert inference["derived_from_claim_ids"] == [claim["claim_id"]]

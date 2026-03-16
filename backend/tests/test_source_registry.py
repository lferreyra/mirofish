import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "app" / "services" / "source_registry.py"
)
MODULE_SPEC = spec_from_file_location("source_registry", MODULE_PATH)
source_registry = module_from_spec(MODULE_SPEC)
assert MODULE_SPEC.loader is not None
sys.modules[MODULE_SPEC.name] = source_registry
MODULE_SPEC.loader.exec_module(source_registry)


def test_build_source_registry_from_docs():
    payload = source_registry.build_source_registry_from_docs()

    assert payload["registry_version"] == "v1"
    assert payload["row_count"] == len(payload["rows"])
    assert payload["row_count"] >= 40

    rows_by_name = {row["name"]: row for row in payload["rows"]}

    bis = rows_by_name["Bureau of Industry and Security (BIS), U.S. Department of Commerce"]
    assert bis["source_class"] == "government_policy_enforcement"
    assert bis["priority_tier"] == "P0"
    assert bis["role"] == "graph_forming"
    assert bis["canonical_url"] == "https://www.bis.doc.gov/"

    sec = rows_by_name["SEC EDGAR Database (10-K, 10-Q, 8-K, 20-F)"]
    assert sec["source_class"] == "company_filing"
    assert sec["suggested_ingestion_class"] == "company_filing"

    linked_in = rows_by_name["LinkedIn Jobs"]
    assert linked_in["source_class"] == "job_posting_hiring_signal"
    assert linked_in["requires_login"] is True

    market_data = rows_by_name["Public delayed options chain capture workflow"]
    assert market_data["source_class"] == "market_data_snapshot"
    assert market_data["access_mode"] == "local_workflow"

    assert Path(payload["generated_from"][0]).name == "2026-03-16-source-investigation-list-v1.md"


def test_build_source_acquisition_plan_for_robotics_parse():
    registry = source_registry.build_source_registry_from_docs()

    source_bundle = {
        "name": "robotics_actuation_source_bundle_v1",
        "theme": "robotics_supply_chain",
        "sources": [
            {
                "source_id": "src_alea_post",
                "source_class": "investor_post",
                "source_quality": "medium",
                "usage_mode": "exploration",
            }
        ],
        "fragments": [],
    }
    structural_parse = {
        "entities": [
            {"entity_type": "System", "canonical_name": "Humanoid Robot"},
            {"entity_type": "Subsystem", "canonical_name": "Actuation / Motion"},
            {"entity_type": "Component", "canonical_name": "Permanent Magnet Motor"},
            {"entity_type": "MaterialInput", "canonical_name": "Neodymium"},
            {"entity_type": "ExpressionCandidate", "canonical_name": "MP"},
            {"entity_type": "Geography", "canonical_name": "China"},
        ],
        "relationships": [
            {"relationship_type": "DEPENDS_ON"},
        ],
        "inferences": [
            {"inference_type": "market_miss", "summary": "actuation chain may be underfollowed"},
        ],
    }
    graduation = {
        "graduation_status": "exploratory_only",
        "gates": {
            "source_gate": False,
            "high_conviction_source_gate": False,
        },
    }

    plan = source_registry.build_source_acquisition_plan(
        registry,
        source_bundle=source_bundle,
        structural_parse=structural_parse,
        graduation=graduation,
        limit=5,
    )

    assert plan["plan_version"] == "v1"
    assert plan["project_domains"] == ["critical_materials", "robotics"]
    assert plan["gap_flags"]["needs_evidence_upgrade"] is True
    assert len(plan["top_recommendations"]) == 5
    assert any(
        row["source_class"] == "government_policy_enforcement"
        for row in plan["top_recommendations"]
    )
    assert any(
        row["source_class"] == "company_filing"
        for row in plan["top_recommendations"]
    )


def test_build_source_gap_report_uses_blocking_gates_and_next_steps():
    registry = source_registry.build_source_registry_from_docs()
    source_bundle = {
        "name": "robotics_actuation_source_bundle_v1",
        "theme": "robotics_supply_chain",
        "sources": [
            {
                "source_id": "src_alea_post",
                "source_class": "investor_post",
                "source_quality": "medium",
                "usage_mode": "exploration",
            }
        ],
    }
    structural_parse = {
        "entities": [
            {"entity_type": "PublicCompany", "canonical_name": "MP"},
            {"entity_type": "PublicCompany", "canonical_name": "NEO"},
            {"entity_type": "ExpressionCandidate", "canonical_name": "MP 2027 call"},
            {"entity_type": "Geography", "canonical_name": "China"},
        ],
        "relationships": [
            {"relationship_type": "DEPENDS_ON"},
        ],
        "inferences": [
            {"inference_type": "market_miss", "statement": "processing layer is underfollowed"},
        ],
    }
    graduation = {
        "graduation_status": "exploratory_only",
        "gates": {
            "source_gate": False,
            "structure_gate": True,
            "market_miss_gate": True,
            "expression_gate": True,
            "high_conviction_source_gate": False,
        },
    }
    plan = source_registry.build_source_acquisition_plan(
        registry,
        source_bundle=source_bundle,
        structural_parse=structural_parse,
        graduation=graduation,
        limit=8,
    )
    report = source_registry.build_source_gap_report(
        registry,
        source_bundle=source_bundle,
        structural_parse=structural_parse,
        graduation=graduation,
        source_acquisition_plan=plan,
    )

    assert report["next_promotion_target"] == "watchlist_candidate"
    assert "source_gate" in report["blocking_gates"]
    assert "high_conviction_source_gate" in report["blocking_gates"]
    assert "company_filing" in report["required_source_classes"]
    assert "industry_body_and_standards" in report["required_source_classes"]
    assert report["target_companies"][:2] == ["MP", "NEO"]
    assert any(
        step["source_class"] == "company_filing"
        for step in report["targeted_next_steps"]
    )


def test_build_source_monitor_plan_classifies_collection_modes():
    acquisition_plan = {
        "project_name": "robotics_actuation_source_bundle_v1",
        "top_recommendations": [
            {
                "source_target_id": "src_target_local_chain",
                "name": "LEAPS watchlist refresh workflow",
                "source_class": "market_data_snapshot",
                "recommendation": "monitor_weekly",
                "access_mode": "local_workflow",
                "requires_login": False,
                "ingestion_cadence": "daily or multi-weekly for watchlist names",
                "expected_artifact_types": ["price_snapshot"],
                "reasons": ["expression validation"],
            },
            {
                "source_target_id": "src_target_sec_edgar",
                "name": "SEC EDGAR Database (10-K, 10-Q, 8-K, 20-F)",
                "source_class": "company_filing",
                "recommendation": "monitor_weekly",
                "access_mode": "web_public",
                "requires_login": False,
                "ingestion_cadence": "filing-driven + daily watchlist monitoring",
                "expected_artifact_types": ["filing"],
                "reasons": ["company disclosure coverage"],
            },
            {
                "source_target_id": "src_target_linkedin_jobs",
                "name": "LinkedIn Jobs",
                "source_class": "job_posting_hiring_signal",
                "recommendation": "backlog_only",
                "access_mode": "login_required",
                "requires_login": True,
                "ingestion_cadence": "weekly scan",
                "expected_artifact_types": ["job_posting"],
                "reasons": ["supporting signal only"],
            },
        ],
        "monitoring_queue": [],
    }

    monitor_plan = source_registry.build_source_monitor_plan(acquisition_plan, max_tasks=10)

    assert monitor_plan["monitor_plan_version"] == "v1"
    assert monitor_plan["task_count"] == 3
    tasks = {task["source_target_id"]: task for task in monitor_plan["tasks"]}
    assert tasks["src_target_local_chain"]["automation_readiness"] == "automatable_now"
    assert tasks["src_target_local_chain"]["next_action"] == "run_local_capture"
    assert tasks["src_target_sec_edgar"]["automation_readiness"] == "web_monitor_ready"
    assert tasks["src_target_linkedin_jobs"]["automation_readiness"] == "blocked_login"

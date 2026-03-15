import json
from pathlib import Path

from app.models.research_project import (
    ResearchProjectManager,
    ResearchProjectStatus,
)


def test_research_project_manager_round_trip(tmp_path):
    original_dir = ResearchProjectManager.RESEARCH_PROJECTS_DIR
    ResearchProjectManager.RESEARCH_PROJECTS_DIR = str(tmp_path / "research_projects")
    try:
        project = ResearchProjectManager.create_project(
            name="HBM Research",
            thesis_intake={"theme": "HBM / advanced packaging"},
            tags=["ai", "memory"],
            focus_areas=["packaging", "hbm"],
        )

        assert project.status == ResearchProjectStatus.INTAKE_DEFINED

        ResearchProjectManager.save_claims_audit(
            project.research_project_id,
            [{"claim_text": "CoWoS is constrained", "status": "supported"}],
        )
        ResearchProjectManager.save_scorecards(
            project.research_project_id,
            [{"candidate_name": "CoWoS", "severity": {"score_0_to_100": 90.8}}],
        )
        ResearchProjectManager.save_summary(
            project.research_project_id,
            {"top_severity_layer": "CoWoS-class packaging"},
        )

        loaded = ResearchProjectManager.get_project(project.research_project_id)
        artifacts = ResearchProjectManager.get_artifacts(project.research_project_id)

        assert loaded is not None
        assert loaded.status == ResearchProjectStatus.REPORTED
        assert loaded.claims_audit_count == 1
        assert loaded.scorecard_count == 1
        assert artifacts["thesis_intake"]["theme"] == "HBM / advanced packaging"
        assert artifacts["summary"]["top_severity_layer"] == "CoWoS-class packaging"

        csv_path = (
            Path(ResearchProjectManager.RESEARCH_PROJECTS_DIR)
            / project.research_project_id
            / "artifacts"
            / "claims_audit.csv"
        )
        assert csv_path.exists()
        assert "claim_text" in csv_path.read_text(encoding="utf-8")

        meta_path = (
            Path(ResearchProjectManager.RESEARCH_PROJECTS_DIR)
            / project.research_project_id
            / "research_project.json"
        )
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        assert meta["ontology_name"] == "bottleneck_research"
    finally:
        ResearchProjectManager.RESEARCH_PROJECTS_DIR = original_dir

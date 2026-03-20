import tempfile
import threading
import time as pytime
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from flask import Flask

from app.api import graph as graph_api
from app.models.project import ProjectManager
from app.models.task import TaskManager, TaskStatus


class DummyOntologyGenerator:
    def generate(self, document_texts, simulation_requirement, additional_context=None):
        pytime.sleep(0.03)
        return {
            "entity_types": [{"name": "Investor", "attributes": []}],
            "edge_types": [{"name": "OWNS", "attributes": []}],
            "analysis_summary": "ok",
        }


class DummyGraphBuilderService:
    def __init__(self, api_key=None):
        self.api_key = api_key

    def build_graph_async(
        self,
        text,
        ontology,
        graph_name="MiroFish Graph",
        chunk_size=500,
        chunk_overlap=50,
        batch_size=3,
    ):
        task_manager = TaskManager()
        task_id = task_manager.create_task("graph_build")
        task_manager.update_task(
            task_id,
            status=TaskStatus.PROCESSING,
            progress=5,
            message="starting graph build",
        )

        def worker():
            pytime.sleep(0.04)
            task_manager.update_task(
                task_id,
                status=TaskStatus.PROCESSING,
                progress=50,
                message="halfway through graph build",
            )
            pytime.sleep(0.04)
            task_manager.update_task(
                task_id,
                status=TaskStatus.COMPLETED,
                progress=100,
                message="graph complete",
                result={"graph_id": "graph_test_123"},
            )

        threading.Thread(target=worker, daemon=True).start()
        return task_id


class DummySimulationManager:
    _states = {}

    def create_simulation(
        self,
        project_id,
        graph_id,
        enable_twitter=True,
        enable_reddit=True,
    ):
        state = SimpleNamespace(
            simulation_id="sim_test_123",
            project_id=project_id,
            graph_id=graph_id,
            status=graph_api.SimulationStatus.CREATED,
            error=None,
        )
        self._states[state.simulation_id] = state
        return state

    def prepare_simulation(
        self,
        simulation_id,
        simulation_requirement,
        document_text,
        defined_entity_types=None,
        use_llm_for_profiles=True,
        progress_callback=None,
        parallel_profile_count=3,
    ):
        if progress_callback:
            progress_callback("reading", 20, "Reading entities...")
        pytime.sleep(0.03)
        if progress_callback:
            progress_callback("generating_profiles", 60, "Generating profiles...")
        pytime.sleep(0.03)
        if progress_callback:
            progress_callback("generating_config", 100, "Preparation done")

        state = self._states[simulation_id]
        state.status = graph_api.SimulationStatus.READY
        return state

    def get_simulation(self, simulation_id):
        return self._states.get(simulation_id)

    def _save_simulation_state(self, state):
        self._states[state.simulation_id] = state


class DummySimulationRunner:
    @classmethod
    def start_simulation(
        cls,
        simulation_id,
        platform="parallel",
        max_rounds=None,
        enable_graph_memory_update=False,
        graph_id=None,
    ):
        return SimpleNamespace(simulation_id=simulation_id, runner_status="running")


class GraphPipelineEndpointTest(unittest.TestCase):
    def setUp(self):
        TaskManager()._tasks.clear()
        DummySimulationManager._states = {}
        self.temp_dir = tempfile.TemporaryDirectory()

        self.patches = [
            patch.object(ProjectManager, "PROJECTS_DIR", str(Path(self.temp_dir.name) / "projects")),
            patch.object(graph_api.Config, "ZEP_API_KEY", "test-key"),
            patch.object(graph_api, "OntologyGenerator", DummyOntologyGenerator),
            patch.object(graph_api, "GraphBuilderService", DummyGraphBuilderService),
            patch.object(graph_api, "SimulationManager", DummySimulationManager),
            patch.object(graph_api, "SimulationRunner", DummySimulationRunner),
            patch.object(graph_api.time, "sleep", lambda seconds: pytime.sleep(0.01)),
        ]

        for active_patch in self.patches:
            active_patch.start()
            self.addCleanup(active_patch.stop)

        app = Flask(__name__)
        app.testing = True
        app.register_blueprint(graph_api.graph_bp, url_prefix="/api/graph")
        self.client = app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def payload(self):
        return {
            "seed_data": {
                "properties": [
                    {
                        "address": "Karl Johans gate 1",
                        "city": "Oslo",
                        "propertyType": "Apartment",
                        "monthlyRentNok": 18000,
                        "currentValueNok": 5200000,
                        "sizeSqm": 68,
                    }
                ],
                "marketContext": {
                    "query": "Hva skjer med boligmarkedet i Oslo?",
                    "generatedAt": "2026-03-20T15:00:00Z",
                    "currency": "NOK",
                },
                "regulatoryContext": {"relevantSignals": []},
                "demographicData": {},
                "agentProfiles": [{"type": "Investor", "name": "Owner"}],
                "metadata": {"locale": "nb-NO"},
            },
            "config": {
                "agents": 4,
                "rounds": 6,
                "time_horizon": "10y",
                "scenario_description": "Test pipeline scenario",
                "entity_types": ["Investor", "Banker"],
            },
        }

    def test_provision_and_start_returns_immediately_and_completes(self):
        started_at = pytime.perf_counter()
        response = self.client.post("/api/graph/pipeline/provision-and-start", json=self.payload())
        elapsed = pytime.perf_counter() - started_at

        self.assertEqual(response.status_code, 200)
        self.assertLess(elapsed, 1.0)

        body = response.get_json()
        data = body["data"]
        self.assertEqual(data["message"], "Pipeline started")
        self.assertTrue(data["pipeline_id"])
        self.assertTrue(data["task_id"])

        pytime.sleep(0.05)
        in_flight = self.client.get(f"/api/graph/pipeline/status/{data['pipeline_id']}")
        self.assertEqual(in_flight.status_code, 200)
        in_flight_data = in_flight.get_json()["data"]
        self.assertIn(in_flight_data["status"], {"running", "completed"})
        self.assertGreaterEqual(in_flight_data["progress"], 10)

        deadline = pytime.time() + 2
        final_data = None
        while pytime.time() < deadline:
            status_response = self.client.get(f"/api/graph/pipeline/status/{data['pipeline_id']}")
            self.assertEqual(status_response.status_code, 200)
            final_data = status_response.get_json()["data"]
            if final_data["status"] == "completed":
                break
            pytime.sleep(0.02)

        self.assertIsNotNone(final_data)
        self.assertEqual(final_data["status"], "completed")
        self.assertEqual(final_data["phase"], "completed")
        self.assertEqual(final_data["progress"], 100)
        self.assertEqual(final_data["job_id"], "sim_test_123")
        self.assertEqual(final_data["result"]["job_id"], "sim_test_123")
        self.assertEqual(final_data["result"]["graph_id"], "graph_test_123")
        self.assertTrue(final_data["result"]["project_id"].startswith("proj_"))

    def test_pipeline_status_returns_404_for_unknown_pipeline(self):
        response = self.client.get("/api/graph/pipeline/status/does-not-exist")
        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.get_json()["success"])

    def test_provision_and_start_requires_seed_data(self):
        response = self.client.post("/api/graph/pipeline/provision-and-start", json={"config": {}})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "请提供 seed_data 对象")

    def test_provision_and_start_validates_rounds(self):
        response = self.client.post(
            "/api/graph/pipeline/provision-and-start",
            json={"seed_data": {}, "config": {"rounds": 0}},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "config.rounds 必须是正整数")

    def test_provision_and_start_validates_entity_types(self):
        response = self.client.post(
            "/api/graph/pipeline/provision-and-start",
            json={"seed_data": {}, "config": {"entity_types": "Investor"}},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "config.entity_types 必须是字符串数组")


if __name__ == "__main__":
    unittest.main()

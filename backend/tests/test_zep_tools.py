import importlib
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

services_pkg = types.ModuleType("app.services")
services_pkg.__path__ = [str(BACKEND_ROOT / "app" / "services")]
sys.modules.setdefault("app.services", services_pkg)

fake_zep_cloud = types.ModuleType("zep_cloud")
fake_zep_cloud.InternalServerError = type("InternalServerError", (Exception,), {})
sys.modules.setdefault("zep_cloud", fake_zep_cloud)

fake_zep_client_module = types.ModuleType("zep_cloud.client")
fake_zep_client_module.Zep = type("Zep", (), {})
sys.modules.setdefault("zep_cloud.client", fake_zep_client_module)

sys.modules.pop("app.services.zep_tools", None)
zep_tools_module = importlib.import_module("app.services.zep_tools")
ZepToolsService = zep_tools_module.ZepToolsService
SearchResult = zep_tools_module.SearchResult
Config = importlib.import_module("app.config").Config


class FakeZepError(Exception):
    def __init__(self, status_code=None, headers=None, body="error"):
        super().__init__(body)
        self.status_code = status_code
        self.headers = headers or {}
        self.body = body


class SequencedCall:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0

    def __call__(self, *args, **kwargs):
        self.calls += 1
        if not self._responses:
            raise AssertionError("No mocked responses left")
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class ZepToolsTests(unittest.TestCase):
    def build_service(self, llm_client=None):
        fake_client = SimpleNamespace(graph=SimpleNamespace())
        with patch("app.services.zep_tools.Zep", return_value=fake_client):
            service = ZepToolsService(api_key="zep-test-key", llm_client=llm_client)
        service.client = fake_client
        return service

    def test_rewrite_query_uses_llm_and_respects_retry_attempts(self):
        llm_client = SimpleNamespace(
            base_url="https://openrouter.ai/api/v1",
            chat_json=lambda **kwargs: {"search_query": "Target mens private label outlook 2026 2028 pricing demand risks"},
        )
        service = self.build_service(llm_client=llm_client)
        long_query = "Analyze the 2026–2028 outlook for Target’s men’s private label business with pricing, demand, competitive risk, assortment mix, and margin implications. " * 5

        with patch.object(Config, "ZEP_QUERY_REWRITE_RETRY_ATTEMPTS", 3):
            with patch.object(service.llm, "chat_json", wraps=service.llm.chat_json) as rewrite_mock:
                effective = service._rewrite_query_for_search(long_query, "simulation_requirement", "graph_search:test")

        self.assertLessEqual(len(effective), service.search_query_max_chars)
        self.assertIn("Target", effective)
        self.assertEqual(rewrite_mock.call_args.kwargs["retry_attempts"], 3)
        self.assertEqual(rewrite_mock.call_args.kwargs["request_label"], "zep_query_rewrite")

    def test_rewrite_query_prefers_longer_deterministic_fallback_when_llm_output_is_too_short(self):
        llm_client = SimpleNamespace(
            base_url="https://openrouter.ai/api/v1",
            chat_json=lambda **kwargs: {"search_query": "short rewrite"},
        )
        service = self.build_service(llm_client=llm_client)
        long_query = "Analyze the 2026–2028 outlook for Target’s men’s private label business with pricing, demand, competitive risk, assortment mix, and margin implications. " * 5
        fallback = "Target mens private label 2026 2028 price architecture demand margin Walmart Amazon brand equity hold vs cut strategy"

        with patch.object(service, "_compress_query_deterministically", return_value=fallback):
            effective = service._rewrite_query_for_search(long_query, "simulation_requirement", "graph_search:test")

        self.assertEqual(effective, fallback)
        self.assertGreater(len(effective), len("short rewrite"))

    def test_call_with_retry_does_not_retry_query_too_long(self):
        service = self.build_service(llm_client=SimpleNamespace(base_url="", chat_json=lambda **kwargs: {}))
        sequenced = SequencedCall([
            FakeZepError(status_code=400, body="message='query cannot be longer than 400 characters (max)'"),
        ])

        with patch("app.services.zep_tools.time.sleep", lambda *_: None):
            with self.assertRaises(FakeZepError):
                service._call_with_retry(
                    sequenced,
                    "graph_search:test",
                    query="x" * 500,
                    effective_query="y" * 350,
                    query_source="simulation_requirement",
                )

        self.assertEqual(sequenced.calls, 1)

    def test_call_with_retry_retries_rate_limit_three_times(self):
        service = self.build_service(llm_client=SimpleNamespace(base_url="", chat_json=lambda **kwargs: {}))
        sequenced = SequencedCall([
            FakeZepError(status_code=429, headers={"retry-after": "1"}, body="Rate limit exceeded"),
            FakeZepError(status_code=429, headers={"retry-after": "1"}, body="Rate limit exceeded"),
            {"ok": True},
        ])
        sleeps = []

        with patch("app.services.zep_tools.time.sleep", side_effect=lambda seconds: sleeps.append(seconds)):
            result = service._call_with_retry(
                sequenced,
                "graph_search:test",
                max_retries=3,
                query="query",
                effective_query="query",
                query_source="quick_search",
            )

        self.assertEqual(result, {"ok": True})
        self.assertEqual(sequenced.calls, 3)
        self.assertEqual(sleeps, [1.0, 1.0])

    def test_extract_error_metadata_does_not_treat_404_with_ratelimit_headers_as_rate_limit(self):
        service = self.build_service(llm_client=SimpleNamespace(base_url="", chat_json=lambda **kwargs: {}))

        metadata = service._extract_error_metadata(
            FakeZepError(
                status_code=404,
                headers={"x-ratelimit-remaining": "296", "x-ratelimit-reset": "1775776740"},
                body="{'message': 'not found'}",
            )
        )

        self.assertEqual(metadata["status_code"], 404)
        self.assertEqual(metadata["category"], "not_found")
        self.assertFalse(metadata["retryable"])

    def test_search_graph_falls_back_to_local_search_on_not_found(self):
        service = self.build_service(llm_client=SimpleNamespace(base_url="", chat_json=lambda **kwargs: {}))
        service.client.graph.search = lambda **kwargs: (_ for _ in ()).throw(
            FakeZepError(
                status_code=404,
                headers={"x-ratelimit-remaining": "296"},
                body="{'message': 'not found'}",
            )
        )
        fallback_result = SearchResult(
            facts=["fallback fact"],
            edges=[],
            nodes=[],
            query="Target Goodfellow fallback",
            total_count=1,
        )

        with patch.object(service, "_local_search", return_value=fallback_result) as local_search_mock:
            result = service.search_graph(
                graph_id="graph-1",
                query="Target Goodfellow fallback",
                limit=5,
                query_source="quick_search",
            )

        self.assertIs(result, fallback_result)
        local_search_mock.assert_called_once_with("graph-1", "Target Goodfellow fallback", 5, "edges")

    def test_get_simulation_context_returns_partial_context_on_rate_limit(self):
        service = self.build_service(llm_client=SimpleNamespace(base_url="", chat_json=lambda **kwargs: {}))

        with patch.object(
            service,
            "search_graph",
            side_effect=FakeZepError(status_code=429, headers={"retry-after": "5"}, body="Rate limit exceeded"),
        ):
            with patch.object(service, "get_graph_statistics", side_effect=AssertionError("should not fetch stats")):
                with patch.object(service, "get_all_nodes", side_effect=AssertionError("should not fetch nodes")):
                    context = service.get_simulation_context("graph-1", "Long simulation requirement")

        self.assertEqual(context["graph_statistics"]["total_nodes"], 0)
        self.assertEqual(context["related_facts"], [])
        self.assertEqual(context["entities"], [])


if __name__ == "__main__":
    unittest.main()

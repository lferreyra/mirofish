import sys
import unittest
import importlib
import tempfile
import types
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.config import Config
from app.utils.file_parser import FileParser
from app.utils.llm_client import (
    LLMClient,
    LLMEmptyResponseError,
    LLMJSONParseError,
    LLMResponseError,
    describe_llm_failure,
)

services_pkg = types.ModuleType("app.services")
services_pkg.__path__ = [str(BACKEND_ROOT / "app" / "services")]
sys.modules.setdefault("app.services", services_pkg)
ontology_generator_module = importlib.import_module("app.services.ontology_generator")
OntologyGenerator = ontology_generator_module.OntologyGenerator


def make_response(content=None, finish_reason="stop", choices_missing=False):
    if choices_missing:
        return SimpleNamespace(choices=None)
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content),
                finish_reason=finish_reason,
            )
        ]
    )


class SequencedCreate:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0

    def __call__(self, **kwargs):
        self.calls += 1
        if not self._responses:
            raise AssertionError("No mocked responses left")
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def build_client(responses):
    client = LLMClient(api_key="test-key", base_url="https://openrouter.ai/api/v1", model="test-model")
    create = SequencedCreate(responses)
    client.client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=create)
        )
    )
    return client, create


class LLMClientTests(unittest.TestCase):
    def test_describe_llm_failure_reports_structured_metadata(self):
        metadata = describe_llm_failure(
            LLMJSONParseError("bad json"),
            request_label="ontology.generate",
            model="test-model",
            base_url="https://openrouter.ai/api/v1",
        )

        self.assertEqual(metadata["failure_category"], "invalid_json")
        self.assertEqual(metadata["provider"], "openrouter")
        self.assertTrue(metadata["retryable"])
        self.assertEqual(metadata["request_label"], "ontology.generate")
        self.assertEqual(metadata["model"], "test-model")

    def test_chat_raises_clear_error_when_choices_missing(self):
        client, _ = build_client([make_response(choices_missing=True)])

        with self.assertRaisesRegex(LLMResponseError, "no choices"):
            client.chat(messages=[{"role": "user", "content": "hello"}], request_label="ontology.generate")

    def test_chat_retries_retryable_response_error_then_succeeds(self):
        client, create = build_client([
            make_response(choices_missing=True),
            make_response(content="Recovered response"),
        ])

        with patch("app.utils.llm_client.time.sleep", lambda *_: None):
            result = client.chat(
                messages=[{"role": "user", "content": "hello"}],
                request_label="report_generation",
                retry_attempts=2,
            )

        self.assertEqual(result, "Recovered response")
        self.assertEqual(create.calls, 2)

    def test_chat_json_retries_empty_content_then_raises(self):
        client, create = build_client([
            make_response(content=None),
            make_response(content=None),
        ])

        with patch("app.utils.llm_client.time.sleep", lambda *_: None):
            with self.assertRaisesRegex(LLMEmptyResponseError, "empty content|blank JSON content"):
                client.chat_json(
                    messages=[{"role": "user", "content": "hello"}],
                    request_label="ontology.generate",
                    retry_attempts=2,
                )

        self.assertEqual(create.calls, 2)

    def test_chat_json_retries_invalid_json_then_succeeds(self):
        client, create = build_client([
            make_response(content='{"entity_types": [}'),
            make_response(content='{"entity_types": [], "edge_types": [], "analysis_summary": "ok"}'),
        ])

        with patch("app.utils.llm_client.time.sleep", lambda *_: None):
            result = client.chat_json(
                messages=[{"role": "user", "content": "hello"}],
                request_label="ontology.generate",
                retry_attempts=2,
            )

        self.assertEqual(result["analysis_summary"], "ok")
        self.assertEqual(create.calls, 2)

    def test_chat_json_invalid_json_exhausts_retries(self):
        client, create = build_client([
            make_response(content='{"entity_types": [}'),
            make_response(content='{"entity_types": [}'),
            make_response(content='{"entity_types": [}'),
        ])

        with patch("app.utils.llm_client.time.sleep", lambda *_: None):
            with self.assertRaisesRegex(LLMJSONParseError, "JSON格式无效"):
                client.chat_json(
                    messages=[{"role": "user", "content": "hello"}],
                    request_label="ontology.generate",
                    retry_attempts=3,
                )

        self.assertEqual(create.calls, 3)

    def test_ontology_generator_retries_and_succeeds(self):
        client, create = build_client([
            make_response(content=None),
            make_response(content='{"entity_types": [], "edge_types": [], "analysis_summary": "generated"}'),
        ])
        generator = OntologyGenerator(llm_client=client)

        with patch("app.utils.llm_client.time.sleep", lambda *_: None):
            result = generator.generate(
                document_texts=["A university professor commented on the issue."],
                simulation_requirement="Generate ontology for a public-opinion simulation.",
            )

        self.assertEqual(result["analysis_summary"], "generated")
        self.assertIn("entity_types", result)
        self.assertIn("edge_types", result)
        self.assertEqual(create.calls, 2)

    def test_ontology_generator_uses_ontology_specific_config_defaults(self):
        captured = {}

        class FakeLLMClient:
            def __init__(self, **kwargs):
                captured["init_kwargs"] = kwargs

            def chat_json(self, **kwargs):
                captured["chat_json_kwargs"] = kwargs
                return {
                    "entity_types": [],
                    "edge_types": [],
                    "analysis_summary": "configured",
                }

        with patch.object(ontology_generator_module, "LLMClient", FakeLLMClient):
            with patch.object(Config, "ONTOLOGY_LLM_TIMEOUT_SECONDS", 777):
                with patch.object(Config, "ONTOLOGY_LLM_MAX_TOKENS", 4321):
                    with patch.object(Config, "ONTOLOGY_LLM_RETRY_ATTEMPTS", 5):
                        generator = OntologyGenerator()
                        result = generator.generate(
                            document_texts=["Short text"],
                            simulation_requirement="Simulate reactions.",
                        )

        self.assertEqual(result["analysis_summary"], "configured")
        self.assertEqual(captured["init_kwargs"]["timeout_seconds"], 777)
        self.assertEqual(captured["chat_json_kwargs"]["max_tokens"], 4321)
        self.assertEqual(captured["chat_json_kwargs"]["retry_attempts"], 5)
        self.assertEqual(captured["chat_json_kwargs"]["request_label"], "ontology.generate")

    def test_image_vision_uses_higher_configured_max_tokens(self):
        calls = []

        class FakeLLMClient:
            def analyze_image(self, **kwargs):
                calls.append(kwargs)
                return "Extracted image content"

        with tempfile.TemporaryDirectory() as tmp_dir:
            image_path = Path(tmp_dir) / "sample.png"
            image_path.write_bytes(b"fake-image")

            result = FileParser._extract_from_image_with_vision(str(image_path), FakeLLMClient())

        self.assertEqual(result, "[IMAGE_ATTACHMENT]\nExtracted image content")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["max_tokens"], Config.INPUT_LLM_IMAGE_MAX_TOKENS)

    def test_pdf_vision_uses_configured_max_tokens(self):
        calls = []

        class FakeLLMClient:
            def analyze_image(self, **kwargs):
                calls.append(kwargs)
                return "PDF visual summary"

        class FakePixmap:
            def tobytes(self, fmt):
                assert fmt == "png"
                return b"png-bytes"

        class FakePage:
            def get_text(self):
                return "PDF page text"

            def get_images(self, full=True):
                return [("image",)]

            def get_drawings(self):
                return []

            def get_pixmap(self, matrix=None, alpha=False):
                return FakePixmap()

        class FakeDoc:
            def __enter__(self):
                return [FakePage()]

            def __exit__(self, exc_type, exc, tb):
                return False

        fake_fitz = types.SimpleNamespace(
            open=lambda _: FakeDoc(),
            Matrix=lambda x, y: (x, y),
        )

        with patch.dict(sys.modules, {"fitz": fake_fitz}):
            text, vision_pages = FileParser._extract_from_pdf_with_vision("dummy.pdf", FakeLLMClient())

        self.assertIn("[PDF_VISION_PAGE_1]\nPDF visual summary", text)
        self.assertEqual(vision_pages, [1])
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["max_tokens"], Config.INPUT_LLM_PDF_VISION_MAX_TOKENS)


if __name__ == "__main__":
    unittest.main()

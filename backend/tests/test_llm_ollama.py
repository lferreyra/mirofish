"""Ollama backend tests. Stubs `requests.post` so no network is needed."""

import json
from types import SimpleNamespace

import pytest

from app.llm.base import BackendConfig, BackendError
from app.llm.ollama import OllamaBackend


def _ok_response(data):
    return SimpleNamespace(status_code=200, text="", json=lambda: data)


def _err_response(status, text="boom"):
    return SimpleNamespace(status_code=status, text=text, json=lambda: {})


@pytest.fixture
def backend():
    cfg = BackendConfig(
        name="local-fast", kind="ollama", model="qwen2.5:3b",
        base_url="http://localhost:11434",
    )
    return OllamaBackend(cfg)


def test_chat_happy_path_parses_token_counts(backend, monkeypatch):
    """Successful call maps prompt_eval_count / eval_count to token fields."""
    captured = {}

    def fake_post(url, json=None, timeout=None):
        captured["url"] = url
        captured["payload"] = json
        return _ok_response({
            "message": {"role": "assistant", "content": "hi there"},
            "prompt_eval_count": 11,
            "eval_count": 4,
            "done": True,
        })

    monkeypatch.setattr("requests.post", fake_post)

    response = backend.chat([{"role": "user", "content": "hi"}])

    assert response.text == "hi there"
    assert response.prompt_tokens == 11
    assert response.completion_tokens == 4
    assert response.cached_tokens == 0  # Ollama doesn't report cache hits
    assert captured["url"] == "http://localhost:11434/api/chat"
    assert captured["payload"]["model"] == "qwen2.5:3b"


def test_chat_json_mode_sets_format_field(backend, monkeypatch):
    """response_format={"type":"json_object"} becomes Ollama's `format: "json"`."""
    captured = {}

    def fake_post(url, json=None, timeout=None):
        captured["payload"] = json
        return _ok_response({"message": {"content": "{}"}, "done": True})

    monkeypatch.setattr("requests.post", fake_post)

    backend.chat(
        [{"role": "user", "content": "q"}],
        response_format={"type": "json_object"},
    )
    assert captured["payload"]["format"] == "json"


def test_chat_http_5xx_is_retryable(backend, monkeypatch):
    """Server errors should raise retryable BackendError."""

    def fake_post(url, json=None, timeout=None):
        return _err_response(500, "internal")

    monkeypatch.setattr("requests.post", fake_post)

    with pytest.raises(BackendError) as exc_info:
        backend.chat([{"role": "user", "content": "hi"}])

    assert exc_info.value.retryable is True
    assert exc_info.value.status == 500


def test_chat_network_exception_wrapped(backend, monkeypatch):
    """A connection error becomes a retryable `network` BackendError."""

    def fake_post(url, json=None, timeout=None):
        raise ConnectionError("refused")

    monkeypatch.setattr("requests.post", fake_post)

    with pytest.raises(BackendError) as exc_info:
        backend.chat([{"role": "user", "content": "hi"}])

    assert exc_info.value.code == "network"
    assert exc_info.value.retryable is True


def test_embed_calls_embeddings_endpoint_per_text(backend, monkeypatch):
    """Ollama's /api/embeddings is one-text-at-a-time; the backend must loop."""
    calls = []

    def fake_post(url, json=None, timeout=None):
        calls.append((url, json["prompt"]))
        return _ok_response({"embedding": [0.1, 0.2, 0.3]})

    monkeypatch.setattr("requests.post", fake_post)

    response = backend.embed(["alpha", "beta"], model="nomic-embed-text")

    assert len(response.vectors) == 2
    assert response.vectors[0] == [0.1, 0.2, 0.3]
    assert [c[1] for c in calls] == ["alpha", "beta"]
    assert all(c[0].endswith("/api/embeddings") for c in calls)

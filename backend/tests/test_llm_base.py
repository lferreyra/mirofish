"""Smoke tests for the LLMBackend abstract base + response types."""

import pytest

from app.llm.base import BackendConfig, BackendError, LLMBackend, LLMResponse, Role


class _StubBackend(LLMBackend):
    """Concrete subclass used to exercise `complete()` and `stream_chat()` defaults."""

    def chat(self, messages, *, temperature=0.7, max_tokens=4096, response_format=None,
            stop=None, cache_key=None, **kwargs):
        return LLMResponse(
            text="hello " + messages[-1]["content"],
            model=self.model,
            backend=self.name,
            prompt_tokens=7,
            completion_tokens=3,
            latency_ms=1.0,
        )


@pytest.fixture
def stub():
    cfg = BackendConfig(name="stub", kind="stub", model="m", provider="test")
    return _StubBackend(cfg)


def test_complete_builds_messages_from_system_and_prompt(stub):
    """`complete()` should combine system+user into the messages list."""
    response = stub.complete("world", system="be nice")
    assert response.text == "hello world"
    assert response.total_tokens == 10


def test_stream_chat_default_emits_single_fragment(stub):
    """The default stream_chat yields the full text once — a valid no-streaming fallback."""
    chunks = list(stub.stream_chat([{"role": "user", "content": "x"}]))
    assert chunks == ["hello x"]


def test_embed_raises_not_implemented_by_default(stub):
    """Backends that don't implement embedding should raise, not silently succeed."""
    with pytest.raises(NotImplementedError):
        stub.embed(["a"])


def test_backend_error_carries_code_and_backend_name():
    """BackendError's stringification exposes both backend and code for debugging."""
    exc = BackendError("rate_limited", "too fast", retryable=True, backend="openai")
    assert "openai" in str(exc)
    assert "rate_limited" in str(exc)
    assert exc.retryable is True
    assert exc.code == "rate_limited"


def test_role_enum_values():
    assert Role.FAST.value == "fast"
    assert Role("heavy") == Role.HEAVY

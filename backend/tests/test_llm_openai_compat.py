"""OpenAI-compat backend tests. Swaps in a fake OpenAI client so nothing hits
the network. Validates usage parsing, cache tagging, and error classification."""

from types import SimpleNamespace

import pytest

from app.llm.base import BackendConfig, BackendError
from app.llm.openai_compat import OpenAICompatBackend


def _fake_response(text="hi", prompt_tokens=10, completion_tokens=5, cached=0):
    """Build an object mimicking openai's chat.completions response."""
    choice = SimpleNamespace(
        message=SimpleNamespace(content=text),
        finish_reason="stop",
    )
    usage = {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "prompt_tokens_details": {"cached_tokens": cached},
    }
    return SimpleNamespace(choices=[choice], usage=usage)


class _FakeClient:
    """Minimal fake for openai.OpenAI used in tests."""

    def __init__(self, response=None, raise_exc=None):
        self._response = response
        self._raise = raise_exc
        self.last_kwargs = None

        outer = self

        class _ChatCompletions:
            def create(self, **kwargs):
                outer.last_kwargs = kwargs
                if outer._raise is not None:
                    raise outer._raise
                return outer._response

        self.chat = SimpleNamespace(completions=_ChatCompletions())


@pytest.fixture
def backend(monkeypatch):
    cfg = BackendConfig(
        name="test", kind="openai_compat", model="gpt-4o-mini",
        api_key="sk-x", base_url="https://api.openai.com/v1", provider="openai",
    )
    b = OpenAICompatBackend(cfg)
    return b


def test_chat_happy_path_parses_usage(backend):
    """A successful call returns text + token counts sourced from `usage`."""
    client = _FakeClient(response=_fake_response(text="pong", prompt_tokens=42, cached=10))
    backend._client = client

    response = backend.chat([{"role": "user", "content": "ping"}])

    assert response.text == "pong"
    assert response.prompt_tokens == 42
    assert response.completion_tokens == 5
    assert response.cached_tokens == 10
    assert response.latency_ms >= 0.0
    assert response.backend == "test"


def test_chat_strips_think_blocks(backend):
    """Some models wrap reasoning in <think>...</think>; the backend must strip them."""
    client = _FakeClient(response=_fake_response(text="<think>reasoning</think>final answer"))
    backend._client = client

    response = backend.chat([{"role": "user", "content": "q"}])
    assert response.text == "final answer"


def test_chat_forwards_prompt_cache_key_for_openai(backend):
    """OpenAI provider should see `prompt_cache_key` forwarded when a cache_key is given."""
    client = _FakeClient(response=_fake_response())
    backend._client = client

    backend.chat([{"role": "user", "content": "hi"}], cache_key="persona.individual")

    assert client.last_kwargs["prompt_cache_key"] == "persona.individual"


def test_chat_does_not_forward_cache_key_for_groq():
    """Providers without prompt_cache_key support should not see the hint leaked through."""
    cfg = BackendConfig(
        name="test", kind="openai_compat", model="llama",
        api_key="x", base_url="https://api.groq.com/openai/v1", provider="groq",
    )
    backend = OpenAICompatBackend(cfg)
    client = _FakeClient(response=_fake_response())
    backend._client = client

    backend.chat([{"role": "user", "content": "hi"}], cache_key="k")

    assert "prompt_cache_key" not in client.last_kwargs


def test_chat_tags_anthropic_system_message_with_cache_control():
    """Anthropic needs cache_control on the system message to actually cache prefix."""
    cfg = BackendConfig(
        name="anth", kind="openai_compat", model="claude-haiku",
        api_key="x", base_url="https://api.anthropic.com/v1", provider="anthropic",
    )
    backend = OpenAICompatBackend(cfg)
    client = _FakeClient(response=_fake_response())
    backend._client = client

    backend.chat([
        {"role": "system", "content": "platform rules"},
        {"role": "user", "content": "go"},
    ])

    sent = client.last_kwargs["messages"]
    assert sent[0]["role"] == "system"
    assert sent[0]["content"][0]["cache_control"] == {"type": "ephemeral"}


def test_chat_wraps_provider_exceptions_in_backend_error(backend):
    """An SDK exception becomes a BackendError with classification + retryable flag."""

    class _RateLimitError(Exception):
        pass

    client = _FakeClient(raise_exc=_RateLimitError("rate_limit: 429 too fast"))
    backend._client = client

    with pytest.raises(BackendError) as exc_info:
        backend.chat([{"role": "user", "content": "hi"}])

    err = exc_info.value
    assert err.code == "rate_limited"
    assert err.retryable is True


def test_chat_auth_error_is_not_retryable(backend):
    """401/auth errors must not be retried — they'd burn budget for nothing."""

    class _AuthError(Exception):
        pass

    client = _FakeClient(raise_exc=_AuthError("unauthorized: 401"))
    backend._client = client

    with pytest.raises(BackendError) as exc_info:
        backend.chat([{"role": "user", "content": "hi"}])

    assert exc_info.value.retryable is False

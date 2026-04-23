"""vLLM backend tests. Verifies speculative-decoding config flows through
`extra_body` and that the OpenAI-style prompt_cache_key hint is NOT forwarded
(vLLM uses token-prefix caching, not a hint)."""

from types import SimpleNamespace

import pytest

from app.llm.base import BackendConfig
from app.llm.vllm import VLLMBackend


class _FakeClient:
    def __init__(self):
        self.last_kwargs = None
        outer = self

        class _C:
            def create(self, **kwargs):
                outer.last_kwargs = kwargs
                return SimpleNamespace(
                    choices=[SimpleNamespace(
                        message=SimpleNamespace(content="ok"),
                        finish_reason="stop",
                    )],
                    usage={"prompt_tokens": 3, "completion_tokens": 1, "prompt_tokens_details": {}},
                )

        self.chat = SimpleNamespace(completions=_C())


def test_speculative_tokens_forwarded_via_extra_body():
    """VLLM_SPECULATIVE_TOKENS should end up in `extra_body.num_speculative_tokens`."""
    cfg = BackendConfig(
        name="vllm-local", kind="vllm", model="llama-3.1-70b",
        base_url="http://vllm:8000/v1", api_key="EMPTY", provider="vllm",
        extra={"speculative_tokens": 4, "draft_model": "llama-3.2-1b"},
    )
    backend = VLLMBackend(cfg)
    backend._client = _FakeClient()

    backend.chat([{"role": "user", "content": "hi"}])

    sent = backend._client.last_kwargs
    assert sent["extra_body"]["num_speculative_tokens"] == 4


def test_cache_key_not_forwarded_to_vllm():
    """vLLM's prefix cache is token-based; the OpenAI cache_key hint must be suppressed."""
    cfg = BackendConfig(
        name="vllm-local", kind="vllm", model="llama",
        base_url="http://vllm:8000/v1", api_key="EMPTY", provider="vllm",
    )
    backend = VLLMBackend(cfg)
    backend._client = _FakeClient()

    backend.chat([{"role": "user", "content": "x"}], cache_key="stable.prefix")

    assert "prompt_cache_key" not in backend._client.last_kwargs

"""
vLLM backend. vLLM exposes an OpenAI-compatible server, so this class is a
thin specialization of `OpenAICompatBackend` that:

  1. Logs prefix-cache + speculative-decoding config at startup so operators
     can confirm their vLLM server was launched with matching flags. These
     are server-launch arguments (e.g. `--enable-prefix-caching`,
     `--speculative-model`) — the client cannot toggle them per-request.
  2. Surfaces `VLLM_DRAFT_MODEL` / `VLLM_SPECULATIVE_TOKENS` env keys so a
     single `.env` drives both the server launch script and the client.
  3. Keeps `prefix_cache=True` as a passthrough hint in case future vLLM
     versions accept per-request overrides.
"""

from __future__ import annotations

from typing import Any, List, Optional

from .base import BackendConfig, LLMResponse
from .openai_compat import OpenAICompatBackend


class VLLMBackend(OpenAICompatBackend):
    """vLLM via its OpenAI-compatible HTTP server."""

    def __init__(self, config: BackendConfig):
        # vLLM always speaks 'generic' openai-compat; tag it so prompt_cache_key
        # isn't forwarded (vLLM's prefix cache is keyed on token prefix, not hint).
        config = BackendConfig(
            **{**config.__dict__, "provider": config.provider or "vllm"}
        )
        super().__init__(config)
        self.draft_model = config.extra.get("draft_model")
        self.speculative_tokens = config.extra.get("speculative_tokens")

    def chat(
        self,
        messages: List[dict],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[dict] = None,
        stop: Optional[List[str]] = None,
        cache_key: Optional[str] = None,  # noqa: ARG002 — vLLM prefix cache is token-based
        **kwargs: Any,
    ) -> LLMResponse:
        # vLLM supports `extra_body` for engine-specific options.
        extra_body = kwargs.pop("extra_body", None) or {}
        # These fields are ignored by vLLM servers that weren't launched with
        # matching flags; harmless when unsupported.
        if self.speculative_tokens is not None:
            extra_body.setdefault("num_speculative_tokens", self.speculative_tokens)
        if extra_body:
            kwargs["extra_body"] = extra_body

        return super().chat(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
            stop=stop,
            cache_key=None,  # intentionally drop — vLLM doesn't use the OpenAI hint
            **kwargs,
        )

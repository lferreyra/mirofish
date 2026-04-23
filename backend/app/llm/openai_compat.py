"""
OpenAI-SDK-compatible backend. Covers OpenAI, Anthropic (via their
OpenAI-compat layer), Together, DeepInfra, Groq, Fireworks, and any other
endpoint that speaks the OpenAI chat-completions API.

Prompt caching:
  * openai    -> ``prompt_cache_key`` top-level parameter (OpenAI-native cache hint)
  * anthropic -> automatic for prompts >=1024 tokens; system messages are
                 tagged via ``cache_control`` in extra_body for aggressive reuse
  * groq/together/deepinfra/fireworks -> best-effort; ignored if unsupported

Token accounting is read directly from the response `usage` object. When the
provider reports cached tokens (OpenAI: ``usage.prompt_tokens_details.cached_tokens``;
Anthropic: ``usage.cache_read_input_tokens``) it's surfaced as `cached_tokens`.
"""

from __future__ import annotations

import re
from typing import Any, Iterator, List, Optional

from .base import (
    BackendConfig,
    BackendError,
    EmbeddingResponse,
    LLMBackend,
    LLMResponse,
)

# Known providers whose prompt_cache_key hint actually does something.
_PROMPT_CACHE_KEY_PROVIDERS = {"openai", "azure"}
_ANTHROPIC_PROVIDERS = {"anthropic"}

# Strip <think>...</think> reasoning blocks that some models emit inside content.
_THINK_RE = re.compile(r"<think>[\s\S]*?</think>", re.IGNORECASE)


def _parse_usage(usage: Any) -> tuple[int, int, int]:
    """Return (prompt_tokens, completion_tokens, cached_tokens) from a usage
    object whose shape varies by provider."""
    if usage is None:
        return 0, 0, 0
    # Pydantic model -> dict; dict stays dict.
    if hasattr(usage, "model_dump"):
        u = usage.model_dump()
    elif isinstance(usage, dict):
        u = usage
    else:
        u = {}

    prompt = int(u.get("prompt_tokens", 0) or 0)
    completion = int(u.get("completion_tokens", 0) or 0)

    cached = 0
    details = u.get("prompt_tokens_details") or {}
    if isinstance(details, dict):
        cached = int(details.get("cached_tokens", 0) or 0)
    if not cached:
        cached = int(u.get("cache_read_input_tokens", 0) or 0)

    return prompt, completion, cached


class OpenAICompatBackend(LLMBackend):
    """OpenAI-SDK-shaped backend. Instantiates `openai.OpenAI` on demand."""

    def __init__(self, config: BackendConfig):
        super().__init__(config)
        self.provider = (config.provider or "generic").lower()
        self._client = None  # lazy init — avoids import at module load

    def _client_instance(self):
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise BackendError(
                    "openai_sdk_missing",
                    "openai package is required for openai_compat backends",
                    retryable=False,
                    backend=self.name,
                ) from exc
            kwargs: dict = {"api_key": self.config.api_key}
            if self.config.base_url:
                kwargs["base_url"] = self.config.base_url
            self._client = OpenAI(**kwargs)
        return self._client

    # --------------------------------------------------------------- chat
    def chat(
        self,
        messages: List[dict],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[dict] = None,
        stop: Optional[List[str]] = None,
        cache_key: Optional[str] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        start = self._now_ms()
        client = self._client_instance()

        req: dict = {
            "model": self.model,
            "messages": self._maybe_tag_cache(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format is not None:
            req["response_format"] = response_format
        if stop:
            req["stop"] = stop
        if cache_key and self.provider in _PROMPT_CACHE_KEY_PROVIDERS:
            req["prompt_cache_key"] = cache_key
        # passthrough extras (e.g. tools, tool_choice)
        for k, v in kwargs.items():
            if v is not None:
                req[k] = v

        try:
            response = client.chat.completions.create(**req)
        except Exception as exc:
            raise BackendError(
                self._classify(exc),
                str(exc),
                retryable=self._is_retryable(exc),
                backend=self.name,
            ) from exc

        choice = response.choices[0]
        content = (choice.message.content or "").strip()
        # Strip <think> blocks some models emit (MiniMax M2.5, some Qwen builds)
        content = _THINK_RE.sub("", content).strip()

        pt, ct, cached = _parse_usage(getattr(response, "usage", None))

        return LLMResponse(
            text=content,
            model=self.model,
            backend=self.name,
            prompt_tokens=pt,
            completion_tokens=ct,
            cached_tokens=cached,
            latency_ms=self._now_ms() - start,
            finish_reason=getattr(choice, "finish_reason", None),
            raw=response,
        )

    def stream_chat(
        self,
        messages: List[dict],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        cache_key: Optional[str] = None,
        **kwargs: Any,
    ) -> Iterator[str]:
        client = self._client_instance()
        req: dict = {
            "model": self.model,
            "messages": self._maybe_tag_cache(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if cache_key and self.provider in _PROMPT_CACHE_KEY_PROVIDERS:
            req["prompt_cache_key"] = cache_key
        for k, v in kwargs.items():
            if v is not None:
                req[k] = v

        try:
            stream = client.chat.completions.create(**req)
            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                fragment = getattr(delta, "content", None) or ""
                if fragment:
                    yield fragment
        except Exception as exc:
            raise BackendError(
                self._classify(exc),
                str(exc),
                retryable=self._is_retryable(exc),
                backend=self.name,
            ) from exc

    # ---------------------------------------------------------- embedding
    def embed(self, texts: List[str], *, model: Optional[str] = None) -> EmbeddingResponse:
        start = self._now_ms()
        target_model = model or self.config.embedding_model
        if not target_model:
            raise BackendError(
                "embed_model_missing",
                "no embedding_model configured for this backend",
                retryable=False,
                backend=self.name,
            )
        client = self._client_instance()
        try:
            response = client.embeddings.create(model=target_model, input=texts)
        except Exception as exc:
            raise BackendError(
                self._classify(exc),
                str(exc),
                retryable=self._is_retryable(exc),
                backend=self.name,
            ) from exc

        vectors = [item.embedding for item in response.data]
        pt, _, _ = _parse_usage(getattr(response, "usage", None))
        return EmbeddingResponse(
            vectors=vectors,
            model=target_model,
            backend=self.name,
            prompt_tokens=pt,
            latency_ms=self._now_ms() - start,
            raw=response,
        )

    # ---------------------------------------------------------- internals
    def _maybe_tag_cache(self, messages: List[dict]) -> List[dict]:
        """For Anthropic's OpenAI-compat layer, add cache_control to the
        system message so the stable prefix (simulation rules, platform
        description, action vocabulary) is actually cached by Anthropic.

        Other providers get the messages unchanged.
        """
        if self.provider not in _ANTHROPIC_PROVIDERS or not messages:
            return messages
        # Only tag the first system message; duplicates don't help and burn budget.
        tagged: List[dict] = []
        tagged_once = False
        for msg in messages:
            if not tagged_once and msg.get("role") == "system":
                content = msg.get("content")
                if isinstance(content, str):
                    tagged.append({
                        "role": "system",
                        "content": [
                            {
                                "type": "text",
                                "text": content,
                                "cache_control": {"type": "ephemeral"},
                            }
                        ],
                    })
                    tagged_once = True
                    continue
            tagged.append(msg)
        return tagged

    @staticmethod
    def _classify(exc: Exception) -> str:
        cls = type(exc).__name__.lower()
        if "ratelimit" in cls or "429" in str(exc):
            return "rate_limited"
        if "timeout" in cls:
            return "timeout"
        if "auth" in cls or "unauthorized" in cls or "401" in str(exc):
            return "auth_failed"
        if "connection" in cls or "network" in cls:
            return "network"
        return "api_error"

    @staticmethod
    def _is_retryable(exc: Exception) -> bool:
        msg = str(exc).lower()
        cls = type(exc).__name__.lower()
        if "auth" in cls or "unauthorized" in cls or "401" in msg or "403" in msg:
            return False
        if "invalid" in cls or "badrequest" in cls or "400" in msg:
            return False
        return True

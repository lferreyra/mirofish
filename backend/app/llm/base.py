"""
Abstract LLM backend interface shared by Ollama, vLLM, and OpenAI-compatible
cloud providers. Concrete backends live in sibling modules.

Design notes:
  * `chat()` is the primary entrypoint. `complete()` is a convenience that
    wraps a single user turn.
  * `stream_chat()` yields text fragments. Backends that cannot stream must
    synthesize a single fragment.
  * `embed()` is optional. Backends that cannot embed raise NotImplementedError,
    and the router surfaces that as `BackendError("embed_unsupported", ...)`.
  * Prompt caching is opaque to callers. A `cache_key` hint is accepted and
    forwarded if the backend supports it; otherwise ignored. Backends report
    `cached_tokens` in the response so the router can track hit rate.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterator, List, Optional


class Role(str, Enum):
    """Task roles the router resolves to backends."""
    FAST = "fast"          # NER, agent actions, routine decisions
    BALANCED = "balanced"  # post/comment generation
    HEAVY = "heavy"        # ReportAgent synthesis
    EMBED = "embed"        # vector embeddings


@dataclass
class LLMResponse:
    """Unified response across backends."""
    text: str
    model: str
    backend: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_tokens: int = 0
    latency_ms: float = 0.0
    finish_reason: Optional[str] = None
    raw: Optional[Any] = None  # provider-native response, for debugging

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass
class EmbeddingResponse:
    vectors: List[List[float]]
    model: str
    backend: str
    prompt_tokens: int = 0
    latency_ms: float = 0.0
    raw: Optional[Any] = None


class BackendError(Exception):
    """Uniform error type every backend raises on transport/API failure.

    The router uses `.retryable` to decide whether to attempt the same backend
    again, and `.code` to categorize for the fallback chain.
    """

    def __init__(
        self,
        code: str,
        message: str,
        *,
        retryable: bool = True,
        status: Optional[int] = None,
        backend: Optional[str] = None,
    ):
        super().__init__(f"[{backend or '?'}:{code}] {message}")
        self.code = code
        self.message = message
        self.retryable = retryable
        self.status = status
        self.backend = backend


@dataclass
class BackendConfig:
    """Everything a backend needs to instantiate. Opaque `extra` holds
    provider-specific knobs (e.g. speculative decoding params for vLLM)."""
    name: str                        # unique label, e.g. "cloud-openai-fast"
    kind: str                        # "openai_compat" | "ollama" | "vllm"
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    provider: Optional[str] = None   # openai/anthropic/together/deepinfra/groq/fireworks/generic
    embedding_model: Optional[str] = None
    extra: dict = field(default_factory=dict)


class LLMBackend(ABC):
    """Abstract backend. Subclasses implement transport; all wrap the same
    `LLMResponse` shape."""

    name: str
    model: str

    def __init__(self, config: BackendConfig):
        self.config = config
        self.name = config.name
        self.model = config.model

    @abstractmethod
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
        ...

    def complete(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """One-shot completion; builds messages from `system` + `prompt`."""
        messages: List[dict] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return self.chat(messages, **kwargs)

    def stream_chat(
        self,
        messages: List[dict],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        cache_key: Optional[str] = None,
        **kwargs: Any,
    ) -> Iterator[str]:
        """Default streaming implementation: emit the full response as one
        fragment. Backends that support real streaming override this."""
        response = self.chat(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            cache_key=cache_key,
            **kwargs,
        )
        yield response.text

    def embed(self, texts: List[str], *, model: Optional[str] = None) -> EmbeddingResponse:
        raise NotImplementedError(f"{self.name} does not support embeddings")

    @staticmethod
    def _now_ms() -> float:
        return time.perf_counter() * 1000.0

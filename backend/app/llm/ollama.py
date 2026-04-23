"""
Ollama backend. Talks to an Ollama server's native HTTP API
(`/api/chat`, `/api/embeddings`). Chosen over the `ollama` Python client so
the dependency stays on `requests`, which we already have transitively.

Prompt caching: Ollama keeps a KV cache per-model across requests automatically
(via `num_ctx`); no client-side hint is needed. We still surface `cached_tokens`
as 0 so the router's hit-rate metric is accurate (ollama doesn't report it).
"""

from __future__ import annotations

import json
from typing import Any, Iterator, List, Optional

from .base import (
    BackendConfig,
    BackendError,
    EmbeddingResponse,
    LLMBackend,
    LLMResponse,
)


_DEFAULT_BASE_URL = "http://localhost:11434"


class OllamaBackend(LLMBackend):
    """Local Ollama backend. No streaming SDK dependency."""

    def __init__(self, config: BackendConfig):
        super().__init__(config)
        self.base_url = (config.base_url or _DEFAULT_BASE_URL).rstrip("/")
        # Timeout lives in extra so operators can bump it for large models.
        self.timeout = float(config.extra.get("timeout_s", 120.0))

    # --------------------------------------------------------------- chat
    def chat(
        self,
        messages: List[dict],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[dict] = None,
        stop: Optional[List[str]] = None,
        cache_key: Optional[str] = None,  # noqa: ARG002 — accepted, not used
        **kwargs: Any,
    ) -> LLMResponse:
        start = self._now_ms()
        options: dict = {
            "temperature": temperature,
            "num_predict": max_tokens,
        }
        if stop:
            options["stop"] = stop

        payload: dict = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": options,
        }
        # Ollama supports `format: "json"` for constrained JSON output.
        if response_format and response_format.get("type") == "json_object":
            payload["format"] = "json"

        data = self._post("/api/chat", payload)
        content = (data.get("message") or {}).get("content", "")

        return LLMResponse(
            text=content.strip(),
            model=self.model,
            backend=self.name,
            prompt_tokens=int(data.get("prompt_eval_count", 0) or 0),
            completion_tokens=int(data.get("eval_count", 0) or 0),
            cached_tokens=0,
            latency_ms=self._now_ms() - start,
            finish_reason="stop" if data.get("done") else None,
            raw=data,
        )

    def stream_chat(
        self,
        messages: List[dict],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        cache_key: Optional[str] = None,  # noqa: ARG002
        **kwargs: Any,
    ) -> Iterator[str]:
        options: dict = {
            "temperature": temperature,
            "num_predict": max_tokens,
        }
        payload: dict = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": options,
        }
        try:
            import requests
            with requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout,
                stream=True,
            ) as resp:
                if resp.status_code != 200:
                    raise BackendError(
                        "api_error",
                        f"ollama {resp.status_code}: {resp.text[:200]}",
                        retryable=resp.status_code >= 500 or resp.status_code == 429,
                        status=resp.status_code,
                        backend=self.name,
                    )
                for line in resp.iter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    msg = chunk.get("message") or {}
                    fragment = msg.get("content", "")
                    if fragment:
                        yield fragment
                    if chunk.get("done"):
                        return
        except BackendError:
            raise
        except Exception as exc:
            raise BackendError(
                "network",
                str(exc),
                retryable=True,
                backend=self.name,
            ) from exc

    # ---------------------------------------------------------- embedding
    def embed(self, texts: List[str], *, model: Optional[str] = None) -> EmbeddingResponse:
        start = self._now_ms()
        target = model or self.config.embedding_model or self.model
        vectors: List[List[float]] = []
        total_prompt = 0
        for text in texts:
            data = self._post(
                "/api/embeddings",
                {"model": target, "prompt": text},
            )
            vectors.append(data["embedding"])
            total_prompt += int(data.get("prompt_eval_count", 0) or 0)
        return EmbeddingResponse(
            vectors=vectors,
            model=target,
            backend=self.name,
            prompt_tokens=total_prompt,
            latency_ms=self._now_ms() - start,
            raw=None,
        )

    # ---------------------------------------------------------- internals
    def _post(self, path: str, payload: dict) -> dict:
        try:
            import requests
        except ImportError as exc:
            raise BackendError(
                "requests_missing",
                "requests package is required for the ollama backend",
                retryable=False,
                backend=self.name,
            ) from exc
        try:
            resp = requests.post(
                f"{self.base_url}{path}",
                json=payload,
                timeout=self.timeout,
            )
        except Exception as exc:
            raise BackendError(
                "network",
                str(exc),
                retryable=True,
                backend=self.name,
            ) from exc

        if resp.status_code != 200:
            raise BackendError(
                "api_error",
                f"ollama {resp.status_code}: {resp.text[:200]}",
                retryable=resp.status_code >= 500 or resp.status_code == 429,
                status=resp.status_code,
                backend=self.name,
            )
        return resp.json()

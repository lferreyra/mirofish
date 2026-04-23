"""
ModelRouter — resolves task roles to backends and wraps every call with
retries, fallback chain, and token accounting.

Configuration (per role: fast / balanced / heavy / embed):

    LLM_ROLE_FAST_BACKEND     # openai_compat | ollama | vllm
    LLM_ROLE_FAST_MODEL
    LLM_ROLE_FAST_API_KEY
    LLM_ROLE_FAST_BASE_URL
    LLM_ROLE_FAST_PROVIDER    # openai|anthropic|together|deepinfra|groq|fireworks|generic
    LLM_ROLE_FAST_FALLBACKS   # comma-separated role names to try on failure

Mode preset:
    BACKEND_MODE=local        # all roles -> ollama with sensible defaults
    BACKEND_MODE=cloud        # honor per-role env; fall through to LLM_API_KEY/etc.
    BACKEND_MODE=custom       # purely per-role env

Back-compat:
    LLM_API_KEY / LLM_BASE_URL / LLM_MODEL_NAME act as a default for any role
    that doesn't specify its own. This keeps every existing caller working.

Failure handling:
    * Every backend call retries up to LLM_MAX_RETRIES (default 3) with
      exponential backoff + jitter. Non-retryable errors (auth, 400) skip retry.
    * If a role has fallbacks configured, the router walks them in order on
      exhaustion. Each fallback is logged at WARNING level.
"""

from __future__ import annotations

import os
import threading
from typing import Any, Iterator, List, Optional

from ..utils.logger import get_logger
from .accounting import get_tracker
from .base import (
    BackendConfig,
    BackendError,
    EmbeddingResponse,
    LLMBackend,
    LLMResponse,
    Role,
)
from .ollama import OllamaBackend
from .openai_compat import OpenAICompatBackend
from .vllm import VLLMBackend

logger = get_logger("mirofish.llm.router")

_BACKEND_REGISTRY = {
    "openai_compat": OpenAICompatBackend,
    "ollama": OllamaBackend,
    "vllm": VLLMBackend,
}

_LOCAL_DEFAULTS = {
    Role.FAST: ("ollama", "qwen2.5:3b"),
    Role.BALANCED: ("ollama", "qwen2.5:7b"),
    Role.HEAVY: ("ollama", "qwen2.5:14b"),
    Role.EMBED: ("ollama", "nomic-embed-text"),
}


def _env(role: Role, suffix: str) -> Optional[str]:
    return os.environ.get(f"LLM_ROLE_{role.value.upper()}_{suffix}")


def _truthy(s: Optional[str]) -> bool:
    return bool(s) and s.lower() in ("1", "true", "yes", "on")


def _build_backend_config(role: Role, mode: str) -> Optional[BackendConfig]:
    """Build a BackendConfig for `role`. Returns None if no config is resolvable
    (caller can decide whether absence is fatal — embeddings are often optional)."""
    kind = _env(role, "BACKEND")
    model = _env(role, "MODEL")
    api_key = _env(role, "API_KEY")
    base_url = _env(role, "BASE_URL")
    provider = _env(role, "PROVIDER")
    embedding_model = _env(role, "EMBEDDING_MODEL")

    # Fall back to BACKEND_MODE preset
    if not kind:
        if mode == "local":
            kind, default_model = _LOCAL_DEFAULTS[role]
            model = model or default_model
        else:
            # cloud / custom: use openai_compat with the legacy LLM_* keys
            kind = "openai_compat"

    # Inherit legacy LLM_API_KEY / LLM_BASE_URL / LLM_MODEL_NAME defaults
    if kind == "openai_compat":
        api_key = api_key or os.environ.get("LLM_API_KEY")
        base_url = base_url or os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
        model = model or os.environ.get("LLM_MODEL_NAME", "gpt-4o-mini")
        provider = provider or _infer_provider(base_url)
    if kind == "ollama":
        base_url = base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        provider = "ollama"
        if not model:
            return None
    if kind == "vllm":
        base_url = base_url or os.environ.get("VLLM_BASE_URL")
        api_key = api_key or os.environ.get("VLLM_API_KEY", "EMPTY")
        provider = provider or "vllm"
        if not (model and base_url):
            return None

    if role == Role.EMBED and not embedding_model:
        # Embed role uses `model` field for the embedding model
        embedding_model = model

    extra: dict = {}
    if kind == "vllm":
        draft = os.environ.get("VLLM_DRAFT_MODEL")
        spec_tokens = os.environ.get("VLLM_SPECULATIVE_TOKENS")
        if draft:
            extra["draft_model"] = draft
        if spec_tokens:
            try:
                extra["speculative_tokens"] = int(spec_tokens)
            except ValueError:
                logger.warning("VLLM_SPECULATIVE_TOKENS=%s not an int; ignoring", spec_tokens)

    return BackendConfig(
        name=f"{role.value}:{kind}:{provider or 'generic'}:{model}",
        kind=kind,
        model=model,
        api_key=api_key,
        base_url=base_url,
        provider=provider,
        embedding_model=embedding_model,
        extra=extra,
    )


def _infer_provider(base_url: Optional[str]) -> str:
    if not base_url:
        return "openai"
    u = base_url.lower()
    if "anthropic" in u:
        return "anthropic"
    if "groq" in u:
        return "groq"
    if "together" in u:
        return "together"
    if "deepinfra" in u:
        return "deepinfra"
    if "fireworks" in u:
        return "fireworks"
    if "openai" in u or "azure" in u:
        return "openai"
    return "generic"


def _instantiate(cfg: BackendConfig) -> LLMBackend:
    cls = _BACKEND_REGISTRY.get(cfg.kind)
    if cls is None:
        raise BackendError(
            "unknown_backend_kind",
            f"unsupported backend kind: {cfg.kind}",
            retryable=False,
        )
    return cls(cfg)


class ModelRouter:
    """Process-wide router. Use `ModelRouter.default()` for the env-derived
    instance; tests construct directly with explicit backends."""

    def __init__(
        self,
        backends: dict[Role, LLMBackend],
        *,
        fallbacks: Optional[dict[Role, List[Role]]] = None,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 30.0,
    ):
        self._backends = backends
        self._fallbacks = fallbacks or {}
        self._max_retries = max_retries
        self._initial_delay = initial_delay
        self._max_delay = max_delay
        self._tracker = get_tracker()

    # ------------------------------------------------------------- factory
    _default_lock = threading.Lock()
    _default_instance: Optional["ModelRouter"] = None

    @classmethod
    def default(cls) -> "ModelRouter":
        if cls._default_instance is not None:
            return cls._default_instance
        with cls._default_lock:
            if cls._default_instance is None:
                cls._default_instance = cls._build_from_env()
        return cls._default_instance

    @classmethod
    def reset_default(cls) -> None:
        with cls._default_lock:
            cls._default_instance = None

    @classmethod
    def _build_from_env(cls) -> "ModelRouter":
        mode = os.environ.get("BACKEND_MODE", "cloud").lower()
        backends: dict[Role, LLMBackend] = {}
        fallbacks: dict[Role, List[Role]] = {}

        for role in Role:
            cfg = _build_backend_config(role, mode)
            if cfg is None:
                # Embed role missing is acceptable; chat roles missing is a config error
                if role == Role.EMBED:
                    logger.info("No embed backend configured; embed() calls will raise.")
                    continue
                # Last resort: reuse balanced if it exists
                continue
            backends[role] = _instantiate(cfg)

            chain = _env(role, "FALLBACKS")
            if chain:
                resolved: List[Role] = []
                for token in chain.split(","):
                    token = token.strip().lower()
                    try:
                        resolved.append(Role(token))
                    except ValueError:
                        logger.warning("Unknown role %r in fallback chain for %s", token, role)
                fallbacks[role] = resolved

        # If chat roles were skipped (missing config), copy from BALANCED if present
        if Role.BALANCED in backends:
            for role in (Role.FAST, Role.HEAVY):
                backends.setdefault(role, backends[Role.BALANCED])

        try:
            max_retries = int(os.environ.get("LLM_MAX_RETRIES", "3"))
        except ValueError:
            max_retries = 3

        return cls(backends, fallbacks=fallbacks, max_retries=max_retries)

    # --------------------------------------------------------------- API
    def get(self, role: Role | str) -> LLMBackend:
        role = Role(role) if isinstance(role, str) else role
        backend = self._backends.get(role)
        if backend is None:
            raise BackendError(
                "no_backend_for_role",
                f"no backend configured for role={role.value}",
                retryable=False,
            )
        return backend

    def chat(
        self,
        role: Role | str,
        messages: List[dict],
        *,
        run_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        cache_key: Optional[str] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        return self._dispatch(
            role,
            "chat",
            run_id=run_id,
            agent_id=agent_id,
            invoke=lambda backend: backend.chat(
                messages, cache_key=cache_key, **kwargs
            ),
        )

    def stream_chat(
        self,
        role: Role | str,
        messages: List[dict],
        *,
        cache_key: Optional[str] = None,
        **kwargs: Any,
    ) -> Iterator[str]:
        # Streaming bypasses fallback; mid-stream switches mangle the output.
        backend = self.get(role)
        yield from backend.stream_chat(messages, cache_key=cache_key, **kwargs)

    def embed(
        self,
        texts: List[str],
        *,
        role: Role | str = Role.EMBED,
        run_id: Optional[str] = None,
    ) -> EmbeddingResponse:
        return self._dispatch(
            role,
            "embed",
            run_id=run_id,
            agent_id=None,
            invoke=lambda backend: backend.embed(texts),
        )

    # ----------------------------------------------------------- internals
    def _dispatch(
        self,
        role: Role | str,
        request_kind: str,
        *,
        run_id: Optional[str],
        agent_id: Optional[str],
        invoke,
    ):
        role = Role(role) if isinstance(role, str) else role
        # Asking for a role with no primary backend is a config bug — fail loudly
        # rather than silently running the fallback chain.
        if role not in self._backends:
            raise BackendError(
                "no_backend_for_role",
                f"no backend configured for role={role.value}",
                retryable=False,
            )
        chain: List[Role] = [role] + self._fallbacks.get(role, [])
        last_error: Optional[Exception] = None
        for attempt_role in chain:
            backend = self._backends.get(attempt_role)
            if backend is None:
                logger.warning("Fallback skipped: no backend for role=%s", attempt_role)
                continue
            try:
                return self._call_with_retry(
                    backend, attempt_role, request_kind, run_id, agent_id, invoke
                )
            except BackendError as exc:
                last_error = exc
                if attempt_role != chain[-1]:
                    logger.warning(
                        "Backend %s failed (%s); falling back from role=%s",
                        backend.name, exc.code, attempt_role.value,
                    )
                continue
        # Exhausted everything
        if last_error is not None:
            raise last_error
        raise BackendError(
            "no_backend_attempted",
            f"no backends were callable for role={role.value}",
            retryable=False,
        )

    def _call_with_retry(
        self,
        backend: LLMBackend,
        role: Role,
        request_kind: str,
        run_id: Optional[str],
        agent_id: Optional[str],
        invoke,
    ):
        import random
        import time as _time

        delay = self._initial_delay
        last_exc: Optional[BackendError] = None
        for attempt in range(self._max_retries):
            with self._tracker.track(
                role=role.value,
                backend=backend.name,
                provider=backend.config.provider,
                model=backend.config.model,
                request_kind=request_kind,
                run_id=run_id,
                agent_id=agent_id,
            ) as record:
                try:
                    response = invoke(backend)
                except BackendError as exc:
                    last_exc = exc
                    # Phase-6: record the failed call in Prometheus too; status
                    # is the BackendError code so dashboards can group by cause.
                    _emit_metric(
                        role.value, backend.config.provider, backend.config.model,
                        status=exc.code, prompt=0, completion=0, cached=0,
                    )
                    if not exc.retryable or attempt == self._max_retries - 1:
                        raise
                    # else fall through to backoff after the `with` exits (re-raised below)
                else:
                    # populate accounting from response
                    if isinstance(response, LLMResponse):
                        record.prompt_tokens = response.prompt_tokens
                        record.completion_tokens = response.completion_tokens
                        record.cached_tokens = response.cached_tokens
                        record.latency_ms = response.latency_ms
                        _emit_metric(
                            role.value, backend.config.provider, backend.config.model,
                            status="ok",
                            prompt=response.prompt_tokens,
                            completion=response.completion_tokens,
                            cached=response.cached_tokens,
                        )
                    elif isinstance(response, EmbeddingResponse):
                        record.prompt_tokens = response.prompt_tokens
                        record.latency_ms = response.latency_ms
                        _emit_metric(
                            role.value, backend.config.provider, backend.config.model,
                            status="ok",
                            prompt=response.prompt_tokens, completion=0, cached=0,
                        )
                    return response

            # If we got here, the call raised a retryable BackendError; back off and retry.
            sleep_for = min(delay, self._max_delay) * (0.5 + random.random())
            logger.warning(
                "Retrying %s on %s after %.1fs (attempt %d/%d): %s",
                request_kind, backend.name, sleep_for, attempt + 1, self._max_retries,
                last_exc.message if last_exc else "?",
            )
            _time.sleep(sleep_for)
            delay *= 2.0

        # Defensive — should not reach here
        if last_exc is not None:
            raise last_exc
        raise BackendError("unknown", "retry loop exited unexpectedly", retryable=False)


# Thin wrapper so the router doesn't hard-depend on the observability package
# being importable (keeps unit-test startup fast and lets CI skip installing
# prometheus_client).
def _emit_metric(role, provider, model, *, status, prompt, completion, cached) -> None:
    try:
        from ..observability import observe_llm_call
        observe_llm_call(
            role=role, provider=provider, model=model, status=status,
            prompt_tokens=prompt, completion_tokens=completion, cached_tokens=cached,
        )
    except Exception:
        # Metrics should never interfere with the actual LLM path.
        pass

"""
OpenRouter runtime helpers.

Provides:
1. pooled OpenRouter API key discovery from environment variables
2. round-robin request distribution with failure-based key failover
3. a lightweight OpenAI client patch so OpenRouter-backed clients can
   transparently rotate keys across requests and on retryable failures
"""

from __future__ import annotations

import functools
import json
import os
import threading
import time
from typing import Any, Callable, Optional

from .logger import get_logger

logger = get_logger("mirofish.openrouter")

_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
_DEFAULT_COOLDOWN_SECONDS = int(os.environ.get("OPENROUTER_KEY_COOLDOWN_SECONDS", "90"))
_ROTATABLE_STATUS_CODES = {401, 402, 429, 500, 502, 503, 504}
_ROTATABLE_TEXT_HINTS = (
    "credit",
    "credits",
    "quota",
    "rate limit",
    "ratelimit",
    "too many requests",
    "provider unavailable",
    "upstream",
    "temporarily unavailable",
    "server error",
    "authentication",
    "invalid api key",
    "api key",
)
_NON_ROTATABLE_403_HINTS = (
    "moderation",
    "flagged",
    "safety",
    "policy",
    "unsafe",
    "content",
)
_ROTATABLE_403_HINTS = (
    "api key",
    "authentication",
    "authorization",
    "scope",
    "provider",
    "forbidden",
)
_CONNECTION_ERROR_CLASS_NAMES = {
    "apiconnectionerror",
    "apitimeouterror",
    "connecterror",
    "connecttimeout",
    "readtimeout",
    "remotedisconnected",
}
_CONNECTION_ERROR_TEXT_HINTS = (
    "connection error",
    "connection aborted",
    "connection reset",
    "connection refused",
    "remote end closed connection",
    "timed out",
    "timeout",
    "temporary failure in name resolution",
    "dns",
)
_MALFORMED_RESPONSE_CLASS_NAMES = {
    "jsondecodeerror",
}

_POOL_SINGLETON: Optional["OpenRouterKeyPool"] = None
_POOL_LOCK = threading.Lock()
_PATCH_INSTALLED = False
_PATCH_LOCK = threading.Lock()


def classify_openrouter_error(exc: Exception) -> str:
    """Classify an OpenRouter error for compact diagnostic logging."""
    status_code = getattr(exc, "status_code", None)
    error_text = _extract_error_text(exc)

    if status_code == 429 and "free plan" in error_text:
        return "free_plan_rate_limit"
    if status_code == 429 or any(hint in error_text for hint in ("rate limit", "ratelimit", "too many requests")):
        return "rate_limit"
    if status_code == 402 or any(hint in error_text for hint in ("credit", "credits", "quota")):
        return "quota_or_credit_exhausted"
    if status_code in {500, 502, 503, 504} or any(hint in error_text for hint in ("provider unavailable", "upstream", "temporarily unavailable", "server error")):
        return "provider_unavailable"
    if _is_connection_failure(exc, error_text):
        return "connection_error"
    if _is_malformed_response_failure(exc):
        return "malformed_provider_response"
    if status_code == 403:
        if any(hint in error_text for hint in _NON_ROTATABLE_403_HINTS):
            return "non_rotatable_403"
        if any(hint in error_text for hint in _ROTATABLE_403_HINTS):
            return "auth_error"
    if status_code == 401 or any(hint in error_text for hint in ("authentication", "invalid api key", "api key", "authorization", "scope")):
        return "auth_error"
    return "unknown_openrouter_error"


def is_openrouter_base_url(base_url: Optional[str]) -> bool:
    """Return True when the configured base URL points to OpenRouter."""
    if not base_url:
        return False
    return "openrouter.ai" in str(base_url).strip().lower()


def get_default_openrouter_base_url() -> str:
    return _OPENROUTER_BASE_URL


def get_configured_openrouter_api_keys(
    include_llm_fallback: bool = True,
    reverse: bool = False,
) -> list[str]:
    """
    Collect configured OpenRouter keys in priority order.

    Supported variables:
    - OPENROUTER_API_KEY
    - OPENROUTER_API_KEY1..N
    - OPENROUTER_API_KEYS (comma/newline separated)
    - LLM_API_KEY (only as a last-resort compatibility fallback)
    """
    ordered_keys: list[str] = []
    seen: set[str] = set()

    def add_key(value: Optional[str]):
        if not value:
            return
        key = str(value).strip()
        if not key or key in seen:
            return
        seen.add(key)
        ordered_keys.append(key)

    add_key(os.environ.get("OPENROUTER_API_KEY"))

    numbered_keys: list[tuple[int, str]] = []
    for env_name, env_value in os.environ.items():
        if not env_name.startswith("OPENROUTER_API_KEY"):
            continue
        suffix = env_name.removeprefix("OPENROUTER_API_KEY")
        if not suffix.isdigit():
            continue
        numbered_keys.append((int(suffix), env_value))

    ordered_numbered_keys = sorted(numbered_keys, key=lambda item: item[0], reverse=reverse)
    for _, env_value in ordered_numbered_keys:
        add_key(env_value)

    combined_keys = os.environ.get("OPENROUTER_API_KEYS", "")
    if combined_keys:
        normalized = combined_keys.replace("\r", "\n").replace(",", "\n")
        for key in normalized.split("\n"):
            add_key(key)

    if include_llm_fallback and not ordered_keys:
        add_key(os.environ.get("LLM_API_KEY"))

    return ordered_keys


def get_primary_openrouter_api_key(reverse: bool = False) -> Optional[str]:
    keys = get_configured_openrouter_api_keys(reverse=reverse)
    return keys[0] if keys else None


def get_effective_llm_api_key(
    explicit_api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    reverse_openrouter_pool: bool = False,
) -> Optional[str]:
    """
    Resolve a single effective API key for compatibility checks.

    When OpenRouter is active and pooled keys exist, returns the first pooled key.
    Otherwise falls back to explicit_api_key or LLM_API_KEY.
    """
    if explicit_api_key:
        return explicit_api_key

    resolved_base_url = base_url or os.environ.get("LLM_BASE_URL", "")
    if is_openrouter_base_url(resolved_base_url):
        pooled_key = get_primary_openrouter_api_key(reverse=reverse_openrouter_pool)
        if pooled_key:
            return pooled_key

    return os.environ.get("LLM_API_KEY")


def configure_openrouter_runtime() -> bool:
    """
    Prepare the current process for OpenRouter pooled-key usage.

    - exposes the first pooled key as LLM_API_KEY when OpenRouter is active
    - installs OpenAI client monkey-patching exactly once
    """
    base_url = os.environ.get("LLM_BASE_URL", "")
    if not is_openrouter_base_url(base_url):
        return False

    pooled_key = get_primary_openrouter_api_key()
    if pooled_key and not os.environ.get("LLM_API_KEY"):
        os.environ["LLM_API_KEY"] = pooled_key

    install_openrouter_openai_patch()
    return bool(pooled_key)


def _extract_error_text(exc: Exception) -> str:
    parts: list[str] = []

    for attr in ("message", "body"):
        value = getattr(exc, attr, None)
        if not value:
            continue
        if isinstance(value, (dict, list)):
            try:
                parts.append(json.dumps(value, ensure_ascii=False))
            except Exception:
                parts.append(str(value))
        else:
            parts.append(str(value))

    response = getattr(exc, "response", None)
    if response is not None:
        for attr in ("text", "content"):
            value = getattr(response, attr, None)
            if value:
                parts.append(str(value))

    parts.append(str(exc))
    return " | ".join(part for part in parts if part).lower()


def _is_connection_failure(exc: Exception, error_text: Optional[str] = None) -> bool:
    if isinstance(exc, (ConnectionError, TimeoutError)):
        return True

    if type(exc).__name__.strip().lower() in _CONNECTION_ERROR_CLASS_NAMES:
        return True

    normalized_error_text = error_text if error_text is not None else _extract_error_text(exc)
    return any(hint in normalized_error_text for hint in _CONNECTION_ERROR_TEXT_HINTS)


def _is_malformed_response_failure(exc: Exception) -> bool:
    if isinstance(exc, json.JSONDecodeError):
        return True

    return type(exc).__name__.strip().lower() in _MALFORMED_RESPONSE_CLASS_NAMES


def should_rotate_openrouter_key(exc: Exception) -> tuple[bool, str]:
    """Decide whether a failure should trigger key rotation."""
    status_code = getattr(exc, "status_code", None)
    error_text = _extract_error_text(exc)

    if status_code in _ROTATABLE_STATUS_CODES:
        return True, f"status={status_code}"

    if _is_connection_failure(exc, error_text):
        return True, "connection-failure"

    if _is_malformed_response_failure(exc):
        return True, "malformed-response"

    if status_code == 403:
        if any(hint in error_text for hint in _NON_ROTATABLE_403_HINTS):
            return False, "403-content-policy"
        if any(hint in error_text for hint in _ROTATABLE_403_HINTS):
            return True, "403-authz"
        return False, "403-non-rotatable"

    if any(hint in error_text for hint in _ROTATABLE_TEXT_HINTS):
        return True, "error-text-match"

    return False, "non-rotatable"


class OpenRouterKeyPool:
    """Process-local OpenRouter API key pool."""

    def __init__(self, keys: list[str]):
        self._keys = list(keys)
        self._cursor = 0
        self._cooldowns: dict[int, float] = {}
        self._lock = threading.Lock()

    @property
    def size(self) -> int:
        return len(self._keys)

    @property
    def enabled(self) -> bool:
        return self.size > 0

    def first_key(self) -> Optional[str]:
        return self._keys[0] if self._keys else None

    def _is_available(self, index: int, now: float) -> bool:
        until = self._cooldowns.get(index, 0.0)
        return until <= now

    def _select_index(self, excluded: set[int]) -> Optional[int]:
        if not self._keys:
            return None

        now = time.time()
        with self._lock:
            start = self._cursor
            total = len(self._keys)

            for offset in range(total):
                idx = (start + offset) % total
                if idx in excluded:
                    continue
                if self._is_available(idx, now):
                    self._cursor = (idx + 1) % total
                    return idx

            for offset in range(total):
                idx = (start + offset) % total
                if idx in excluded:
                    continue
                self._cursor = (idx + 1) % total
                return idx

        return None

    def mark_failure(self, index: int, cooldown_seconds: int = _DEFAULT_COOLDOWN_SECONDS):
        with self._lock:
            self._cooldowns[index] = time.time() + max(1, cooldown_seconds)

    def call_with_failover(
        self,
        operation: Callable[[str], Any],
        operation_name: str = "OpenRouter request",
    ) -> Any:
        """
        Execute an operation with request-level round-robin and failover.

        Behavior:
        - choose a starting key in round-robin order
        - keep that key for the request unless a rotatable failure occurs
        - on rotatable failure, mark the failed key in cooldown and try the next key
        """
        if not self._keys:
            raise ValueError("No OpenRouter API keys configured")

        attempted: set[int] = set()
        last_error: Optional[Exception] = None

        while len(attempted) < len(self._keys):
            key_index = self._select_index(excluded=attempted)
            if key_index is None:
                break

            attempted.add(key_index)
            api_key = self._keys[key_index]
            logger.info(
                "%s OpenRouter attempt=%s/%s key#%s",
                operation_name,
                len(attempted),
                len(self._keys),
                key_index + 1,
            )

            try:
                result = operation(api_key)
                logger.info(
                    "%s OpenRouter success key#%s attempts_used=%s",
                    operation_name,
                    key_index + 1,
                    len(attempted),
                )
                return result
            except Exception as exc:
                last_error = exc
                should_rotate, reason = should_rotate_openrouter_key(exc)
                error_category = classify_openrouter_error(exc)
                exhausted = len(attempted) >= len(self._keys)
                if not should_rotate or exhausted:
                    logger.error(
                        "%s OpenRouter final_failure key#%s category=%s rotate_reason=%s exhausted=%s",
                        operation_name,
                        key_index + 1,
                        error_category,
                        reason,
                        exhausted,
                    )
                    raise

                self.mark_failure(key_index)
                logger.warning(
                    "%s OpenRouter rotate_from=key#%s category=%s rotate_reason=%s next_key_pending=true",
                    operation_name,
                    key_index + 1,
                    error_category,
                    reason,
                )

        if last_error is not None:
            logger.error(
                "%s OpenRouter all_keys_exhausted category=%s",
                operation_name,
                classify_openrouter_error(last_error),
            )
            raise last_error

        raise RuntimeError(f"{operation_name} failed before any OpenRouter key could be selected")


def get_openrouter_key_pool() -> OpenRouterKeyPool:
    global _POOL_SINGLETON
    if _POOL_SINGLETON is None:
        with _POOL_LOCK:
            if _POOL_SINGLETON is None:
                _POOL_SINGLETON = OpenRouterKeyPool(get_configured_openrouter_api_keys())
    return _POOL_SINGLETON


def _patch_client_create_method(client: Any, attr_path: tuple[str, ...], operation_name: str):
    target = client
    for attr in attr_path[:-1]:
        target = getattr(target, attr, None)
        if target is None:
            return

    method_name = attr_path[-1]
    original_method = getattr(target, method_name, None)
    if original_method is None or getattr(original_method, "_mirofish_openrouter_patched", False):
        return

    client_lock = threading.RLock()

    @functools.wraps(original_method)
    def wrapped(*args, **kwargs):
        pool = get_openrouter_key_pool()
        if not pool.enabled:
            return original_method(*args, **kwargs)

        def invoke(api_key: str):
            with client_lock:
                previous_key = getattr(client, "api_key", None)
                setattr(client, "api_key", api_key)
                try:
                    return original_method(*args, **kwargs)
                finally:
                    setattr(client, "api_key", previous_key)

        return pool.call_with_failover(invoke, operation_name=operation_name)

    wrapped._mirofish_openrouter_patched = True  # type: ignore[attr-defined]
    setattr(target, method_name, wrapped)


def _patch_openai_client_instance(client: Any):
    if getattr(client, "_mirofish_openrouter_client_patched", False):
        return

    base_url = getattr(client, "base_url", None)
    if not is_openrouter_base_url(str(base_url) if base_url is not None else ""):
        return

    if not get_openrouter_key_pool().enabled:
        return

    _patch_client_create_method(
        client,
        ("chat", "completions", "create"),
        "chat.completions.create",
    )
    _patch_client_create_method(
        client,
        ("responses", "create"),
        "responses.create",
    )
    setattr(client, "_mirofish_openrouter_client_patched", True)


def install_openrouter_openai_patch() -> bool:
    """Install OpenAI client monkey-patching exactly once per process."""
    global _PATCH_INSTALLED
    if _PATCH_INSTALLED:
        return True

    with _PATCH_LOCK:
        if _PATCH_INSTALLED:
            return True

        try:
            import openai  # type: ignore
        except ImportError:
            logger.warning("OpenAI SDK not installed yet; skipping OpenRouter runtime patch")
            return False

        openai_client_cls = getattr(openai, "OpenAI", None)
        if openai_client_cls is None:
            logger.warning("OpenAI SDK missing OpenAI client class; skipping OpenRouter runtime patch")
            return False

        if getattr(openai_client_cls, "_mirofish_openrouter_init_patched", False):
            _PATCH_INSTALLED = True
            return True

        original_init = openai_client_cls.__init__

        @functools.wraps(original_init)
        def patched_init(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            _patch_openai_client_instance(self)

        patched_init._mirofish_openrouter_init_patched = True  # type: ignore[attr-defined]
        openai_client_cls.__init__ = patched_init
        openai_client_cls._mirofish_openrouter_init_patched = True  # type: ignore[attr-defined]

        _PATCH_INSTALLED = True
        logger.info(
            "Installed OpenRouter runtime patch with %s pooled key(s)",
            get_openrouter_key_pool().size,
        )
        return True

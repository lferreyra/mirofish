"""Router tests — retry, fallback chain, accounting wiring."""

import pytest

from app.llm.base import (
    BackendConfig,
    BackendError,
    EmbeddingResponse,
    LLMBackend,
    LLMResponse,
    Role,
)
from app.llm.router import ModelRouter


class _ScriptedBackend(LLMBackend):
    """Backend that replays a scripted list of (result-or-exception) responses
    for each call. Used to simulate transient failures and fallback behavior."""

    def __init__(self, name, script):
        cfg = BackendConfig(name=name, kind="scripted", model="m", provider="test")
        super().__init__(cfg)
        self._script = list(script)
        self.calls = 0

    def chat(self, messages, **kwargs):
        self.calls += 1
        if not self._script:
            raise AssertionError(f"scripted backend {self.name} exhausted")
        item = self._script.pop(0)
        if isinstance(item, Exception):
            raise item
        return LLMResponse(
            text=item, model=self.model, backend=self.name,
            prompt_tokens=1, completion_tokens=1, latency_ms=0.1,
        )

    def embed(self, texts, *, model=None):
        return EmbeddingResponse(
            vectors=[[0.0] * 3 for _ in texts], model=model or "m",
            backend=self.name, prompt_tokens=len(texts),
        )


def test_happy_path_first_backend_succeeds():
    """A healthy backend returns on the first try; no retry, no fallback."""
    primary = _ScriptedBackend("primary", ["hello"])
    router = ModelRouter(backends={Role.FAST: primary})

    response = router.chat(Role.FAST, [{"role": "user", "content": "hi"}])

    assert response.text == "hello"
    assert primary.calls == 1


def test_retry_on_retryable_backend_error(monkeypatch):
    """First attempt raises a retryable error; second succeeds. No fallback triggered."""
    err = BackendError("rate_limited", "slow down", retryable=True, backend="primary")
    primary = _ScriptedBackend("primary", [err, "ok-after-retry"])
    router = ModelRouter(backends={Role.FAST: primary}, max_retries=3, initial_delay=0.0)

    # Neutralize the sleep in the retry loop so tests stay fast.
    monkeypatch.setattr("time.sleep", lambda *_args, **_kwargs: None)

    response = router.chat(Role.FAST, [{"role": "user", "content": "hi"}])

    assert response.text == "ok-after-retry"
    assert primary.calls == 2


def test_non_retryable_error_skips_retries(monkeypatch):
    """Auth failures shouldn't burn retries; they should fall through immediately."""
    err = BackendError("auth_failed", "401", retryable=False, backend="primary")
    primary = _ScriptedBackend("primary", [err])
    router = ModelRouter(backends={Role.FAST: primary}, max_retries=3, initial_delay=0.0)
    monkeypatch.setattr("time.sleep", lambda *_a, **_k: None)

    with pytest.raises(BackendError) as exc_info:
        router.chat(Role.FAST, [{"role": "user", "content": "hi"}])

    assert exc_info.value.code == "auth_failed"
    assert primary.calls == 1


def test_fallback_chain_tries_next_role_on_exhaustion(monkeypatch):
    """When primary exhausts retries, router walks to the fallback role."""
    # Primary raises a retryable error on every attempt
    err = BackendError("rate_limited", "nope", retryable=True, backend="primary")
    primary = _ScriptedBackend("primary", [err, err, err])
    fallback = _ScriptedBackend("fallback", ["recovered"])
    router = ModelRouter(
        backends={Role.FAST: primary, Role.BALANCED: fallback},
        fallbacks={Role.FAST: [Role.BALANCED]},
        max_retries=3, initial_delay=0.0,
    )
    monkeypatch.setattr("time.sleep", lambda *_a, **_k: None)

    response = router.chat(Role.FAST, [{"role": "user", "content": "hi"}])

    assert response.text == "recovered"
    assert primary.calls == 3
    assert fallback.calls == 1


def test_router_persists_accounting_for_successful_call():
    """Every successful call is recorded in the tracker with token counts."""
    primary = _ScriptedBackend("primary", ["x"])
    router = ModelRouter(backends={Role.FAST: primary})

    router.chat(Role.FAST, [{"role": "user", "content": "hi"}])

    rows = router._tracker._connect().execute(
        "SELECT role, backend, prompt_tokens, completion_tokens, status FROM llm_calls"
    ).fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "fast"
    assert rows[0][4] == "ok"


def test_missing_role_raises_no_backend_error():
    """Asking for a role with no backend configured must fail loudly."""
    router = ModelRouter(backends={})
    with pytest.raises(BackendError) as exc_info:
        router.chat(Role.FAST, [{"role": "user", "content": "hi"}])
    assert exc_info.value.code == "no_backend_for_role"


def test_embed_dispatches_to_embed_role():
    """embed() defaults to Role.EMBED; tokens land in the tracker."""
    embed_backend = _ScriptedBackend("emb", [])  # chat script unused
    router = ModelRouter(backends={Role.EMBED: embed_backend})

    response = router.embed(["a", "b", "c"])

    assert len(response.vectors) == 3
    rows = router._tracker._connect().execute(
        "SELECT role, request_kind, prompt_tokens FROM llm_calls"
    ).fetchall()
    assert rows[0] == ("embed", "embed", 3)

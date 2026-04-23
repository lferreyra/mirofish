"""Accounting tests — SQLite persistence, cost estimation, cache-hit rate."""

import pytest

from app.llm.accounting import LLMCallTracker, _estimate_cost


def test_cost_estimation_openai_gpt4o_mini():
    """Known provider+model uses the built-in price table."""
    cost = _estimate_cost("openai", "gpt-4o-mini", 1_000_000, 500_000, 0)
    # 1M input * $0.15 + 500k output * $0.60 / 1M = 0.15 + 0.30 = 0.45
    assert cost == pytest.approx(0.45, rel=1e-6)


def test_cost_estimation_cached_tokens_use_cached_rate():
    """Cached tokens should be billed at the cached-input rate, not full rate."""
    cost = _estimate_cost("openai", "gpt-4o-mini", 1_000_000, 0, 1_000_000)
    # All 1M cached -> 1M * $0.075 = 0.075
    assert cost == pytest.approx(0.075, rel=1e-6)


def test_cost_estimation_unknown_returns_none():
    """Unknown provider/model returns None so callers don't show bogus $0."""
    assert _estimate_cost("mystery", "mystery-xl", 100, 100, 0) is None


def test_cost_estimation_local_backend_free():
    """Local backends are zero-cost via the wildcard entry."""
    assert _estimate_cost("ollama", "qwen2.5:3b", 1000, 500, 0) == 0.0


def test_tracker_persists_call(tmp_path):
    """A successful call is written to SQLite with token counts and cost."""
    db = tmp_path / "a.db"
    tracker = LLMCallTracker(str(db))

    with tracker.track(
        role="fast", backend="b", provider="openai", model="gpt-4o-mini",
    ) as record:
        record.prompt_tokens = 100
        record.completion_tokens = 50
        record.cached_tokens = 0

    # Query
    conn = tracker._connect()
    row = conn.execute(
        "SELECT role, backend, prompt_tokens, completion_tokens, status, cost_usd "
        "FROM llm_calls"
    ).fetchone()
    assert row[0] == "fast"
    assert row[2] == 100
    assert row[3] == 50
    assert row[4] == "ok"
    assert row[5] is not None and row[5] > 0


def test_tracker_marks_error_and_still_commits(tmp_path):
    """A failed call still lands in the DB with status=error for debugging."""
    db = tmp_path / "b.db"
    tracker = LLMCallTracker(str(db))

    with pytest.raises(RuntimeError):
        with tracker.track(role="fast", backend="b", provider="openai", model="m") as record:
            record.prompt_tokens = 5
            raise RuntimeError("kaboom")

    row = tracker._connect().execute(
        "SELECT status, error_code, error_message FROM llm_calls"
    ).fetchone()
    assert row[0] == "error"
    assert row[1] == "RuntimeError"
    assert "kaboom" in row[2]


def test_cache_hit_rate_aggregates_across_calls(tmp_path):
    """cache_hit_rate divides sum(cached)/sum(prompt) — verified by construction."""
    db = tmp_path / "c.db"
    tracker = LLMCallTracker(str(db))

    for cached, prompt in [(80, 100), (20, 100)]:
        with tracker.track(role="fast", backend="b", provider="openai", model="m") as r:
            r.prompt_tokens = prompt
            r.cached_tokens = cached
            r.completion_tokens = 1

    # 100/200 = 0.5
    assert tracker.cache_hit_rate() == pytest.approx(0.5)
    assert tracker.cache_hit_rate(role="fast") == pytest.approx(0.5)
    assert tracker.cache_hit_rate(role="heavy") == 0.0

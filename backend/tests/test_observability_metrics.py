"""Tests for the Prometheus metrics registry."""

import pytest

from app.observability.metrics import MetricsRegistry, get_registry


@pytest.fixture
def reg():
    return MetricsRegistry()


def test_llm_call_metric_increments_labels(reg):
    reg.observe_llm_call(
        role="fast", provider="openai", model="gpt-4o-mini", status="ok",
        prompt_tokens=100, completion_tokens=50, cached_tokens=20,
    )
    _, body = reg.render()
    # labels must appear in the Prometheus text format
    assert 'role="fast"' in body
    assert 'provider="openai"' in body
    assert 'model="gpt-4o-mini"' in body
    # token kind labels
    assert 'kind="prompt"' in body
    assert 'kind="completion"' in body
    assert 'kind="cached"' in body


def test_cache_hit_ratio_updated_after_calls(reg):
    reg.observe_llm_call(
        role="fast", provider="openai", model="m", status="ok",
        prompt_tokens=1000, cached_tokens=300,
    )
    _, body = reg.render()
    # 300 / 1000 = 0.3
    assert "llm_cache_hit_ratio 0.3" in body


def test_memory_op_histogram_records_duration(reg):
    with reg.observe_memory_op(op="retrieve", backend="in_memory"):
        # noop — just need the context manager to record
        pass
    _, body = reg.render()
    assert "memory_op_duration_seconds_bucket" in body
    assert 'op="retrieve"' in body
    assert 'backend="in_memory"' in body


def test_track_active_run_gauge(reg):
    reg.track_active_run(+2)
    reg.track_active_run(-1)
    _, body = reg.render()
    assert "simulation_active_runs 1" in body


def test_auth_rejections_counter(reg):
    reg.observe_auth_rejection(reason="invalid_key")
    reg.observe_auth_rejection(reason="invalid_key")
    reg.observe_auth_rejection(reason="missing_key")
    _, body = reg.render()
    assert 'reason="invalid_key"' in body
    assert 'reason="missing_key"' in body


def test_render_returns_prometheus_content_type(reg):
    content_type, _ = reg.render()
    assert "text/plain" in content_type


def test_fallback_when_prometheus_client_missing(monkeypatch):
    """If prometheus_client isn't importable, the helpers still work."""
    import builtins
    orig = builtins.__import__

    def _fake(name, *args, **kwargs):
        if name == "prometheus_client":
            raise ImportError("pretend missing")
        return orig(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake)
    fallback_reg = MetricsRegistry()
    fallback_reg.observe_llm_call(
        role="fast", provider="openai", model="m", status="ok",
        prompt_tokens=10, completion_tokens=5,
    )
    content_type, body = fallback_reg.render()
    assert "prometheus_client not installed" in body
    assert "llm_calls_total" in body


def test_global_accessor_is_singleton():
    a = get_registry()
    b = get_registry()
    assert a is b
    c = get_registry(fresh=True)
    assert c is not a

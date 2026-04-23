"""Tests for OpenTelemetry tracing helpers."""

import pytest

from app.observability import tracing


@pytest.fixture(autouse=True)
def _reset():
    tracing.reset_for_tests()
    yield
    tracing.reset_for_tests()


def test_configure_returns_false_without_endpoint(monkeypatch):
    """No OTEL_EXPORTER_OTLP_ENDPOINT -> tracing stays disabled."""
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    assert tracing.configure_tracing() is False


def test_start_span_is_noop_when_tracing_disabled():
    """With no tracer configured, start_span yields None but doesn't crash."""
    with tracing.start_span("test.op", foo="bar") as span:
        assert span is None


def test_configure_idempotent(monkeypatch):
    """Second call should not overwrite the tracer / double-register the exporter."""
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    tracing.configure_tracing()
    tracing.configure_tracing()  # must not raise


def test_start_span_with_endpoint_sets_attributes(monkeypatch):
    """When configured, the span context manager opens a real span and accepts
    primitive attributes without raising. The endpoint is non-routable so the
    BatchSpanProcessor retry thread doesn't pollute test teardown; we shut it
    down explicitly when the test finishes."""
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://127.0.0.1:1/invalid")
    ok = tracing.configure_tracing()
    if not ok:
        pytest.skip("opentelemetry SDK not importable in this environment")
    try:
        with tracing.start_span("llm.chat", role="fast", prompt_tokens=10, cached=True) as span:
            assert span is not None
    finally:
        from opentelemetry import trace
        provider = trace.get_tracer_provider()
        if hasattr(provider, "shutdown"):
            provider.shutdown()

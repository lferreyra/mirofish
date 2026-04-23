"""
OpenTelemetry tracing.

Every LLM call, every memory read/write, every IPC message gets a span when
this module is configured. When opentelemetry-api isn't installed, the
`start_span` context manager is a no-op — callers don't have to check
whether tracing is live.

Configuration (env, picked up by `configure_tracing`):
    OTEL_EXPORTER_OTLP_ENDPOINT   e.g. http://otel-collector:4318
    OTEL_SERVICE_NAME             default: "mirofish-backend"
    OTEL_TRACES_SAMPLER           default: "parentbased_traceidratio"
    OTEL_TRACES_SAMPLER_ARG       default: "0.1" (10% sampling)

We intentionally do NOT auto-install instrumentations for flask/requests/etc.
— the operator opts in via `pip install opentelemetry-instrumentation-flask`
and our code just emits the manual spans.
"""

from __future__ import annotations

import contextlib
import os
from typing import Any, Iterator, Optional


_CONFIGURED = False
_tracer = None


def configure_tracing(service_name: Optional[str] = None) -> bool:
    """Initialize the OpenTelemetry tracer + OTLP exporter. Safe to call
    multiple times. Returns True if tracing was actually enabled."""
    global _CONFIGURED, _tracer
    if _CONFIGURED:
        return _tracer is not None
    _CONFIGURED = True

    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return False

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        # OTLP/HTTP is lighter than gRPC and pairs well with collectors
        # behind ingress controllers that only speak HTTP.
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    except ImportError:
        return False

    resource = Resource.create({
        "service.name": service_name or os.environ.get("OTEL_SERVICE_NAME", "mirofish-backend"),
    })
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer("mirofish")
    return True


@contextlib.contextmanager
def start_span(name: str, **attrs: Any) -> Iterator[Optional[Any]]:
    """Context manager that opens a span when tracing is configured, and is a
    no-op otherwise. Attributes are flattened onto the span."""
    if _tracer is None:
        yield None
        return
    with _tracer.start_as_current_span(name) as span:
        for key, value in attrs.items():
            # Span attrs must be primitive types; skip the rest with best effort.
            if isinstance(value, (str, int, float, bool)) or value is None:
                try:
                    span.set_attribute(key, value)
                except Exception:
                    pass
        yield span


def current_span() -> Optional[Any]:
    if _tracer is None:
        return None
    try:
        from opentelemetry import trace
        return trace.get_current_span()
    except ImportError:
        return None


def reset_for_tests() -> None:
    """Test hook — returns tracing to 'unconfigured' state."""
    global _CONFIGURED, _tracer
    _CONFIGURED = False
    _tracer = None

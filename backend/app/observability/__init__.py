"""
Structured logging, Prometheus metrics, OpenTelemetry tracing.

The three submodules are intentionally independent:
    logging.py  -- always works (stdlib fallback). Configures structlog when
                   installed; otherwise JSON-formats via stdlib logging.
    metrics.py  -- Prometheus counters/histograms. If prometheus_client is
                   missing, the helpers become no-ops.
    tracing.py  -- OpenTelemetry spans. If opentelemetry-api isn't installed,
                   start_span() returns a no-op context manager.

This "gracefully degrade when deps missing" pattern keeps the backend runnable
in minimal environments (eval-smoke CI, bare local dev) without forcing every
operator to install the full observability stack.
"""

from .logging import bind_context, configure_logging, get_logger
from .metrics import (
    MetricsRegistry,
    get_registry,
    observe_llm_call,
    observe_memory_op,
    render_prometheus,
    track_active_run,
)
from .tracing import configure_tracing, current_span, start_span

__all__ = [
    "bind_context",
    "configure_logging",
    "configure_tracing",
    "current_span",
    "get_logger",
    "get_registry",
    "MetricsRegistry",
    "observe_llm_call",
    "observe_memory_op",
    "render_prometheus",
    "start_span",
    "track_active_run",
]

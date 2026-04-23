"""
Prometheus metrics.

Registers the counters / histograms the Phase-6 spec calls out:
  llm_calls_total{role,provider,model,status}
  llm_tokens_total{role,kind}            # kind = prompt | completion | cached
  llm_cache_hit_ratio                    # gauge, recalculated on emit
  memory_op_duration_seconds{op,backend} # histogram
  simulation_active_runs                 # gauge
  simulation_rounds_total{platform}      # counter
  auth_rejections_total{reason}          # counter

When `prometheus_client` is not installed, `render_prometheus()` returns a
small text block with "prometheus_client not installed" so /metrics still
responds 200 (operators can tell the binding is live, just missing deps).
"""

from __future__ import annotations

import contextlib
import threading
import time
from dataclasses import dataclass
from typing import Iterator, Optional


@dataclass
class _LocalFallbackCounters:
    """In-process counter fallback used when prometheus_client is missing.

    Keys are tuples of (metric_name, tuple(sorted(label_items))).
    """
    values: dict
    lock: threading.Lock


class MetricsRegistry:
    """Wrapper around the actual Prometheus registry. Lazily constructs it
    so tests can grab a fresh one per test via `get_registry(fresh=True)`."""

    def __init__(self):
        self._prom = None         # prometheus_client module (or None)
        self._registry = None     # CollectorRegistry (or None)
        self._metrics: dict = {}
        self._fallback = _LocalFallbackCounters(values={}, lock=threading.Lock())
        self._lock = threading.Lock()
        self._init()

    def _init(self) -> None:
        try:
            import prometheus_client  # type: ignore
            self._prom = prometheus_client
            self._registry = prometheus_client.CollectorRegistry()
        except ImportError:
            self._prom = None
            self._registry = None
            return

        prom = self._prom
        self._metrics["llm_calls_total"] = prom.Counter(
            "llm_calls_total",
            "LLM calls issued through the ModelRouter.",
            ["role", "provider", "model", "status"],
            registry=self._registry,
        )
        self._metrics["llm_tokens_total"] = prom.Counter(
            "llm_tokens_total",
            "Total LLM tokens, by role and kind (prompt / completion / cached).",
            ["role", "kind"],
            registry=self._registry,
        )
        self._metrics["llm_cache_hit_ratio"] = prom.Gauge(
            "llm_cache_hit_ratio",
            "Rolling cache hit ratio: cached_tokens / prompt_tokens.",
            registry=self._registry,
        )
        self._metrics["memory_op_duration_seconds"] = prom.Histogram(
            "memory_op_duration_seconds",
            "Latency of memory backend operations.",
            ["op", "backend"],
            # Buckets tuned for in-memory + neo4j/zep cloud ops (ms to sub-second).
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
            registry=self._registry,
        )
        self._metrics["simulation_active_runs"] = prom.Gauge(
            "simulation_active_runs",
            "Number of simulations currently running.",
            registry=self._registry,
        )
        self._metrics["simulation_rounds_total"] = prom.Counter(
            "simulation_rounds_total",
            "Total simulation rounds completed.",
            ["platform"],
            registry=self._registry,
        )
        self._metrics["auth_rejections_total"] = prom.Counter(
            "auth_rejections_total",
            "Requests rejected due to auth or quota policies.",
            ["reason"],
            registry=self._registry,
        )

    # ---- observation API --------------------------------------------------

    def observe_llm_call(
        self,
        *,
        role: str,
        provider: Optional[str],
        model: str,
        status: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        cached_tokens: int = 0,
    ) -> None:
        provider = provider or "unknown"
        if self._prom is None:
            self._fallback_inc("llm_calls_total", role=role, provider=provider, model=model, status=status)
            self._fallback_inc("llm_tokens_total", amount=prompt_tokens, role=role, kind="prompt")
            self._fallback_inc("llm_tokens_total", amount=completion_tokens, role=role, kind="completion")
            self._fallback_inc("llm_tokens_total", amount=cached_tokens, role=role, kind="cached")
            return
        self._metrics["llm_calls_total"].labels(role=role, provider=provider, model=model, status=status).inc()
        if prompt_tokens:
            self._metrics["llm_tokens_total"].labels(role=role, kind="prompt").inc(prompt_tokens)
        if completion_tokens:
            self._metrics["llm_tokens_total"].labels(role=role, kind="completion").inc(completion_tokens)
        if cached_tokens:
            self._metrics["llm_tokens_total"].labels(role=role, kind="cached").inc(cached_tokens)
        # Update the rolling cache-hit ratio gauge cheaply: use current
        # accumulators from this registry.
        prompt_c = _sum_counter(self._metrics["llm_tokens_total"], kind="prompt")
        cached_c = _sum_counter(self._metrics["llm_tokens_total"], kind="cached")
        if prompt_c > 0:
            self._metrics["llm_cache_hit_ratio"].set(cached_c / prompt_c)

    @contextlib.contextmanager
    def observe_memory_op(self, *, op: str, backend: str) -> Iterator[None]:
        start = time.perf_counter()
        try:
            yield
        finally:
            duration = time.perf_counter() - start
            if self._prom is None:
                self._fallback_inc("memory_op_duration_seconds_sum", amount=duration, op=op, backend=backend)
                self._fallback_inc("memory_op_duration_seconds_count", op=op, backend=backend)
            else:
                self._metrics["memory_op_duration_seconds"].labels(op=op, backend=backend).observe(duration)

    def track_active_run(self, delta: int) -> None:
        if self._prom is None:
            self._fallback_inc("simulation_active_runs", amount=delta)
            return
        gauge = self._metrics["simulation_active_runs"]
        if delta > 0:
            gauge.inc(delta)
        elif delta < 0:
            gauge.dec(-delta)

    def observe_round(self, *, platform: str) -> None:
        if self._prom is None:
            self._fallback_inc("simulation_rounds_total", platform=platform)
            return
        self._metrics["simulation_rounds_total"].labels(platform=platform).inc()

    def observe_auth_rejection(self, *, reason: str) -> None:
        if self._prom is None:
            self._fallback_inc("auth_rejections_total", reason=reason)
            return
        self._metrics["auth_rejections_total"].labels(reason=reason).inc()

    # ---- rendering --------------------------------------------------------

    def render(self) -> tuple[str, str]:
        """Return (content_type, body) suitable for a Flask response."""
        if self._prom is None:
            return (
                "text/plain; version=0.0.4",
                self._render_fallback(),
            )
        body = self._prom.generate_latest(self._registry).decode("utf-8")
        return self._prom.CONTENT_TYPE_LATEST, body

    # ---- helpers ----------------------------------------------------------

    def _fallback_inc(self, metric: str, *, amount: float = 1.0, **labels) -> None:
        key = (metric, tuple(sorted(labels.items())))
        with self._fallback.lock:
            self._fallback.values[key] = self._fallback.values.get(key, 0.0) + amount

    def _render_fallback(self) -> str:
        lines = [
            "# prometheus_client not installed; falling back to a minimal text "
            "format. Install prometheus_client to get proper histograms and types.",
        ]
        with self._fallback.lock:
            for (metric, labels), value in sorted(self._fallback.values.items()):
                label_str = ",".join(f'{k}="{v}"' for k, v in labels)
                suffix = f"{{{label_str}}}" if label_str else ""
                lines.append(f"{metric}{suffix} {value}")
        return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------
# module-level accessor
# --------------------------------------------------------------------------

_GLOBAL: Optional[MetricsRegistry] = None
_LOCK = threading.Lock()


def get_registry(fresh: bool = False) -> MetricsRegistry:
    global _GLOBAL
    if fresh or _GLOBAL is None:
        with _LOCK:
            if fresh or _GLOBAL is None:
                _GLOBAL = MetricsRegistry()
    return _GLOBAL


# ---- convenience shims — stay short; callers use these everywhere. -------

def observe_llm_call(**kwargs) -> None:
    get_registry().observe_llm_call(**kwargs)


def observe_memory_op(*, op: str, backend: str):
    return get_registry().observe_memory_op(op=op, backend=backend)


def track_active_run(delta: int) -> None:
    get_registry().track_active_run(delta)


def render_prometheus() -> tuple[str, str]:
    return get_registry().render()


# ---- internal -------------------------------------------------------------

def _sum_counter(counter, *, kind: Optional[str] = None) -> float:
    """Sum a Counter's underlying samples. prometheus_client doesn't give a
    direct 'total value' accessor so we walk the collect() output."""
    total = 0.0
    for metric in counter.collect():
        for sample in metric.samples:
            if sample.name.endswith("_total"):
                if kind is None or sample.labels.get("kind") == kind:
                    total += sample.value
    return total

"""
Per-call token / latency / cost accounting for the LLM router.

Persists to a SQLite file (`backend/data/llm_calls.db` by default) so the
router can answer "what was the prefix-cache hit rate after round 3?"
without holding everything in memory.

Cost is computed from a small per-provider/per-model price table. Unknown
models record NULL cost; the table is consulted by `(provider, model)`.
Prices are USD per 1M tokens, sourced from public price pages and may drift —
the operator can override via `LLM_PRICING_JSON` (path to a JSON file with
the same shape as `_BUILTIN_PRICING`).

Concurrency: the tracker uses a per-thread connection. SQLite WAL mode is
enabled so concurrent simulation workers don't block each other.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterator, Optional

# USD per 1M tokens. (input, output, cached_input).
# Unknown models -> NULL cost. Update via LLM_PRICING_JSON to add more.
_BUILTIN_PRICING: dict[tuple[str, str], tuple[float, float, float]] = {
    # OpenAI (Apr 2025-ish — operator should override for current numbers)
    ("openai", "gpt-4o-mini"): (0.15, 0.60, 0.075),
    ("openai", "gpt-4o"): (2.50, 10.00, 1.25),
    ("openai", "gpt-4.1-mini"): (0.40, 1.60, 0.10),
    ("openai", "text-embedding-3-large"): (0.13, 0.0, 0.0),
    ("openai", "text-embedding-3-small"): (0.02, 0.0, 0.0),
    # Anthropic
    ("anthropic", "claude-haiku-4-5-20251001"): (1.00, 5.00, 0.10),
    ("anthropic", "claude-sonnet-4-6"): (3.00, 15.00, 0.30),
    ("anthropic", "claude-opus-4-7"): (15.00, 75.00, 1.50),
    # Groq (free tier exists; price is conservative non-free fallback)
    ("groq", "llama-3.3-70b-versatile"): (0.59, 0.79, 0.0),
    # Local — zero cost
    ("ollama", "*"): (0.0, 0.0, 0.0),
    ("vllm", "*"): (0.0, 0.0, 0.0),
}


def _load_pricing() -> dict[tuple[str, str], tuple[float, float, float]]:
    table = dict(_BUILTIN_PRICING)
    override_path = os.environ.get("LLM_PRICING_JSON")
    if override_path and os.path.exists(override_path):
        try:
            with open(override_path, encoding="utf-8") as fh:
                data = json.load(fh)
            for entry in data:
                key = (entry["provider"].lower(), entry["model"])
                table[key] = (
                    float(entry.get("input_per_mtok", 0.0)),
                    float(entry.get("output_per_mtok", 0.0)),
                    float(entry.get("cached_input_per_mtok", 0.0)),
                )
        except Exception:
            # Pricing override is best-effort; never fail a call over bad config.
            pass
    return table


_PRICING = _load_pricing()


def _estimate_cost(
    provider: Optional[str],
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    cached_tokens: int,
) -> Optional[float]:
    if not provider:
        return None
    p = provider.lower()
    rates = _PRICING.get((p, model)) or _PRICING.get((p, "*"))
    if rates is None:
        return None
    input_rate, output_rate, cached_rate = rates
    uncached_prompt = max(0, prompt_tokens - cached_tokens)
    return (
        uncached_prompt * input_rate
        + cached_tokens * cached_rate
        + completion_tokens * output_rate
    ) / 1_000_000.0


_SCHEMA = """
CREATE TABLE IF NOT EXISTS llm_calls (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    call_id         TEXT NOT NULL,
    ts              REAL NOT NULL,
    role            TEXT,
    backend         TEXT,
    provider        TEXT,
    model           TEXT,
    prompt_tokens   INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    cached_tokens   INTEGER NOT NULL DEFAULT 0,
    latency_ms      REAL,
    cost_usd        REAL,
    status          TEXT NOT NULL,
    error_code      TEXT,
    error_message   TEXT,
    run_id          TEXT,
    agent_id        TEXT,
    request_kind    TEXT NOT NULL DEFAULT 'chat'
);
CREATE INDEX IF NOT EXISTS idx_llm_calls_ts ON llm_calls(ts);
CREATE INDEX IF NOT EXISTS idx_llm_calls_run ON llm_calls(run_id);
CREATE INDEX IF NOT EXISTS idx_llm_calls_role ON llm_calls(role);
"""


@dataclass
class CallRecord:
    """Mutable record filled in by the tracker as a call proceeds."""
    role: str
    backend: str
    provider: Optional[str]
    model: str
    request_kind: str = "chat"
    run_id: Optional[str] = None
    agent_id: Optional[str] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_tokens: int = 0
    latency_ms: float = 0.0
    status: str = "ok"
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    call_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    ts: float = field(default_factory=time.time)


class LLMCallTracker:
    """SQLite-backed tracker. One instance per process; share via accessor."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._tls = threading.local()
        with self._connect() as conn:
            conn.executescript(_SCHEMA)
            conn.execute("PRAGMA journal_mode=WAL;")

    def _connect(self) -> sqlite3.Connection:
        # Per-thread connection; SQLite forbids cross-thread sharing without check_same_thread=False.
        conn = getattr(self._tls, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=10)
            conn.execute("PRAGMA foreign_keys=ON;")
            self._tls.conn = conn
        return conn

    @contextmanager
    def track(
        self,
        *,
        role: str,
        backend: str,
        provider: Optional[str],
        model: str,
        request_kind: str = "chat",
        run_id: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> Iterator[CallRecord]:
        record = CallRecord(
            role=role,
            backend=backend,
            provider=provider,
            model=model,
            request_kind=request_kind,
            run_id=run_id,
            agent_id=agent_id,
        )
        start = time.perf_counter()
        try:
            yield record
        except Exception as exc:
            record.status = "error"
            # If the underlying exception is a BackendError it carries .code; otherwise stringify.
            record.error_code = getattr(exc, "code", type(exc).__name__)
            record.error_message = str(exc)[:500]
            raise
        finally:
            if record.latency_ms == 0.0:
                record.latency_ms = (time.perf_counter() - start) * 1000.0
            cost = _estimate_cost(
                record.provider,
                record.model,
                record.prompt_tokens,
                record.completion_tokens,
                record.cached_tokens,
            )
            self._write(record, cost)

    def _write(self, r: CallRecord, cost: Optional[float]) -> None:
        try:
            conn = self._connect()
            conn.execute(
                "INSERT INTO llm_calls (call_id, ts, role, backend, provider, model, "
                "prompt_tokens, completion_tokens, cached_tokens, latency_ms, cost_usd, "
                "status, error_code, error_message, run_id, agent_id, request_kind) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    r.call_id, r.ts, r.role, r.backend, r.provider, r.model,
                    r.prompt_tokens, r.completion_tokens, r.cached_tokens,
                    r.latency_ms, cost,
                    r.status, r.error_code, r.error_message,
                    r.run_id, r.agent_id, r.request_kind,
                ),
            )
            conn.commit()
        except Exception:
            # Accounting must never break a working call. Operators get visibility
            # via the existing logger; we deliberately don't raise here.
            pass

    # -------- read API for /metrics and the cache-hit-rate acceptance check
    def cache_hit_rate(self, *, role: Optional[str] = None, since_ts: Optional[float] = None) -> float:
        sql = (
            "SELECT COALESCE(SUM(cached_tokens),0) * 1.0 / NULLIF(SUM(prompt_tokens),0) "
            "FROM llm_calls WHERE status='ok'"
        )
        params: list = []
        if role is not None:
            sql += " AND role=?"
            params.append(role)
        if since_ts is not None:
            sql += " AND ts>=?"
            params.append(since_ts)
        cur = self._connect().execute(sql, params)
        row = cur.fetchone()
        return float(row[0] or 0.0)

    def total_cost_usd(self, *, run_id: Optional[str] = None) -> float:
        sql = "SELECT COALESCE(SUM(cost_usd),0) FROM llm_calls WHERE cost_usd IS NOT NULL"
        params: list = []
        if run_id is not None:
            sql += " AND run_id=?"
            params.append(run_id)
        cur = self._connect().execute(sql, params)
        return float(cur.fetchone()[0] or 0.0)


# ---- module-level singleton accessor
_GLOBAL: Optional[LLMCallTracker] = None
_LOCK = threading.Lock()


def get_tracker(db_path: Optional[str] = None) -> LLMCallTracker:
    """Return the process-wide tracker, instantiating on first call."""
    global _GLOBAL
    if _GLOBAL is not None:
        return _GLOBAL
    with _LOCK:
        if _GLOBAL is None:
            path = db_path or os.environ.get("LLM_CALLS_DB") or _default_db_path()
            _GLOBAL = LLMCallTracker(path)
    return _GLOBAL


def _default_db_path() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(here, "..", "..", "data", "llm_calls.db"))


def reset_tracker_for_tests(db_path: Optional[str] = None) -> LLMCallTracker:
    """Test hook — replaces the singleton with a fresh tracker."""
    global _GLOBAL
    with _LOCK:
        _GLOBAL = LLMCallTracker(db_path or _default_db_path())
    return _GLOBAL

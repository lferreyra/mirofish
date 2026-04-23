"""
Reference in-memory backend.

Stores everything in per-process dicts keyed by namespace. Used by:
  * the pytest suite (no external services required)
  * `MEMORY_BACKEND=in_memory` for zero-dependency local runs

Not a persistence option — all records are lost when the process exits.
Concurrency: a single `RLock` guards the dictionaries; enough for the
simulation's moderate write rate without the complexity of a per-namespace lock.
"""

from __future__ import annotations

import threading
from typing import Dict, List, Optional

from .base import (
    ConflictEdge,
    MemoryBackend,
    MemoryBackendError,
    MemoryRecord,
    Namespace,
    Observation,
    RecordKind,
    Reflection,
    RetrievalResult,
)


class InMemoryBackend(MemoryBackend):
    """Pure-Python reference backend."""

    name = "in_memory"

    def __init__(self) -> None:
        self._records: Dict[str, Dict[str, MemoryRecord]] = {}  # namespace -> id -> record
        self._conflicts: Dict[str, List[ConflictEdge]] = {}     # namespace -> edges
        self._lock = threading.RLock()

    # ------------------------------------------------------------- writes
    def write_observation(self, observation: Observation) -> Observation:
        self._validate_namespace(observation.namespace)
        with self._lock:
            self._records.setdefault(observation.namespace, {})[observation.id] = observation
        return observation

    def write_reflection(self, reflection: Reflection) -> Reflection:
        self._validate_namespace(reflection.namespace)
        with self._lock:
            bucket = self._records.setdefault(reflection.namespace, {})
            # Verify source_ids actually exist in this namespace — catches typos fast.
            for sid in reflection.source_ids:
                if sid not in bucket:
                    raise MemoryBackendError(
                        "dangling_source",
                        f"reflection.source_ids references missing record {sid} "
                        f"in namespace {reflection.namespace}",
                        backend=self.name,
                    )
            bucket[reflection.id] = reflection
        return reflection

    def write_conflict_edge(self, edge: ConflictEdge) -> ConflictEdge:
        with self._lock:
            # Look up the namespace from either endpoint — conflict edges live
            # in whichever namespace their observations belong to.
            ns = self._find_namespace_for(edge.from_id)
            if ns is None:
                ns = self._find_namespace_for(edge.to_id)
            if ns is None:
                raise MemoryBackendError(
                    "unknown_endpoint",
                    f"neither endpoint of conflict edge exists: {edge.from_id} / {edge.to_id}",
                    backend=self.name,
                )
            self._conflicts.setdefault(ns, []).append(edge)
        return edge

    # -------------------------------------------------------------- reads
    def retrieve(
        self,
        *,
        namespace: Namespace,
        query: str,
        query_embedding: Optional[List[float]] = None,
        top_k: int = 10,
        alpha: float = 1.0,
        beta: float = 1.0,
        gamma: float = 1.0,
        now_ts: Optional[float] = None,
    ) -> RetrievalResult:
        now_ts = now_ts if now_ts is not None else self._now_ts()
        weight_sum = alpha + beta + gamma
        if weight_sum <= 0:
            weight_sum = 1.0
        a, b, g = alpha / weight_sum, beta / weight_sum, gamma / weight_sum

        with self._lock:
            items = list(self._records.get(namespace.key, {}).values())

        scored: List[MemoryRecord] = []
        for rec in items:
            relevance = self._relevance(rec, query, query_embedding)
            recency = self._recency_score(rec.ts, now_ts)
            importance = self._importance_score(rec.importance)
            combined = a * recency + b * importance + g * relevance
            # Attach scores so callers can debug / surface them; we copy the
            # record so we don't mutate the stored instance.
            rec_copy = self._copy(rec)
            rec_copy.relevance_score = relevance
            rec_copy.recency_score = recency
            rec_copy.combined_score = combined
            scored.append(rec_copy)

        scored.sort(key=lambda r: r.combined_score or 0.0, reverse=True)
        return RetrievalResult(records=scored[:top_k], namespace=namespace.key, query=query)

    def nearest(
        self,
        *,
        namespace: Namespace,
        query_embedding: List[float],
        top_k: int = 3,
        kind: Optional[RecordKind] = None,
    ) -> List[MemoryRecord]:
        with self._lock:
            items = list(self._records.get(namespace.key, {}).values())
        if kind is not None:
            items = [r for r in items if r.kind == kind]
        items = [r for r in items if r.embedding]  # can't compare without vectors
        items.sort(
            key=lambda r: self._cosine(r.embedding or [], query_embedding),
            reverse=True,
        )
        return [self._copy(r) for r in items[:top_k]]

    def list_reflections(self, *, namespace: Namespace, limit: int = 50) -> List[Reflection]:
        with self._lock:
            bucket = list(self._records.get(namespace.key, {}).values())
        reflections = [r for r in bucket if isinstance(r, Reflection)]
        reflections.sort(key=lambda r: (r.round_num, r.ts), reverse=True)
        return [self._copy(r) for r in reflections[:limit]]

    def list_conflicts(self, *, namespace: Namespace, limit: int = 50) -> List[ConflictEdge]:
        with self._lock:
            edges = list(self._conflicts.get(namespace.key, []))
        return edges[-limit:][::-1]  # most recent first

    def summarize_window(
        self,
        *,
        namespace: Namespace,
        since_round: Optional[int] = None,
        until_round: Optional[int] = None,
        top_k: int = 50,
    ) -> List[MemoryRecord]:
        with self._lock:
            items = list(self._records.get(namespace.key, {}).values())
        if since_round is not None:
            items = [r for r in items if r.round_num >= since_round]
        if until_round is not None:
            items = [r for r in items if r.round_num <= until_round]
        items.sort(key=lambda r: (r.round_num, r.ts))
        # top_k selects the most IMPORTANT within the window (what the
        # reflection scheduler wants), not the most recent.
        items.sort(key=lambda r: r.importance, reverse=True)
        return [self._copy(r) for r in items[:top_k]]

    # ------------------------------------------------------------- helpers
    def _validate_namespace(self, key: str) -> None:
        if not (key.startswith("agent:") or key.startswith("public:")):
            raise MemoryBackendError(
                "invalid_namespace",
                f"namespace must start with 'agent:' or 'public:'; got {key!r}",
                backend=self.name,
            )

    def _find_namespace_for(self, record_id: str) -> Optional[str]:
        for ns, bucket in self._records.items():
            if record_id in bucket:
                return ns
        return None

    def _relevance(
        self,
        record: MemoryRecord,
        query: str,
        query_embedding: Optional[List[float]],
    ) -> float:
        """Vector cosine sim if both vectors exist; else a toy token overlap
        score (better than nothing for tests without a live embedding model)."""
        if query_embedding is not None and record.embedding:
            return max(0.0, self._cosine(record.embedding, query_embedding))
        q_tokens = set(query.lower().split())
        r_tokens = set(record.content.lower().split())
        if not q_tokens or not r_tokens:
            return 0.0
        return len(q_tokens & r_tokens) / len(q_tokens | r_tokens)

    @staticmethod
    def _copy(record: MemoryRecord) -> MemoryRecord:
        # Shallow copy is safe — lists are the only mutable field we share, and
        # callers only read scores/metadata, not mutate them.
        return type(record)(**record.__dict__)

    # Test-only helper: drop all state
    def clear(self) -> None:
        with self._lock:
            self._records.clear()
            self._conflicts.clear()

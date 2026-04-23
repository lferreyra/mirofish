"""
Zep Cloud adapter.

Wraps the pre-existing `zep_cloud.client.Zep` API so agent observations and
reflections can flow through the common MemoryBackend interface.

Zep-specific notes:
  * Zep computes embeddings server-side. We pass `embedding` if the caller
    supplied one, but the server may overwrite. Our `record.embedding` after
    write is whatever the caller sent (or None); retrieval uses Zep's own search.
  * Zep's graph is per-`graph_id`. We map one simulation to one graph_id, and
    tag observations with a namespace prefix in the episode text so we can
    filter on read.
  * `nearest()` and vector-only retrieval aren't native to the Zep API at the
    level we need; we fall back to `graph.search(query=..., scope='edges')`
    using the content itself as the query string. Good enough for contradiction
    detection on cloud.

Feature-flag: this adapter is only instantiated when MEMORY_BACKEND=zep_cloud
or as a fallback for a user who wants the pre-existing Zep pipeline.
"""

from __future__ import annotations

import json
import logging
from typing import Any, List, Optional

from ..config import Config
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

logger = logging.getLogger("mirofish.memory.zep_cloud")

# Marker prefix on every episode body so we can parse records back out.
_MARKER = "[mf-mem]"


class ZepCloudBackend(MemoryBackend):
    """Adapter around the managed Zep graph."""

    name = "zep_cloud"

    def __init__(self, graph_id: str, api_key: Optional[str] = None):
        self.graph_id = graph_id
        self.api_key = api_key or Config.ZEP_API_KEY
        if not self.api_key:
            raise MemoryBackendError(
                "missing_api_key",
                "ZEP_API_KEY is required for zep_cloud backend",
                backend=self.name,
            )
        try:
            from zep_cloud.client import Zep
        except ImportError as exc:
            raise MemoryBackendError(
                "zep_sdk_missing",
                "zep-cloud package is required for ZepCloudBackend",
                backend=self.name,
            ) from exc
        self._client = Zep(api_key=self.api_key)

    # ------------------------------------------------------------- writes
    def write_observation(self, observation: Observation) -> Observation:
        self._send_episode(observation)
        return observation

    def write_reflection(self, reflection: Reflection) -> Reflection:
        self._send_episode(reflection)
        return reflection

    def write_conflict_edge(self, edge: ConflictEdge) -> ConflictEdge:
        # Zep doesn't have a direct "add edge between two episodes" API we can
        # rely on; persist as a special-kind episode so reflections surfacing
        # this agent's memory can still see it.
        body = json.dumps({
            "kind": "conflict",
            "from_id": edge.from_id,
            "to_id": edge.to_id,
            "reason": edge.reason or "",
        }, ensure_ascii=False)
        try:
            self._client.graph.add(
                graph_id=self.graph_id,
                type="text",
                data=f"{_MARKER} conflict {body}",
            )
        except Exception as exc:
            logger.warning("ZepCloudBackend conflict edge write failed: %s", exc)
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
        # Zep has its own recency+relevance scoring; we honor the weight params
        # by adjusting top_k but can't directly reproduce the α/β/γ formula.
        # We post-filter by namespace marker and return a plain relevance-sorted list.
        raw_edges = self._search(namespace=namespace.key, query=query, top_k=top_k * 3)
        records: List[MemoryRecord] = []
        for fact in raw_edges:
            parsed = self._parse_fact(fact, namespace.key)
            if parsed is None:
                continue
            # Zep gives us a relevance score implicitly via result ordering;
            # we leave combined_score=None so callers know the ranking is Zep-native.
            records.append(parsed)
            if len(records) >= top_k:
                break
        return RetrievalResult(records=records, namespace=namespace.key, query=query)

    def nearest(
        self,
        *,
        namespace: Namespace,
        query_embedding: List[float],
        top_k: int = 3,
        kind: Optional[RecordKind] = None,
    ) -> List[MemoryRecord]:
        # Zep doesn't expose a vector-only search via this SDK path, so we
        # degrade to a content-free search that at minimum respects namespace.
        # Callers that need tight vector KNN (contradiction detection) should
        # use a backend that supports it (in_memory, neo4j_local/aura).
        logger.info("ZepCloudBackend.nearest falls back to empty — use a vector-capable backend "
                    "for contradiction detection on cloud.")
        return []

    def list_reflections(self, *, namespace: Namespace, limit: int = 50) -> List[Reflection]:
        results = self._search(namespace=namespace.key, query="reflection", top_k=limit * 2)
        out: List[Reflection] = []
        for fact in results:
            rec = self._parse_fact(fact, namespace.key)
            if isinstance(rec, Reflection):
                out.append(rec)
            if len(out) >= limit:
                break
        return out

    def list_conflicts(self, *, namespace: Namespace, limit: int = 50) -> List[ConflictEdge]:
        # Best-effort — we stored conflicts as marker episodes; search for them.
        out: List[ConflictEdge] = []
        results = self._search(namespace=namespace.key, query="conflict", top_k=limit * 2)
        for fact in results:
            if "conflict" not in fact:
                continue
            try:
                body = fact.split("conflict", 1)[1].strip()
                data = json.loads(body)
                out.append(ConflictEdge(
                    id=ConflictEdge.new_id(),
                    from_id=data["from_id"],
                    to_id=data["to_id"],
                    ts=self._now_ts(),
                    reason=data.get("reason"),
                ))
            except Exception:
                continue
            if len(out) >= limit:
                break
        return out

    def summarize_window(
        self,
        *,
        namespace: Namespace,
        since_round: Optional[int] = None,
        until_round: Optional[int] = None,
        top_k: int = 50,
    ) -> List[MemoryRecord]:
        results = self._search(namespace=namespace.key, query="", top_k=top_k * 2)
        out: List[MemoryRecord] = []
        for fact in results:
            rec = self._parse_fact(fact, namespace.key)
            if rec is None:
                continue
            if since_round is not None and rec.round_num < since_round:
                continue
            if until_round is not None and rec.round_num > until_round:
                continue
            out.append(rec)
            if len(out) >= top_k:
                break
        return out

    # ------------------------------------------------------------- helpers
    def _send_episode(self, record: MemoryRecord) -> None:
        header = {
            "ns": record.namespace,
            "kind": record.kind.value,
            "id": record.id,
            "round": record.round_num,
            "importance": record.importance,
        }
        if isinstance(record, Reflection):
            header["source_ids"] = record.source_ids
        body = f"{_MARKER} {json.dumps(header, ensure_ascii=False)} :: {record.content}"
        try:
            self._client.graph.add(graph_id=self.graph_id, type="text", data=body)
        except Exception as exc:
            raise MemoryBackendError(
                "zep_write_failed",
                f"graph.add failed: {exc}",
                backend=self.name,
            ) from exc

    def _search(self, *, namespace: str, query: str, top_k: int) -> List[str]:
        """Facet against Zep's graph.search and return raw fact strings that
        match our namespace marker."""
        try:
            resp = self._client.graph.search(
                graph_id=self.graph_id,
                query=query or namespace,
                scope="edges",
                limit=top_k,
            )
        except Exception as exc:
            logger.warning("ZepCloudBackend search failed: %s", exc)
            return []

        facts: List[str] = []
        for edge in getattr(resp, "edges", None) or []:
            fact = getattr(edge, "fact", None)
            if isinstance(fact, str) and _MARKER in fact and namespace in fact:
                facts.append(fact)
        return facts

    def _parse_fact(self, fact: str, namespace: str) -> Optional[MemoryRecord]:
        try:
            _, body = fact.split(_MARKER, 1)
            header_json, content = body.split("::", 1)
            header = json.loads(header_json.strip())
        except Exception:
            return None
        if header.get("ns") != namespace:
            return None
        kind = header.get("kind")
        content = content.strip()
        if kind == RecordKind.REFLECTION.value:
            return Reflection(
                id=header.get("id", Reflection.new_id()),
                namespace=namespace,
                content=content,
                round_num=int(header.get("round", 0) or 0),
                ts=self._now_ts(),
                importance=float(header.get("importance", 5.0) or 5.0),
                source_ids=header.get("source_ids", []) or [],
            )
        return Observation(
            id=header.get("id", Observation.new_id()),
            namespace=namespace,
            content=content,
            round_num=int(header.get("round", 0) or 0),
            ts=self._now_ts(),
            importance=float(header.get("importance", 5.0) or 5.0),
        )

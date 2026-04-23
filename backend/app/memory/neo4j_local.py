"""
Neo4j (local / self-hosted CE) memory backend.

Schema
------
    (:Agent {sim_id, agent_id})
    (:Namespace {key, sim_id, kind, agent_id})
    (:Observation {id, namespace, content, round_num, ts,
                   importance, embedding, action_type, author_id, metadata})
    (:Reflection  {id, namespace, content, round_num, ts,
                   importance, embedding, source_ids, metadata})
    (:Observation)-[:IN]->(:Namespace)
    (:Reflection)-[:IN]->(:Namespace)
    (:Reflection)-[:DERIVED_FROM]->(:Observation)
    (:Observation)-[:CONTRADICTS {id, ts, reason}]->(:Observation)

Vector similarity
-----------------
Neo4j 5.x has a native vector index, but the Cypher syntax changes across
point releases and requires APOC for many ops. To keep this backend portable
(and to avoid binding the test suite to a specific Neo4j image), we compute
cosine similarity in Python after fetching candidate vectors. For large agent
populations this is fine up to ~10k memories per namespace; beyond that, flip
on the vector index via the `VectorIndexHint` notes at the bottom of this file.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

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

logger = logging.getLogger("mirofish.memory.neo4j")

_SCHEMA_CYPHER = [
    # Uniqueness on record ids (across both Observation and Reflection)
    "CREATE CONSTRAINT mf_obs_id IF NOT EXISTS FOR (o:Observation) REQUIRE o.id IS UNIQUE",
    "CREATE CONSTRAINT mf_ref_id IF NOT EXISTS FOR (r:Reflection) REQUIRE r.id IS UNIQUE",
    "CREATE CONSTRAINT mf_ns_key IF NOT EXISTS FOR (n:Namespace) REQUIRE n.key IS UNIQUE",
    # Helpful indexes
    "CREATE INDEX mf_obs_ns IF NOT EXISTS FOR (o:Observation) ON (o.namespace)",
    "CREATE INDEX mf_ref_ns IF NOT EXISTS FOR (r:Reflection) ON (r.namespace)",
    "CREATE INDEX mf_obs_round IF NOT EXISTS FOR (o:Observation) ON (o.round_num)",
    "CREATE INDEX mf_ref_round IF NOT EXISTS FOR (r:Reflection) ON (r.round_num)",
]


class Neo4jLocalBackend(MemoryBackend):
    """Self-hosted Neo4j CE backend (bolt://)."""

    name = "neo4j_local"

    def __init__(
        self,
        *,
        uri: str,
        user: str,
        password: str,
        database: str = "neo4j",
    ):
        try:
            from neo4j import GraphDatabase
        except ImportError as exc:
            raise MemoryBackendError(
                "neo4j_sdk_missing",
                "neo4j package is required for Neo4jLocalBackend",
                backend=self.name,
            ) from exc
        self._driver = GraphDatabase.driver(uri, auth=(user, password))
        self._database = database
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self._driver.session(database=self._database) as session:
            for stmt in _SCHEMA_CYPHER:
                session.run(stmt)

    def close(self) -> None:
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    # -------------------------------------------------------------- writes
    def write_observation(self, observation: Observation) -> Observation:
        params = self._record_params(observation)
        params["action_type"] = observation.action_type
        params["author_id"] = observation.author_id
        query = """
        MERGE (ns:Namespace {key: $namespace})
            ON CREATE SET ns.created_ts = $ts
        CREATE (o:Observation {
            id: $id,
            namespace: $namespace,
            content: $content,
            round_num: $round_num,
            ts: $ts,
            importance: $importance,
            embedding: $embedding,
            action_type: $action_type,
            author_id: $author_id,
            metadata: $metadata_json
        })
        CREATE (o)-[:IN]->(ns)
        """
        self._run(query, params)
        return observation

    def write_reflection(self, reflection: Reflection) -> Reflection:
        params = self._record_params(reflection)
        params["source_ids"] = reflection.source_ids
        query = """
        MERGE (ns:Namespace {key: $namespace})
            ON CREATE SET ns.created_ts = $ts
        CREATE (r:Reflection {
            id: $id,
            namespace: $namespace,
            content: $content,
            round_num: $round_num,
            ts: $ts,
            importance: $importance,
            embedding: $embedding,
            source_ids: $source_ids,
            metadata: $metadata_json
        })
        CREATE (r)-[:IN]->(ns)
        WITH r
        UNWIND $source_ids AS sid
        MATCH (o:Observation {id: sid})
        CREATE (r)-[:DERIVED_FROM]->(o)
        """
        self._run(query, params)
        return reflection

    def write_conflict_edge(self, edge: ConflictEdge) -> ConflictEdge:
        query = """
        MATCH (a:Observation {id: $from_id}), (b:Observation {id: $to_id})
        CREATE (a)-[:CONTRADICTS {id: $id, ts: $ts, reason: $reason}]->(b)
        """
        self._run(query, {
            "from_id": edge.from_id, "to_id": edge.to_id,
            "id": edge.id, "ts": edge.ts, "reason": edge.reason or "",
        })
        return edge

    # --------------------------------------------------------------- reads
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

        # Fetch all candidates for this namespace, then score in Python.
        # For very large namespaces this is the spot to swap in a vector index.
        raw = self._run(
            """
            MATCH (r)-[:IN]->(:Namespace {key: $ns})
            RETURN r, labels(r) AS lbls
            """,
            {"ns": namespace.key},
        )
        records: List[MemoryRecord] = []
        for row in raw:
            rec = self._hydrate_record(row["r"], row["lbls"])
            if rec is None:
                continue
            relevance = self._relevance(rec, query, query_embedding)
            recency = self._recency_score(rec.ts, now_ts)
            importance = self._importance_score(rec.importance)
            rec.relevance_score = relevance
            rec.recency_score = recency
            rec.combined_score = a * recency + b * importance + g * relevance
            records.append(rec)

        records.sort(key=lambda r: r.combined_score or 0.0, reverse=True)
        return RetrievalResult(records=records[:top_k], namespace=namespace.key, query=query)

    def nearest(
        self,
        *,
        namespace: Namespace,
        query_embedding: List[float],
        top_k: int = 3,
        kind: Optional[RecordKind] = None,
    ) -> List[MemoryRecord]:
        label = None
        if kind == RecordKind.OBSERVATION:
            label = "Observation"
        elif kind == RecordKind.REFLECTION:
            label = "Reflection"

        if label:
            cypher = f"""
            MATCH (r:{label})-[:IN]->(:Namespace {{key: $ns}})
            WHERE r.embedding IS NOT NULL
            RETURN r, labels(r) AS lbls
            """
        else:
            cypher = """
            MATCH (r)-[:IN]->(:Namespace {key: $ns})
            WHERE r.embedding IS NOT NULL
            RETURN r, labels(r) AS lbls
            """
        raw = self._run(cypher, {"ns": namespace.key})
        records: List[MemoryRecord] = []
        for row in raw:
            rec = self._hydrate_record(row["r"], row["lbls"])
            if rec is None or not rec.embedding:
                continue
            rec.relevance_score = self._cosine(rec.embedding, query_embedding)
            records.append(rec)
        records.sort(key=lambda r: r.relevance_score or 0.0, reverse=True)
        return records[:top_k]

    def list_reflections(self, *, namespace: Namespace, limit: int = 50) -> List[Reflection]:
        raw = self._run(
            """
            MATCH (r:Reflection)-[:IN]->(:Namespace {key: $ns})
            RETURN r
            ORDER BY r.round_num DESC, r.ts DESC
            LIMIT $limit
            """,
            {"ns": namespace.key, "limit": limit},
        )
        return [r for r in (self._hydrate_record(row["r"], ["Reflection"]) for row in raw)
                if isinstance(r, Reflection)]

    def list_conflicts(self, *, namespace: Namespace, limit: int = 50) -> List[ConflictEdge]:
        raw = self._run(
            """
            MATCH (a:Observation)-[c:CONTRADICTS]->(b:Observation)
            WHERE a.namespace = $ns
            RETURN c.id AS id, a.id AS from_id, b.id AS to_id,
                   c.ts AS ts, c.reason AS reason
            ORDER BY c.ts DESC
            LIMIT $limit
            """,
            {"ns": namespace.key, "limit": limit},
        )
        return [
            ConflictEdge(
                id=row["id"], from_id=row["from_id"], to_id=row["to_id"],
                ts=row["ts"], reason=row["reason"] or None,
            )
            for row in raw
        ]

    def summarize_window(
        self,
        *,
        namespace: Namespace,
        since_round: Optional[int] = None,
        until_round: Optional[int] = None,
        top_k: int = 50,
    ) -> List[MemoryRecord]:
        clauses = ["r.namespace = $ns"]
        params: Dict[str, Any] = {"ns": namespace.key, "limit": top_k}
        if since_round is not None:
            clauses.append("r.round_num >= $since")
            params["since"] = since_round
        if until_round is not None:
            clauses.append("r.round_num <= $until")
            params["until"] = until_round
        where = " AND ".join(clauses)
        raw = self._run(
            f"""
            MATCH (r) WHERE {where}
            RETURN r, labels(r) AS lbls
            ORDER BY r.importance DESC
            LIMIT $limit
            """,
            params,
        )
        return [
            rec for rec in (self._hydrate_record(row["r"], row["lbls"]) for row in raw)
            if rec is not None
        ]

    # ------------------------------------------------------------- helpers
    def _run(self, cypher: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        try:
            with self._driver.session(database=self._database) as session:
                result = session.run(cypher, params)
                return [dict(record) for record in result]
        except Exception as exc:
            raise MemoryBackendError(
                "neo4j_query_failed",
                f"{exc}",
                backend=self.name,
            ) from exc

    @staticmethod
    def _record_params(record: MemoryRecord) -> Dict[str, Any]:
        return {
            "id": record.id,
            "namespace": record.namespace,
            "content": record.content,
            "round_num": record.round_num,
            "ts": record.ts,
            "importance": record.importance,
            "embedding": record.embedding,   # list[float] -> Neo4j FLOAT[]
            "metadata_json": json.dumps(record.metadata, ensure_ascii=False),
        }

    def _hydrate_record(
        self,
        node: Any,
        labels: List[str],
    ) -> Optional[MemoryRecord]:
        if not node:
            return None
        data = dict(node)
        metadata = {}
        md = data.get("metadata")
        if md:
            try:
                metadata = json.loads(md)
            except Exception:
                metadata = {}
        if "Reflection" in labels:
            return Reflection(
                id=data["id"], namespace=data["namespace"], content=data["content"],
                round_num=int(data["round_num"] or 0), ts=float(data["ts"] or 0.0),
                importance=float(data.get("importance", 5.0) or 5.0),
                embedding=list(data.get("embedding") or []) or None,
                metadata=metadata,
                source_ids=list(data.get("source_ids") or []),
            )
        return Observation(
            id=data["id"], namespace=data["namespace"], content=data["content"],
            round_num=int(data["round_num"] or 0), ts=float(data["ts"] or 0.0),
            importance=float(data.get("importance", 5.0) or 5.0),
            embedding=list(data.get("embedding") or []) or None,
            metadata=metadata,
            action_type=data.get("action_type"),
            author_id=data.get("author_id"),
        )

    def _relevance(
        self,
        record: MemoryRecord,
        query: str,
        query_embedding: Optional[List[float]],
    ) -> float:
        if query_embedding and record.embedding:
            return max(0.0, self._cosine(record.embedding, query_embedding))
        q_tokens = set(query.lower().split())
        r_tokens = set(record.content.lower().split())
        if not q_tokens or not r_tokens:
            return 0.0
        return len(q_tokens & r_tokens) / len(q_tokens | r_tokens)


# VectorIndexHint -----------------------------------------------------------
# To upgrade retrieval / nearest to native vector search on Neo4j 5.11+:
#   CREATE VECTOR INDEX mf_obs_vec IF NOT EXISTS
#   FOR (o:Observation) ON (o.embedding)
#   OPTIONS { indexConfig: {
#     `vector.dimensions`: 3072,                  -- must match the embed model
#     `vector.similarity_function`: 'cosine'
#   }};
# Then replace the Python cosine loop with:
#   CALL db.index.vector.queryNodes('mf_obs_vec', $top_k, $q_embedding)
#   YIELD node, score
# which is O(log N) instead of O(N).

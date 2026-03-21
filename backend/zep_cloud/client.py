"""
Zep-compatible client backed by Neo4j for private deployment.

This shim preserves the subset of the Zep SDK API used by MiroFish while
switching storage/lookup to local Neo4j.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Optional

from neo4j import GraphDatabase

from . import EpisodeData, InternalServerError

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - optional at runtime
    OpenAI = None  # type: ignore


logger = logging.getLogger('mirofish.zep_compat')


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return {}
    return {}


def _ensure_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else ([] if value is None else [value])


def _dict_to_json(value: Any) -> str:
    try:
        return json.dumps(_ensure_dict(value), ensure_ascii=False)
    except Exception:
        return "{}"


def _normalize_labels(labels: Any) -> list[str]:
    if isinstance(labels, list):
        result = [str(i) for i in labels if str(i).strip()]
    elif labels:
        result = [str(labels)]
    else:
        result = []
    if "Entity" not in result:
        result.insert(0, "Entity")
    return list(dict.fromkeys(result))


def _clean_text(text: str, limit: int = 8000) -> str:
    text = (text or "").strip()
    if len(text) > limit:
        return text[:limit]
    return text


def _tokenize_query(query: str) -> list[str]:
    tokens = re.split(r"[\s,，。；;：:!?！？/\\\n\r\t]+", (query or "").lower())
    return [t for t in tokens if len(t) > 1]


def _score_text(query: str, text: str) -> int:
    if not text:
        return 0
    q = (query or "").lower().strip()
    t = text.lower()
    score = 0
    if q and q in t:
        score += 100
    for token in _tokenize_query(q):
        if token in t:
            score += 10
    return score


def _run_coro_safely(coro):
    """Run coroutine from sync context; skip when loop already running."""
    try:
        asyncio.get_running_loop()
        # Flask sync workers generally do not have a running loop.
        return None
    except RuntimeError:
        return asyncio.run(coro)


def _humanize_ingest_error(err: Exception) -> str:
    """Convert low-level storage exceptions to actionable Chinese messages."""
    raw = str(err) or err.__class__.__name__
    lower = raw.lower()

    if "property values can only be of primitive types" in lower:
        return (
            "Neo4j写入失败：检测到不支持的属性类型（Map/Object）。"
            "系统已改为JSON字符串存储属性；请重试当前构建任务。"
        )
    if "connection" in lower and "neo4j" in lower:
        return "Neo4j连接失败，请检查 NEO4J_URI/NEO4J_USER/NEO4J_PASSWORD 与数据库状态。"
    if "authentication" in lower or "unauthorized" in lower:
        return "Neo4j认证失败，请检查 NEO4J_USER/NEO4J_PASSWORD 是否正确。"

    return f"图谱写入失败：{raw}"


@dataclass
class _EpisodeObj:
    uuid_: str
    processed: bool = True
    data: str = ""
    type: str = "text"
    created_at: Optional[str] = None

    @property
    def uuid(self) -> str:
        return self.uuid_


@dataclass
class _NodeObj:
    uuid_: str
    name: str = ""
    labels: list[str] = field(default_factory=list)
    summary: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None

    @property
    def uuid(self) -> str:
        return self.uuid_


@dataclass
class _EdgeObj:
    uuid_: str
    name: str = ""
    fact: str = ""
    source_node_uuid: str = ""
    target_node_uuid: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None
    valid_at: Optional[str] = None
    invalid_at: Optional[str] = None
    expired_at: Optional[str] = None
    episode_ids: list[str] = field(default_factory=list)

    @property
    def uuid(self) -> str:
        return self.uuid_

    @property
    def episodes(self) -> list[str]:
        return self.episode_ids


@dataclass
class _SearchResultObj:
    edges: list[_EdgeObj] = field(default_factory=list)
    nodes: list[_NodeObj] = field(default_factory=list)


class _GraphitiMirror:
    """Best-effort Graphiti side-write. Failures never block core flow."""

    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        self._graphiti = None
        self._episode_type_text = None
        enabled = os.environ.get('GRAPHITI_ENABLED', 'true').lower() == 'true'
        if not enabled:
            logger.info("Graphiti mirror disabled by GRAPHITI_ENABLED=false")
            return

        try:
            from graphiti_core import Graphiti  # type: ignore
            from graphiti_core.nodes import EpisodeType  # type: ignore
        except Exception as e:  # pragma: no cover - depends on environment
            logger.warning(f"Graphiti import failed, fallback to Neo4j-only mode: {e}")
            return

        try:
            self._graphiti = Graphiti(neo4j_uri, neo4j_user, neo4j_password)
            # Prefer text source enum when available.
            self._episode_type_text = getattr(EpisodeType, 'text', None) or getattr(EpisodeType, 'message', None)
            _run_coro_safely(self._graphiti.build_indices_and_constraints())
            logger.info("Graphiti mirror initialized")
        except Exception as e:  # pragma: no cover - runtime dependent
            logger.warning(f"Graphiti init failed, continuing in Neo4j-only mode: {e}")
            self._graphiti = None
            self._episode_type_text = None

    def add_episode(self, graph_id: str, episode_uuid: str, text: str):
        if not self._graphiti or not self._episode_type_text:
            return
        try:
            _run_coro_safely(
                self._graphiti.add_episode(
                    name=f"{graph_id}:{episode_uuid}",
                    episode_body=_clean_text(text, 20000),
                    source_description=f"MiroFish graph {graph_id}",
                    reference_time=datetime.now(timezone.utc),
                    source=self._episode_type_text,
                )
            )
        except Exception as e:  # pragma: no cover - best effort
            logger.debug(f"Graphiti episode mirror skipped: {e}")


class _EpisodeAPI:
    def __init__(self, graph_api: "_GraphAPI"):
        self._graph = graph_api

    def get(self, uuid_: str):
        return self._graph._get_episode(uuid_)


class _NodeAPI:
    def __init__(self, graph_api: "_GraphAPI"):
        self._graph = graph_api

    def get_by_graph_id(self, graph_id: str, limit: int = 100, uuid_cursor: Optional[str] = None):
        return self._graph._get_nodes_by_graph_id(graph_id=graph_id, limit=limit, uuid_cursor=uuid_cursor)

    def get(self, uuid_: str):
        return self._graph._get_node(uuid_)

    def get_entity_edges(self, node_uuid: str):
        return self._graph._get_node_edges(node_uuid)


class _EdgeAPI:
    def __init__(self, graph_api: "_GraphAPI"):
        self._graph = graph_api

    def get_by_graph_id(self, graph_id: str, limit: int = 100, uuid_cursor: Optional[str] = None):
        return self._graph._get_edges_by_graph_id(graph_id=graph_id, limit=limit, uuid_cursor=uuid_cursor)


class _GraphAPI:
    def __init__(self, driver, graphiti_mirror: Optional[_GraphitiMirror]):
        self._driver = driver
        self._graphiti_mirror = graphiti_mirror

        self.node = _NodeAPI(self)
        self.edge = _EdgeAPI(self)
        self.episode = _EpisodeAPI(self)

        self._llm_client = None

    # ===== Public compatibility methods =====

    def create(self, graph_id: str, name: str = "", description: str = ""):
        now = _now_iso()
        with self._driver.session() as session:
            session.run(
                """
                MERGE (g:MiroGraph {graph_id: $graph_id})
                ON CREATE SET g.name = $name,
                              g.description = $description,
                              g.created_at = $now,
                              g.updated_at = $now
                ON MATCH SET g.name = CASE WHEN $name <> '' THEN $name ELSE g.name END,
                             g.description = CASE WHEN $description <> '' THEN $description ELSE g.description END,
                             g.updated_at = $now
                """,
                graph_id=graph_id,
                name=name or "",
                description=description or "",
                now=now,
            )
        return {"graph_id": graph_id}

    def set_ontology(self, graph_ids: list[str], entities=None, edges=None):
        ontology = self._serialize_ontology(entities=entities, edges=edges)
        now = _now_iso()
        ontology_json = json.dumps(ontology, ensure_ascii=False)
        entity_type_names = [e.get("name", "") for e in ontology.get("entity_types", []) if e.get("name")]
        edge_type_names = [e.get("name", "") for e in ontology.get("edge_types", []) if e.get("name")]

        with self._driver.session() as session:
            for graph_id in graph_ids or []:
                session.run(
                    """
                    MERGE (g:MiroGraph {graph_id: $graph_id})
                    ON CREATE SET g.created_at = $now
                    SET g.ontology_json = $ontology_json,
                        g.entity_types = $entity_types,
                        g.edge_types = $edge_types,
                        g.updated_at = $now
                    """,
                    graph_id=graph_id,
                    ontology_json=ontology_json,
                    entity_types=entity_type_names,
                    edge_types=edge_type_names,
                    now=now,
                )
        return {"graph_ids": graph_ids}

    def add_batch(self, graph_id: str, episodes: list[EpisodeData]):
        self.create(graph_id=graph_id, name=graph_id, description="")
        results: list[_EpisodeObj] = []

        for ep in episodes or []:
            episode_uuid = str(uuid.uuid4())
            ep_text = str(getattr(ep, 'data', '') or '')
            ep_type = str(getattr(ep, 'type', 'text') or 'text')
            now = _now_iso()

            with self._driver.session() as session:
                session.run(
                    """
                    CREATE (e:MiroEpisode {
                        graph_id: $graph_id,
                        uuid: $uuid,
                        type: $type,
                        data: $data,
                        processed: true,
                        created_at: $now
                    })
                    """,
                    graph_id=graph_id,
                    uuid=episode_uuid,
                    type=ep_type,
                    data=_clean_text(ep_text, 20000),
                    now=now,
                )

            try:
                if ep_text.strip():
                    self._ingest_episode(graph_id=graph_id, episode_uuid=episode_uuid, text=ep_text)
            except Exception as e:
                friendly = _humanize_ingest_error(e)
                logger.exception("Episode ingest failed: %s", e)
                raise InternalServerError(f"Episode ingest failed: {friendly}") from e

            if self._graphiti_mirror:
                self._graphiti_mirror.add_episode(graph_id=graph_id, episode_uuid=episode_uuid, text=ep_text)

            results.append(_EpisodeObj(uuid_=episode_uuid, processed=True, data=ep_text, type=ep_type, created_at=now))

        return results

    def add(self, graph_id: str, type: str, data: str):
        batch = self.add_batch(graph_id=graph_id, episodes=[EpisodeData(data=data, type=type)])
        return batch[0] if batch else None

    def search(
        self,
        graph_id: str,
        query: str,
        limit: int = 10,
        scope: str = "edges",
        reranker: Optional[str] = None,
        **kwargs,
    ):
        del reranker, kwargs
        scope = (scope or "edges").lower()
        result = _SearchResultObj()

        if scope in ("edges", "both"):
            edges = self._get_edges_by_graph_id(graph_id=graph_id, limit=5000, uuid_cursor=None)
            scored_edges = []
            node_map = {n.uuid_: n for n in self._get_nodes_by_graph_id(graph_id=graph_id, limit=5000, uuid_cursor=None)}
            for e in edges:
                source_name = node_map.get(e.source_node_uuid, _NodeObj("")).name
                target_name = node_map.get(e.target_node_uuid, _NodeObj("")).name
                text = " ".join([e.fact or "", e.name or "", source_name or "", target_name or ""])
                score = _score_text(query, text)
                if score > 0:
                    scored_edges.append((score, e))
            scored_edges.sort(key=lambda x: x[0], reverse=True)
            result.edges = [e for _, e in scored_edges[: max(limit, 1)]]

        if scope in ("nodes", "both"):
            nodes = self._get_nodes_by_graph_id(graph_id=graph_id, limit=5000, uuid_cursor=None)
            scored_nodes = []
            for n in nodes:
                text = " ".join([n.name or "", n.summary or "", " ".join(n.labels or [])])
                score = _score_text(query, text)
                if score > 0:
                    scored_nodes.append((score, n))
            scored_nodes.sort(key=lambda x: x[0], reverse=True)
            result.nodes = [n for _, n in scored_nodes[: max(limit, 1)]]

        return result

    def delete(self, graph_id: str):
        with self._driver.session() as session:
            # Delete relationships first to avoid any cross-residue.
            session.run(
                """
                MATCH ()-[r:MIRO_EDGE {graph_id: $graph_id}]-()
                DELETE r
                """,
                graph_id=graph_id,
            )
            session.run(
                """
                MATCH (n)
                WHERE n.graph_id = $graph_id
                DETACH DELETE n
                """,
                graph_id=graph_id,
            )
        return {"graph_id": graph_id, "deleted": True}

    # ===== Read APIs used by zep_paging and services =====

    def _get_nodes_by_graph_id(self, graph_id: str, limit: int = 100, uuid_cursor: Optional[str] = None):
        with self._driver.session() as session:
            records = session.run(
                """
                MATCH (n:MiroNode {graph_id: $graph_id})
                WHERE $uuid_cursor IS NULL OR n.uuid > $uuid_cursor
                RETURN n
                ORDER BY n.uuid
                LIMIT $limit
                """,
                graph_id=graph_id,
                uuid_cursor=uuid_cursor,
                limit=max(1, int(limit or 100)),
            )
            return [self._node_from_props(dict(r["n"])) for r in records]

    def _get_edges_by_graph_id(self, graph_id: str, limit: int = 100, uuid_cursor: Optional[str] = None):
        with self._driver.session() as session:
            records = session.run(
                """
                MATCH (s:MiroNode {graph_id: $graph_id})-[r:MIRO_EDGE {graph_id: $graph_id}]->(t:MiroNode {graph_id: $graph_id})
                WHERE $uuid_cursor IS NULL OR r.uuid > $uuid_cursor
                RETURN s, r, t
                ORDER BY r.uuid
                LIMIT $limit
                """,
                graph_id=graph_id,
                uuid_cursor=uuid_cursor,
                limit=max(1, int(limit or 100)),
            )
            return [self._edge_from_record(r) for r in records]

    def _get_node(self, uuid_: str):
        with self._driver.session() as session:
            record = session.run(
                """
                MATCH (n:MiroNode {uuid: $uuid})
                RETURN n
                LIMIT 1
                """,
                uuid=uuid_,
            ).single()
            if not record:
                return None
            return self._node_from_props(dict(record["n"]))

    def _get_node_edges(self, node_uuid: str):
        with self._driver.session() as session:
            records = session.run(
                """
                MATCH (s:MiroNode)-[r:MIRO_EDGE]->(t:MiroNode)
                WHERE s.uuid = $node_uuid OR t.uuid = $node_uuid
                RETURN s, r, t
                ORDER BY r.created_at, r.uuid
                """,
                node_uuid=node_uuid,
            )
            return [self._edge_from_record(r) for r in records]

    def _get_episode(self, uuid_: str):
        with self._driver.session() as session:
            record = session.run(
                """
                MATCH (e:MiroEpisode {uuid: $uuid})
                RETURN e
                LIMIT 1
                """,
                uuid=uuid_,
            ).single()

            if not record:
                # Return processed=True to avoid wait loops on missing records.
                return _EpisodeObj(uuid_=uuid_, processed=True)

            props = dict(record["e"])
            return _EpisodeObj(
                uuid_=str(props.get("uuid", uuid_)),
                processed=bool(props.get("processed", True)),
                data=str(props.get("data", "")),
                type=str(props.get("type", "text")),
                created_at=props.get("created_at"),
            )

    # ===== Internal conversion =====

    def _node_from_props(self, props: dict[str, Any]) -> _NodeObj:
        attrs = _ensure_dict(props.get("attributes_json"))
        if not attrs:
            attrs = _ensure_dict(props.get("attributes"))
        return _NodeObj(
            uuid_=str(props.get("uuid", "")),
            name=str(props.get("name", "")),
            labels=_normalize_labels(props.get("labels")),
            summary=str(props.get("summary", "")),
            attributes=attrs,
            created_at=props.get("created_at"),
        )

    def _edge_from_record(self, record) -> _EdgeObj:
        source = dict(record["s"])
        rel = dict(record["r"])
        target = dict(record["t"])
        attrs = _ensure_dict(rel.get("attributes_json"))
        if not attrs:
            attrs = _ensure_dict(rel.get("attributes"))
        return _EdgeObj(
            uuid_=str(rel.get("uuid", "")),
            name=str(rel.get("name", "")),
            fact=str(rel.get("fact", "")),
            source_node_uuid=str(source.get("uuid", "")),
            target_node_uuid=str(target.get("uuid", "")),
            attributes=attrs,
            created_at=rel.get("created_at"),
            valid_at=rel.get("valid_at"),
            invalid_at=rel.get("invalid_at"),
            expired_at=rel.get("expired_at"),
            episode_ids=[str(i) for i in _ensure_list(rel.get("episode_ids"))],
        )

    # ===== Ontology & extraction =====

    def _serialize_ontology(self, entities=None, edges=None) -> dict[str, Any]:
        entity_types = []
        edge_types = []

        for name, model in (entities or {}).items():
            fields = getattr(model, "model_fields", {}) or {}
            attrs = []
            for field_name, field_info in fields.items():
                desc = ""
                if getattr(field_info, "description", None):
                    desc = str(field_info.description)
                attrs.append({"name": field_name, "description": desc})
            entity_types.append({
                "name": str(name),
                "description": getattr(model, "__doc__", "") or "",
                "attributes": attrs,
            })

        for edge_name, edge_val in (edges or {}).items():
            edge_model = edge_val[0] if isinstance(edge_val, tuple) and edge_val else edge_val
            source_targets = edge_val[1] if isinstance(edge_val, tuple) and len(edge_val) > 1 else []
            fields = getattr(edge_model, "model_fields", {}) or {}
            attrs = []
            for field_name, field_info in fields.items():
                desc = ""
                if getattr(field_info, "description", None):
                    desc = str(field_info.description)
                attrs.append({"name": field_name, "description": desc})
            edge_types.append({
                "name": str(edge_name),
                "description": getattr(edge_model, "__doc__", "") or "",
                "attributes": attrs,
                "source_targets": [
                    {
                        "source": str(getattr(st, "source", "")),
                        "target": str(getattr(st, "target", "")),
                    }
                    for st in source_targets or []
                ],
            })

        return {"entity_types": entity_types, "edge_types": edge_types}

    def _get_graph_ontology(self, graph_id: str) -> dict[str, Any]:
        with self._driver.session() as session:
            record = session.run(
                """
                MATCH (g:MiroGraph {graph_id: $graph_id})
                RETURN g.ontology_json AS ontology_json
                LIMIT 1
                """,
                graph_id=graph_id,
            ).single()
        if not record:
            return {"entity_types": [], "edge_types": []}
        raw = record.get("ontology_json")
        if not raw:
            return {"entity_types": [], "edge_types": []}
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
        return {"entity_types": [], "edge_types": []}

    def _get_llm_client(self):
        if self._llm_client is not None:
            return self._llm_client
        if OpenAI is None:
            return None
        api_key = os.environ.get("LLM_API_KEY")
        if not api_key:
            return None
        base_url = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
        self._llm_client = OpenAI(api_key=api_key, base_url=base_url)
        return self._llm_client

    def _extract_from_llm(self, text: str, ontology: dict[str, Any]) -> Optional[dict[str, Any]]:
        llm = self._get_llm_client()
        if llm is None:
            return None

        entity_types = [e.get("name", "") for e in ontology.get("entity_types", []) if e.get("name")]
        edge_types = [e.get("name", "") for e in ontology.get("edge_types", []) if e.get("name")]
        model_name = os.environ.get("LLM_MODEL_NAME", "gpt-4o-mini")

        system_prompt = (
            "你是知识图谱抽取器。"
            "请从输入文本中提取实体与关系。"
            "必须严格输出 JSON 对象，字段仅包含 entities 和 relations。"
        )

        user_prompt = (
            "请从以下文本抽取图谱信息。\n"
            f"实体类型候选: {entity_types or ['Entity']}\n"
            f"关系类型候选: {edge_types or ['RELATED_TO']}\n\n"
            "输出格式:\n"
            "{\n"
            '  "entities": [{"name":"", "type":"", "summary":"", "attributes":{}}],\n'
            '  "relations": [{"source":"", "target":"", "type":"", "fact":"", "attributes":{}}]\n'
            "}\n\n"
            f"文本:\n{_clean_text(text, 6000)}"
        )

        try:
            resp = llm.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )
            content = (resp.choices[0].message.content or "").strip()
            data = json.loads(content)
            if not isinstance(data, dict):
                return None
            entities = data.get("entities", [])
            relations = data.get("relations", data.get("edges", []))
            if not isinstance(entities, list):
                entities = []
            if not isinstance(relations, list):
                relations = []
            return {"entities": entities, "relations": relations}
        except Exception as e:
            logger.debug(f"LLM extraction failed, using heuristic fallback: {e}")
            return None

    def _extract_heuristic(self, text: str, ontology: dict[str, Any]) -> dict[str, Any]:
        entity_types = [e.get("name", "") for e in ontology.get("entity_types", []) if e.get("name")]
        default_entity_type = entity_types[0] if entity_types else "Entity"
        edge_types = [e.get("name", "") for e in ontology.get("edge_types", []) if e.get("name")]
        default_edge_type = edge_types[0] if edge_types else "RELATED_TO"

        zh_terms = re.findall(r"[\u4e00-\u9fff]{2,8}", text or "")
        en_terms = re.findall(r"[A-Za-z][A-Za-z0-9_\-]{2,}", text or "")

        stopwords = {"我们", "你们", "他们", "这个", "那个", "以及", "如果", "因为", "所以", "进行", "可以"}
        terms = []
        for term in zh_terms + en_terms:
            t = term.strip()
            if not t or t in stopwords:
                continue
            if t not in terms:
                terms.append(t)
            if len(terms) >= 12:
                break

        if not terms:
            snippet = _clean_text(text.replace("\n", " "), 20)
            terms = [snippet or "未知实体"]

        entities = [
            {
                "name": term,
                "type": default_entity_type,
                "summary": "",
                "attributes": {},
            }
            for term in terms
        ]

        relations = []
        for i in range(len(terms) - 1):
            source = terms[i]
            target = terms[i + 1]
            if source == target:
                continue
            relations.append(
                {
                    "source": source,
                    "target": target,
                    "type": default_edge_type,
                    "fact": f"{source} 与 {target} 在文本中存在关联",
                    "attributes": {},
                }
            )
            if len(relations) >= 24:
                break

        return {"entities": entities, "relations": relations}

    def _extract_structured(self, graph_id: str, text: str) -> dict[str, Any]:
        ontology = self._get_graph_ontology(graph_id)
        parsed = self._extract_from_llm(text=text, ontology=ontology)
        if parsed is None:
            parsed = self._extract_heuristic(text=text, ontology=ontology)
        return parsed

    def _ingest_episode(self, graph_id: str, episode_uuid: str, text: str):
        extracted = self._extract_structured(graph_id=graph_id, text=text)
        entities = extracted.get("entities", []) if isinstance(extracted, dict) else []
        relations = extracted.get("relations", []) if isinstance(extracted, dict) else []

        ontology = self._get_graph_ontology(graph_id)
        entity_types = [e.get("name", "") for e in ontology.get("entity_types", []) if e.get("name")]
        edge_types = [e.get("name", "") for e in ontology.get("edge_types", []) if e.get("name")]
        default_entity_type = entity_types[0] if entity_types else "Entity"
        default_edge_type = edge_types[0] if edge_types else "RELATED_TO"

        name_to_uuid: dict[str, str] = {}

        for entity in entities:
            if not isinstance(entity, dict):
                continue
            node_uuid = self._upsert_entity(
                graph_id=graph_id,
                entity=entity,
                default_entity_type=default_entity_type,
            )
            name = str(entity.get("name", "")).strip()
            if name and node_uuid:
                name_to_uuid[name] = node_uuid

        if not name_to_uuid:
            fallback_name = _clean_text((text or "").replace("\n", " "), 24) or "未知实体"
            node_uuid = self._upsert_entity(
                graph_id=graph_id,
                entity={"name": fallback_name, "type": default_entity_type, "summary": "", "attributes": {}},
                default_entity_type=default_entity_type,
            )
            name_to_uuid[fallback_name] = node_uuid

        created_relation = False
        for relation in relations:
            if not isinstance(relation, dict):
                continue
            ok = self._upsert_relation(
                graph_id=graph_id,
                relation=relation,
                name_to_uuid=name_to_uuid,
                default_entity_type=default_entity_type,
                default_edge_type=default_edge_type,
                episode_uuid=episode_uuid,
            )
            created_relation = created_relation or ok

        # Ensure graph isn't relation-empty for downstream tools.
        if not created_relation and len(name_to_uuid) >= 2:
            names = list(name_to_uuid.keys())[:2]
            self._upsert_relation(
                graph_id=graph_id,
                relation={
                    "source": names[0],
                    "target": names[1],
                    "type": default_edge_type,
                    "fact": f"{names[0]} 与 {names[1]} 在同一段文本中出现",
                    "attributes": {},
                },
                name_to_uuid=name_to_uuid,
                default_entity_type=default_entity_type,
                default_edge_type=default_edge_type,
                episode_uuid=episode_uuid,
            )

    def _upsert_entity(self, graph_id: str, entity: dict[str, Any], default_entity_type: str) -> str:
        name = str(entity.get("name", "")).strip()
        if not name:
            return ""
        entity_type = str(entity.get("type", "")).strip() or default_entity_type
        labels = _normalize_labels(["Entity", entity_type])
        summary = str(entity.get("summary", "") or "")
        attributes = _ensure_dict(entity.get("attributes"))
        attributes_json = _dict_to_json(attributes)

        name_lc = name.lower()
        node_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{graph_id}:{name_lc}"))
        now = _now_iso()

        with self._driver.session() as session:
            existing = session.run(
                """
                MATCH (n:MiroNode {graph_id: $graph_id, name_lc: $name_lc})
                RETURN n
                LIMIT 1
                """,
                graph_id=graph_id,
                name_lc=name_lc,
            ).single()

            if existing:
                props = dict(existing["n"])
                merged_labels = list(dict.fromkeys(_normalize_labels(props.get("labels")) + labels))
                merged_attrs = _ensure_dict(props.get("attributes_json"))
                if not merged_attrs:
                    merged_attrs = _ensure_dict(props.get("attributes"))
                merged_attrs.update(attributes)
                merged_attrs_json = _dict_to_json(merged_attrs)
                merged_summary = str(props.get("summary") or summary or "")
                session.run(
                    """
                    MATCH (n:MiroNode {graph_id: $graph_id, name_lc: $name_lc})
                    SET n.name = $name,
                        n.labels = $labels,
                        n.summary = $summary,
                        n.attributes_json = $attributes_json,
                        n.updated_at = $now
                    """,
                    graph_id=graph_id,
                    name_lc=name_lc,
                    name=name,
                    labels=merged_labels,
                    summary=merged_summary,
                    attributes_json=merged_attrs_json,
                    now=now,
                )
                return str(props.get("uuid", node_uuid))

            session.run(
                """
                CREATE (n:MiroNode {
                    graph_id: $graph_id,
                    uuid: $uuid,
                    name: $name,
                    name_lc: $name_lc,
                    labels: $labels,
                    summary: $summary,
                    attributes_json: $attributes_json,
                    created_at: $now,
                    updated_at: $now
                })
                """,
                graph_id=graph_id,
                uuid=node_uuid,
                name=name,
                name_lc=name_lc,
                labels=labels,
                summary=summary,
                attributes_json=attributes_json,
                now=now,
            )

        return node_uuid

    def _upsert_relation(
        self,
        graph_id: str,
        relation: dict[str, Any],
        name_to_uuid: dict[str, str],
        default_entity_type: str,
        default_edge_type: str,
        episode_uuid: str,
    ) -> bool:
        source_name = str(relation.get("source", "")).strip()
        target_name = str(relation.get("target", "")).strip()
        if not source_name or not target_name:
            return False

        source_uuid = name_to_uuid.get(source_name)
        if not source_uuid:
            source_uuid = self._upsert_entity(
                graph_id=graph_id,
                entity={"name": source_name, "type": default_entity_type, "summary": "", "attributes": {}},
                default_entity_type=default_entity_type,
            )
            name_to_uuid[source_name] = source_uuid

        target_uuid = name_to_uuid.get(target_name)
        if not target_uuid:
            target_uuid = self._upsert_entity(
                graph_id=graph_id,
                entity={"name": target_name, "type": default_entity_type, "summary": "", "attributes": {}},
                default_entity_type=default_entity_type,
            )
            name_to_uuid[target_name] = target_uuid

        if not source_uuid or not target_uuid:
            return False

        edge_name = str(relation.get("type", "")).strip() or default_edge_type
        fact = str(relation.get("fact", "")).strip() or f"{source_name} {edge_name} {target_name}"
        attributes = _ensure_dict(relation.get("attributes"))
        attributes_json = _dict_to_json(attributes)

        rel_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{graph_id}:{source_uuid}:{edge_name}:{target_uuid}:{fact}"))
        now = _now_iso()

        with self._driver.session() as session:
            session.run(
                """
                MATCH (s:MiroNode {graph_id: $graph_id, uuid: $source_uuid})
                MATCH (t:MiroNode {graph_id: $graph_id, uuid: $target_uuid})
                MERGE (s)-[r:MIRO_EDGE {graph_id: $graph_id, uuid: $uuid}]->(t)
                ON CREATE SET r.name = $name,
                              r.fact = $fact,
                              r.attributes_json = $attributes_json,
                              r.created_at = $now,
                              r.valid_at = $now,
                              r.invalid_at = null,
                              r.expired_at = null,
                              r.episode_ids = [$episode_uuid],
                              r.updated_at = $now
                ON MATCH SET r.name = CASE WHEN r.name IS NULL OR r.name = '' THEN $name ELSE r.name END,
                             r.fact = CASE WHEN r.fact IS NULL OR r.fact = '' THEN $fact ELSE r.fact END,
                             r.attributes_json = CASE
                                 WHEN r.attributes_json IS NULL OR r.attributes_json = '' THEN $attributes_json
                                 ELSE r.attributes_json
                             END,
                             r.episode_ids = CASE
                                 WHEN $episode_uuid IN coalesce(r.episode_ids, []) THEN coalesce(r.episode_ids, [])
                                 ELSE coalesce(r.episode_ids, []) + $episode_uuid
                             END,
                             r.updated_at = $now
                """,
                graph_id=graph_id,
                source_uuid=source_uuid,
                target_uuid=target_uuid,
                uuid=rel_uuid,
                name=edge_name,
                fact=fact,
                attributes_json=attributes_json,
                episode_uuid=episode_uuid,
                now=now,
            )
        return True


class Zep:
    """
    Compatibility client preserving the project's expected Zep interface.
    """

    _init_lock = Lock()
    _driver = None
    _schema_ready = False
    _graphiti_mirror: Optional[_GraphitiMirror] = None

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or "local-neo4j"
        self._ensure_initialized()
        self.graph = _GraphAPI(self.__class__._driver, self.__class__._graphiti_mirror)

    @classmethod
    def _ensure_initialized(cls):
        with cls._init_lock:
            if cls._driver is None:
                uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
                user = os.environ.get("NEO4J_USER", "neo4j")
                password = os.environ.get("NEO4J_PASSWORD", "mirofish123")
                try:
                    cls._driver = GraphDatabase.driver(uri, auth=(user, password))
                    with cls._driver.session() as session:
                        session.run("RETURN 1").single()
                    logger.info(f"Neo4j connected: {uri}")
                except Exception as e:
                    raise RuntimeError(f"Neo4j connection failed ({uri}): {e}") from e

                cls._graphiti_mirror = _GraphitiMirror(uri, user, password)

            if not cls._schema_ready:
                cls._setup_schema()
                cls._schema_ready = True

    @classmethod
    def _setup_schema(cls):
        statements = [
            "CREATE CONSTRAINT miro_graph_id IF NOT EXISTS FOR (g:MiroGraph) REQUIRE g.graph_id IS UNIQUE",
            "CREATE CONSTRAINT miro_episode_uuid IF NOT EXISTS FOR (e:MiroEpisode) REQUIRE e.uuid IS UNIQUE",
            "CREATE CONSTRAINT miro_node_composite IF NOT EXISTS FOR (n:MiroNode) REQUIRE (n.graph_id, n.uuid) IS UNIQUE",
            "CREATE INDEX miro_node_graph_name IF NOT EXISTS FOR (n:MiroNode) ON (n.graph_id, n.name_lc)",
            "CREATE INDEX miro_edge_graph_uuid IF NOT EXISTS FOR ()-[r:MIRO_EDGE]-() ON (r.graph_id, r.uuid)",
        ]
        with cls._driver.session() as session:
            for stmt in statements:
                try:
                    session.run(stmt)
                except Exception as e:
                    logger.debug(f"Schema statement skipped: {stmt} ({e})")

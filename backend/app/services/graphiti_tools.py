"""
Graphiti retrieval tools service
Encapsulates graph search, node reading, edge queries and other tools for Report Agent use

Core retrieval tools (optimized):
1. InsightForge (deep insight retrieval) - Most powerful hybrid retrieval
2. PanoramaSearch (broad search) - Get full picture, including expired content
3. QuickSearch (simple search) - Quick retrieval
"""

import json
import asyncio
import concurrent.futures
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from ..config import Config
from ..utils.logger import get_logger
from ..utils.llm_client import LLMClient
from .graphiti_client import get_graphiti

logger = get_logger('mirofish.graphiti_tools')


def _run_async(coro):
    """Bridge sync -> async."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


# ===================== Data classes (same interface as zep_tools) =====================


@dataclass
class SearchResult:
    """Search result"""
    facts: List[str]
    edges: List[Dict[str, Any]]
    nodes: List[Dict[str, Any]]
    query: str
    total_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "facts": self.facts,
            "edges": self.edges,
            "nodes": self.nodes,
            "query": self.query,
            "total_count": self.total_count,
        }

    def to_text(self) -> str:
        text_parts = [
            f"Search query: {self.query}",
            f"Found {self.total_count} related items",
        ]
        if self.facts:
            text_parts.append("\n### Related facts:")
            for i, fact in enumerate(self.facts, 1):
                text_parts.append(f"{i}. {fact}")
        return "\n".join(text_parts)


@dataclass
class NodeInfo:
    """Node info"""
    uuid: str
    name: str
    labels: List[str]
    summary: str
    attributes: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "uuid": self.uuid,
            "name": self.name,
            "labels": self.labels,
            "summary": self.summary,
            "attributes": self.attributes,
        }

    def to_text(self) -> str:
        entity_type = next(
            (l for l in self.labels if l not in ("Entity", "Node", "Episodic")),
            "Unknown type",
        )
        return f"Entity: {self.name} (type: {entity_type})\nSummary: {self.summary}"


@dataclass
class EdgeInfo:
    """Edge info"""
    uuid: str
    name: str
    fact: str
    source_node_uuid: str
    target_node_uuid: str
    source_node_name: Optional[str] = None
    target_node_name: Optional[str] = None
    created_at: Optional[str] = None
    valid_at: Optional[str] = None
    invalid_at: Optional[str] = None
    expired_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "uuid": self.uuid,
            "name": self.name,
            "fact": self.fact,
            "source_node_uuid": self.source_node_uuid,
            "target_node_uuid": self.target_node_uuid,
            "source_node_name": self.source_node_name,
            "target_node_name": self.target_node_name,
            "created_at": self.created_at,
            "valid_at": self.valid_at,
            "invalid_at": self.invalid_at,
            "expired_at": self.expired_at,
        }

    def to_text(self, include_temporal: bool = False) -> str:
        source = self.source_node_name or self.source_node_uuid[:8]
        target = self.target_node_name or self.target_node_uuid[:8]
        base_text = f"Relationship: {source} --[{self.name}]--> {target}\nFact: {self.fact}"
        if include_temporal:
            valid_at = self.valid_at or "Unknown"
            invalid_at = self.invalid_at or "Present"
            base_text += f"\nValidity: {valid_at} - {invalid_at}"
            if self.expired_at:
                base_text += f" (Expired: {self.expired_at})"
        return base_text

    @property
    def is_expired(self) -> bool:
        return self.expired_at is not None

    @property
    def is_invalid(self) -> bool:
        return self.invalid_at is not None


@dataclass
class InsightForgeResult:
    """Deep insight retrieval result"""
    query: str
    simulation_requirement: str
    sub_queries: List[str]
    semantic_facts: List[str] = field(default_factory=list)
    entity_insights: List[Dict[str, Any]] = field(default_factory=list)
    relationship_chains: List[str] = field(default_factory=list)
    total_facts: int = 0
    total_entities: int = 0
    total_relationships: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "simulation_requirement": self.simulation_requirement,
            "sub_queries": self.sub_queries,
            "semantic_facts": self.semantic_facts,
            "entity_insights": self.entity_insights,
            "relationship_chains": self.relationship_chains,
            "total_facts": self.total_facts,
            "total_entities": self.total_entities,
            "total_relationships": self.total_relationships,
        }

    def to_text(self) -> str:
        text_parts = [
            "## Deep Predictive Analysis",
            f"Analysis question: {self.query}",
            f"Prediction scenario: {self.simulation_requirement}",
            "\n### Prediction Data Statistics",
            f"- Related prediction facts: {self.total_facts}",
            f"- Involved entities: {self.total_entities}",
            f"- Relationship chains: {self.total_relationships}",
        ]
        if self.sub_queries:
            text_parts.append("\n### Analyzed Sub-questions")
            for i, sq in enumerate(self.sub_queries, 1):
                text_parts.append(f"{i}. {sq}")
        if self.semantic_facts:
            text_parts.append(
                "\n### [Key Facts] (please cite these in the report)"
            )
            for i, fact in enumerate(self.semantic_facts, 1):
                text_parts.append(f'{i}. "{fact}"')
        if self.entity_insights:
            text_parts.append("\n### [Core Entities]")
            for entity in self.entity_insights:
                text_parts.append(
                    f"- **{entity.get('name', 'Unknown')}** ({entity.get('type', 'Entity')})"
                )
                if entity.get("summary"):
                    text_parts.append(f'  Summary: "{entity.get("summary")}"')
                if entity.get("related_facts"):
                    text_parts.append(
                        f"  Related facts: {len(entity.get('related_facts', []))}"
                    )
        if self.relationship_chains:
            text_parts.append("\n### [Relationship Chains]")
            for chain in self.relationship_chains:
                text_parts.append(f"- {chain}")
        return "\n".join(text_parts)


@dataclass
class PanoramaResult:
    """Broad search result"""
    query: str
    all_nodes: List[NodeInfo] = field(default_factory=list)
    all_edges: List[EdgeInfo] = field(default_factory=list)
    active_facts: List[str] = field(default_factory=list)
    historical_facts: List[str] = field(default_factory=list)
    total_nodes: int = 0
    total_edges: int = 0
    active_count: int = 0
    historical_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "all_nodes": [n.to_dict() for n in self.all_nodes],
            "all_edges": [e.to_dict() for e in self.all_edges],
            "active_facts": self.active_facts,
            "historical_facts": self.historical_facts,
            "total_nodes": self.total_nodes,
            "total_edges": self.total_edges,
            "active_count": self.active_count,
            "historical_count": self.historical_count,
        }

    def to_text(self) -> str:
        text_parts = [
            "## Broad Search Results (Future Panoramic View)",
            f"Query: {self.query}",
            "\n### Statistics",
            f"- Total nodes: {self.total_nodes}",
            f"- Total edges: {self.total_edges}",
            f"- Current active facts: {self.active_count}",
            f"- Historical/expired facts: {self.historical_count}",
        ]
        if self.active_facts:
            text_parts.append(
                "\n### [Current Active Facts] (simulation result originals)"
            )
            for i, fact in enumerate(self.active_facts, 1):
                text_parts.append(f'{i}. "{fact}"')
        if self.historical_facts:
            text_parts.append(
                "\n### [Historical/Expired Facts] (evolution process records)"
            )
            for i, fact in enumerate(self.historical_facts, 1):
                text_parts.append(f'{i}. "{fact}"')
        if self.all_nodes:
            text_parts.append("\n### [Involved Entities]")
            for node in self.all_nodes:
                entity_type = next(
                    (l for l in node.labels if l not in ("Entity", "Node", "Episodic")),
                    "Entity",
                )
                text_parts.append(f"- **{node.name}** ({entity_type})")
        return "\n".join(text_parts)


@dataclass
class AgentInterview:
    """Single Agent interview result"""
    agent_name: str
    agent_role: str
    agent_bio: str
    question: str
    response: str
    key_quotes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "agent_role": self.agent_role,
            "agent_bio": self.agent_bio,
            "question": self.question,
            "response": self.response,
            "key_quotes": self.key_quotes,
        }

    def to_text(self) -> str:
        text = f"**{self.agent_name}** ({self.agent_role})\n"
        text += f"_Bio: {self.agent_bio}_\n\n"
        text += f"**Q:** {self.question}\n\n"
        text += f"**A:** {self.response}\n"
        if self.key_quotes:
            text += "\n**Key Quotes:**\n"
            for quote in self.key_quotes:
                clean_quote = quote.replace('\u201c', '').replace('\u201d', '').replace('"', '')
                clean_quote = clean_quote.replace('\u300c', '').replace('\u300d', '')
                clean_quote = clean_quote.strip()
                while clean_quote and clean_quote[0] in '\uff0c,\uff1b;\uff1a:\u3001\u3002\uff01\uff1f\n\r\t ':
                    clean_quote = clean_quote[1:]
                skip = False
                for d in '123456789':
                    if f'\u95ee\u9898{d}' in clean_quote:
                        skip = True
                        break
                if skip:
                    continue
                if len(clean_quote) > 150:
                    dot_pos = clean_quote.find('\u3002', 80)
                    if dot_pos > 0:
                        clean_quote = clean_quote[:dot_pos + 1]
                    else:
                        clean_quote = clean_quote[:147] + "..."
                if clean_quote and len(clean_quote) >= 10:
                    text += f'> "{clean_quote}"\n'
        return text


@dataclass
class InterviewResult:
    """Interview Result"""
    interview_topic: str
    interview_questions: List[str]
    selected_agents: List[Dict[str, Any]] = field(default_factory=list)
    interviews: List[AgentInterview] = field(default_factory=list)
    selection_reasoning: str = ""
    summary: str = ""
    total_agents: int = 0
    interviewed_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "interview_topic": self.interview_topic,
            "interview_questions": self.interview_questions,
            "selected_agents": self.selected_agents,
            "interviews": [i.to_dict() for i in self.interviews],
            "selection_reasoning": self.selection_reasoning,
            "summary": self.summary,
            "total_agents": self.total_agents,
            "interviewed_count": self.interviewed_count,
        }

    def to_text(self) -> str:
        text_parts = [
            "## In-depth Interview Report",
            f"**Interview Topic:** {self.interview_topic}",
            f"**Interviewees:** {self.interviewed_count} / {self.total_agents} simulation Agents",
            "\n### Agent Selection Reasoning",
            self.selection_reasoning or "(Auto-selected)",
            "\n---",
            "\n### Interview Transcripts",
        ]
        if self.interviews:
            for i, interview in enumerate(self.interviews, 1):
                text_parts.append(f"\n#### Interview #{i}: {interview.agent_name}")
                text_parts.append(interview.to_text())
                text_parts.append("\n---")
        else:
            text_parts.append("(No interview records)\n\n---")
        text_parts.append("\n### Interview Summary & Key Viewpoints")
        text_parts.append(self.summary or "(No summary)")
        return "\n".join(text_parts)


# ===================== Main service class =====================


class GraphitiToolsService:
    """
    Graphiti retrieval tools service

    [Core Retrieval Tools - Optimized]
    1. insight_forge - Deep insight retrieval
    2. panorama_search - Broad search
    3. quick_search - Simple search
    4. interview_agents - Deep interview

    [Basic Tools]
    - search_graph, get_all_nodes, get_all_edges, get_node_detail,
      get_node_edges, get_entities_by_type, get_entity_summary
    """

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self._llm_client = llm_client
        logger.info("GraphitiToolsService initialized")

    @property
    def llm(self) -> LLMClient:
        if self._llm_client is None:
            self._llm_client = LLMClient()
        return self._llm_client

    # ========== Search ==========

    def search_graph(
        self,
        graph_id: str,
        query: str,
        limit: int = 10,
        scope: str = "edges",
    ) -> SearchResult:
        """Graph hybrid search using Graphiti."""
        logger.info(f"Graph search: graph_id={graph_id}, query={query[:50]}...")
        try:
            return _run_async(
                self._search_graph_async(graph_id, query, limit, scope)
            )
        except Exception as e:
            logger.warning(f"Graphiti search failed, falling back to local: {str(e)}")
            return self._local_search(graph_id, query, limit, scope)

    async def _search_graph_async(
        self, graph_id: str, query: str, limit: int, scope: str
    ) -> SearchResult:
        graphiti = await get_graphiti()

        from graphiti_core.search.search_config_recipes import (
            EDGE_HYBRID_SEARCH_CROSS_ENCODER,
            NODE_HYBRID_SEARCH_RRF,
        )

        facts = []
        edges = []
        nodes = []

        if scope in ("edges", "both"):
            edge_results = await graphiti.search(
                query=query,
                config=EDGE_HYBRID_SEARCH_CROSS_ENCODER,
                group_ids=[graph_id],
                num_results=limit,
            )
            for edge in edge_results:
                fact = getattr(edge, "fact", "") or ""
                if fact:
                    facts.append(fact)
                edges.append({
                    "uuid": getattr(edge, "uuid", ""),
                    "name": getattr(edge, "name", ""),
                    "fact": fact,
                    "source_node_uuid": getattr(edge, "source_node_uuid", ""),
                    "target_node_uuid": getattr(edge, "target_node_uuid", ""),
                })

        if scope in ("nodes", "both"):
            node_results = await graphiti.search(
                query=query,
                config=NODE_HYBRID_SEARCH_RRF,
                group_ids=[graph_id],
                num_results=limit,
            )
            for node in node_results:
                node_name = getattr(node, "name", "")
                summary = getattr(node, "summary", "")
                nodes.append({
                    "uuid": getattr(node, "uuid", ""),
                    "name": node_name,
                    "labels": getattr(node, "labels", []),
                    "summary": summary,
                })
                if summary:
                    facts.append(f"[{node_name}]: {summary}")

        logger.info(f"Search complete: found {len(facts)} related facts")
        return SearchResult(
            facts=facts,
            edges=edges,
            nodes=nodes,
            query=query,
            total_count=len(facts),
        )

    def _local_search(
        self, graph_id: str, query: str, limit: int = 10, scope: str = "edges"
    ) -> SearchResult:
        """Local keyword matching search (fallback)"""
        logger.info(f"Using local search: query={query[:30]}...")
        facts = []
        edges_result = []
        nodes_result = []

        query_lower = query.lower()
        keywords = [
            w.strip()
            for w in query_lower.replace(",", " ").replace("\uff0c", " ").split()
            if len(w.strip()) > 1
        ]

        def match_score(text: str) -> int:
            if not text:
                return 0
            text_lower = text.lower()
            if query_lower in text_lower:
                return 100
            score = 0
            for keyword in keywords:
                if keyword in text_lower:
                    score += 10
            return score

        try:
            if scope in ("edges", "both"):
                all_edges = self.get_all_edges(graph_id)
                scored = [(match_score(e.fact) + match_score(e.name), e) for e in all_edges]
                scored = [(s, e) for s, e in scored if s > 0]
                scored.sort(key=lambda x: x[0], reverse=True)
                for _, edge in scored[:limit]:
                    if edge.fact:
                        facts.append(edge.fact)
                    edges_result.append({
                        "uuid": edge.uuid,
                        "name": edge.name,
                        "fact": edge.fact,
                        "source_node_uuid": edge.source_node_uuid,
                        "target_node_uuid": edge.target_node_uuid,
                    })
            if scope in ("nodes", "both"):
                all_nodes = self.get_all_nodes(graph_id)
                scored = [(match_score(n.name) + match_score(n.summary), n) for n in all_nodes]
                scored = [(s, n) for s, n in scored if s > 0]
                scored.sort(key=lambda x: x[0], reverse=True)
                for _, node in scored[:limit]:
                    nodes_result.append({
                        "uuid": node.uuid,
                        "name": node.name,
                        "labels": node.labels,
                        "summary": node.summary,
                    })
                    if node.summary:
                        facts.append(f"[{node.name}]: {node.summary}")
            logger.info(f"Local search complete: found {len(facts)} related facts")
        except Exception as e:
            logger.error(f"Local search failed: {str(e)}")

        return SearchResult(
            facts=facts, edges=edges_result, nodes=nodes_result,
            query=query, total_count=len(facts),
        )

    # ========== Node / Edge accessors ==========

    def get_all_nodes(self, graph_id: str) -> List[NodeInfo]:
        """Get all nodes from graph"""
        return _run_async(self._get_all_nodes_async(graph_id))

    async def _get_all_nodes_async(self, graph_id: str) -> List[NodeInfo]:
        graphiti = await get_graphiti()
        driver = graphiti.driver
        records, _, _ = await driver.execute_query(
            "MATCH (n:Entity) WHERE n.group_id = $gid RETURN n", gid=graph_id
        )
        result = []
        for rec in records:
            node = rec["n"]
            result.append(NodeInfo(
                uuid=node.element_id,
                name=node.get("name", ""),
                labels=list(node.labels),
                summary=node.get("summary", ""),
                attributes=dict(node),
            ))
        logger.info(f"Fetched {len(result)} nodes")
        return result

    def get_all_edges(self, graph_id: str, include_temporal: bool = True) -> List[EdgeInfo]:
        """Get all edges from graph"""
        return _run_async(self._get_all_edges_async(graph_id, include_temporal))

    async def _get_all_edges_async(self, graph_id: str, include_temporal: bool) -> List[EdgeInfo]:
        graphiti = await get_graphiti()
        driver = graphiti.driver
        records, _, _ = await driver.execute_query(
            "MATCH (s)-[r:RELATES_TO]->(t) WHERE r.group_id = $gid RETURN s, r, t",
            gid=graph_id,
        )
        result = []
        for rec in records:
            s_node = rec["s"]
            rel = rec["r"]
            t_node = rec["t"]
            edge_info = EdgeInfo(
                uuid=rel.element_id,
                name=rel.get("name", ""),
                fact=rel.get("fact", ""),
                source_node_uuid=s_node.element_id,
                target_node_uuid=t_node.element_id,
                source_node_name=s_node.get("name", ""),
                target_node_name=t_node.get("name", ""),
            )
            if include_temporal:
                edge_info.created_at = rel.get("created_at")
                edge_info.valid_at = rel.get("valid_at")
                edge_info.invalid_at = rel.get("invalid_at")
                edge_info.expired_at = rel.get("expired_at")
            result.append(edge_info)
        logger.info(f"Fetched {len(result)} edges")
        return result

    def get_node_detail(self, node_uuid: str) -> Optional[NodeInfo]:
        """Get detailed info for a single node"""
        return _run_async(self._get_node_detail_async(node_uuid))

    async def _get_node_detail_async(self, node_uuid: str) -> Optional[NodeInfo]:
        graphiti = await get_graphiti()
        driver = graphiti.driver
        try:
            records, _, _ = await driver.execute_query(
                "MATCH (n) WHERE elementId(n) = $nid RETURN n", nid=node_uuid
            )
            if not records:
                return None
            node = records[0]["n"]
            return NodeInfo(
                uuid=node.element_id,
                name=node.get("name", ""),
                labels=list(node.labels),
                summary=node.get("summary", ""),
                attributes=dict(node),
            )
        except Exception as e:
            logger.error(f"Failed to get node detail: {str(e)}")
            return None

    def get_node_edges(self, graph_id: str, node_uuid: str) -> List[EdgeInfo]:
        """Get all edges related to a node"""
        all_edges = self.get_all_edges(graph_id)
        return [
            e for e in all_edges
            if e.source_node_uuid == node_uuid or e.target_node_uuid == node_uuid
        ]

    def get_entities_by_type(self, graph_id: str, entity_type: str) -> List[NodeInfo]:
        """Get entities by type"""
        all_nodes = self.get_all_nodes(graph_id)
        return [n for n in all_nodes if entity_type in n.labels]

    def get_entity_summary(self, graph_id: str, entity_name: str) -> Dict[str, Any]:
        """Get relationship summary for a specified entity"""
        search_result = self.search_graph(graph_id=graph_id, query=entity_name, limit=20)
        all_nodes = self.get_all_nodes(graph_id)
        entity_node = None
        for node in all_nodes:
            if node.name.lower() == entity_name.lower():
                entity_node = node
                break
        related_edges = []
        if entity_node:
            related_edges = self.get_node_edges(graph_id, entity_node.uuid)
        return {
            "entity_name": entity_name,
            "entity_info": entity_node.to_dict() if entity_node else None,
            "related_facts": search_result.facts,
            "related_edges": [e.to_dict() for e in related_edges],
            "total_relations": len(related_edges),
        }

    def get_graph_statistics(self, graph_id: str) -> Dict[str, Any]:
        """Get graph statistics"""
        nodes = self.get_all_nodes(graph_id)
        edges = self.get_all_edges(graph_id)
        entity_types = {}
        for node in nodes:
            for label in node.labels:
                if label not in ("Entity", "Node", "Episodic"):
                    entity_types[label] = entity_types.get(label, 0) + 1
        relation_types = {}
        for edge in edges:
            relation_types[edge.name] = relation_types.get(edge.name, 0) + 1
        return {
            "graph_id": graph_id,
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "entity_types": entity_types,
            "relation_types": relation_types,
        }

    def get_simulation_context(
        self, graph_id: str, simulation_requirement: str, limit: int = 30
    ) -> Dict[str, Any]:
        """Get simulation-related context information"""
        search_result = self.search_graph(
            graph_id=graph_id, query=simulation_requirement, limit=limit
        )
        stats = self.get_graph_statistics(graph_id)
        all_nodes = self.get_all_nodes(graph_id)
        entities = []
        for node in all_nodes:
            custom_labels = [
                l for l in node.labels if l not in ("Entity", "Node", "Episodic")
            ]
            if custom_labels:
                entities.append({
                    "name": node.name,
                    "type": custom_labels[0],
                    "summary": node.summary,
                })
        return {
            "simulation_requirement": simulation_requirement,
            "related_facts": search_result.facts,
            "graph_statistics": stats,
            "entities": entities[:limit],
            "total_entities": len(entities),
        }

    # ========== Core Retrieval Tools ==========

    def insight_forge(
        self,
        graph_id: str,
        query: str,
        simulation_requirement: str,
        report_context: str = "",
        max_sub_queries: int = 5,
    ) -> InsightForgeResult:
        """[InsightForge - Deep Insight Retrieval]"""
        logger.info(f"InsightForge deep insight retrieval: {query[:50]}...")
        result = InsightForgeResult(
            query=query, simulation_requirement=simulation_requirement, sub_queries=[]
        )

        sub_queries = self._generate_sub_queries(
            query=query,
            simulation_requirement=simulation_requirement,
            report_context=report_context,
            max_queries=max_sub_queries,
        )
        result.sub_queries = sub_queries

        all_facts = []
        all_edges = []
        seen_facts = set()

        for sub_query in sub_queries:
            sr = self.search_graph(graph_id=graph_id, query=sub_query, limit=15, scope="edges")
            for fact in sr.facts:
                if fact not in seen_facts:
                    all_facts.append(fact)
                    seen_facts.add(fact)
            all_edges.extend(sr.edges)

        main_search = self.search_graph(graph_id=graph_id, query=query, limit=20, scope="edges")
        for fact in main_search.facts:
            if fact not in seen_facts:
                all_facts.append(fact)
                seen_facts.add(fact)

        result.semantic_facts = all_facts
        result.total_facts = len(all_facts)

        entity_uuids = set()
        for edge_data in all_edges:
            if isinstance(edge_data, dict):
                for key in ("source_node_uuid", "target_node_uuid"):
                    val = edge_data.get(key, "")
                    if val:
                        entity_uuids.add(val)

        entity_insights = []
        node_map = {}
        for uid in entity_uuids:
            if not uid:
                continue
            try:
                node = self.get_node_detail(uid)
                if node:
                    node_map[uid] = node
                    entity_type = next(
                        (l for l in node.labels if l not in ("Entity", "Node", "Episodic")),
                        "Entity",
                    )
                    related_facts = [f for f in all_facts if node.name.lower() in f.lower()]
                    entity_insights.append({
                        "uuid": node.uuid,
                        "name": node.name,
                        "type": entity_type,
                        "summary": node.summary,
                        "related_facts": related_facts,
                    })
            except Exception as e:
                logger.debug(f"Failed to get node {uid}: {e}")

        result.entity_insights = entity_insights
        result.total_entities = len(entity_insights)

        relationship_chains = []
        for edge_data in all_edges:
            if isinstance(edge_data, dict):
                source_uuid = edge_data.get("source_node_uuid", "")
                target_uuid = edge_data.get("target_node_uuid", "")
                relation_name = edge_data.get("name", "")
                source_name = (
                    node_map.get(source_uuid, NodeInfo("", "", [], "", {})).name
                    or source_uuid[:8]
                )
                target_name = (
                    node_map.get(target_uuid, NodeInfo("", "", [], "", {})).name
                    or target_uuid[:8]
                )
                chain = f"{source_name} --[{relation_name}]--> {target_name}"
                if chain not in relationship_chains:
                    relationship_chains.append(chain)

        result.relationship_chains = relationship_chains
        result.total_relationships = len(relationship_chains)

        logger.info(
            f"InsightForge complete: {result.total_facts} facts, "
            f"{result.total_entities} entities, {result.total_relationships} relationships"
        )
        return result

    def _generate_sub_queries(
        self,
        query: str,
        simulation_requirement: str,
        report_context: str = "",
        max_queries: int = 5,
    ) -> List[str]:
        """Use LLM to generate sub-questions"""
        system_prompt = (
            "You are a professional question analysis expert. Your task is to decompose "
            "a complex question into multiple sub-questions that can be independently "
            "observed in the simulation world.\n\n"
            "Requirements:\n"
            "1. Each sub-question should be specific enough to find related Agent behaviors\n"
            "2. Sub-questions should cover different dimensions\n"
            "3. Sub-questions should be related to the simulation scenario\n"
            '4. Return JSON format: {"sub_queries": ["sub-question 1", ...]}'
        )
        user_prompt = (
            f"Simulation requirement background:\n{simulation_requirement}\n\n"
            f"{f'Report context: {report_context[:500]}' if report_context else ''}\n\n"
            f"Please decompose the following question into {max_queries} sub-questions:\n"
            f"{query}\n\nReturn sub-question list in JSON format."
        )
        try:
            response = self.llm.chat_json(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
            )
            return [str(sq) for sq in response.get("sub_queries", [])[:max_queries]]
        except Exception as e:
            logger.warning(f"Failed to generate sub-queries: {str(e)}")
            return [
                query,
                f"Main participants in {query}",
                f"Causes and effects of {query}",
                f"Development process of {query}",
            ][:max_queries]

    def panorama_search(
        self,
        graph_id: str,
        query: str,
        include_expired: bool = True,
        limit: int = 50,
    ) -> PanoramaResult:
        """[PanoramaSearch - Broad Search]"""
        logger.info(f"PanoramaSearch broad search: {query[:50]}...")
        result = PanoramaResult(query=query)

        all_nodes = self.get_all_nodes(graph_id)
        node_map = {n.uuid: n for n in all_nodes}
        result.all_nodes = all_nodes
        result.total_nodes = len(all_nodes)

        all_edges = self.get_all_edges(graph_id, include_temporal=True)
        result.all_edges = all_edges
        result.total_edges = len(all_edges)

        active_facts = []
        historical_facts = []

        for edge in all_edges:
            if not edge.fact:
                continue
            is_historical = edge.is_expired or edge.is_invalid
            if is_historical:
                valid_at = edge.valid_at or "Unknown"
                invalid_at = edge.invalid_at or edge.expired_at or "Unknown"
                historical_facts.append(f"[{valid_at} - {invalid_at}] {edge.fact}")
            else:
                active_facts.append(edge.fact)

        query_lower = query.lower()
        keywords = [
            w.strip()
            for w in query_lower.replace(",", " ").replace("\uff0c", " ").split()
            if len(w.strip()) > 1
        ]

        def relevance_score(fact: str) -> int:
            fl = fact.lower()
            score = 0
            if query_lower in fl:
                score += 100
            for kw in keywords:
                if kw in fl:
                    score += 10
            return score

        active_facts.sort(key=relevance_score, reverse=True)
        historical_facts.sort(key=relevance_score, reverse=True)

        result.active_facts = active_facts[:limit]
        result.historical_facts = historical_facts[:limit] if include_expired else []
        result.active_count = len(active_facts)
        result.historical_count = len(historical_facts)

        logger.info(f"PanoramaSearch complete: {result.active_count} active, {result.historical_count} historical")
        return result

    def quick_search(self, graph_id: str, query: str, limit: int = 10) -> SearchResult:
        """[QuickSearch - Simple Search]"""
        logger.info(f"QuickSearch simple search: {query[:50]}...")
        result = self.search_graph(graph_id=graph_id, query=query, limit=limit, scope="edges")
        logger.info(f"QuickSearch complete: {result.total_count} results")
        return result

    def interview_agents(
        self,
        simulation_id: str,
        interview_requirement: str,
        simulation_requirement: str = "",
        max_agents: int = 5,
        custom_questions: List[str] = None,
    ) -> InterviewResult:
        """[InterviewAgents - Deep Interview] (same logic, no Zep dependency)"""
        from .simulation_runner import SimulationRunner
        import re

        logger.info(f"InterviewAgents deep interview: {interview_requirement[:50]}...")
        result = InterviewResult(
            interview_topic=interview_requirement,
            interview_questions=custom_questions or [],
        )

        profiles = self._load_agent_profiles(simulation_id)
        if not profiles:
            result.summary = "No interviewable Agent persona files found"
            return result

        result.total_agents = len(profiles)

        selected_agents, selected_indices, selection_reasoning = (
            self._select_agents_for_interview(
                profiles=profiles,
                interview_requirement=interview_requirement,
                simulation_requirement=simulation_requirement,
                max_agents=max_agents,
            )
        )
        result.selected_agents = selected_agents
        result.selection_reasoning = selection_reasoning

        if not result.interview_questions:
            result.interview_questions = self._generate_interview_questions(
                interview_requirement=interview_requirement,
                simulation_requirement=simulation_requirement,
                selected_agents=selected_agents,
            )

        combined_prompt = "\n".join(
            [f"{i+1}. {q}" for i, q in enumerate(result.interview_questions)]
        )
        INTERVIEW_PROMPT_PREFIX = (
            "You are being interviewed. Please combine your persona, all past memories and actions, "
            "and directly answer the following questions in plain text.\n"
            "Reply Requirements:\n"
            "1. Answer directly in natural language, do not call any tools\n"
            "2. Do not return JSON format or tool call format\n"
            "3. Do not use Markdown headings (like #, ##, ###)\n"
            "4. Answer each question by number, starting each answer with \"Question X:\"\n"
            "5. Separate answers between questions with blank lines\n"
            "6. Answers should have substance, at least 2-3 sentences per question\n\n"
        )
        optimized_prompt = f"{INTERVIEW_PROMPT_PREFIX}{combined_prompt}"

        try:
            interviews_request = []
            for agent_idx in selected_indices:
                interviews_request.append({
                    "agent_id": agent_idx,
                    "prompt": optimized_prompt,
                })

            api_result = SimulationRunner.interview_agents_batch(
                simulation_id=simulation_id,
                interviews=interviews_request,
                platform=None,
                timeout=180.0,
            )

            if not api_result.get("success", False):
                result.summary = f"Interview API call failed: {api_result.get('error', 'Unknown')}"
                return result

            api_data = api_result.get("result", {})
            results_dict = api_data.get("results", {}) if isinstance(api_data, dict) else {}

            for i, agent_idx in enumerate(selected_indices):
                agent = selected_agents[i]
                agent_name = agent.get("realname", agent.get("username", f"Agent_{agent_idx}"))
                agent_role = agent.get("profession", "Unknown")
                agent_bio = agent.get("bio", "")

                twitter_result = results_dict.get(f"twitter_{agent_idx}", {})
                reddit_result = results_dict.get(f"reddit_{agent_idx}", {})
                twitter_response = self._clean_tool_call_response(twitter_result.get("response", ""))
                reddit_response = self._clean_tool_call_response(reddit_result.get("response", ""))

                twitter_text = twitter_response or "(No response on this platform)"
                reddit_text = reddit_response or "(No response on this platform)"
                response_text = f"[Twitter Platform Response]\n{twitter_text}\n\n[Reddit Platform Response]\n{reddit_text}"

                combined_responses = f"{twitter_response} {reddit_response}"
                clean_text = re.sub(r'#{1,6}\s+', '', combined_responses)
                clean_text = re.sub(r'\{[^}]*tool_name[^}]*\}', '', clean_text)
                clean_text = re.sub(r'[*_`|>~\-]{2,}', '', clean_text)
                clean_text = re.sub(r'Question\s*\d+[:\uff1a]\s*', '', clean_text)
                clean_text = re.sub(r'\u3010[^\u3011]+\u3011', '', clean_text)

                sentences = re.split(r'[\u3002\uff01\uff1f]', clean_text)
                meaningful = [
                    s.strip() for s in sentences
                    if 20 <= len(s.strip()) <= 150
                    and not re.match(r'^[\s\W\uff0c,\uff1b;\uff1a:\u3001]+', s.strip())
                    and not s.strip().startswith(('{', 'Question'))
                ]
                meaningful.sort(key=len, reverse=True)
                key_quotes = [s + "\u3002" for s in meaningful[:3]]

                if not key_quotes:
                    paired = re.findall(r'\u201c([^\u201c\u201d]{15,100})\u201d', clean_text)
                    paired += re.findall(r'\u300c([^\u300c\u300d]{15,100})\u300d', clean_text)
                    key_quotes = [q for q in paired if not re.match(r'^[\uff0c,\uff1b;\uff1a:\u3001]', q)][:3]

                interview = AgentInterview(
                    agent_name=agent_name,
                    agent_role=agent_role,
                    agent_bio=agent_bio[:1000],
                    question=combined_prompt,
                    response=response_text,
                    key_quotes=key_quotes[:5],
                )
                result.interviews.append(interview)

            result.interviewed_count = len(result.interviews)

        except ValueError as e:
            result.summary = f"Interview failed: {str(e)}"
            return result
        except Exception as e:
            logger.error(f"Interview API call exception: {e}")
            result.summary = f"Error occurred during interview: {str(e)}"
            return result

        if result.interviews:
            result.summary = self._generate_interview_summary(
                interviews=result.interviews,
                interview_requirement=interview_requirement,
            )

        logger.info(f"InterviewAgents complete: interviewed {result.interviewed_count} Agents")
        return result

    @staticmethod
    def _clean_tool_call_response(response: str) -> str:
        if not response or not response.strip().startswith('{'):
            return response
        text = response.strip()
        if 'tool_name' not in text[:80]:
            return response
        import re as _re
        try:
            data = json.loads(text)
            if isinstance(data, dict) and 'arguments' in data:
                for key in ('content', 'text', 'body', 'message', 'reply'):
                    if key in data['arguments']:
                        return str(data['arguments'][key])
        except (json.JSONDecodeError, KeyError, TypeError):
            match = _re.search(r'"content"\s*:\s*"((?:[^"\\]|\\.)*)"', text)
            if match:
                return match.group(1).replace('\\n', '\n').replace('\\"', '"')
        return response

    def _load_agent_profiles(self, simulation_id: str) -> List[Dict[str, Any]]:
        import os
        import csv
        sim_dir = os.path.join(
            os.path.dirname(__file__),
            f'../../uploads/simulations/{simulation_id}',
        )
        profiles = []
        reddit_path = os.path.join(sim_dir, "reddit_profiles.json")
        if os.path.exists(reddit_path):
            try:
                with open(reddit_path, 'r', encoding='utf-8') as f:
                    profiles = json.load(f)
                return profiles
            except Exception as e:
                logger.warning(f"Failed to read reddit_profiles.json: {e}")
        twitter_path = os.path.join(sim_dir, "twitter_profiles.csv")
        if os.path.exists(twitter_path):
            try:
                with open(twitter_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        profiles.append({
                            "realname": row.get("name", ""),
                            "username": row.get("username", ""),
                            "bio": row.get("description", ""),
                            "persona": row.get("user_char", ""),
                            "profession": "Unknown",
                        })
                return profiles
            except Exception as e:
                logger.warning(f"Failed to read twitter_profiles.csv: {e}")
        return profiles

    def _select_agents_for_interview(self, profiles, interview_requirement, simulation_requirement, max_agents):
        agent_summaries = []
        for i, profile in enumerate(profiles):
            agent_summaries.append({
                "index": i,
                "name": profile.get("realname", profile.get("username", f"Agent_{i}")),
                "profession": profile.get("profession", "Unknown"),
                "bio": profile.get("bio", "")[:200],
                "interested_topics": profile.get("interested_topics", []),
            })
        system_prompt = (
            "You are a professional interview planning expert. Select the most suitable "
            "interview subjects from the simulation Agent list based on interview requirements.\n\n"
            "Selection criteria:\n"
            "1. Agent identity/profession is related to interview topic\n"
            "2. Agent may hold unique or valuable viewpoints\n"
            "3. Select diverse perspectives\n"
            "4. Prioritize roles directly related to the event\n\n"
            'Return JSON format:\n{"selected_indices": [...], "reasoning": "..."}'
        )
        user_prompt = (
            f"Interview requirement:\n{interview_requirement}\n\n"
            f"Simulation background:\n{simulation_requirement or 'Not provided'}\n\n"
            f"Available Agent list (total {len(agent_summaries)}):\n"
            f"{json.dumps(agent_summaries, ensure_ascii=False, indent=2)}\n\n"
            f"Please select up to {max_agents} most suitable Agents."
        )
        try:
            response = self.llm.chat_json(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
            )
            selected_indices = response.get("selected_indices", [])[:max_agents]
            reasoning = response.get("reasoning", "Auto-selected")
            selected_agents = []
            valid_indices = []
            for idx in selected_indices:
                if 0 <= idx < len(profiles):
                    selected_agents.append(profiles[idx])
                    valid_indices.append(idx)
            return selected_agents, valid_indices, reasoning
        except Exception as e:
            logger.warning(f"LLM Agent selection failed: {e}")
            selected = profiles[:max_agents]
            indices = list(range(min(max_agents, len(profiles))))
            return selected, indices, "Using default selection strategy"

    def _generate_interview_questions(self, interview_requirement, simulation_requirement, selected_agents):
        agent_roles = [a.get("profession", "Unknown") for a in selected_agents]
        system_prompt = (
            "You are a professional journalist. Generate 3-5 interview questions.\n\n"
            "Requirements:\n1. Open-ended\n2. Cover multiple dimensions\n3. Natural language\n"
            '4. Return JSON: {"questions": [...]}'
        )
        user_prompt = (
            f"Interview requirement: {interview_requirement}\n"
            f"Simulation background: {simulation_requirement or 'Not provided'}\n"
            f"Interviewee roles: {', '.join(agent_roles)}\n"
            "Please generate 3-5 interview questions."
        )
        try:
            response = self.llm.chat_json(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.5,
            )
            return response.get("questions", [f"What are your views on {interview_requirement}?"])
        except Exception:
            return [
                f"What is your opinion on {interview_requirement}?",
                "What impact does this have on you?",
                "How do you think this should be solved?",
            ]

    def _generate_interview_summary(self, interviews, interview_requirement):
        if not interviews:
            return "No interviews completed"
        interview_texts = []
        for iv in interviews:
            interview_texts.append(f"[{iv.agent_name} ({iv.agent_role})]\n{iv.response[:500]}")
        system_prompt = (
            "You are a professional news editor. Based on interviewees' responses, "
            "generate an interview summary.\n\n"
            "Requirements:\n1. Distill main viewpoints\n2. Identify consensus and disagreements\n"
            "3. Highlight quotes\n4. Be objective\n5. Keep within 1000 words\n\n"
            "Format: plain text paragraphs, no Markdown headings."
        )
        user_prompt = (
            f"Interview topic: {interview_requirement}\n\n"
            f"Interview content:\n{''.join(interview_texts)}\n\n"
            "Please generate summary."
        )
        try:
            return self.llm.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=800,
            )
        except Exception:
            return f"Interviewed {len(interviews)} respondents: " + ", ".join(
                [i.agent_name for i in interviews]
            )

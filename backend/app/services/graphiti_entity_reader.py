"""
Graphiti entity reading and filtering service
Reads nodes from Graphiti/Neo4j graph and filters those matching predefined entity types
"""

import asyncio
import concurrent.futures
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field

from ..config import Config
from ..utils.logger import get_logger
from .graphiti_client import get_graphiti

logger = get_logger('mirofish.graphiti_entity_reader')


def _safe(obj):
    """Convert Neo4j types (DateTime etc.) to JSON-safe values."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (list, tuple)):
        return [_safe(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _safe(v) for k, v in obj.items()}
    return str(obj)


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


@dataclass
class EntityNode:
    """Entity node data structure"""
    uuid: str
    name: str
    labels: List[str]
    summary: str
    attributes: Dict[str, Any]
    related_edges: List[Dict[str, Any]] = field(default_factory=list)
    related_nodes: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "uuid": self.uuid,
            "name": self.name,
            "labels": self.labels,
            "summary": self.summary,
            "attributes": self.attributes,
            "related_edges": self.related_edges,
            "related_nodes": self.related_nodes,
        }

    def get_entity_type(self) -> Optional[str]:
        """Get entity type (excluding default Entity label)"""
        for label in self.labels:
            if label not in ("Entity", "Node", "Episodic"):
                return label
        return None


@dataclass
class FilteredEntities:
    """Filtered entity set"""
    entities: List[EntityNode]
    entity_types: Set[str]
    total_count: int
    filtered_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entities": [e.to_dict() for e in self.entities],
            "entity_types": list(self.entity_types),
            "total_count": self.total_count,
            "filtered_count": self.filtered_count,
        }


class GraphitiEntityReader:
    """
    Graphiti entity reading and filtering service

    Main functions:
    1. Read all entity nodes from Neo4j graph filtered by group_id
    2. Filter nodes matching predefined entity types
    3. Get related edges and associated node information for each entity
    """

    def __init__(self):
        pass

    def get_all_nodes(self, graph_id: str) -> List[Dict[str, Any]]:
        """Get all entity nodes of the graph"""
        return _run_async(self._get_all_nodes_async(graph_id))

    async def _get_all_nodes_async(self, graph_id: str) -> List[Dict[str, Any]]:
        graphiti = await get_graphiti()
        driver = graphiti.driver

        records, _, _ = await driver.execute_query(
            "MATCH (n:Entity) WHERE n.group_id = $gid RETURN n",
            gid=graph_id,
        )

        nodes_data = []
        for rec in records:
            node = rec["n"]
            nodes_data.append({
                "uuid": node.element_id,
                "name": node.get("name", ""),
                "labels": list(node.labels),
                "summary": node.get("summary", ""),
                "attributes": _safe(dict(node)),
            })

        logger.info(f"Fetched {len(nodes_data)} nodes from graph {graph_id}")
        return nodes_data

    def get_all_edges(self, graph_id: str) -> List[Dict[str, Any]]:
        """Get all edges of the graph"""
        return _run_async(self._get_all_edges_async(graph_id))

    async def _get_all_edges_async(self, graph_id: str) -> List[Dict[str, Any]]:
        graphiti = await get_graphiti()
        driver = graphiti.driver

        records, _, _ = await driver.execute_query(
            "MATCH (s)-[r:RELATES_TO]->(t) WHERE r.group_id = $gid RETURN s, r, t",
            gid=graph_id,
        )

        edges_data = []
        for rec in records:
            s_node = rec["s"]
            rel = rec["r"]
            t_node = rec["t"]
            edges_data.append({
                "uuid": rel.element_id,
                "name": rel.get("name", ""),
                "fact": rel.get("fact", ""),
                "source_node_uuid": s_node.element_id,
                "target_node_uuid": t_node.element_id,
                "attributes": _safe(dict(rel)),
            })

        logger.info(f"Fetched {len(edges_data)} edges from graph {graph_id}")
        return edges_data

    def get_node_edges(self, node_uuid: str) -> List[Dict[str, Any]]:
        """Get all related edges for a specific node"""
        return _run_async(self._get_node_edges_async(node_uuid))

    async def _get_node_edges_async(self, node_uuid: str) -> List[Dict[str, Any]]:
        graphiti = await get_graphiti()
        driver = graphiti.driver

        try:
            records, _, _ = await driver.execute_query(
                """
                MATCH (n) WHERE elementId(n) = $nid
                MATCH (n)-[r:RELATES_TO]-(other)
                RETURN n, r, other
                """,
                nid=node_uuid,
            )

            edges_data = []
            for rec in records:
                rel = rec["r"]
                other = rec["other"]
                edges_data.append({
                    "uuid": rel.element_id,
                    "name": rel.get("name", ""),
                    "fact": rel.get("fact", ""),
                    "source_node_uuid": rel.start_node.element_id if hasattr(rel, 'start_node') else "",
                    "target_node_uuid": rel.end_node.element_id if hasattr(rel, 'end_node') else "",
                    "attributes": _safe(dict(rel)),
                })
            return edges_data
        except Exception as e:
            logger.warning(f"Failed to get edges for node {node_uuid}: {str(e)}")
            return []

    def filter_defined_entities(
        self,
        graph_id: str,
        defined_entity_types: Optional[List[str]] = None,
        enrich_with_edges: bool = True,
    ) -> FilteredEntities:
        """
        Filter nodes matching predefined entity types

        Filtering logic:
        - If a node's Labels only contain "Entity", it does not match and is skipped
        - If a node's Labels contain labels beyond "Entity" and "Node", it matches
        """
        logger.info(f"Starting entity filtering for graph {graph_id}...")

        all_nodes = self.get_all_nodes(graph_id)
        total_count = len(all_nodes)

        all_edges = self.get_all_edges(graph_id) if enrich_with_edges else []

        node_map = {n["uuid"]: n for n in all_nodes}

        filtered_entities = []
        entity_types_found = set()

        for node in all_nodes:
            labels = node.get("labels", [])

            custom_labels = [
                l for l in labels if l not in ("Entity", "Node", "Episodic")
            ]

            # Graphiti may not add custom labels — use "Entity" as fallback
            if custom_labels:
                entity_type = custom_labels[0]
            else:
                entity_type = "Entity"

            if defined_entity_types and entity_type != "Entity":
                if entity_type not in defined_entity_types:
                    continue

            entity_types_found.add(entity_type)

            entity = EntityNode(
                uuid=node["uuid"],
                name=node["name"],
                labels=labels,
                summary=node["summary"],
                attributes=node["attributes"],
            )

            if enrich_with_edges:
                related_edges = []
                related_node_uuids = set()

                for edge in all_edges:
                    if edge["source_node_uuid"] == node["uuid"]:
                        related_edges.append({
                            "direction": "outgoing",
                            "edge_name": edge["name"],
                            "fact": edge["fact"],
                            "target_node_uuid": edge["target_node_uuid"],
                        })
                        related_node_uuids.add(edge["target_node_uuid"])
                    elif edge["target_node_uuid"] == node["uuid"]:
                        related_edges.append({
                            "direction": "incoming",
                            "edge_name": edge["name"],
                            "fact": edge["fact"],
                            "source_node_uuid": edge["source_node_uuid"],
                        })
                        related_node_uuids.add(edge["source_node_uuid"])

                entity.related_edges = related_edges

                related_nodes = []
                for related_uuid in related_node_uuids:
                    if related_uuid in node_map:
                        related_node = node_map[related_uuid]
                        related_nodes.append({
                            "uuid": related_node["uuid"],
                            "name": related_node["name"],
                            "labels": related_node["labels"],
                            "summary": related_node.get("summary", ""),
                        })
                entity.related_nodes = related_nodes

            filtered_entities.append(entity)

        logger.info(
            f"Filtering complete: total nodes {total_count}, eligible {len(filtered_entities)}, "
            f"entity types: {entity_types_found}"
        )

        return FilteredEntities(
            entities=filtered_entities,
            entity_types=entity_types_found,
            total_count=total_count,
            filtered_count=len(filtered_entities),
        )

    def get_entity_with_context(
        self, graph_id: str, entity_uuid: str
    ) -> Optional[EntityNode]:
        """Get a single entity with full context (edges and related nodes)"""
        return _run_async(self._get_entity_with_context_async(graph_id, entity_uuid))

    async def _get_entity_with_context_async(
        self, graph_id: str, entity_uuid: str
    ) -> Optional[EntityNode]:
        graphiti = await get_graphiti()
        driver = graphiti.driver

        try:
            records, _, _ = await driver.execute_query(
                "MATCH (n) WHERE elementId(n) = $nid RETURN n",
                nid=entity_uuid,
            )
            if not records:
                return None

            node = records[0]["n"]

            # Get edges
            edge_records, _, _ = await driver.execute_query(
                """
                MATCH (n) WHERE elementId(n) = $nid
                MATCH (n)-[r:RELATES_TO]-(other)
                RETURN r, other, startNode(r) AS src, endNode(r) AS tgt
                """,
                nid=entity_uuid,
            )

            # Get all nodes for lookup
            all_nodes_data = await self._get_all_nodes_async(graph_id)
            node_map = {n["uuid"]: n for n in all_nodes_data}

            related_edges = []
            related_node_uuids = set()

            for erec in edge_records:
                rel = erec["r"]
                src = erec["src"]
                tgt = erec["tgt"]
                src_id = src.element_id
                tgt_id = tgt.element_id

                if src_id == entity_uuid:
                    related_edges.append({
                        "direction": "outgoing",
                        "edge_name": rel.get("name", ""),
                        "fact": rel.get("fact", ""),
                        "target_node_uuid": tgt_id,
                    })
                    related_node_uuids.add(tgt_id)
                else:
                    related_edges.append({
                        "direction": "incoming",
                        "edge_name": rel.get("name", ""),
                        "fact": rel.get("fact", ""),
                        "source_node_uuid": src_id,
                    })
                    related_node_uuids.add(src_id)

            related_nodes = []
            for related_uuid in related_node_uuids:
                if related_uuid in node_map:
                    rn = node_map[related_uuid]
                    related_nodes.append({
                        "uuid": rn["uuid"],
                        "name": rn["name"],
                        "labels": rn["labels"],
                        "summary": rn.get("summary", ""),
                    })

            return EntityNode(
                uuid=node.element_id,
                name=node.get("name", ""),
                labels=list(node.labels),
                summary=node.get("summary", ""),
                attributes=dict(node),
                related_edges=related_edges,
                related_nodes=related_nodes,
            )

        except Exception as e:
            logger.error(f"Failed to get entity {entity_uuid}: {str(e)}")
            return None

    def get_entities_by_type(
        self,
        graph_id: str,
        entity_type: str,
        enrich_with_edges: bool = True,
    ) -> List[EntityNode]:
        """Get all entities of a specific type"""
        result = self.filter_defined_entities(
            graph_id=graph_id,
            defined_entity_types=[entity_type],
            enrich_with_edges=enrich_with_edges,
        )
        return result.entities

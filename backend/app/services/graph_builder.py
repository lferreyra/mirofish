"""
Graph building service
Interface 2: Build Standalone Graph using Graphiti + Neo4j
"""

import os
import uuid
import time
import asyncio
import threading
import concurrent.futures
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime

from ..config import Config
from ..models.task import TaskManager, TaskStatus
from .text_processor import TextProcessor
from .graphiti_client import get_graphiti
from ..utils.logger import get_logger

logger = get_logger('mirofish.graph_builder')


def _run_async(coro):
    """Bridge sync -> async. Works whether or not an event loop is already running."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


@dataclass
class GraphInfo:
    """Graph information"""
    graph_id: str
    node_count: int
    edge_count: int
    entity_types: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "entity_types": self.entity_types,
        }


class GraphBuilderService:
    """
    Graph building service
    Responsible for calling Graphiti to build knowledge graphs
    """

    def __init__(self):
        self.task_manager = TaskManager()

    def build_graph_async(
        self,
        text: str,
        ontology: Dict[str, Any],
        graph_name: str = "MiroFish Graph",
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        batch_size: int = 3,
    ) -> str:
        """
        Build graph asynchronously

        Args:
            text: Input text
            ontology: Ontology definition (output from Interface 1)
            graph_name: Graph name
            chunk_size: Text chunk size
            chunk_overlap: Chunk overlap size
            batch_size: Number of chunks per batch

        Returns:
            Task ID
        """
        task_id = self.task_manager.create_task(
            task_type="graph_build",
            metadata={
                "graph_name": graph_name,
                "chunk_size": chunk_size,
                "text_length": len(text),
            },
        )

        thread = threading.Thread(
            target=self._build_graph_worker,
            args=(
                task_id,
                text,
                ontology,
                graph_name,
                chunk_size,
                chunk_overlap,
                batch_size,
            ),
        )
        thread.daemon = True
        thread.start()

        return task_id

    def _build_graph_worker(
        self,
        task_id: str,
        text: str,
        ontology: Dict[str, Any],
        graph_name: str,
        chunk_size: int,
        chunk_overlap: int,
        batch_size: int,
    ):
        """Graph building worker thread"""
        try:
            self.task_manager.update_task(
                task_id,
                status=TaskStatus.PROCESSING,
                progress=5,
                message="Starting graph construction...",
            )

            # 1. Create graph (group_id)
            graph_id = self.create_graph(graph_name)
            self.task_manager.update_task(
                task_id, progress=10, message=f"Graph created: {graph_id}"
            )

            # 2. Ontology is used as entity/edge type hints for add_episode_bulk
            self.task_manager.update_task(
                task_id, progress=15, message="Ontology configured"
            )

            # 3. Split text into chunks
            chunks = TextProcessor.split_text(text, chunk_size, chunk_overlap)
            total_chunks = len(chunks)
            self.task_manager.update_task(
                task_id,
                progress=20,
                message=f"Text split into {total_chunks} chunks",
            )

            # 4. Send data in batches
            self.add_text_batches(
                graph_id,
                chunks,
                batch_size,
                lambda msg, prog: self.task_manager.update_task(
                    task_id,
                    progress=20 + int(prog * 0.6),  # 20-80%
                    message=msg,
                ),
            )

            # 5. Graphiti processes synchronously during add_episode_bulk,
            #    no separate wait needed.
            self.task_manager.update_task(
                task_id, progress=85, message="Retrieving graph information..."
            )

            # 6. Get graph information
            graph_info = self._get_graph_info(graph_id)

            self.task_manager.complete_task(
                task_id,
                {
                    "graph_id": graph_id,
                    "graph_info": graph_info.to_dict(),
                    "chunks_processed": total_chunks,
                },
            )

        except Exception as e:
            import traceback

            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            self.task_manager.fail_task(task_id, error_msg)

    def create_graph(self, name: str) -> str:
        """
        Create a new graph (returns a group_id).
        Graphiti uses group_id to partition data; no separate graph creation API needed.
        """
        graph_id = f"mirofish_{uuid.uuid4().hex[:16]}"
        return graph_id

    def set_ontology(self, graph_id: str, ontology: Dict[str, Any]):
        """
        Store ontology for later use.
        Graphiti does not have a separate set_ontology API; entity_types and
        edge_types are passed to add_episode / add_episode_bulk calls.
        This is a no-op kept for interface compatibility.
        """
        pass

    def add_text_batches(
        self,
        graph_id: str,
        chunks: List[str],
        batch_size: int = 3,
        progress_callback: Optional[Callable] = None,
    ) -> List[str]:
        """Add text to graph in batches using Graphiti add_episode_bulk"""
        from graphiti_core.types import RawEpisode, EpisodeType

        total_chunks = len(chunks)

        for i in range(0, total_chunks, batch_size):
            batch_chunks = chunks[i : i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total_chunks + batch_size - 1) // batch_size

            if progress_callback:
                progress = (i + len(batch_chunks)) / total_chunks
                progress_callback(
                    f"Sending batch {batch_num}/{total_batches} ({len(batch_chunks)} chunks)...",
                    progress,
                )

            episodes = [
                RawEpisode(
                    name=f"chunk_{i + j}",
                    content=chunk,
                    source=EpisodeType.text,
                    source_description="MiroFish document chunk",
                    reference_time=datetime.now(),
                    group_id=graph_id,
                )
                for j, chunk in enumerate(batch_chunks)
            ]

            try:
                _run_async(self._add_episode_bulk(episodes, graph_id))
            except Exception as e:
                if progress_callback:
                    progress_callback(f"Batch {batch_num} failed: {str(e)}", 0)
                raise

        return []  # Graphiti processes synchronously, no episode UUIDs to track

    async def _add_episode_bulk(self, episodes, group_id: str):
        """Async helper to call graphiti.add_episode_bulk"""
        graphiti = await get_graphiti()
        await graphiti.add_episode_bulk(episodes)

    def _get_graph_info(self, graph_id: str) -> GraphInfo:
        """Get graph information via Cypher"""
        return _run_async(self._get_graph_info_async(graph_id))

    async def _get_graph_info_async(self, graph_id: str) -> GraphInfo:
        graphiti = await get_graphiti()
        driver = graphiti.driver

        # Count nodes
        node_records, _, _ = await driver.execute_query(
            "MATCH (n:Entity) WHERE n.group_id = $gid RETURN count(n) AS cnt",
            gid=graph_id,
        )
        node_count = node_records[0]["cnt"] if node_records else 0

        # Count edges
        edge_records, _, _ = await driver.execute_query(
            "MATCH ()-[r:RELATES_TO]->() WHERE r.group_id = $gid RETURN count(r) AS cnt",
            gid=graph_id,
        )
        edge_count = edge_records[0]["cnt"] if edge_records else 0

        # Entity types (labels beyond Entity)
        label_records, _, _ = await driver.execute_query(
            "MATCH (n:Entity) WHERE n.group_id = $gid RETURN labels(n) AS lbls",
            gid=graph_id,
        )
        entity_types = set()
        for rec in label_records:
            for label in rec["lbls"]:
                if label not in ("Entity", "Node", "Episodic"):
                    entity_types.add(label)

        return GraphInfo(
            graph_id=graph_id,
            node_count=node_count,
            edge_count=edge_count,
            entity_types=list(entity_types),
        )

    def get_graph_data(self, graph_id: str) -> Dict[str, Any]:
        """
        Get complete graph data (nodes and edges with details)
        """
        return _run_async(self._get_graph_data_async(graph_id))

    async def _get_graph_data_async(self, graph_id: str) -> Dict[str, Any]:
        graphiti = await get_graphiti()
        driver = graphiti.driver

        # Fetch nodes
        node_records, _, _ = await driver.execute_query(
            "MATCH (n:Entity) WHERE n.group_id = $gid RETURN n",
            gid=graph_id,
        )

        node_map = {}
        nodes_data = []
        for rec in node_records:
            node = rec["n"]
            node_id = node.element_id
            name = node.get("name", "")
            node_map[node_id] = name

            created_at = node.get("created_at")
            nodes_data.append(
                {
                    "uuid": node_id,
                    "name": name,
                    "labels": list(node.labels),
                    "summary": node.get("summary", ""),
                    "attributes": dict(node),
                    "created_at": str(created_at) if created_at else None,
                }
            )

        # Fetch edges
        edge_records, _, _ = await driver.execute_query(
            "MATCH (s)-[r:RELATES_TO]->(t) WHERE r.group_id = $gid RETURN s, r, t",
            gid=graph_id,
        )

        edges_data = []
        for rec in edge_records:
            s_node = rec["s"]
            rel = rec["r"]
            t_node = rec["t"]

            created_at = rel.get("created_at")
            valid_at = rel.get("valid_at")
            invalid_at = rel.get("invalid_at")
            expired_at = rel.get("expired_at")

            edges_data.append(
                {
                    "uuid": rel.element_id,
                    "name": rel.get("name", ""),
                    "fact": rel.get("fact", ""),
                    "fact_type": rel.get("fact_type", rel.get("name", "")),
                    "source_node_uuid": s_node.element_id,
                    "target_node_uuid": t_node.element_id,
                    "source_node_name": s_node.get("name", ""),
                    "target_node_name": t_node.get("name", ""),
                    "attributes": dict(rel),
                    "created_at": str(created_at) if created_at else None,
                    "valid_at": str(valid_at) if valid_at else None,
                    "invalid_at": str(invalid_at) if invalid_at else None,
                    "expired_at": str(expired_at) if expired_at else None,
                    "episodes": [],
                }
            )

        return {
            "graph_id": graph_id,
            "nodes": nodes_data,
            "edges": edges_data,
            "node_count": len(nodes_data),
            "edge_count": len(edges_data),
        }

    def delete_graph(self, graph_id: str):
        """Delete graph by removing all nodes with the given group_id"""
        _run_async(self._delete_graph_async(graph_id))

    async def _delete_graph_async(self, graph_id: str):
        graphiti = await get_graphiti()
        driver = graphiti.driver
        await driver.execute_query(
            "MATCH (n) WHERE n.group_id = $gid DETACH DELETE n",
            gid=graph_id,
        )
        logger.info(f"Deleted graph data for group_id={graph_id}")

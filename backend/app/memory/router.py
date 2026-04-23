"""
MemoryRouter — picks a MemoryBackend based on env config.

Selection logic
---------------
    MEMORY_BACKEND=in_memory        # zero-dependency; tests + local-local runs
    MEMORY_BACKEND=zep_cloud        # pre-existing Zep path (default if ZEP_API_KEY set)
    MEMORY_BACKEND=neo4j_local      # self-hosted Neo4j 5.x
    MEMORY_BACKEND=neo4j_aura       # managed Neo4j AuraDB

The router constructs a *template* backend — for Zep and Neo4j, actual
instances are per-simulation because Zep graphs are keyed by `graph_id`.
Call `MemoryRouter.default().for_simulation(simulation_id, graph_id=...)`.
"""

from __future__ import annotations

import os
import threading
from typing import Optional

from ..config import Config
from .base import MemoryBackend, MemoryBackendError

_AUTO = "auto"


def _pick_kind() -> str:
    """Resolve the backend kind. `auto` picks the most capable option that
    has its prerequisites set."""
    kind = os.environ.get("MEMORY_BACKEND", _AUTO).strip().lower()
    if kind and kind != _AUTO:
        return kind
    # Auto heuristic
    if os.environ.get("NEO4J_URI"):
        if "+s://" in os.environ["NEO4J_URI"]:
            return "neo4j_aura"
        return "neo4j_local"
    if os.environ.get("ZEP_API_KEY") or Config.ZEP_API_KEY:
        return "zep_cloud"
    return "in_memory"


class MemoryRouter:
    """Process-wide singleton. Use `default()`; tests construct directly."""

    _default_lock = threading.Lock()
    _default_instance: Optional["MemoryRouter"] = None

    def __init__(self, kind: Optional[str] = None):
        self.kind = (kind or _pick_kind()).lower()

    # ------------------------------------------------------------- factory
    @classmethod
    def default(cls) -> "MemoryRouter":
        if cls._default_instance is not None:
            return cls._default_instance
        with cls._default_lock:
            if cls._default_instance is None:
                cls._default_instance = cls()
        return cls._default_instance

    @classmethod
    def reset_default(cls) -> None:
        with cls._default_lock:
            cls._default_instance = None

    # --------------------------------------------------------- instance API
    def for_simulation(
        self,
        simulation_id: str,
        *,
        graph_id: Optional[str] = None,
    ) -> MemoryBackend:
        """Return a backend bound to a specific simulation.

        `graph_id` is only consulted by the Zep backend (simulation_id is used
        as the Zep graph_id fallback if not provided).
        """
        if self.kind == "in_memory":
            from .in_memory import InMemoryBackend
            return InMemoryBackend()

        if self.kind == "zep_cloud":
            from .zep_cloud import ZepCloudBackend
            return ZepCloudBackend(graph_id=graph_id or simulation_id)

        if self.kind == "neo4j_local":
            from .neo4j_local import Neo4jLocalBackend
            return Neo4jLocalBackend(
                uri=os.environ["NEO4J_URI"],
                user=os.environ.get("NEO4J_USER", "neo4j"),
                password=os.environ["NEO4J_PASSWORD"],
                database=os.environ.get("NEO4J_DATABASE", "neo4j"),
            )

        if self.kind == "neo4j_aura":
            from .neo4j_aura import Neo4jAuraBackend
            return Neo4jAuraBackend(
                uri=os.environ["NEO4J_URI"],
                user=os.environ.get("NEO4J_USER", "neo4j"),
                password=os.environ["NEO4J_PASSWORD"],
                database=os.environ.get("NEO4J_DATABASE", "neo4j"),
            )

        raise MemoryBackendError(
            "unknown_backend_kind",
            f"unsupported MEMORY_BACKEND={self.kind!r}",
        )

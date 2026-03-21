"""
Local Zep-compatible shim backed by Neo4j + Graphiti-friendly ingestion.

This package keeps the existing import surface used by the project:
`from zep_cloud.client import Zep` and
`from zep_cloud import EpisodeData, EntityEdgeSourceTarget, InternalServerError`.
"""

from dataclasses import dataclass


class InternalServerError(Exception):
    """Compatibility exception used by retry logic."""


@dataclass
class EpisodeData:
    """Compatibility payload for batch episode ingestion."""

    data: str
    type: str = "text"


@dataclass
class EntityEdgeSourceTarget:
    """Compatibility type used by ontology mapping."""

    source: str
    target: str


from .client import Zep  # noqa: E402,F401


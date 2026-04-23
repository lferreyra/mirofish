"""
Neo4j AuraDB backend. Identical to `Neo4jLocalBackend` except for the
authentication and connection-string defaults.

AuraDB always uses the `neo4j+s://` scheme (TLS, bolt routing) and a
randomly generated password paired with the username `neo4j`. The `database`
is `neo4j` on Aura Free / Professional and user-configurable on Enterprise.
"""

from __future__ import annotations

from .neo4j_local import Neo4jLocalBackend


class Neo4jAuraBackend(Neo4jLocalBackend):
    """Managed Neo4j AuraDB."""

    name = "neo4j_aura"

    def __init__(
        self,
        *,
        uri: str,
        user: str = "neo4j",
        password: str,
        database: str = "neo4j",
    ):
        if not uri.startswith(("neo4j+s://", "neo4j+ssc://", "bolt+s://", "bolt+ssc://")):
            # Not strictly fatal — Aura routing supports these prefixes, but a
            # user who supplied a plain neo4j:// almost certainly meant to use
            # the local backend. Flag the ambiguity early.
            import logging
            logging.getLogger("mirofish.memory.neo4j").warning(
                "Neo4jAuraBackend got non-TLS uri %r — "
                "most managed deployments require neo4j+s://", uri,
            )
        super().__init__(uri=uri, user=user, password=password, database=database)

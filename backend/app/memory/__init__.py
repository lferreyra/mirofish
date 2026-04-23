"""
Agent memory — hierarchical observations + reflections with pluggable storage.

Public surface:
    from app.memory import MemoryRouter, Observation, Reflection, Namespace
    memory = MemoryRouter.default().for_simulation("sim-123")
    obs = memory.record_observation(agent_id=7, content="saw post X", round_num=3)

Phase 2 introduces:
  * base.py          - abstract MemoryBackend + records
  * in_memory.py     - reference backend for tests / local runs
  * zep_cloud.py     - adapter around the pre-existing Zep path
  * neo4j_local.py   - self-hosted Neo4j 5.x via bolt://
  * neo4j_aura.py    - managed Neo4j AuraDB (subclass)
  * hierarchical.py  - importance scoring, reflection, contradiction (backend-agnostic)
  * router.py        - env-driven backend selection + fallback
  * manager.py       - high-level `MemoryManager` used by simulation services
"""

from .base import (
    ConflictEdge,
    MemoryBackend,
    MemoryBackendError,
    MemoryRecord,
    Namespace,
    Observation,
    Reflection,
    RetrievalResult,
)
from .router import MemoryRouter

__all__ = [
    "ConflictEdge",
    "MemoryBackend",
    "MemoryBackendError",
    "MemoryRecord",
    "MemoryRouter",
    "Namespace",
    "Observation",
    "Reflection",
    "RetrievalResult",
]

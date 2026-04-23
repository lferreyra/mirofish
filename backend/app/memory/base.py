"""
Abstract MemoryBackend — what every concrete backend must implement.

Design notes
------------
* **Records** are typed dataclasses (Observation, Reflection). Free-text writes
  are out; we want enough structure to reason about importance, source links,
  and conflicts.
* **Namespaces** are first-class. Every write lands in a specific partition:
  per-agent ("agent:<sim>:<id>") or public ("public:<sim>:timeline"). Cross-agent
  reads must explicitly pass through the public namespace — backends MUST
  refuse to join a peer agent's private partition.
* **Embeddings** are optional on write. Backends that can embed server-side
  (Zep) ignore the embedding argument; backends that rely on client-side sim
  (Neo4j, in_memory) compute on the fly via the LLM router's embed role.
* **Retrieval scoring** is `alpha*recency + beta*importance + gamma*relevance`.
  Backends normalize each component into [0, 1] and then weight; the caller
  passes absolute weights (not pre-normalized) so the router can sum and rescale.
"""

from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List, Optional


class RecordKind(str, Enum):
    OBSERVATION = "observation"
    REFLECTION = "reflection"


@dataclass(frozen=True)
class Namespace:
    """Memory partition identifier. Use the factory methods — they enforce the
    documented prefix so backends can validate on write."""
    key: str

    @classmethod
    def for_agent(cls, simulation_id: str, agent_id: int) -> "Namespace":
        return cls(f"agent:{simulation_id}:{agent_id}")

    @classmethod
    def public_timeline(cls, simulation_id: str) -> "Namespace":
        return cls(f"public:{simulation_id}:timeline")

    @property
    def is_public(self) -> bool:
        return self.key.startswith("public:")

    @property
    def simulation_id(self) -> str:
        parts = self.key.split(":", 2)
        if len(parts) < 2:
            raise ValueError(f"malformed namespace key: {self.key!r}")
        return parts[1]

    @property
    def agent_id(self) -> Optional[int]:
        parts = self.key.split(":", 2)
        if parts[0] != "agent":
            return None
        try:
            return int(parts[2])
        except (IndexError, ValueError):
            return None


@dataclass
class MemoryRecord:
    """Base record type. Subclasses carry kind-specific extras."""
    id: str
    namespace: str
    content: str
    round_num: int
    ts: float
    importance: float = 5.0           # 1-10; default mid-scale
    kind: RecordKind = RecordKind.OBSERVATION
    embedding: Optional[List[float]] = None
    metadata: dict = field(default_factory=dict)
    # Populated by retrieve() so callers can inspect scoring
    relevance_score: Optional[float] = None
    recency_score: Optional[float] = None
    combined_score: Optional[float] = None

    @staticmethod
    def new_id() -> str:
        return uuid.uuid4().hex


@dataclass
class Observation(MemoryRecord):
    """A single logged agent action / perception."""
    action_type: Optional[str] = None   # CREATE_POST / LIKE_POST / ...
    author_id: Optional[int] = None     # for public timeline posts

    def __post_init__(self) -> None:
        self.kind = RecordKind.OBSERVATION


@dataclass
class Reflection(MemoryRecord):
    """A higher-level belief synthesized from a set of observations."""
    source_ids: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.kind = RecordKind.REFLECTION


@dataclass
class ConflictEdge:
    """A directed 'contradicts' link between two observations."""
    id: str
    from_id: str
    to_id: str
    ts: float
    reason: Optional[str] = None    # short human-readable explanation

    @staticmethod
    def new_id() -> str:
        return uuid.uuid4().hex


@dataclass
class RetrievalResult:
    """Scored memory records returned from `retrieve()`."""
    records: List[MemoryRecord]
    namespace: str
    query: str


class MemoryBackendError(Exception):
    """Uniform error type raised by concrete backends."""

    def __init__(self, code: str, message: str, *, backend: Optional[str] = None):
        super().__init__(f"[{backend or '?'}:{code}] {message}")
        self.code = code
        self.message = message
        self.backend = backend


class MemoryBackend(ABC):
    """Abstract base. Subclasses implement storage + retrieval; the hierarchical
    layer (importance / reflection / contradiction) sits *above* the backend so
    every backend benefits equally."""

    name: str = "abstract"

    # --- writes ------------------------------------------------------------
    @abstractmethod
    def write_observation(self, observation: Observation) -> Observation:
        """Persist an observation. Backend may compute/override `embedding` if
        the implementation supports server-side embeddings."""
        ...

    @abstractmethod
    def write_reflection(self, reflection: Reflection) -> Reflection:
        """Persist a reflection. `source_ids` must reference observations in
        the same namespace."""
        ...

    @abstractmethod
    def write_conflict_edge(self, edge: ConflictEdge) -> ConflictEdge:
        ...

    # --- reads -------------------------------------------------------------
    @abstractmethod
    def retrieve(
        self,
        *,
        namespace: Namespace,
        query: str,
        query_embedding: Optional[List[float]] = None,
        top_k: int = 10,
        alpha: float = 1.0,   # recency weight
        beta: float = 1.0,    # importance weight
        gamma: float = 1.0,   # relevance weight
        now_ts: Optional[float] = None,
    ) -> RetrievalResult:
        """Return the top-K records in `namespace`, scored by
        α·recency + β·importance + γ·relevance. The caller supplies absolute
        weights; the backend normalizes inside [0,1] before combining."""
        ...

    @abstractmethod
    def nearest(
        self,
        *,
        namespace: Namespace,
        query_embedding: List[float],
        top_k: int = 3,
        kind: Optional[RecordKind] = None,
    ) -> List[MemoryRecord]:
        """Pure vector-KNN retrieval used by the contradiction detector (no
        recency / importance weighting)."""
        ...

    @abstractmethod
    def list_reflections(
        self,
        *,
        namespace: Namespace,
        limit: int = 50,
    ) -> List[Reflection]:
        ...

    @abstractmethod
    def list_conflicts(
        self,
        *,
        namespace: Namespace,
        limit: int = 50,
    ) -> List[ConflictEdge]:
        ...

    @abstractmethod
    def summarize_window(
        self,
        *,
        namespace: Namespace,
        since_round: Optional[int] = None,
        until_round: Optional[int] = None,
        top_k: int = 50,
    ) -> List[MemoryRecord]:
        """Return observations+reflections in a round range, ordered by
        (round_num, ts). Used by the reflection scheduler to pick sources."""
        ...

    # --- lifecycle ---------------------------------------------------------
    def close(self) -> None:  # optional override
        """Release any resources (connection pools, threads). No-op by default."""
        return None

    # --- helpers -----------------------------------------------------------
    @staticmethod
    def _now_ts() -> float:
        return time.time()

    @staticmethod
    def _recency_score(ts: float, now_ts: float, half_life_s: float = 3600.0) -> float:
        """Exponential decay: ~1.0 for fresh, -> 0 for old. half_life_s is the
        point at which score == 0.5."""
        if now_ts <= ts:
            return 1.0
        age = now_ts - ts
        # 0.5 ** (age/half_life) — maps age -> (0, 1]
        return 0.5 ** (age / half_life_s)

    @staticmethod
    def _importance_score(importance: float) -> float:
        """Map importance (1-10) -> [0, 1]."""
        return max(0.0, min(1.0, (importance - 1.0) / 9.0))

    @staticmethod
    def _cosine(a: List[float], b: List[float]) -> float:
        """Client-side cosine similarity. Returns 0 if either vector is zero."""
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        na = sum(x * x for x in a) ** 0.5
        nb = sum(y * y for y in b) ** 0.5
        if na == 0.0 or nb == 0.0:
            return 0.0
        return dot / (na * nb)

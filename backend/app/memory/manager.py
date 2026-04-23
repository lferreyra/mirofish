"""
High-level MemoryManager — the object simulation code actually holds onto.

Wraps a `MemoryBackend` with the hierarchical-memory services (importance
scoring, reflection scheduling, contradiction detection) so callers don't
have to wire them up individually.

Typical usage from `simulation_runner.py` or the IPC server:

    manager = MemoryManager.create_for_simulation("sim-42", graph_id="sim-42")
    manager.record_agent_action(agent_id=7, round_num=3, action_type="CREATE_POST",
                                content="Biden announces...", public=True)
    # ... end of round ...
    manager.on_round_complete(round_num=3)
    # In a later round, the agent can retrieve:
    context = manager.retrieve_for_agent(agent_id=7, query="public opinion",
                                         include_public=True, top_k=10)

Design rules:
  * Embeddings are produced via the LLM router's `embed` role. If that role
    isn't configured, we skip embedding — retrieval falls back to token
    overlap. This keeps the backend operational without a live embed model.
  * Per-agent namespaces are enforced here; the backend treats them as opaque
    strings.
  * Public posts are duplicated into the shared `public:<sim>:timeline`
    namespace so other agents can discover them without touching private
    partitions.
"""

from __future__ import annotations

import logging
import threading
from typing import Dict, List, Optional

from ..llm import ModelRouter, Role
from ..llm.base import BackendError
from .base import (
    MemoryBackend,
    Namespace,
    Observation,
    Reflection,
    RetrievalResult,
)
from .hierarchical import ContradictionDetector, ImportanceScorer, ReflectionScheduler
from .router import MemoryRouter

logger = logging.getLogger("mirofish.memory.manager")


class MemoryManager:
    """One instance per simulation. Not thread-safe for concurrent writes to
    the same agent (ZepGraphMemoryUpdater's per-platform worker handles that)."""

    def __init__(
        self,
        *,
        simulation_id: str,
        backend: MemoryBackend,
        llm_router: Optional[ModelRouter] = None,
        every_n_rounds: int = 5,
        top_k_sources: int = 10,
        enable_importance: bool = True,
        enable_reflection: bool = True,
        enable_contradiction: bool = True,
        credibility_weighter=None,  # app.personas.CredibilityWeighter | None
    ):
        self.simulation_id = simulation_id
        self._backend = backend
        self._llm = llm_router or ModelRouter.default()
        self._public = Namespace.public_timeline(simulation_id)

        self._importance = ImportanceScorer(self._llm) if enable_importance else None
        self._reflector = (
            ReflectionScheduler(
                backend, self._llm,
                every_n_rounds=every_n_rounds,
                top_k_sources=top_k_sources,
            )
            if enable_reflection else None
        )
        self._contradiction = (
            ContradictionDetector(backend, self._llm) if enable_contradiction else None
        )
        # Phase-4: optional author-credibility reweighter applied after combined
        # retrieval. When unset, retrieve_for_agent behaves exactly as Phase 2.
        self._credibility = credibility_weighter

        self._agents_seen: Dict[int, bool] = {}
        self._agents_lock = threading.Lock()

    def set_credibility_weighter(self, weighter) -> None:
        """Install a CredibilityWeighter after construction — used when the
        persona store is built lazily during simulation prep."""
        self._credibility = weighter

    # ------------------------------------------------------------- factory
    @classmethod
    def create_for_simulation(
        cls,
        simulation_id: str,
        *,
        graph_id: Optional[str] = None,
        **kwargs,
    ) -> "MemoryManager":
        backend = MemoryRouter.default().for_simulation(simulation_id, graph_id=graph_id)
        return cls(simulation_id=simulation_id, backend=backend, **kwargs)

    # --------------------------------------------------------------- writes
    def record_agent_action(
        self,
        *,
        agent_id: int,
        round_num: int,
        content: str,
        action_type: Optional[str] = None,
        author_id: Optional[int] = None,
        public: bool = False,
        run_id: Optional[str] = None,
    ) -> Observation:
        """Write an observation into the agent's namespace; also mirror to the
        public timeline if `public=True` (posts, comments, reposts)."""
        embedding = self._maybe_embed(content)
        importance = self._score_importance(content, run_id=run_id)

        private = self._build_observation(
            namespace=Namespace.for_agent(self.simulation_id, agent_id).key,
            content=content,
            round_num=round_num,
            importance=importance,
            embedding=embedding,
            action_type=action_type,
            author_id=author_id or agent_id,
        )
        private = self._backend.write_observation(private)

        if self._contradiction is not None:
            try:
                self._contradiction.check(private, run_id=run_id)
            except Exception as exc:
                # Contradiction is purely enrichment — never block the write.
                logger.debug("contradiction check failed: %s", exc)

        if public:
            mirror = self._build_observation(
                namespace=self._public.key,
                content=content,
                round_num=round_num,
                importance=importance,
                embedding=embedding,
                action_type=action_type,
                author_id=author_id or agent_id,
            )
            self._backend.write_observation(mirror)

        with self._agents_lock:
            self._agents_seen[agent_id] = True
        return private

    def on_round_complete(self, round_num: int, *, run_id: Optional[str] = None) -> None:
        """Call once per round. Triggers per-agent reflection if cadence hits."""
        if self._reflector is None:
            return
        with self._agents_lock:
            agents = list(self._agents_seen.keys())
        for agent_id in agents:
            try:
                self._reflector.maybe_reflect(
                    simulation_id=self.simulation_id,
                    agent_id=agent_id,
                    round_num=round_num,
                    run_id=run_id,
                )
            except Exception as exc:
                logger.warning("reflection for agent %s failed: %s", agent_id, exc)

    # ---------------------------------------------------------------- reads
    def retrieve_for_agent(
        self,
        *,
        agent_id: int,
        query: str,
        include_public: bool = True,
        top_k: int = 10,
        alpha: float = 1.0,
        beta: float = 1.0,
        gamma: float = 1.0,
    ) -> List[Observation | Reflection]:
        """Return records scored α·recency + β·importance + γ·relevance,
        pulling from the agent's private partition and optionally from the
        public timeline. Cross-agent reads never go through another agent's
        private namespace — that is by design."""
        query_embedding = self._maybe_embed(query)
        private_ns = Namespace.for_agent(self.simulation_id, agent_id)

        private_result = self._backend.retrieve(
            namespace=private_ns, query=query, query_embedding=query_embedding,
            top_k=top_k, alpha=alpha, beta=beta, gamma=gamma,
        )
        combined = list(private_result.records)
        if include_public:
            public_result = self._backend.retrieve(
                namespace=self._public, query=query, query_embedding=query_embedding,
                top_k=top_k, alpha=alpha, beta=beta, gamma=gamma,
            )
            combined.extend(public_result.records)

        # Phase-4: apply credibility weighting if configured. Done BEFORE the
        # final sort so boosts are reflected in ordering.
        if self._credibility is not None:
            combined = self._credibility.reweight(combined)
        else:
            # Re-sort the merged list by combined_score; tie-break by ts desc.
            combined.sort(
                key=lambda r: (r.combined_score or 0.0, r.ts),
                reverse=True,
            )
        return combined[:top_k]

    def list_reflections(self, agent_id: int, limit: int = 50) -> List[Reflection]:
        ns = Namespace.for_agent(self.simulation_id, agent_id)
        return self._backend.list_reflections(namespace=ns, limit=limit)

    def list_conflicts(self, agent_id: int, limit: int = 50):
        ns = Namespace.for_agent(self.simulation_id, agent_id)
        return self._backend.list_conflicts(namespace=ns, limit=limit)

    # ------------------------------------------------------------- teardown
    def close(self) -> None:
        self._backend.close()

    # ------------------------------------------------------------- internals
    def _maybe_embed(self, text: str) -> Optional[List[float]]:
        """Embed via the LLM router if the embed role is configured. If not,
        retrieval gracefully degrades to token overlap — better than erroring."""
        if not text:
            return None
        try:
            response = self._llm.embed([text])
        except BackendError as exc:
            if exc.code in ("no_backend_for_role", "embed_model_missing"):
                return None
            logger.debug("embedding failed (%s); retrieval will use token overlap", exc.code)
            return None
        except Exception as exc:
            logger.debug("embedding raised unexpectedly: %s", exc)
            return None
        return response.vectors[0] if response.vectors else None

    def _score_importance(self, content: str, *, run_id: Optional[str]) -> float:
        if self._importance is None:
            return 5.0
        return float(self._importance.score(content, run_id=run_id))

    def _build_observation(
        self,
        *,
        namespace: str,
        content: str,
        round_num: int,
        importance: float,
        embedding: Optional[List[float]],
        action_type: Optional[str],
        author_id: Optional[int],
    ) -> Observation:
        return Observation(
            id=Observation.new_id(),
            namespace=namespace,
            content=content,
            round_num=round_num,
            ts=self._backend._now_ts(),
            importance=importance,
            embedding=embedding,
            action_type=action_type,
            author_id=author_id,
            metadata={"simulation_id": self.simulation_id},
        )

"""
Hierarchical memory — backend-agnostic services that sit *above* MemoryBackend.

Implements the Stanford Generative Agents pattern:
  * `ImportanceScorer`    - LLM (fast role) scores each observation 1-10 at write time.
  * `ReflectionScheduler` - every N rounds, retrieves top-K observations by importance
                             and asks the LLM (balanced role) for 3-5 higher-level beliefs.
  * `ContradictionDetector` - before writing an observation, finds top-3 nearest neighbors
                             and asks the LLM (fast role, binary) whether the new observation
                             contradicts any. Flags land in a `conflict_edge`.

These three are pure services — no storage coupling. Any MemoryBackend plugs in.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from ..llm import ModelRouter, Role
from .base import (
    ConflictEdge,
    MemoryBackend,
    Namespace,
    Observation,
    RecordKind,
    Reflection,
)

logger = logging.getLogger("mirofish.memory.hierarchical")


# --------------------------------------------------------------------------
# Importance scoring
# --------------------------------------------------------------------------

_IMPORTANCE_SYSTEM = """You rate how important a single observation is for an
agent's future decision-making, on a scale of 1 (trivial) to 10 (life-changing).
Only output a single integer between 1 and 10. Nothing else."""

_IMPORTANCE_USER_TEMPLATE = """Observation: {content}

Rate importance (1-10):"""

_IMPORTANCE_INT_RE = re.compile(r"\b([1-9]|10)\b")


class ImportanceScorer:
    """Assigns a 1-10 importance value to each observation using the `fast` LLM.

    If the LLM call fails, falls back to a neutral 5 rather than blocking the
    write path. Cache hit rate matters here because the same action types
    (CREATE_POST / LIKE_POST) produce very similar prompts — the system prompt
    goes first so prefix caching catches it.
    """

    def __init__(self, router: Optional[ModelRouter] = None, default: int = 5):
        self._router = router or ModelRouter.default()
        self._default = default

    def score(self, content: str, *, run_id: Optional[str] = None) -> int:
        messages = [
            {"role": "system", "content": _IMPORTANCE_SYSTEM},
            {"role": "user", "content": _IMPORTANCE_USER_TEMPLATE.format(content=content[:1000])},
        ]
        try:
            response = self._router.chat(
                Role.FAST,
                messages,
                temperature=0.0,
                max_tokens=8,
                cache_key="memory.importance",
                run_id=run_id,
            )
        except Exception as exc:
            logger.warning("ImportanceScorer LLM call failed, using default %d: %s",
                           self._default, exc)
            return self._default

        match = _IMPORTANCE_INT_RE.search(response.text)
        if not match:
            logger.debug("ImportanceScorer got unparseable reply %r; using default", response.text)
            return self._default
        return int(match.group(1))


# --------------------------------------------------------------------------
# Reflection
# --------------------------------------------------------------------------

_REFLECTION_SYSTEM = """You are the inner voice of an agent in a social-media
simulation. Given a recent batch of the agent's observations, write 3-5 short
higher-level beliefs that summarize what the agent should now hold to be true
about the topic, people, or situation.

Output JSON only, this exact shape:
{"beliefs": ["belief 1", "belief 2", ...]}

Each belief is a single sentence, <=30 words, written from the agent's
first-person perspective ("I believe...", "I've noticed..."). Do not repeat
observations verbatim — synthesize."""


@dataclass
class ReflectionResult:
    reflections: List[Reflection]
    source_ids: List[str]
    round_num: int


class ReflectionScheduler:
    """Runs a reflection pass per-agent every `every_n_rounds` rounds.

    Call `maybe_reflect(agent_id, round_num, simulation_id)` after each round.
    The scheduler tracks when each agent last reflected and no-ops until the
    cadence is hit.
    """

    def __init__(
        self,
        backend: MemoryBackend,
        router: Optional[ModelRouter] = None,
        *,
        every_n_rounds: int = 5,
        top_k_sources: int = 10,
        min_new_observations: int = 3,
    ):
        self._backend = backend
        self._router = router or ModelRouter.default()
        self._every_n = every_n_rounds
        self._top_k = top_k_sources
        self._min_new = min_new_observations
        # Per-agent "last round we reflected on" so the cadence is stable across
        # out-of-order calls.
        self._last_reflected_round: Dict[Tuple[str, int], int] = {}

    def maybe_reflect(
        self,
        *,
        simulation_id: str,
        agent_id: int,
        round_num: int,
        run_id: Optional[str] = None,
    ) -> Optional[ReflectionResult]:
        key = (simulation_id, agent_id)
        last = self._last_reflected_round.get(key, -1)
        if round_num - last < self._every_n:
            return None

        ns = Namespace.for_agent(simulation_id, agent_id)
        sources = self._backend.summarize_window(
            namespace=ns,
            since_round=last + 1,
            until_round=round_num,
            top_k=self._top_k,
        )
        # Only reflect on OBSERVATIONS; pulling previous reflections in would
        # make the agent endlessly talk about its own beliefs.
        sources = [r for r in sources if r.kind == RecordKind.OBSERVATION]
        if len(sources) < self._min_new:
            return None

        beliefs = self._generate_beliefs(sources, run_id=run_id)
        if not beliefs:
            return None

        # Persist each belief as a reflection pointing at all source ids.
        reflections: List[Reflection] = []
        source_ids = [r.id for r in sources]
        for belief in beliefs:
            reflection = Reflection(
                id=Reflection.new_id(),
                namespace=ns.key,
                content=belief,
                round_num=round_num,
                ts=self._backend._now_ts(),
                importance=7.0,   # reflections skew higher than observations by construction
                source_ids=list(source_ids),
                metadata={"kind": "reflection", "simulation_id": simulation_id},
            )
            reflections.append(self._backend.write_reflection(reflection))

        self._last_reflected_round[key] = round_num
        return ReflectionResult(reflections=reflections, source_ids=source_ids, round_num=round_num)

    def _generate_beliefs(
        self,
        sources,
        *,
        run_id: Optional[str],
    ) -> List[str]:
        import json
        numbered = "\n".join(f"- (importance={r.importance:.0f}) {r.content}" for r in sources)
        messages = [
            {"role": "system", "content": _REFLECTION_SYSTEM},
            {"role": "user", "content": f"Recent observations:\n{numbered}"},
        ]
        try:
            response = self._router.chat(
                Role.BALANCED,
                messages,
                temperature=0.0,
                max_tokens=512,
                response_format={"type": "json_object"},
                cache_key="memory.reflection",
                run_id=run_id,
            )
        except Exception as exc:
            logger.warning("ReflectionScheduler LLM call failed: %s", exc)
            return []

        raw = response.text.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"\s*```$", "", raw)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("ReflectionScheduler got non-JSON reply: %r", raw[:200])
            return []

        beliefs = data.get("beliefs") or []
        # Defensive: clip anything wild.
        return [b.strip() for b in beliefs if isinstance(b, str) and b.strip()][:5]


# --------------------------------------------------------------------------
# Contradiction detection
# --------------------------------------------------------------------------

_CONTRADICTION_SYSTEM = """You decide whether two short statements carry
OPPOSITE sentiment or factual claims about the same topic. This is not
"related" or "different" — this is specifically "directly contradictory".

Output JSON only: {"contradicts": true|false, "reason": "short phrase"}"""


class ContradictionDetector:
    """Binary classifier using the `fast` LLM role. For each incoming
    observation, pulls top-3 nearest neighbors in the agent's namespace and
    asks "does this contradict that". A yes writes a `conflict_edge` so the
    agent's next retrieval will surface the conflict.
    """

    def __init__(
        self,
        backend: MemoryBackend,
        router: Optional[ModelRouter] = None,
        *,
        neighbors_to_check: int = 3,
    ):
        self._backend = backend
        self._router = router or ModelRouter.default()
        self._neighbors = neighbors_to_check

    def check(
        self,
        observation: Observation,
        *,
        run_id: Optional[str] = None,
    ) -> List[ConflictEdge]:
        if not observation.embedding:
            # No vector -> we have no credible way to find semantic neighbors.
            # Skipping rather than blocking the write is the right call here.
            return []

        namespace = Namespace(observation.namespace)
        candidates = self._backend.nearest(
            namespace=namespace,
            query_embedding=observation.embedding,
            top_k=self._neighbors,
            kind=RecordKind.OBSERVATION,
        )
        edges: List[ConflictEdge] = []
        for cand in candidates:
            if cand.id == observation.id:
                continue
            if self._contradicts(observation.content, cand.content, run_id=run_id):
                edge = ConflictEdge(
                    id=ConflictEdge.new_id(),
                    from_id=observation.id,
                    to_id=cand.id,
                    ts=self._backend._now_ts(),
                    reason="sentiment_flip",  # best-effort; LLM reason is logged
                )
                edges.append(self._backend.write_conflict_edge(edge))
        return edges

    def _contradicts(self, a: str, b: str, *, run_id: Optional[str]) -> bool:
        import json
        messages = [
            {"role": "system", "content": _CONTRADICTION_SYSTEM},
            {"role": "user", "content": f"A: {a[:500]}\nB: {b[:500]}"},
        ]
        try:
            response = self._router.chat(
                Role.FAST,
                messages,
                temperature=0.0,
                max_tokens=64,
                response_format={"type": "json_object"},
                cache_key="memory.contradiction",
                run_id=run_id,
            )
        except Exception as exc:
            logger.debug("ContradictionDetector LLM call failed: %s", exc)
            return False

        raw = response.text.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"\s*```$", "", raw)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return False
        return bool(data.get("contradicts"))

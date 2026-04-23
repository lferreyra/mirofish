"""
Opinion inertia — tracks how many opposing posts each agent has seen, so a
high-conviction agent doesn't flip on a single convincing post.

This counter lives in memory only (not persisted to the MemoryBackend) —
it's a runtime dynamics parameter, not a recallable belief. Checkpoints
snapshot it via `snapshot()` / `restore()` so resumed runs preserve the
accumulated evidence.

Usage (inside MemoryManager.record_agent_action or similar):

    inertia.observe_post(
        observer_agent_id=7,
        persona=persona_of_agent_7,
        post_valence=+0.6,
    )
    if inertia.should_allow_flip(agent_id=7, persona=persona_of_agent_7):
        # agent has seen enough opposing evidence to justify shifting stance
        ...
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Dict

from .schema import StructuredPersona


@dataclass
class _Counter:
    opposing: int = 0
    supporting: int = 0

    def as_dict(self) -> Dict[str, int]:
        return {"opposing": self.opposing, "supporting": self.supporting}


class StanceInertia:
    """Per-agent counter of posts that oppose / support their current stance.

    Thread-safe. Accumulates across rounds until `reset_agent` is called
    (typically after a successful stance flip).
    """

    # How strong a post's valence must be to "count" as opposing/supporting.
    # Weaker signals are ignored — saves the counter from being tickled by
    # every neutral restatement of the topic.
    VALENCE_THRESHOLD = 0.2

    def __init__(self) -> None:
        self._counts: Dict[int, _Counter] = {}
        self._lock = threading.Lock()

    # ---- writes ---------------------------------------------------------
    def observe_post(
        self,
        *,
        observer_agent_id: int,
        persona: StructuredPersona,
        post_valence: float,
    ) -> None:
        """Record that `observer_agent_id` has seen a post with `post_valence`.

        Only posts above the valence threshold tick the counter; neutral
        posts don't count toward either side.
        """
        if abs(post_valence) < self.VALENCE_THRESHOLD:
            return
        with self._lock:
            counter = self._counts.setdefault(observer_agent_id, _Counter())
            if persona.stance_is_opposed_by(post_valence):
                counter.opposing += 1
            elif persona.initial_stance.valence * post_valence > 0.0:
                counter.supporting += 1

    def reset_agent(self, agent_id: int) -> None:
        """Clear the counters — call after the agent actually flips stance."""
        with self._lock:
            self._counts.pop(agent_id, None)

    # ---- reads ----------------------------------------------------------
    def opposing_count(self, agent_id: int) -> int:
        with self._lock:
            c = self._counts.get(agent_id)
            return c.opposing if c else 0

    def supporting_count(self, agent_id: int) -> int:
        with self._lock:
            c = self._counts.get(agent_id)
            return c.supporting if c else 0

    def should_allow_flip(self, *, agent_id: int, persona: StructuredPersona) -> bool:
        """True when this agent has seen enough opposing evidence to justify
        a stance change. Uses the schema rule: need >=ceil(10*conviction)
        opposing posts."""
        needed = persona.opposing_posts_needed()
        return self.opposing_count(agent_id) >= needed

    # ---- serialization (for checkpoints) --------------------------------
    def snapshot(self) -> Dict[str, Dict[str, int]]:
        """Return a JSON-safe dict. Keys are stringified agent IDs."""
        with self._lock:
            return {
                str(aid): counter.as_dict()
                for aid, counter in self._counts.items()
            }

    def restore(self, data: Dict[str, Dict[str, int]]) -> None:
        """Load from a snapshot dict. Clobbers any existing counters."""
        with self._lock:
            self._counts.clear()
            for aid_str, raw in data.items():
                try:
                    self._counts[int(aid_str)] = _Counter(
                        opposing=int(raw.get("opposing", 0)),
                        supporting=int(raw.get("supporting", 0)),
                    )
                except (TypeError, ValueError):
                    continue

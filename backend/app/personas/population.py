"""
Population-level mixer: given N agents and archetype percentages, return an
assignment of `agent_id -> Archetype`.

This module does NOT call the LLM. It's purely mechanical — given knobs, it
decides which agents are normal vs bots vs trolls. The caller then feeds
normal/media/expert agents into `PersonaGenerator` and constructs bot/troll
personas procedurally via `StructuredPersona.default_for_archetype`.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .schema import Archetype, StanceVector, StructuredPersona


@dataclass
class PopulationAssignment:
    """Result of `build_population`. One entry per agent."""
    assignments: Dict[int, Archetype]
    bot_count: int = 0
    troll_count: int = 0
    normal_count: int = 0
    media_count: int = 0
    expert_count: int = 0

    def as_list(self) -> List[tuple[int, Archetype]]:
        return sorted(self.assignments.items())


def build_population(
    *,
    agent_ids: List[int],
    bot_pct: float = 0.0,
    troll_pct: float = 0.0,
    media_pct: float = 0.0,
    expert_pct: float = 0.0,
    rng: Optional[random.Random] = None,
) -> PopulationAssignment:
    """Return an assignment of archetypes over `agent_ids`.

    Percentages are in [0, 100]. The sum of bot+troll+media+expert must be
    <= 100; the remainder is assigned NORMAL. Assignment is randomized so
    that the same seed produces the same mix — use `rng=random.Random(seed)`
    for determinism.

    Phase-4 default: bot_pct=0, troll_pct=0. Those are *experimental knobs*;
    enabling them changes simulation outcomes per the spec.
    """
    rng = rng or random.Random()
    total_pct = bot_pct + troll_pct + media_pct + expert_pct
    if total_pct > 100.0 + 1e-6:
        raise ValueError(
            f"archetype percentages exceed 100: bot={bot_pct} troll={troll_pct} "
            f"media={media_pct} expert={expert_pct}"
        )
    if bot_pct < 0 or troll_pct < 0 or media_pct < 0 or expert_pct < 0:
        raise ValueError("archetype percentages must be non-negative")

    n = len(agent_ids)
    # Integer rounding — floor each bucket, then hand remaining slots to
    # NORMAL so we never over-allocate.
    bot_n = int(math.floor(n * bot_pct / 100.0))
    troll_n = int(math.floor(n * troll_pct / 100.0))
    media_n = int(math.floor(n * media_pct / 100.0))
    expert_n = int(math.floor(n * expert_pct / 100.0))
    normal_n = n - (bot_n + troll_n + media_n + expert_n)

    roles: List[Archetype] = (
        [Archetype.BOT] * bot_n
        + [Archetype.TROLL] * troll_n
        + [Archetype.MEDIA] * media_n
        + [Archetype.EXPERT] * expert_n
        + [Archetype.NORMAL] * normal_n
    )
    # Shuffle so adversarial agents are spread across the agent_id space —
    # otherwise the lowest IDs all become bots, which skews any sort-based
    # retrieval tests.
    rng.shuffle(roles)

    assignments = {agent_ids[i]: roles[i] for i in range(n)}
    return PopulationAssignment(
        assignments=assignments,
        bot_count=bot_n,
        troll_count=troll_n,
        media_count=media_n,
        expert_count=expert_n,
        normal_count=normal_n,
    )


def build_bot_persona(
    *,
    agent_id: int,
    narrative: str,
    initial_stance: Optional[StanceVector] = None,
) -> StructuredPersona:
    """Procedural bot persona. `narrative` is the fixed text they post every turn."""
    return StructuredPersona.default_for_archetype(
        agent_id=agent_id,
        archetype=Archetype.BOT,
        background="Automated account posting a fixed narrative.",
        initial_stance=initial_stance or StanceVector(label="fixed_narrative", valence=0.0),
        extras={"narrative": narrative},
    )


def build_troll_persona(
    *,
    agent_id: int,
    tone: str = "mocking",
    initial_stance: Optional[StanceVector] = None,
) -> StructuredPersona:
    """Procedural troll persona. `tone` guides the hostility flavor in prompts."""
    return StructuredPersona.default_for_archetype(
        agent_id=agent_id,
        archetype=Archetype.TROLL,
        background=f"Hostile account that reply-bombs with a {tone} tone.",
        initial_stance=initial_stance or StanceVector(label="contrarian", valence=0.0),
        extras={"tone": tone},
    )

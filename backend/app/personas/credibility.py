"""
Credibility-weighted retrieval.

When an agent asks "what posts are relevant to me right now", we don't want
to treat a CDC tweet and a random burner account equally. The credibility
weighter looks up each public-post author's persona, reads their
`credibility` score, and boosts / dampens the post's combined retrieval
score accordingly.

Formula:
    new_score = base_score * (1 + CRED_WEIGHT * (credibility - 0.5))

With `CRED_WEIGHT=1.0` (the default):
    * credibility=1.0 -> 1.5x the base score
    * credibility=0.5 -> 1.0x (neutral, no effect)
    * credibility=0.0 -> 0.5x

Posts with no resolvable author persona (cross-simulation noise, imported
data) fall back to neutral — the weighter never drops them silently.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from ..memory.base import MemoryRecord
from .schema import StructuredPersona


class CredibilityWeighter:
    """Re-ranks a list of retrieved records by the author's credibility."""

    def __init__(
        self,
        persona_store: Dict[int, StructuredPersona],
        *,
        weight: float = 1.0,
    ):
        self._personas = persona_store
        self._weight = max(0.0, weight)

    def reweight(self, records: List[MemoryRecord]) -> List[MemoryRecord]:
        """Return a NEW list — caller's list is not mutated. Records without a
        resolvable author credibility keep their original combined_score."""
        adjusted: List[MemoryRecord] = []
        for record in records:
            author_id = self._author_of(record)
            credibility = 0.5  # neutral fallback
            if author_id is not None:
                persona = self._personas.get(author_id)
                if persona is not None:
                    credibility = persona.credibility
            multiplier = 1.0 + self._weight * (credibility - 0.5)
            base = record.combined_score if record.combined_score is not None else 0.0
            # Shallow-copy the record so the caller's originals stay untouched;
            # the record dataclasses are frozen-ish in spirit (no mutation upstream).
            new = type(record)(**record.__dict__)
            new.combined_score = base * multiplier
            adjusted.append(new)
        adjusted.sort(
            key=lambda r: (r.combined_score or 0.0, r.ts),
            reverse=True,
        )
        return adjusted

    # ----
    @staticmethod
    def _author_of(record: MemoryRecord) -> Optional[int]:
        """Pull the author_id off a record. Observations carry it natively;
        reflections don't have one (they're synthesized by the agent about
        themselves)."""
        author = getattr(record, "author_id", None)
        if author is None:
            return None
        try:
            return int(author)
        except (TypeError, ValueError):
            return None

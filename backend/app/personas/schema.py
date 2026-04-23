"""
Typed persona schema.

Every agent in a Phase-4 run carries a `StructuredPersona`. The schema is
deliberately small — just the fields that measurably change behavior — so
downstream prompts can fit it on a single system message without bloating
the prefix cache.

Serialization contract:
  * `to_dict()` / `from_dict()` roundtrip cleanly (tested in
    `test_personas_schema.py`). This is the wire format written to the OASIS
    profile's `persona` field.
  * `to_prompt_block()` produces the exact text injected into the agent's
    system prompt. Changing this function changes agent behavior — version
    bump + acceptance-check re-run required.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class Archetype(str, Enum):
    """High-level agent kind. Steers the prompt block toward default patterns
    of behavior the LLM should follow."""
    NORMAL = "normal"      # persona driven by Big Five + stance
    MEDIA = "media"        # institutional voice; higher baseline credibility
    EXPERT = "expert"      # domain authority; higher baseline credibility
    BOT = "bot"            # posts a fixed narrative repeatedly
    TROLL = "troll"        # reply-bombs with hostility


# Default credibility bands per archetype. Callers can override.
_ARCHETYPE_CREDIBILITY_DEFAULT = {
    Archetype.NORMAL: 0.4,
    Archetype.MEDIA: 0.8,
    Archetype.EXPERT: 0.85,
    Archetype.BOT: 0.15,
    Archetype.TROLL: 0.10,
}

# Conviction floor per archetype. Bots/trolls never "change their mind".
_ARCHETYPE_CONVICTION_FLOOR = {
    Archetype.NORMAL: 0.3,
    Archetype.MEDIA: 0.6,
    Archetype.EXPERT: 0.7,
    Archetype.BOT: 1.0,
    Archetype.TROLL: 1.0,
}


@dataclass
class BigFive:
    """OCEAN personality traits in [0.0, 1.0]. Neutral = 0.5."""
    openness: float = 0.5
    conscientiousness: float = 0.5
    extraversion: float = 0.5
    agreeableness: float = 0.5
    neuroticism: float = 0.5

    def clamp(self) -> "BigFive":
        return BigFive(
            openness=_clamp01(self.openness),
            conscientiousness=_clamp01(self.conscientiousness),
            extraversion=_clamp01(self.extraversion),
            agreeableness=_clamp01(self.agreeableness),
            neuroticism=_clamp01(self.neuroticism),
        )

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BigFive":
        return cls(
            openness=float(data.get("openness", 0.5)),
            conscientiousness=float(data.get("conscientiousness", 0.5)),
            extraversion=float(data.get("extraversion", 0.5)),
            agreeableness=float(data.get("agreeableness", 0.5)),
            neuroticism=float(data.get("neuroticism", 0.5)),
        )


@dataclass
class StanceVector:
    """Initial position on the seed topic.

    `label` is short, human-readable ("supports policy X"). `valence` is a
    signed scalar in [-1.0, 1.0]: -1 = strongly opposed, +1 = strongly in
    favor, 0 = neutral / undecided. `valence` is what the inertia counter
    compares against when deciding whether a new post opposes the current
    stance.
    """
    label: str = "neutral"
    valence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {"label": self.label, "valence": self.valence}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StanceVector":
        return cls(
            label=str(data.get("label", "neutral")),
            valence=_clamp(float(data.get("valence", 0.0)), -1.0, 1.0),
        )


@dataclass
class StructuredPersona:
    """What every agent carries. Compact by design.

    * `agent_id` is the OASIS user_id — the same integer the memory namespace
      and retrieval APIs use.
    * `background` is capped at 200 chars per the Phase-4 spec so the system
      prompt stays small and prefix-cacheable.
    """
    agent_id: int
    archetype: Archetype = Archetype.NORMAL
    big_five: BigFive = field(default_factory=BigFive)
    conviction: float = 0.5          # [0,1] — resistance to stance change
    credibility: float = 0.4         # [0,1] — weight others give this agent
    background: str = ""             # <= 200 chars
    initial_stance: StanceVector = field(default_factory=StanceVector)
    # Per-archetype payload. For BOT: {"narrative": "..."}; TROLL: {"tone": "..."}.
    extras: Dict[str, Any] = field(default_factory=dict)

    # ---- validation ------------------------------------------------------
    def __post_init__(self) -> None:
        # Background length is part of the contract — enforce loudly.
        if len(self.background) > 200:
            self.background = self.background[:200]
        self.conviction = _clamp01(self.conviction)
        self.credibility = _clamp01(self.credibility)
        self.big_five = self.big_five.clamp()
        # Coerce archetype strings to enum for from_dict paths
        if isinstance(self.archetype, str):
            try:
                self.archetype = Archetype(self.archetype)
            except ValueError:
                self.archetype = Archetype.NORMAL

    # ---- factories -------------------------------------------------------
    @classmethod
    def default_for_archetype(
        cls,
        *,
        agent_id: int,
        archetype: Archetype,
        background: str = "",
        initial_stance: Optional[StanceVector] = None,
        extras: Optional[Dict[str, Any]] = None,
    ) -> "StructuredPersona":
        """Build a default persona whose conviction + credibility reflect the
        archetype. Useful for bots/trolls where you don't need the LLM to
        'invent' traits — their behavior is dictated by the archetype itself.
        """
        return cls(
            agent_id=agent_id,
            archetype=archetype,
            big_five=BigFive(),
            conviction=_ARCHETYPE_CONVICTION_FLOOR[archetype],
            credibility=_ARCHETYPE_CREDIBILITY_DEFAULT[archetype],
            background=background,
            initial_stance=initial_stance or StanceVector(),
            extras=extras or {},
        )

    # ---- serialization ---------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "archetype": self.archetype.value,
            "big_five": self.big_five.to_dict(),
            "conviction": self.conviction,
            "credibility": self.credibility,
            "background": self.background,
            "initial_stance": self.initial_stance.to_dict(),
            "extras": dict(self.extras),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StructuredPersona":
        return cls(
            agent_id=int(data["agent_id"]),
            archetype=Archetype(data.get("archetype", Archetype.NORMAL.value)),
            big_five=BigFive.from_dict(data.get("big_five") or {}),
            conviction=float(data.get("conviction", 0.5)),
            credibility=float(data.get("credibility", 0.4)),
            background=str(data.get("background", ""))[:200],
            initial_stance=StanceVector.from_dict(data.get("initial_stance") or {}),
            extras=dict(data.get("extras") or {}),
        )

    @classmethod
    def from_json(cls, raw: str) -> "StructuredPersona":
        return cls.from_dict(json.loads(raw))

    # ---- prompt surface --------------------------------------------------
    def opposing_posts_needed(self) -> int:
        """How many opposing posts the agent must see before they should
        even consider shifting stance. Spec: `ceil(10 * conviction)`."""
        import math
        return max(1, math.ceil(10.0 * self.conviction))

    def stance_is_opposed_by(self, valence: float) -> bool:
        """True when an external post's valence is on the opposite sign of
        the persona's current stance. Neutral stances (valence near zero)
        are never 'opposed' — neutral agents have no stance to defend."""
        if abs(self.initial_stance.valence) < 0.15:
            return False
        return self.initial_stance.valence * valence < 0.0


# ---- helpers --------------------------------------------------------------

def _clamp(x: float, lo: float, hi: float) -> float:
    if x < lo:
        return lo
    if x > hi:
        return hi
    return x


def _clamp01(x: float) -> float:
    return _clamp(x, 0.0, 1.0)

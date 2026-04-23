"""
Structured persona schema + agent dynamics (conviction, credibility, archetypes).

Before Phase 4, personas were free-form prose — the LLM re-invented each
agent's personality every turn, which produced the herd-behavior problem the
original MiroFish paper acknowledges. This package fixes that by:

  * Pinning every agent to a typed `StructuredPersona` (Big Five + conviction
    + credibility + initial stance) that serializes as JSON and is injected
    verbatim into every prompt.
  * Tracking opposing-evidence counters per agent (`StanceInertia`) so a
    high-conviction agent doesn't flip on a single convincing post.
  * Weighting retrieval by author credibility so a CDC post punches harder
    than a rando tweet.
  * Adding bot and troll archetypes whose behavior is enforced via the
    persona instruction block rather than rewriting OASIS's action loop.
"""

from .credibility import CredibilityWeighter
from .generator import PersonaGenerator
from .inertia import StanceInertia
from .population import build_population
from .prompts import persona_system_block
from .schema import (
    Archetype,
    BigFive,
    StanceVector,
    StructuredPersona,
)

__all__ = [
    "Archetype",
    "BigFive",
    "CredibilityWeighter",
    "PersonaGenerator",
    "StanceInertia",
    "StanceVector",
    "StructuredPersona",
    "build_population",
    "persona_system_block",
]

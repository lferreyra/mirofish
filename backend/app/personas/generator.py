"""
LLM-driven StructuredPersona generator.

Replaces the free-form prose persona step. Instead of asking the model to
invent personality in prose, we hand it a strict JSON schema and ask it to
fill in Big Five + conviction + credibility + a short background + an
initial stance. That typed output is then injected verbatim via
`persona_system_block` into every agent prompt.

This generator is only responsible for NORMAL / MEDIA / EXPERT archetypes.
BOT and TROLL personas are built procedurally in `population.py` — having
the LLM 'invent' bot behavior defeats the purpose of the archetype.
"""

from __future__ import annotations

import json
import logging
import random
import re
from typing import Any, Dict, Optional

from ..llm import ModelRouter, Role
from ..llm.base import BackendError
from .schema import Archetype, BigFive, StanceVector, StructuredPersona

logger = logging.getLogger("mirofish.personas.generator")


_SYSTEM = """You generate a STRUCTURED persona for a social-media simulation
agent. Output JSON ONLY matching this schema:

{
  "big_five": {"openness":0-1, "conscientiousness":0-1, "extraversion":0-1,
               "agreeableness":0-1, "neuroticism":0-1},
  "conviction": 0-1,
  "credibility": 0-1,
  "background": "<=200 chars, third-person, factual",
  "initial_stance": {"label": "short phrase", "valence": -1..1}
}

Rules:
- All floats in [0, 1] except valence in [-1, 1].
- `credibility` reflects public trust: expert / media agents > 0.7, random
  individuals 0.2-0.5, anonymous accounts < 0.2.
- `conviction` reflects how strongly the person sticks to their views.
- `initial_stance.valence`: -1 strongly opposes the topic, +1 strongly
  supports, 0 neutral / undecided.
- `background` must be <= 200 characters. No line breaks.
- Output JSON only. No prose, no code fences."""


class PersonaGenerator:
    """One-shot persona generator. Caller supplies seed info (entity name +
    type + topic summary); generator returns a `StructuredPersona`."""

    def __init__(self, router: Optional[ModelRouter] = None, rng: Optional[random.Random] = None):
        self._router = router or ModelRouter.default()
        self._rng = rng or random.Random()

    def generate(
        self,
        *,
        agent_id: int,
        entity_name: str,
        entity_type: str,
        topic_summary: str,
        archetype: Archetype = Archetype.NORMAL,
        run_id: Optional[str] = None,
    ) -> StructuredPersona:
        """Produce a StructuredPersona. Falls back to a procedural persona
        when the LLM is unreachable or returns garbage — a persona with
        defaults is strictly better than blocking the simulation."""
        user_prompt = (
            f"Entity: {entity_name}\n"
            f"Entity type: {entity_type}\n"
            f"Archetype: {archetype.value}\n"
            f"Topic: {topic_summary[:1000]}\n\n"
            "Generate the persona JSON for this entity. Their stance on the "
            "topic should be consistent with who they are."
        )
        messages = [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": user_prompt},
        ]
        try:
            response = self._router.chat(
                Role.BALANCED,
                messages,
                temperature=0.4,
                max_tokens=512,
                response_format={"type": "json_object"},
                cache_key="personas.generate",
                run_id=run_id,
            )
            data = _parse_llm_json(response.text)
            return self._assemble(agent_id=agent_id, archetype=archetype, data=data)
        except Exception as exc:
            # Any LLM failure (transport, parse, schema) falls back to a
            # procedural persona. The simulation must not die because one
            # entity's persona couldn't be generated.
            logger.warning(
                "PersonaGenerator falling back to procedural persona for "
                "agent=%s (%s): %s", agent_id, entity_name, exc,
            )
            return self._procedural_fallback(
                agent_id=agent_id, archetype=archetype,
                entity_name=entity_name, entity_type=entity_type,
            )

    # ------------------------------------------------------------- internals
    def _assemble(
        self,
        *,
        agent_id: int,
        archetype: Archetype,
        data: Dict[str, Any],
    ) -> StructuredPersona:
        bf = BigFive.from_dict(data.get("big_five") or {})
        stance = StanceVector.from_dict(data.get("initial_stance") or {})

        conviction = float(data.get("conviction", 0.5))
        credibility = float(data.get("credibility", 0.4))
        background = str(data.get("background", "")).replace("\n", " ").strip()

        persona = StructuredPersona(
            agent_id=agent_id,
            archetype=archetype,
            big_five=bf,
            conviction=conviction,
            credibility=credibility,
            background=background[:200],
            initial_stance=stance,
        )
        # Guardrail: bots/trolls from the LLM path shouldn't happen, but if
        # they do, re-level conviction/credibility to match their archetype.
        if archetype in (Archetype.BOT, Archetype.TROLL):
            floor = StructuredPersona.default_for_archetype(
                agent_id=agent_id, archetype=archetype,
            )
            persona.conviction = max(persona.conviction, floor.conviction)
            persona.credibility = min(persona.credibility, floor.credibility)
        return persona

    def _procedural_fallback(
        self,
        *,
        agent_id: int,
        archetype: Archetype,
        entity_name: str,
        entity_type: str,
    ) -> StructuredPersona:
        """Used when the LLM call fails. Keeps the simulation moving."""
        rng = self._rng
        persona = StructuredPersona.default_for_archetype(
            agent_id=agent_id,
            archetype=archetype,
            background=f"{entity_name} ({entity_type})",
        )
        persona.big_five = BigFive(
            openness=rng.uniform(0.3, 0.8),
            conscientiousness=rng.uniform(0.3, 0.8),
            extraversion=rng.uniform(0.2, 0.8),
            agreeableness=rng.uniform(0.3, 0.8),
            neuroticism=rng.uniform(0.2, 0.7),
        ).clamp()
        persona.initial_stance = StanceVector(
            label="neutral",
            valence=rng.uniform(-0.3, 0.3),
        )
        return persona


def _parse_llm_json(raw: str) -> Dict[str, Any]:
    """Strip code fences some models still emit in JSON mode, then parse."""
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return json.loads(cleaned)

"""
Private Impact Profile Generator

Converts Zep graph entities into RelationalAgentProfile instances for the
Private Impact simulation mode.

Extends OasisProfileGenerator with relational dimensions:
- Relationship type with the decision maker (hierarchical, client, peer, ...)
- Trust level, financial sensitivity, equity tolerance, institutional loyalty
- Natural reaction mode (internalize, confront, silent_leave, coalition_build)
- Cascade influence graph (which agents this agent can expose)

Key design principle (from IDEE-FORK-MIROFISH.md §4):
    The `persona` field is the sole behavioral vector injected into the LLM
    system prompt each round. All relational dimensions are encoded as natural
    language inside `persona` — no engine modification required.
"""

import json
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock
from typing import Any, Dict, List, Optional

import concurrent.futures

from openai import OpenAI
from zep_cloud.client import Zep

from ..config import Config
from ..utils.logger import get_logger
from ..utils.locale import get_language_instruction, get_locale, set_locale
from .oasis_profile_generator import OasisAgentProfile, OasisProfileGenerator
from .zep_entity_reader import EntityNode

logger = get_logger('mirofish.private_impact_profile')


# ── RelationalAgentProfile ────────────────────────────────────────────────────

@dataclass
class RelationalAgentProfile(OasisAgentProfile):
    """
    Extended OASIS Agent Profile with relational network dimensions.

    All relational fields are encoded into the `persona` text field via
    _encode_relational_persona() before being stored. The inherited `persona`
    is what gets injected into the LLM system prompt each simulation round.
    """

    # Relationship with the decision maker
    relational_link_type: str = "peer"          # hierarchical | client | peer | family | competitor
    relational_seniority_years: int = 0
    relational_trust_level: float = 0.5         # 0.0 → 1.0

    # Psycho-social dimensions
    financial_sensitivity: float = 0.5          # Sensitivity to wealth signals
    equity_tolerance: float = 0.5               # Tolerance for status disparities
    institutional_loyalty: float = 0.5          # Loyalty to the org vs the person

    # Natural reaction mode when facing a triggering decision
    private_reaction_mode: str = "internalize"  # internalize | confront | silent_leave | coalition_build

    # Cascade influence graph: agent_ids this agent can expose
    cascade_influence: List[int] = field(default_factory=list)

    def to_private_format(self) -> Dict[str, Any]:
        """
        Serialize to the format expected by run_private_simulation.py.

        The simulation engine reads agent_configs as plain dicts, accessing:
        agent_id, entity_name, persona, cascade_influence, active_hours,
        activity_level.
        """
        return {
            "agent_id": self.user_id,
            "entity_name": self.name,
            "user_name": self.user_name,
            "bio": self.bio,
            "persona": self.persona,                    # Encoded with relational context
            "cascade_influence": self.cascade_influence,
            "relational_link_type": self.relational_link_type,
            "relational_seniority_years": self.relational_seniority_years,
            "relational_trust_level": self.relational_trust_level,
            "financial_sensitivity": self.financial_sensitivity,
            "equity_tolerance": self.equity_tolerance,
            "institutional_loyalty": self.institutional_loyalty,
            "private_reaction_mode": self.private_reaction_mode,
            "age": self.age,
            "gender": self.gender,
            "mbti": self.mbti,
            "country": self.country,
            "profession": self.profession,
            "source_entity_uuid": self.source_entity_uuid,
            "source_entity_type": self.source_entity_type,
            "created_at": self.created_at,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Full dict representation including relational fields."""
        base = super().to_dict()
        base.update({
            "relational_link_type": self.relational_link_type,
            "relational_seniority_years": self.relational_seniority_years,
            "relational_trust_level": self.relational_trust_level,
            "financial_sensitivity": self.financial_sensitivity,
            "equity_tolerance": self.equity_tolerance,
            "institutional_loyalty": self.institutional_loyalty,
            "private_reaction_mode": self.private_reaction_mode,
            "cascade_influence": self.cascade_influence,
        })
        return base


# ── PrivateImpactProfileGenerator ────────────────────────────────────────────

class PrivateImpactProfileGenerator(OasisProfileGenerator):
    """
    Generates RelationalAgentProfile instances for the Private Impact simulation.

    Extends OasisProfileGenerator with:
    - Relational entity types (Employee, Manager, Client, ...)
    - LLM prompt enriched with relational dimensions
    - Relational rule-based fallback by entity type
    - persona encoding that injects relational context as natural language

    Pipeline (same as OasisProfileGenerator):
        EntityNode (Zep) → _build_entity_context() → LLM / rule-based
        → RelationalAgentProfile (relational fields encoded into persona)
    """

    # Relational entity types — map to default behavioral parameters
    RELATIONAL_ENTITY_TYPES = [
        "employee", "manager", "client", "competitor",
        "partner", "familymember", "colleague", "investor",
    ]

    # Default behavioral parameters by relational type
    # (trust_level, financial_sensitivity, equity_tolerance,
    #  institutional_loyalty, reaction_mode, activity_level, active_hours)
    RELATIONAL_DEFAULTS: Dict[str, Dict[str, Any]] = {
        "employee": {
            "trust_level": 0.6,
            "financial_sensitivity": 0.7,
            "equity_tolerance": 0.4,
            "institutional_loyalty": 0.6,
            "reaction_mode": "internalize",
            "activity_level": 0.6,
            "active_hours": list(range(8, 19)),
            "influence_weight": 0.8,
        },
        "manager": {
            "trust_level": 0.7,
            "financial_sensitivity": 0.5,
            "equity_tolerance": 0.5,
            "institutional_loyalty": 0.7,
            "reaction_mode": "confront",
            "activity_level": 0.5,
            "active_hours": list(range(8, 20)),
            "influence_weight": 1.5,
        },
        "client": {
            "trust_level": 0.4,
            "financial_sensitivity": 0.3,
            "equity_tolerance": 0.6,
            "institutional_loyalty": 0.3,
            "reaction_mode": "silent_leave",
            "activity_level": 0.3,
            "active_hours": list(range(9, 13)) + list(range(17, 21)),
            "influence_weight": 1.2,
        },
        "competitor": {
            "trust_level": 0.2,
            "financial_sensitivity": 0.4,
            "equity_tolerance": 0.7,
            "institutional_loyalty": 0.1,
            "reaction_mode": "coalition_build",
            "activity_level": 0.2,
            "active_hours": list(range(9, 19)),
            "influence_weight": 1.0,
        },
        "partner": {
            "trust_level": 0.6,
            "financial_sensitivity": 0.4,
            "equity_tolerance": 0.6,
            "institutional_loyalty": 0.5,
            "reaction_mode": "internalize",
            "activity_level": 0.4,
            "active_hours": list(range(9, 18)),
            "influence_weight": 1.3,
        },
        "familymember": {
            "trust_level": 0.8,
            "financial_sensitivity": 0.8,
            "equity_tolerance": 0.5,
            "institutional_loyalty": 0.2,
            "reaction_mode": "confront",
            "activity_level": 0.7,
            "active_hours": list(range(7, 10)) + list(range(18, 24)),
            "influence_weight": 0.9,
        },
    }

    # Reaction mode descriptions for LLM prompt injection
    REACTION_MODE_DESCRIPTIONS: Dict[str, str] = {
        "internalize": "processes the news internally without immediate visible action; absorbs tension before potentially acting later",
        "confront": "tends to address the issue head-on, speaking directly to the decision maker or raising concerns openly",
        "silent_leave": "quietly disengages — reduces commitment, starts looking for alternatives, without announcing it",
        "coalition_build": "looks for allies among peers before taking any visible action; builds shared narratives",
    }

    def generate_profile_from_entity(
        self,
        entity: EntityNode,
        user_id: int,
        use_llm: bool = True,
        cascade_influence: Optional[List[int]] = None,
    ) -> RelationalAgentProfile:
        """
        Generate a RelationalAgentProfile from a Zep entity node.

        Divergence from OasisProfileGenerator.generate_profile_from_entity:
        Returns RelationalAgentProfile instead of OasisAgentProfile.
        Relational dimensions are encoded into the persona text field.

        Args:
            entity: Zep entity node.
            user_id: Agent ID in the simulation.
            use_llm: Whether to use LLM for profile generation.
            cascade_influence: List of agent_ids this agent can expose (optional).

        Returns:
            RelationalAgentProfile with relational context encoded in persona.
        """
        entity_type = entity.get_entity_type() or "peer"
        name = entity.name
        user_name = self._generate_username(name)
        context = self._build_entity_context(entity)

        if use_llm:
            profile_data = self._generate_relational_profile_with_llm(
                entity_name=name,
                entity_type=entity_type,
                entity_summary=entity.summary,
                entity_attributes=entity.attributes,
                context=context,
            )
        else:
            profile_data = self._generate_relational_profile_rule_based(
                entity_name=name,
                entity_type=entity_type,
                entity_summary=entity.summary,
            )

        # Extract relational dimensions from LLM output
        relational_link_type = profile_data.get("relational_link_type", "peer")
        seniority_years = int(profile_data.get("relational_seniority_years", 0))
        trust_level = float(profile_data.get("relational_trust_level", 0.5))
        financial_sensitivity = float(profile_data.get("financial_sensitivity", 0.5))
        equity_tolerance = float(profile_data.get("equity_tolerance", 0.5))
        institutional_loyalty = float(profile_data.get("institutional_loyalty", 0.5))
        reaction_mode = profile_data.get("private_reaction_mode", "internalize")

        # Clamp floats to [0.0, 1.0]
        trust_level = max(0.0, min(1.0, trust_level))
        financial_sensitivity = max(0.0, min(1.0, financial_sensitivity))
        equity_tolerance = max(0.0, min(1.0, equity_tolerance))
        institutional_loyalty = max(0.0, min(1.0, institutional_loyalty))

        # Encode relational context into the persona text
        base_persona = profile_data.get(
            "persona", entity.summary or f"A {entity_type} named {name}."
        )
        enriched_persona = self._encode_relational_persona(
            base_persona=base_persona,
            name=name,
            relational_link_type=relational_link_type,
            seniority_years=seniority_years,
            trust_level=trust_level,
            financial_sensitivity=financial_sensitivity,
            equity_tolerance=equity_tolerance,
            institutional_loyalty=institutional_loyalty,
            reaction_mode=reaction_mode,
        )

        return RelationalAgentProfile(
            user_id=user_id,
            user_name=user_name,
            name=name,
            bio=profile_data.get("bio", f"{entity_type}: {name}"),
            persona=enriched_persona,
            karma=profile_data.get("karma", random.randint(500, 3000)),
            friend_count=profile_data.get("friend_count", random.randint(20, 300)),
            follower_count=profile_data.get("follower_count", random.randint(30, 500)),
            statuses_count=profile_data.get("statuses_count", random.randint(50, 1000)),
            age=profile_data.get("age"),
            gender=profile_data.get("gender"),
            mbti=profile_data.get("mbti"),
            country=profile_data.get("country"),
            profession=profile_data.get("profession"),
            interested_topics=profile_data.get("interested_topics", []),
            source_entity_uuid=entity.uuid,
            source_entity_type=entity_type,
            relational_link_type=relational_link_type,
            relational_seniority_years=seniority_years,
            relational_trust_level=trust_level,
            financial_sensitivity=financial_sensitivity,
            equity_tolerance=equity_tolerance,
            institutional_loyalty=institutional_loyalty,
            private_reaction_mode=reaction_mode,
            cascade_influence=cascade_influence or [],
        )

    # ── Persona encoding ──────────────────────────────────────────────────────

    def _encode_relational_persona(
        self,
        base_persona: str,
        name: str,
        relational_link_type: str,
        seniority_years: int,
        trust_level: float,
        financial_sensitivity: float,
        equity_tolerance: float,
        institutional_loyalty: float,
        reaction_mode: str,
    ) -> str:
        """
        Encode relational dimensions into natural language appended to persona.

        This is the central mechanism: OASIS (and our private simulation) inject
        the persona field as-is into the LLM system prompt. By appending a
        structured relational context block, we guide agent behavior without
        modifying the simulation engine.

        Args:
            base_persona: Base persona text from LLM or rule-based fallback.
            name: Agent name.
            relational_link_type: Type of relationship with the decision maker.
            seniority_years: Years in this relational context.
            trust_level: Trust level with decision maker (0–1).
            financial_sensitivity: Sensitivity to wealth signals (0–1).
            equity_tolerance: Tolerance for status disparities (0–1).
            institutional_loyalty: Loyalty to the org vs the person (0–1).
            reaction_mode: Natural reaction pattern.

        Returns:
            Enriched persona string with relational context block appended.
        """
        # Trust descriptor
        if trust_level >= 0.75:
            trust_desc = "very high"
        elif trust_level >= 0.5:
            trust_desc = "moderate"
        elif trust_level >= 0.25:
            trust_desc = "low"
        else:
            trust_desc = "very low"

        # Financial sensitivity descriptor
        if financial_sensitivity >= 0.75:
            fin_desc = "highly sensitive to wealth signals and perceived inequity"
        elif financial_sensitivity >= 0.5:
            fin_desc = "moderately sensitive to financial signals"
        else:
            fin_desc = "relatively indifferent to wealth signals"

        # Equity tolerance descriptor
        if equity_tolerance <= 0.25:
            eq_desc = "very low tolerance for status disparities — notices and resents inequalities"
        elif equity_tolerance <= 0.5:
            eq_desc = "moderate discomfort with status disparities"
        else:
            eq_desc = "accepts status differences as normal"

        reaction_desc = self.REACTION_MODE_DESCRIPTIONS.get(
            reaction_mode,
            "processes the situation and responds according to their character"
        )

        seniority_str = (
            f"{seniority_years} year{'s' if seniority_years != 1 else ''}"
            if seniority_years > 0 else "recent"
        )

        loyalty_desc = (
            "strongly attached to the organization and its continuity"
            if institutional_loyalty >= 0.7
            else "balanced between personal interests and organizational ones"
            if institutional_loyalty >= 0.4
            else "primarily driven by personal interests over institutional ones"
        )

        relational_block = (
            f"\n\n--- Relational Context (Private Impact Simulation) ---\n"
            f"Your name is {name}.\n"
            f"Your relationship with the decision maker: {relational_link_type} "
            f"({seniority_str} of shared history).\n"
            f"Trust level with the decision maker: {trust_desc} ({trust_level:.1f}/1.0).\n"
            f"Financial sensitivity: {fin_desc} (score: {financial_sensitivity:.1f}).\n"
            f"Equity tolerance: {eq_desc} (score: {equity_tolerance:.1f}).\n"
            f"Institutional loyalty: {loyalty_desc} (score: {institutional_loyalty:.1f}).\n"
            f"Your natural reaction mode: {reaction_mode} — you {reaction_desc}.\n"
            f"--- End Relational Context ---"
        )

        return base_persona + relational_block

    # ── LLM profile generation ────────────────────────────────────────────────

    def _generate_relational_profile_with_llm(
        self,
        entity_name: str,
        entity_type: str,
        entity_summary: str,
        entity_attributes: Dict[str, Any],
        context: str,
    ) -> Dict[str, Any]:
        """
        Generate relational profile via LLM.

        Divergence from OasisProfileGenerator._generate_profile_with_llm:
        Adds relational dimension fields to the JSON output schema.
        Falls back to rule-based generation on failure (same pattern as parent).

        Args:
            entity_name: Entity name.
            entity_type: Entity type from Zep.
            entity_summary: Entity summary from Zep.
            entity_attributes: Entity attributes dict.
            context: Enriched context from _build_entity_context().

        Returns:
            Profile data dict including relational dimensions.
        """
        prompt = self._build_relational_persona_prompt(
            entity_name=entity_name,
            entity_type=entity_type,
            entity_summary=entity_summary,
            entity_attributes=entity_attributes,
            context=context,
        )
        system_prompt = (
            "You are an expert in organizational psychology and behavioral simulation. "
            "Generate realistic relational agent profiles for private impact simulations. "
            "Return valid JSON only — no markdown, no prose outside the JSON object. "
            f"{get_language_instruction()}"
        )

        max_attempts = 3
        last_error = None

        for attempt in range(max_attempts):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.7 - (attempt * 0.1),
                )

                content = response.choices[0].message.content
                finish_reason = response.choices[0].finish_reason

                if finish_reason == 'length':
                    logger.warning(f"LLM output truncated (attempt {attempt + 1}), attempting fix...")
                    content = self._fix_truncated_json(content)

                try:
                    result = json.loads(content)

                    # Ensure required fields
                    if not result.get("bio"):
                        result["bio"] = entity_summary[:200] if entity_summary else f"{entity_type}: {entity_name}"
                    if not result.get("persona"):
                        result["persona"] = entity_summary or f"{entity_name} is a {entity_type}."

                    return result

                except json.JSONDecodeError as je:
                    logger.warning(f"JSON parse failed (attempt {attempt + 1}): {str(je)[:80]}")
                    result = self._try_fix_json(content, entity_name, entity_type, entity_summary)
                    if result.get("_fixed"):
                        del result["_fixed"]
                        return result
                    last_error = je

            except Exception as e:
                logger.warning(f"LLM call failed (attempt {attempt + 1}): {str(e)[:80]}")
                last_error = e
                time.sleep(1 * (attempt + 1))

        logger.warning(
            f"LLM profile generation failed after {max_attempts} attempts: {last_error}. "
            f"Falling back to rule-based."
        )
        return self._generate_relational_profile_rule_based(
            entity_name=entity_name,
            entity_type=entity_type,
            entity_summary=entity_summary,
        )

    def _build_relational_persona_prompt(
        self,
        entity_name: str,
        entity_type: str,
        entity_summary: str,
        entity_attributes: Dict[str, Any],
        context: str,
    ) -> str:
        """
        Build the LLM prompt for relational profile generation.

        Divergence from parent _build_individual_persona_prompt:
        Adds relational dimension fields to the JSON schema.
        """
        attrs_str = json.dumps(entity_attributes, ensure_ascii=False) if entity_attributes else "none"
        context_str = context[:3000] if context else "No additional context."

        return f"""Generate a relational agent profile for a private impact simulation.

Entity name: {entity_name}
Entity type: {entity_type}
Entity summary: {entity_summary}
Entity attributes: {attrs_str}

Context:
{context_str}

Return a JSON object with these fields:

1. bio: Short profile description (max 200 characters)
2. persona: Detailed behavioral description (plain text, no line breaks inside the string, ~500 words):
   - Background, personality, professional history
   - Emotional patterns and communication style
   - Relationship with authority and institutions
   - Known reactions to organizational decisions
3. age: Integer (or null)
4. gender: "male", "female", or "other"
5. mbti: MBTI type (e.g. "INTJ") or null
6. country: Country name
7. profession: Current role or function
8. interested_topics: Array of relevant topics

Relational dimensions (required):
9.  relational_link_type: One of "hierarchical", "client", "peer", "family", "competitor"
10. relational_seniority_years: Integer (years in this relational context)
11. relational_trust_level: Float 0.0–1.0 (trust in decision maker)
12. financial_sensitivity: Float 0.0–1.0 (sensitivity to wealth signals)
13. equity_tolerance: Float 0.0–1.0 (tolerance for status disparities)
14. institutional_loyalty: Float 0.0–1.0 (loyalty to org vs personal interests)
15. private_reaction_mode: One of "internalize", "confront", "silent_leave", "coalition_build"

Rules:
- All string values must not contain literal line breaks
- persona must be a single continuous text paragraph
- Float values must be between 0.0 and 1.0
- Infer relational dimensions from entity type and context when possible
"""

    # ── Rule-based fallback ───────────────────────────────────────────────────

    def _generate_relational_profile_rule_based(
        self,
        entity_name: str,
        entity_type: str,
        entity_summary: str,
    ) -> Dict[str, Any]:
        """
        Generate relational profile using predefined defaults by entity type.

        Divergence from OasisProfileGenerator._generate_profile_rule_based:
        Uses RELATIONAL_DEFAULTS table instead of social media entity types.
        Covers: Employee, Manager, Client, Competitor, Partner, FamilyMember.

        Args:
            entity_name: Entity name.
            entity_type: Relational entity type.
            entity_summary: Entity summary for persona fallback.

        Returns:
            Profile data dict with relational dimensions set from defaults.
        """
        type_key = entity_type.lower()
        defaults = self.RELATIONAL_DEFAULTS.get(type_key, self.RELATIONAL_DEFAULTS["employee"])

        base_persona = (
            entity_summary
            or f"{entity_name} is a {entity_type} connected to the decision maker's network."
        )

        return {
            "bio": (
                entity_summary[:150]
                if entity_summary
                else f"{entity_type}: {entity_name}"
            ),
            "persona": base_persona,
            "age": random.randint(25, 55),
            "gender": random.choice(["male", "female"]),
            "mbti": random.choice(self.MBTI_TYPES),
            "country": random.choice(self.COUNTRIES),
            "profession": entity_type.capitalize(),
            "interested_topics": ["Professional Development", "Organizational Dynamics"],
            # Relational dimensions from defaults table
            "relational_link_type": type_key if type_key in (
                "hierarchical", "client", "peer", "family", "competitor"
            ) else "peer",
            "relational_seniority_years": random.randint(1, 8),
            "relational_trust_level": defaults["trust_level"],
            "financial_sensitivity": defaults["financial_sensitivity"],
            "equity_tolerance": defaults.get("equity_tolerance", 0.5),
            "institutional_loyalty": defaults.get("institutional_loyalty", 0.5),
            "private_reaction_mode": defaults["reaction_mode"],
        }

    # ── Batch generation ──────────────────────────────────────────────────────

    def generate_profiles_from_entities(
        self,
        entities: List[EntityNode],
        use_llm: bool = True,
        progress_callback: Optional[callable] = None,
        graph_id: Optional[str] = None,
        parallel_count: int = 5,
        realtime_output_path: Optional[str] = None,
        cascade_influence_map: Optional[Dict[int, List[int]]] = None,
        **kwargs,  # absorb unused parent kwargs (output_platform, etc.)
    ) -> List[RelationalAgentProfile]:
        """
        Generate RelationalAgentProfile instances for all entities in parallel.

        Divergence from OasisProfileGenerator.generate_profiles_from_entities:
        Returns RelationalAgentProfile instances.
        Accepts cascade_influence_map to assign relational graph edges per agent.

        Args:
            entities: List of Zep entity nodes.
            use_llm: Whether to use LLM generation (falls back to rule-based).
            progress_callback: Optional callback(current, total, message).
            graph_id: Zep graph ID for context enrichment.
            parallel_count: Number of concurrent generation threads.
            realtime_output_path: Path to write profiles as they are generated.
            cascade_influence_map: {agent_index: [influenced_agent_ids]}.

        Returns:
            List of RelationalAgentProfile instances.
        """
        if graph_id:
            self.graph_id = graph_id

        cascade_influence_map = cascade_influence_map or {}
        total = len(entities)
        profiles: List[Optional[RelationalAgentProfile]] = [None] * total
        completed_count = [0]
        lock = Lock()

        def save_realtime() -> None:
            """Write generated profiles to file as they complete."""
            if not realtime_output_path:
                return
            with lock:
                existing = [p for p in profiles if p is not None]
                if not existing:
                    return
                try:
                    data = [p.to_private_format() for p in existing]
                    with open(realtime_output_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                except Exception as e:
                    logger.warning(f"Realtime save failed: {e}")

        current_locale = get_locale()

        def generate_single(idx: int, entity: EntityNode) -> tuple:
            set_locale(current_locale)
            entity_type = entity.get_entity_type() or "peer"
            cascade = cascade_influence_map.get(idx, [])

            try:
                profile = self.generate_profile_from_entity(
                    entity=entity,
                    user_id=idx,
                    use_llm=use_llm,
                    cascade_influence=cascade,
                )
                self._print_generated_relational_profile(entity.name, entity_type, profile)
                return idx, profile, None

            except Exception as e:
                logger.error(f"Profile generation failed for {entity.name}: {e}")
                fallback = RelationalAgentProfile(
                    user_id=idx,
                    user_name=self._generate_username(entity.name),
                    name=entity.name,
                    bio=f"{entity_type}: {entity.name}",
                    persona=(
                        entity.summary
                        or f"{entity.name} is a {entity_type} in the relational network."
                    ),
                    source_entity_uuid=entity.uuid,
                    source_entity_type=entity_type,
                    cascade_influence=cascade,
                )
                return idx, fallback, str(e)

        logger.info(
            f"Starting parallel profile generation — {total} entities, "
            f"parallel_count={parallel_count}"
        )
        print(f"\n{'='*60}")
        print(f"Private Impact — Generating {total} relational profiles (parallel: {parallel_count})")
        print(f"{'='*60}\n")

        with concurrent.futures.ThreadPoolExecutor(max_workers=parallel_count) as executor:
            future_map = {
                executor.submit(generate_single, idx, entity): (idx, entity)
                for idx, entity in enumerate(entities)
            }

            for future in concurrent.futures.as_completed(future_map):
                idx, entity = future_map[future]
                entity_type = entity.get_entity_type() or "peer"

                try:
                    result_idx, profile, error = future.result()
                    profiles[result_idx] = profile

                    with lock:
                        completed_count[0] += 1
                        current = completed_count[0]

                    save_realtime()

                    if progress_callback:
                        progress_callback(
                            current,
                            total,
                            f"Done {current}/{total}: {entity.name} ({entity_type})"
                        )

                    if error:
                        logger.warning(f"[{current}/{total}] {entity.name} using fallback: {error}")
                    else:
                        logger.info(f"[{current}/{total}] Generated: {entity.name} ({entity_type})")

                except Exception as e:
                    logger.error(f"Error processing {entity.name}: {e}")
                    with lock:
                        completed_count[0] += 1

                    profiles[idx] = RelationalAgentProfile(
                        user_id=idx,
                        user_name=self._generate_username(entity.name),
                        name=entity.name,
                        bio=f"{entity_type}: {entity.name}",
                        persona=entity.summary or "A participant in the relational network.",
                        source_entity_uuid=entity.uuid,
                        source_entity_type=entity_type,
                    )
                    save_realtime()

        valid_count = len([p for p in profiles if p is not None])
        print(f"\n{'='*60}")
        print(f"Profile generation complete — {valid_count} relational agents ready")
        print(f"{'='*60}\n")

        return [p for p in profiles if p is not None]

    def save_profiles(
        self,
        profiles: List[RelationalAgentProfile],
        file_path: str,
        platform: str = "private",
    ) -> None:
        """
        Save relational profiles to JSON.

        Divergence from OasisProfileGenerator.save_profiles:
        Always uses to_private_format() — no CSV output, no Reddit/Twitter format.
        The output is a JSON array of agent config dicts consumed by
        run_private_simulation.py.

        Args:
            profiles: List of RelationalAgentProfile instances.
            file_path: Output path (.json).
            platform: Ignored — always uses private format.
        """
        data = [p.to_private_format() for p in profiles]
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(profiles)} relational profiles to {file_path}")

    # ── Console output ────────────────────────────────────────────────────────

    def _print_generated_relational_profile(
        self,
        entity_name: str,
        entity_type: str,
        profile: RelationalAgentProfile,
    ) -> None:
        """Print a summary of the generated relational profile to stdout."""
        separator = "-" * 70
        lines = [
            f"\n{separator}",
            f"[Private Impact] Profile generated: {entity_name} ({entity_type})",
            separator,
            f"Name: {profile.name}  |  Link: {profile.relational_link_type}  "
            f"|  Reaction: {profile.private_reaction_mode}",
            f"Trust: {profile.relational_trust_level:.2f}  "
            f"|  Fin.Sensitivity: {profile.financial_sensitivity:.2f}  "
            f"|  Loyalty: {profile.institutional_loyalty:.2f}",
            f"Cascade influence: {profile.cascade_influence}",
            f"",
            f"[Bio] {profile.bio}",
            separator,
        ]
        print("\n".join(lines))

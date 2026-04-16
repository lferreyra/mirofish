"""
Private Impact Config Generator

Generates behavioral parameters for RelationalAgents in Private Impact mode.
Equivalent of simulation_config_generator.py for the private relational network.

Key differences from SimulationConfigGenerator:
- No PlatformConfig (no social network)
- Time is measured in days with rounds per day (morning / noon / evening)
- RelationalActivityConfig replaces AgentActivityConfig
- PrivateEventConfig uses a decision statement instead of initial posts
- LLM calls: time config → event config → agent configs (batches of 15)
"""

import json
import math
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from openai import OpenAI

from ..config import Config
from ..utils.logger import get_logger
from ..utils.locale import get_language_instruction

logger = get_logger('mirofish.private_impact_config')


# ── Dataclasses ───────────────────────────────────────────────────────────────

@dataclass
class RelationalActivityConfig:
    """
    Behavioral activity configuration for a single RelationalAgent.

    Equivalent of AgentActivityConfig for the private simulation mode.
    No posting frequencies — private reactions replace social media posts.
    """
    agent_id: int
    entity_uuid: str
    entity_name: str
    relational_link_type: str  # employee | manager | client | competitor | partner | familymember

    # Activity parameters
    activity_level: float = 0.5         # Overall engagement level (0.0–1.0)
    response_delay_min: int = 0         # Min reaction delay (days)
    response_delay_max: int = 3         # Max reaction delay (days)

    # Behavioral stance toward the decision
    sentiment_bias: float = 0.0         # -1.0 (hostile) → 1.0 (supportive)
    stance: str = "neutral"             # supportive | opposing | neutral | observer

    # Influence within the relational graph
    influence_weight: float = 1.0       # Weight for cascade propagation

    # Relational graph: agent_ids this agent can expose to the decision
    cascade_influence: List[int] = field(default_factory=list)

    # Simulation round at which this agent is first exposed to the decision
    exposure_round: int = 0             # 0 = exposed at the very first round


@dataclass
class PrivateTimeConfig:
    """
    Time configuration for the Private Impact simulation.

    Replaces TimeSimulationConfig (Twitter/hour-based) with a day-based,
    relational-rhythm model: days × rounds per day.
    """
    total_simulation_days: int = 30     # Total simulated days
    rounds_per_day: int = 3             # Morning / noon / evening
    reaction_delay_days_min: int = 0    # Min delay before an agent reacts
    reaction_delay_days_max: int = 7    # Max delay before an agent reacts


@dataclass
class PrivateEventConfig:
    """
    Event configuration for the Private Impact simulation.

    Replaces EventConfig (social posts) with a decision injection model.
    """
    decision_statement: str = ""                            # The decision injected into the network
    decision_maker_profile: str = ""                        # Short description of the decision maker
    hot_topics: List[str] = field(default_factory=list)     # Related sensitive topics
    initial_exposed_agent_ids: List[int] = field(          # Distance-1 agents (heard it first)
        default_factory=list
    )


@dataclass
class PrivateSimulationParameters:
    """Complete parameter set for a Private Impact simulation."""
    time_config: PrivateTimeConfig = field(default_factory=PrivateTimeConfig)
    agent_configs: List[RelationalActivityConfig] = field(default_factory=list)
    event_config: PrivateEventConfig = field(default_factory=PrivateEventConfig)

    # LLM metadata
    llm_model: str = ""
    llm_base_url: str = ""
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    generation_reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to plain dict."""
        return {
            "time_config": asdict(self.time_config),
            "agent_configs": [asdict(a) for a in self.agent_configs],
            "event_config": asdict(self.event_config),
            "llm_model": self.llm_model,
            "llm_base_url": self.llm_base_url,
            "generated_at": self.generated_at,
            "generation_reasoning": self.generation_reasoning,
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


# ── PrivateImpactConfigGenerator ──────────────────────────────────────────────

class PrivateImpactConfigGenerator:
    """
    Generates PrivateSimulationParameters for the Private Impact simulation.

    Equivalent of SimulationConfigGenerator for the private relational mode.
    Uses 3 sequential LLM calls:
        1. PrivateTimeConfig  — relational rhythm (days, rounds)
        2. PrivateEventConfig — decision injection setup
        3. RelationalActivityConfig list — batches of AGENTS_PER_BATCH

    Falls back to a rule-based table per relational type on LLM failure.
    """

    AGENTS_PER_BATCH = 15

    # Context length limits (characters)
    TIME_CONFIG_CONTEXT_LENGTH = 8000
    EVENT_CONFIG_CONTEXT_LENGTH = 6000
    AGENT_SUMMARY_LENGTH = 300

    # Rule-based fallback table by relational type
    # Keys: activity_level, response_delay_min, response_delay_max, stance, influence_weight
    RELATIONAL_FALLBACKS: Dict[str, Dict[str, Any]] = {
        "employee": {
            "activity_level": 0.6,
            "response_delay_min": 0,
            "response_delay_max": 3,
            "sentiment_bias": 0.0,
            "stance": "neutral",
            "influence_weight": 0.8,
        },
        "manager": {
            "activity_level": 0.5,
            "response_delay_min": 0,
            "response_delay_max": 1,
            "sentiment_bias": 0.0,
            "stance": "neutral",
            "influence_weight": 1.5,
        },
        "client": {
            "activity_level": 0.3,
            "response_delay_min": 2,
            "response_delay_max": 7,
            "sentiment_bias": 0.0,
            "stance": "observer",
            "influence_weight": 1.2,
        },
        "competitor": {
            "activity_level": 0.2,
            "response_delay_min": 1,
            "response_delay_max": 5,
            "sentiment_bias": -0.3,
            "stance": "opposing",
            "influence_weight": 1.0,
        },
        "partner": {
            "activity_level": 0.4,
            "response_delay_min": 0,
            "response_delay_max": 2,
            "sentiment_bias": 0.1,
            "stance": "neutral",
            "influence_weight": 1.3,
        },
        "familymember": {
            "activity_level": 0.7,
            "response_delay_min": 0,
            "response_delay_max": 0,
            "sentiment_bias": 0.4,
            "stance": "supportive",
            "influence_weight": 0.9,
        },
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        self.model_name = model_name or Config.LLM_MODEL_NAME

        if not self.api_key:
            raise ValueError("LLM_API_KEY is not configured")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

    # ── Public API ─────────────────────────────────────────────────────────────

    def generate_config(
        self,
        agent_profiles: List[Dict[str, Any]],
        simulation_requirement: str,
        decision_context: str = "",
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> PrivateSimulationParameters:
        """
        Generate the complete PrivateSimulationParameters.

        Performs 3 sequential LLM call groups:
            Step 1 — PrivateTimeConfig (relational rhythm)
            Step 2 — PrivateEventConfig (decision injection)
            Step 3-N — RelationalActivityConfig batches (AGENTS_PER_BATCH each)

        Falls back to rule-based generation per step on LLM failure.

        Args:
            agent_profiles: List of agent dicts from private_impact_profile_generator.
                Each dict must include: agent_id, entity_name, relational_link_type,
                cascade_influence, source_entity_uuid, persona (optional).
            simulation_requirement: Natural language description of the simulation goal.
            decision_context: Additional context about the decision or the organization.
            progress_callback: Optional callback(current_step, total_steps, message).

        Returns:
            PrivateSimulationParameters ready for run_private_simulation.py.
        """
        num_agents = len(agent_profiles)
        num_batches = math.ceil(num_agents / self.AGENTS_PER_BATCH)
        total_steps = 2 + num_batches  # time + event + N agent batches
        current_step = 0

        def report(step: int, message: str) -> None:
            nonlocal current_step
            current_step = step
            if progress_callback:
                progress_callback(step, total_steps, message)
            logger.info(f"[{step}/{total_steps}] {message}")

        context = self._build_context(
            simulation_requirement=simulation_requirement,
            decision_context=decision_context,
            agent_profiles=agent_profiles,
        )
        reasoning_parts: List[str] = []

        # ── Step 1: PrivateTimeConfig ─────────────────────────────────────────
        report(1, "Generating relational time configuration...")
        time_result = self._generate_time_config(context, num_agents)
        time_config = self._parse_time_config(time_result)
        reasoning_parts.append(f"Time: {time_result.get('reasoning', 'ok')}")

        # ── Step 2: PrivateEventConfig ────────────────────────────────────────
        report(2, "Generating decision event configuration...")
        event_result = self._generate_event_config(context, simulation_requirement, agent_profiles)
        event_config = self._parse_event_config(event_result, agent_profiles)
        reasoning_parts.append(f"Event: {event_result.get('reasoning', 'ok')}")

        # ── Steps 3-N: RelationalActivityConfig batches ───────────────────────
        all_agent_configs: List[RelationalActivityConfig] = []
        for batch_idx in range(num_batches):
            start = batch_idx * self.AGENTS_PER_BATCH
            end = min(start + self.AGENTS_PER_BATCH, num_agents)
            batch = agent_profiles[start:end]

            report(
                3 + batch_idx,
                f"Generating agent configs {start + 1}–{end} / {num_agents}...",
            )

            batch_configs = self._generate_agent_configs_batch(
                context=context,
                agent_profiles=batch,
                start_idx=start,
                simulation_requirement=simulation_requirement,
            )
            all_agent_configs.extend(batch_configs)

        reasoning_parts.append(f"Agents: {len(all_agent_configs)} configured")

        return PrivateSimulationParameters(
            time_config=time_config,
            agent_configs=all_agent_configs,
            event_config=event_config,
            llm_model=self.model_name,
            llm_base_url=self.base_url,
            generation_reasoning=" | ".join(reasoning_parts),
        )

    # ── Context builder ────────────────────────────────────────────────────────

    def _build_context(
        self,
        simulation_requirement: str,
        decision_context: str,
        agent_profiles: List[Dict[str, Any]],
    ) -> str:
        """Build the shared LLM context string for all generation steps."""
        by_type: Dict[str, int] = {}
        for a in agent_profiles:
            rtype = a.get("relational_link_type", "unknown")
            by_type[rtype] = by_type.get(rtype, 0) + 1

        type_summary = "\n".join(
            f"  - {rtype}: {count}" for rtype, count in sorted(by_type.items())
        )

        parts = [
            f"## Simulation Requirement\n{simulation_requirement}",
            f"\n## Relational Network ({len(agent_profiles)} agents)\n{type_summary}",
        ]

        if decision_context:
            parts.append(f"\n## Decision Context\n{decision_context[:3000]}")

        return "\n".join(parts)

    # ── Step 1: Time config ────────────────────────────────────────────────────

    def _generate_time_config(
        self, context: str, num_agents: int
    ) -> Dict[str, Any]:
        """Generate PrivateTimeConfig via LLM."""
        context_truncated = context[:self.TIME_CONFIG_CONTEXT_LENGTH]

        prompt = f"""Based on the following private impact simulation context, generate a relational time configuration.

{context_truncated}

## Task
Generate a time configuration for a private relational network simulation.
Unlike social media, this is a closed human network where decisions propagate
over days through interpersonal channels (conversations, emails, hallway talks).

Return a JSON object (no markdown):
{{
    "total_simulation_days": <int, 7–90, how many days until the network reaches equilibrium>,
    "rounds_per_day": <int, 2–4, typically 3: morning/noon/evening>,
    "reaction_delay_days_min": <int, 0–3>,
    "reaction_delay_days_max": <int, 1–14>,
    "reasoning": "<brief explanation>"
}}

Guidelines:
- Major organizational decisions: 30–60 days
- Personal or family decisions: 7–21 days
- Sudden crises: 7–14 days
- rounds_per_day=3 is the standard (morning / noon / evening)
- reaction_delay_days_max should not exceed total_simulation_days / 4"""

        system_prompt = (
            "You are an expert in organizational psychology and network dynamics. "
            "Return pure JSON only — no markdown. "
            f"{get_language_instruction()}"
        )

        try:
            return self._call_llm_with_retry(prompt, system_prompt)
        except Exception as e:
            logger.warning(f"Time config LLM failed: {e}. Using defaults.")
            return self._default_time_config()

    def _default_time_config(self) -> Dict[str, Any]:
        """Rule-based default time config."""
        return {
            "total_simulation_days": 30,
            "rounds_per_day": 3,
            "reaction_delay_days_min": 0,
            "reaction_delay_days_max": 7,
            "reasoning": "Default relational time config",
        }

    def _parse_time_config(self, result: Dict[str, Any]) -> PrivateTimeConfig:
        """Parse and validate PrivateTimeConfig from LLM result."""
        total_days = max(7, int(result.get("total_simulation_days", 30)))
        rounds_per_day = max(2, min(4, int(result.get("rounds_per_day", 3))))
        delay_min = max(0, int(result.get("reaction_delay_days_min", 0)))
        delay_max = max(delay_min, int(result.get("reaction_delay_days_max", 7)))

        if delay_max >= total_days:
            delay_max = max(delay_min + 1, total_days // 4)
            logger.warning(f"reaction_delay_days_max capped to {delay_max}")

        return PrivateTimeConfig(
            total_simulation_days=total_days,
            rounds_per_day=rounds_per_day,
            reaction_delay_days_min=delay_min,
            reaction_delay_days_max=delay_max,
        )

    # ── Step 2: Event config ───────────────────────────────────────────────────

    def _generate_event_config(
        self,
        context: str,
        simulation_requirement: str,
        agent_profiles: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Generate PrivateEventConfig via LLM."""
        context_truncated = context[:self.EVENT_CONFIG_CONTEXT_LENGTH]

        # Build distance-1 candidate list (agents closest to the decision maker)
        distance1_candidates = [
            {
                "agent_id": a.get("agent_id", i),
                "name": a.get("entity_name", ""),
                "type": a.get("relational_link_type", ""),
            }
            for i, a in enumerate(agent_profiles)
            if a.get("relational_link_type", "") in (
                "manager", "employee", "partner", "familymember"
            )
        ][:10]

        candidates_json = json.dumps(distance1_candidates, ensure_ascii=False)

        prompt = f"""Based on the following private impact simulation context, generate the event configuration.

{context_truncated}

## Distance-1 agent candidates (closest to decision maker)
{candidates_json}

## Task
Generate an event configuration for private impact injection.
Return a JSON object (no markdown):
{{
    "decision_statement": "<precise wording of the decision being injected — 2–4 sentences>",
    "decision_maker_profile": "<short description of the person making the decision — role, authority, relationship style>",
    "hot_topics": ["<sensitive topic 1>", "<sensitive topic 2>", ...],
    "initial_exposed_agent_ids": [<agent_id>, ...],
    "reasoning": "<brief explanation>"
}}

Rules:
- decision_statement must be specific and concrete, not vague
- initial_exposed_agent_ids must only contain ids from the distance-1 candidates list above
- initial_exposed_agent_ids should be 1–3 agents (direct announcement recipients)
- hot_topics: 3–6 strings describing the sensitive dimensions of this decision
  (e.g. "salary equity", "job security", "family impact", "competitive pressure")"""

        system_prompt = (
            "You are an expert in organizational decision impact simulation. "
            "Return pure JSON only — no markdown. "
            f"{get_language_instruction()}"
        )

        try:
            return self._call_llm_with_retry(prompt, system_prompt)
        except Exception as e:
            logger.warning(f"Event config LLM failed: {e}. Using defaults.")
            first_id = agent_profiles[0].get("agent_id", 0) if agent_profiles else 0
            return {
                "decision_statement": simulation_requirement,
                "decision_maker_profile": "The decision maker",
                "hot_topics": ["organizational change", "impact"],
                "initial_exposed_agent_ids": [first_id],
                "reasoning": "Default event config (LLM fallback)",
            }

    def _parse_event_config(
        self,
        result: Dict[str, Any],
        agent_profiles: List[Dict[str, Any]],
    ) -> PrivateEventConfig:
        """Parse and validate PrivateEventConfig from LLM result."""
        valid_ids = {a.get("agent_id", i) for i, a in enumerate(agent_profiles)}
        raw_exposed = result.get("initial_exposed_agent_ids", [])
        exposed = [aid for aid in raw_exposed if aid in valid_ids]

        if not exposed and agent_profiles:
            exposed = [agent_profiles[0].get("agent_id", 0)]

        return PrivateEventConfig(
            decision_statement=result.get("decision_statement", ""),
            decision_maker_profile=result.get("decision_maker_profile", ""),
            hot_topics=result.get("hot_topics", []),
            initial_exposed_agent_ids=exposed,
        )

    # ── Steps 3-N: Agent config batches ───────────────────────────────────────

    def _generate_agent_configs_batch(
        self,
        context: str,
        agent_profiles: List[Dict[str, Any]],
        start_idx: int,
        simulation_requirement: str,
    ) -> List[RelationalActivityConfig]:
        """
        Generate a batch of RelationalActivityConfig via LLM with rule-based fallback.

        Args:
            context: Shared simulation context string.
            agent_profiles: Slice of agent dicts for this batch.
            start_idx: Index of the first agent in the full list (for logging).
            simulation_requirement: Natural language simulation goal.

        Returns:
            List of RelationalActivityConfig for this batch.
        """
        agent_list = []
        summary_len = self.AGENT_SUMMARY_LENGTH
        for i, a in enumerate(agent_profiles):
            agent_list.append({
                "agent_id": a.get("agent_id", start_idx + i),
                "entity_name": a.get("entity_name", ""),
                "relational_link_type": a.get("relational_link_type", "peer"),
                "cascade_influence": a.get("cascade_influence", []),
                "persona_excerpt": (a.get("persona", "") or "")[:summary_len],
            })

        prompt = f"""Based on the following private impact simulation context, generate activity configurations for each relational agent.

Simulation requirement: {simulation_requirement}

## Agent list
```json
{json.dumps(agent_list, ensure_ascii=False, indent=2)}
```

## Task
Generate a RelationalActivityConfig for each agent.

Behavioral guidelines by relational type:
- employee:     activity_level=0.6, response_delay_max=3 days, stance=neutral
- manager:      activity_level=0.5, response_delay_max=1 day,  stance=neutral
- client:       activity_level=0.3, response_delay_max=7 days, stance=observer
- competitor:   activity_level=0.2, response_delay_max=5 days, stance=opposing
- partner:      activity_level=0.4, response_delay_max=2 days, stance=neutral
- familymember: activity_level=0.7, response_delay_max=0 days, stance=supportive

Return a JSON object (no markdown):
{{
    "agent_configs": [
        {{
            "agent_id": <must match input>,
            "activity_level": <0.0–1.0>,
            "response_delay_min": <int, days>,
            "response_delay_max": <int, days>,
            "sentiment_bias": <-1.0 to 1.0>,
            "stance": "<supportive|opposing|neutral|observer>",
            "influence_weight": <float>,
            "exposure_round": <int, 0 for initial exposed agents>
        }},
        ...
    ]
}}

Rules:
- agent_id must match the input exactly
- stance must be one of: supportive, opposing, neutral, observer
- exposure_round = 0 for agents in initial_exposed_agent_ids, else infer from cascade distance"""

        system_prompt = (
            "You are an expert in private organizational network dynamics. "
            "Return pure JSON only — no markdown. "
            "IMPORTANT: The 'stance' field MUST be one of: "
            "'supportive', 'opposing', 'neutral', 'observer'. "
            f"{get_language_instruction()}"
        )

        try:
            result = self._call_llm_with_retry(prompt, system_prompt)
            llm_map: Dict[int, Dict[str, Any]] = {
                cfg["agent_id"]: cfg for cfg in result.get("agent_configs", [])
            }
        except Exception as e:
            logger.warning(f"Agent config batch LLM failed: {e}. Using rule-based fallback.")
            llm_map = {}

        configs: List[RelationalActivityConfig] = []
        for i, agent in enumerate(agent_profiles):
            agent_id = agent.get("agent_id", start_idx + i)
            rtype = agent.get("relational_link_type", "employee").lower()
            cfg = llm_map.get(agent_id)

            if not cfg:
                cfg = self._agent_config_by_rule(rtype)

            configs.append(RelationalActivityConfig(
                agent_id=agent_id,
                entity_uuid=agent.get("source_entity_uuid", ""),
                entity_name=agent.get("entity_name", ""),
                relational_link_type=rtype,
                activity_level=float(cfg.get("activity_level", 0.5)),
                response_delay_min=int(cfg.get("response_delay_min", 0)),
                response_delay_max=int(cfg.get("response_delay_max", 3)),
                sentiment_bias=float(cfg.get("sentiment_bias", 0.0)),
                stance=cfg.get("stance", "neutral"),
                influence_weight=float(cfg.get("influence_weight", 1.0)),
                cascade_influence=agent.get("cascade_influence", []),
                exposure_round=int(cfg.get("exposure_round", 0)),
            ))

        return configs

    def _agent_config_by_rule(self, relational_type: str) -> Dict[str, Any]:
        """
        Return rule-based activity config for a given relational type.

        Falls back to 'employee' defaults for unknown types.

        Args:
            relational_type: Lowercase relational type string.

        Returns:
            Dict with activity_level, response_delay_min/max, sentiment_bias,
            stance, influence_weight.
        """
        return dict(self.RELATIONAL_FALLBACKS.get(
            relational_type, self.RELATIONAL_FALLBACKS["employee"]
        ))

    # ── LLM helpers ───────────────────────────────────────────────────────────

    def _call_llm_with_retry(self, prompt: str, system_prompt: str) -> Dict[str, Any]:
        """
        Call the LLM with up to 3 retry attempts.

        Mirrors SimulationConfigGenerator._call_llm_with_retry with:
        - JSON response format enforced
        - Temperature annealing on each retry
        - Truncation repair via _fix_truncated_json

        Args:
            prompt: User prompt.
            system_prompt: System instructions.

        Returns:
            Parsed JSON dict.

        Raises:
            Exception: If all attempts fail.
        """
        import time

        max_attempts = 3
        last_error: Optional[Exception] = None

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

                if finish_reason == "length":
                    logger.warning(
                        f"LLM output truncated (attempt {attempt + 1}), attempting repair..."
                    )
                    content = self._fix_truncated_json(content)

                try:
                    return json.loads(content)
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON parse failed (attempt {attempt + 1}): {str(e)[:80]}")
                    fixed = self._try_fix_config_json(content)
                    if fixed:
                        return fixed
                    last_error = e

            except Exception as e:
                logger.warning(f"LLM call failed (attempt {attempt + 1}): {str(e)[:80]}")
                last_error = e
                time.sleep(2 * (attempt + 1))

        raise last_error or Exception("LLM call failed after all retries")

    def _fix_truncated_json(self, content: str) -> str:
        """Repair truncated JSON by closing unclosed brackets and strings."""
        content = content.strip()
        open_braces = content.count("{") - content.count("}")
        open_brackets = content.count("[") - content.count("]")

        if content and content[-1] not in '",}]':
            content += '"'

        content += "]" * open_brackets
        content += "}" * open_braces
        return content

    def _try_fix_config_json(self, content: str) -> Optional[Dict[str, Any]]:
        """Attempt to extract and repair a JSON object from malformed LLM output."""
        import re

        content = self._fix_truncated_json(content)
        json_match = re.search(r"\{[\s\S]*\}", content)
        if not json_match:
            return None

        json_str = json_match.group()

        def fix_string(match: re.Match) -> str:
            s = match.group(0)
            s = s.replace("\n", " ").replace("\r", " ")
            s = re.sub(r"\s+", " ", s)
            return s

        json_str = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', fix_string, json_str)

        try:
            return json.loads(json_str)
        except Exception:
            json_str = re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", json_str)
            json_str = re.sub(r"\s+", " ", json_str)
            try:
                return json.loads(json_str)
            except Exception:
                return None

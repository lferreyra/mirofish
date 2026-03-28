"""
Agent class for the custom simulation engine.

Each agent has a persona and can decide actions via LLM calls.
Replaces the OASIS agent system.
"""

import json
import logging
import re
from typing import Dict, List, Optional, Tuple

from .actions import ActionType

logger = logging.getLogger(__name__)


class Agent:
    """
    A simulated social media agent with a persona.

    The agent can decide which action to take based on its persona,
    current observation (feed), and available actions, by calling an LLM.
    """

    def __init__(
        self,
        agent_id: int,
        persona: str,
        profile: Dict = None,
        user_id: int = None,
        name: str = None,
    ):
        """
        Initialize an agent.

        Args:
            agent_id: Unique integer identifier for this agent.
            persona: Full persona text describing the agent's personality,
                     background, interests, and behavior patterns.
            profile: Raw profile data dict (from CSV/JSON).
            user_id: Database user_id (defaults to agent_id).
            name: Display name for the agent.
        """
        self.agent_id = agent_id
        self.persona = persona
        self.profile = profile or {}
        self.user_id = user_id if user_id is not None else agent_id
        self.name = name or f"Agent_{agent_id}"

    async def decide_action(
        self,
        observation: str,
        available_actions: List[ActionType],
        llm_model,
        platform: str = "Twitter",
    ) -> Tuple[ActionType, Dict]:
        """
        Use the LLM to decide which action to take.

        Args:
            observation: Text summary of the current feed / state.
            available_actions: List of ActionType values the agent can choose.
            llm_model: An LLM model instance with an async generate() method.
            platform: Platform name for the prompt context.

        Returns:
            A tuple of (ActionType, args_dict).
        """
        actions_list = ", ".join(a.value for a in available_actions)

        system_prompt = self.persona

        user_prompt = (
            f"You are on {platform}. Here is your current feed:\n"
            f"{observation}\n\n"
            f"Available actions: {actions_list}\n\n"
            f"Based on your persona and the current feed, decide what action to take.\n"
            f"Respond with JSON only: {{\"action\": \"ACTION_TYPE\", \"args\": {{\"content\": \"...\", ...}}}}\n"
            f"If you choose do_nothing, respond: {{\"action\": \"do_nothing\", \"args\": {{}}}}\n"
            f"For create_post, include \"content\" in args.\n"
            f"For like_post, include \"post_id\" (integer) in args.\n"
            f"For repost, include \"post_id\" (integer) in args.\n"
            f"For follow, include \"user_id\" (integer) in args.\n"
            f"For quote_post, include \"post_id\" (integer) and \"content\" in args.\n"
            f"For create_comment, include \"post_id\" (integer) and \"content\" in args.\n"
            f"Respond with ONLY the JSON object, no other text."
        )

        response = await llm_model.generate(system_prompt, user_prompt)
        return self._parse_action_response(response, available_actions)

    def _parse_action_response(
        self,
        response: str,
        available_actions: List[ActionType],
    ) -> Tuple[ActionType, Dict]:
        """
        Parse the LLM response into an ActionType and args dict.

        Falls back to DO_NOTHING if parsing fails.
        """
        if not response:
            return ActionType.DO_NOTHING, {}

        # Try to extract JSON from the response
        try:
            # Strip markdown code fences if present
            cleaned = response.strip()
            cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
            cleaned = re.sub(r'\s*```$', '', cleaned)
            cleaned = cleaned.strip()

            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            # Try to find JSON object in the response
            match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if match:
                try:
                    parsed = json.loads(match.group())
                except json.JSONDecodeError:
                    logger.warning(
                        "Agent %d: failed to parse LLM response: %s",
                        self.agent_id,
                        response[:200],
                    )
                    return ActionType.DO_NOTHING, {}
            else:
                logger.warning(
                    "Agent %d: no JSON found in LLM response: %s",
                    self.agent_id,
                    response[:200],
                )
                return ActionType.DO_NOTHING, {}

        action_str = parsed.get("action", "do_nothing")
        args = parsed.get("args", {})

        # Match action string to ActionType
        try:
            action_type = ActionType(action_str)
        except ValueError:
            # Try case-insensitive match
            action_str_lower = action_str.lower()
            matched = False
            for at in available_actions:
                if at.value == action_str_lower:
                    action_type = at
                    matched = True
                    break
            if not matched:
                logger.warning(
                    "Agent %d: unknown action '%s', falling back to DO_NOTHING",
                    self.agent_id,
                    action_str,
                )
                return ActionType.DO_NOTHING, {}

        # Verify the action is in the available actions list
        if action_type not in available_actions and action_type != ActionType.DO_NOTHING:
            logger.warning(
                "Agent %d: action '%s' not in available actions, falling back to DO_NOTHING",
                self.agent_id,
                action_type.value,
            )
            return ActionType.DO_NOTHING, {}

        return action_type, args

    def __repr__(self):
        return f"Agent(id={self.agent_id}, name={self.name})"

    def __hash__(self):
        return hash(self.agent_id)

    def __eq__(self, other):
        if isinstance(other, Agent):
            return self.agent_id == other.agent_id
        return False

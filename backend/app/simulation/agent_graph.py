"""
AgentGraph factory for loading agent profiles from CSV or JSON files.

Replaces the OASIS generate_twitter_agent_graph and generate_reddit_agent_graph.
"""

import csv
import json
import logging
from typing import Dict, List, Optional, Tuple

from .actions import ActionType
from .agent import Agent

logger = logging.getLogger(__name__)


class AgentGraph:
    """
    Container for all agents in a simulation.

    Provides methods to load agents from profile files (CSV for Twitter,
    JSON for Reddit) and to retrieve agents by ID.
    """

    def __init__(self):
        self._agents: Dict[int, Agent] = {}

    def add_agent(self, agent: Agent):
        """Add an agent to the graph."""
        self._agents[agent.agent_id] = agent

    def get_agent(self, agent_id: int) -> Agent:
        """
        Get an agent by its ID.

        Args:
            agent_id: The agent's integer identifier.

        Returns:
            The Agent instance.

        Raises:
            KeyError: If the agent_id is not found.
        """
        if agent_id not in self._agents:
            raise KeyError(f"Agent {agent_id} not found in graph")
        return self._agents[agent_id]

    def get_agents(self) -> List[Tuple[int, Agent]]:
        """
        Get all agents as (agent_id, agent) pairs.

        Returns:
            List of (agent_id, Agent) tuples.
        """
        return list(self._agents.items())

    def agent_count(self) -> int:
        """Return the number of agents in the graph."""
        return len(self._agents)

    @classmethod
    def load_from_csv(
        cls,
        path: str,
        model=None,
        available_actions: List[ActionType] = None,
    ) -> "AgentGraph":
        """
        Load agents from a CSV file (Twitter profile format).

        The CSV is expected to have columns that may include:
        agent_id, name, persona/description/bio, and other profile fields.

        Args:
            path: Path to the CSV file.
            model: LLM model instance (stored for reference, not used here).
            available_actions: List of available action types (stored for reference).

        Returns:
            An AgentGraph populated with Agent instances.
        """
        graph = cls()

        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader):
                agent_id = int(row.get("agent_id", idx))
                name = row.get("name", row.get("user_name", f"Agent_{agent_id}"))

                # Build persona from available fields
                persona_parts = []
                for key in ["persona", "description", "bio", "profile"]:
                    if key in row and row[key]:
                        persona_parts.append(row[key])

                if not persona_parts:
                    # Use all non-ID fields as persona context
                    for k, v in row.items():
                        if k not in ("agent_id", "name", "user_name") and v:
                            persona_parts.append(f"{k}: {v}")

                persona = "\n".join(persona_parts) if persona_parts else f"You are {name}."

                agent = Agent(
                    agent_id=agent_id,
                    persona=persona,
                    profile=dict(row),
                    name=name,
                )
                graph.add_agent(agent)

        logger.info("Loaded %d agents from CSV: %s", graph.agent_count(), path)
        return graph

    @classmethod
    def load_from_json(
        cls,
        path: str,
        model=None,
        available_actions: List[ActionType] = None,
    ) -> "AgentGraph":
        """
        Load agents from a JSON file (Reddit profile format).

        The JSON is expected to be a list of agent profile objects.

        Args:
            path: Path to the JSON file.
            model: LLM model instance (stored for reference, not used here).
            available_actions: List of available action types (stored for reference).

        Returns:
            An AgentGraph populated with Agent instances.
        """
        graph = cls()

        with open(path, "r", encoding="utf-8") as f:
            profiles = json.load(f)

        if isinstance(profiles, dict):
            profiles = profiles.get("agents", profiles.get("profiles", [profiles]))

        for idx, profile in enumerate(profiles):
            agent_id = int(profile.get("agent_id", idx))
            name = profile.get("name", profile.get("user_name", f"Agent_{agent_id}"))

            # Build persona from available fields
            persona_parts = []
            for key in ["persona", "description", "bio", "profile"]:
                if key in profile and profile[key]:
                    persona_parts.append(str(profile[key]))

            if not persona_parts:
                for k, v in profile.items():
                    if k not in ("agent_id", "name", "user_name") and v:
                        persona_parts.append(f"{k}: {v}")

            persona = "\n".join(persona_parts) if persona_parts else f"You are {name}."

            agent = Agent(
                agent_id=agent_id,
                persona=persona,
                profile=profile,
                name=name,
            )
            graph.add_agent(agent)

        logger.info("Loaded %d agents from JSON: %s", graph.agent_count(), path)
        return graph


async def generate_twitter_agent_graph(
    profile_path: str,
    model=None,
    available_actions: List[ActionType] = None,
) -> AgentGraph:
    """
    Async factory function to create an AgentGraph for Twitter simulation.

    Drop-in replacement for oasis.generate_twitter_agent_graph().

    Args:
        profile_path: Path to the Twitter profiles CSV file.
        model: LLM model instance.
        available_actions: List of available ActionType values.

    Returns:
        An AgentGraph populated from the CSV.
    """
    return AgentGraph.load_from_csv(
        path=profile_path,
        model=model,
        available_actions=available_actions,
    )


async def generate_reddit_agent_graph(
    profile_path: str,
    model=None,
    available_actions: List[ActionType] = None,
) -> AgentGraph:
    """
    Async factory function to create an AgentGraph for Reddit simulation.

    Drop-in replacement for oasis.generate_reddit_agent_graph().

    Args:
        profile_path: Path to the Reddit profiles JSON file.
        model: LLM model instance.
        available_actions: List of available ActionType values.

    Returns:
        An AgentGraph populated from the JSON.
    """
    return AgentGraph.load_from_json(
        path=profile_path,
        model=model,
        available_actions=available_actions,
    )

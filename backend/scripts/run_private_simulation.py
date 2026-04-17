"""
Private Impact Simulation Script

Simulates the impact of a private decision in a closed relational network.
Unlike Twitter/Reddit OASIS simulations, this mode has no social media platform:
no echo chamber, no recency weight, no asyncio.gather() across two platforms.

Differences from run_parallel_simulation.py:
- No OASIS env / agent_graph (no Twitter, no Reddit, no PlatformConfig)
- Single relational simulation (no asyncio.gather parallel platforms)
- Relational actions: REACT_PRIVATELY, CONFRONT, COALITION_BUILD,
  SILENT_LEAVE, VOCAL_SUPPORT, DO_NOTHING
- Propagation via cascade_influence graph:
    distance 1 = direct exposure (initial_posts targets)
    distance 2 = cascade via cascade_influence of reacting agents
- Direct LLM calls via camel-ai ChatAgent (no OASIS action loop)
- Output: backend/scripts/private/actions.jsonl (same JSONL format)
- zep_graph_memory_updater.py reused as-is (platform="private")

Usage:
    python run_private_simulation.py --config simulation_config.json
    python run_private_simulation.py --config simulation_config.json --no-wait
    python run_private_simulation.py --config simulation_config.json --max-rounds 10

Log structure:
    sim_xxx/
    ├── private/
    │   └── actions.jsonl    # Relational network action log
    ├── simulation.log       # Main simulation process log
    └── run_state.json       # Run state (API polling)
"""

# ============================================================
# Windows UTF-8 fix — same as run_parallel_simulation.py
# ============================================================
import sys
import os

if sys.platform == 'win32':
    os.environ.setdefault('PYTHONUTF8', '1')
    os.environ.setdefault('PYTHONIOENCODING', 'utf-8')

    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

    import builtins
    _original_open = builtins.open

    def _utf8_open(file, mode='r', buffering=-1, encoding=None, errors=None,
                   newline=None, closefd=True, opener=None):
        """Wrap open() to default to UTF-8 for text mode — fixes third-party libs."""
        if encoding is None and 'b' not in mode:
            encoding = 'utf-8'
        return _original_open(file, mode, buffering, encoding, errors,
                              newline, closefd, opener)

    builtins.open = _utf8_open

import argparse
import asyncio
import json
import logging
import random
import signal
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

# ── Path setup (same as run_parallel_simulation.py) ──────────────────────────
_scripts_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.abspath(os.path.join(_scripts_dir, '..'))
_project_root = os.path.abspath(os.path.join(_backend_dir, '..'))
sys.path.insert(0, _scripts_dir)
sys.path.insert(0, _backend_dir)

from dotenv import load_dotenv
_env_file = os.path.join(_project_root, '.env')
if os.path.exists(_env_file):
    load_dotenv(_env_file)
    print(f"Loaded env config: {_env_file}")
else:
    _backend_env = os.path.join(_backend_dir, '.env')
    if os.path.exists(_backend_env):
        load_dotenv(_backend_env)
        print(f"Loaded env config: {_backend_env}")

# ── Logging helpers ───────────────────────────────────────────────────────────

class MaxTokensWarningFilter(logging.Filter):
    """Suppress camel-ai max_tokens warnings (intentionally not set)."""

    def filter(self, record: logging.LogRecord) -> bool:
        if "max_tokens" in record.getMessage() and "Invalid or missing" in record.getMessage():
            return False
        return True


logging.getLogger().addFilter(MaxTokensWarningFilter())

from action_logger import SimulationLogManager, PlatformActionLogger

try:
    from camel.models import ModelFactory
    from camel.types import ModelPlatformType
    from camel.messages import BaseMessage
    from camel.agents import ChatAgent
except ImportError as e:
    print(f"Error: missing dependency {e}")
    print("Please install: pip install camel-ai")
    sys.exit(1)

# Optional: Zep graph memory updater — same as run_parallel_simulation.py
try:
    from app.services.zep_graph_memory_updater import AgentActivity, ZepGraphMemoryUpdater
    _ZEP_AVAILABLE = True
except ImportError:
    _ZEP_AVAILABLE = False

# ── Global shutdown state ─────────────────────────────────────────────────────
_shutdown_event: Optional[asyncio.Event] = None
_cleanup_done: bool = False

# ── Relational actions — no social media vocabulary ───────────────────────────
# Divergence from run_parallel_simulation.py:
# TWITTER_ACTIONS / REDDIT_ACTIONS → PRIVATE_ACTIONS
PRIVATE_ACTIONS = [
    "REACT_PRIVATELY",   # Internal reaction — changes agent state, not visible externally
    "CONFRONT",          # Direct confrontation with the decision maker
    "COALITION_BUILD",   # Rallies other network agents to a shared reaction
    "SILENT_LEAVE",      # Progressive disengagement (resignation, client churn...)
    "VOCAL_SUPPORT",     # Public or private defense of the decision
    "DO_NOTHING",        # Indifference — absorbs without reacting
]

# IPC constants (same pattern as run_parallel_simulation.py)
IPC_COMMANDS_DIR = "ipc_commands"
IPC_RESPONSES_DIR = "ipc_responses"
ENV_STATUS_FILE = "env_status.json"


class CommandType:
    INTERVIEW = "interview"
    BATCH_INTERVIEW = "batch_interview"
    CLOSE_ENV = "close_env"


# ── Config / model helpers ────────────────────────────────────────────────────

def load_config(config_path: str) -> Dict[str, Any]:
    """Load simulation config JSON."""
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def create_model(config: Dict[str, Any]):
    """
    Create LLM model from environment variables.
    Same logic as run_parallel_simulation.py — no boost variant needed here
    (single simulation, no parallel platforms to distribute load).
    """
    llm_api_key = os.environ.get("LLM_API_KEY", "")
    llm_base_url = os.environ.get("LLM_BASE_URL", "")
    llm_model = os.environ.get("LLM_MODEL_NAME", "") or config.get("llm_model", "gpt-4o-mini")

    if llm_api_key:
        os.environ["OPENAI_API_KEY"] = llm_api_key

    if not os.environ.get("OPENAI_API_KEY"):
        raise ValueError("Missing API Key — set LLM_API_KEY in .env")

    if llm_base_url:
        os.environ["OPENAI_API_BASE_URL"] = llm_base_url

    print(f"[Private] model={llm_model}, base_url={llm_base_url[:40] if llm_base_url else 'default'}...")

    return ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=llm_model,
    )


def get_agent_names_from_config(config: Dict[str, Any]) -> Dict[int, str]:
    """Build agent_id → entity_name mapping from simulation_config."""
    agent_names = {}
    for cfg in config.get("agent_configs", []):
        agent_id = cfg.get("agent_id")
        if agent_id is not None:
            agent_names[agent_id] = cfg.get("entity_name", f"Agent_{agent_id}")
    return agent_names


# ── Relational graph ──────────────────────────────────────────────────────────

def build_relational_graph(agent_configs: List[Dict[str, Any]]) -> Dict[int, List[int]]:
    """
    Build the cascade influence graph from agent configs.

    Divergence from run_parallel_simulation.py:
    No OASIS platform graph — this is a relational influence graph where
    cascade_influence[agent_id] = [list of agent_ids this agent can expose].

    Returns:
        {agent_id: [influenced_agent_ids]}
    """
    graph: Dict[int, List[int]] = {}
    for cfg in agent_configs:
        agent_id = cfg.get("agent_id", 0)
        graph[agent_id] = cfg.get("cascade_influence", [])
    return graph


def get_initial_exposed_agents(config: Dict[str, Any]) -> Set[int]:
    """
    Return the full set of agent IDs — all agents are exposed to the decision
    at simulation start.

    Relational network propagation: in Private Impact mode, the decision
    circulates through the network (e.g. LinkedIn post) and all agents
    receive context from round 1. The LLM-generated initial_exposed_agent_ids
    is intentionally ignored — exposure is a structural parameter, not an
    LLM decision.
    """
    exposed: Set[int] = set()
    for cfg in config.get("agent_configs", []):
        agent_id = cfg.get("agent_id")
        if agent_id is not None:
            exposed.add(agent_id)
    return exposed


def get_decision_context(config: Dict[str, Any]) -> str:
    """
    Extract the triggering decision text from event_config.

    Supports two event_config formats:
    - PrivateImpactConfigGenerator: decision_statement (plain text)
    - OASIS initial_posts: content of the first post
    """
    event_config = config.get("event_config", {})

    # PrivateImpactConfigGenerator format
    decision_statement = event_config.get("decision_statement", "")
    if decision_statement:
        return decision_statement

    # OASIS initial_posts format
    posts = event_config.get("initial_posts", [])
    if posts:
        return posts[0].get("content", "A private decision has been made.")

    return "A private decision has been made."


# ── Active agent selection ────────────────────────────────────────────────────

def get_active_agents_for_round_private(
    agent_configs: List[Dict[str, Any]],
    exposed_agents: Set[int],
    current_hour: int,
    round_num: int,
    time_config: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Select active agents for this round.

    Divergence from run_parallel_simulation.py:
    Only exposed agents are eligible (relational propagation gate).
    Active hours and activity_level logic is preserved from the original.

    Args:
        agent_configs: Full list of agent configs.
        exposed_agents: Set of agent_ids who have received the decision.
        current_hour: Simulated hour (0-23).
        round_num: Current round number.
        time_config: Time configuration from simulation config.

    Returns:
        List of agent config dicts for agents that will act this round.
    """
    base_min = time_config.get("agents_per_hour_min", 3)
    base_max = time_config.get("agents_per_hour_max", 10)

    peak_hours = time_config.get("peak_hours", [9, 10, 11, 14, 15, 20, 21, 22])
    off_peak_hours = time_config.get("off_peak_hours", [0, 1, 2, 3, 4, 5])

    if current_hour in peak_hours:
        multiplier = time_config.get("peak_activity_multiplier", 1.5)
    elif current_hour in off_peak_hours:
        multiplier = time_config.get("off_peak_activity_multiplier", 0.3)
    else:
        multiplier = 1.0

    target_count = int(random.uniform(base_min, base_max) * multiplier)

    candidates = []
    for cfg in agent_configs:
        agent_id = cfg.get("agent_id", 0)

        # Only exposed agents can act (relational propagation gate)
        if agent_id not in exposed_agents:
            continue

        active_hours = cfg.get("active_hours", list(range(8, 23)))
        if current_hour not in active_hours:
            continue

        activity_level = cfg.get("activity_level", 0.5)
        if random.random() < activity_level:
            candidates.append(cfg)

    selected = random.sample(candidates, min(target_count, len(candidates))) if candidates else []
    return selected


# ── LLM agent decision ────────────────────────────────────────────────────────

async def get_agent_action(
    agent_config: Dict[str, Any],
    decision_context: str,
    network_summary: str,
    model: Any,
    round_num: int,
) -> Dict[str, Any]:
    """
    Query LLM for the agent's relational action in the current round.

    Divergence from run_parallel_simulation.py:
    No OASIS action loop — direct ChatAgent call.
    The persona field encodes all behavioral dimensions (relational link,
    trust level, financial sensitivity, reaction mode).
    LLM reads this context and adapts decisions naturally — same pattern
    as OASIS where persona is injected as-is into the system prompt.

    Args:
        agent_config: Agent configuration dict (must contain "persona").
        decision_context: The triggering decision text.
        network_summary: Recent network activity (last N rounds).
        model: camel-ai model instance.
        round_num: Current round number.

    Returns:
        {"action_type": str, "action_args": dict}
    """
    persona = agent_config.get("persona", "You are a member of a professional network.")
    entity_name = agent_config.get(
        "entity_name", f"Agent_{agent_config.get('agent_id', 0)}"
    )

    actions_list = "\n".join(f"- {a}" for a in PRIVATE_ACTIONS)
    system_content = (
        f"{persona}\n\n"
        f"Available actions (choose exactly one):\n{actions_list}\n\n"
        "Respond with valid JSON only, no markdown:\n"
        '{"action": "<ACTION>", "reasoning": "<brief explanation in 1-2 sentences>", '
        '"target_agents": [<agent_ids if COALITION_BUILD, else empty list>]}'
    )

    user_content = (
        f"Round {round_num}.\n\n"
        f"Triggering decision:\n{decision_context}\n\n"
        f"Recent network activity:\n{network_summary if network_summary else 'No prior activity.'}\n\n"
        "What do you do? Choose one action. Respond in JSON only."
    )

    def _sync_call() -> Dict[str, Any]:
        """Synchronous LLM call — wrapped in asyncio.to_thread to avoid blocking."""
        try:
            agent = ChatAgent(
                system_message=BaseMessage.make_assistant_message(
                    role_name=entity_name,
                    content=system_content,
                ),
                model=model,
            )
            response = agent.step(
                BaseMessage.make_user_message(
                    role_name="Facilitator",
                    content=user_content,
                )
            )
            text = response.msg.content.strip()

            # Strip markdown code fence if present
            if "```" in text:
                parts = text.split("```")
                text = parts[1] if len(parts) > 1 else parts[0]
                if text.startswith("json"):
                    text = text[4:].strip()

            data = json.loads(text)
            action_type = str(data.get("action", "DO_NOTHING")).upper()
            if action_type not in PRIVATE_ACTIONS:
                action_type = "DO_NOTHING"

            return {
                "action_type": action_type,
                "action_args": {
                    "reasoning": data.get("reasoning", ""),
                    "target_agents": data.get("target_agents", []),
                },
            }
        except Exception:
            return {"action_type": "DO_NOTHING", "action_args": {}}

    return await asyncio.to_thread(_sync_call)


# ── Private IPC handler ───────────────────────────────────────────────────────

class PrivateIPCHandler:
    """
    IPC command handler for the private impact simulation.

    Divergence from ParallelIPCHandler in run_parallel_simulation.py:
    Single simulation context (no twitter_env / reddit_env).
    Interview responses are generated via direct LLM call.
    """

    def __init__(
        self,
        simulation_dir: str,
        agent_configs: List[Dict[str, Any]],
        model: Any,
    ):
        self.simulation_dir = simulation_dir
        self.agent_configs = {cfg["agent_id"]: cfg for cfg in agent_configs}
        self.model = model

        self.commands_dir = os.path.join(simulation_dir, IPC_COMMANDS_DIR)
        self.responses_dir = os.path.join(simulation_dir, IPC_RESPONSES_DIR)
        self.status_file = os.path.join(simulation_dir, ENV_STATUS_FILE)

        os.makedirs(self.commands_dir, exist_ok=True)
        os.makedirs(self.responses_dir, exist_ok=True)

    def update_status(self, status: str) -> None:
        """Write current env status to disk."""
        with open(self.status_file, 'w', encoding='utf-8') as f:
            json.dump({
                "status": status,
                "platform": "private",
                "timestamp": datetime.now().isoformat(),
            }, f, ensure_ascii=False, indent=2)

    def poll_command(self) -> Optional[Dict[str, Any]]:
        """Poll for pending IPC commands."""
        if not os.path.exists(self.commands_dir):
            return None

        command_files = sorted(
            (os.path.join(self.commands_dir, fn), os.path.getmtime(os.path.join(self.commands_dir, fn)))
            for fn in os.listdir(self.commands_dir)
            if fn.endswith('.json')
        )

        for filepath, _ in command_files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                continue
        return None

    def send_response(
        self,
        command_id: str,
        status: str,
        result: Optional[Dict] = None,
        error: Optional[str] = None,
    ) -> None:
        """Write response file and delete the command file."""
        response = {
            "command_id": command_id,
            "status": status,
            "result": result,
            "error": error,
            "timestamp": datetime.now().isoformat(),
        }
        response_file = os.path.join(self.responses_dir, f"{command_id}.json")
        with open(response_file, 'w', encoding='utf-8') as f:
            json.dump(response, f, ensure_ascii=False, indent=2)

        command_file = os.path.join(self.commands_dir, f"{command_id}.json")
        try:
            os.remove(command_file)
        except OSError:
            pass

    async def handle_interview(
        self,
        command_id: str,
        agent_id: int,
        prompt: str,
    ) -> bool:
        """Interview an agent via direct LLM call."""
        cfg = self.agent_configs.get(agent_id)
        if not cfg:
            self.send_response(command_id, "failed", error=f"Agent {agent_id} not found")
            return False

        persona = cfg.get("persona", "")
        entity_name = cfg.get("entity_name", f"Agent_{agent_id}")

        def _sync_interview() -> str:
            agent = ChatAgent(
                system_message=BaseMessage.make_assistant_message(
                    role_name=entity_name,
                    content=persona,
                ),
                model=self.model,
            )
            response = agent.step(
                BaseMessage.make_user_message(role_name="Interviewer", content=prompt)
            )
            return response.msg.content

        try:
            answer = await asyncio.to_thread(_sync_interview)
            self.send_response(command_id, "completed", result={
                "agent_id": agent_id,
                "agent_name": entity_name,
                "platform": "private",
                "prompt": prompt,
                "response": answer,
                "timestamp": datetime.now().isoformat(),
            })
            print(f"  Interview done: agent_id={agent_id}")
            return True
        except Exception as e:
            self.send_response(command_id, "failed", error=str(e))
            return False

    async def handle_batch_interview(
        self,
        command_id: str,
        interviews: List[Dict[str, Any]],
    ) -> bool:
        """Batch interview multiple agents."""
        tasks = [
            self.handle_interview(
                f"{command_id}_{i}",
                item.get("agent_id", 0),
                item.get("prompt", ""),
            )
            for i, item in enumerate(interviews)
        ]
        results_flags = await asyncio.gather(*tasks)
        success_count = sum(results_flags)

        if success_count > 0:
            self.send_response(command_id, "completed", result={
                "interviews_count": success_count,
            })
            return True

        self.send_response(command_id, "failed", error="All interviews failed")
        return False

    async def process_commands(self) -> bool:
        """
        Process pending IPC commands.

        Returns:
            True to keep running, False to exit.
        """
        command = self.poll_command()
        if not command:
            return True

        command_id = command.get("command_id")
        command_type = command.get("command_type")
        args = command.get("args", {})

        print(f"\nIPC command received: {command_type}, id={command_id}")

        if command_type == CommandType.INTERVIEW:
            await self.handle_interview(
                command_id,
                args.get("agent_id", 0),
                args.get("prompt", ""),
            )
            return True

        if command_type == CommandType.BATCH_INTERVIEW:
            await self.handle_batch_interview(
                command_id,
                args.get("interviews", []),
            )
            return True

        if command_type == CommandType.CLOSE_ENV:
            print("Close env command received")
            self.send_response(command_id, "completed", result={"message": "Environment closing"})
            return False

        self.send_response(command_id, "failed", error=f"Unknown command: {command_type}")
        return True


# ── Main simulation coroutine ─────────────────────────────────────────────────

async def run_private_simulation(
    config: Dict[str, Any],
    simulation_dir: str,
    action_logger: Optional[PlatformActionLogger] = None,
    main_logger: Optional[SimulationLogManager] = None,
    max_rounds: Optional[int] = None,
    zep_updater: Optional[Any] = None,
) -> Tuple[int, List[Dict[str, Any]]]:
    """
    Run the private impact simulation.

    Divergence from run_twitter_simulation / run_reddit_simulation:
    - No OASIS env — direct LLM calls per agent per round
    - No PlatformConfig (no recency_weight, no echo_chamber)
    - Relational graph drives exposure propagation
    - REACT_PRIVATELY does NOT cascade (internal reaction, invisible)
    - All other non-DO_NOTHING actions cascade to cascade_influence targets

    Args:
        config: Simulation config dict.
        simulation_dir: Directory for log output.
        action_logger: PlatformActionLogger instance ("private" platform).
        main_logger: SimulationLogManager for main simulation.log.
        max_rounds: Optional round cap.
        zep_updater: Optional ZepGraphMemoryUpdater (reused as-is).

    Returns:
        (total_actions, agent_configs) — for IPC handler initialisation.
    """

    def log(msg: str) -> None:
        if main_logger:
            main_logger.info(f"[Private] {msg}")
        print(f"[Private] {msg}")

    log("Initializing...")

    agent_configs = config.get("agent_configs", [])
    agent_names = get_agent_names_from_config(config)
    time_config = config.get("time_config", {})

    # Build relational cascade graph
    relational_graph = build_relational_graph(agent_configs)

    # Agents exposed to the decision at simulation start (distance 1)
    exposed_agents: Set[int] = get_initial_exposed_agents(config)
    log(f"Distance-1 exposed agents: {sorted(exposed_agents)}")

    # The triggering decision text (from event_config.initial_posts)
    decision_context = get_decision_context(config)
    log(f"Decision context: {decision_context[:100]}...")

    model = create_model(config)

    if action_logger:
        action_logger.log_simulation_start(config)

    total_actions = 0

    # Round 0 — log the decision injection (mirrors initial_posts in OASIS)
    if action_logger:
        action_logger.log_round_start(0, 0)

    event_config = config.get("event_config", {})
    initial_posts = event_config.get("initial_posts", [])
    initial_count = 0

    for post in initial_posts:
        poster_id = post.get("poster_agent_id", 0)
        content = post.get("content", "")
        poster_name = agent_names.get(poster_id, f"Agent_{poster_id}")

        if action_logger:
            action_logger.log_action(
                round_num=0,
                agent_id=poster_id,
                agent_name=poster_name,
                action_type="CREATE_POST",
                action_args={"content": content},
            )
            total_actions += 1
            initial_count += 1

        if zep_updater and _ZEP_AVAILABLE:
            zep_updater.add_activity_from_dict({
                "agent_id": poster_id,
                "agent_name": poster_name,
                "action_type": "CREATE_POST",
                "action_args": {"content": content},
                "round": 0,
                "timestamp": datetime.now().isoformat(),
            }, platform="private")

    log(f"Decision injected: {initial_count} initial post(s)")

    if action_logger:
        action_logger.log_round_end(0, initial_count, simulated_day=1)

    # Compute total rounds — support both time config formats:
    # PrivateImpactConfigGenerator: total_simulation_days + rounds_per_day
    # OASIS format: total_simulation_hours + minutes_per_round
    if "total_simulation_days" in time_config:
        _days = int(time_config["total_simulation_days"])
        _rpd = int(time_config.get("rounds_per_day", 3))
        total_rounds = _days * _rpd
        minutes_per_round = (24 * 60) // _rpd if _rpd > 0 else 480
    else:
        total_hours = time_config.get("total_simulation_hours", 72)
        minutes_per_round = time_config.get("minutes_per_round", 30)
        total_rounds = (total_hours * 60) // minutes_per_round

    if max_rounds is not None and max_rounds > 0:
        original_rounds = total_rounds
        total_rounds = min(total_rounds, max_rounds)
        if total_rounds < original_rounds:
            log(f"Rounds capped: {original_rounds} → {total_rounds} (max_rounds={max_rounds})")

    # Rolling network activity log for LLM context (last 10 visible actions)
    network_log: List[str] = []

    start_time = datetime.now()

    for round_num in range(total_rounds):
        if _shutdown_event and _shutdown_event.is_set():
            log(f"Shutdown signal received, stopping at round {round_num + 1}")
            break

        simulated_minutes = round_num * minutes_per_round
        simulated_hour = (simulated_minutes // 60) % 24
        simulated_day = simulated_minutes // (60 * 24) + 1

        active_cfgs = get_active_agents_for_round_private(
            agent_configs, exposed_agents, simulated_hour, round_num, time_config
        )

        if action_logger:
            action_logger.log_round_start(round_num + 1, simulated_hour)

        if not active_cfgs:
            if action_logger:
                action_logger.log_round_end(round_num + 1, 0, simulated_day=simulated_day)
            continue

        # Build context summary for LLM prompts this round
        network_summary = "\n".join(network_log[-10:])

        # Query all active agents concurrently
        tasks = [
            get_agent_action(
                cfg, decision_context, network_summary, model, round_num + 1
            )
            for cfg in active_cfgs
        ]
        action_results = await asyncio.gather(*tasks)

        round_action_count = 0
        newly_exposed: Set[int] = set()

        for cfg, result in zip(active_cfgs, action_results):
            agent_id = cfg.get("agent_id", 0)
            agent_name = agent_names.get(agent_id, f"Agent_{agent_id}")
            action_type = result["action_type"]
            action_args = result["action_args"]

            if action_logger:
                action_logger.log_action(
                    round_num=round_num + 1,
                    agent_id=agent_id,
                    agent_name=agent_name,
                    action_type=action_type,
                    action_args=action_args,
                )
                total_actions += 1
                round_action_count += 1

            if zep_updater and _ZEP_AVAILABLE:
                zep_updater.add_activity_from_dict({
                    "agent_id": agent_id,
                    "agent_name": agent_name,
                    "action_type": action_type,
                    "action_args": action_args,
                    "round": round_num + 1,
                    "timestamp": datetime.now().isoformat(),
                }, platform="private")

            # Rolling network log — only visible actions update context
            if action_type not in ("DO_NOTHING",):
                reasoning = action_args.get("reasoning", "")
                entry = f"[Round {round_num + 1}] {agent_name}: {action_type}"
                if reasoning:
                    entry += f" — {reasoning[:80]}"
                network_log.append(entry)

            # Propagate exposure via cascade_influence.
            # REACT_PRIVATELY is invisible externally — does NOT cascade.
            # All other non-DO_NOTHING actions cascade to influenced agents.
            if action_type not in ("DO_NOTHING", "REACT_PRIVATELY"):
                for influenced_id in relational_graph.get(agent_id, []):
                    if influenced_id not in exposed_agents:
                        newly_exposed.add(influenced_id)
                        influenced_name = agent_names.get(influenced_id, f"Agent_{influenced_id}")
                        log(f"  → {influenced_name} exposed via {agent_name}'s {action_type}")

        # Expand exposed set with newly reached agents
        exposed_agents.update(newly_exposed)

        if action_logger:
            action_logger.log_round_end(round_num + 1, round_action_count, simulated_day=simulated_day)

        if (round_num + 1) % 20 == 0:
            progress = (round_num + 1) / total_rounds * 100
            log(
                f"Day {simulated_day}, {simulated_hour:02d}:00 "
                f"— Round {round_num + 1}/{total_rounds} ({progress:.1f}%) "
                f"| Exposed: {len(exposed_agents)}/{len(agent_configs)}"
            )

    if action_logger:
        action_logger.log_simulation_end(total_rounds, total_actions)

    elapsed = (datetime.now() - start_time).total_seconds()
    log(f"Simulation complete! Elapsed: {elapsed:.1f}s, Total actions: {total_actions}")

    return total_actions, agent_configs


# ── Entry point ───────────────────────────────────────────────────────────────

async def main() -> None:
    parser = argparse.ArgumentParser(description='Private Impact Simulation')
    parser.add_argument(
        '--config',
        type=str,
        required=True,
        help='Path to simulation_config.json',
    )
    parser.add_argument(
        '--max-rounds',
        type=int,
        default=None,
        help='Maximum number of simulation rounds (optional cap)',
    )
    parser.add_argument(
        '--no-wait',
        action='store_true',
        default=False,
        help='Close environment immediately after simulation (no IPC wait)',
    )

    args = parser.parse_args()

    global _shutdown_event
    _shutdown_event = asyncio.Event()

    if not os.path.exists(args.config):
        print(f"Error: config file not found: {args.config}")
        sys.exit(1)

    config = load_config(args.config)
    simulation_dir = os.path.dirname(args.config) or "."
    wait_for_commands = not args.no_wait

    # Suppress OASIS loggers (precaution if imported transitively)
    for logger_name in ("social.agent", "social.twitter", "social.rec", "oasis.env", "table"):
        lg = logging.getLogger(logger_name)
        lg.setLevel(logging.CRITICAL)
        lg.handlers.clear()
        lg.propagate = False

    log_manager = SimulationLogManager(simulation_dir)
    private_logger = log_manager.get_private_logger()

    log_manager.info("=" * 60)
    log_manager.info("Private Impact Simulation")
    log_manager.info(f"Config: {args.config}")
    log_manager.info(f"Simulation ID: {config.get('simulation_id', 'unknown')}")
    log_manager.info(f"Wait mode: {'enabled' if wait_for_commands else 'disabled'}")
    log_manager.info("=" * 60)

    time_config = config.get("time_config", {})
    if "total_simulation_days" in time_config:
        config_total_rounds = (
            int(time_config["total_simulation_days"])
            * int(time_config.get("rounds_per_day", 3))
        )
    else:
        total_hours = time_config.get("total_simulation_hours", 72)
        minutes_per_round = time_config.get("minutes_per_round", 30)
        config_total_rounds = (total_hours * 60) // minutes_per_round

    log_manager.info("Simulation parameters:")
    if "total_simulation_days" in time_config:
        log_manager.info(f"  - Total simulated duration: {time_config['total_simulation_days']} days")
        log_manager.info(f"  - Rounds per day: {time_config.get('rounds_per_day', 3)}")
    else:
        log_manager.info(f"  - Total simulated duration: {time_config.get('total_simulation_hours', 72)}h")
        log_manager.info(f"  - Minutes per round: {time_config.get('minutes_per_round', 30)}")
    log_manager.info(f"  - Config total rounds: {config_total_rounds}")
    if args.max_rounds:
        log_manager.info(f"  - Round cap: {args.max_rounds}")
    log_manager.info(f"  - Agent count: {len(config.get('agent_configs', []))}")
    log_manager.info("Log structure:")
    log_manager.info(f"  - Main log: simulation.log")
    log_manager.info(f"  - Private actions: private/actions.jsonl")
    log_manager.info("=" * 60)

    start_time = datetime.now()

    total_actions, agent_configs = await run_private_simulation(
        config=config,
        simulation_dir=simulation_dir,
        action_logger=private_logger,
        main_logger=log_manager,
        max_rounds=args.max_rounds,
    )

    total_elapsed = (datetime.now() - start_time).total_seconds()
    log_manager.info("=" * 60)
    log_manager.info(f"Simulation loop complete! Elapsed: {total_elapsed:.1f}s")

    if wait_for_commands:
        log_manager.info("")
        log_manager.info("=" * 60)
        log_manager.info("Waiting for commands — environment active")
        log_manager.info("Supported: interview, batch_interview, close_env")
        log_manager.info("=" * 60)

        model = create_model(config)
        ipc_handler = PrivateIPCHandler(
            simulation_dir=simulation_dir,
            agent_configs=agent_configs,
            model=model,
        )
        ipc_handler.update_status("alive")

        try:
            while not _shutdown_event.is_set():
                should_continue = await ipc_handler.process_commands()
                if not should_continue:
                    break
                try:
                    await asyncio.wait_for(_shutdown_event.wait(), timeout=0.5)
                    break
                except asyncio.TimeoutError:
                    pass
        except KeyboardInterrupt:
            print("\nInterrupt received")
        except asyncio.CancelledError:
            print("\nTask cancelled")
        except Exception as e:
            print(f"\nCommand processing error: {e}")

        log_manager.info("\nShutting down...")
        ipc_handler.update_status("stopped")

    log_manager.info("=" * 60)
    log_manager.info("All done!")
    log_manager.info(f"  - {os.path.join(simulation_dir, 'simulation.log')}")
    log_manager.info(f"  - {os.path.join(simulation_dir, 'private', 'actions.jsonl')}")
    log_manager.info("=" * 60)


def setup_signal_handlers() -> None:
    """
    Register SIGTERM/SIGINT handlers.
    Same pattern as run_parallel_simulation.py — sets _shutdown_event
    instead of calling sys.exit() directly to allow graceful cleanup.
    """
    def signal_handler(signum: int, frame: Any) -> None:
        global _cleanup_done
        sig_name = "SIGTERM" if signum == signal.SIGTERM else "SIGINT"
        print(f"\n{sig_name} received, shutting down...")

        if not _cleanup_done:
            _cleanup_done = True
            if _shutdown_event:
                _shutdown_event.set()
        else:
            print("Forced exit...")
            sys.exit(1)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)


if __name__ == "__main__":
    setup_signal_handlers()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram interrupted")
    except SystemExit:
        pass
    finally:
        try:
            from multiprocessing import resource_tracker
            resource_tracker._resource_tracker._stop()
        except Exception:
            pass
        print("Simulation process exited")

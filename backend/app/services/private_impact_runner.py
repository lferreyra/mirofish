"""
Private Impact Runner

Orchestrates the Private Impact simulation via subprocess, monitors
private/actions.jsonl for real-time state updates, and exposes the
interface used by the Flask /api/private-impact blueprint.

Equivalent of simulation_runner.py for the Private Impact mode.

Key differences from SimulationRunner:
- Single platform: "private" (no Twitter/Reddit split)
- Action log: {sim_dir}/private/actions.jsonl
- Config file: private_simulation_config.json
- Script: backend/scripts/run_private_simulation.py
- Time unit: simulated days (not hours)
- Cleanup removes private_simulation.db + private/ directory

Note on SimulationLogManager.get_private_logger():
    SimulationLogManager (backend/scripts/action_logger.py) does NOT currently
    expose get_private_logger(). run_private_simulation.py falls back directly
    to PlatformActionLogger("private", simulation_dir). This method must be added
    to action_logger.py in a future prompt — see CONTEXT.md.
"""

import json
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from ..utils.logger import get_logger
from ..utils.locale import get_locale, set_locale
from .zep_graph_memory_updater import ZepGraphMemoryManager

logger = get_logger('mirofish.private_impact_runner')

IS_WINDOWS = sys.platform == 'win32'


# ── Enums ─────────────────────────────────────────────────────────────────────

class PrivateRunnerStatus(str, Enum):
    """Run state of the Private Impact simulation subprocess."""
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    COMPLETED = "completed"
    FAILED = "failed"


# ── Dataclasses ───────────────────────────────────────────────────────────────

@dataclass
class PrivateAgentAction:
    """
    Single relational action record parsed from private/actions.jsonl.

    Equivalent of AgentAction for the private simulation mode.
    No platform split — all actions are platform="private".
    """
    round_num: int
    timestamp: str
    agent_id: int
    agent_name: str
    action_type: str        # REACT_PRIVATELY | CONFRONT | COALITION_BUILD |
                            # SILENT_LEAVE | VOCAL_SUPPORT | DO_NOTHING
    action_args: Dict[str, Any] = field(default_factory=dict)
    result: Optional[str] = None
    success: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "round_num": self.round_num,
            "timestamp": self.timestamp,
            "platform": "private",
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "action_type": self.action_type,
            "action_args": self.action_args,
            "result": self.result,
            "success": self.success,
        }


@dataclass
class PrivateSimulationRunState:
    """
    Real-time run state for a Private Impact simulation.

    Equivalent of SimulationRunState for the private mode.
    Uses private_* field names — no twitter_* / reddit_* split.
    """
    simulation_id: str
    runner_status: PrivateRunnerStatus = PrivateRunnerStatus.IDLE

    # Progress
    private_current_round: int = 0
    private_total_rounds: int = 0
    private_simulated_days: int = 0
    private_total_days: int = 0

    # Platform state (single: private)
    private_running: bool = False
    private_actions_count: int = 0
    private_completed: bool = False

    # Error
    private_error: Optional[str] = None

    # Recent actions for frontend live display
    recent_actions: List[PrivateAgentAction] = field(default_factory=list)
    max_recent_actions: int = 50

    # Timestamps
    started_at: Optional[str] = None
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None

    # Subprocess PID
    process_pid: Optional[int] = None

    def add_action(self, action: PrivateAgentAction) -> None:
        """Prepend action to recent_actions and increment actions counter."""
        self.recent_actions.insert(0, action)
        if len(self.recent_actions) > self.max_recent_actions:
            self.recent_actions = self.recent_actions[:self.max_recent_actions]
        self.private_actions_count += 1
        self.updated_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        total = max(self.private_total_rounds, 1)
        return {
            "simulation_id": self.simulation_id,
            "runner_status": self.runner_status.value,
            "private_current_round": self.private_current_round,
            "private_total_rounds": self.private_total_rounds,
            "private_simulated_days": self.private_simulated_days,
            "private_total_days": self.private_total_days,
            "progress_percent": round(self.private_current_round / total * 100, 1),
            "private_running": self.private_running,
            "private_actions_count": self.private_actions_count,
            "private_completed": self.private_completed,
            "private_error": self.private_error,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "process_pid": self.process_pid,
        }

    def to_detail_dict(self) -> Dict[str, Any]:
        """Extended dict including recent actions."""
        result = self.to_dict()
        result["recent_actions"] = [a.to_dict() for a in self.recent_actions]
        return result


# ── PrivateImpactRunner ────────────────────────────────────────────────────────

class PrivateImpactRunner:
    """
    Orchestrates Private Impact simulations.

    Equivalent of SimulationRunner for the private relational mode.
    Launches run_private_simulation.py as a subprocess, monitors
    private/actions.jsonl for state updates, and exposes the interface
    consumed by the Flask /api/private-impact blueprint.

    Directory layout (under RUN_STATE_DIR/{simulation_id}/):
        private_simulation_config.json  — PrivateSimulationParameters.to_dict()
        private/actions.jsonl           — relational action log
        simulation.log                  — subprocess stdout + stderr
        run_state.json                  — persisted PrivateSimulationRunState
    """

    RUN_STATE_DIR = os.path.join(
        os.path.dirname(__file__),
        '../../uploads/simulations'
    )
    SCRIPTS_DIR = os.path.join(
        os.path.dirname(__file__),
        '../../scripts'
    )

    CONFIG_FILENAME = "private_simulation_config.json"
    SCRIPT_NAME = "run_private_simulation.py"

    # Class-level in-memory state (same pattern as SimulationRunner)
    _run_states: Dict[str, PrivateSimulationRunState] = {}
    _processes: Dict[str, subprocess.Popen] = {}
    _monitor_threads: Dict[str, threading.Thread] = {}
    _stdout_files: Dict[str, Any] = {}
    _graph_memory_enabled: Dict[str, bool] = {}

    # ── Public API ─────────────────────────────────────────────────────────────

    @classmethod
    def get_status(cls, simulation_id: str) -> Optional[PrivateSimulationRunState]:
        """
        Return the current run state for a simulation.

        Checks in-memory cache first, then falls back to disk
        (same pattern as SimulationRunner.get_run_state).

        Args:
            simulation_id: Simulation identifier.

        Returns:
            PrivateSimulationRunState or None if not found.
        """
        if simulation_id in cls._run_states:
            return cls._run_states[simulation_id]
        return cls._load_run_state(simulation_id)

    @classmethod
    def start_simulation(
        cls,
        simulation_id: str,
        max_rounds: Optional[int] = None,
        enable_graph_memory_update: bool = False,
        graph_id: Optional[str] = None,
    ) -> PrivateSimulationRunState:
        """
        Launch the private impact simulation subprocess.

        Same mechanics as SimulationRunner.start_simulation (L.387–399):
        - Reads private_simulation_config.json from the simulation directory
        - Spawns run_private_simulation.py with start_new_session=True
        - Redirects stdout/stderr to simulation.log
        - Launches a background monitor thread

        Args:
            simulation_id: Unique simulation identifier.
            max_rounds: Optional upper bound on simulation rounds.
            enable_graph_memory_update: Push activity updates to Zep graph.
            graph_id: Required when enable_graph_memory_update=True.

        Returns:
            PrivateSimulationRunState with status=STARTING.

        Raises:
            ValueError: If already running, config missing, or graph_id absent.
        """
        existing = cls.get_status(simulation_id)
        if existing and existing.runner_status in (
            PrivateRunnerStatus.RUNNING, PrivateRunnerStatus.STARTING
        ):
            raise ValueError(f"Private simulation already running: {simulation_id}")

        sim_dir = os.path.join(cls.RUN_STATE_DIR, simulation_id)
        config_path = os.path.join(sim_dir, cls.CONFIG_FILENAME)

        if not os.path.exists(config_path):
            raise ValueError(
                f"Private simulation config not found: {config_path}. "
                "Call /prepare first to generate the config."
            )

        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        time_cfg = config.get("time_config", {})
        total_days = time_cfg.get("total_simulation_days", 30)
        rounds_per_day = time_cfg.get("rounds_per_day", 3)
        total_rounds = total_days * rounds_per_day

        if max_rounds is not None and max_rounds > 0:
            total_rounds = min(total_rounds, max_rounds)
            logger.info(
                f"[PRIVATE] Rounds capped to {total_rounds} "
                f"(max_rounds={max_rounds})"
            )

        state = PrivateSimulationRunState(
            simulation_id=simulation_id,
            runner_status=PrivateRunnerStatus.STARTING,
            private_total_rounds=total_rounds,
            private_total_days=total_days,
            private_running=True,
            started_at=datetime.now().isoformat(),
        )
        cls._save_run_state(state)

        # Optional Zep graph memory update
        if enable_graph_memory_update:
            if not graph_id:
                raise ValueError(
                    "graph_id is required when enable_graph_memory_update=True"
                )
            try:
                ZepGraphMemoryManager.create_updater(simulation_id, graph_id)
                cls._graph_memory_enabled[simulation_id] = True
                logger.info(
                    f"[PRIVATE] Graph memory update enabled: "
                    f"simulation_id={simulation_id}, graph_id={graph_id}"
                )
            except Exception as e:
                logger.error(f"[PRIVATE] Failed to create graph memory updater: {e}")
                cls._graph_memory_enabled[simulation_id] = False
        else:
            cls._graph_memory_enabled[simulation_id] = False

        script_path = os.path.join(cls.SCRIPTS_DIR, cls.SCRIPT_NAME)
        if not os.path.exists(script_path):
            raise ValueError(f"Script not found: {script_path}")

        try:
            cmd = [sys.executable, script_path, "--config", config_path]
            if max_rounds is not None and max_rounds > 0:
                cmd.extend(["--max-rounds", str(max_rounds)])

            main_log_path = os.path.join(sim_dir, "simulation.log")
            main_log_file = open(main_log_path, 'w', encoding='utf-8')

            env = os.environ.copy()
            env['PYTHONUTF8'] = '1'
            env['PYTHONIOENCODING'] = 'utf-8'

            process = subprocess.Popen(
                cmd,
                cwd=sim_dir,
                stdout=main_log_file,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                bufsize=1,
                env=env,
                start_new_session=True,
            )

            cls._stdout_files[simulation_id] = main_log_file
            state.process_pid = process.pid
            state.runner_status = PrivateRunnerStatus.RUNNING
            cls._processes[simulation_id] = process
            cls._save_run_state(state)

            current_locale = get_locale()
            monitor_thread = threading.Thread(
                target=cls._monitor_simulation,
                args=(simulation_id, current_locale),
                daemon=True,
            )
            monitor_thread.start()
            cls._monitor_threads[simulation_id] = monitor_thread

            logger.info(
                f"[PRIVATE] Simulation started: {simulation_id}, "
                f"pid={process.pid}, total_rounds={total_rounds}, "
                f"total_days={total_days}"
            )

        except Exception as e:
            state.runner_status = PrivateRunnerStatus.FAILED
            state.private_error = str(e)
            state.private_running = False
            cls._save_run_state(state)
            raise

        return state

    @classmethod
    def stop_simulation(cls, simulation_id: str) -> PrivateSimulationRunState:
        """
        Stop a running private simulation with a clean SIGTERM.

        Same mechanics as SimulationRunner.stop_simulation.

        Args:
            simulation_id: Simulation identifier.

        Returns:
            Updated PrivateSimulationRunState with status=STOPPED.

        Raises:
            ValueError: If simulation does not exist or is not running.
        """
        state = cls.get_status(simulation_id)
        if not state:
            raise ValueError(f"Private simulation not found: {simulation_id}")
        if state.runner_status not in (
            PrivateRunnerStatus.RUNNING, PrivateRunnerStatus.STARTING
        ):
            raise ValueError(
                f"Private simulation is not running: "
                f"{simulation_id}, status={state.runner_status}"
            )

        state.runner_status = PrivateRunnerStatus.STOPPING
        cls._save_run_state(state)

        process = cls._processes.get(simulation_id)
        if process and process.poll() is None:
            try:
                cls._terminate_process(process, simulation_id)
            except ProcessLookupError:
                pass
            except Exception as e:
                logger.error(f"[PRIVATE] Terminate failed: {simulation_id}, {e}")
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except Exception:
                    process.kill()

        state.runner_status = PrivateRunnerStatus.STOPPED
        state.private_running = False
        state.completed_at = datetime.now().isoformat()
        cls._save_run_state(state)

        if cls._graph_memory_enabled.get(simulation_id, False):
            try:
                ZepGraphMemoryManager.stop_updater(simulation_id)
            except Exception as e:
                logger.error(f"[PRIVATE] Failed to stop graph updater: {e}")
            cls._graph_memory_enabled.pop(simulation_id, None)

        logger.info(f"[PRIVATE] Simulation stopped: {simulation_id}")
        return state

    @classmethod
    def get_all_actions(
        cls,
        simulation_id: str,
        agent_id: Optional[int] = None,
        round_num: Optional[int] = None,
    ) -> List[PrivateAgentAction]:
        """
        Read the complete private/actions.jsonl action history.

        Args:
            simulation_id: Simulation identifier.
            agent_id: Optional filter by agent ID.
            round_num: Optional filter by round number.

        Returns:
            List of PrivateAgentAction sorted by timestamp descending.
        """
        sim_dir = os.path.join(cls.RUN_STATE_DIR, simulation_id)
        log_path = os.path.join(sim_dir, "private", "actions.jsonl")
        actions = cls._read_actions_from_file(
            log_path, agent_id=agent_id, round_num=round_num
        )
        actions.sort(key=lambda a: a.timestamp, reverse=True)
        return actions

    @classmethod
    def cleanup(cls, simulation_id: str) -> Dict[str, Any]:
        """
        Remove private simulation artifacts to allow a fresh restart.

        Deletes:
        - run_state.json
        - simulation.log
        - private_simulation.db
        - private/ directory (contains actions.jsonl)

        Does NOT delete: private_simulation_config.json, profile files.

        Args:
            simulation_id: Simulation identifier.

        Returns:
            Dict with keys: success (bool), cleaned_files (list), errors (list|None).
        """
        sim_dir = os.path.join(cls.RUN_STATE_DIR, simulation_id)
        if not os.path.exists(sim_dir):
            return {"success": True, "cleaned_files": [], "errors": None}

        cleaned: List[str] = []
        errors: List[str] = []

        for filename in ("run_state.json", "simulation.log", "private_simulation.db"):
            path = os.path.join(sim_dir, filename)
            if os.path.exists(path):
                try:
                    os.remove(path)
                    cleaned.append(filename)
                except Exception as e:
                    errors.append(f"Failed to delete {filename}: {e}")

        private_dir = os.path.join(sim_dir, "private")
        if os.path.exists(private_dir):
            try:
                shutil.rmtree(private_dir)
                cleaned.append("private/")
            except Exception as e:
                errors.append(f"Failed to delete private/: {e}")

        cls._run_states.pop(simulation_id, None)

        logger.info(
            f"[PRIVATE] Cleanup done: {simulation_id}, removed={cleaned}"
        )
        return {
            "success": len(errors) == 0,
            "cleaned_files": cleaned,
            "errors": errors or None,
        }

    # ── Internal: monitor thread ───────────────────────────────────────────────

    @classmethod
    def _monitor_simulation(cls, simulation_id: str, locale: str = 'en') -> None:
        """
        Background thread: poll private/actions.jsonl until subprocess exits.

        Same pattern as SimulationRunner._monitor_simulation (L.482–581):
        - Loops while process is alive, reading new log lines every 2 s
        - Performs a final read after process exit
        - Sets COMPLETED or FAILED based on exit code
        - Stops graph memory updater in finally block

        Args:
            simulation_id: Simulation identifier.
            locale: Locale inherited from the calling thread.
        """
        set_locale(locale)
        sim_dir = os.path.join(cls.RUN_STATE_DIR, simulation_id)
        private_log = os.path.join(sim_dir, "private", "actions.jsonl")

        process = cls._processes.get(simulation_id)
        state = cls.get_status(simulation_id)

        if not process or not state:
            return

        log_position = 0

        try:
            while process.poll() is None:
                if os.path.exists(private_log):
                    log_position = cls._read_action_log(
                        private_log, log_position, state
                    )
                cls._save_run_state(state)
                time.sleep(2)

            # Final read after process exits
            if os.path.exists(private_log):
                cls._read_action_log(private_log, log_position, state)

            exit_code = process.returncode
            if exit_code == 0:
                state.runner_status = PrivateRunnerStatus.COMPLETED
                state.completed_at = datetime.now().isoformat()
                logger.info(f"[PRIVATE] Simulation completed: {simulation_id}")
            else:
                state.runner_status = PrivateRunnerStatus.FAILED
                main_log = os.path.join(sim_dir, "simulation.log")
                error_tail = ""
                try:
                    if os.path.exists(main_log):
                        with open(main_log, 'r', encoding='utf-8') as f:
                            error_tail = f.read()[-2000:]
                except Exception:
                    pass
                state.private_error = (
                    f"Process exited with code {exit_code}. "
                    f"Last log output: {error_tail}"
                )
                logger.error(
                    f"[PRIVATE] Simulation failed: {simulation_id}, "
                    f"exit_code={exit_code}"
                )

            state.private_running = False
            cls._save_run_state(state)

        except Exception as e:
            logger.error(f"[PRIVATE] Monitor thread error: {simulation_id}, {e}")
            state.runner_status = PrivateRunnerStatus.FAILED
            state.private_error = str(e)
            cls._save_run_state(state)

        finally:
            if cls._graph_memory_enabled.get(simulation_id, False):
                try:
                    ZepGraphMemoryManager.stop_updater(simulation_id)
                    logger.info(
                        f"[PRIVATE] Graph memory updater stopped: {simulation_id}"
                    )
                except Exception as e:
                    logger.error(
                        f"[PRIVATE] Failed to stop graph updater: {e}"
                    )
                cls._graph_memory_enabled.pop(simulation_id, None)

            cls._processes.pop(simulation_id, None)

            if simulation_id in cls._stdout_files:
                try:
                    cls._stdout_files[simulation_id].close()
                except Exception:
                    pass
                cls._stdout_files.pop(simulation_id, None)

    # ── Internal: log reader ───────────────────────────────────────────────────

    @classmethod
    def _read_action_log(
        cls,
        log_path: str,
        position: int,
        state: PrivateSimulationRunState,
    ) -> int:
        """
        Incremental read of private/actions.jsonl from a byte offset.

        Same pattern as SimulationRunner._read_action_log (L.683–684):
        - Seeks to last read position, reads new lines only
        - Calls ZepGraphMemoryUpdater.add_activity_from_dict(data, "private")
        - Handles round_end and simulation_end event entries

        Args:
            log_path: Absolute path to private/actions.jsonl.
            position: Byte offset of the previous read.
            state: Mutable run state to update in place.

        Returns:
            New byte offset after reading.
        """
        graph_memory_enabled = cls._graph_memory_enabled.get(
            state.simulation_id, False
        )
        graph_updater = None
        if graph_memory_enabled:
            graph_updater = ZepGraphMemoryManager.get_updater(state.simulation_id)

        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                f.seek(position)
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)

                        # Structured event entries (no agent_id)
                        if "event_type" in data:
                            event_type = data["event_type"]

                            if event_type == "simulation_end":
                                state.private_completed = True
                                state.private_running = False
                                state.runner_status = PrivateRunnerStatus.COMPLETED
                                state.completed_at = datetime.now().isoformat()
                                logger.info(
                                    f"[PRIVATE] simulation_end received: "
                                    f"{state.simulation_id}, "
                                    f"total_rounds={data.get('total_rounds')}, "
                                    f"total_actions={data.get('total_actions')}"
                                )

                            elif event_type == "round_end":
                                round_num = data.get("round", 0)
                                if round_num > state.private_current_round:
                                    state.private_current_round = round_num
                                # simulated_day may be written by run_private_simulation.py
                                simulated_day = data.get("simulated_day", 0)
                                if simulated_day > state.private_simulated_days:
                                    state.private_simulated_days = simulated_day

                            continue

                        # Skip non-agent entries
                        if "agent_id" not in data:
                            continue

                        action = PrivateAgentAction(
                            round_num=data.get("round", 0),
                            timestamp=data.get(
                                "timestamp", datetime.now().isoformat()
                            ),
                            agent_id=data.get("agent_id", 0),
                            agent_name=data.get("agent_name", ""),
                            action_type=data.get("action_type", ""),
                            action_args=data.get("action_args", {}),
                            result=data.get("result"),
                            success=data.get("success", True),
                        )
                        state.add_action(action)

                        if action.round_num > state.private_current_round:
                            state.private_current_round = action.round_num

                        # Push to Zep graph memory with platform="private"
                        if graph_updater:
                            graph_updater.add_activity_from_dict(data, "private")

                    except json.JSONDecodeError:
                        pass
                return f.tell()

        except Exception as e:
            logger.warning(
                f"[PRIVATE] Failed to read action log: {log_path}, {e}"
            )
            return position

    # ── Internal: persistence ─────────────────────────────────────────────────

    @classmethod
    def _save_run_state(cls, state: PrivateSimulationRunState) -> None:
        """Persist run state to run_state.json and update in-memory cache."""
        sim_dir = os.path.join(cls.RUN_STATE_DIR, state.simulation_id)
        os.makedirs(sim_dir, exist_ok=True)
        state_file = os.path.join(sim_dir, "run_state.json")
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state.to_detail_dict(), f, ensure_ascii=False, indent=2)
        cls._run_states[state.simulation_id] = state

    @classmethod
    def _load_run_state(
        cls, simulation_id: str
    ) -> Optional[PrivateSimulationRunState]:
        """
        Load run state from disk.

        Same pattern as SimulationRunner._load_run_state.

        Args:
            simulation_id: Simulation identifier.

        Returns:
            PrivateSimulationRunState or None on failure / missing file.
        """
        state_file = os.path.join(
            cls.RUN_STATE_DIR, simulation_id, "run_state.json"
        )
        if not os.path.exists(state_file):
            return None

        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            state = PrivateSimulationRunState(
                simulation_id=simulation_id,
                runner_status=PrivateRunnerStatus(
                    data.get("runner_status", "idle")
                ),
                private_current_round=data.get("private_current_round", 0),
                private_total_rounds=data.get("private_total_rounds", 0),
                private_simulated_days=data.get("private_simulated_days", 0),
                private_total_days=data.get("private_total_days", 0),
                private_running=data.get("private_running", False),
                private_actions_count=data.get("private_actions_count", 0),
                private_completed=data.get("private_completed", False),
                private_error=data.get("private_error"),
                started_at=data.get("started_at"),
                updated_at=data.get("updated_at", datetime.now().isoformat()),
                completed_at=data.get("completed_at"),
                process_pid=data.get("process_pid"),
            )

            for a in data.get("recent_actions", []):
                state.recent_actions.append(PrivateAgentAction(
                    round_num=a.get("round_num", 0),
                    timestamp=a.get("timestamp", ""),
                    agent_id=a.get("agent_id", 0),
                    agent_name=a.get("agent_name", ""),
                    action_type=a.get("action_type", ""),
                    action_args=a.get("action_args", {}),
                    result=a.get("result"),
                    success=a.get("success", True),
                ))

            cls._run_states[simulation_id] = state
            return state

        except Exception as e:
            logger.error(
                f"[PRIVATE] Failed to load run state: {simulation_id}, {e}"
            )
            return None

    @classmethod
    def _read_actions_from_file(
        cls,
        file_path: str,
        agent_id: Optional[int] = None,
        round_num: Optional[int] = None,
    ) -> List[PrivateAgentAction]:
        """
        Read all agent actions from a JSONL file with optional filters.

        Args:
            file_path: Path to actions.jsonl.
            agent_id: Optional filter by agent ID.
            round_num: Optional filter by round number.

        Returns:
            List of PrivateAgentAction instances.
        """
        if not os.path.exists(file_path):
            return []

        actions: List[PrivateAgentAction] = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if "event_type" in data:
                        continue
                    if "agent_id" not in data:
                        continue
                    if agent_id is not None and data.get("agent_id") != agent_id:
                        continue
                    if round_num is not None and data.get("round") != round_num:
                        continue
                    actions.append(PrivateAgentAction(
                        round_num=data.get("round", 0),
                        timestamp=data.get("timestamp", ""),
                        agent_id=data.get("agent_id", 0),
                        agent_name=data.get("agent_name", ""),
                        action_type=data.get("action_type", ""),
                        action_args=data.get("action_args", {}),
                        result=data.get("result"),
                        success=data.get("success", True),
                    ))
                except json.JSONDecodeError:
                    continue

        return actions

    # ── Internal: process management ──────────────────────────────────────────

    @classmethod
    def _terminate_process(
        cls,
        process: subprocess.Popen,
        simulation_id: str,
        timeout: int = 10,
    ) -> None:
        """
        Terminate subprocess and its children cross-platform.

        Same implementation as SimulationRunner._terminate_process:
        - Windows: taskkill /PID /T, then /F if unresponsive
        - Unix: SIGTERM to process group, SIGKILL on timeout

        Args:
            process: Subprocess to terminate.
            simulation_id: Simulation ID for logging.
            timeout: Seconds to wait before force-killing.
        """
        if IS_WINDOWS:
            logger.info(
                f"[PRIVATE] Terminating process tree (Windows): "
                f"simulation={simulation_id}, pid={process.pid}"
            )
            try:
                subprocess.run(
                    ['taskkill', '/PID', str(process.pid), '/T'],
                    capture_output=True, timeout=5
                )
                try:
                    process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    logger.warning(
                        f"[PRIVATE] Process unresponsive, force killing: "
                        f"{simulation_id}"
                    )
                    subprocess.run(
                        ['taskkill', '/F', '/PID', str(process.pid), '/T'],
                        capture_output=True, timeout=5
                    )
                    process.wait(timeout=5)
            except Exception as e:
                logger.warning(f"[PRIVATE] taskkill failed, falling back: {e}")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
        else:
            pgid = os.getpgid(process.pid)
            logger.info(
                f"[PRIVATE] Terminating process group (Unix): "
                f"simulation={simulation_id}, pgid={pgid}"
            )
            os.killpg(pgid, signal.SIGTERM)
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                logger.warning(
                    f"[PRIVATE] Process group unresponsive, force killing: "
                    f"{simulation_id}"
                )
                os.killpg(pgid, signal.SIGKILL)
                process.wait(timeout=5)

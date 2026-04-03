"""Tests for SimulationRunner._read_action_log partial-line safety.

Verifies that the monitor thread never advances its file position past
an incomplete (non-newline-terminated) line, preventing permanent
action data loss when the writer process hasn't flushed a full line.

Bug scenario (before fix):
    1. Writer appends: '{"agent_id": 1, "action_type": "CRE'  (no \n yet)
    2. Reader iterates, gets partial line, json.loads fails (silently skipped)
    3. Reader returns f.tell() which is PAST the partial data
    4. Writer completes: 'ATE_POST", "round": 1}\n'
    5. Next poll starts mid-line, reads: 'ATE_POST", "round": 1}\n'
    6. json.loads fails again — the action is permanently lost

Fix: track safe_position (only advanced after complete lines with \n).
Partial lines are left for the next poll cycle.
"""

import json
import os
import tempfile
import threading
import time
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

# We test _read_action_log in isolation, so we only need the class and its
# data structures.  Patch out heavy dependencies that aren't needed.
import sys

# Import strategy: load simulation_runner.py via importlib with the parent
# package set to 'app.services' so relative imports resolve correctly.
# All dependencies are stubbed in sys.modules beforehand.
import types
import importlib
import importlib.util

backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')

def _stub(name: str, **attrs):
    """Install a stub module (as a package)."""
    m = types.ModuleType(name)
    m.__path__ = []  # make it a package
    m.__package__ = name
    for k, v in attrs.items():
        setattr(m, k, v)
    sys.modules[name] = m
    return m

# Build the stub hierarchy
_stub('app')
_config = _stub('app.config')
_config.Config = MagicMock()

_stub('app.utils')
_logger = _stub('app.utils.logger')
_logger.get_logger = MagicMock(return_value=MagicMock())
_locale = _stub('app.utils.locale')
_locale.get_locale = MagicMock(return_value='en')
_locale.set_locale = MagicMock()

_stub('app.services')
_zep = _stub('app.services.zep_graph_memory_updater')
_zep.ZepGraphMemoryManager = MagicMock()
_ipc = _stub('app.services.simulation_ipc')
_ipc.SimulationIPCClient = MagicMock()
_ipc.CommandType = MagicMock()
_ipc.IPCResponse = MagicMock()

# Load simulation_runner.py by file path, setting its package context so
# relative imports (from ..config, from .simulation_ipc, etc.) work.
_runner_path = os.path.join(backend_dir, 'app', 'services', 'simulation_runner.py')
_spec = importlib.util.spec_from_file_location(
    'app.services.simulation_runner',
    _runner_path,
    submodule_search_locations=[],
)
_mod = importlib.util.module_from_spec(_spec)
_mod.__package__ = 'app.services'
sys.modules['app.services.simulation_runner'] = _mod
_spec.loader.exec_module(_mod)

SimulationRunner = _mod.SimulationRunner
SimulationRunState = _mod.SimulationRunState
RunnerStatus = _mod.RunnerStatus


def _make_state(sim_id: str = "test_sim") -> SimulationRunState:
    return SimulationRunState(simulation_id=sim_id)


def _action_line(agent_id: int = 1, action_type: str = "CREATE_POST", round_num: int = 1) -> str:
    """Build a valid JSONL action line (with trailing newline)."""
    obj = {
        "agent_id": agent_id,
        "agent_name": f"Agent_{agent_id}",
        "action_type": action_type,
        "round": round_num,
        "timestamp": datetime.now().isoformat(),
        "action_args": {},
        "result": "ok",
        "success": True,
    }
    return json.dumps(obj, ensure_ascii=False) + "\n"


def _event_line(event_type: str = "round_end", round_num: int = 1, **extra) -> str:
    """Build a valid JSONL event line."""
    obj = {"event_type": event_type, "round": round_num, **extra}
    return json.dumps(obj, ensure_ascii=False) + "\n"


# -----------------------------------------------------------------------
# Core regression test: partial lines must not cause data loss
# -----------------------------------------------------------------------

class TestPartialLineDataLoss:
    """The main fix: partial (incomplete) lines must not advance the position."""

    def test_partial_line_not_consumed(self, tmp_path):
        """A line without trailing \\n must not advance the read position."""
        log_file = tmp_path / "actions.jsonl"

        # Write one complete line + one partial line (no \n)
        complete_line = _action_line(agent_id=1)
        partial_data = '{"agent_id": 2, "action_type": "LIKE_POS'

        log_file.write_text(complete_line + partial_data, encoding="utf-8")

        state = _make_state()
        new_pos = SimulationRunner._read_action_log(
            str(log_file), 0, state, "twitter"
        )

        # Only agent_id=1 should have been parsed
        assert state.twitter_actions_count == 1
        # Position should be right after the first complete line,
        # NOT at the end of the file (which includes the partial data)
        assert new_pos == len(complete_line.encode("utf-8"))

    def test_partial_line_recovered_on_next_poll(self, tmp_path):
        """After a partial line is skipped, the next poll reads it once complete."""
        log_file = tmp_path / "actions.jsonl"

        # First write: complete line + partial line
        line1 = _action_line(agent_id=1)
        partial = '{"agent_id": 2, "action_type": "LIKE_POST"'
        log_file.write_text(line1 + partial, encoding="utf-8")

        state = _make_state()
        pos = SimulationRunner._read_action_log(str(log_file), 0, state, "twitter")
        assert state.twitter_actions_count == 1  # only line1

        # Second write: complete the partial line
        remainder = ', "round": 1, "timestamp": "2026-01-01T00:00:00"}\n'
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(remainder)

        pos2 = SimulationRunner._read_action_log(str(log_file), pos, state, "twitter")
        assert state.twitter_actions_count == 2  # now both parsed
        assert pos2 > pos

    def test_multiple_partial_writes_no_loss(self, tmp_path):
        """Simulate realistic multi-write scenario with no data loss."""
        log_file = tmp_path / "actions.jsonl"
        log_file.write_text("", encoding="utf-8")

        state = _make_state()
        pos = 0

        # Write 3 complete actions
        with open(log_file, "a", encoding="utf-8") as f:
            for i in range(3):
                f.write(_action_line(agent_id=i, round_num=1))

        pos = SimulationRunner._read_action_log(str(log_file), pos, state, "twitter")
        assert state.twitter_actions_count == 3

        # Write a partial action (simulating mid-flush)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write('{"agent_id": 10, "action_type": "REPOST", "round": 2')

        pos = SimulationRunner._read_action_log(str(log_file), pos, state, "twitter")
        assert state.twitter_actions_count == 3  # no new action yet

        # Complete the action + add one more
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(', "timestamp": "2026-01-01"}\n')
            f.write(_action_line(agent_id=11, round_num=2))

        pos = SimulationRunner._read_action_log(str(log_file), pos, state, "twitter")
        assert state.twitter_actions_count == 5  # all 5 actions recovered


# -----------------------------------------------------------------------
# Basic functionality tests (must still work correctly)
# -----------------------------------------------------------------------

class TestBasicActionReading:
    """Verify basic action log reading still works after the fix."""

    def test_empty_file(self, tmp_path):
        """Empty file returns position 0."""
        log_file = tmp_path / "actions.jsonl"
        log_file.write_text("", encoding="utf-8")

        state = _make_state()
        pos = SimulationRunner._read_action_log(str(log_file), 0, state, "twitter")
        assert pos == 0
        assert state.twitter_actions_count == 0

    def test_single_complete_action(self, tmp_path):
        """Single complete action line is parsed correctly."""
        log_file = tmp_path / "actions.jsonl"
        line = _action_line(agent_id=42, action_type="LIKE_POST", round_num=3)
        log_file.write_text(line, encoding="utf-8")

        state = _make_state()
        pos = SimulationRunner._read_action_log(str(log_file), 0, state, "twitter")

        assert state.twitter_actions_count == 1
        assert state.recent_actions[0].agent_id == 42
        assert state.recent_actions[0].action_type == "LIKE_POST"
        assert state.current_round == 3
        assert pos == len(line.encode("utf-8"))

    def test_multiple_actions(self, tmp_path):
        """Multiple complete action lines are all parsed."""
        log_file = tmp_path / "actions.jsonl"
        lines = ""
        for i in range(5):
            lines += _action_line(agent_id=i, round_num=i + 1)
        log_file.write_text(lines, encoding="utf-8")

        state = _make_state()
        pos = SimulationRunner._read_action_log(str(log_file), 0, state, "twitter")

        assert state.twitter_actions_count == 5
        assert state.current_round == 5

    def test_event_lines_parsed(self, tmp_path):
        """Event lines (round_end, simulation_end) are handled correctly."""
        log_file = tmp_path / "actions.jsonl"
        content = (
            _event_line("round_end", round_num=3, simulated_hours=6)
            + _action_line(agent_id=1, round_num=3)
        )
        log_file.write_text(content, encoding="utf-8")

        state = _make_state()
        SimulationRunner._read_action_log(str(log_file), 0, state, "twitter")

        assert state.twitter_current_round == 3
        assert state.twitter_simulated_hours == 6
        assert state.twitter_actions_count == 1

    def test_simulation_end_event(self, tmp_path):
        """simulation_end event marks platform as completed."""
        log_file = tmp_path / "actions.jsonl"
        content = _event_line("simulation_end", total_rounds=10, total_actions=50)
        log_file.write_text(content, encoding="utf-8")

        state = _make_state()
        SimulationRunner._read_action_log(str(log_file), 0, state, "twitter")

        assert state.twitter_completed is True
        assert state.twitter_running is False

    def test_incremental_reading(self, tmp_path):
        """Incremental reads with position tracking work correctly."""
        log_file = tmp_path / "actions.jsonl"

        # Write first batch
        batch1 = _action_line(agent_id=1) + _action_line(agent_id=2)
        log_file.write_text(batch1, encoding="utf-8")

        state = _make_state()
        pos = SimulationRunner._read_action_log(str(log_file), 0, state, "twitter")
        assert state.twitter_actions_count == 2

        # Append second batch
        batch2 = _action_line(agent_id=3) + _action_line(agent_id=4)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(batch2)

        pos2 = SimulationRunner._read_action_log(str(log_file), pos, state, "twitter")
        assert state.twitter_actions_count == 4
        assert pos2 > pos


# -----------------------------------------------------------------------
# Edge cases
# -----------------------------------------------------------------------

class TestEdgeCases:
    """Edge cases and robustness tests."""

    def test_malformed_json_skipped(self, tmp_path):
        """Lines with invalid JSON are skipped without crashing."""
        log_file = tmp_path / "actions.jsonl"
        content = (
            "this is not json\n"
            + _action_line(agent_id=1)
            + "{broken json\n"
            + _action_line(agent_id=2)
        )
        log_file.write_text(content, encoding="utf-8")

        state = _make_state()
        SimulationRunner._read_action_log(str(log_file), 0, state, "twitter")

        assert state.twitter_actions_count == 2

    def test_blank_lines_skipped(self, tmp_path):
        """Blank lines don't cause issues."""
        log_file = tmp_path / "actions.jsonl"
        content = "\n\n" + _action_line(agent_id=1) + "\n\n" + _action_line(agent_id=2) + "\n"
        log_file.write_text(content, encoding="utf-8")

        state = _make_state()
        SimulationRunner._read_action_log(str(log_file), 0, state, "twitter")

        assert state.twitter_actions_count == 2

    def test_unicode_content(self, tmp_path):
        """Unicode content in action data is handled correctly."""
        log_file = tmp_path / "actions.jsonl"
        obj = {
            "agent_id": 1,
            "agent_name": "张三",
            "action_type": "CREATE_POST",
            "round": 1,
            "timestamp": "2026-01-01T00:00:00",
            "action_args": {"content": "这是一条中文测试 🎉"},
            "success": True,
        }
        log_file.write_text(json.dumps(obj, ensure_ascii=False) + "\n", encoding="utf-8")

        state = _make_state()
        SimulationRunner._read_action_log(str(log_file), 0, state, "twitter")

        assert state.twitter_actions_count == 1
        assert state.recent_actions[0].agent_name == "张三"

    def test_nonexistent_file(self, tmp_path):
        """Reading a nonexistent file returns the original position."""
        state = _make_state()
        pos = SimulationRunner._read_action_log(
            str(tmp_path / "nonexistent.jsonl"), 42, state, "twitter"
        )
        assert pos == 42
        assert state.twitter_actions_count == 0

    def test_reddit_platform(self, tmp_path):
        """Reddit platform actions are counted separately."""
        log_file = tmp_path / "actions.jsonl"
        log_file.write_text(
            _action_line(agent_id=1) + _action_line(agent_id=2),
            encoding="utf-8",
        )

        state = _make_state()
        SimulationRunner._read_action_log(str(log_file), 0, state, "reddit")

        assert state.reddit_actions_count == 2
        assert state.twitter_actions_count == 0

    def test_only_partial_line_no_advance(self, tmp_path):
        """File containing only a partial line doesn't advance position at all."""
        log_file = tmp_path / "actions.jsonl"
        log_file.write_text('{"agent_id": 1', encoding="utf-8")

        state = _make_state()
        pos = SimulationRunner._read_action_log(str(log_file), 0, state, "twitter")

        assert pos == 0
        assert state.twitter_actions_count == 0


# -----------------------------------------------------------------------
# Concurrent writer simulation
# -----------------------------------------------------------------------

class TestConcurrentWriter:
    """Simulate realistic concurrent writing scenarios."""

    def test_writer_mid_line_then_completes(self, tmp_path):
        """
        Simulate: writer writes half a line, reader polls, writer finishes.
        No data should be lost.
        """
        log_file = tmp_path / "actions.jsonl"

        # Pre-write some complete actions
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(_action_line(agent_id=0))

        state = _make_state()

        # Poll 1: read complete action
        pos = SimulationRunner._read_action_log(str(log_file), 0, state, "twitter")
        assert state.twitter_actions_count == 1

        # Writer starts a new line but doesn't finish
        with open(log_file, "a", encoding="utf-8") as f:
            f.write('{"agent_id": 99, "action_type": "FOLLOW"')
            f.flush()

        # Poll 2: should NOT consume the partial line
        pos = SimulationRunner._read_action_log(str(log_file), pos, state, "twitter")
        assert state.twitter_actions_count == 1  # unchanged

        # Writer finishes the line
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(', "round": 5, "timestamp": "2026-01-01"}\n')
            f.flush()

        # Poll 3: should now read the completed line
        pos = SimulationRunner._read_action_log(str(log_file), pos, state, "twitter")
        assert state.twitter_actions_count == 2
        assert state.recent_actions[0].agent_id == 99

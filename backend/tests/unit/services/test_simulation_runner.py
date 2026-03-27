"""Tests for simulation runner module"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from app.services.simulation_runner import (
    SimulationRunState,
    AgentAction,
    RoundSummary,
    RunnerStatus,
)


class TestAgentAction:
    """Test cases for AgentAction dataclass"""

    def test_agent_action_creation(self):
        """Test creating an AgentAction"""
        action = AgentAction(
            round_num=1,
            timestamp="2024-03-26T10:00:00",
            platform="twitter",
            agent_id=1,
            agent_name="Agent Smith",
            action_type="CREATE_POST",
            action_args={"content": "Test post"},
            result="Post created successfully",
            success=True
        )

        assert action.round_num == 1
        assert action.platform == "twitter"
        assert action.agent_id == 1
        assert action.action_type == "CREATE_POST"
        assert action.success is True

    def test_agent_action_to_dict(self):
        """Test converting AgentAction to dictionary"""
        action = AgentAction(
            round_num=2,
            timestamp="2024-03-26T11:00:00",
            platform="reddit",
            agent_id=2,
            agent_name="Bot Johnson",
            action_type="LIKE_POST",
            action_args={"post_id": "123"},
            result="Liked successfully",
            success=True
        )

        action_dict = action.to_dict()

        assert isinstance(action_dict, dict)
        assert action_dict["round_num"] == 2
        assert action_dict["platform"] == "reddit"
        assert action_dict["agent_name"] == "Bot Johnson"
        assert action_dict["action_type"] == "LIKE_POST"

    def test_agent_action_with_failure(self):
        """Test AgentAction with failed action"""
        action = AgentAction(
            round_num=1,
            timestamp="2024-03-26T10:00:00",
            platform="twitter",
            agent_id=1,
            agent_name="Agent Smith",
            action_type="DELETE_POST",
            action_args={"post_id": "invalid"},
            result="Post not found",
            success=False
        )

        assert action.success is False
        assert action.result == "Post not found"


class TestRoundSummary:
    """Test cases for RoundSummary dataclass"""

    def test_round_summary_creation(self):
        """Test creating a RoundSummary"""
        summary = RoundSummary(
            round_num=1,
            start_time="2024-03-26T10:00:00",
            simulated_hour=2,
            twitter_actions=5,
            reddit_actions=3,
            active_agents=[1, 2, 3]
        )

        assert summary.round_num == 1
        assert summary.simulated_hour == 2
        assert summary.twitter_actions == 5
        assert summary.reddit_actions == 3
        assert len(summary.active_agents) == 3

    def test_round_summary_to_dict(self):
        """Test converting RoundSummary to dictionary"""
        summary = RoundSummary(
            round_num=2,
            start_time="2024-03-26T11:00:00",
            end_time="2024-03-26T11:30:00",
            simulated_hour=3,
            twitter_actions=8,
            reddit_actions=6,
            active_agents=[1, 2, 3, 4]
        )

        summary_dict = summary.to_dict()

        assert isinstance(summary_dict, dict)
        assert summary_dict["round_num"] == 2
        assert summary_dict["twitter_actions"] == 8
        assert summary_dict["actions_count"] == 0  # No actions added yet

    def test_round_summary_with_actions(self):
        """Test RoundSummary with actions"""
        action1 = AgentAction(
            round_num=1,
            timestamp="2024-03-26T10:00:00",
            platform="twitter",
            agent_id=1,
            agent_name="Agent 1",
            action_type="CREATE_POST"
        )
        action2 = AgentAction(
            round_num=1,
            timestamp="2024-03-26T10:05:00",
            platform="reddit",
            agent_id=2,
            agent_name="Agent 2",
            action_type="COMMENT"
        )

        summary = RoundSummary(
            round_num=1,
            start_time="2024-03-26T10:00:00",
            simulated_hour=1,
            actions=[action1, action2]
        )

        summary_dict = summary.to_dict()
        assert summary_dict["actions_count"] == 2


class TestSimulationRunState:
    """Test cases for SimulationRunState dataclass"""

    def test_simulation_run_state_creation(self):
        """Test creating a SimulationRunState"""
        state = SimulationRunState(
            simulation_id="sim_123",
            runner_status=RunnerStatus.IDLE,
            total_rounds=10,
            total_simulation_hours=24
        )

        assert state.simulation_id == "sim_123"
        assert state.runner_status == RunnerStatus.IDLE
        assert state.current_round == 0
        assert state.total_rounds == 10
        assert state.total_simulation_hours == 24

    def test_simulation_run_state_add_action_twitter(self):
        """Test adding a Twitter action to simulation state"""
        state = SimulationRunState(
            simulation_id="sim_123",
            total_rounds=10
        )

        action = AgentAction(
            round_num=1,
            timestamp="2024-03-26T10:00:00",
            platform="twitter",
            agent_id=1,
            agent_name="Agent 1",
            action_type="CREATE_POST"
        )

        state.add_action(action)

        assert len(state.recent_actions) == 1
        assert state.recent_actions[0].agent_id == 1
        assert state.twitter_actions_count == 1
        assert state.reddit_actions_count == 0

    def test_simulation_run_state_add_action_reddit(self):
        """Test adding a Reddit action to simulation state"""
        state = SimulationRunState(
            simulation_id="sim_456",
            total_rounds=10
        )

        action = AgentAction(
            round_num=1,
            timestamp="2024-03-26T10:00:00",
            platform="reddit",
            agent_id=2,
            agent_name="Agent 2",
            action_type="COMMENT"
        )

        state.add_action(action)

        assert state.twitter_actions_count == 0
        assert state.reddit_actions_count == 1

    def test_simulation_run_state_recent_actions_limit(self):
        """Test that recent_actions list respects max_recent_actions limit"""
        state = SimulationRunState(
            simulation_id="sim_789",
            total_rounds=10
        )
        state.max_recent_actions = 5

        # Add 7 actions
        for i in range(7):
            action = AgentAction(
                round_num=1,
                timestamp=f"2024-03-26T10:{i:02d}:00",
                platform="twitter" if i % 2 == 0 else "reddit",
                agent_id=i,
                agent_name=f"Agent {i}",
                action_type="CREATE_POST"
            )
            state.add_action(action)

        assert len(state.recent_actions) == 5
        assert state.recent_actions[0].agent_id == 6  # Most recent

    def test_simulation_run_state_to_dict(self):
        """Test converting SimulationRunState to dictionary"""
        state = SimulationRunState(
            simulation_id="sim_dict",
            runner_status=RunnerStatus.RUNNING,
            current_round=5,
            total_rounds=10,
            simulated_hours=12,
            total_simulation_hours=24
        )

        state_dict = state.to_dict()

        assert isinstance(state_dict, dict)
        assert state_dict["simulation_id"] == "sim_dict"
        assert state_dict["runner_status"] == "running"
        assert state_dict["progress_percent"] == 50.0

    def test_simulation_run_state_progress_calculation(self):
        """Test progress percentage calculation"""
        state = SimulationRunState(
            simulation_id="sim_progress",
            current_round=3,
            total_rounds=10
        )

        state_dict = state.to_dict()
        assert state_dict["progress_percent"] == 30.0

    def test_simulation_run_state_progress_zero_total_rounds(self):
        """Test progress calculation with zero total rounds"""
        state = SimulationRunState(
            simulation_id="sim_zero",
            current_round=0,
            total_rounds=0
        )

        state_dict = state.to_dict()
        # Should not divide by zero
        assert state_dict["progress_percent"] == 0.0

    def test_simulation_run_state_to_detail_dict(self):
        """Test converting to detail dictionary with recent actions"""
        state = SimulationRunState(
            simulation_id="sim_detail",
            total_rounds=10
        )

        action = AgentAction(
            round_num=1,
            timestamp="2024-03-26T10:00:00",
            platform="twitter",
            agent_id=1,
            agent_name="Agent 1",
            action_type="CREATE_POST"
        )
        state.add_action(action)

        detail_dict = state.to_detail_dict()

        assert "recent_actions" in detail_dict
        assert len(detail_dict["recent_actions"]) == 1
        assert "rounds_count" in detail_dict

    def test_simulation_run_state_with_timestamps(self):
        """Test SimulationRunState timestamp handling"""
        state = SimulationRunState(
            simulation_id="sim_time",
            runner_status=RunnerStatus.RUNNING,
            total_rounds=10
        )

        state.started_at = "2024-03-26T10:00:00"
        state.completed_at = "2024-03-26T12:00:00"

        state_dict = state.to_dict()

        assert state_dict["started_at"] == "2024-03-26T10:00:00"
        assert state_dict["completed_at"] == "2024-03-26T12:00:00"


class TestRunnerStatus:
    """Test cases for RunnerStatus enum"""

    def test_runner_status_values(self):
        """Test all RunnerStatus enum values"""
        assert RunnerStatus.IDLE.value == "idle"
        assert RunnerStatus.STARTING.value == "starting"
        assert RunnerStatus.RUNNING.value == "running"
        assert RunnerStatus.PAUSED.value == "paused"
        assert RunnerStatus.STOPPING.value == "stopping"
        assert RunnerStatus.STOPPED.value == "stopped"
        assert RunnerStatus.COMPLETED.value == "completed"
        assert RunnerStatus.FAILED.value == "failed"

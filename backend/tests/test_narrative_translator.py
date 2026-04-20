import os
import json
import tempfile
import pytest
from app.services.narrative.narrative_translator import read_actions_for_round


@pytest.fixture
def actions_file():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "actions.jsonl")
        lines = [
            {"round": 1, "agent_id": 1, "agent_name": "Alice", "action_type": "CREATE_POST",
             "action_args": {"content": "Hi"}, "success": True, "timestamp": "2026-03-26T12:00:00"},
            {"round": 1, "agent_id": 2, "agent_name": "Bob", "action_type": "LIKE_POST",
             "action_args": {"post_id": 1}, "success": True, "timestamp": "2026-03-26T12:00:01"},
            {"event_type": "round_end", "round": 1, "timestamp": "2026-03-26T12:00:02"},
            {"round": 2, "agent_id": 1, "agent_name": "Alice", "action_type": "REPOST",
             "action_args": {}, "success": True, "timestamp": "2026-03-26T12:00:03"},
        ]
        with open(path, "w") as f:
            for line in lines:
                f.write(json.dumps(line) + "\n")
        yield path


def test_read_actions_for_round_1(actions_file):
    actions, next_offset = read_actions_for_round(actions_file, start_offset=0, target_round=1)
    assert len(actions) == 2
    assert actions[0]["agent_name"] == "Alice"
    assert actions[1]["agent_name"] == "Bob"
    assert next_offset > 0


def test_read_actions_resumes_from_offset(actions_file):
    _, offset_after_round_1 = read_actions_for_round(actions_file, start_offset=0, target_round=1)
    actions, _ = read_actions_for_round(actions_file, start_offset=offset_after_round_1, target_round=2)
    assert len(actions) == 1
    assert actions[0]["action_type"] == "REPOST"


def test_read_actions_missing_file_returns_empty():
    actions, offset = read_actions_for_round("/nonexistent/path.jsonl", start_offset=0, target_round=1)
    assert actions == []
    assert offset == 0

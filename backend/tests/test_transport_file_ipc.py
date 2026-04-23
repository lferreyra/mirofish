"""Tests for the file-poll IPC transport (legacy back-compat path)."""

import threading
import time

import pytest

from app.transport import (
    Command,
    CommandType,
    Event,
    EventType,
    Response,
    ResponseStatus,
)
from app.transport.file_ipc import FileServerTransport, FileTransport


@pytest.fixture
def sim_dir(tmp_path):
    return str(tmp_path / "sim")


def test_command_roundtrip_over_files(sim_dir):
    """Backend writes a command file; server reads it, responds; backend reads response."""
    client = FileTransport(sim_dir, poll_interval=0.01)
    server = FileServerTransport(sim_dir, poll_interval=0.01)

    def _server_loop():
        cmd = server.recv_command(timeout=2.0)
        assert cmd is not None
        server.send_response(Response(
            command_id=cmd.command_id, status=ResponseStatus.COMPLETED,
            result={"echo": cmd.args},
        ))

    t = threading.Thread(target=_server_loop, daemon=True)
    t.start()

    cmd = Command(command_type=CommandType.INTERVIEW, args={"agent_id": 3})
    resp = client.send_command(cmd, timeout=2.0)
    assert resp.status == ResponseStatus.COMPLETED
    assert resp.result == {"echo": {"agent_id": 3}}
    t.join(timeout=1.0)


def test_events_file_is_append_only_and_tailed(sim_dir):
    """Subscribers should pick up events written after they start watching."""
    server = FileServerTransport(sim_dir, poll_interval=0.01)
    client = FileTransport(sim_dir, poll_interval=0.01)

    collected = []
    stop = threading.Event()

    def _subscriber():
        for event in client.subscribe_events(run_id="run-1", timeout=0.05):
            collected.append(event)
            if stop.is_set() and len(collected) >= 2:
                return

    t = threading.Thread(target=_subscriber, daemon=True)
    t.start()

    # Publish two events from the "subprocess" side
    server.publish_event(Event(
        event_type=EventType.ROUND_STARTED, run_id="run-1",
        payload={"round": 1},
    ))
    server.publish_event(Event(
        event_type=EventType.AGENT_ACTION, run_id="run-1",
        payload={"agent_id": 2, "action_type": "CREATE_POST"},
    ))
    # Give the subscriber a moment to catch up
    deadline = time.time() + 2.0
    while len(collected) < 2 and time.time() < deadline:
        time.sleep(0.05)
    stop.set()
    t.join(timeout=1.0)

    assert len(collected) >= 2
    types = [e.event_type for e in collected[:2]]
    assert types == [EventType.ROUND_STARTED, EventType.AGENT_ACTION]


def test_events_filtered_by_run_id(sim_dir):
    """Events for other runs are ignored by a run-scoped subscriber."""
    server = FileServerTransport(sim_dir, poll_interval=0.01)
    client = FileTransport(sim_dir, poll_interval=0.01)

    seen = []
    stop = threading.Event()

    def _subscriber():
        for event in client.subscribe_events(run_id="wanted", timeout=0.05):
            seen.append(event)
            if stop.is_set() and seen:
                return

    t = threading.Thread(target=_subscriber, daemon=True)
    t.start()

    # Event for a different run — should be filtered out
    server.publish_event(Event(
        event_type=EventType.LOG, run_id="other", payload={"msg": "skip me"},
    ))
    server.publish_event(Event(
        event_type=EventType.LOG, run_id="wanted", payload={"msg": "keep me"},
    ))

    deadline = time.time() + 2.0
    while not seen and time.time() < deadline:
        time.sleep(0.05)
    stop.set()
    t.join(timeout=1.0)

    assert len(seen) == 1
    assert seen[0].run_id == "wanted"
    assert seen[0].payload["msg"] == "keep me"

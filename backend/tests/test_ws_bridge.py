"""Tests for the WebSocket bridge — event fan-out to multiple subscribers."""

import threading
import time

import pytest

from app.transport import Event, EventType
from app.transport.file_ipc import FileServerTransport
from app.ws.bridge import EventBridge, reset_bridge_for_tests


@pytest.fixture
def bridge():
    return reset_bridge_for_tests()


def test_event_fans_out_to_all_subscribers(tmp_path, bridge, monkeypatch):
    """Every connected subscriber sees every event for its run_id."""
    monkeypatch.setenv("IPC_TRANSPORT", "file")  # deterministic, no slow-joiner race

    sim_dir = str(tmp_path / "sim")
    bridge.register_run("run-1", sim_dir)

    seen_a, seen_b = [], []
    bridge.subscribe("run-1", seen_a.append)
    bridge.subscribe("run-1", seen_b.append)

    # Publish from the subprocess side
    server = FileServerTransport(sim_dir)
    server.publish_event(Event(
        event_type=EventType.AGENT_ACTION, run_id="run-1",
        payload={"agent_id": 2},
    ))
    server.publish_event(Event(
        event_type=EventType.ROUND_COMPLETED, run_id="run-1",
        payload={"round": 4},
    ))

    # Bridge worker polls every 500ms — give it time to pick up both events.
    deadline = time.time() + 3.0
    while (len(seen_a) < 2 or len(seen_b) < 2) and time.time() < deadline:
        time.sleep(0.05)

    assert len(seen_a) == 2 and len(seen_b) == 2
    assert [e["event_type"] for e in seen_a] == ["agent_action", "round_completed"]
    # Both subscribers saw the same event payload (fan-out correctness).
    assert seen_a[0]["payload"] == seen_b[0]["payload"]


def test_unsubscribe_stops_delivery(tmp_path, bridge, monkeypatch):
    monkeypatch.setenv("IPC_TRANSPORT", "file")
    sim_dir = str(tmp_path / "sim")
    bridge.register_run("run-2", sim_dir)

    seen = []
    unsub = bridge.subscribe("run-2", seen.append)

    server = FileServerTransport(sim_dir)
    server.publish_event(Event(
        event_type=EventType.LOG, run_id="run-2", payload={"msg": "first"},
    ))
    # Wait for the first event to be delivered
    deadline = time.time() + 2.0
    while not seen and time.time() < deadline:
        time.sleep(0.05)
    assert len(seen) == 1

    unsub()
    # Subsequent events shouldn't land in `seen` (the list is the subscriber).
    server.publish_event(Event(
        event_type=EventType.LOG, run_id="run-2", payload={"msg": "second"},
    ))
    time.sleep(1.0)
    assert len(seen) == 1  # still just the first one


def test_stop_run_releases_transport(tmp_path, bridge, monkeypatch):
    """After stop_run, new subscriptions require register_run again — used on
    simulation teardown so background threads actually exit."""
    monkeypatch.setenv("IPC_TRANSPORT", "file")
    sim_dir = str(tmp_path / "sim")
    bridge.register_run("run-3", sim_dir)
    bridge.subscribe("run-3", lambda e: None)
    assert "run-3" in bridge._transports  # worker spun up

    bridge.stop_run("run-3")
    assert "run-3" not in bridge._transports
    assert "run-3" not in bridge._subs

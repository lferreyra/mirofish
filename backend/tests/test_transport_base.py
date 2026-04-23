"""Tests for the transport package's base types + in-memory pair."""

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
    TransportError,
)
from app.transport.base import make_memory_pair


def test_command_json_roundtrip():
    cmd = Command(
        command_type=CommandType.INTERVIEW,
        args={"agent_id": 5, "question": "hi"},
    )
    raw = cmd.to_json()
    parsed = Command.from_json(raw)
    assert parsed.command_id == cmd.command_id
    assert parsed.command_type == CommandType.INTERVIEW
    assert parsed.args == {"agent_id": 5, "question": "hi"}


def test_response_json_roundtrip_preserves_status():
    resp = Response(
        command_id="abc",
        status=ResponseStatus.FAILED,
        error="boom",
    )
    parsed = Response.from_json(resp.to_json())
    assert parsed.status == ResponseStatus.FAILED
    assert parsed.error == "boom"


def test_event_frames_roundtrip():
    """ZMQ uses multipart (topic, body) frames; the encoding must roundtrip."""
    event = Event(
        event_type=EventType.AGENT_ACTION,
        payload={"agent_id": 2, "action": "CREATE_POST"},
        run_id="sim-9",
    )
    topic, body = event.to_frames()
    assert topic == b"run:sim-9"
    parsed = Event.from_frames(topic, body)
    assert parsed.event_type == EventType.AGENT_ACTION
    assert parsed.payload["agent_id"] == 2
    assert parsed.run_id == "sim-9"


def test_memory_pair_send_command_returns_matching_response():
    """Validates the shared-queue primitive used in later transport tests."""
    client, server = make_memory_pair()

    def _server_loop():
        cmd = server.recv_command(timeout=2.0)
        assert cmd is not None
        server.send_response(Response(command_id=cmd.command_id, result={"ok": True}))

    t = threading.Thread(target=_server_loop, daemon=True)
    t.start()

    cmd = Command(command_type=CommandType.PING, args={})
    resp = client.send_command(cmd, timeout=2.0)
    assert resp.command_id == cmd.command_id
    assert resp.result == {"ok": True}
    t.join(timeout=1.0)


def test_memory_pair_send_command_times_out_with_no_server():
    """When no server replies, send_command must raise — never hang forever."""
    client, _server = make_memory_pair()
    cmd = Command(command_type=CommandType.PING, args={})
    with pytest.raises(TransportError) as exc_info:
        client.send_command(cmd, timeout=0.05)
    assert exc_info.value.code == "timeout"


def test_event_topic_uses_run_placeholder_when_unset():
    """Events with no run_id still have a parseable topic for subscribers."""
    event = Event(event_type=EventType.LOG, payload={})
    topic, _ = event.to_frames()
    assert topic == b"run:_"

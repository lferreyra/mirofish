"""Tests for the ZeroMQ transport. Uses `inproc://` sockets so the test
doesn't touch the network or the filesystem."""

import threading
import time
import uuid

import pytest

pytest.importorskip("zmq")

from app.transport import (
    Command,
    CommandType,
    Event,
    EventType,
    Response,
    ResponseStatus,
    TransportError,
)
from app.transport.zmq_transport import ZmqServerTransport, ZmqTransport


@pytest.fixture
def endpoints():
    """Unique inproc endpoints per test so parallel tests don't collide."""
    tag = uuid.uuid4().hex[:8]
    return f"inproc://cmd-{tag}", f"inproc://evt-{tag}"


def test_command_roundtrip_zmq(endpoints):
    """DEALER (backend) sends to ROUTER (subprocess); reply routes back by identity."""
    cmd_ep, evt_ep = endpoints
    # Server binds first, then client connects — required for inproc:// on pyzmq <25.
    server = ZmqServerTransport(cmd_endpoint=cmd_ep, event_endpoint=evt_ep)
    try:
        client = ZmqTransport(cmd_endpoint=cmd_ep, event_endpoint=evt_ep)

        def _serve():
            cmd = server.recv_command(timeout=2.0)
            assert cmd is not None
            server.send_response(Response(
                command_id=cmd.command_id, status=ResponseStatus.COMPLETED,
                result={"pong": True},
            ))

        t = threading.Thread(target=_serve, daemon=True)
        t.start()

        cmd = Command(command_type=CommandType.PING, args={})
        resp = client.send_command(cmd, timeout=2.0)
        assert resp.command_id == cmd.command_id
        assert resp.result == {"pong": True}
        t.join(timeout=1.0)
        client.close()
    finally:
        server.close()


def test_send_command_times_out_when_server_silent(endpoints):
    cmd_ep, evt_ep = endpoints
    server = ZmqServerTransport(cmd_endpoint=cmd_ep, event_endpoint=evt_ep)
    try:
        client = ZmqTransport(cmd_endpoint=cmd_ep, event_endpoint=evt_ep)
        with pytest.raises(TransportError) as exc_info:
            client.send_command(Command(command_type=CommandType.PING, args={}), timeout=0.1)
        assert exc_info.value.code == "timeout"
        client.close()
    finally:
        server.close()


def test_event_publish_subscribe(endpoints):
    """PUB/SUB: subscriber starts, then server publishes — test slow-joiner
    mitigation via a short pre-publish sleep."""
    cmd_ep, evt_ep = endpoints
    server = ZmqServerTransport(cmd_endpoint=cmd_ep, event_endpoint=evt_ep)
    try:
        client = ZmqTransport(cmd_endpoint=cmd_ep, event_endpoint=evt_ep)

        received = []
        stop = threading.Event()

        def _consume():
            # The subscriber can raise TransportError("recv_failed") when the
            # socket is closed during shutdown; swallow it so pytest doesn't
            # surface a PytestUnhandledThreadExceptionWarning.
            try:
                for event in client.subscribe_events(run_id="r1", timeout=0.1):
                    received.append(event)
                    if stop.is_set():
                        return
            except Exception:
                return

        t = threading.Thread(target=_consume, daemon=True)
        t.start()
        # Slow-joiner: PUB drops messages until SUB subscribes. Give it a tick.
        time.sleep(0.1)

        server.publish_event(Event(
            event_type=EventType.AGENT_ACTION, run_id="r1",
            payload={"agent_id": 5, "action_type": "CREATE_POST"},
        ))
        server.publish_event(Event(
            event_type=EventType.ROUND_COMPLETED, run_id="r1",
            payload={"round": 1},
        ))

        deadline = time.time() + 2.0
        while len(received) < 2 and time.time() < deadline:
            time.sleep(0.05)
        stop.set()
        # Close the client SUB socket before joining — this wakes the poll()
        # inside _consume so the thread exits cleanly instead of on shutdown.
        client.close()
        t.join(timeout=2.0)

        assert len(received) == 2
        assert received[0].event_type == EventType.AGENT_ACTION
        assert received[1].event_type == EventType.ROUND_COMPLETED
    finally:
        server.close()

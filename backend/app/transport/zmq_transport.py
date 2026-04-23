"""
ZeroMQ transport. Replaces the file-poll IPC with real sockets.

Topology:
    Backend side (Transport):
        DEALER socket -> connects to subprocess ROUTER  (request/reply)
        SUB socket    -> connects to subprocess PUB     (event fan-out)

    Subprocess side (ServerTransport):
        ROUTER socket -> binds on `cmd_endpoint`
        PUB socket    -> binds on `event_endpoint`

Why DEALER/ROUTER instead of REQ/REP: REQ enforces strict send-then-recv
turn-taking. DEALER lets the backend issue concurrent commands (e.g.
interviews from multiple WebSocket clients) without serializing them.

Chosen over gRPC for the reason stated in Phase 3: ZeroMQ has no service-
definition / codegen overhead, handles the in-process test endpoint
(`inproc://`) without any network binding, and ships a PUB/SUB pattern out
of the box. If we needed HTTP/2 multiplexing with schemas we'd pick gRPC;
for local IPC between two trusted processes, ZMQ is less friction.
"""

from __future__ import annotations

import threading
import time
import uuid
from typing import Dict, Iterator, Optional

from .base import (
    Command,
    Event,
    EventType,
    Response,
    ServerTransport,
    Transport,
    TransportError,
)


def _import_zmq():
    try:
        import zmq  # type: ignore
        return zmq
    except ImportError as exc:
        raise TransportError(
            "zmq_missing",
            "pyzmq package is required for the zmq transport",
            transport="zmq",
        ) from exc


class ZmqTransport(Transport):
    """Backend side."""

    name = "zmq"

    def __init__(self, *, cmd_endpoint: str, event_endpoint: str):
        zmq = _import_zmq()
        self._zmq = zmq
        self._ctx = zmq.Context.instance()

        self._cmd_sock = self._ctx.socket(zmq.DEALER)
        # Unique identity so the ROUTER on the other side can route replies back.
        self._cmd_sock.setsockopt(zmq.IDENTITY, uuid.uuid4().bytes)
        self._cmd_sock.connect(cmd_endpoint)

        self._evt_sock = self._ctx.socket(zmq.SUB)
        self._evt_sock.connect(event_endpoint)
        # Subscribe to everything by default; filtering is cheap and per-subscriber.
        self._evt_sock.setsockopt(zmq.SUBSCRIBE, b"")

        # Thread-safety: pyzmq sockets aren't thread-safe. Serialize sends.
        self._send_lock = threading.Lock()
        self._cmd_endpoint = cmd_endpoint
        self._event_endpoint = event_endpoint

    def send_command(self, command: Command, *, timeout: float = 60.0) -> Response:
        zmq = self._zmq
        try:
            with self._send_lock:
                self._cmd_sock.send(command.to_json().encode("utf-8"))
            # Poll so `timeout` is honored; raw recv() blocks forever.
            if self._cmd_sock.poll(int(timeout * 1000), flags=zmq.POLLIN) == 0:
                raise TransportError(
                    "timeout",
                    f"no response within {timeout}s for {command.command_id}",
                    transport=self.name,
                )
            raw = self._cmd_sock.recv()
            response = Response.from_json(raw)
        except TransportError:
            raise
        except Exception as exc:
            raise TransportError("send_failed", str(exc), transport=self.name) from exc

        if response.command_id != command.command_id:
            # DEALER guarantees FIFO to the same ROUTER, but log the mismatch
            # in case a stale reply slipped in. The command_id is authoritative.
            raise TransportError(
                "mismatched_response",
                f"expected id={command.command_id}, got {response.command_id}",
                transport=self.name,
            )
        return response

    def subscribe_events(
        self,
        *,
        run_id: Optional[str] = None,
        timeout: float = 1.0,
    ) -> Iterator[Event]:
        zmq = self._zmq
        while True:
            if self._evt_sock.poll(int(timeout * 1000), flags=zmq.POLLIN) == 0:
                continue
            try:
                topic, body = self._evt_sock.recv_multipart()
            except Exception as exc:
                raise TransportError("recv_failed", str(exc), transport=self.name) from exc
            event = Event.from_frames(topic, body)
            if run_id is None or event.run_id == run_id:
                yield event

    def close(self) -> None:
        try:
            self._cmd_sock.close(linger=0)
            self._evt_sock.close(linger=0)
        except Exception:
            pass


class ZmqServerTransport(ServerTransport):
    """Subprocess side. ROUTER for commands, PUB for events."""

    name = "zmq"

    def __init__(self, *, cmd_endpoint: str, event_endpoint: str):
        zmq = _import_zmq()
        self._zmq = zmq
        self._ctx = zmq.Context.instance()

        self._cmd_sock = self._ctx.socket(zmq.ROUTER)
        self._cmd_sock.bind(cmd_endpoint)

        self._evt_sock = self._ctx.socket(zmq.PUB)
        self._evt_sock.bind(event_endpoint)

        # Maps command_id -> the peer identity so `send_response` routes back.
        self._peer_by_command: Dict[str, bytes] = {}
        self._lock = threading.Lock()

    def recv_command(self, *, timeout: float = 1.0) -> Optional[Command]:
        zmq = self._zmq
        if self._cmd_sock.poll(int(timeout * 1000), flags=zmq.POLLIN) == 0:
            return None
        # ROUTER prepends the peer identity.
        peer, raw = self._cmd_sock.recv_multipart()
        command = Command.from_json(raw)
        with self._lock:
            self._peer_by_command[command.command_id] = peer
        return command

    def send_response(self, response: Response) -> None:
        with self._lock:
            peer = self._peer_by_command.pop(response.command_id, None)
        if peer is None:
            # The command either never arrived or someone is responding twice.
            # Drop silently — logging left to the caller.
            return
        self._cmd_sock.send_multipart([peer, response.to_json().encode("utf-8")])

    def publish_event(self, event: Event) -> None:
        topic, body = event.to_frames()
        self._evt_sock.send_multipart([topic, body])

    def close(self) -> None:
        try:
            self._cmd_sock.close(linger=0)
            self._evt_sock.close(linger=0)
        except Exception:
            pass

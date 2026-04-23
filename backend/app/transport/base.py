"""
Transport abstractions. Two halves:

    Transport       - held by the Flask backend; sends commands, subscribes to events
    ServerTransport - held by the simulation subprocess; receives commands, publishes events

A single concrete implementation (`ZmqTransport`, `FileTransport`) usually
exposes both sides via factory methods because they must agree on wire
format.

Why two ABCs instead of one: the backend's typical work is very different
from the subprocess's — merging them produces methods that raise on one
side or the other. Separate ABCs make that explicit.
"""

from __future__ import annotations

import json
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Iterator, Optional


# --------------------------------------------------------------------------
# Command/Response/Event types
# --------------------------------------------------------------------------

class CommandType(str, Enum):
    """Backend -> subprocess command kinds."""
    PING = "ping"                        # health check
    INTERVIEW = "interview"              # ask a single agent a question
    INTERVIEW_STREAM = "interview_stream"  # token-by-token streaming reply
    BATCH_INTERVIEW = "batch_interview"  # ask multiple agents
    CLOSE_ENV = "close_env"              # stop the simulation cleanly
    CHECKPOINT = "checkpoint"            # capture round state
    RESTORE = "restore"                  # resume from a capture


class ResponseStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class EventType(str, Enum):
    """Subprocess -> backend event kinds."""
    ROUND_STARTED = "round_started"
    ROUND_COMPLETED = "round_completed"
    AGENT_ACTION = "agent_action"
    INTERVIEW_CHUNK = "interview_chunk"       # single streamed fragment
    INTERVIEW_DONE = "interview_done"
    ERROR = "error"
    LOG = "log"


@dataclass
class Command:
    args: Dict[str, Any]
    command_type: CommandType = CommandType.PING
    command_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    ts: float = field(default_factory=time.time)

    def to_json(self) -> str:
        return json.dumps({
            "command_id": self.command_id,
            "command_type": self.command_type.value,
            "args": self.args,
            "ts": self.ts,
        })

    @classmethod
    def from_json(cls, raw: bytes | str) -> "Command":
        data = json.loads(raw)
        return cls(
            command_id=data["command_id"],
            command_type=CommandType(data["command_type"]),
            args=data.get("args", {}) or {},
            ts=float(data.get("ts", time.time())),
        )


@dataclass
class Response:
    command_id: str
    status: ResponseStatus = ResponseStatus.COMPLETED
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    ts: float = field(default_factory=time.time)

    def to_json(self) -> str:
        return json.dumps({
            "command_id": self.command_id,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "ts": self.ts,
        })

    @classmethod
    def from_json(cls, raw: bytes | str) -> "Response":
        data = json.loads(raw)
        return cls(
            command_id=data["command_id"],
            status=ResponseStatus(data["status"]),
            result=data.get("result"),
            error=data.get("error"),
            ts=float(data.get("ts", time.time())),
        )


@dataclass
class Event:
    """Subprocess -> backend published message. No reply expected."""
    event_type: EventType
    payload: Dict[str, Any] = field(default_factory=dict)
    run_id: Optional[str] = None
    ts: float = field(default_factory=time.time)

    # Routing topic for ZMQ PUB/SUB. The backend subscribes to `run:<id>` and
    # rebroadcasts to WebSocket clients watching that run.
    @property
    def topic(self) -> str:
        return f"run:{self.run_id}" if self.run_id else "run:_"

    def to_frames(self) -> tuple[bytes, bytes]:
        """Return (topic, body) for ZMQ multipart send."""
        body = json.dumps({
            "event_type": self.event_type.value,
            "payload": self.payload,
            "run_id": self.run_id,
            "ts": self.ts,
        }).encode("utf-8")
        return self.topic.encode("utf-8"), body

    @classmethod
    def from_frames(cls, topic: bytes, body: bytes) -> "Event":
        data = json.loads(body)
        return cls(
            event_type=EventType(data["event_type"]),
            payload=data.get("payload", {}) or {},
            run_id=data.get("run_id"),
            ts=float(data.get("ts", time.time())),
        )


@dataclass
class Envelope:
    """Lightweight container for things that carry either a Command, Response,
    or Event. Used by in-memory transport in tests."""
    kind: str
    command: Optional[Command] = None
    response: Optional[Response] = None
    event: Optional[Event] = None


class TransportError(Exception):
    def __init__(self, code: str, message: str, *, transport: Optional[str] = None):
        super().__init__(f"[{transport or '?'}:{code}] {message}")
        self.code = code
        self.message = message
        self.transport = transport


# --------------------------------------------------------------------------
# Abstract client (backend) and server (subprocess) transports
# --------------------------------------------------------------------------

class Transport(ABC):
    """Backend side — sends commands, receives events."""

    name: str = "abstract"

    @abstractmethod
    def send_command(self, command: Command, *, timeout: float = 60.0) -> Response:
        ...

    @abstractmethod
    def subscribe_events(
        self,
        *,
        run_id: Optional[str] = None,
        timeout: float = 1.0,
    ) -> Iterator[Event]:
        """Yield events indefinitely until the caller breaks out of the loop.
        `timeout` is the per-poll wait so consumers can cooperatively shut down."""
        ...

    def close(self) -> None:  # optional override
        return None


class ServerTransport(ABC):
    """Subprocess side — receives commands, publishes events."""

    name: str = "abstract"

    @abstractmethod
    def recv_command(self, *, timeout: float = 1.0) -> Optional[Command]:
        """Return the next pending command, or None after `timeout`."""
        ...

    @abstractmethod
    def send_response(self, response: Response) -> None:
        ...

    @abstractmethod
    def publish_event(self, event: Event) -> None:
        ...

    def close(self) -> None:
        return None


# --------------------------------------------------------------------------
# Convenience helper for tests: an in-memory transport pair
# --------------------------------------------------------------------------

class _InMemoryTransport(Transport):
    """Paired with `_InMemoryServerTransport` via a shared queue dict."""

    name = "memory"

    def __init__(self, shared: Dict[str, Any]):
        self._shared = shared

    def send_command(self, command: Command, *, timeout: float = 60.0) -> Response:
        self._shared["cmd_q"].append(command)
        # Synchronously wait for the matching response.
        deadline = time.time() + timeout
        while time.time() < deadline:
            for idx, resp in enumerate(self._shared["resp_q"]):
                if resp.command_id == command.command_id:
                    return self._shared["resp_q"].pop(idx)
            time.sleep(0.001)
        raise TransportError("timeout", f"no response for {command.command_id}", transport=self.name)

    def subscribe_events(self, *, run_id=None, timeout=1.0):
        idx = 0
        while True:
            while idx < len(self._shared["events"]):
                ev = self._shared["events"][idx]
                idx += 1
                if run_id is None or ev.run_id == run_id:
                    yield ev
            time.sleep(timeout)


class _InMemoryServerTransport(ServerTransport):
    name = "memory"

    def __init__(self, shared: Dict[str, Any]):
        self._shared = shared

    def recv_command(self, *, timeout: float = 1.0) -> Optional[Command]:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self._shared["cmd_q"]:
                return self._shared["cmd_q"].pop(0)
            time.sleep(0.001)
        return None

    def send_response(self, response: Response) -> None:
        self._shared["resp_q"].append(response)

    def publish_event(self, event: Event) -> None:
        self._shared["events"].append(event)


def make_memory_pair() -> tuple[Transport, ServerTransport]:
    """Factory that returns a matched (client, server) pair for tests."""
    shared: Dict[str, Any] = {"cmd_q": [], "resp_q": [], "events": []}
    return _InMemoryTransport(shared), _InMemoryServerTransport(shared)

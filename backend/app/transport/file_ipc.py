"""
File-based transport — wraps the pre-existing polling-loop protocol so the
legacy code path continues to work when `IPC_TRANSPORT=file`.

Known limitation (which is why Phase 3 replaces this by default): no native
event channel. `publish_event` and `subscribe_events` are implemented as an
append-only JSON-lines file that both sides poll. Works, but not real-time.
"""

from __future__ import annotations

import json
import os
import time
from typing import Iterator, Optional

from .base import (
    Command,
    CommandType,
    Event,
    EventType,
    Response,
    ResponseStatus,
    ServerTransport,
    Transport,
    TransportError,
)


def _ensure(dir_path: str) -> str:
    os.makedirs(dir_path, exist_ok=True)
    return dir_path


class FileTransport(Transport):
    """Backend side — writes command files, polls for response + event files."""

    name = "file"

    def __init__(self, simulation_dir: str, *, poll_interval: float = 0.1):
        self._dir = simulation_dir
        self._cmd_dir = _ensure(os.path.join(simulation_dir, "ipc_commands"))
        self._resp_dir = _ensure(os.path.join(simulation_dir, "ipc_responses"))
        self._events_file = os.path.join(simulation_dir, "ipc_events.jsonl")
        self._poll = poll_interval

    def send_command(self, command: Command, *, timeout: float = 60.0) -> Response:
        cmd_path = os.path.join(self._cmd_dir, f"{command.command_id}.json")
        resp_path = os.path.join(self._resp_dir, f"{command.command_id}.json")
        # Atomic write to avoid the subprocess reading a half-written file.
        tmp = cmd_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(command.to_json())
        os.replace(tmp, cmd_path)

        deadline = time.time() + timeout
        while time.time() < deadline:
            if os.path.exists(resp_path):
                with open(resp_path, "r", encoding="utf-8") as fh:
                    data = fh.read()
                try:
                    os.remove(resp_path)
                except OSError:
                    pass
                return Response.from_json(data)
            time.sleep(self._poll)
        raise TransportError(
            "timeout",
            f"no response within {timeout}s for {command.command_id}",
            transport=self.name,
        )

    def subscribe_events(
        self,
        *,
        run_id: Optional[str] = None,
        timeout: float = 1.0,
    ) -> Iterator[Event]:
        offset = 0
        while True:
            if os.path.exists(self._events_file):
                with open(self._events_file, "r", encoding="utf-8") as fh:
                    fh.seek(offset)
                    for line in fh:
                        offset += len(line.encode("utf-8"))
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                            event = Event(
                                event_type=EventType(data["event_type"]),
                                payload=data.get("payload", {}) or {},
                                run_id=data.get("run_id"),
                                ts=float(data.get("ts", time.time())),
                            )
                        except Exception:
                            continue
                        if run_id is None or event.run_id == run_id:
                            yield event
            time.sleep(timeout)


class FileServerTransport(ServerTransport):
    """Subprocess side — polls the command dir, writes responses + events."""

    name = "file"

    def __init__(self, simulation_dir: str, *, poll_interval: float = 0.05):
        self._dir = simulation_dir
        self._cmd_dir = _ensure(os.path.join(simulation_dir, "ipc_commands"))
        self._resp_dir = _ensure(os.path.join(simulation_dir, "ipc_responses"))
        self._events_file = os.path.join(simulation_dir, "ipc_events.jsonl")
        self._poll = poll_interval

    def recv_command(self, *, timeout: float = 1.0) -> Optional[Command]:
        deadline = time.time() + timeout
        while time.time() < deadline:
            pending = sorted(
                f for f in os.listdir(self._cmd_dir)
                if f.endswith(".json") and not f.endswith(".tmp")
            )
            if pending:
                path = os.path.join(self._cmd_dir, pending[0])
                try:
                    with open(path, "r", encoding="utf-8") as fh:
                        data = fh.read()
                    os.remove(path)
                except FileNotFoundError:
                    continue
                return Command.from_json(data)
            time.sleep(self._poll)
        return None

    def send_response(self, response: Response) -> None:
        path = os.path.join(self._resp_dir, f"{response.command_id}.json")
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(response.to_json())
        os.replace(tmp, path)

    def publish_event(self, event: Event) -> None:
        # Append-only jsonl so the backend can tail without coordination.
        _, body = event.to_frames()
        with open(self._events_file, "ab") as fh:
            fh.write(body + b"\n")

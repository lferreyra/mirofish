"""
Factory helpers — pick the right transport pair based on env + endpoints.

Usage:
    # Backend:
    client = build_client_transport(run_id="sim-42", simulation_dir="/var/runs/sim-42")

    # Subprocess:
    server = build_server_transport(run_id="sim-42", simulation_dir="/var/runs/sim-42")

Both sides must resolve to the same transport kind. When using ZMQ with TCP
endpoints, pass them explicitly; for local runs the factory picks stable
`ipc://` endpoints derived from the simulation_dir.
"""

from __future__ import annotations

import os
from typing import Optional


def _transport_kind() -> str:
    return os.environ.get("IPC_TRANSPORT", "zmq").strip().lower()


def _ipc_endpoints(simulation_dir: str, run_id: str) -> tuple[str, str]:
    """Return (cmd_endpoint, event_endpoint) for `ipc://` sockets. Paths live
    inside the simulation dir so parallel runs don't collide."""
    sock_dir = os.path.join(simulation_dir, ".sockets")
    os.makedirs(sock_dir, exist_ok=True)
    cmd = os.environ.get("IPC_CMD_ENDPOINT") or f"ipc://{sock_dir}/cmd.sock"
    evt = os.environ.get("IPC_EVENT_ENDPOINT") or f"ipc://{sock_dir}/events.sock"
    return cmd, evt


def build_client_transport(
    *,
    run_id: str,
    simulation_dir: str,
    kind: Optional[str] = None,
):
    """Construct the backend-side transport for a given simulation."""
    kind = (kind or _transport_kind()).lower()
    if kind == "file":
        from .file_ipc import FileTransport
        return FileTransport(simulation_dir)
    if kind == "zmq":
        from .zmq_transport import ZmqTransport
        cmd, evt = _ipc_endpoints(simulation_dir, run_id)
        return ZmqTransport(cmd_endpoint=cmd, event_endpoint=evt)
    raise ValueError(f"unknown IPC_TRANSPORT={kind!r}")


def build_server_transport(
    *,
    run_id: str,
    simulation_dir: str,
    kind: Optional[str] = None,
):
    """Construct the subprocess-side transport for a given simulation."""
    kind = (kind or _transport_kind()).lower()
    if kind == "file":
        from .file_ipc import FileServerTransport
        return FileServerTransport(simulation_dir)
    if kind == "zmq":
        from .zmq_transport import ZmqServerTransport
        cmd, evt = _ipc_endpoints(simulation_dir, run_id)
        return ZmqServerTransport(cmd_endpoint=cmd, event_endpoint=evt)
    raise ValueError(f"unknown IPC_TRANSPORT={kind!r}")

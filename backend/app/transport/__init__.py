"""
Pluggable transport between Flask backend and the simulation subprocess.

Phase-3 design:
  * Two channels per simulation:
       - command channel (request/reply): backend -> subprocess
       - event channel (publish/subscribe): subprocess -> backend (and onward
         to WebSocket clients)
  * Two implementations:
       - file_ipc:   the legacy file-poll protocol, unchanged on the wire
       - zmq:        REQ/REP for commands, PUB/SUB for events

Selection is env-driven (`IPC_TRANSPORT=file|zmq`). The default is `zmq` for
new runs; existing simulations launched on the file protocol keep working.
"""

from .base import (
    Command,
    CommandType,
    Envelope,
    Event,
    EventType,
    Response,
    ResponseStatus,
    ServerTransport,
    Transport,
    TransportError,
)
from .factory import build_client_transport, build_server_transport

__all__ = [
    "Command",
    "CommandType",
    "Envelope",
    "Event",
    "EventType",
    "Response",
    "ResponseStatus",
    "ServerTransport",
    "Transport",
    "TransportError",
    "build_client_transport",
    "build_server_transport",
]

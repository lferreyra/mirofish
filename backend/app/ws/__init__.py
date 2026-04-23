"""
WebSocket bridge — rebroadcasts Transport events to browser clients.

The backend-side Transport's `subscribe_events()` iterator runs in a single
background thread per run. Connected WebSocket sessions hand their send
function to the bridge; every event is forwarded to every subscriber.

Usage (registered in `create_app`):

    from app.ws.streaming import register_ws_routes
    register_ws_routes(app)

Clients connect to `ws://host/ws/simulation/<run_id>` and receive JSON
messages of the form:

    {"event_type": "agent_action", "payload": {...}, "run_id": "...", "ts": ...}
"""

from .bridge import EventBridge, get_bridge

__all__ = ["EventBridge", "get_bridge"]

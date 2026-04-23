"""
Flask WebSocket routes:

    /ws/simulation/<run_id>        -- live event feed for a simulation
    /ws/simulation/<run_id>/interview
                                   -- send {"question": "...", "agent_id": N}; receive
                                      stream of {"chunk": "...tokens..."} then
                                      {"done": true}

Uses flask-sock (falls back cleanly if not installed — register_ws_routes
logs a warning and is a no-op).
"""

from __future__ import annotations

import json
import logging
import threading
from typing import TYPE_CHECKING

from ..llm import ModelRouter, Role
from ..llm.base import BackendError
from ..transport import Command, CommandType, build_client_transport
from .bridge import get_bridge

logger = logging.getLogger("mirofish.ws.streaming")

if TYPE_CHECKING:
    from flask import Flask


def register_ws_routes(app: "Flask") -> None:
    """Attach /ws/* routes onto the Flask app. No-op if flask-sock is missing."""
    try:
        from flask_sock import Sock  # type: ignore
    except ImportError:
        logger.warning(
            "flask-sock not installed; WebSocket endpoints /ws/simulation/<id> "
            "are unavailable. Install with: pip install flask-sock"
        )
        return

    sock = Sock(app)

    @sock.route("/ws/simulation/<run_id>")
    def simulation_events(ws, run_id: str):
        """Forward transport events to this WebSocket client in real time."""
        bridge = get_bridge()

        # Simple thread-safe send — flask-sock runs one worker per connection.
        send_lock = threading.Lock()

        def _subscriber(event_dict: dict) -> None:
            with send_lock:
                try:
                    ws.send(json.dumps(event_dict))
                except Exception:
                    # Socket went away; let the unsubscribe happen via the
                    # outer try/finally below.
                    raise

        unsubscribe = bridge.subscribe(run_id, _subscriber)
        try:
            # Hold the connection open until the client disconnects. A ping
            # loop keeps intermediate proxies from closing idle sockets.
            while True:
                msg = ws.receive(timeout=30)
                if msg is None:
                    # 30s with no traffic — send a ping so the client knows we're alive.
                    with send_lock:
                        ws.send(json.dumps({"event_type": "ping", "ts": 0}))
        except Exception:
            return
        finally:
            unsubscribe()

    @sock.route("/ws/simulation/<run_id>/interview")
    def interview_stream(ws, run_id: str):
        """Streaming interview: one question in, many token fragments out.

        Protocol: first message from client must be JSON
        `{"agent_id": N, "question": "..."}`. Server responds with a series
        of `{"chunk": "...tokens..."}` messages, terminated by `{"done": true}`
        (or `{"error": "..."}`).

        The LLM call goes directly through the ModelRouter — no subprocess
        round-trip needed — which is why Phase-3 interviews are <20ms
        per-chunk instead of the old ~200ms file-poll.
        """
        router = ModelRouter.default()
        try:
            first = ws.receive()
            if first is None:
                return
            req = json.loads(first)
            agent_id = int(req.get("agent_id", 0))
            question = req.get("question", "").strip()
            if not question:
                ws.send(json.dumps({"error": "question is required"}))
                return
        except Exception as exc:
            try:
                ws.send(json.dumps({"error": f"bad request: {exc}"}))
            except Exception:
                pass
            return

        # Build the prompt — for Phase 3 this is intentionally minimal. Phase 4
        # will enrich with structured personas; for now the front matter just
        # tags the agent so the model has context.
        messages = [
            {
                "role": "system",
                "content": (
                    "You are being interviewed as agent {agent_id} in simulation "
                    "{run_id}. Answer honestly and in first person, in 2-4 short "
                    "sentences."
                ).format(agent_id=agent_id, run_id=run_id),
            },
            {"role": "user", "content": question},
        ]

        try:
            for chunk in router.stream_chat(
                Role.BALANCED,
                messages,
                temperature=0.4,
                max_tokens=400,
                cache_key=f"interview:{run_id}",
            ):
                ws.send(json.dumps({"chunk": chunk}))
            ws.send(json.dumps({"done": True}))
        except BackendError as exc:
            ws.send(json.dumps({"error": f"{exc.code}: {exc.message}"}))
        except Exception as exc:
            ws.send(json.dumps({"error": str(exc)}))

"""
EventBridge — process-wide fan-out from transport events to WebSocket clients.

One bridge, many runs. For each run_id the bridge spawns a lazy worker
thread that subscribes to the transport's event stream and writes each
event to every registered subscriber. Subscribers are bare callables
(`callable(event_dict)`) so this module doesn't know about Flask or
flask-sock directly — easier to test.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import asdict
from typing import Callable, Dict, List, Optional

from ..transport import Event, Transport, build_client_transport

logger = logging.getLogger("mirofish.ws.bridge")

Subscriber = Callable[[dict], None]


class EventBridge:
    """Fan-out hub. Thread-safe."""

    def __init__(self):
        # run_id -> list of subscribers
        self._subs: Dict[str, List[Subscriber]] = {}
        # run_id -> worker thread (lazily spawned)
        self._workers: Dict[str, threading.Thread] = {}
        self._transports: Dict[str, Transport] = {}
        # run_id -> simulation_dir so we can construct the transport lazily.
        self._run_dirs: Dict[str, str] = {}
        # Signal for cooperative shutdown.
        self._stop_flags: Dict[str, threading.Event] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------- setup
    def register_run(self, run_id: str, simulation_dir: str) -> None:
        """Tell the bridge a simulation exists. Called from simulation_runner
        when it spawns a subprocess. Safe to call multiple times."""
        with self._lock:
            self._run_dirs[run_id] = simulation_dir

    def subscribe(self, run_id: str, subscriber: Subscriber) -> Callable[[], None]:
        """Register a subscriber; returns an unsubscribe function."""
        with self._lock:
            self._subs.setdefault(run_id, []).append(subscriber)
            self._ensure_worker(run_id)

        def _unsubscribe() -> None:
            with self._lock:
                bucket = self._subs.get(run_id)
                if not bucket:
                    return
                try:
                    bucket.remove(subscriber)
                except ValueError:
                    return
                if not bucket:
                    # Keep the worker alive — other runs may be active and stopping
                    # the transport here would race with future subscribers. We
                    # do stop the worker via `stop_run()` when the simulation ends.
                    pass

        return _unsubscribe

    def stop_run(self, run_id: str) -> None:
        """Stop the worker thread and close the transport for a run."""
        with self._lock:
            flag = self._stop_flags.pop(run_id, None)
            transport = self._transports.pop(run_id, None)
            self._workers.pop(run_id, None)
            self._subs.pop(run_id, None)
            self._run_dirs.pop(run_id, None)
        if flag is not None:
            flag.set()
        if transport is not None:
            try:
                transport.close()
            except Exception:
                pass

    # --------------------------------------------------------- internals
    def _ensure_worker(self, run_id: str) -> None:
        """Must be called with self._lock held."""
        if run_id in self._workers and self._workers[run_id].is_alive():
            return
        sim_dir = self._run_dirs.get(run_id)
        if sim_dir is None:
            # No known directory — caller forgot to register_run. Log and skip.
            logger.warning("EventBridge: no simulation_dir registered for run=%s", run_id)
            return
        transport = build_client_transport(run_id=run_id, simulation_dir=sim_dir)
        self._transports[run_id] = transport
        stop_flag = threading.Event()
        self._stop_flags[run_id] = stop_flag
        worker = threading.Thread(
            target=self._worker_loop,
            args=(run_id, transport, stop_flag),
            daemon=True,
            name=f"ws-bridge-{run_id}",
        )
        self._workers[run_id] = worker
        worker.start()

    def _worker_loop(self, run_id: str, transport: Transport, stop_flag: threading.Event) -> None:
        """Pull events from the transport, fan them out to subscribers."""
        try:
            for event in transport.subscribe_events(run_id=run_id, timeout=0.5):
                if stop_flag.is_set():
                    return
                self._fan_out(run_id, event)
        except Exception as exc:
            logger.warning("EventBridge worker crashed for run=%s: %s", run_id, exc)
        finally:
            try:
                transport.close()
            except Exception:
                pass

    def _fan_out(self, run_id: str, event: Event) -> None:
        with self._lock:
            subscribers = list(self._subs.get(run_id, []))
        if not subscribers:
            return
        payload = {
            "event_type": event.event_type.value,
            "payload": event.payload,
            "run_id": event.run_id,
            "ts": event.ts,
        }
        for sub in subscribers:
            try:
                sub(payload)
            except Exception as exc:
                logger.debug("subscriber raised, dropping: %s", exc)


# Process-wide singleton — the Flask app calls `get_bridge()`.
_GLOBAL: Optional[EventBridge] = None
_LOCK = threading.Lock()


def get_bridge() -> EventBridge:
    global _GLOBAL
    if _GLOBAL is not None:
        return _GLOBAL
    with _LOCK:
        if _GLOBAL is None:
            _GLOBAL = EventBridge()
    return _GLOBAL


def reset_bridge_for_tests() -> EventBridge:
    """Test hook — replaces the singleton with a fresh bridge."""
    global _GLOBAL
    with _LOCK:
        _GLOBAL = EventBridge()
    return _GLOBAL

"""
Determinism controls for eval runs.

Two runs of `python -m backend.eval.runner --case X --deterministic` must
produce bit-identical verdicts. That's the Phase-5 acceptance check.

What we pin:
  * Python's `random` module (seeded per-call site via `seeded_random`)
  * The LLM router's effective temperature (forced to 0.0 via `DeterministicRouterWrapper`)
  * The mock LLM router's internal state (seeded)
  * timestamps — we replace real `time.time()` with a monotonic counter in
    deterministic mode so created_ts / round ts fields don't float

What we do NOT control:
  * Real cloud LLM jitter (different models sometimes return different
    tokenizations even at temperature=0). Deterministic mode therefore
    pairs with `--mock-llm` for CI; live runs can still be deterministic
    with a single-model server + temp=0, but byte-identical guarantees
    end at the wire.
"""

from __future__ import annotations

import contextlib
import random
import threading
import time
from dataclasses import dataclass
from typing import Iterator, Optional

# Bump when the eval math, verdict extraction, or mock LLM tables change.
# CI compares this to the determinism fixture to catch silent drift.
DETERMINISTIC_VERSION = 1


@dataclass
class DeterministicClock:
    """Monotonic counter replacing wall-clock time in deterministic runs."""
    start: float = 1_700_000_000.0  # 2023-11-14; arbitrary but fixed
    step: float = 1.0
    _t: float = 0.0

    def now(self) -> float:
        self._t += self.step
        return self.start + self._t

    def reset(self) -> None:
        self._t = 0.0


_ACTIVE_CLOCK: Optional[DeterministicClock] = None
_CLOCK_LOCK = threading.Lock()


def now_ts() -> float:
    """Return either the pinned deterministic clock (inside a deterministic
    block) or real wall-clock. Callers that need reproducible timestamps
    should route through this helper instead of `time.time()`."""
    with _CLOCK_LOCK:
        if _ACTIVE_CLOCK is not None:
            return _ACTIVE_CLOCK.now()
    return time.time()


@contextlib.contextmanager
def deterministic_run(seed: int = 1234) -> Iterator[int]:
    """Context manager that pins:
         * the global `random` module,
         * the deterministic clock (now_ts),
       so anything routing through `now_ts()` returns a reproducible sequence.

    Returns the seed so the caller can pass it to per-component RNGs
    (PersonaGenerator, population mixer, etc.).
    """
    global _ACTIVE_CLOCK
    # Seed Python's global RNG; many callers use random.Random() directly,
    # but any uses of the module-level `random.shuffle` / `random.random`
    # will also be stable.
    state = random.getstate()
    random.seed(seed)

    clock = DeterministicClock()
    with _CLOCK_LOCK:
        prev_clock = _ACTIVE_CLOCK
        _ACTIVE_CLOCK = clock

    try:
        yield seed
    finally:
        with _CLOCK_LOCK:
            _ACTIVE_CLOCK = prev_clock
        random.setstate(state)


def seeded_random(seed: int) -> random.Random:
    """Return a fresh `random.Random` with the given seed. Prefer this over
    touching the global RNG; it composes better with concurrent code."""
    return random.Random(seed)

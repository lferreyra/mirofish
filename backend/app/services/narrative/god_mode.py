"""God Mode intervention handlers.

All handlers mutate on-disk JSON under narrative/ and return the result.
Each intervention is logged to world_state.event_log for auditability.
"""
from typing import Optional

from app.services.narrative.story_store import StoryStore
from app.services.narrative.world_state import WorldStateStore


def _current_round(sim_dir: str) -> int:
    """Return the 'current' round: last translated beat's round + 1, or 1."""
    beats = StoryStore(sim_dir).get_all_beats()
    if not beats:
        return 1
    return beats[-1].get("round", 0) + 1


def inject_event(sim_dir: str, description: str, round_num: Optional[int] = None) -> dict:
    """Append a user-described event to the world event log."""
    world = WorldStateStore(sim_dir)
    round_val = round_num if round_num is not None else _current_round(sim_dir)
    return world.append_event({
        "type": "god_mode_injection",
        "description": description,
        "round": round_val,
    })

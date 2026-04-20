"""Reads OASIS actions.jsonl and translates rounds into story prose.

The translator is stateless about which round comes next — callers maintain
the file offset via StoryStore. Each call to `read_actions_for_round` reads
from the saved offset until a matching `round_end` event is seen (or EOF).
"""
import os
import json
from typing import List, Tuple


def read_actions_for_round(
    jsonl_path: str, start_offset: int, target_round: int
) -> Tuple[List[dict], int]:
    """Read all agent actions for `target_round` starting at `start_offset`.

    Returns:
        (actions, new_offset): list of action dicts and the file position to
        resume from on the next read. If the target round hasn't completed yet
        (no matching `round_end` event), new_offset is advanced to EOF so the
        next call picks up where we left off.
    """
    if not os.path.exists(jsonl_path):
        return [], start_offset

    actions: List[dict] = []
    new_offset = start_offset

    with open(jsonl_path, "r", encoding="utf-8") as f:
        f.seek(start_offset)
        while True:
            line = f.readline()
            if not line:
                break
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                # Skip malformed lines but keep advancing
                new_offset = f.tell()
                continue

            # Round-end event for our target marks the boundary
            if entry.get("event_type") == "round_end" and entry.get("round") == target_round:
                new_offset = f.tell()
                break

            # Skip other event types (simulation_start, simulation_end, etc.)
            if "event_type" in entry:
                new_offset = f.tell()
                continue

            # Skip actions from other rounds
            if entry.get("round") != target_round:
                new_offset = f.tell()
                continue

            actions.append(entry)
            new_offset = f.tell()

    return actions, new_offset

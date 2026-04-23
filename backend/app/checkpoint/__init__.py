"""
Simulation checkpoint / restore.

A checkpoint captures everything needed to resume a simulation from the exact
round boundary it was taken at:

    round_num              - the last completed round
    action_log_offset      - byte offset into the subprocess's actions.jsonl
    oasis_state            - opaque blob returned by the OASIS platform
    agent_memories         - per-agent observations + reflections (via
                             MemoryManager.list_*)
    public_timeline        - public:<sim>:timeline namespace contents
    config                 - the SimulationParameters that produced this run

Archive format: `.tar.zst` so the operator can inspect contents with standard
tools (`zstd -d ... -c | tar -tv`). Compression is fast enough for large
memory dumps; falls back to `.tar.gz` if `zstandard` isn't installed.
"""

from .archiver import restore_checkpoint, save_checkpoint
from .serializer import CheckpointData, collect_checkpoint, restore_into

__all__ = [
    "CheckpointData",
    "collect_checkpoint",
    "restore_into",
    "save_checkpoint",
    "restore_checkpoint",
]

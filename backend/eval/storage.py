"""
Simple JSON-Lines store for eval run results.

One line per run, so the dashboard can tail the file without parsing a
single giant JSON blob. Lives under `backend/data/eval_results.jsonl` by
default; override with the `EVAL_RESULTS_PATH` env var.
"""

from __future__ import annotations

import json
import os
import threading
import time
from typing import Any, Dict, Iterator, List, Optional


def default_results_path() -> str:
    override = os.environ.get("EVAL_RESULTS_PATH")
    if override:
        return override
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(here, "..", "data", "eval_results.jsonl"))


_LOCK = threading.Lock()


def append_result(entry: Dict[str, Any], *, path: Optional[str] = None) -> str:
    """Append a run entry to the results file. Returns the path written to.

    Adds `recorded_ts` if missing so the dashboard can plot over time.
    """
    path = path or default_results_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    entry = dict(entry)
    entry.setdefault("recorded_ts", time.time())
    with _LOCK:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return path


def read_results(
    *,
    path: Optional[str] = None,
    limit: Optional[int] = None,
    case: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return the most recent `limit` entries, optionally filtered by case."""
    path = path or default_results_path()
    if not os.path.exists(path):
        return []
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if case is not None and row.get("case") != case:
                continue
            rows.append(row)
    rows.sort(key=lambda r: r.get("recorded_ts", 0.0), reverse=True)
    if limit is not None:
        rows = rows[:limit]
    return rows

"""
Per-API-key usage counters.

Two semantics supported:
  * `check_and_debit(key, tokens=..., usd=...)` — atomic "do we have budget"
    + "consume budget". Raises `QuotaExceeded` when it doesn't. This is the
    call site the middleware uses on every authenticated request.
  * `preview(key, tokens=..., usd=...)` — returns the would-be post-debit
    values without actually debiting. Used by the cost estimator to decide
    whether to prompt for user approval.

State lives in a SQLite table so it survives restarts. A single lock
serializes writes; the table is small (one row per key) so this is cheap.
"""

from __future__ import annotations

import os
import sqlite3
import threading
import time
from dataclasses import dataclass
from typing import Optional, Tuple

from .keys import ApiKey


_SCHEMA = """
CREATE TABLE IF NOT EXISTS api_key_usage (
    key_id         TEXT PRIMARY KEY,
    tokens_used    INTEGER NOT NULL DEFAULT 0,
    usd_used       REAL NOT NULL DEFAULT 0.0,
    window_start   REAL NOT NULL,
    last_debit_ts  REAL
);
"""


class QuotaExceeded(Exception):
    """Raised when a debit would push a key past its configured quota."""

    def __init__(self, message: str, *, key_id: str, reason: str,
                 limit: float, used: float, requested: float):
        super().__init__(message)
        self.key_id = key_id
        self.reason = reason   # "tokens" | "usd"
        self.limit = limit
        self.used = used
        self.requested = requested

    def to_dict(self) -> dict:
        return {
            "error": "quota_exceeded",
            "key_id": self.key_id,
            "reason": self.reason,
            "limit": self.limit,
            "used": self.used,
            "requested": self.requested,
            "message": str(self),
        }


@dataclass
class UsageSnapshot:
    key_id: str
    tokens_used: int
    usd_used: float
    window_start: float


class QuotaTracker:
    """SQLite-backed per-key usage tracker. Thread-safe."""

    def __init__(self, db_path: str, *, window_seconds: int = 30 * 24 * 3600):
        """`window_seconds` is the rolling window for quotas. Default 30 days.
        When a window expires, counters reset on the next debit attempt."""
        self.db_path = db_path
        self.window_seconds = window_seconds
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._tls = threading.local()
        self._write_lock = threading.Lock()
        with self._connect() as conn:
            conn.executescript(_SCHEMA)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = getattr(self._tls, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=10)
            conn.row_factory = sqlite3.Row
            self._tls.conn = conn
        return conn

    # ---- public API --------------------------------------------------------
    def usage_for(self, key: ApiKey) -> UsageSnapshot:
        """Return current usage for a key — zeros when no debits yet recorded."""
        row = self._connect().execute(
            "SELECT * FROM api_key_usage WHERE key_id = ?", (key.key_id,),
        ).fetchone()
        if row is None:
            return UsageSnapshot(
                key_id=key.key_id, tokens_used=0, usd_used=0.0,
                window_start=time.time(),
            )
        return self._maybe_reset_window(row)

    def check_and_debit(self, key: ApiKey, *, tokens: int = 0, usd: float = 0.0) -> UsageSnapshot:
        """Atomic quota enforcement: raises `QuotaExceeded` if the requested
        tokens / usd would exceed the configured caps, otherwise debits and
        returns the new usage snapshot."""
        tokens = max(0, int(tokens))
        usd = max(0.0, float(usd))
        with self._write_lock:
            snap = self.usage_for(key)
            if key.quota_tokens > 0 and snap.tokens_used + tokens > key.quota_tokens:
                raise QuotaExceeded(
                    f"token quota exceeded for key {key.key_id}",
                    key_id=key.key_id, reason="tokens",
                    limit=key.quota_tokens, used=snap.tokens_used, requested=tokens,
                )
            if key.quota_usd > 0.0 and snap.usd_used + usd > key.quota_usd:
                raise QuotaExceeded(
                    f"usd quota exceeded for key {key.key_id}",
                    key_id=key.key_id, reason="usd",
                    limit=key.quota_usd, used=snap.usd_used, requested=usd,
                )
            new_tokens = snap.tokens_used + tokens
            new_usd = snap.usd_used + usd
            now = time.time()
            self._upsert(key.key_id, new_tokens, new_usd, snap.window_start, now)
            return UsageSnapshot(
                key_id=key.key_id, tokens_used=new_tokens, usd_used=new_usd,
                window_start=snap.window_start,
            )

    def preview(self, key: ApiKey, *, tokens: int = 0, usd: float = 0.0) -> Tuple[bool, str, UsageSnapshot]:
        """Non-mutating quota check. Returns (would_allow, reason_if_not, snapshot)."""
        snap = self.usage_for(key)
        if key.quota_tokens > 0 and snap.tokens_used + tokens > key.quota_tokens:
            return False, "tokens", snap
        if key.quota_usd > 0.0 and snap.usd_used + usd > key.quota_usd:
            return False, "usd", snap
        return True, "", snap

    def reset(self, key_id: str) -> None:
        """Admin-only: zero the counters for one key."""
        with self._write_lock:
            self._upsert(key_id, 0, 0.0, time.time(), time.time())

    # ---- internals ---------------------------------------------------------
    def _upsert(self, key_id: str, tokens: int, usd: float,
                window_start: float, now: float) -> None:
        conn = self._connect()
        conn.execute(
            "INSERT INTO api_key_usage (key_id, tokens_used, usd_used, window_start, last_debit_ts) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(key_id) DO UPDATE SET tokens_used=excluded.tokens_used, "
            "usd_used=excluded.usd_used, window_start=excluded.window_start, "
            "last_debit_ts=excluded.last_debit_ts",
            (key_id, tokens, usd, window_start, now),
        )
        conn.commit()

    def _maybe_reset_window(self, row: sqlite3.Row) -> UsageSnapshot:
        """If the rolling window has expired, treat counters as zero.

        Reset is lazy: we don't write the new window_start until the next
        `check_and_debit` call, which keeps reads pure."""
        start = float(row["window_start"])
        if time.time() - start > self.window_seconds:
            return UsageSnapshot(
                key_id=row["key_id"], tokens_used=0, usd_used=0.0,
                window_start=time.time(),
            )
        return UsageSnapshot(
            key_id=row["key_id"],
            tokens_used=int(row["tokens_used"] or 0),
            usd_used=float(row["usd_used"] or 0.0),
            window_start=start,
        )


# --------------------------------------------------------------------------
# singleton
# --------------------------------------------------------------------------

_GLOBAL: Optional[QuotaTracker] = None
_LOCK = threading.Lock()


def _default_db_path() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(here, "..", "..", "data", "auth_usage.db"))


def get_tracker(db_path: Optional[str] = None) -> QuotaTracker:
    global _GLOBAL
    if _GLOBAL is not None and db_path is None:
        return _GLOBAL
    with _LOCK:
        if _GLOBAL is None or db_path is not None:
            _GLOBAL = QuotaTracker(
                db_path or os.environ.get("QUOTA_DB_PATH") or _default_db_path(),
            )
    return _GLOBAL


def reset_for_tests(db_path: Optional[str] = None) -> QuotaTracker:
    global _GLOBAL
    with _LOCK:
        _GLOBAL = QuotaTracker(db_path or _default_db_path())
    return _GLOBAL

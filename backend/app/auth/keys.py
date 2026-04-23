"""
SQLite-backed API key store.

Wire format:
    mf_<key_id>_<secret>
    e.g.  mf_6f3a91cb_sAt5...long random suffix...

`key_id` is 8 hex chars (fits in a log line); the secret is 40 chars of
urlsafe base64. Only the secret's SHA-256 hash is stored — the plaintext is
returned *once* at issue time and never again.
"""

from __future__ import annotations

import base64
import hashlib
import os
import secrets
import sqlite3
import threading
import time
from dataclasses import dataclass
from typing import List, Optional


_SCHEMA = """
CREATE TABLE IF NOT EXISTS api_keys (
    key_id         TEXT PRIMARY KEY,
    secret_hash    TEXT NOT NULL,
    owner          TEXT NOT NULL,
    created_ts     REAL NOT NULL,
    revoked_ts     REAL,
    quota_tokens   INTEGER NOT NULL DEFAULT 0,
    quota_usd      REAL NOT NULL DEFAULT 0.0,
    note           TEXT
);
CREATE INDEX IF NOT EXISTS idx_api_keys_owner ON api_keys(owner);
"""


@dataclass
class ApiKey:
    """In-memory view of a row. `secret_hash` is never returned to clients."""
    key_id: str
    owner: str
    created_ts: float
    secret_hash: str = ""
    revoked_ts: Optional[float] = None
    quota_tokens: int = 0         # 0 = unlimited
    quota_usd: float = 0.0        # 0.0 = unlimited
    note: Optional[str] = None

    @property
    def is_active(self) -> bool:
        return self.revoked_ts is None

    def to_dict(self, *, include_secret: bool = False) -> dict:
        """Public-safe dict. `include_secret=False` strips the hash."""
        d = {
            "key_id": self.key_id,
            "owner": self.owner,
            "created_ts": self.created_ts,
            "revoked_ts": self.revoked_ts,
            "quota_tokens": self.quota_tokens,
            "quota_usd": self.quota_usd,
            "note": self.note,
            "is_active": self.is_active,
        }
        if include_secret:
            d["secret_hash"] = self.secret_hash
        return d


class ApiKeyStore:
    """One store per process. Thread-safe."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._tls = threading.local()
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

    # ------------------------------------------------------------------ API
    def issue(
        self,
        *,
        owner: str,
        quota_tokens: int = 0,
        quota_usd: float = 0.0,
        note: Optional[str] = None,
    ) -> tuple[str, ApiKey]:
        """Return (plaintext_key, ApiKey). The plaintext is NOT persisted."""
        key_id = secrets.token_hex(4)                     # 8 hex chars
        secret_raw = secrets.token_urlsafe(30)            # ~40 chars
        secret_hash = _hash(secret_raw)
        created = time.time()
        plaintext = f"mf_{key_id}_{secret_raw}"
        conn = self._connect()
        conn.execute(
            "INSERT INTO api_keys (key_id, secret_hash, owner, created_ts, "
            "quota_tokens, quota_usd, note) VALUES (?,?,?,?,?,?,?)",
            (key_id, secret_hash, owner, created, quota_tokens, quota_usd, note),
        )
        conn.commit()
        return plaintext, ApiKey(
            key_id=key_id, owner=owner, created_ts=created, secret_hash=secret_hash,
            quota_tokens=quota_tokens, quota_usd=quota_usd, note=note,
        )

    def verify(self, plaintext: str) -> Optional[ApiKey]:
        """Return the ApiKey when the plaintext is valid + not revoked."""
        parts = plaintext.split("_", 2) if plaintext else []
        if len(parts) != 3 or parts[0] != "mf":
            return None
        key_id, secret_raw = parts[1], parts[2]
        conn = self._connect()
        row = conn.execute(
            "SELECT * FROM api_keys WHERE key_id = ? AND revoked_ts IS NULL",
            (key_id,),
        ).fetchone()
        if row is None:
            return None
        if not _constant_time_eq(row["secret_hash"], _hash(secret_raw)):
            return None
        return _row_to_key(row)

    def revoke(self, key_id: str) -> bool:
        conn = self._connect()
        cur = conn.execute(
            "UPDATE api_keys SET revoked_ts = ? WHERE key_id = ? AND revoked_ts IS NULL",
            (time.time(), key_id),
        )
        conn.commit()
        return cur.rowcount > 0

    def list_keys(self, *, owner: Optional[str] = None,
                  include_revoked: bool = False) -> List[ApiKey]:
        conn = self._connect()
        clauses = []
        params: list = []
        if owner is not None:
            clauses.append("owner = ?")
            params.append(owner)
        if not include_revoked:
            clauses.append("revoked_ts IS NULL")
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = conn.execute(
            f"SELECT * FROM api_keys {where} ORDER BY created_ts DESC", params,
        ).fetchall()
        return [_row_to_key(r) for r in rows]


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _hash(secret_raw: str) -> str:
    return hashlib.sha256(secret_raw.encode("utf-8")).hexdigest()


def _constant_time_eq(a: str, b: str) -> bool:
    # Python's hmac.compare_digest would work too; stdlib-only is fine here.
    if len(a) != len(b):
        return False
    result = 0
    for x, y in zip(a, b):
        result |= ord(x) ^ ord(y)
    return result == 0


def _row_to_key(row: sqlite3.Row) -> ApiKey:
    return ApiKey(
        key_id=row["key_id"], owner=row["owner"], created_ts=float(row["created_ts"]),
        secret_hash=row["secret_hash"], revoked_ts=row["revoked_ts"],
        quota_tokens=int(row["quota_tokens"] or 0),
        quota_usd=float(row["quota_usd"] or 0.0),
        note=row["note"],
    )


# --------------------------------------------------------------------------
# module-level singleton
# --------------------------------------------------------------------------

_GLOBAL: Optional[ApiKeyStore] = None
_LOCK = threading.Lock()


def _default_db_path() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(here, "..", "..", "data", "auth.db"))


def get_store(db_path: Optional[str] = None) -> ApiKeyStore:
    global _GLOBAL
    if _GLOBAL is not None and db_path is None:
        return _GLOBAL
    with _LOCK:
        if _GLOBAL is None or db_path is not None:
            _GLOBAL = ApiKeyStore(
                db_path or os.environ.get("AUTH_DB_PATH") or _default_db_path()
            )
    return _GLOBAL


def issue_key(**kwargs) -> tuple[str, ApiKey]:
    return get_store().issue(**kwargs)


def verify_key(plaintext: str) -> Optional[ApiKey]:
    return get_store().verify(plaintext)


def revoke_key(key_id: str) -> bool:
    return get_store().revoke(key_id)


def reset_for_tests(db_path: Optional[str] = None) -> ApiKeyStore:
    global _GLOBAL
    with _LOCK:
        _GLOBAL = ApiKeyStore(db_path or _default_db_path())
    return _GLOBAL

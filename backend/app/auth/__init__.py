"""
API-key auth + per-key quotas for the Phase-6 deployable surface.

    keys.py       -- SQLite-backed ApiKey model + issue/verify/revoke.
                     Plaintext secrets are hashed at rest.
    quotas.py     -- Per-key rolling-window usage counters. Enforcement is
                     "pre-check + debit" so a midflight simulation can't
                     silently overrun.
    middleware.py -- Flask `@require_api_key` decorator. Honors
                     ALLOW_ANONYMOUS_API=true for demo deployments.
"""

from .keys import ApiKey, ApiKeyStore, get_store, issue_key, revoke_key, verify_key
from .middleware import require_api_key
from .quotas import QuotaExceeded, QuotaTracker, get_tracker

__all__ = [
    "ApiKey",
    "ApiKeyStore",
    "QuotaExceeded",
    "QuotaTracker",
    "get_store",
    "get_tracker",
    "issue_key",
    "require_api_key",
    "revoke_key",
    "verify_key",
]

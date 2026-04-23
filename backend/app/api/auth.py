"""
/api/auth/keys — issue, list, revoke API keys.

Admin-only endpoints by default: require the `X-MiroFish-Admin-Token` header
to match `ADMIN_TOKEN` env. In demo deployments where `ALLOW_ANONYMOUS_API`
is on, the admin token can still gate key management even when other
endpoints accept anonymous traffic.

    POST   /api/auth/keys
        body: {"owner": "...", "quota_tokens": 0, "quota_usd": 0.0, "note": "..."}
        -> {"plaintext": "mf_xxx_yyy", "key": {...}}
           plaintext is returned ONCE; never re-retrievable.

    GET    /api/auth/keys[?owner=...&include_revoked=true]
        -> {"keys": [...]}   (no secrets — hashes are stripped)

    DELETE /api/auth/keys/<key_id>
        -> {"revoked": bool}

    GET    /api/auth/quota
        -> {"key_id": ..., "tokens_used": ..., "usd_used": ...,
            "quota_tokens": ..., "quota_usd": ...}
           requires a regular API key (not admin).
"""

from __future__ import annotations

import functools
import os

from flask import Blueprint, g, jsonify, request

from ..auth import (
    get_store,
    get_tracker,
    issue_key,
    require_api_key,
    revoke_key,
)


auth_bp = Blueprint("auth", __name__)


def _require_admin(view):
    @functools.wraps(view)
    def wrapper(*args, **kwargs):
        expected = os.environ.get("ADMIN_TOKEN")
        if not expected:
            return jsonify({
                "error": "admin_token_not_configured",
                "message": "set ADMIN_TOKEN env before using /api/auth/keys",
            }), 503
        supplied = request.headers.get("X-MiroFish-Admin-Token", "").strip()
        if supplied != expected:
            return jsonify({"error": "admin_token_invalid"}), 403
        return view(*args, **kwargs)
    return wrapper


@auth_bp.route("/keys", methods=["POST"])
@_require_admin
def create_key():
    body = request.get_json(silent=True) or {}
    owner = (body.get("owner") or "").strip()
    if not owner:
        return jsonify({"error": "owner_required"}), 400
    quota_tokens = int(body.get("quota_tokens", 0))
    quota_usd = float(body.get("quota_usd", 0.0))
    note = body.get("note")

    plaintext, key = issue_key(
        owner=owner, quota_tokens=quota_tokens,
        quota_usd=quota_usd, note=note,
    )
    # The plaintext is shown ONCE. Make that loud in the response body.
    return jsonify({
        "plaintext": plaintext,
        "plaintext_warning": (
            "Store this now — the server keeps only the hash and cannot "
            "re-issue it. Lose it and you must revoke + re-create the key."
        ),
        "key": key.to_dict(include_secret=False),
    }), 201


@auth_bp.route("/keys", methods=["GET"])
@_require_admin
def list_keys():
    owner = request.args.get("owner")
    include_revoked = (request.args.get("include_revoked", "false").lower()
                       in ("1", "true", "yes"))
    keys = get_store().list_keys(owner=owner, include_revoked=include_revoked)
    return jsonify({"keys": [k.to_dict() for k in keys]})


@auth_bp.route("/keys/<key_id>", methods=["DELETE"])
@_require_admin
def delete_key(key_id: str):
    revoked = revoke_key(key_id)
    status = 200 if revoked else 404
    return jsonify({"revoked": revoked, "key_id": key_id}), status


@auth_bp.route("/quota", methods=["GET"])
@require_api_key
def current_quota():
    """Return the authenticated key's current usage. Used by the frontend
    to show a quota meter."""
    key = g.api_key
    if key is None:
        return jsonify({"anonymous": True})
    usage = get_tracker().usage_for(key)
    return jsonify({
        "key_id": key.key_id,
        "owner": key.owner,
        "tokens_used": usage.tokens_used,
        "usd_used": usage.usd_used,
        "quota_tokens": key.quota_tokens,
        "quota_usd": key.quota_usd,
    })

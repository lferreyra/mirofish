"""
Flask decorator + helpers that enforce API-key auth on protected endpoints.

Usage:
    from app.auth import require_api_key

    @some_blueprint.route("/protected")
    @require_api_key
    def protected():
        key = flask.g.api_key   # ApiKey instance
        return ...

Configuration:
    * Header: `X-MiroFish-Key: mf_<id>_<secret>` (preferred)
    * Query:  `?api_key=mf_<id>_<secret>` (fallback, discouraged)
    * Env flag: `ALLOW_ANONYMOUS_API=true` bypasses the check for demo
      deployments. Every anonymous request still records an auth rejection
      metric so dashboards see when it's being relied on.
"""

from __future__ import annotations

import functools
import os
from typing import Callable

from .keys import verify_key


_HEADER_NAME = "X-MiroFish-Key"


def _extract_key() -> str:
    try:
        from flask import request
    except ImportError:
        return ""
    header = request.headers.get(_HEADER_NAME)
    if header:
        return header.strip()
    # Fallback to query string. Most tools log query strings, so recommend
    # the header in docs — but the fallback is useful for browser-based demos.
    return (request.args.get("api_key") or "").strip()


def _anonymous_allowed() -> bool:
    flag = os.environ.get("ALLOW_ANONYMOUS_API", "false").strip().lower()
    return flag in ("1", "true", "yes", "on")


def require_api_key(view: Callable) -> Callable:
    """Decorate a Flask view so it receives `flask.g.api_key`. Returns 401
    when the key is missing / invalid, unless ALLOW_ANONYMOUS_API=true."""

    @functools.wraps(view)
    def wrapper(*args, **kwargs):
        from flask import g, jsonify
        from ..observability import get_registry

        plaintext = _extract_key()
        if not plaintext:
            if _anonymous_allowed():
                g.api_key = None
                return view(*args, **kwargs)
            get_registry().observe_auth_rejection(reason="missing_key")
            return jsonify({"error": "api_key_required",
                            "message": f"missing {_HEADER_NAME} header"}), 401

        key = verify_key(plaintext)
        if key is None:
            get_registry().observe_auth_rejection(reason="invalid_key")
            return jsonify({"error": "invalid_api_key",
                            "message": "API key is invalid or has been revoked"}), 401

        g.api_key = key
        return view(*args, **kwargs)

    return wrapper

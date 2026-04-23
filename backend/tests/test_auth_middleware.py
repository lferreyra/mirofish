"""Tests for the Flask `@require_api_key` decorator."""

import pytest
from flask import Flask, g, jsonify

from app.auth import keys as keys_module
from app.auth.middleware import require_api_key
from app.auth.keys import ApiKeyStore


@pytest.fixture
def app(tmp_path, monkeypatch):
    """Fresh Flask app + isolated key store per test."""
    # Point the global key store at a per-test SQLite file
    db = tmp_path / "auth.db"
    monkeypatch.setenv("AUTH_DB_PATH", str(db))
    keys_module.reset_for_tests(str(db))

    app = Flask(__name__)
    app.testing = True

    @app.route("/protected")
    @require_api_key
    def protected():
        return jsonify({"owner": g.api_key.owner if g.api_key else None})

    return app


def test_missing_header_returns_401(app, monkeypatch):
    monkeypatch.delenv("ALLOW_ANONYMOUS_API", raising=False)
    client = app.test_client()
    r = client.get("/protected")
    assert r.status_code == 401
    assert r.json["error"] == "api_key_required"


def test_valid_key_is_accepted(app):
    plaintext, _ = keys_module.get_store().issue(owner="alice")
    client = app.test_client()
    r = client.get("/protected", headers={"X-MiroFish-Key": plaintext})
    assert r.status_code == 200
    assert r.json["owner"] == "alice"


def test_invalid_key_returns_401(app):
    client = app.test_client()
    r = client.get("/protected", headers={"X-MiroFish-Key": "mf_fake_bogus"})
    assert r.status_code == 401
    assert r.json["error"] == "invalid_api_key"


def test_revoked_key_returns_401(app):
    plaintext, key = keys_module.get_store().issue(owner="bob")
    keys_module.get_store().revoke(key.key_id)
    client = app.test_client()
    r = client.get("/protected", headers={"X-MiroFish-Key": plaintext})
    assert r.status_code == 401


def test_anonymous_allowed_flag_bypasses_auth(app, monkeypatch):
    monkeypatch.setenv("ALLOW_ANONYMOUS_API", "true")
    client = app.test_client()
    r = client.get("/protected")
    assert r.status_code == 200
    # Anonymous request -> g.api_key is None
    assert r.json["owner"] is None


def test_query_string_fallback_is_accepted(app):
    plaintext, _ = keys_module.get_store().issue(owner="alice")
    client = app.test_client()
    r = client.get(f"/protected?api_key={plaintext}")
    assert r.status_code == 200

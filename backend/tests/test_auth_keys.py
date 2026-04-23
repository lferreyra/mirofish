"""Tests for API-key issue / verify / revoke."""

import pytest

from app.auth.keys import ApiKeyStore


@pytest.fixture
def store(tmp_path):
    return ApiKeyStore(str(tmp_path / "auth.db"))


def test_issue_returns_plaintext_only_once(store):
    plaintext, key = store.issue(owner="alice")
    assert plaintext.startswith("mf_")
    assert key.key_id
    assert key.owner == "alice"
    # Plaintext is NOT stored — only the hash
    assert key.secret_hash != plaintext


def test_verify_roundtrip(store):
    plaintext, key = store.issue(owner="alice")
    got = store.verify(plaintext)
    assert got is not None
    assert got.key_id == key.key_id
    assert got.owner == "alice"


def test_verify_rejects_garbage(store):
    assert store.verify("not-a-key") is None
    assert store.verify("mf_whatever") is None
    assert store.verify("") is None
    assert store.verify(None) is None


def test_verify_rejects_tampered_secret(store):
    plaintext, _ = store.issue(owner="alice")
    # Flip the last character — hash will no longer match
    tampered = plaintext[:-1] + ("a" if plaintext[-1] != "a" else "b")
    assert store.verify(tampered) is None


def test_revoke_invalidates_subsequent_verify(store):
    plaintext, key = store.issue(owner="alice")
    assert store.verify(plaintext) is not None
    assert store.revoke(key.key_id) is True
    assert store.verify(plaintext) is None
    # Double revoke returns False
    assert store.revoke(key.key_id) is False


def test_list_keys_filters_by_owner(store):
    store.issue(owner="alice")
    store.issue(owner="bob")
    store.issue(owner="alice", note="second")
    alice_keys = store.list_keys(owner="alice")
    bob_keys = store.list_keys(owner="bob")
    assert len(alice_keys) == 2
    assert len(bob_keys) == 1


def test_list_keys_excludes_revoked_by_default(store):
    _, key1 = store.issue(owner="alice")
    store.issue(owner="alice")
    store.revoke(key1.key_id)
    assert len(store.list_keys(owner="alice")) == 1
    assert len(store.list_keys(owner="alice", include_revoked=True)) == 2


def test_to_dict_strips_secret_by_default(store):
    _, key = store.issue(owner="alice")
    public_view = key.to_dict()
    assert "secret_hash" not in public_view
    private_view = key.to_dict(include_secret=True)
    assert "secret_hash" in private_view


def test_quotas_stored_on_key(store):
    _, key = store.issue(owner="alice", quota_tokens=100_000, quota_usd=5.0)
    assert key.quota_tokens == 100_000
    assert key.quota_usd == 5.0
    # Roundtrip via verify
    plaintext, _ = store.issue(owner="bob", quota_tokens=0, quota_usd=0.0)
    retrieved = store.verify(plaintext)
    assert retrieved.quota_tokens == 0   # 0 = unlimited

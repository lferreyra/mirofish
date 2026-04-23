"""Tests for per-API-key quota enforcement."""

import pytest

from app.auth.keys import ApiKey
from app.auth.quotas import QuotaExceeded, QuotaTracker


@pytest.fixture
def tracker(tmp_path):
    return QuotaTracker(str(tmp_path / "usage.db"))


def _key(**overrides):
    defaults = {"key_id": "k1", "owner": "alice", "created_ts": 0.0}
    defaults.update(overrides)
    return ApiKey(**defaults)


def test_unlimited_key_never_raises(tracker):
    key = _key(quota_tokens=0, quota_usd=0.0)
    # Debit a huge amount — zero-cap should allow it
    snap = tracker.check_and_debit(key, tokens=1_000_000_000, usd=99999.0)
    assert snap.tokens_used == 1_000_000_000


def test_token_quota_enforced(tracker):
    key = _key(quota_tokens=1000)
    tracker.check_and_debit(key, tokens=700)
    # Second debit would push over the cap
    with pytest.raises(QuotaExceeded) as exc_info:
        tracker.check_and_debit(key, tokens=500)
    assert exc_info.value.reason == "tokens"
    assert exc_info.value.limit == 1000
    assert exc_info.value.used == 700


def test_usd_quota_enforced(tracker):
    key = _key(quota_usd=5.0)
    tracker.check_and_debit(key, usd=3.0)
    with pytest.raises(QuotaExceeded):
        tracker.check_and_debit(key, usd=2.5)


def test_partial_debit_still_applied_on_success(tracker):
    """Successful debit updates tokens AND usd atomically."""
    key = _key(quota_tokens=10_000, quota_usd=10.0)
    tracker.check_and_debit(key, tokens=500, usd=0.25)
    snap = tracker.usage_for(key)
    assert snap.tokens_used == 500
    assert snap.usd_used == pytest.approx(0.25)


def test_failed_debit_does_not_apply(tracker):
    """When a check fails, NOTHING should be debited — not even the partial
    field that fit."""
    key = _key(quota_tokens=1000, quota_usd=1.0)
    tracker.check_and_debit(key, tokens=500, usd=0.5)
    with pytest.raises(QuotaExceeded):
        # The usd component fits (0.4 more), but tokens don't (700 > 500 remaining).
        tracker.check_and_debit(key, tokens=700, usd=0.4)
    snap = tracker.usage_for(key)
    assert snap.tokens_used == 500
    assert snap.usd_used == pytest.approx(0.5)


def test_preview_does_not_mutate(tracker):
    key = _key(quota_tokens=1000)
    tracker.check_and_debit(key, tokens=800)
    allowed, reason, _ = tracker.preview(key, tokens=500)
    assert not allowed
    assert reason == "tokens"
    # Preview must NOT have debited — counter stays at 800
    assert tracker.usage_for(key).tokens_used == 800


def test_reset_zeroes_counters(tracker):
    key = _key(quota_tokens=1000)
    tracker.check_and_debit(key, tokens=500)
    tracker.reset(key.key_id)
    assert tracker.usage_for(key).tokens_used == 0


def test_usage_for_fresh_key_returns_zeros(tracker):
    snap = tracker.usage_for(_key(key_id="never-seen"))
    assert snap.tokens_used == 0
    assert snap.usd_used == 0.0

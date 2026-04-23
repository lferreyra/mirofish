"""Tests for the deterministic clock + seeded_random helpers."""

import random

from eval.determinism import (
    DETERMINISTIC_VERSION,
    deterministic_run,
    now_ts,
    seeded_random,
)


def test_deterministic_clock_is_monotonic_and_reproducible():
    with deterministic_run(seed=7):
        t1 = now_ts()
        t2 = now_ts()
        t3 = now_ts()
    # Strictly monotonic inside the block
    assert t2 > t1
    assert t3 > t2

    # Same seed twice -> same absolute timestamps
    with deterministic_run(seed=7):
        u1 = now_ts()
    with deterministic_run(seed=7):
        u2 = now_ts()
    assert u1 == u2


def test_now_ts_outside_deterministic_block_returns_wallclock():
    """When no deterministic block is active, now_ts() falls through to time.time()."""
    before = now_ts()
    # Should be close to wall clock — well above the deterministic clock's
    # fixed start of 1700000000.
    assert before > 1700000000.0


def test_global_random_state_is_restored():
    """A deterministic block must not leak its seed state to callers."""
    random.seed(999)
    outer_before = random.random()
    random.seed(999)

    with deterministic_run(seed=1234):
        pass
    # After the block, the global state should be whatever it was before.
    after_same_seed = random.random()
    assert after_same_seed == outer_before


def test_seeded_random_is_isolated():
    """Two seeded_random instances don't share state."""
    a = seeded_random(42)
    b = seeded_random(42)
    for _ in range(5):
        assert a.random() == b.random()


def test_determinism_version_constant_exposed():
    """CI compares this constant against fixtures. It must be an int."""
    assert isinstance(DETERMINISTIC_VERSION, int)
    assert DETERMINISTIC_VERSION >= 1

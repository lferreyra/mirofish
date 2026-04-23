"""Tests for the pure scoring functions."""

import pytest

from eval.scoring import (
    DEFAULT_WEIGHTS,
    Truth,
    Verdict,
    calibration,
    directional_accuracy,
    magnitude_error,
    score_verdict,
)


def _v(direction, magnitude, confidence=0.7):
    return Verdict(direction=direction, magnitude=magnitude, confidence=confidence)


def _t(direction, magnitude):
    return Truth(direction=direction, magnitude=magnitude)


def test_directional_accuracy_matches_on_sign():
    assert directional_accuracy(_v("positive", 0.5), _t("positive", 0.6)) == 1.0
    assert directional_accuracy(_v("negative", 0.5), _t("negative", 0.9)) == 1.0
    assert directional_accuracy(_v("positive", 0.5), _t("negative", 0.9)) == 0.0
    assert directional_accuracy(_v("neutral", 0.0), _t("neutral", 0.1)) == 1.0


def test_directional_accepts_synonyms():
    """Some datasets use 'support'/'oppose' instead of 'positive'/'negative'."""
    assert directional_accuracy(_v("support", 0.5), _t("positive", 0.5)) == 1.0
    assert directional_accuracy(_v("oppose", 0.5), _t("negative", 0.5)) == 1.0


def test_magnitude_error_is_clipped():
    """Two runs with very different magnitudes should produce a high error."""
    assert magnitude_error(_v("positive", 0.1), _t("positive", 0.9)) == pytest.approx(0.8)
    # Bigger-than-1 inputs get clamped
    assert magnitude_error(_v("positive", 2.5), _t("positive", 0.5)) == pytest.approx(0.5)


def test_calibration_penalizes_wrong_direction_with_high_confidence():
    """Being very confident AND wrong = low calibration."""
    v = _v("positive", 0.5, confidence=0.9)  # very confident
    t = _t("negative", 0.5)                   # actually wrong direction
    # outcome=0 (wrong); confidence=0.9 -> calibration = 1 - |0.9 - 0| = 0.1
    assert calibration(v, t) == pytest.approx(0.1)


def test_calibration_rewards_low_confidence_when_wrong():
    """Being right to hedge when you're wrong = good calibration."""
    v = _v("positive", 0.5, confidence=0.1)  # not confident
    t = _t("negative", 0.5)
    assert calibration(v, t) == pytest.approx(0.9)


def test_score_verdict_composite_uses_weights():
    """Composite should equal the weighted sum of the three components."""
    v = _v("positive", 0.5, confidence=0.7)
    t = _t("positive", 0.5)
    s = score_verdict(v, t)
    # directional=1, magnitude_error=0 so (1-mag)=1, calibration = 1 - |0.7 - 1| = 0.7
    # composite = 0.5*1 + 0.3*1 + 0.2*0.7 = 0.94
    assert s.directional == 1.0
    assert s.magnitude_error == pytest.approx(0.0)
    assert s.calibration == pytest.approx(0.7)
    assert s.composite == pytest.approx(0.94)


def test_score_verdict_respects_custom_weights():
    v = _v("positive", 0.0)
    t = _t("positive", 1.0)
    # directional=1, mag_err=1 -> (1-mag)=0, calibration depends on confidence
    custom = {"directional": 1.0, "magnitude": 0.0, "calibration": 0.0}
    s = score_verdict(v, t, weights=custom)
    # Only directional weight matters -> composite = 1.0
    assert s.composite == pytest.approx(1.0)


def test_score_composite_clamped_to_unit_interval():
    """Weights that don't sum to 1 shouldn't produce out-of-range composite."""
    v = _v("positive", 0.5, confidence=1.0)
    t = _t("positive", 0.5)
    s = score_verdict(v, t, weights={"directional": 5.0, "magnitude": 5.0, "calibration": 5.0})
    assert 0.0 <= s.composite <= 1.0

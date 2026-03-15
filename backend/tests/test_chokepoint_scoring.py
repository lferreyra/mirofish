from app.services.chokepoint_scoring import (
    ChokepointCandidate,
    ChokepointSeveritySignals,
    ValueCaptureSignals,
    classify_score,
    score_candidate,
    score_candidate_severity,
    score_candidate_value_capture,
)


def test_score_candidate_returns_two_scores_in_bounds():
    candidate = ChokepointCandidate(
        name="InP Substrates",
        layer="substrate",
        description="Concentrated upstream photonics input",
        severity_signals=ChokepointSeveritySignals(
            supplier_concentration=5,
            qualification_friction=4,
            capacity_lead_time=4,
            geopolitical_exposure=5,
            demand_acceleration=4,
            substitutability_inverse=4,
            pricing_power_evidence=3,
        ),
        value_capture_signals=ValueCaptureSignals(
            pricing_power_realization=3,
            listed_vehicle_purity=4,
            margin_leverage=3,
            balance_sheet_capacity=2,
            scarcity_duration=4,
            competitive_retention=3,
            state_support_independence=4,
        ),
        public_companies=["AXTI", "SMTOY"],
    )

    result = score_candidate(candidate)

    assert 0 <= result.severity.score_0_to_100 <= 100
    assert 0 <= result.value_capture.score_0_to_100 <= 100
    assert result.severity.band in {"critical", "high", "moderate", "emerging", "low"}
    assert result.value_capture.band in {"critical", "high", "moderate", "emerging", "low"}
    assert "InP Substrates" in result.severity.explanation
    assert "InP Substrates" in result.value_capture.explanation


def test_individual_score_functions_work():
    candidate = ChokepointCandidate(
        name="Utility Transformers",
        layer="transmission",
        description="Grid bottleneck candidate",
        severity_signals=ChokepointSeveritySignals(
            supplier_concentration=4,
            qualification_friction=5,
            capacity_lead_time=5,
            geopolitical_exposure=3,
            demand_acceleration=5,
            substitutability_inverse=5,
            pricing_power_evidence=4,
        ),
        value_capture_signals=ValueCaptureSignals(
            pricing_power_realization=4,
            listed_vehicle_purity=3,
            margin_leverage=4,
            balance_sheet_capacity=4,
            scarcity_duration=5,
            competitive_retention=4,
            state_support_independence=5,
        ),
    )

    severity = score_candidate_severity(candidate)
    value_capture = score_candidate_value_capture(candidate)

    assert severity.score_type == "severity"
    assert value_capture.score_type == "value_capture"
    assert severity.score_0_to_100 != value_capture.score_0_to_100


def test_classify_score_bands_are_stable():
    assert classify_score(10) == "low"
    assert classify_score(30) == "emerging"
    assert classify_score(50) == "moderate"
    assert classify_score(70) == "high"
    assert classify_score(85) == "critical"

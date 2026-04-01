"""
리스크 평가 + Kelly Criterion 배팅 사이징
"""

from typing import Optional
from .models import AggregationResult, RiskAssessment


# Kelly 파라미터
KELLY_FRACTION = 0.5    # Half-Kelly (안전 마진)
MAX_BET_FRACTION = 0.15  # 최대 뱅크롤 15%
MIN_EDGE = 0.02          # 최소 2% edge 필요


def assess(
    aggregation: AggregationResult,
    market_odds: Optional[float] = None,
    resolution_date: Optional[str] = None,
) -> RiskAssessment:
    """
    예측 결과의 리스크를 평가하고 Kelly 배팅 사이즈를 계산합니다.

    Args:
        aggregation: 앙상블 합산 결과
        market_odds: 현재 Polymarket 가격 (0.0-1.0)
        resolution_date: 해상도 날짜 (ISO format)
    """
    p = aggregation.calibrated_probability
    confidence = aggregation.confidence
    ci_width = aggregation.ci_upper - aggregation.ci_lower
    ci_width_pct = ci_width * 100

    # Edge 계산
    if market_odds is not None and market_odds > 0:
        edge = p - market_odds
    else:
        edge = 0.0

    # Kelly Criterion
    kelly = _compute_kelly(p, market_odds, confidence)

    # Expected Value (달러당)
    if market_odds is not None and market_odds > 0 and edge > 0:
        ev = edge * (1.0 / market_odds - 1.0)
    else:
        ev = 0.0

    # 리스크 분류
    risk_rating = _classify_risk(ci_width_pct, confidence, resolution_date)

    # 리스크에 따른 Kelly 조정
    risk_multiplier = {
        "safe": 1.0,
        "moderate": 0.7,
        "risky": 0.4,
        "extreme": 0.0,
    }
    adjusted_kelly = kelly * risk_multiplier.get(risk_rating, 0.0)

    # Reasoning
    reasoning = _build_reasoning(p, market_odds, edge, risk_rating, ci_width_pct, confidence)

    return RiskAssessment(
        risk_rating=risk_rating,
        edge=round(edge * 100, 2),  # 퍼센트로
        kelly_fraction=round(kelly, 4),
        recommended_bet=round(adjusted_kelly, 4),
        expected_value=round(ev, 4),
        reasoning=reasoning,
    )


def _compute_kelly(
    probability: float,
    market_odds: Optional[float],
    confidence: float,
) -> float:
    """
    Half-Kelly 계산.

    kelly = edge / (1 - market_odds) / 2
    × confidence 스케일링
    × max 15% cap
    """
    if market_odds is None or market_odds <= 0 or market_odds >= 1:
        return 0.0

    edge = probability - market_odds

    # 최소 edge 미달 → 배팅 안 함
    if edge <= MIN_EDGE:
        return 0.0

    # Kelly fraction
    kelly = edge / (1.0 - market_odds)

    # Half-Kelly
    kelly *= KELLY_FRACTION

    # Confidence 스케일링
    kelly *= (confidence / 100.0)

    # Cap
    kelly = max(0.0, min(kelly, MAX_BET_FRACTION))

    return kelly


def _classify_risk(
    ci_width_pct: float,
    confidence: float,
    resolution_date: Optional[str] = None,
) -> str:
    """
    리스크 분류.

    | Level    | CI 폭   | Confidence | 해상도   |
    |----------|---------|------------|---------|
    | Safe     | < 15%   | > 70%      | 30일+   |
    | Moderate | < 25%   | > 50%      | -       |
    | Risky    | < 40%   | > 30%      | -       |
    | Extreme  | ≥ 40%   | ≤ 30%      | -       |
    """
    # 해상도까지 남은 일수
    days_to_resolution = _days_until(resolution_date)

    if ci_width_pct < 15 and confidence > 70:
        if days_to_resolution is None or days_to_resolution >= 30:
            return "safe"
        # 해상도가 가까우면 한 단계 상향
        return "moderate"

    if ci_width_pct < 25 and confidence > 50:
        return "moderate"

    if ci_width_pct < 40 and confidence > 30:
        return "risky"

    return "extreme"


def _days_until(date_str: Optional[str]) -> Optional[int]:
    """ISO 날짜까지 남은 일수."""
    if not date_str:
        return None
    try:
        from datetime import datetime, date
        target = datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
        delta = (target - date.today()).days
        return max(0, delta)
    except (ValueError, TypeError):
        return None


def _build_reasoning(
    probability: float,
    market_odds: Optional[float],
    edge: float,
    risk_rating: str,
    ci_width_pct: float,
    confidence: float,
) -> str:
    """리스크 평가 이유 텍스트."""
    parts = [f"예측 확률: {probability * 100:.1f}%"]

    if market_odds is not None:
        parts.append(f"시장 가격: {market_odds * 100:.1f}%")
        parts.append(f"Edge: {edge * 100:+.1f}%p")

    parts.append(f"신뢰구간 폭: {ci_width_pct:.1f}%p")
    parts.append(f"신뢰도: {confidence:.1f}%")
    parts.append(f"리스크: {risk_rating}")

    if edge <= MIN_EDGE:
        parts.append("Edge 부족 (2% 미만) → 배팅 비추천")
    elif risk_rating == "extreme":
        parts.append("불확실성 과다 → 배팅 비추천")

    return " | ".join(parts)

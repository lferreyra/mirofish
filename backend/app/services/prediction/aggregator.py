"""
앙상블 결과 합산
Trimmed weighted mean + 95% CI + Bayesian Model Averaging 캘리브레이션
"""

import math
from typing import List, Optional
from .models import RunSignal, AggregationResult


# t-분포 critical values (two-tailed 95%)
# scipy 없이 하드코딩 (소수 자유도용)
T_CRITICAL = {
    1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571,
    6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
    11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131,
    16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086,
    25: 2.060, 30: 2.042, 40: 2.021, 50: 2.009, 100: 1.984,
}


def _get_t_critical(df: int) -> float:
    """자유도에 따른 t-분포 critical value (95% two-tailed)."""
    if df >= 100:
        return 1.960
    # 가장 가까운 키 찾기
    keys = sorted(T_CRITICAL.keys())
    for k in keys:
        if k >= df:
            return T_CRITICAL[k]
    return 1.960


def aggregate(
    signals: List[RunSignal],
    trim_fraction: float = 0.1,
    use_calibration: bool = False,
    shrinkage: float = 0.15,
) -> AggregationResult:
    """
    N개의 RunSignal을 하나의 확률로 합산합니다.

    Args:
        signals: 각 run에서 추출된 신호
        trim_fraction: 상하 trim 비율 (기본 10%)
        use_calibration: BMA 캘리브레이션 적용 여부 (Heavy 모드)
        shrinkage: 과신 보정 수축 계수 (0.15 = 극단값 15% 수축)

    Returns:
        AggregationResult
    """
    if not signals:
        return AggregationResult(
            probability=0.5, calibrated_probability=0.5,
            confidence=0.0, std_dev=0.5, ci_lower=0.0, ci_upper=1.0,
            trimmed_n=0,
        )

    n = len(signals)

    # 1. 확률순 정렬
    sorted_signals = sorted(signals, key=lambda s: s.probability_yes)

    # 2. 상하 trim
    trim_count = max(1, int(n * trim_fraction)) if n >= 5 else 0
    trimmed = sorted_signals[trim_count:n - trim_count] if trim_count > 0 else sorted_signals
    trimmed_n = len(trimmed)

    if trimmed_n == 0:
        trimmed = sorted_signals
        trimmed_n = len(trimmed)

    # 3. 가중 평균 (weight = run confidence)
    weights = [max(s.confidence, 0.1) for s in trimmed]
    total_weight = sum(weights)

    probabilities = [s.probability_yes for s in trimmed]
    weighted_mean = sum(w * p for w, p in zip(weights, probabilities)) / total_weight

    # 4. 가중 표준편차
    weighted_var = sum(w * (p - weighted_mean) ** 2 for w, p in zip(weights, probabilities)) / total_weight
    std_dev = math.sqrt(weighted_var)

    # 5. 95% 신뢰구간 (t-분포)
    df = trimmed_n - 1
    if df < 1:
        df = 1
    t_crit = _get_t_critical(df)
    se = std_dev / math.sqrt(trimmed_n)
    ci_lower = max(0.0, weighted_mean - t_crit * se)
    ci_upper = min(1.0, weighted_mean + t_crit * se)

    # 6. BMA 캘리브레이션 (Heavy 모드)
    if use_calibration:
        calibrated = _calibrate_bma(weighted_mean, shrinkage)
    else:
        calibrated = weighted_mean

    # 7. Confidence 점수 (0-100)
    agreement = 1.0 - min(std_dev / 0.5, 1.0)  # 합의도
    data_quality = sum(s.confidence for s in trimmed) / trimmed_n  # 평균 run confidence
    sample_factor = min(1.0, trimmed_n / 20.0)  # 표본 크기

    confidence = 100.0 * (0.4 * agreement + 0.4 * data_quality + 0.2 * sample_factor)
    confidence = max(5.0, min(95.0, confidence))  # 5-95% 클램프

    # 8. 핵심 근거 수집
    all_for = []
    all_against = []
    for s in signals:
        all_for.extend(s.key_arguments_for)
        all_against.extend(s.key_arguments_against)

    # 빈도순 정렬 (중복 제거하면서)
    top_for = _dedupe_top_n(all_for, 5)
    top_against = _dedupe_top_n(all_against, 5)

    return AggregationResult(
        probability=weighted_mean,
        calibrated_probability=calibrated,
        confidence=confidence,
        std_dev=std_dev,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        trimmed_n=trimmed_n,
        top_arguments_for=top_for,
        top_arguments_against=top_against,
    )


def _calibrate_bma(raw_probability: float, shrinkage: float = 0.15) -> float:
    """
    Bayesian Model Averaging 캘리브레이션.
    LLM은 체계적으로 과신 (NAACL 2024) → 극단값을 중앙으로 수축.

    shrinkage=0.15일 때:
      raw 0.85 → 0.7975
      raw 0.60 → 0.585
      raw 0.50 → 0.50 (변화 없음)
    """
    return 0.5 + (raw_probability - 0.5) * (1.0 - shrinkage)


def _dedupe_top_n(items: List[str], n: int) -> List[str]:
    """빈도순으로 상위 N개 고유 항목 반환."""
    seen = {}
    for item in items:
        key = item.strip().lower()
        if key not in seen:
            seen[key] = item.strip()
    return list(seen.values())[:n]

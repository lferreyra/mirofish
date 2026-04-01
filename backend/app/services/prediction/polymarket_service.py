"""
Polymarket Prediction 오케스트레이터
전체 파이프라인: research → frame → ensemble → extract → aggregate → risk
"""

import uuid
import time
from typing import Optional, Callable
from datetime import datetime

from ...utils.llm_client import LLMClient
from ...utils.logger import get_logger
from ..external_data import get_external_data_service
from .models import (
    PredictionRequest, PredictionResult, PredictionMode,
    RunSignal, AggregationResult, RiskAssessment,
)
from .question_framer import QuestionFramer
from .ensemble_runner import EnsembleRunner
from .signal_extractor import SignalExtractor
from . import aggregator
from . import risk_assessor

logger = get_logger('mirofish.prediction.service')


class PolymarketPredictionService:
    """
    Polymarket 예측 서비스.

    전체 파이프라인:
    1. Research — 외부 데이터 수집
    2. Question Framing — 질문 → 시뮬레이션 파라미터 변환
    3. Ensemble — N회 시뮬레이션 실행
    4. Signal Extraction — 각 run에서 확률 추출
    5. Aggregation — 통계 합산
    6. Risk Assessment — 리스크 분류 + Kelly 배팅
    """

    def __init__(self, llm: Optional[LLMClient] = None):
        self.llm = llm or LLMClient()
        self.framer = QuestionFramer(llm=self.llm)
        self.extractor = SignalExtractor(llm=self.llm)
        self.external_data = get_external_data_service()

    async def predict(
        self,
        request: PredictionRequest,
        progress_callback: Optional[Callable] = None,
    ) -> PredictionResult:
        """
        전체 예측 파이프라인을 실행합니다.

        Args:
            request: 예측 요청
            progress_callback: fn(phase, progress_pct, message)

        Returns:
            PredictionResult
        """
        prediction_id = f"pred_{uuid.uuid4().hex[:12]}"
        start_time = time.time()
        mode_config = request.mode_config

        logger.info(
            f"예측 시작: {prediction_id}, mode={request.mode.value}, "
            f"ensemble={mode_config.ensemble_size}, agents={mode_config.agent_count}"
        )

        # ── Phase 1: Research ──
        if progress_callback:
            progress_callback("research", 0, "외부 데이터 수집 중...")

        research = self.external_data.fetch_all(
            topic=request.question,
            symbols=request.relevant_symbols or None,
        )
        research_text = research.to_text() if not research.is_empty else ""

        logger.info(f"Research 완료: {len(research_text)} chars")

        # ── Phase 2: Question Framing ──
        if progress_callback:
            progress_callback("framing", 5, "질문 분석 중...")

        frame = self.framer.frame_question(request, research_text)

        logger.info(
            f"Framing 완료: {len(frame.archetypes)} archetypes, "
            f"{len(frame.initial_posts)} initial posts"
        )

        # ── Phase 3: Ensemble Simulation ──
        if progress_callback:
            progress_callback("ensemble", 10, "앙상블 시뮬레이션 시작...")

        runner = EnsembleRunner(prediction_id, request, framer=self.framer)
        completed_runs = await runner.run_ensemble(
            frame,
            progress_callback=lambda phase, pct, msg: (
                progress_callback("ensemble", 10 + int(pct * 0.6), msg)
                if progress_callback else None
            ),
        )

        successful_runs = [r for r in completed_runs if r.success]
        logger.info(f"Ensemble 완료: {len(successful_runs)}/{len(completed_runs)} 성공")

        if not successful_runs:
            elapsed = time.time() - start_time
            return PredictionResult(
                prediction_id=prediction_id,
                question=request.question,
                mode=request.mode.value,
                probability=50.0,
                confidence=0.0,
                risk_rating="extreme",
                recommended_bet_size=0.0,
                edge=0.0,
                expected_value=0.0,
                ensemble_size=mode_config.ensemble_size,
                completed_runs=0,
                confidence_interval_lower=0.0,
                confidence_interval_upper=100.0,
                std_deviation=0.5,
                key_factors_for=["시뮬레이션 전부 실패"],
                key_factors_against=[],
                market_odds=request.market_odds,
                created_at=datetime.now().isoformat(),
                total_duration_seconds=elapsed,
            )

        # ── Phase 4: Signal Extraction ──
        if progress_callback:
            progress_callback("extraction", 70, "시뮬레이션 결과 분석 중...")

        signals = []
        for i, run in enumerate(successful_runs):
            if progress_callback:
                progress_callback(
                    "extraction",
                    70 + int((i / len(successful_runs)) * 15),
                    f"Run {i + 1}/{len(successful_runs)} 신호 추출 중..."
                )

            signal = await self.extractor.extract_signal(
                simulation_dir=run.simulation_dir,
                question=request.question,
                run_id=run.run_id,
                run_index=run.run_index,
                methods=mode_config.signal_methods,
            )
            signals.append(signal)

        logger.info(f"Signal extraction 완료: {len(signals)} signals")

        # ── Phase 5: Aggregation ──
        if progress_callback:
            progress_callback("aggregation", 85, "결과 합산 중...")

        agg = aggregator.aggregate(
            signals,
            trim_fraction=0.1,
            use_calibration=mode_config.use_calibration,
        )

        # ── Phase 6: Risk Assessment ──
        if progress_callback:
            progress_callback("risk", 90, "리스크 평가 중...")

        risk = risk_assessor.assess(
            aggregation=agg,
            market_odds=request.market_odds,
            resolution_date=request.resolution_date,
        )

        # ── 최종 결과 ──
        elapsed = time.time() - start_time

        result = PredictionResult(
            prediction_id=prediction_id,
            question=request.question,
            mode=request.mode.value,
            probability=round(agg.calibrated_probability * 100, 1),
            confidence=round(agg.confidence, 1),
            risk_rating=risk.risk_rating,
            recommended_bet_size=risk.recommended_bet,
            edge=risk.edge,
            expected_value=risk.expected_value,
            ensemble_size=mode_config.ensemble_size,
            completed_runs=len(successful_runs),
            confidence_interval_lower=round(agg.ci_lower * 100, 1),
            confidence_interval_upper=round(agg.ci_upper * 100, 1),
            std_deviation=round(agg.std_dev, 3),
            key_factors_for=agg.top_arguments_for,
            key_factors_against=agg.top_arguments_against,
            research_summary=research_text[:2000] if research_text else "",
            run_signals=signals,
            market_odds=request.market_odds,
            created_at=datetime.now().isoformat(),
            total_duration_seconds=elapsed,
        )

        if progress_callback:
            progress_callback("complete", 100, "예측 완료")

        logger.info(
            f"예측 완료: {prediction_id}, "
            f"probability={result.probability}%, "
            f"confidence={result.confidence}%, "
            f"risk={result.risk_rating}, "
            f"kelly={result.recommended_bet_size:.4f}, "
            f"elapsed={elapsed:.0f}s"
        )

        return result

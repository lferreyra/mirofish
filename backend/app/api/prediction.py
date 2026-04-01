"""
Polymarket Prediction API
/api/prediction/*
"""

import asyncio
import threading
from flask import Blueprint, request, jsonify

from ..utils.logger import get_logger
from ..models.task import TaskManager, TaskStatus

logger = get_logger('mirofish.api.prediction')

prediction_bp = Blueprint('prediction', __name__)

# 예측 결과 저장소 (메모리, 향후 파일/DB로 전환 가능)
_prediction_results = {}
_prediction_tasks = {}
_task_manager = TaskManager()


@prediction_bp.route('/create', methods=['POST'])
def create_prediction():
    """
    예측 요청을 생성하고 background task로 실행합니다.

    Request body:
    {
        "question": "Will Bitcoin hit $100K by Dec 2026?",
        "mode": "mid",                    // "low", "mid", "heavy"
        "market_odds": 0.65,              // 현재 Polymarket 가격 (선택)
        "resolution_criteria": "...",     // 해상도 기준 (선택)
        "resolution_date": "2026-12-31",  // ISO date (선택)
        "category": "crypto",             // 카테고리 (선택)
        "relevant_symbols": ["BTC"],      // 시장 심볼 (선택)
        "platform": "twitter"             // "twitter", "reddit", "parallel" (선택)
    }
    """
    data = request.get_json()
    if not data or 'question' not in data:
        return jsonify({"error": "question 필요"}), 400

    from ..services.prediction.models import PredictionRequest, PredictionMode

    try:
        mode = PredictionMode(data.get('mode', 'mid'))
    except ValueError:
        return jsonify({"error": f"유효하지 않은 mode: {data.get('mode')}. low/mid/heavy 중 선택"}), 400

    pred_request = PredictionRequest(
        question=data['question'],
        mode=mode,
        market_odds=data.get('market_odds'),
        resolution_criteria=data.get('resolution_criteria', ''),
        resolution_date=data.get('resolution_date'),
        category=data.get('category', ''),
        relevant_symbols=data.get('relevant_symbols', []),
        platform=data.get('platform', 'twitter'),
    )

    # Task 생성
    task_id = _task_manager.create_task(
        task_type="prediction",
        metadata={
            "question": pred_request.question,
            "mode": pred_request.mode.value,
            "ensemble_size": pred_request.mode_config.ensemble_size,
        }
    )

    # Background thread에서 실행
    thread = threading.Thread(
        target=_run_prediction_async,
        args=(task_id, pred_request),
        daemon=True,
    )
    thread.start()

    _prediction_tasks[task_id] = {
        "question": pred_request.question,
        "mode": pred_request.mode.value,
        "status": "running",
    }

    mode_config = pred_request.mode_config
    return jsonify({
        "task_id": task_id,
        "question": pred_request.question,
        "mode": pred_request.mode.value,
        "ensemble_size": mode_config.ensemble_size,
        "agent_count": mode_config.agent_count,
        "simulation_hours": mode_config.simulation_hours,
        "message": f"예측 시작됨 (mode={mode.value}, {mode_config.ensemble_size}회 앙상블)",
    })


def _run_prediction_async(task_id: str, pred_request):
    """Background thread에서 예측을 실행합니다."""
    try:
        from ..services.prediction.polymarket_service import PolymarketPredictionService

        _task_manager.update_task(task_id, status=TaskStatus.PROCESSING, progress=0, message="예측 시작...")

        service = PolymarketPredictionService()

        # asyncio 이벤트 루프 생성
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        def progress_cb(phase, pct, msg):
            _task_manager.update_task(task_id, progress=pct, message=f"[{phase}] {msg}")

        result = loop.run_until_complete(
            service.predict(pred_request, progress_callback=progress_cb)
        )
        loop.close()

        # 결과 저장
        _prediction_results[result.prediction_id] = result
        _prediction_tasks[task_id]["prediction_id"] = result.prediction_id
        _prediction_tasks[task_id]["status"] = "completed"

        _task_manager.complete_task(task_id, {
            "prediction_id": result.prediction_id,
            "probability": result.probability,
            "confidence": result.confidence,
            "risk_rating": result.risk_rating,
        })

        logger.info(f"예측 완료: {result.prediction_id}, probability={result.probability}%")

    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        _prediction_tasks[task_id]["status"] = "failed"
        _prediction_tasks[task_id]["error"] = str(e)
        _task_manager.fail_task(task_id, error_msg)
        logger.error(f"예측 실패: {e}")


@prediction_bp.route('/status/<task_id>', methods=['GET'])
def get_prediction_status(task_id: str):
    """예측 진행 상황을 반환합니다."""
    task = _task_manager.get_task(task_id)
    if not task:
        return jsonify({"error": "예측 task를 찾을 수 없음"}), 404

    response = {
        "task_id": task_id,
        "status": task.get("status", "unknown"),
        "progress": task.get("progress", 0),
        "message": task.get("message", ""),
    }

    # 완료된 경우 prediction_id 포함
    meta = _prediction_tasks.get(task_id, {})
    if "prediction_id" in meta:
        response["prediction_id"] = meta["prediction_id"]
    if "error" in meta:
        response["error"] = meta["error"]

    return jsonify(response)


@prediction_bp.route('/result/<prediction_id>', methods=['GET'])
def get_prediction_result(prediction_id: str):
    """완료된 예측 결과를 반환합니다."""
    result = _prediction_results.get(prediction_id)
    if not result:
        return jsonify({"error": "예측 결과를 찾을 수 없음"}), 404

    return jsonify(result.to_dict())


@prediction_bp.route('/list', methods=['GET'])
def list_predictions():
    """모든 예측 목록을 반환합니다."""
    predictions = []
    for pred_id, result in _prediction_results.items():
        predictions.append({
            "prediction_id": pred_id,
            "question": result.question,
            "mode": result.mode,
            "probability": result.probability,
            "confidence": result.confidence,
            "risk_rating": result.risk_rating,
            "created_at": result.created_at,
        })
    return jsonify({"predictions": predictions, "total": len(predictions)})

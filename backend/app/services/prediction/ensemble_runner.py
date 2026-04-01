"""
앙상블 시뮬레이션 실행 관리
N회 시뮬레이션을 순차 실행하고, 파라미터 변이를 적용합니다.
"""

import os
import uuid
import json
import time
import asyncio
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass

from ...utils.logger import get_logger
from .models import PredictionRequest, QuestionFrame, AgentArchetype, MODE_CONFIGS
from .question_framer import QuestionFramer
from .signal_extractor import SignalExtractor

logger = get_logger('mirofish.prediction.ensemble')


@dataclass
class CompletedRun:
    """완료된 시뮬레이션 run"""
    run_id: str
    run_index: int
    simulation_dir: str
    config: Dict[str, Any]
    success: bool
    error: Optional[str] = None


class EnsembleRunner:
    """
    앙상블 시뮬레이션 실행 관리.

    N회 시뮬레이션을 순차 실행하고 (rate limit 로테이션 활용),
    각 run에 파라미터 변이를 적용합니다.
    """

    def __init__(
        self,
        prediction_id: str,
        request: PredictionRequest,
        framer: Optional[QuestionFramer] = None,
    ):
        self.prediction_id = prediction_id
        self.request = request
        self.mode_config = request.mode_config
        self.framer = framer or QuestionFramer()

    async def run_ensemble(
        self,
        question_frame: QuestionFrame,
        progress_callback: Optional[Callable] = None,
    ) -> List[CompletedRun]:
        """
        N회 시뮬레이션을 실행합니다.

        Args:
            question_frame: 질문 프레이밍 결과
            progress_callback: fn(phase, progress_pct, message)

        Returns:
            CompletedRun 리스트
        """
        n = self.mode_config.ensemble_size
        completed_runs = []

        logger.info(
            f"앙상블 시작: {n}회, mode={self.request.mode.value}, "
            f"agents={self.mode_config.agent_count}, "
            f"hours={self.mode_config.simulation_hours}"
        )

        for i in range(n):
            run_id = f"{self.prediction_id}_run_{i:03d}"

            if progress_callback:
                progress_callback(
                    "ensemble",
                    int((i / n) * 100),
                    f"시뮬레이션 {i + 1}/{n} 실행 중..."
                )

            try:
                # 파라미터 변이 생성
                perturbation = self.framer.generate_perturbation(
                    question_frame.archetypes,
                    run_index=i,
                    temperature_sweep=self.mode_config.temperature_sweep,
                )

                # 시뮬레이션 config 생성
                sim_config = self._build_simulation_config(
                    question_frame,
                    perturbation,
                    run_id,
                    run_index=i,
                )

                # 시뮬레이션 디렉토리 생성
                sim_dir = self._create_simulation_dir(run_id, sim_config)

                # 시뮬레이션 실행
                success = await self._run_single_simulation(sim_dir, sim_config)

                completed_runs.append(CompletedRun(
                    run_id=run_id,
                    run_index=i,
                    simulation_dir=sim_dir,
                    config=sim_config,
                    success=success,
                ))

                logger.info(f"Run {i + 1}/{n} 완료: {run_id} ({'성공' if success else '실패'})")

            except Exception as e:
                logger.error(f"Run {i + 1}/{n} 실패: {e}")
                completed_runs.append(CompletedRun(
                    run_id=run_id,
                    run_index=i,
                    simulation_dir="",
                    config={},
                    success=False,
                    error=str(e),
                ))

        successful = sum(1 for r in completed_runs if r.success)
        logger.info(f"앙상블 완료: {successful}/{n} 성공")

        return completed_runs

    def _build_simulation_config(
        self,
        frame: QuestionFrame,
        perturbation: Dict[str, Any],
        run_id: str,
        run_index: int,
    ) -> Dict[str, Any]:
        """시뮬레이션 config JSON을 생성합니다."""
        archetypes = perturbation["archetypes"]
        llm_temp = perturbation["llm_temperature"]
        echo_chamber = perturbation["echo_chamber_strength"]

        # 에이전트 configs 생성
        agent_configs = []
        agent_id = 0
        for arch in archetypes:
            import random
            rng = random.Random(run_index * 100 + agent_id)

            for j in range(arch.count):
                sentiment = rng.uniform(arch.sentiment_min, arch.sentiment_max)
                activity = rng.uniform(0.3, 0.8)

                agent_configs.append({
                    "agent_id": agent_id,
                    "entity_uuid": f"pred_{run_id}_{agent_id}",
                    "entity_name": f"{arch.label}_{j + 1}",
                    "entity_type": arch.role,
                    "activity_level": round(activity, 2),
                    "posts_per_hour": round(rng.uniform(0.5, 2.0), 1),
                    "comments_per_hour": round(rng.uniform(0.5, 3.0), 1),
                    "active_hours": list(range(6, 24)),  # 6AM-midnight
                    "response_delay_min": 1,
                    "response_delay_max": 10,
                    "sentiment_bias": round(sentiment, 2),
                    "stance": arch.stance,
                    "influence_weight": round(arch.influence_weight, 2),
                    "persona": arch.description,
                })
                agent_id += 1

        # 시간 config
        hours = self.mode_config.simulation_hours
        config = {
            "simulation_id": run_id,
            "prediction_id": self.prediction_id,
            "simulation_requirement": frame.simulation_requirement,
            "time_config": {
                "total_simulation_hours": hours,
                "minutes_per_round": 60,
                "agents_per_hour_min": max(3, len(agent_configs) // 4),
                "agents_per_hour_max": len(agent_configs),
            },
            "agent_configs": agent_configs,
            "event_config": {
                "initial_posts": frame.initial_posts,
                "hot_topics": frame.hot_topics,
                "narrative_direction": frame.narrative_direction,
            },
            "twitter_config": {
                "recommendation_weights": {
                    "recency": 0.3,
                    "popularity": 0.4,
                    "relevance": 0.3,
                },
                "viral_threshold": 5,
                "echo_chamber_strength": echo_chamber,
            },
            "llm_temperature": llm_temp,
            "run_index": run_index,
        }

        return config

    def _create_simulation_dir(self, run_id: str, config: Dict) -> str:
        """시뮬레이션 디렉토리를 생성하고 config를 저장합니다."""
        from ...config import Config

        base_dir = os.path.join(
            Config.OASIS_SIMULATION_DATA_DIR,
            "predictions",
            self.prediction_id,
        )
        sim_dir = os.path.join(base_dir, run_id)
        os.makedirs(sim_dir, exist_ok=True)

        # Twitter/Reddit 서브 디렉토리
        os.makedirs(os.path.join(sim_dir, "twitter"), exist_ok=True)
        os.makedirs(os.path.join(sim_dir, "reddit"), exist_ok=True)

        # Config 저장
        config_path = os.path.join(sim_dir, "simulation_config.json")
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        return sim_dir

    async def _run_single_simulation(
        self,
        simulation_dir: str,
        config: Dict,
    ) -> bool:
        """
        단일 시뮬레이션을 실행합니다.
        기존 SimulationRunner를 재사용합니다.
        """
        try:
            # 시뮬레이션 스크립트 직접 실행
            script_path = os.path.join(
                os.path.dirname(__file__), '../../../scripts/run_parallel_simulation.py'
            )
            config_path = os.path.join(simulation_dir, "simulation_config.json")

            process = await asyncio.create_subprocess_exec(
                'python', script_path,
                '--config', config_path,
                '--output-dir', simulation_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                logger.error(f"시뮬레이션 실패: {stderr.decode()[:500]}")
                return False

            # actions.jsonl 존재 확인
            actions_path = os.path.join(simulation_dir, "twitter", "actions.jsonl")
            if os.path.exists(actions_path):
                return True

            # Reddit으로 폴백 확인
            actions_path = os.path.join(simulation_dir, "reddit", "actions.jsonl")
            return os.path.exists(actions_path)

        except Exception as e:
            logger.error(f"시뮬레이션 실행 오류: {e}")
            return False

"""
Polymarket 질문 → 시뮬레이션 파라미터 변환
LLM을 사용하여 질문을 에이전트 아키타입과 시뮬레이션 설정으로 변환합니다.
"""

import json
import random
from typing import List, Dict, Any, Optional

from ...utils.llm_client import LLMClient
from ...utils.logger import get_logger
from .models import (
    PredictionRequest, PredictionMode, QuestionFrame,
    AgentArchetype, DEFAULT_ARCHETYPES, ModeConfig, MODE_CONFIGS,
)

logger = get_logger('mirofish.prediction.framer')

FRAMING_PROMPT = """\
You are a prediction market analyst. Convert the following question into a social media simulation setup.

**Question:** {question}
**Category:** {category}
**Resolution criteria:** {resolution_criteria}
**Resolution date:** {resolution_date}

**Current research context:**
{research_context}

**Agent archetypes to use:**
{archetypes_description}

Your task:
1. Write a `simulation_requirement` — a natural language description of the debate topic for the simulation (in English, 2-3 sentences)
2. For each agent archetype, write a brief persona description that fits the question context
3. Create 3-5 initial seed posts that kickstart the debate (balanced for/against)
4. List 5-10 hot topic keywords relevant to this question
5. Write a `narrative_direction` — what the debate should explore (1-2 sentences)

Output JSON:
{{
    "simulation_requirement": "...",
    "agent_personas": {{
        "archetype_role": "persona description for this question context"
    }},
    "initial_posts": [
        {{"poster_archetype": "bull", "content": "post content"}},
        {{"poster_archetype": "bear", "content": "post content"}}
    ],
    "hot_topics": ["keyword1", "keyword2"],
    "narrative_direction": "..."
}}"""


class QuestionFramer:
    """Polymarket 질문을 시뮬레이션 파라미터로 변환합니다."""

    def __init__(self, llm: Optional[LLMClient] = None):
        self.llm = llm or LLMClient()

    def frame_question(
        self,
        request: PredictionRequest,
        research_context: str = "",
    ) -> QuestionFrame:
        """
        질문을 시뮬레이션 파라미터로 변환합니다.

        Args:
            request: 예측 요청
            research_context: ExternalDataService에서 수집한 컨텍스트

        Returns:
            QuestionFrame
        """
        mode_config = request.mode_config
        archetypes = DEFAULT_ARCHETYPES[request.mode]

        # 아키타입 설명 텍스트
        arch_desc = "\n".join(
            f"- {a.role} ({a.count}명, stance={a.stance}, sentiment={a.sentiment_min}~{a.sentiment_max}): {a.description}"
            for a in archetypes
        )

        prompt = FRAMING_PROMPT.format(
            question=request.question,
            category=request.category or "general",
            resolution_criteria=request.resolution_criteria or "Standard Polymarket resolution",
            resolution_date=request.resolution_date or "Not specified",
            research_context=research_context[:3000] if research_context else "No research data available",
            archetypes_description=arch_desc,
        )

        try:
            result = self.llm.chat_json(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=4096,
            )

            # 아키타입에 LLM이 생성한 persona 적용
            personas = result.get("agent_personas", {})
            enriched_archetypes = []
            for arch in archetypes:
                persona = personas.get(arch.role, arch.description)
                enriched = AgentArchetype(
                    role=arch.role,
                    label=arch.label,
                    count=arch.count,
                    stance=arch.stance,
                    sentiment_min=arch.sentiment_min,
                    sentiment_max=arch.sentiment_max,
                    influence_weight=arch.influence_weight,
                    description=persona,
                )
                enriched_archetypes.append(enriched)

            # 초기 게시물
            initial_posts = []
            for i, post in enumerate(result.get("initial_posts", [])):
                initial_posts.append({
                    "poster_agent_id": i % mode_config.agent_count,
                    "content": post.get("content", ""),
                    "archetype": post.get("poster_archetype", ""),
                })

            frame = QuestionFrame(
                simulation_requirement=result.get("simulation_requirement", request.question),
                archetypes=enriched_archetypes,
                initial_posts=initial_posts,
                hot_topics=result.get("hot_topics", []),
                narrative_direction=result.get("narrative_direction", ""),
                research_context=research_context[:2000] if research_context else "",
            )

            logger.info(
                f"질문 프레이밍 완료: {len(enriched_archetypes)}개 아키타입, "
                f"{len(initial_posts)}개 초기 게시물, {len(frame.hot_topics)}개 핫토픽"
            )
            return frame

        except Exception as e:
            logger.error(f"질문 프레이밍 실패, 기본값 사용: {e}")
            # 폴백: LLM 없이 기본 프레임 생성
            return QuestionFrame(
                simulation_requirement=request.question,
                archetypes=list(archetypes),
                initial_posts=[],
                hot_topics=request.question.split()[:5],
                narrative_direction=request.question,
                research_context=research_context[:2000] if research_context else "",
            )

    def generate_perturbation(
        self,
        base_archetypes: List[AgentArchetype],
        run_index: int,
        temperature_sweep: bool = False,
    ) -> Dict[str, Any]:
        """
        앙상블 run별 파라미터 변이를 생성합니다.

        Args:
            base_archetypes: 기본 아키타입 목록
            run_index: 현재 run 번호 (seed로 사용)
            temperature_sweep: LLM temperature 변이 여부

        Returns:
            {"archetypes": [...], "llm_temperature": float, "echo_chamber": float}
        """
        rng = random.Random(run_index * 42 + 7)

        perturbed = []
        for arch in base_archetypes:
            # sentiment_bias 변이: ±0.2
            sentiment_shift = rng.uniform(-0.2, 0.2)
            new_min = max(-1.0, min(1.0, arch.sentiment_min + sentiment_shift))
            new_max = max(-1.0, min(1.0, arch.sentiment_max + sentiment_shift))
            if new_min > new_max:
                new_min, new_max = new_max, new_min

            # stance 스왑: 5% 확률로 1명 스왑
            new_stance = arch.stance
            if rng.random() < 0.05:
                swap_map = {
                    "supportive": "opposing",
                    "opposing": "supportive",
                    "neutral": rng.choice(["supportive", "opposing"]),
                    "observer": "neutral",
                }
                new_stance = swap_map.get(arch.stance, arch.stance)

            # activity 변이
            activity_factor = rng.uniform(0.7, 1.3)

            perturbed.append(AgentArchetype(
                role=arch.role,
                label=arch.label,
                count=arch.count,
                stance=new_stance,
                sentiment_min=round(new_min, 2),
                sentiment_max=round(new_max, 2),
                influence_weight=round(arch.influence_weight * activity_factor, 2),
                description=arch.description,
            ))

        # LLM temperature sweep
        if temperature_sweep:
            temp = 0.3 + (run_index / 50) * 0.7  # 0.3 ~ 1.0
            temp = min(1.0, max(0.3, temp))
        else:
            temp = rng.uniform(0.5, 0.9)

        # Echo chamber strength
        echo = rng.uniform(0.2, 0.8)

        return {
            "archetypes": perturbed,
            "llm_temperature": round(temp, 2),
            "echo_chamber_strength": round(echo, 2),
        }

"""
시뮬레이션 결과에서 확률 신호를 추출합니다.

방법 A (content): 에이전트 게시물을 LLM으로 for/against/neutral 분류
방법 B (trajectory): 시간별 여론 변화 궤적 분석
방법 C (report_agent): ReportAgent에게 직접 확률 질문
"""

import os
import json
from typing import List, Dict, Any, Optional

from ...utils.llm_client import LLMClient
from ...utils.logger import get_logger
from .models import RunSignal

logger = get_logger('mirofish.prediction.signal')

CLASSIFY_PROMPT = """\
You are analyzing social media posts from a prediction simulation.

**Question being predicted:** {question}

**Posts to classify:**
{posts_text}

For each post, classify:
- stance: "for" (supports YES outcome), "against" (supports NO outcome), or "neutral"
- confidence: 0.0-1.0 (how strongly the post expresses this stance)

Output JSON:
{{
    "classifications": [
        {{"post_index": 0, "stance": "for", "confidence": 0.8, "key_argument": "brief summary"}},
        ...
    ],
    "overall_sentiment": -1.0 to 1.0,
    "dominant_stance": "for" or "against" or "mixed",
    "key_arguments_for": ["arg1", "arg2"],
    "key_arguments_against": ["arg1", "arg2"]
}}"""

PROBABILITY_PROMPT = """\
You are a calibrated forecaster analyzing simulation results.

**Question:** {question}

**Simulation summary:**
- Total agents: {agent_count}
- Total actions: {action_count}
- Posts for YES: {for_count} (weighted: {for_weight:.2f})
- Posts against: {against_count} (weighted: {against_weight:.2f})
- Neutral posts: {neutral_count}
- Sentiment trajectory: {trajectory}
- Key arguments FOR: {args_for}
- Key arguments AGAINST: {args_against}

Based on this simulation data, what is the probability of the YES outcome?
Answer with ONLY a JSON object:
{{"probability": 0.XX, "reasoning": "brief explanation"}}"""


class SignalExtractor:
    """시뮬레이션 결과에서 확률 신호를 추출합니다."""

    def __init__(self, llm: Optional[LLMClient] = None):
        self.llm = llm or LLMClient()

    async def extract_signal(
        self,
        simulation_dir: str,
        question: str,
        run_id: str,
        run_index: int,
        methods: List[str] = None,
    ) -> RunSignal:
        """
        하나의 시뮬레이션 run에서 확률 신호를 추출합니다.

        Args:
            simulation_dir: 시뮬레이션 디렉토리 경로
            question: 예측 질문
            run_id: run 식별자
            run_index: run 번호
            methods: 사용할 방법 목록 ["content", "trajectory", "report_agent"]
        """
        if methods is None:
            methods = ["content"]

        # actions.jsonl 파싱
        actions = self._load_actions(simulation_dir)
        posts = [a for a in actions if a.get("action_type") in ("CREATE_POST", "CREATE_COMMENT")]

        if not posts:
            logger.warning(f"Run {run_id}: 게시물 없음")
            return RunSignal(
                run_id=run_id, run_index=run_index,
                probability_yes=0.5, sentiment_score=0.0,
                confidence=0.1, agent_count=0, action_count=0,
                dominant_stance="mixed",
            )

        method_scores = {}
        all_args_for = []
        all_args_against = []

        # 방법 A: Content-based LLM classification
        if "content" in methods:
            content_result = self._extract_content_signal(posts, question)
            method_scores["content"] = content_result["probability"]
            all_args_for.extend(content_result.get("args_for", []))
            all_args_against.extend(content_result.get("args_against", []))

        # 방법 B: Trajectory analysis
        if "trajectory" in methods:
            trajectory_result = self._extract_trajectory_signal(posts, question)
            method_scores["trajectory"] = trajectory_result["probability"]

        # 방법 C: Direct LLM probability estimate
        if "report_agent" in methods:
            content_result_for_context = method_scores.get("content")
            report_result = self._extract_report_signal(
                posts, question, content_result_for_context
            )
            method_scores["report_agent"] = report_result["probability"]

        # 가중 합산
        weights = {"content": 0.4, "trajectory": 0.3, "report_agent": 0.3}
        total_weight = sum(weights.get(m, 0) for m in method_scores)
        if total_weight > 0:
            probability = sum(
                weights.get(m, 0.33) * score
                for m, score in method_scores.items()
            ) / total_weight
        else:
            probability = 0.5

        # 에이전트 수, 액션 수
        agent_ids = set(a.get("agent_id") for a in actions)
        dominant = "mixed"
        if probability > 0.6:
            dominant = "for"
        elif probability < 0.4:
            dominant = "against"

        return RunSignal(
            run_id=run_id,
            run_index=run_index,
            probability_yes=round(probability, 4),
            sentiment_score=round(probability * 2 - 1, 4),  # 0-1 → -1~1
            confidence=round(min(len(posts) / 50, 1.0), 2),  # 게시물 많을수록 높은 confidence
            agent_count=len(agent_ids),
            action_count=len(actions),
            dominant_stance=dominant,
            key_arguments_for=all_args_for[:5],
            key_arguments_against=all_args_against[:5],
            method_scores=method_scores,
        )

    def _extract_content_signal(
        self, posts: List[Dict], question: str
    ) -> Dict[str, Any]:
        """방법 A: 게시물 내용을 LLM으로 분류하여 확률 추출."""
        # 게시물을 배치로 분류 (최대 30개)
        sample = posts[:30] if len(posts) > 30 else posts
        posts_text = "\n\n".join(
            f"[Post {i}] (Agent: {p.get('agent_name', 'unknown')}, Round: {p.get('round_num', '?')})\n"
            f"{p.get('action_args', {}).get('content', '')[:300]}"
            for i, p in enumerate(sample)
        )

        try:
            result = self.llm.chat_json(
                messages=[{
                    "role": "user",
                    "content": CLASSIFY_PROMPT.format(
                        question=question,
                        posts_text=posts_text,
                    ),
                }],
                temperature=0.2,
                max_tokens=4096,
            )

            classifications = result.get("classifications", [])
            for_weight = sum(
                c.get("confidence", 0.5) for c in classifications if c.get("stance") == "for"
            )
            against_weight = sum(
                c.get("confidence", 0.5) for c in classifications if c.get("stance") == "against"
            )
            total = for_weight + against_weight
            probability = for_weight / total if total > 0 else 0.5

            return {
                "probability": probability,
                "args_for": result.get("key_arguments_for", []),
                "args_against": result.get("key_arguments_against", []),
                "for_count": sum(1 for c in classifications if c.get("stance") == "for"),
                "against_count": sum(1 for c in classifications if c.get("stance") == "against"),
            }
        except Exception as e:
            logger.warning(f"Content signal extraction 실패: {e}")
            return {"probability": 0.5, "args_for": [], "args_against": []}

    def _extract_trajectory_signal(
        self, posts: List[Dict], question: str
    ) -> Dict[str, Any]:
        """방법 B: 시간별 여론 변화 궤적 분석."""
        if len(posts) < 4:
            return {"probability": 0.5}

        # 전반부 vs 후반부 분할
        mid = len(posts) // 2
        first_half = posts[:mid]
        second_half = posts[mid:]

        # 간단한 키워드 기반 sentiment (LLM 없이 빠르게)
        positive_keywords = {
            "yes", "will", "bullish", "positive", "growth", "increase", "rise",
            "support", "agree", "likely", "probable", "definitely", "확실",
            "상승", "긍정", "찬성", "가능", "오를",
        }
        negative_keywords = {
            "no", "won't", "bearish", "negative", "decline", "decrease", "fall",
            "oppose", "disagree", "unlikely", "improbable", "doubtful", "불가능",
            "하락", "부정", "반대", "위험", "내릴",
        }

        def sentiment_score(post_list):
            pos = 0
            neg = 0
            for p in post_list:
                content = p.get("action_args", {}).get("content", "").lower()
                pos += sum(1 for kw in positive_keywords if kw in content)
                neg += sum(1 for kw in negative_keywords if kw in content)
            total = pos + neg
            return pos / total if total > 0 else 0.5

        first_score = sentiment_score(first_half)
        second_score = sentiment_score(second_half)

        # 후반부에 2x 가중치
        trajectory_probability = (first_score * 1 + second_score * 2) / 3

        return {"probability": trajectory_probability}

    def _extract_report_signal(
        self, posts: List[Dict], question: str,
        content_probability: Optional[float] = None,
    ) -> Dict[str, Any]:
        """방법 C: LLM에게 직접 확률 판단 요청."""
        # 요약 통계
        for_count = 0
        against_count = 0
        neutral_count = 0
        for_weight = 0.0
        against_weight = 0.0

        if content_probability is not None:
            for_weight = content_probability
            against_weight = 1.0 - content_probability
            for_count = int(len(posts) * content_probability)
            against_count = int(len(posts) * (1 - content_probability))
            neutral_count = len(posts) - for_count - against_count
        else:
            for_count = len(posts) // 3
            against_count = len(posts) // 3
            neutral_count = len(posts) - for_count - against_count
            for_weight = 0.5
            against_weight = 0.5

        try:
            result = self.llm.chat_json(
                messages=[{
                    "role": "user",
                    "content": PROBABILITY_PROMPT.format(
                        question=question,
                        agent_count=len(set(p.get("agent_id") for p in posts)),
                        action_count=len(posts),
                        for_count=for_count,
                        for_weight=for_weight,
                        against_count=against_count,
                        against_weight=against_weight,
                        neutral_count=neutral_count,
                        trajectory="improving" if (content_probability or 0.5) > 0.55 else
                                   "declining" if (content_probability or 0.5) < 0.45 else "stable",
                        args_for="(see content analysis)",
                        args_against="(see content analysis)",
                    ),
                }],
                temperature=0.3,
                max_tokens=512,
            )
            probability = float(result.get("probability", 0.5))
            return {"probability": max(0.0, min(1.0, probability))}
        except Exception as e:
            logger.warning(f"Report signal extraction 실패: {e}")
            return {"probability": 0.5}

    def _load_actions(self, simulation_dir: str) -> List[Dict]:
        """시뮬레이션 디렉토리에서 actions.jsonl 로드."""
        actions = []
        for platform in ["twitter", "reddit"]:
            path = os.path.join(simulation_dir, platform, "actions.jsonl")
            if not os.path.exists(path):
                continue
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                actions.append(json.loads(line))
                            except json.JSONDecodeError:
                                continue
            except Exception as e:
                logger.warning(f"actions.jsonl 로드 실패 ({path}): {e}")
        return actions

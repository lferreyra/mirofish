"""
Polymarket Prediction Mode — 데이터 모델
"""

import uuid
from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime


# ── Prediction Mode ──

class PredictionMode(str, Enum):
    """
    예측 모드.
    리서치 기반 최적 파라미터:
    - LLM 앙상블 8개 ≈ 유의미한 시작점 (Wisdom of Silicon Crowd, Science Advances 2024)
    - Monte Carlo CI 안정화: N≥20에서 t→z 수렴
    - 에이전트 18명+ 부터 예측시장 정확도 유의미 (Harvard, Bassamboo et al.)
    """
    LOW = "low"      # Scout: 빠른 스크리닝
    MID = "mid"      # Standard: 실전 배팅
    HEAVY = "heavy"  # Maximum: 최고 정확도


@dataclass
class ModeConfig:
    """모드별 설정값"""
    ensemble_size: int
    agent_count: int
    simulation_hours: int
    signal_methods: List[str]  # ["content", "trajectory", "report_agent"]
    use_calibration: bool
    use_cross_validation: bool
    temperature_sweep: bool  # LLM temperature 변이 여부


MODE_CONFIGS: Dict[PredictionMode, ModeConfig] = {
    PredictionMode.LOW: ModeConfig(
        ensemble_size=8,
        agent_count=15,
        simulation_hours=24,
        signal_methods=["content"],
        use_calibration=False,
        use_cross_validation=False,
        temperature_sweep=False,
    ),
    PredictionMode.MID: ModeConfig(
        ensemble_size=20,
        agent_count=30,
        simulation_hours=48,
        signal_methods=["content", "trajectory", "report_agent"],
        use_calibration=False,
        use_cross_validation=False,
        temperature_sweep=False,
    ),
    PredictionMode.HEAVY: ModeConfig(
        ensemble_size=50,
        agent_count=50,
        simulation_hours=72,
        signal_methods=["content", "trajectory", "report_agent"],
        use_calibration=True,
        use_cross_validation=True,
        temperature_sweep=True,
    ),
}


# ── Agent Archetype ──

@dataclass
class AgentArchetype:
    """에이전트 아키타입 정의"""
    role: str           # "strong_bull", "analyst", "contrarian" 등
    label: str          # 사람이 읽을 수 있는 이름
    count: int          # 이 아키타입의 에이전트 수
    stance: str         # "supportive", "opposing", "neutral", "observer"
    sentiment_min: float
    sentiment_max: float
    influence_weight: float = 1.0
    description: str = ""


# Heavy 모드 기본 아키타입 (50명)
HEAVY_ARCHETYPES: List[AgentArchetype] = [
    AgentArchetype("strong_bull", "Strong Bull", 6, "supportive", 0.5, 0.8, 1.0,
                   "강한 찬성론자. 주제에 대해 매우 낙관적."),
    AgentArchetype("moderate_bull", "Moderate Bull", 6, "supportive", 0.2, 0.4, 0.8,
                   "온건한 찬성. 조건부로 긍정적 전망."),
    AgentArchetype("strong_bear", "Strong Bear", 6, "opposing", -0.8, -0.5, 1.0,
                   "강한 반대론자. 주제에 대해 매우 비관적."),
    AgentArchetype("moderate_bear", "Moderate Bear", 6, "opposing", -0.4, -0.2, 0.8,
                   "온건한 반대. 리스크 중심 분석."),
    AgentArchetype("analyst", "Data Analyst", 8, "neutral", -0.1, 0.1, 1.2,
                   "데이터 기반 중립 분석가. 팩트와 통계로 판단."),
    AgentArchetype("contrarian", "Contrarian", 5, "observer", -0.3, 0.3, 0.9,
                   "다수 의견에 반박하는 역할. 군중심리 견제."),
    AgentArchetype("retail", "Retail Trader", 8, "neutral", -0.3, 0.3, 0.6,
                   "일반 투자자/시민. 뉴스와 감정에 영향 받음."),
    AgentArchetype("insider", "Industry Expert", 5, "neutral", -0.1, 0.1, 1.5,
                   "업계 전문가. 깊은 도메인 지식. 높은 영향력."),
]

# Mid 모드 기본 아키타입 (30명)
MID_ARCHETYPES: List[AgentArchetype] = [
    AgentArchetype("bull", "Bull", 7, "supportive", 0.2, 0.6, 1.0, "찬성론자"),
    AgentArchetype("bear", "Bear", 7, "opposing", -0.6, -0.2, 1.0, "반대론자"),
    AgentArchetype("analyst", "Analyst", 6, "neutral", -0.1, 0.1, 1.2, "중립 분석가"),
    AgentArchetype("contrarian", "Contrarian", 3, "observer", -0.3, 0.3, 0.9, "역발상"),
    AgentArchetype("retail", "Retail", 7, "neutral", -0.3, 0.3, 0.6, "일반인"),
]

# Low 모드 기본 아키타입 (15명)
LOW_ARCHETYPES: List[AgentArchetype] = [
    AgentArchetype("bull", "Bull", 4, "supportive", 0.2, 0.6, 1.0, "찬성론자"),
    AgentArchetype("bear", "Bear", 4, "opposing", -0.6, -0.2, 1.0, "반대론자"),
    AgentArchetype("analyst", "Analyst", 4, "neutral", -0.1, 0.1, 1.2, "분석가"),
    AgentArchetype("retail", "Retail", 3, "neutral", -0.3, 0.3, 0.6, "일반인"),
]

DEFAULT_ARCHETYPES: Dict[PredictionMode, List[AgentArchetype]] = {
    PredictionMode.LOW: LOW_ARCHETYPES,
    PredictionMode.MID: MID_ARCHETYPES,
    PredictionMode.HEAVY: HEAVY_ARCHETYPES,
}


# ── Request / Response ──

@dataclass
class PredictionRequest:
    """예측 요청"""
    question: str                           # "Will Bitcoin hit $100K by Dec 2026?"
    mode: PredictionMode = PredictionMode.MID
    market_odds: Optional[float] = None     # 현재 Polymarket 가격 (0.0-1.0)
    resolution_criteria: str = ""           # 해상도 기준
    resolution_date: Optional[str] = None   # ISO date
    category: str = ""                      # "crypto", "politics", "sports"
    relevant_symbols: List[str] = field(default_factory=list)  # ["BTC"]
    platform: str = "twitter"               # "twitter", "reddit", "parallel"

    @property
    def mode_config(self) -> ModeConfig:
        return MODE_CONFIGS[self.mode]


@dataclass
class RunSignal:
    """단일 시뮬레이션 run에서 추출된 신호"""
    run_id: str
    run_index: int
    probability_yes: float          # 0.0-1.0
    sentiment_score: float          # -1.0 to 1.0
    confidence: float               # 0.0-1.0
    agent_count: int
    action_count: int
    dominant_stance: str            # "for" / "against" / "mixed"
    key_arguments_for: List[str] = field(default_factory=list)
    key_arguments_against: List[str] = field(default_factory=list)
    method_scores: Dict[str, float] = field(default_factory=dict)  # {"content": 0.7, "trajectory": 0.6, ...}


@dataclass
class AggregationResult:
    """앙상블 합산 결과"""
    probability: float              # 0.0-1.0
    calibrated_probability: float   # BMA 보정 후
    confidence: float               # 0-100
    std_dev: float
    ci_lower: float                 # 95% CI
    ci_upper: float
    trimmed_n: int                  # trim 후 사용된 run 수
    top_arguments_for: List[str] = field(default_factory=list)
    top_arguments_against: List[str] = field(default_factory=list)


@dataclass
class RiskAssessment:
    """리스크 평가 결과"""
    risk_rating: str                # "safe", "moderate", "risky", "extreme"
    edge: float                     # 우리 확률 - 시장 확률
    kelly_fraction: float           # raw Kelly
    recommended_bet: float          # 조정된 배팅 비율 (0-0.15)
    expected_value: float           # 달러당 EV
    reasoning: str = ""


@dataclass
class PredictionResult:
    """최종 예측 결과"""
    prediction_id: str
    question: str
    mode: str

    # 핵심 결과
    probability: float              # 0-100%
    confidence: float               # 0-100%
    risk_rating: str                # "safe" / "moderate" / "risky" / "extreme"
    recommended_bet_size: float     # 뱅크롤 비율 (0-0.15)
    edge: float                     # 시장 대비 우위
    expected_value: float

    # 앙상블 상세
    ensemble_size: int
    completed_runs: int
    confidence_interval_lower: float
    confidence_interval_upper: float
    std_deviation: float

    # 근거
    key_factors_for: List[str] = field(default_factory=list)
    key_factors_against: List[str] = field(default_factory=list)
    research_summary: str = ""

    # 개별 run 신호
    run_signals: List[RunSignal] = field(default_factory=list)

    # 메타데이터
    market_odds: Optional[float] = None
    created_at: str = ""
    total_duration_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prediction_id": self.prediction_id,
            "question": self.question,
            "mode": self.mode,
            "probability": round(self.probability, 1),
            "confidence": round(self.confidence, 1),
            "risk_rating": self.risk_rating,
            "recommended_bet_size": round(self.recommended_bet_size, 4),
            "edge": round(self.edge, 2),
            "expected_value": round(self.expected_value, 4),
            "ensemble_size": self.ensemble_size,
            "completed_runs": self.completed_runs,
            "confidence_interval": [
                round(self.confidence_interval_lower, 1),
                round(self.confidence_interval_upper, 1),
            ],
            "std_deviation": round(self.std_deviation, 3),
            "key_factors_for": self.key_factors_for[:5],
            "key_factors_against": self.key_factors_against[:5],
            "market_odds": self.market_odds,
            "created_at": self.created_at,
            "total_duration_seconds": round(self.total_duration_seconds, 1),
        }


@dataclass
class QuestionFrame:
    """질문 프레이밍 결과 (LLM이 생성)"""
    simulation_requirement: str     # 시뮬레이션 requirement 문장
    archetypes: List[AgentArchetype]  # 에이전트 아키타입 목록
    initial_posts: List[Dict[str, Any]]  # 초기 게시물
    hot_topics: List[str]           # 핫토픽 키워드
    narrative_direction: str        # 토론 방향
    research_context: str           # 외부 데이터 요약

"""
멀티 계정 매니저
여러 LLM 계정을 관리하고, rate limit 발생 시 자동으로 다른 계정으로 전환합니다.

openclaw 스타일의 cooldown 추적, usage stats, failover 정책을 적용합니다.
Codex 5h/1week rolling window rate limit에 맞는 지수 백오프 적용.
"""

import time
import threading
from typing import Optional, List, Dict, Any, Literal
from dataclasses import dataclass, field
from enum import Enum
from openai import OpenAI

from .codex_oauth import CodexOAuthClient, OAuthError
from ..utils.logger import get_logger

logger = get_logger('mirofish.account_manager')

# ── Thinking / Reasoning ──────────────────────────────────────────────

ThinkLevel = Literal["off", "minimal", "low", "medium", "high", "xhigh"]

THINK_LEVEL_ORDER: Dict[str, int] = {
    "off": 0, "minimal": 1, "low": 2, "medium": 3, "high": 4, "xhigh": 5,
}

# xhigh thinking을 지원하는 모델 패턴
XHIGH_CAPABLE_MODELS = {
    "o3", "o3-mini", "o4-mini",
    "claude-opus-4-6", "claude-sonnet-4-6",
    "gemini-2.5-pro", "gemini-2.5-flash",
}

# OpenAI o-series reasoning_effort 매핑
# OpenAI API는 "low"/"medium"/"high" 만 허용
OPENAI_REASONING_EFFORT_MAP: Dict[str, str] = {
    "off": "low",
    "minimal": "low",
    "low": "low",
    "medium": "medium",
    "high": "high",
    "xhigh": "high",  # xhigh → high (OpenAI는 xhigh 미지원)
}


def normalize_think_level(raw: Optional[str]) -> Optional[ThinkLevel]:
    """사용자 입력을 정규화된 ThinkLevel로 변환합니다."""
    if not raw:
        return None
    key = raw.strip().lower().replace("-", "").replace("_", "")
    mapping = {
        "off": "off", "none": "off", "disable": "off", "disabled": "off",
        "minimal": "minimal", "min": "minimal",
        "low": "low", "on": "low", "enable": "low", "enabled": "low",
        "medium": "medium", "med": "medium", "mid": "medium",
        "high": "high",
        "xhigh": "xhigh", "extrahigh": "xhigh", "veryhigh": "xhigh", "max": "xhigh",
    }
    return mapping.get(key)


def map_to_openai_reasoning_effort(level: ThinkLevel) -> str:
    """ThinkLevel을 OpenAI reasoning_effort 값으로 변환합니다."""
    return OPENAI_REASONING_EFFORT_MAP.get(level, "high")


def supports_xhigh_thinking(model: Optional[str]) -> bool:
    """모델이 xhigh thinking을 지원하는지 확인합니다."""
    if not model:
        return False
    model_lower = _strip_provider_prefix(model).lower()
    for pattern in XHIGH_CAPABLE_MODELS:
        if model_lower.startswith(pattern):
            return True
    return False


def supports_thinking(model: Optional[str]) -> bool:
    """모델이 extended thinking을 지원하는지 확인합니다."""
    if not model:
        return False
    model_lower = _strip_provider_prefix(model).lower()
    thinking_patterns = (
        "o1", "o3", "o4",
        "claude-opus", "claude-sonnet",
        "gemini-2.5",
        "deepseek-r1", "qwq",
    )
    return any(model_lower.startswith(p) for p in thinking_patterns)


def is_openai_reasoning_model(model: Optional[str]) -> bool:
    """OpenAI o-series reasoning 모델인지 확인합니다 (o1, o3, o4 등)."""
    if not model:
        return False
    model_lower = _strip_provider_prefix(model).lower()
    # o1, o1-mini, o1-preview, o3, o3-mini, o4-mini, o4-mini-2025-04-16 등
    return bool(model_lower) and model_lower[0] == 'o' and len(model_lower) > 1 and model_lower[1].isdigit()


def _strip_provider_prefix(model: str) -> str:
    """'openai/o3-mini' → 'o3-mini' 형태에서 provider prefix를 제거합니다."""
    m = model.strip()
    if '/' in m:
        return m.split('/', 1)[1]
    return m


def clamp_think_level(level: ThinkLevel, model: Optional[str]) -> ThinkLevel:
    """모델이 지원하지 않는 thinking level을 하향 조정합니다."""
    if level == "xhigh" and not supports_xhigh_thinking(model):
        logger.info(f"모델 '{model}'이 xhigh를 지원하지 않아 high로 하향 조정")
        return "high"
    if level != "off" and not supports_thinking(model):
        return "off"
    return level


# ── Failure Reasons & Cooldown ────────────────────────────────────────

class FailureReason(str, Enum):
    RATE_LIMIT = "rate_limit"
    AUTH = "auth"
    AUTH_PERMANENT = "auth_permanent"
    BILLING = "billing"
    OVERLOADED = "overloaded"
    TIMEOUT = "timeout"
    MODEL_NOT_FOUND = "model_not_found"
    UNKNOWN = "unknown"


# 연속 오류 시 비활성화 임계값
MAX_ERROR_COUNT_BEFORE_DISABLE = 5

# DISABLED 상태에서 자동 복구 시도까지의 시간 (circuit breaker half-open)
DISABLED_AUTO_RECOVERY_SECONDS = 3600.0  # 1시간


def calculate_cooldown(reason: FailureReason, error_count: int, retry_after: Optional[float] = None) -> float:
    """
    실패 원인과 연속 오류 횟수에 따른 cooldown 시간을 계산합니다.

    Codex rate limit 구조:
    - 5시간 rolling window (primary) — limit 도달 시 reset까지 최대 5h
    - 1주일 rolling window (secondary/team) — limit 도달 시 최대 수 시간~일

    서버가 Retry-After를 보내면 그걸 우선 사용.
    못 가져오면 지수 백오프 적용.
    """
    # 서버가 명시적으로 retry_after를 보냈으면 그걸 존중 (단, 상한선 적용)
    if retry_after is not None and retry_after > 0:
        if reason == FailureReason.RATE_LIMIT:
            # Codex 5h window: 최대 5시간까지 허용
            return min(retry_after, 5 * 3600)
        return min(retry_after, 24 * 3600)

    # 서버가 retry_after를 안 보낸 경우: 원인별 지수 백오프
    n = max(1, error_count)

    if reason == FailureReason.RATE_LIMIT:
        # Codex 5h/1week limit에 맞는 공격적인 백오프
        # 30s → 2m → 10m → 30m → 2h → 5h (cap)
        tiers = [30, 120, 600, 1800, 7200, 18000]
        return tiers[min(n - 1, len(tiers) - 1)]

    if reason == FailureReason.BILLING:
        # 5h × 2^(n-1), max 24h (openclaw 패턴)
        base = 5 * 3600
        return min(base * (2 ** (n - 1)), 24 * 3600)

    if reason == FailureReason.AUTH:
        # 인증 오류: 1h → 4h → 12h (cap)
        tiers = [3600, 14400, 43200]
        return tiers[min(n - 1, len(tiers) - 1)]

    if reason == FailureReason.AUTH_PERMANENT:
        return 24 * 3600  # 24시간

    if reason == FailureReason.MODEL_NOT_FOUND:
        return 24 * 3600  # 24시간

    if reason == FailureReason.OVERLOADED:
        # 30s → 60s → 2m → 5m (cap)
        tiers = [30, 60, 120, 300]
        return tiers[min(n - 1, len(tiers) - 1)]

    if reason == FailureReason.TIMEOUT:
        # 15s → 30s → 60s (cap)
        tiers = [15, 30, 60]
        return tiers[min(n - 1, len(tiers) - 1)]

    # UNKNOWN
    # 30s → 60s → 5m (cap)
    tiers = [30, 60, 300]
    return tiers[min(n - 1, len(tiers) - 1)]


# ── Auth & Account Types ──────────────────────────────────────────────

class AuthType(str, Enum):
    API_KEY = "api_key"
    OAUTH = "oauth"


class AccountStatus(str, Enum):
    AVAILABLE = "available"
    RATE_LIMITED = "rate_limited"
    COOLDOWN = "cooldown"
    DISABLED = "disabled"


@dataclass
class AccountConfig:
    """단일 LLM 계정 설정"""
    name: str
    auth_type: AuthType
    base_url: str
    model: str

    # API Key 인증용
    api_key: Optional[str] = None

    # OAuth 인증용
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    token_url: Optional[str] = None
    oauth_scope: Optional[str] = None
    oauth_audience: Optional[str] = None

    # 우선순위 (낮을수록 높은 우선순위)
    priority: int = 0

    # Thinking 설정
    default_thinking: Optional[str] = None     # 기본 thinking level
    max_thinking_budget: Optional[int] = None  # 최대 thinking budget tokens

    def validate(self):
        if self.auth_type == AuthType.API_KEY and not self.api_key:
            raise ValueError(f"계정 '{self.name}': API key 인증에는 api_key가 필요합니다")
        if self.auth_type == AuthType.OAUTH:
            if not self.client_id or not self.client_secret or not self.token_url:
                raise ValueError(
                    f"계정 '{self.name}': OAuth 인증에는 client_id, client_secret, token_url이 필요합니다"
                )


@dataclass
class UsageStats:
    """openclaw 스타일의 프로필별 사용 통계"""
    last_used: float = 0.0
    cooldown_until: float = 0.0
    cooldown_reason: Optional[FailureReason] = None
    disabled_at: float = 0.0             # DISABLED 전환 시각 (auto-recovery용)
    error_count: int = 0
    total_requests: int = 0
    last_failure_at: float = 0.0
    failure_counts: Dict[str, int] = field(default_factory=dict)


@dataclass
class AccountState:
    """계정의 런타임 상태"""
    config: AccountConfig
    status: AccountStatus = AccountStatus.AVAILABLE
    usage: UsageStats = field(default_factory=UsageStats)
    oauth_client: Optional[CodexOAuthClient] = None
    _openai_client: Optional[OpenAI] = None
    _last_oauth_token: Optional[str] = None  # 토큰 변경 감지용

    def get_openai_client(self) -> OpenAI:
        """해당 계정에 맞는 OpenAI 클라이언트를 반환합니다."""
        if self.config.auth_type == AuthType.OAUTH:
            if not self.oauth_client:
                self.oauth_client = CodexOAuthClient(
                    client_id=self.config.client_id,
                    client_secret=self.config.client_secret,
                    token_url=self.config.token_url,
                    scope=self.config.oauth_scope,
                    audience=self.config.oauth_audience,
                )
            token = self.oauth_client.get_access_token()
            # 토큰이 실제로 변경된 경우에만 클라이언트 재생성
            if self._openai_client is None or token != self._last_oauth_token:
                self._openai_client = OpenAI(
                    api_key=token,
                    base_url=self.config.base_url,
                )
                self._last_oauth_token = token
        else:
            if self._openai_client is None:
                self._openai_client = OpenAI(
                    api_key=self.config.api_key,
                    base_url=self.config.base_url,
                )
        return self._openai_client

    @property
    def is_available(self) -> bool:
        if self.status == AccountStatus.AVAILABLE:
            return True

        if self.status in (AccountStatus.RATE_LIMITED, AccountStatus.COOLDOWN):
            if time.time() >= self.usage.cooldown_until:
                self.status = AccountStatus.AVAILABLE
                self.usage.cooldown_reason = None
                return True
            return False

        if self.status == AccountStatus.DISABLED:
            # Circuit breaker half-open: 일정 시간 후 자동 복구 시도
            if self.usage.disabled_at > 0:
                elapsed = time.time() - self.usage.disabled_at
                if elapsed >= DISABLED_AUTO_RECOVERY_SECONDS:
                    logger.info(
                        f"계정 '{self.config.name}' DISABLED 후 {elapsed / 3600:.1f}시간 경과, "
                        f"half-open 복구 시도"
                    )
                    self.status = AccountStatus.AVAILABLE
                    self.usage.error_count = 0
                    self.usage.cooldown_reason = None
                    return True
            return False

        return False

    def mark_cooldown(self, reason: FailureReason, retry_after: Optional[float] = None):
        """cooldown 상태로 표시합니다."""
        self.usage.error_count += 1
        self.usage.last_failure_at = time.time()
        self.usage.failure_counts[reason.value] = self.usage.failure_counts.get(reason.value, 0) + 1

        # 지수 백오프 cooldown 계산
        cooldown = calculate_cooldown(reason, self.usage.error_count, retry_after)
        self.usage.cooldown_until = time.time() + cooldown
        self.usage.cooldown_reason = reason

        if reason == FailureReason.RATE_LIMIT:
            self.status = AccountStatus.RATE_LIMITED
        else:
            self.status = AccountStatus.COOLDOWN

        # 연속 오류가 임계값 이상이면 비활성화
        if self.usage.error_count >= MAX_ERROR_COUNT_BEFORE_DISABLE:
            self.status = AccountStatus.DISABLED
            self.usage.disabled_at = time.time()
            logger.error(
                f"계정 '{self.config.name}' 연속 {self.usage.error_count}회 오류로 비활성화 "
                f"(원인: {reason.value}), {DISABLED_AUTO_RECOVERY_SECONDS / 3600:.0f}시간 후 자동 복구 시도"
            )
        else:
            logger.warning(
                f"계정 '{self.config.name}' cooldown: reason={reason.value}, "
                f"error_count={self.usage.error_count}, {cooldown:.0f}초 후 재시도"
            )

    def mark_success(self):
        self.usage.error_count = 0
        self.usage.total_requests += 1
        self.usage.last_used = time.time()
        self.usage.cooldown_reason = None
        self.usage.disabled_at = 0.0
        self.status = AccountStatus.AVAILABLE

    @property
    def effective_thinking(self) -> Optional[ThinkLevel]:
        """이 계정의 유효한 thinking level을 반환합니다."""
        raw = self.config.default_thinking
        if not raw:
            return None
        level = normalize_think_level(raw)
        if level:
            return clamp_think_level(level, self.config.model)
        return None


class AccountManager:
    """
    멀티 계정 매니저

    여러 LLM 계정을 관리하며, rate limit 또는 오류 발생 시
    자동으로 다음 사용 가능한 계정으로 전환합니다.

    Codex 5h/1week rolling window rate limit에 맞는 지수 백오프.
    openclaw 스타일의 failover: rotate_profile → surface_error.
    Circuit breaker: 연속 실패 시 DISABLED → 1시간 후 half-open 자동 복구.
    """

    def __init__(self, accounts: Optional[List[AccountConfig]] = None):
        self._accounts: List[AccountState] = []
        self._lock = threading.Lock()

        if accounts:
            for acc in accounts:
                self.add_account(acc)

    def add_account(self, config: AccountConfig):
        """계정을 추가합니다."""
        config.validate()
        state = AccountState(config=config)
        self._accounts.append(state)
        self._accounts.sort(key=lambda a: a.config.priority)
        logger.info(
            f"계정 추가: '{config.name}' (type={config.auth_type.value}, "
            f"model={config.model}, priority={config.priority}, "
            f"thinking={config.default_thinking or 'off'})"
        )

    @property
    def account_count(self) -> int:
        return len(self._accounts)

    def get_available_account(self) -> Optional[AccountState]:
        """사용 가능한 계정을 반환합니다 (우선순위 기반)."""
        with self._lock:
            for account in self._accounts:
                if account.is_available:
                    return account

            # 모든 계정이 cooldown인 경우 로그
            recoverable = [
                a for a in self._accounts
                if a.status in (AccountStatus.RATE_LIMITED, AccountStatus.COOLDOWN)
            ]
            if recoverable:
                earliest = min(recoverable, key=lambda a: a.usage.cooldown_until)
                wait_time = earliest.usage.cooldown_until - time.time()
                if wait_time > 0:
                    logger.info(
                        f"사용 가능한 계정 없음. 가장 빠른 복구: "
                        f"'{earliest.config.name}' {wait_time:.0f}초 후 "
                        f"(reason: {earliest.usage.cooldown_reason})"
                    )
            return None

    def on_failure(
        self,
        account: AccountState,
        reason: FailureReason,
        retry_after: Optional[float] = None,
    ):
        """요청 실패를 처리합니다."""
        with self._lock:
            account.mark_cooldown(reason, retry_after)

    def on_success(self, account: AccountState):
        """요청 성공을 기록합니다."""
        account.mark_success()

    def get_status(self) -> List[Dict[str, Any]]:
        """모든 계정의 상태를 반환합니다."""
        now = time.time()
        result = []
        for acc in self._accounts:
            info = {
                "name": acc.config.name,
                "auth_type": acc.config.auth_type.value,
                "model": acc.config.model,
                "status": acc.status.value,
                "total_requests": acc.usage.total_requests,
                "error_count": acc.usage.error_count,
                "priority": acc.config.priority,
                "thinking": acc.config.default_thinking or "off",
            }
            if acc.status in (AccountStatus.RATE_LIMITED, AccountStatus.COOLDOWN):
                remaining = max(0, acc.usage.cooldown_until - now)
                info["cooldown_remaining_seconds"] = round(remaining, 1)
                info["cooldown_reason"] = acc.usage.cooldown_reason.value if acc.usage.cooldown_reason else None
            elif acc.status == AccountStatus.DISABLED:
                if acc.usage.disabled_at > 0:
                    recovery_in = max(0, (acc.usage.disabled_at + DISABLED_AUTO_RECOVERY_SECONDS) - now)
                    info["auto_recovery_in_seconds"] = round(recovery_in, 1)
            if acc.usage.failure_counts:
                info["failure_counts"] = dict(acc.usage.failure_counts)
            result.append(info)
        return result

    def get_soonest_available_time(self) -> Optional[float]:
        """가장 빨리 사용 가능해지는 시간(seconds from now)을 반환합니다."""
        now = time.time()
        candidates = []

        for a in self._accounts:
            if a.status in (AccountStatus.RATE_LIMITED, AccountStatus.COOLDOWN):
                candidates.append(a.usage.cooldown_until - now)
            elif a.status == AccountStatus.DISABLED and a.usage.disabled_at > 0:
                candidates.append((a.usage.disabled_at + DISABLED_AUTO_RECOVERY_SECONDS) - now)

        if not candidates:
            return None
        return max(0, min(candidates))

    def reset_all(self):
        """모든 계정 상태를 초기화합니다."""
        with self._lock:
            for acc in self._accounts:
                acc.status = AccountStatus.AVAILABLE
                acc.usage = UsageStats()
        logger.info("모든 계정 상태 초기화")

    def reset_account(self, name: str):
        """특정 계정의 상태를 초기화합니다."""
        with self._lock:
            for acc in self._accounts:
                if acc.config.name == name:
                    acc.status = AccountStatus.AVAILABLE
                    acc.usage = UsageStats()
                    logger.info(f"계정 '{name}' 상태 초기화")
                    return

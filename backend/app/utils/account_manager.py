"""
멀티 계정 매니저
여러 LLM 계정을 관리하고, rate limit 발생 시 자동으로 다른 계정으로 전환합니다.

openclaw 스타일의 cooldown 추적, usage stats, failover 정책을 적용합니다.
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


def supports_xhigh_thinking(model: Optional[str]) -> bool:
    """모델이 xhigh thinking을 지원하는지 확인합니다."""
    if not model:
        return False
    model_lower = model.strip().lower()
    for pattern in XHIGH_CAPABLE_MODELS:
        if model_lower.startswith(pattern):
            return True
    return False


def supports_thinking(model: Optional[str]) -> bool:
    """모델이 extended thinking을 지원하는지 확인합니다."""
    if not model:
        return False
    model_lower = model.strip().lower()
    thinking_patterns = (
        "o1", "o3", "o4",
        "claude-opus", "claude-sonnet",
        "gemini-2.5",
        "deepseek-r1", "qwq",
    )
    return any(model_lower.startswith(p) for p in thinking_patterns)


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
    BILLING = "billing"
    OVERLOADED = "overloaded"
    TIMEOUT = "timeout"
    MODEL_NOT_FOUND = "model_not_found"
    UNKNOWN = "unknown"


# openclaw 스타일 cooldown 시간 (ms → seconds)
COOLDOWN_BY_REASON: Dict[FailureReason, float] = {
    FailureReason.RATE_LIMIT: 60.0,
    FailureReason.AUTH: 3600.0,       # 1시간 (영구적 문제일 수 있음)
    FailureReason.BILLING: 7200.0,    # 2시간
    FailureReason.OVERLOADED: 30.0,
    FailureReason.TIMEOUT: 15.0,
    FailureReason.MODEL_NOT_FOUND: 86400.0,  # 24시간
    FailureReason.UNKNOWN: 30.0,
}

MAX_ERROR_COUNT_BEFORE_DISABLE = 5


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
            self._openai_client = OpenAI(
                api_key=token,
                base_url=self.config.base_url,
            )
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
                self.usage.error_count = 0
                self.usage.cooldown_reason = None
                return True
        return False

    def mark_cooldown(self, reason: FailureReason, cooldown_seconds: Optional[float] = None):
        """cooldown 상태로 표시합니다 (openclaw 패턴)."""
        cooldown = cooldown_seconds or COOLDOWN_BY_REASON.get(reason, 60.0)
        self.usage.cooldown_until = time.time() + cooldown
        self.usage.cooldown_reason = reason
        self.usage.last_failure_at = time.time()
        self.usage.error_count += 1
        self.usage.failure_counts[reason.value] = self.usage.failure_counts.get(reason.value, 0) + 1

        if reason == FailureReason.RATE_LIMIT:
            self.status = AccountStatus.RATE_LIMITED
        else:
            self.status = AccountStatus.COOLDOWN

        # 연속 오류가 너무 많으면 비활성화
        if self.usage.error_count >= MAX_ERROR_COUNT_BEFORE_DISABLE:
            self.status = AccountStatus.DISABLED
            logger.error(
                f"계정 '{self.config.name}' 연속 {self.usage.error_count}회 오류로 비활성화 "
                f"(마지막 원인: {reason.value})"
            )
        else:
            logger.warning(
                f"계정 '{self.config.name}' cooldown: reason={reason.value}, "
                f"{cooldown:.0f}초 후 재시도 가능"
            )

    def mark_success(self):
        self.usage.error_count = 0
        self.usage.total_requests += 1
        self.usage.last_used = time.time()
        self.usage.cooldown_reason = None
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

    openclaw 스타일의 failover 정책:
    1. rotate_profile: 다른 계정으로 전환
    2. fallback_model: 같은 계정의 다른 모델로 전환 (해당 시)
    3. surface_error: 모든 계정 실패 시 에러 반환
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

            # 모든 계정이 cooldown인 경우
            recoverable = [
                a for a in self._accounts
                if a.status in (AccountStatus.RATE_LIMITED, AccountStatus.COOLDOWN)
            ]
            if recoverable:
                earliest = min(recoverable, key=lambda a: a.usage.cooldown_until)
                wait_time = earliest.usage.cooldown_until - time.time()
                if wait_time > 0:
                    logger.info(
                        f"모든 계정 cooldown, {wait_time:.0f}초 대기 "
                        f"(계정: '{earliest.config.name}', "
                        f"reason: {earliest.usage.cooldown_reason})"
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
                remaining = max(0, acc.usage.cooldown_until - time.time())
                info["cooldown_remaining_seconds"] = round(remaining, 1)
                info["cooldown_reason"] = acc.usage.cooldown_reason.value if acc.usage.cooldown_reason else None
            if acc.usage.failure_counts:
                info["failure_counts"] = dict(acc.usage.failure_counts)
            result.append(info)
        return result

    def get_soonest_available_time(self) -> Optional[float]:
        """가장 빨리 사용 가능해지는 시간(seconds from now)을 반환합니다."""
        recoverable = [
            a for a in self._accounts
            if a.status in (AccountStatus.RATE_LIMITED, AccountStatus.COOLDOWN)
        ]
        if not recoverable:
            return None
        earliest = min(recoverable, key=lambda a: a.usage.cooldown_until)
        return max(0, earliest.usage.cooldown_until - time.time())

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

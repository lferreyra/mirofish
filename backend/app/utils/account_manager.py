"""
멀티 계정 매니저
여러 LLM 계정을 관리하고, rate limit 발생 시 자동으로 다른 계정으로 전환합니다.
"""

import time
import threading
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from openai import OpenAI

from .codex_oauth import CodexOAuthClient, OAuthError
from ..utils.logger import get_logger

logger = get_logger('mirofish.account_manager')


class AuthType(str, Enum):
    API_KEY = "api_key"
    OAUTH = "oauth"


class AccountStatus(str, Enum):
    AVAILABLE = "available"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"


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

    def validate(self):
        if self.auth_type == AuthType.API_KEY and not self.api_key:
            raise ValueError(f"계정 '{self.name}': API key 인증에는 api_key가 필요합니다")
        if self.auth_type == AuthType.OAUTH:
            if not self.client_id or not self.client_secret or not self.token_url:
                raise ValueError(
                    f"계정 '{self.name}': OAuth 인증에는 client_id, client_secret, token_url이 필요합니다"
                )


@dataclass
class AccountState:
    """계정의 런타임 상태"""
    config: AccountConfig
    status: AccountStatus = AccountStatus.AVAILABLE
    rate_limited_until: float = 0.0
    consecutive_errors: int = 0
    total_requests: int = 0
    oauth_client: Optional[CodexOAuthClient] = None
    _openai_client: Optional[OpenAI] = None

    def get_openai_client(self) -> OpenAI:
        """해당 계정에 맞는 OpenAI 클라이언트를 반환합니다."""
        if self.config.auth_type == AuthType.OAUTH:
            # OAuth: 매 요청마다 최신 토큰 사용
            if not self.oauth_client:
                self.oauth_client = CodexOAuthClient(
                    client_id=self.config.client_id,
                    client_secret=self.config.client_secret,
                    token_url=self.config.token_url,
                    scope=self.config.oauth_scope,
                    audience=self.config.oauth_audience,
                )
            token = self.oauth_client.get_access_token()
            # 토큰이 변경될 수 있으므로 매번 클라이언트 재생성
            self._openai_client = OpenAI(
                api_key=token,
                base_url=self.config.base_url,
            )
        else:
            # API Key: 클라이언트 재사용
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
        if self.status == AccountStatus.RATE_LIMITED:
            if time.time() >= self.rate_limited_until:
                self.status = AccountStatus.AVAILABLE
                self.consecutive_errors = 0
                return True
        return False

    def mark_rate_limited(self, retry_after: float = 60.0):
        """Rate limit 상태로 표시합니다."""
        self.status = AccountStatus.RATE_LIMITED
        self.rate_limited_until = time.time() + retry_after
        logger.warning(
            f"계정 '{self.config.name}' rate limited, "
            f"{retry_after:.0f}초 후 재시도 가능"
        )

    def mark_success(self):
        self.consecutive_errors = 0
        self.total_requests += 1
        self.status = AccountStatus.AVAILABLE

    def mark_error(self):
        self.consecutive_errors += 1
        if self.consecutive_errors >= 3:
            self.status = AccountStatus.ERROR
            logger.error(
                f"계정 '{self.config.name}' 연속 {self.consecutive_errors}회 오류, 비활성화"
            )


class AccountManager:
    """
    멀티 계정 매니저

    여러 LLM 계정을 관리하며, rate limit 또는 오류 발생 시
    자동으로 다음 사용 가능한 계정으로 전환합니다.
    """

    def __init__(self, accounts: Optional[List[AccountConfig]] = None):
        self._accounts: List[AccountState] = []
        self._lock = threading.Lock()
        self._current_index = 0

        if accounts:
            for acc in accounts:
                self.add_account(acc)

    def add_account(self, config: AccountConfig):
        """계정을 추가합니다."""
        config.validate()
        state = AccountState(config=config)
        self._accounts.append(state)
        # 우선순위순 정렬
        self._accounts.sort(key=lambda a: a.config.priority)
        logger.info(
            f"계정 추가: '{config.name}' (type={config.auth_type.value}, "
            f"model={config.model}, priority={config.priority})"
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

            # 모든 계정이 rate limited인 경우, 가장 빨리 풀리는 계정을 대기
            rate_limited = [
                a for a in self._accounts
                if a.status == AccountStatus.RATE_LIMITED
            ]
            if rate_limited:
                earliest = min(rate_limited, key=lambda a: a.rate_limited_until)
                wait_time = earliest.rate_limited_until - time.time()
                if wait_time > 0:
                    logger.info(
                        f"모든 계정 rate limited, {wait_time:.0f}초 대기 "
                        f"(계정: '{earliest.config.name}')"
                    )
                    return None

            return None

    def on_rate_limit(self, account: AccountState, retry_after: Optional[float] = None):
        """Rate limit 발생을 처리합니다."""
        with self._lock:
            cooldown = retry_after if retry_after else 60.0
            account.mark_rate_limited(cooldown)

    def on_success(self, account: AccountState):
        """요청 성공을 기록합니다."""
        account.mark_success()

    def on_error(self, account: AccountState):
        """요청 오류를 기록합니다."""
        account.mark_error()

    def get_status(self) -> List[Dict[str, Any]]:
        """모든 계정의 상태를 반환합니다."""
        result = []
        for acc in self._accounts:
            info = {
                "name": acc.config.name,
                "auth_type": acc.config.auth_type.value,
                "model": acc.config.model,
                "status": acc.status.value,
                "total_requests": acc.total_requests,
                "priority": acc.config.priority,
            }
            if acc.status == AccountStatus.RATE_LIMITED:
                remaining = max(0, acc.rate_limited_until - time.time())
                info["rate_limit_remaining_seconds"] = round(remaining, 1)
            result.append(info)
        return result

    def reset_all(self):
        """모든 계정 상태를 초기화합니다."""
        with self._lock:
            for acc in self._accounts:
                acc.status = AccountStatus.AVAILABLE
                acc.consecutive_errors = 0
                acc.rate_limited_until = 0.0
        logger.info("모든 계정 상태 초기화")

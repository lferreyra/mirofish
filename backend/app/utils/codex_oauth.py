"""
Codex OAuth 클라이언트
OAuth2 client credentials flow를 통한 토큰 발급 및 갱신 지원
"""

import time
import threading
import requests
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from ..utils.logger import get_logger

logger = get_logger('mirofish.codex_oauth')


@dataclass
class OAuthToken:
    """OAuth 토큰 정보"""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600
    refresh_token: Optional[str] = None
    scope: Optional[str] = None
    _issued_at: float = field(default_factory=time.time)

    @property
    def is_expired(self) -> bool:
        """토큰 만료 여부 (만료 60초 전에 갱신)"""
        return time.time() >= (self._issued_at + self.expires_in - 60)

    @property
    def authorization_header(self) -> str:
        return f"{self.token_type} {self.access_token}"


class CodexOAuthClient:
    """
    Codex OAuth2 클라이언트

    Client Credentials Flow 또는 Refresh Token Flow를 사용하여
    액세스 토큰을 발급하고 자동으로 갱신합니다.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        token_url: str,
        scope: Optional[str] = None,
        audience: Optional[str] = None,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = token_url
        self.scope = scope
        self.audience = audience
        self._token: Optional[OAuthToken] = None
        self._lock = threading.Lock()

    def get_access_token(self) -> str:
        """
        유효한 액세스 토큰을 반환합니다.
        만료된 경우 자동으로 갱신합니다.
        """
        with self._lock:
            if self._token is None or self._token.is_expired:
                self._refresh_or_acquire_token()
            return self._token.access_token

    def get_authorization_header(self) -> Dict[str, str]:
        """Authorization 헤더를 반환합니다."""
        token = self.get_access_token()
        return {"Authorization": f"Bearer {token}"}

    def _refresh_or_acquire_token(self):
        """토큰을 갱신하거나 새로 발급합니다."""
        if self._token and self._token.refresh_token:
            try:
                self._do_refresh_token()
                return
            except Exception as e:
                logger.warning(f"토큰 갱신 실패, 새로 발급 시도: {e}")

        self._do_client_credentials()

    def _do_client_credentials(self):
        """Client Credentials Flow로 토큰 발급"""
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        if self.scope:
            data["scope"] = self.scope
        if self.audience:
            data["audience"] = self.audience

        self._request_token(data)

    def _do_refresh_token(self):
        """Refresh Token Flow로 토큰 갱신"""
        data = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self._token.refresh_token,
        }
        self._request_token(data)

    def _request_token(self, data: Dict[str, str]):
        """토큰 엔드포인트에 요청을 보내고 토큰을 저장합니다."""
        try:
            response = requests.post(
                self.token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30,
            )
            response.raise_for_status()
            token_data = response.json()

            self._token = OAuthToken(
                access_token=token_data["access_token"],
                token_type=token_data.get("token_type", "Bearer"),
                expires_in=token_data.get("expires_in", 3600),
                refresh_token=token_data.get("refresh_token"),
                scope=token_data.get("scope"),
            )
            logger.info("OAuth 토큰 발급/갱신 성공")

        except requests.exceptions.RequestException as e:
            logger.error(f"OAuth 토큰 요청 실패: {e}")
            raise OAuthError(f"토큰 요청 실패: {e}") from e

    def invalidate(self):
        """현재 토큰을 무효화합니다 (강제 재발급 트리거)."""
        with self._lock:
            self._token = None


class OAuthError(Exception):
    """OAuth 관련 오류"""
    pass

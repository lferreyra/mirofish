"""
Codex OAuth 클라이언트
PKCE 브라우저 로그인 flow + refresh token 자동 갱신 지원

사용법:
1. 서버 실행 중 POST /api/accounts/oauth/login 호출 → 브라우저 URL 반환
2. 브라우저에서 로그인 → callback으로 토큰 수신
3. 토큰 자동 저장, 이후 자동 갱신
"""

import os
import time
import json
import secrets
import hashlib
import base64
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlencode, urlparse, parse_qs
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
import requests

from ..utils.logger import get_logger

logger = get_logger('mirofish.codex_oauth')

# ── 토큰 저장 경로 ──
TOKEN_STORE_DIR = os.path.join(os.path.dirname(__file__), '../../.oauth_tokens')

# ── Codex OAuth 기본 엔드포인트 ──
DEFAULT_AUTHORIZE_URL = "https://auth.openai.com/authorize"
DEFAULT_TOKEN_URL = "https://auth.openai.com/oauth/token"
DEFAULT_CALLBACK_PORT = 14551
DEFAULT_CALLBACK_PATH = "/auth/callback"


def _ensure_token_store_dir():
    os.makedirs(TOKEN_STORE_DIR, exist_ok=True)
    # 퍼미션 제한 (owner only)
    try:
        os.chmod(TOKEN_STORE_DIR, 0o700)
    except OSError:
        pass


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
        """토큰 만료 여부 (만료 5분 전에 갱신 — openclaw 패턴)"""
        return time.time() >= (self._issued_at + self.expires_in - 300)

    @property
    def authorization_header(self) -> str:
        return f"{self.token_type} {self.access_token}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "access_token": self.access_token,
            "token_type": self.token_type,
            "expires_in": self.expires_in,
            "refresh_token": self.refresh_token,
            "scope": self.scope,
            "_issued_at": self._issued_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OAuthToken':
        return cls(
            access_token=data["access_token"],
            token_type=data.get("token_type", "Bearer"),
            expires_in=data.get("expires_in", 3600),
            refresh_token=data.get("refresh_token"),
            scope=data.get("scope"),
            _issued_at=data.get("_issued_at", time.time()),
        )


# ── PKCE 헬퍼 ──

def _generate_pkce() -> Tuple[str, str]:
    """PKCE code_verifier와 code_challenge를 생성합니다."""
    verifier = secrets.token_urlsafe(64)[:128]
    digest = hashlib.sha256(verifier.encode('ascii')).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b'=').decode('ascii')
    return verifier, challenge


# ── 토큰 파일 저장/로드 ──

def save_token(account_name: str, token: OAuthToken):
    """토큰을 파일에 저장합니다."""
    _ensure_token_store_dir()
    path = os.path.join(TOKEN_STORE_DIR, f"{account_name}.json")
    with open(path, 'w') as f:
        json.dump(token.to_dict(), f, indent=2)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    logger.info(f"토큰 저장: {account_name}")


def load_token(account_name: str) -> Optional[OAuthToken]:
    """저장된 토큰을 로드합니다."""
    path = os.path.join(TOKEN_STORE_DIR, f"{account_name}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        return OAuthToken.from_dict(data)
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"토큰 로드 실패 ({account_name}): {e}")
        return None


class CodexOAuthClient:
    """
    Codex OAuth2 클라이언트

    두 가지 모드 지원:
    1. PKCE 브라우저 로그인 (Codex 사용자 인증)
    2. Client Credentials (서버 간 인증)
    3. Refresh Token 자동 갱신

    PKCE flow:
    - start_login() → 브라우저 URL 반환
    - 사용자가 브라우저에서 로그인
    - callback으로 authorization code 수신
    - code를 token으로 교환
    - refresh token으로 자동 갱신
    """

    def __init__(
        self,
        client_id: str,
        client_secret: Optional[str] = None,
        token_url: Optional[str] = None,
        authorize_url: Optional[str] = None,
        scope: Optional[str] = None,
        audience: Optional[str] = None,
        account_name: Optional[str] = None,
        callback_port: int = DEFAULT_CALLBACK_PORT,
    ):
        self.client_id = client_id
        self.client_secret = client_secret or ""
        self.token_url = token_url or DEFAULT_TOKEN_URL
        self.authorize_url = authorize_url or DEFAULT_AUTHORIZE_URL
        self.scope = scope
        self.audience = audience
        self.account_name = account_name or f"codex-{client_id[:8]}"
        self.callback_port = callback_port
        self._token: Optional[OAuthToken] = None
        self._lock = threading.Lock()
        self._pkce_verifier: Optional[str] = None
        self._pkce_state: Optional[str] = None

        # 저장된 토큰 로드 시도
        saved = load_token(self.account_name)
        if saved:
            self._token = saved
            logger.info(f"저장된 토큰 로드: {self.account_name}")

    def get_access_token(self) -> str:
        """유효한 액세스 토큰을 반환합니다. 만료 시 자동 갱신."""
        with self._lock:
            if self._token is None:
                raise OAuthError(
                    f"계정 '{self.account_name}' 로그인 필요. "
                    f"POST /api/accounts/oauth/login 으로 로그인하세요."
                )
            if self._token.is_expired:
                self._refresh_or_fail()
            return self._token.access_token

    def has_token(self) -> bool:
        """토큰이 있는지 확인합니다."""
        return self._token is not None

    # ── PKCE 브라우저 로그인 ──

    def start_login(self) -> str:
        """
        PKCE OAuth 로그인을 시작합니다.
        브라우저에서 열 URL을 반환합니다.
        """
        self._pkce_verifier, challenge = _generate_pkce()
        self._pkce_state = secrets.token_urlsafe(32)

        callback_url = f"http://127.0.0.1:{self.callback_port}{DEFAULT_CALLBACK_PATH}"

        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": callback_url,
            "state": self._pkce_state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
        if self.scope:
            params["scope"] = self.scope
        if self.audience:
            params["audience"] = self.audience

        url = f"{self.authorize_url}?{urlencode(params)}"
        logger.info(f"OAuth 로그인 시작: {self.account_name}")
        return url

    def start_callback_server(self, timeout: float = 300) -> bool:
        """
        로컬 callback 서버를 시작하고 authorization code를 기다립니다.
        성공 시 True, 타임아웃/실패 시 False.
        """
        result = {"code": None, "error": None}
        expected_state = self._pkce_state

        class CallbackHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urlparse(self.path)
                if parsed.path != DEFAULT_CALLBACK_PATH:
                    self.send_response(404)
                    self.end_headers()
                    return

                params = parse_qs(parsed.query)
                state = params.get("state", [None])[0]
                code = params.get("code", [None])[0]
                error = params.get("error", [None])[0]

                if state != expected_state:
                    result["error"] = "state mismatch"
                elif error:
                    result["error"] = error
                elif code:
                    result["code"] = code
                else:
                    result["error"] = "no code received"

                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                if result["code"]:
                    self.wfile.write(b"<html><body><h2>Login successful!</h2><p>You can close this tab.</p></body></html>")
                else:
                    self.wfile.write(f"<html><body><h2>Login failed</h2><p>{result['error']}</p></body></html>".encode())

            def log_message(self, format, *args):
                pass  # suppress default logging

        server = HTTPServer(("127.0.0.1", self.callback_port), CallbackHandler)
        server.timeout = timeout

        logger.info(f"Callback 서버 시작: 127.0.0.1:{self.callback_port}")
        server.handle_request()
        server.server_close()

        if result["code"]:
            self._exchange_code(result["code"])
            return True
        else:
            logger.error(f"OAuth 로그인 실패: {result['error']}")
            return False

    def handle_callback_code(self, code: str, state: Optional[str] = None):
        """
        수동으로 authorization code를 처리합니다.
        (callback 서버 대신 직접 code를 붙여넣는 경우)
        """
        if state and self._pkce_state and state != self._pkce_state:
            raise OAuthError("state 불일치")
        self._exchange_code(code)

    def _exchange_code(self, code: str):
        """Authorization code를 token으로 교환합니다."""
        callback_url = f"http://127.0.0.1:{self.callback_port}{DEFAULT_CALLBACK_PATH}"

        data = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "code": code,
            "redirect_uri": callback_url,
            "code_verifier": self._pkce_verifier,
        }
        if self.client_secret:
            data["client_secret"] = self.client_secret

        self._request_token(data)
        self._pkce_verifier = None
        self._pkce_state = None

    # ── Token 관리 ──

    def set_tokens(self, access_token: str, refresh_token: Optional[str] = None,
                   expires_in: int = 3600):
        """외부에서 토큰을 직접 설정합니다 (다른 방법으로 토큰을 받은 경우)."""
        with self._lock:
            self._token = OAuthToken(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=expires_in,
            )
            save_token(self.account_name, self._token)
            logger.info(f"토큰 직접 설정: {self.account_name}")

    def _refresh_or_fail(self):
        """토큰을 갱신합니다. refresh_token이 없으면 에러."""
        if self._token and self._token.refresh_token:
            try:
                self._do_refresh_token()
                return
            except Exception as e:
                logger.warning(f"토큰 갱신 실패: {e}")

        # client_secret이 있으면 client_credentials 시도
        if self.client_secret:
            try:
                self._do_client_credentials()
                return
            except Exception as e:
                logger.warning(f"Client credentials 실패: {e}")

        raise OAuthError(
            f"계정 '{self.account_name}' 토큰 만료, 재로그인 필요. "
            f"POST /api/accounts/oauth/login 으로 로그인하세요."
        )

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
            "refresh_token": self._token.refresh_token,
        }
        if self.client_secret:
            data["client_secret"] = self.client_secret
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

            # refresh_token이 새로 안 오면 기존 것 유지 (RFC 6749 §6)
            new_refresh = token_data.get("refresh_token")
            if not new_refresh and self._token:
                new_refresh = self._token.refresh_token

            self._token = OAuthToken(
                access_token=token_data["access_token"],
                token_type=token_data.get("token_type", "Bearer"),
                expires_in=token_data.get("expires_in", 3600),
                refresh_token=new_refresh,
                scope=token_data.get("scope"),
            )
            save_token(self.account_name, self._token)
            logger.info(f"OAuth 토큰 발급/갱신 성공: {self.account_name}")

        except requests.exceptions.RequestException as e:
            logger.error(f"OAuth 토큰 요청 실패: {e}")
            raise OAuthError(f"토큰 요청 실패: {e}") from e

    def invalidate(self):
        """현재 토큰을 무효화합니다."""
        with self._lock:
            self._token = None


class OAuthError(Exception):
    """OAuth 관련 오류"""
    pass

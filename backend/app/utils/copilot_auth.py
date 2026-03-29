"""
GitHub Copilot Token Exchange
Exchanges a GitHub token for a short-lived Copilot API token,
enabling use of GitHub Copilot subscription as an LLM provider.

Auth flow (mirrors OpenClaw's github-copilot extension):
  1. Take a GitHub token (PAT, GH_TOKEN, GITHUB_TOKEN, etc.)
  2. POST to api.github.com/copilot_internal/v2/token → short-lived Copilot token + proxy-ep
  3. Derive the OpenAI-compatible base URL from proxy-ep
  4. Cache token locally, auto-refresh when expired
"""

import os
import json
import re
import time
import threading
from typing import Optional, Dict, Any

from .logger import get_logger

logger = get_logger('mirofish.copilot_auth')

# GitHub Copilot internal token exchange endpoint
COPILOT_TOKEN_URL = "https://api.github.com/copilot_internal/v2/token"

# Default base URL when proxy-ep cannot be derived
DEFAULT_COPILOT_API_BASE_URL = "https://api.individual.githubcopilot.com"

# Safety margin: refresh token 5 minutes before expiry
TOKEN_REFRESH_MARGIN_SECONDS = 5 * 60

# Headers to mimic a Copilot client (required by the API)
COPILOT_REQUEST_HEADERS = {
    "Accept": "application/json",
    "Editor-Version": "vscode/1.96.2",
    "User-Agent": "GitHubCopilotChat/0.26.7",
    "X-Github-Api-Version": "2025-04-01",
}


class CopilotTokenManager:
    """
    Manages GitHub Copilot API token lifecycle:
    - Exchange GitHub token for Copilot API token
    - Cache token in memory and optionally on disk
    - Auto-refresh before expiry
    - Thread-safe access

    Usage:
        manager = CopilotTokenManager(github_token="ghp_xxx")
        api_key = manager.get_api_key()
        base_url = manager.get_base_url()
    """

    def __init__(
        self,
        github_token: str,
        cache_dir: Optional[str] = None,
    ):
        self._github_token = github_token
        self._lock = threading.Lock()

        # In-memory cache
        self._cached_token: Optional[str] = None
        self._cached_base_url: str = DEFAULT_COPILOT_API_BASE_URL
        self._expires_at: float = 0  # epoch seconds

        # Disk cache path
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)
            self._cache_path = os.path.join(cache_dir, "copilot-token.json")
        else:
            self._cache_path = None

        # Try loading from disk cache on init
        self._load_disk_cache()

    def get_api_key(self) -> str:
        """
        Get a valid Copilot API token. Refreshes automatically if expired.
        Thread-safe.
        """
        with self._lock:
            if self._is_token_valid():
                return self._cached_token
        # Release lock during network call, then re-acquire to store
        return self._refresh_token()

    def get_base_url(self) -> str:
        """
        Get the Copilot API base URL (derived from the token's proxy-ep).
        Ensures a valid token exists first.
        """
        # Ensure we have a valid token (which sets base_url)
        self.get_api_key()
        with self._lock:
            return self._cached_base_url

    def _is_token_valid(self) -> bool:
        """Check if cached token is still usable (with safety margin)."""
        if not self._cached_token:
            return False
        return time.time() < (self._expires_at - TOKEN_REFRESH_MARGIN_SECONDS)

    def _refresh_token(self) -> str:
        """Exchange GitHub token for a fresh Copilot API token."""
        import urllib.request
        import urllib.error

        logger.info("Exchanging GitHub token for Copilot API token...")

        headers = {
            **COPILOT_REQUEST_HEADERS,
            "Authorization": f"Bearer {self._github_token}",
        }

        req = urllib.request.Request(
            COPILOT_TOKEN_URL,
            method="GET",
            headers=headers,
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace") if e.fp else ""
            logger.error(
                "Copilot token exchange failed: HTTP %d — %s", e.code, body
            )
            raise RuntimeError(
                f"GitHub Copilot token exchange failed (HTTP {e.code}). "
                "Ensure your GitHub token is valid and you have an active Copilot subscription."
            ) from e
        except Exception as e:
            logger.error("Copilot token exchange error: %s", e)
            raise RuntimeError(
                f"GitHub Copilot token exchange failed: {e}"
            ) from e

        token = data.get("token", "")
        expires_at_unix = data.get("expires_at", 0)

        if not token:
            raise RuntimeError(
                "Copilot token exchange returned empty token. "
                "Check your GitHub Copilot subscription status."
            )

        # expires_at from the API is in seconds since epoch
        if isinstance(expires_at_unix, (int, float)):
            expires_at = float(expires_at_unix)
        else:
            # Fallback: assume 30 minutes from now
            expires_at = time.time() + 1800

        base_url = self._derive_base_url_from_token(token)

        with self._lock:
            self._cached_token = token
            self._expires_at = expires_at
            self._cached_base_url = base_url

        # Persist to disk
        self._save_disk_cache(token, expires_at)

        logger.info(
            "Copilot token acquired (expires in %d min), base_url=%s",
            int((expires_at - time.time()) / 60),
            base_url,
        )

        return token

    @staticmethod
    def _derive_base_url_from_token(token: str) -> str:
        """
        Derive the OpenAI-compatible API base URL from the Copilot token.

        The token contains semicolon-delimited key=value pairs.
        The proxy-ep field indicates which proxy endpoint to use.
        Convert proxy.* → api.* (matching OpenClaw's behavior).
        """
        match = re.search(r"(?:^|;)\s*proxy-ep=([^;\s]+)", token, re.IGNORECASE)
        if not match:
            return DEFAULT_COPILOT_API_BASE_URL

        proxy_ep = match.group(1).strip()
        if not proxy_ep:
            return DEFAULT_COPILOT_API_BASE_URL

        # Strip protocol, replace proxy. prefix with api.
        host = re.sub(r"^https?://", "", proxy_ep)
        host = re.sub(r"^proxy\.", "api.", host, flags=re.IGNORECASE)

        if not host:
            return DEFAULT_COPILOT_API_BASE_URL

        return f"https://{host}"

    def _load_disk_cache(self):
        """Load cached token from disk if available and valid."""
        if not self._cache_path or not os.path.exists(self._cache_path):
            return
        try:
            with open(self._cache_path, "r") as f:
                data = json.load(f)
            token = data.get("token", "")
            expires_at = data.get("expires_at", 0)
            if token and time.time() < (expires_at - TOKEN_REFRESH_MARGIN_SECONDS):
                self._cached_token = token
                self._expires_at = expires_at
                self._cached_base_url = self._derive_base_url_from_token(token)
                logger.debug("Loaded Copilot token from disk cache")
        except Exception as e:
            logger.debug("Could not load Copilot token cache: %s", e)

    def _save_disk_cache(self, token: str, expires_at: float):
        """Persist token to disk for cross-process reuse."""
        if not self._cache_path:
            return
        try:
            data = {
                "token": token,
                "expires_at": expires_at,
                "updated_at": time.time(),
            }
            with open(self._cache_path, "w") as f:
                json.dump(data, f)
            logger.debug("Saved Copilot token to disk cache")
        except Exception as e:
            logger.debug("Could not save Copilot token cache: %s", e)


def resolve_github_token() -> Optional[str]:
    """
    Resolve a GitHub token from environment variables.
    Checks (in priority order): COPILOT_GITHUB_TOKEN, GH_TOKEN, GITHUB_TOKEN.
    Returns None if no token is found.
    """
    for var in ("COPILOT_GITHUB_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"):
        token = os.environ.get(var, "").strip()
        if token:
            logger.debug("Resolved GitHub token from %s", var)
            return token
    return None


def is_copilot_provider() -> bool:
    """
    Check if the user has configured GitHub Copilot as their LLM provider.
    Returns True if LLM_PROVIDER is set to 'github-copilot' or
    if a GitHub token is available and no LLM_API_KEY is set.
    """
    provider = os.environ.get("LLM_PROVIDER", "").strip().lower()
    if provider == "github-copilot":
        return True

    # Auto-detect: if no LLM_API_KEY but a GitHub token exists
    llm_key = os.environ.get("LLM_API_KEY", "").strip()
    if not llm_key and resolve_github_token():
        return True

    return False


# Module-level singleton (lazy-initialized)
_token_manager: Optional[CopilotTokenManager] = None
_manager_lock = threading.Lock()


def get_copilot_token_manager() -> CopilotTokenManager:
    """
    Get or create the singleton CopilotTokenManager.
    Thread-safe lazy initialization.
    """
    global _token_manager
    if _token_manager is not None:
        return _token_manager

    with _manager_lock:
        if _token_manager is not None:
            return _token_manager

        github_token = resolve_github_token()
        if not github_token:
            raise RuntimeError(
                "GitHub Copilot provider is enabled but no GitHub token found. "
                "Set COPILOT_GITHUB_TOKEN, GH_TOKEN, or GITHUB_TOKEN in your .env file."
            )

        # Cache directory inside the backend data directory
        cache_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "uploads",
            ".copilot-cache",
        )

        _token_manager = CopilotTokenManager(
            github_token=github_token,
            cache_dir=cache_dir,
        )
        return _token_manager

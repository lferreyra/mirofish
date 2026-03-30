"""
GitHub Copilot token exchange.

Auth flow:
  1. Take a GitHub PAT (from COPILOT_GITHUB_TOKEN / GH_TOKEN / GITHUB_TOKEN)
  2. POST to api.github.com/copilot_internal/v2/token → short-lived Copilot token
  3. Derive the OpenAI-compatible base URL from the token's proxy-ep field
  4. Cache the token in memory and on disk; auto-refresh before expiry

Note: Uses the same undocumented endpoint as VS Code Copilot. Tokens expire in ~30 min.
"""

import json
import os
import re
import threading
import time
from typing import Optional

from .logger import get_logger

logger = get_logger('mirofish.copilot_auth')

COPILOT_TOKEN_URL = "https://api.github.com/copilot_internal/v2/token"
DEFAULT_COPILOT_BASE_URL = "https://api.individual.githubcopilot.com"
TOKEN_REFRESH_MARGIN = 5 * 60  # refresh 5 min before expiry

# Headers required to pass GitHub's Copilot client check
COPILOT_REQUEST_HEADERS = {
    "Accept": "application/json",
    "Editor-Version": "vscode/1.96.2",
    "User-Agent": "GitHubCopilotChat/0.26.7",
    "X-Github-Api-Version": "2025-04-01",
}


class CopilotTokenManager:
    """
    Manages GitHub Copilot API token lifecycle.
    Thread-safe; caches token in memory and optionally on disk.

    Usage:
        mgr = CopilotTokenManager(github_token="ghp_xxx")
        api_key  = mgr.get_api_key()
        base_url = mgr.get_base_url()
    """

    def __init__(self, github_token: str, cache_dir: Optional[str] = None):
        self._github_token = github_token
        self._lock = threading.Lock()
        self._cached_token: Optional[str] = None
        self._cached_base_url: str = DEFAULT_COPILOT_BASE_URL
        self._expires_at: float = 0

        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)
            self._cache_path = os.path.join(cache_dir, "copilot-token.json")
        else:
            self._cache_path = None

        self._load_disk_cache()

    def get_api_key(self) -> str:
        """Return a valid Copilot API token, refreshing if necessary. Thread-safe."""
        with self._lock:
            if self._is_valid():
                return self._cached_token
        return self._refresh()

    def get_base_url(self) -> str:
        """Return the Copilot API base URL. Ensures a valid token exists first."""
        self.get_api_key()
        with self._lock:
            return self._cached_base_url

    def _is_valid(self) -> bool:
        return bool(self._cached_token) and time.time() < (self._expires_at - TOKEN_REFRESH_MARGIN)

    def _refresh(self) -> str:
        import urllib.request
        import urllib.error

        logger.info("Exchanging GitHub token for Copilot API token...")
        headers = {**COPILOT_REQUEST_HEADERS, "Authorization": f"Bearer {self._github_token}"}
        req = urllib.request.Request(COPILOT_TOKEN_URL, method="GET", headers=headers)

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            body = (e.read() or b"").decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Copilot token exchange failed (HTTP {e.code}): {body}. "
                "Check your GitHub token and Copilot subscription."
            ) from e
        except Exception as e:
            raise RuntimeError(f"Copilot token exchange error: {e}") from e

        token = data.get("token", "")
        if not token:
            raise RuntimeError(
                "Copilot token exchange returned empty token. "
                "Check your GitHub Copilot subscription status."
            )

        expires_at = float(data.get("expires_at", time.time() + 1800))
        base_url = self._derive_base_url(token)

        with self._lock:
            self._cached_token = token
            self._expires_at = expires_at
            self._cached_base_url = base_url

        self._save_disk_cache(token, expires_at)
        logger.info(
            "Copilot token acquired (expires in %d min), base_url=%s",
            int((expires_at - time.time()) / 60),
            base_url,
        )
        return token

    @staticmethod
    def _derive_base_url(token: str) -> str:
        """Derive API base URL from the proxy-ep field embedded in the token."""
        match = re.search(r"(?:^|;)\s*proxy-ep=([^;\s]+)", token, re.IGNORECASE)
        if not match:
            return DEFAULT_COPILOT_BASE_URL
        host = re.sub(r"^https?://", "", match.group(1).strip())
        host = re.sub(r"^proxy\.", "api.", host, flags=re.IGNORECASE)
        return f"https://{host}" if host else DEFAULT_COPILOT_BASE_URL

    def _load_disk_cache(self):
        if not self._cache_path or not os.path.exists(self._cache_path):
            return
        try:
            with open(self._cache_path) as f:
                data = json.load(f)
            token = data.get("token", "")
            expires_at = data.get("expires_at", 0)
            if token and time.time() < (expires_at - TOKEN_REFRESH_MARGIN):
                self._cached_token = token
                self._expires_at = expires_at
                self._cached_base_url = self._derive_base_url(token)
                logger.debug("Loaded Copilot token from disk cache")
        except Exception as e:
            logger.debug("Could not load Copilot token cache: %s", e)

    def _save_disk_cache(self, token: str, expires_at: float):
        if not self._cache_path:
            return
        try:
            with open(self._cache_path, "w") as f:
                json.dump({"token": token, "expires_at": expires_at, "updated_at": time.time()}, f)
        except Exception as e:
            logger.debug("Could not save Copilot token cache: %s", e)


def resolve_github_token() -> Optional[str]:
    """Check COPILOT_GITHUB_TOKEN, GH_TOKEN, GITHUB_TOKEN in priority order."""
    for var in ("COPILOT_GITHUB_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"):
        token = os.environ.get(var, "").strip()
        if token:
            logger.debug("GitHub token resolved from %s", var)
            return token
    return None


# Module-level singleton
_manager: Optional[CopilotTokenManager] = None
_manager_lock = threading.Lock()


def get_copilot_token_manager() -> CopilotTokenManager:
    """Return the singleton CopilotTokenManager, creating it on first call."""
    global _manager
    if _manager is not None:
        return _manager
    with _manager_lock:
        if _manager is not None:
            return _manager
        github_token = resolve_github_token()
        if not github_token:
            raise RuntimeError(
                "github-copilot provider requires a GitHub token. "
                "Set COPILOT_GITHUB_TOKEN, GH_TOKEN, or GITHUB_TOKEN in .env."
            )
        cache_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "uploads", ".copilot-cache"
        )
        _manager = CopilotTokenManager(github_token=github_token, cache_dir=cache_dir)
    return _manager

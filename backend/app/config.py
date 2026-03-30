"""
Configuration management.
Loads settings from the .env file at the project root (MiroFish/.env).
"""

import os
import shutil
from dotenv import load_dotenv

# Load .env from project root — path relative to backend/app/config.py
_project_root_env = os.path.join(os.path.dirname(__file__), '../../.env')

if os.path.exists(_project_root_env):
    load_dotenv(_project_root_env, override=True)
else:
    # No .env at root — fall back to environment variables (production mode)
    load_dotenv(override=True)


class Config:
    """Flask configuration class."""

    # ── Flask ────────────────────────────────────────────────────────────────
    SECRET_KEY = os.environ.get('SECRET_KEY', 'mirofish-secret-key')
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'

    # Disable ASCII escaping so non-ASCII characters display correctly in JSON
    JSON_AS_ASCII = False

    # ── LLM provider selection ────────────────────────────────────────────────
    # Supported values:
    #   auto (default) — infer from LLM_MODEL_NAME and available env vars
    #   openai         — OpenAI SDK (works with any OpenAI-compatible API)
    #   anthropic      — Anthropic Claude SDK (direct API, requires LLM_API_KEY)
    #   github-copilot — GitHub Copilot via token exchange (requires GITHUB_TOKEN)
    #   ollama         — Local Ollama via OpenAI-compatible endpoint
    #   claude         — Claude CLI subprocess (requires `claude` CLI installed)
    LLM_PROVIDER = os.environ.get('LLM_PROVIDER', 'auto')

    # ── LLM credentials & model ──────────────────────────────────────────────
    LLM_API_KEY = os.environ.get('LLM_API_KEY')
    LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://api.openai.com/v1')
    LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME', 'gpt-4o-mini')

    # Optional: faster/cheaper secondary LLM for non-critical calls
    LLM_BOOST_API_KEY = os.environ.get('LLM_BOOST_API_KEY')
    LLM_BOOST_BASE_URL = os.environ.get('LLM_BOOST_BASE_URL')
    LLM_BOOST_MODEL_NAME = os.environ.get('LLM_BOOST_MODEL_NAME')

    # ── Provider-specific settings ───────────────────────────────────────────
    # Claude CLI: path to the `claude` executable (used when LLM_PROVIDER=claude)
    CLAUDE_CLI_PATH = os.environ.get('CLAUDE_CLI_PATH', 'claude')

    # GitHub Copilot: token env vars (checked in priority order)
    # COPILOT_GITHUB_TOKEN > GH_TOKEN > GITHUB_TOKEN
    GITHUB_TOKEN = (
        os.environ.get('COPILOT_GITHUB_TOKEN')
        or os.environ.get('GH_TOKEN')
        or os.environ.get('GITHUB_TOKEN')
    )

    @classmethod
    def get_resolved_provider(cls) -> str:
        """
        Resolve the effective LLM provider.

        In 'auto' mode the provider is inferred:
          1. Model name starts with 'claude-'  → anthropic
          2. GitHub token present, no API key  → github-copilot
          3. Otherwise                         → openai
        """
        provider = (cls.LLM_PROVIDER or 'auto').lower()
        if provider != 'auto':
            return provider

        model = (cls.LLM_MODEL_NAME or '').lower()
        if model.startswith('claude-'):
            return 'anthropic'
        if cls.GITHUB_TOKEN and not cls.LLM_API_KEY:
            return 'github-copilot'
        return 'openai'

    # ── Zep memory graph ─────────────────────────────────────────────────────
    ZEP_API_KEY = os.environ.get('ZEP_API_KEY')

    # ── File uploads ─────────────────────────────────────────────────────────
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '../uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'md', 'txt', 'markdown'}

    # ── Text chunking ────────────────────────────────────────────────────────
    DEFAULT_CHUNK_SIZE = 500
    DEFAULT_CHUNK_OVERLAP = 50

    # ── OASIS simulation ─────────────────────────────────────────────────────
    OASIS_DEFAULT_MAX_ROUNDS = int(os.environ.get('OASIS_DEFAULT_MAX_ROUNDS', '10'))
    OASIS_SIMULATION_DATA_DIR = os.path.join(
        os.path.dirname(__file__), '../uploads/simulations'
    )

    OASIS_TWITTER_ACTIONS = [
        'CREATE_POST', 'LIKE_POST', 'REPOST', 'FOLLOW', 'DO_NOTHING', 'QUOTE_POST',
    ]
    OASIS_REDDIT_ACTIONS = [
        'LIKE_POST', 'DISLIKE_POST', 'CREATE_POST', 'CREATE_COMMENT',
        'LIKE_COMMENT', 'DISLIKE_COMMENT', 'SEARCH_POSTS', 'SEARCH_USER',
        'TREND', 'REFRESH', 'DO_NOTHING', 'FOLLOW', 'MUTE',
    ]

    # ── Report Agent ─────────────────────────────────────────────────────────
    REPORT_AGENT_MAX_TOOL_CALLS = int(os.environ.get('REPORT_AGENT_MAX_TOOL_CALLS', '5'))
    REPORT_AGENT_MAX_REFLECTION_ROUNDS = int(
        os.environ.get('REPORT_AGENT_MAX_REFLECTION_ROUNDS', '2')
    )
    REPORT_AGENT_TEMPERATURE = float(os.environ.get('REPORT_AGENT_TEMPERATURE', '0.5'))

    @classmethod
    def validate(cls):
        """Validate required configuration and return a list of error strings."""
        import logging
        log = logging.getLogger('mirofish.config')
        errors = []
        provider = cls.get_resolved_provider()

        if provider == 'anthropic':
            if not cls.LLM_API_KEY:
                errors.append(
                    "LLM_API_KEY is required for the anthropic provider. "
                    "Get a key at https://console.anthropic.com/settings/keys"
                )
        elif provider == 'openai':
            if not cls.LLM_API_KEY:
                errors.append("LLM_API_KEY is not configured (required for openai provider)")
        elif provider == 'github-copilot':
            if not cls.GITHUB_TOKEN:
                errors.append(
                    "github-copilot provider requires a GitHub token. "
                    "Set COPILOT_GITHUB_TOKEN, GH_TOKEN, or GITHUB_TOKEN in .env."
                )
        elif provider == 'ollama':
            if cls.LLM_BASE_URL and '11434' not in cls.LLM_BASE_URL:
                log.warning(
                    "LLM_BASE_URL (%s) doesn't include port 11434; "
                    "make sure Ollama is reachable at that address.",
                    cls.LLM_BASE_URL,
                )
        elif provider == 'claude':
            if shutil.which(cls.CLAUDE_CLI_PATH) is None:
                errors.append(
                    f"Claude CLI not found at '{cls.CLAUDE_CLI_PATH}'. "
                    "Install it (https://claude.ai/download) or set CLAUDE_CLI_PATH in .env."
                )

        if not cls.ZEP_API_KEY:
            errors.append(
                "ZEP_API_KEY is not configured. "
                "Get a free key at https://app.getzep.com/"
            )
        return errors

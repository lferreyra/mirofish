"""
Configuration management
Loads configuration from the .env file at the project root
"""

import os
import shutil
from dotenv import load_dotenv

# Load .env from the project root
# Path: MiroFish/.env (relative to backend/app/config.py)
project_root_env = os.path.join(os.path.dirname(__file__), '../../.env')

if os.path.exists(project_root_env):
    load_dotenv(project_root_env, override=True)
else:
    # If no .env at root, try loading environment variables (for production)
    load_dotenv(override=True)


class Config:
    """Flask configuration class"""

    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'mirofish-secret-key')
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'

    # JSON settings - disable ASCII escaping so non-ASCII characters display correctly
    JSON_AS_ASCII = False

    # LLM provider: "claude" (default), "openai", or "ollama"
    LLM_PROVIDER = os.environ.get('LLM_PROVIDER', 'claude')

    # LLM settings
    LLM_API_KEY = os.environ.get('LLM_API_KEY')
    LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://api.openai.com/v1')
    LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME', 'sonnet')

    # Claude CLI path (only used when LLM_PROVIDER=claude)
    CLAUDE_CLI_PATH = os.environ.get('CLAUDE_CLI_PATH', 'claude')

    # Zep settings
    ZEP_API_KEY = os.environ.get('ZEP_API_KEY')

    # File upload settings
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '../uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'md', 'txt', 'markdown'}

    # Text processing settings
    DEFAULT_CHUNK_SIZE = 500
    DEFAULT_CHUNK_OVERLAP = 50

    # OASIS simulation settings
    OASIS_DEFAULT_MAX_ROUNDS = int(os.environ.get('OASIS_DEFAULT_MAX_ROUNDS', '10'))
    OASIS_SIMULATION_DATA_DIR = os.path.join(os.path.dirname(__file__), '../uploads/simulations')

    # OASIS platform available actions
    OASIS_TWITTER_ACTIONS = [
        'CREATE_POST', 'LIKE_POST', 'REPOST', 'FOLLOW', 'DO_NOTHING', 'QUOTE_POST'
    ]
    OASIS_REDDIT_ACTIONS = [
        'LIKE_POST', 'DISLIKE_POST', 'CREATE_POST', 'CREATE_COMMENT',
        'LIKE_COMMENT', 'DISLIKE_COMMENT', 'SEARCH_POSTS', 'SEARCH_USER',
        'TREND', 'REFRESH', 'DO_NOTHING', 'FOLLOW', 'MUTE'
    ]

    # Report Agent settings
    REPORT_AGENT_MAX_TOOL_CALLS = int(os.environ.get('REPORT_AGENT_MAX_TOOL_CALLS', '5'))
    REPORT_AGENT_MAX_REFLECTION_ROUNDS = int(os.environ.get('REPORT_AGENT_MAX_REFLECTION_ROUNDS', '2'))
    REPORT_AGENT_TEMPERATURE = float(os.environ.get('REPORT_AGENT_TEMPERATURE', '0.5'))

    @classmethod
    def validate(cls):
        """Validate required configuration."""
        import logging
        log = logging.getLogger('mirofish.config')
        errors = []

        provider = cls.LLM_PROVIDER

        if provider == "claude":
            if shutil.which(cls.CLAUDE_CLI_PATH) is None:
                errors.append(
                    f"Claude CLI not found at '{cls.CLAUDE_CLI_PATH}'. "
                    "Install it or set CLAUDE_CLI_PATH."
                )
        elif provider == "openai":
            if not cls.LLM_API_KEY:
                errors.append("LLM_API_KEY is not configured (required for openai provider)")
        elif provider == "ollama":
            if cls.LLM_BASE_URL and "11434" not in cls.LLM_BASE_URL:
                log.warning(
                    "LLM_BASE_URL (%s) does not contain port 11434; "
                    "make sure Ollama is reachable.",
                    cls.LLM_BASE_URL,
                )
        else:
            errors.append(f"Unknown LLM_PROVIDER: '{provider}' (expected claude, openai, or ollama)")

        if not cls.ZEP_API_KEY:
            errors.append("ZEP_API_KEY is not configured")

        return errors

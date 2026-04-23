"""
配置管理
统一从项目根目录的 .env 文件加载配置
"""

import os
from dotenv import load_dotenv

# 加载项目根目录的 .env 文件
# 路径: MiroFish/.env (相对于 backend/app/config.py)
project_root_env = os.path.join(os.path.dirname(__file__), '../../.env')

if os.path.exists(project_root_env):
    load_dotenv(project_root_env, override=True)
else:
    # 如果根目录没有 .env，尝试加载环境变量（用于生产环境）
    load_dotenv(override=True)


class Config:
    """Flask配置类"""
    
    # Flask配置
    SECRET_KEY = os.environ.get('SECRET_KEY', 'mirofish-secret-key')
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    # JSON配置 - 禁用ASCII转义，让中文直接显示（而不是 \uXXXX 格式）
    JSON_AS_ASCII = False
    
    # ===== Backend selection =====
    # local  -> Ollama for every role (no cloud creds needed; sensible model defaults)
    # cloud  -> per-role cloud config; legacy LLM_* keys act as defaults
    # custom -> purely per-role config (LLM_ROLE_*_BACKEND etc.)
    BACKEND_MODE = os.environ.get('BACKEND_MODE', 'cloud').lower()

    # ===== Legacy single-endpoint LLM config =====
    # Still consulted by openai_compat backends as a fallback when the
    # per-role keys are not set. Keep these populated for back-compat.
    LLM_API_KEY = os.environ.get('LLM_API_KEY')
    LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://api.openai.com/v1')
    LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME', 'gpt-4o-mini')

    # ===== Router behavior =====
    # Maximum retry attempts per backend before falling through to the next
    # entry in LLM_ROLE_<role>_FALLBACKS. Default 3 with exponential backoff + jitter.
    LLM_MAX_RETRIES = int(os.environ.get('LLM_MAX_RETRIES', '3'))

    # SQLite database for per-call token / latency / cost accounting.
    # Default: backend/data/llm_calls.db
    LLM_CALLS_DB = os.environ.get('LLM_CALLS_DB')
    
    # Zep配置
    ZEP_API_KEY = os.environ.get('ZEP_API_KEY')

    # ===== Phase 2: memory backend =====
    # auto        -> pick based on what's configured (NEO4J_URI > ZEP_API_KEY > in_memory)
    # in_memory   -> per-process dict; for tests + minimal local runs
    # zep_cloud   -> pre-existing Zep path (requires ZEP_API_KEY)
    # neo4j_local -> self-hosted Neo4j 5.x via bolt://
    # neo4j_aura  -> managed Neo4j AuraDB via neo4j+s://
    MEMORY_BACKEND = os.environ.get('MEMORY_BACKEND', 'auto').lower()
    NEO4J_URI = os.environ.get('NEO4J_URI')
    NEO4J_USER = os.environ.get('NEO4J_USER', 'neo4j')
    NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD')
    NEO4J_DATABASE = os.environ.get('NEO4J_DATABASE', 'neo4j')

    # ===== Phase 2: hierarchical memory =====
    # Reflection cadence (rounds). Stanford Generative Agents used 10; we default
    # to 5 because a typical MiroFish run is shorter than the GA paper's.
    REFLECTION_EVERY_N_ROUNDS = int(os.environ.get('REFLECTION_EVERY_N_ROUNDS', '5'))
    REFLECTION_TOP_K_SOURCES = int(os.environ.get('REFLECTION_TOP_K_SOURCES', '10'))
    # Retrieval weights (α·recency + β·importance + γ·relevance). Any non-negative
    # values are fine — the backend normalizes before combining.
    MEMORY_ALPHA = float(os.environ.get('MEMORY_ALPHA', '1.0'))
    MEMORY_BETA = float(os.environ.get('MEMORY_BETA', '1.0'))
    MEMORY_GAMMA = float(os.environ.get('MEMORY_GAMMA', '1.0'))
    # Feature flags — toggle off to A/B whether each contributed.
    MEMORY_ENABLE_IMPORTANCE = os.environ.get('MEMORY_ENABLE_IMPORTANCE', 'true').lower() == 'true'
    MEMORY_ENABLE_REFLECTION = os.environ.get('MEMORY_ENABLE_REFLECTION', 'true').lower() == 'true'
    MEMORY_ENABLE_CONTRADICTION = os.environ.get('MEMORY_ENABLE_CONTRADICTION', 'true').lower() == 'true'

    # ===== Phase 6: auth + observability =====
    # Admin token for /api/auth/keys management endpoints. Unset -> those
    # endpoints return 503 so a misconfigured deployment fails loudly.
    ADMIN_TOKEN = os.environ.get('ADMIN_TOKEN')
    # `true` lets non-auth endpoints accept anonymous traffic; useful for
    # demos, discouraged in prod. The auth middleware still records
    # rejections metrics so dashboards see when anonymous is being relied on.
    ALLOW_ANONYMOUS_API = os.environ.get('ALLOW_ANONYMOUS_API', 'false').lower() == 'true'
    # API key SQLite location. Defaults to backend/data/auth.db.
    AUTH_DB_PATH = os.environ.get('AUTH_DB_PATH')
    QUOTA_DB_PATH = os.environ.get('QUOTA_DB_PATH')
    # OpenTelemetry exporter endpoint (OTLP/HTTP). Empty -> tracing disabled.
    OTEL_EXPORTER_OTLP_ENDPOINT = os.environ.get('OTEL_EXPORTER_OTLP_ENDPOINT')
    OTEL_SERVICE_NAME = os.environ.get('OTEL_SERVICE_NAME', 'mirofish-backend')

    # ===== Phase 4: persona dynamics =====
    # Percentage of the agent population converted into adversarial archetypes.
    # DEFAULT IS ZERO. Enabling these changes simulation outcomes in measurable
    # ways — the spec calls this out explicitly.
    BOT_POPULATION_PCT = float(os.environ.get('BOT_POPULATION_PCT', '0'))
    TROLL_POPULATION_PCT = float(os.environ.get('TROLL_POPULATION_PCT', '0'))
    # Institutional archetypes that get a default credibility boost. Safe to
    # enable without affecting outcome integrity.
    MEDIA_POPULATION_PCT = float(os.environ.get('MEDIA_POPULATION_PCT', '0'))
    EXPERT_POPULATION_PCT = float(os.environ.get('EXPERT_POPULATION_PCT', '0'))
    # Deterministic population-mix seed; set for reproducible experiments.
    POPULATION_SEED = os.environ.get('POPULATION_SEED')
    # Author-credibility weighting strength. 0.0 disables; 1.0 means high
    # credibility ~1.5x score, low credibility ~0.5x score. See personas/credibility.py.
    CREDIBILITY_WEIGHT = float(os.environ.get('CREDIBILITY_WEIGHT', '1.0'))

    # ===== Phase 3: transport =====
    # zmq  -> ZeroMQ REQ/REP (commands) + PUB/SUB (events). Default.
    # file -> legacy file-poll IPC. Preserved for back-compat; can't do events.
    IPC_TRANSPORT = os.environ.get('IPC_TRANSPORT', 'zmq').lower()
    # Optional explicit endpoints. When unset, the transport uses ipc:// sockets
    # under <simulation_dir>/.sockets/.
    IPC_CMD_ENDPOINT = os.environ.get('IPC_CMD_ENDPOINT')
    IPC_EVENT_ENDPOINT = os.environ.get('IPC_EVENT_ENDPOINT')
    
    # 文件上传配置
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '../uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'md', 'txt', 'markdown'}
    
    # 文本处理配置
    DEFAULT_CHUNK_SIZE = 500  # 默认切块大小
    DEFAULT_CHUNK_OVERLAP = 50  # 默认重叠大小
    
    # OASIS模拟配置
    OASIS_DEFAULT_MAX_ROUNDS = int(os.environ.get('OASIS_DEFAULT_MAX_ROUNDS', '10'))
    OASIS_SIMULATION_DATA_DIR = os.path.join(os.path.dirname(__file__), '../uploads/simulations')
    
    # OASIS平台可用动作配置
    OASIS_TWITTER_ACTIONS = [
        'CREATE_POST', 'LIKE_POST', 'REPOST', 'FOLLOW', 'DO_NOTHING', 'QUOTE_POST'
    ]
    OASIS_REDDIT_ACTIONS = [
        'LIKE_POST', 'DISLIKE_POST', 'CREATE_POST', 'CREATE_COMMENT',
        'LIKE_COMMENT', 'DISLIKE_COMMENT', 'SEARCH_POSTS', 'SEARCH_USER',
        'TREND', 'REFRESH', 'DO_NOTHING', 'FOLLOW', 'MUTE'
    ]
    
    # Report Agent配置
    REPORT_AGENT_MAX_TOOL_CALLS = int(os.environ.get('REPORT_AGENT_MAX_TOOL_CALLS', '5'))
    REPORT_AGENT_MAX_REFLECTION_ROUNDS = int(os.environ.get('REPORT_AGENT_MAX_REFLECTION_ROUNDS', '2'))
    REPORT_AGENT_TEMPERATURE = float(os.environ.get('REPORT_AGENT_TEMPERATURE', '0.5'))
    
    @classmethod
    def validate(cls):
        """验证必要配置。

        BACKEND_MODE=local uses Ollama + the in-memory/Neo4j backends; neither
        cloud LLM nor Zep keys are required in that mode. When a per-role
        backend is configured for every role, the legacy LLM_API_KEY is also
        optional.
        """
        errors = []

        if cls.BACKEND_MODE != 'local':
            # Cloud / custom mode needs either the legacy fallback key or a
            # per-role API key for at least the balanced role (the main
            # default used by every caller).
            per_role_api = os.environ.get('LLM_ROLE_BALANCED_API_KEY')
            if not cls.LLM_API_KEY and not per_role_api:
                errors.append(
                    "LLM_API_KEY (or LLM_ROLE_BALANCED_API_KEY) 未配置"
                )
            # Zep is still used by the pre-existing graph-builder path. Not
            # required when MEMORY_BACKEND skips it entirely.
            if not cls.ZEP_API_KEY and cls.MEMORY_BACKEND in ('auto', 'zep_cloud'):
                errors.append("ZEP_API_KEY 未配置")

        return errors


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
        """验证必要配置"""
        errors = []
        if not cls.LLM_API_KEY:
            errors.append("LLM_API_KEY 未配置")
        if not cls.ZEP_API_KEY:
            errors.append("ZEP_API_KEY 未配置")
        return errors


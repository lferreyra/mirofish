"""
配置管理
统一从项目根目录的 .env 文件加载配置
"""

import os
from dotenv import load_dotenv

from .utils.openrouter_runtime import (
    configure_openrouter_runtime,
    get_configured_openrouter_api_keys,
    get_default_openrouter_base_url,
)

# 加载项目根目录的 .env 文件
# 路径: MiroFish/.env (相对于 backend/app/config.py)
project_root_env = os.path.join(os.path.dirname(__file__), '../../.env')

if os.path.exists(project_root_env):
    load_dotenv(project_root_env, override=True)
else:
    # 如果根目录没有 .env，尝试加载环境变量（用于生产环境）
    load_dotenv(override=True)

# 如果当前使用 OpenRouter，则为兼容代码路径补齐单键变量并安装运行时补丁
configure_openrouter_runtime()


class Config:
    """Flask配置类"""
    
    # Flask配置
    SECRET_KEY = os.environ.get('SECRET_KEY', 'mirofish-secret-key')
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    # JSON配置 - 禁用ASCII转义，让中文直接显示（而不是 \uXXXX 格式）
    JSON_AS_ASCII = False

    # OpenRouter 多 Key 配置
    OPENROUTER_API_KEYS = get_configured_openrouter_api_keys()
    
    # LLM配置（统一使用OpenAI格式）
    LLM_API_KEY = os.environ.get('LLM_API_KEY') or (OPENROUTER_API_KEYS[0] if OPENROUTER_API_KEYS else None)
    LLM_BASE_URL = os.environ.get('LLM_BASE_URL', get_default_openrouter_base_url())
    LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME', 'arcee-ai/trinity-large-preview:free')
    LLM_REQUEST_TIMEOUT_SECONDS = float(os.environ.get('LLM_REQUEST_TIMEOUT_SECONDS', '300'))
    LLM_JSON_RETRY_ATTEMPTS = int(os.environ.get('LLM_JSON_RETRY_ATTEMPTS', '3'))
    LLM_MAX_OUTPUT_TOKENS = int(os.environ.get('LLM_MAX_OUTPUT_TOKENS', '1000000'))
    ONTOLOGY_LLM_TIMEOUT_SECONDS = float(os.environ.get('ONTOLOGY_LLM_TIMEOUT_SECONDS', str(LLM_REQUEST_TIMEOUT_SECONDS)))
    ONTOLOGY_LLM_RETRY_ATTEMPTS = int(os.environ.get('ONTOLOGY_LLM_RETRY_ATTEMPTS', str(LLM_JSON_RETRY_ATTEMPTS)))
    ONTOLOGY_LLM_MAX_TOKENS = int(os.environ.get('ONTOLOGY_LLM_MAX_TOKENS', str(LLM_MAX_OUTPUT_TOKENS)))
    ONTOLOGY_MAX_INPUT_CHARS = int(os.environ.get('ONTOLOGY_MAX_INPUT_CHARS', '1000000'))
    
    # 首次附件解析专用 LLM 配置（可选，不配置则回退到通用 LLM）
    INPUT_LLM_API_KEY = os.environ.get('INPUT_LLM_API_KEY') or LLM_API_KEY
    INPUT_LLM_BASE_URL = os.environ.get('INPUT_LLM_BASE_URL') or LLM_BASE_URL
    INPUT_LLM_MODEL_NAME = os.environ.get('INPUT_LLM_MODEL_NAME') or LLM_MODEL_NAME
    INPUT_LLM_IMAGE_MAX_TOKENS = int(os.environ.get('INPUT_LLM_IMAGE_MAX_TOKENS', str(LLM_MAX_OUTPUT_TOKENS)))
    INPUT_LLM_PDF_VISION_MAX_TOKENS = int(os.environ.get('INPUT_LLM_PDF_VISION_MAX_TOKENS', str(LLM_MAX_OUTPUT_TOKENS)))

    # 1M context-oriented truncation settings (character-based guards inside the app)
    SIMULATION_CONFIG_MAX_CONTEXT_CHARS = int(os.environ.get('SIMULATION_CONFIG_MAX_CONTEXT_CHARS', '1000000'))
    SIMULATION_CONFIG_TIME_CONTEXT_CHARS = int(
        os.environ.get('SIMULATION_CONFIG_TIME_CONTEXT_CHARS', str(SIMULATION_CONFIG_MAX_CONTEXT_CHARS))
    )
    SIMULATION_CONFIG_EVENT_CONTEXT_CHARS = int(
        os.environ.get('SIMULATION_CONFIG_EVENT_CONTEXT_CHARS', str(SIMULATION_CONFIG_MAX_CONTEXT_CHARS))
    )
    
    # Zep配置
    ZEP_API_KEY = os.environ.get('ZEP_API_KEY')
    ZEP_MAX_RETRIES = int(os.environ.get('ZEP_MAX_RETRIES', '3'))
    ZEP_RETRY_DELAY_SECONDS = float(os.environ.get('ZEP_RETRY_DELAY_SECONDS', '2.0'))
    ZEP_SEARCH_QUERY_MAX_CHARS = int(os.environ.get('ZEP_SEARCH_QUERY_MAX_CHARS', '400'))
    ZEP_QUERY_REWRITE_TARGET_CHARS = int(os.environ.get('ZEP_QUERY_REWRITE_TARGET_CHARS', '340'))
    ZEP_QUERY_REWRITE_RETRY_ATTEMPTS = int(
        os.environ.get('ZEP_QUERY_REWRITE_RETRY_ATTEMPTS', str(LLM_JSON_RETRY_ATTEMPTS))
    )
    
    # 文件上传配置
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '../uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'md', 'txt', 'markdown', 'png', 'jpg', 'jpeg', 'webp'}
    
    # 文本处理配置
    DEFAULT_CHUNK_SIZE = 500  # 默认切块大小
    DEFAULT_CHUNK_OVERLAP = 50  # 默认重叠大小
    
    # OASIS模拟配置
    OASIS_DEFAULT_MAX_ROUNDS = int(os.environ.get('OASIS_DEFAULT_MAX_ROUNDS', '10'))
    OASIS_SIMULATION_DATA_DIR = os.path.join(os.path.dirname(__file__), '../uploads/simulations')
    OASIS_BATCH_INTERVIEW_TIMEOUT_SECONDS = float(
        os.environ.get('OASIS_BATCH_INTERVIEW_TIMEOUT_SECONDS', '300')
    )
    
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
    REPORT_AGENT_MAX_TOKENS = int(os.environ.get('REPORT_AGENT_MAX_TOKENS', str(LLM_MAX_OUTPUT_TOKENS)))
    REPORT_AGENT_LLM_RETRY_ATTEMPTS = int(
        os.environ.get('REPORT_AGENT_LLM_RETRY_ATTEMPTS', str(LLM_JSON_RETRY_ATTEMPTS))
    )
    ZEP_INTERVIEW_SUMMARY_MAX_TOKENS = int(
        os.environ.get('ZEP_INTERVIEW_SUMMARY_MAX_TOKENS', str(LLM_MAX_OUTPUT_TOKENS))
    )
    
    @classmethod
    def validate(cls):
        """验证必要配置"""
        errors = []
        if not cls.LLM_API_KEY and not cls.OPENROUTER_API_KEYS:
            errors.append("未配置 LLM_API_KEY 或 OPENROUTER_API_KEY1..N")
        if not cls.ZEP_API_KEY:
            errors.append("ZEP_API_KEY 未配置")
        return errors

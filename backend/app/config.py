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
    load_dotenv(override=True)


class Config:
    """Flask配置类"""
    
    # Flask配置
    SECRET_KEY = os.environ.get('SECRET_KEY', 'mirofish-secret-key')
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    # JSON配置
    JSON_AS_ASCII = False
    
    # ===== Primary LLM (Groq) - 3 keys, auto-rotates on rate limit =====
    LLM_API_KEY_1 = os.environ.get('LLM_API_KEY_1')
    LLM_API_KEY_2 = os.environ.get('LLM_API_KEY_2')
    LLM_API_KEY_3 = os.environ.get('LLM_API_KEY_3')
    LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://api.groq.com/openai/v1')
    LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME', 'llama-3.3-70b-versatile')

    # Backward compatibility alias
    LLM_API_KEY = os.environ.get('LLM_API_KEY_1') or os.environ.get('LLM_API_KEY')

    # ===== Boost LLM (Gemini) - 3 keys, auto-rotates on rate limit =====
    LLM_BOOST_API_KEY_1 = os.environ.get('LLM_BOOST_API_KEY_1')
    LLM_BOOST_API_KEY_2 = os.environ.get('LLM_BOOST_API_KEY_2')
    LLM_BOOST_API_KEY_3 = os.environ.get('LLM_BOOST_API_KEY_3')
    LLM_BOOST_BASE_URL = os.environ.get('LLM_BOOST_BASE_URL')
    LLM_BOOST_MODEL_NAME = os.environ.get('LLM_BOOST_MODEL_NAME')

    # Zep配置
    ZEP_API_KEY = os.environ.get('ZEP_API_KEY')
    
    # 文件上传配置
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '../uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'md', 'txt', 'markdown'}
    
    # 文本处理配置
    DEFAULT_CHUNK_SIZE = 500
    DEFAULT_CHUNK_OVERLAP = 50
    
    # OASIS模拟配置
    OASIS_DEFAULT_MAX_ROUNDS = int(os.environ.get('OASIS_DEFAULT_MAX_ROUNDS', '3'))
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
    REPORT_AGENT_MAX_TOOL_CALLS = int(os.environ.get('REPORT_AGENT_MAX_TOOL_CALLS', '1'))
    REPORT_AGENT_MAX_REFLECTION_ROUNDS = int(os.environ.get('REPORT_AGENT_MAX_REFLECTION_ROUNDS', '1'))
    REPORT_AGENT_TEMPERATURE = float(os.environ.get('REPORT_AGENT_TEMPERATURE', '0.3'))

    @classmethod
    def get_primary_keys(cls) -> list:
        """Return all configured primary (Groq) API keys"""
        return [k for k in [cls.LLM_API_KEY_1, cls.LLM_API_KEY_2, cls.LLM_API_KEY_3] if k]

    @classmethod
    def get_boost_keys(cls) -> list:
        """Return all configured boost (Gemini) API keys"""
        return [k for k in [cls.LLM_BOOST_API_KEY_1, cls.LLM_BOOST_API_KEY_2, cls.LLM_BOOST_API_KEY_3] if k]

    @classmethod
    def has_boost(cls) -> bool:
        """Check if boost LLM is configured"""
        return bool(cls.LLM_BOOST_API_KEY_1 and cls.LLM_BOOST_BASE_URL and cls.LLM_BOOST_MODEL_NAME)

    @classmethod
    def validate(cls):
        """验证必要配置"""
        errors = []
        primary_keys = cls.get_primary_keys()
        if not primary_keys:
            errors.append("LLM_API_KEY_1 未配置")
        else:
            print(f"✅ Primary LLM: {len(primary_keys)} key(s) configured")
        if not cls.ZEP_API_KEY:
            errors.append("ZEP_API_KEY 未配置")
        if cls.has_boost():
            print(f"✅ Boost LLM: {len(cls.get_boost_keys())} key(s) configured")
        else:
            print("⚠️ LLM_BOOST not configured - all tasks will use primary LLM")
        return errors
"""
配置管理
统一从项目根目录的 .env 文件加载配置
"""

import os
import json
from typing import Optional, List
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
    
    # LLM配置（统一使用OpenAI格式）
    LLM_API_KEY = os.environ.get('LLM_API_KEY')
    LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://api.openai.com/v1')
    LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME', 'gpt-4o-mini')
    
    # Zep配置
    ZEP_API_KEY = os.environ.get('ZEP_API_KEY')
    
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
    
    # Polymarket Prediction 설정
    PREDICTION_DEFAULT_MODE = os.environ.get('PREDICTION_DEFAULT_MODE', 'mid')
    PREDICTION_KELLY_FRACTION = float(os.environ.get('PREDICTION_KELLY_FRACTION', '0.5'))
    PREDICTION_MAX_BET_FRACTION = float(os.environ.get('PREDICTION_MAX_BET_FRACTION', '0.15'))
    PREDICTION_MIN_EDGE = float(os.environ.get('PREDICTION_MIN_EDGE', '0.02'))
    PREDICTION_CALIBRATION_SHRINKAGE = float(os.environ.get('PREDICTION_CALIBRATION_SHRINKAGE', '0.15'))

    # 외부 데이터 설정
    EXTERNAL_DATA_ENABLED = os.environ.get('EXTERNAL_DATA_ENABLED', 'true').lower() == 'true'
    BRAVE_SEARCH_API_KEY = os.environ.get('BRAVE_SEARCH_API_KEY')
    TAVILY_API_KEY = os.environ.get('TAVILY_API_KEY')
    SERP_API_KEY = os.environ.get('SERP_API_KEY')
    NEWS_API_KEY = os.environ.get('NEWS_API_KEY')
    ALPHA_VANTAGE_API_KEY = os.environ.get('ALPHA_VANTAGE_API_KEY')
    EXTERNAL_DATA_INJECT_INTERVAL = int(os.environ.get('EXTERNAL_DATA_INJECT_INTERVAL', '10'))

    # Report Agent配置
    REPORT_AGENT_MAX_TOOL_CALLS = int(os.environ.get('REPORT_AGENT_MAX_TOOL_CALLS', '5'))
    REPORT_AGENT_MAX_REFLECTION_ROUNDS = int(os.environ.get('REPORT_AGENT_MAX_REFLECTION_ROUNDS', '2'))
    REPORT_AGENT_TEMPERATURE = float(os.environ.get('REPORT_AGENT_TEMPERATURE', '0.5'))
    
    @classmethod
    def get_llm_accounts(cls) -> Optional[List]:
        """
        환경 변수에서 멀티 LLM 계정 설정을 파싱합니다.

        지원 형식:
        1) JSON 배열 (LLM_ACCOUNTS 환경변수):
           LLM_ACCOUNTS='[{"name":"acc1","auth_type":"api_key","api_key":"sk-...","base_url":"...","model":"..."}]'

        2) 번호 기반 환경변수:
           LLM_ACCOUNT_1_NAME=primary
           LLM_ACCOUNT_1_AUTH_TYPE=api_key
           LLM_ACCOUNT_1_API_KEY=sk-...
           LLM_ACCOUNT_1_BASE_URL=https://api.openai.com/v1
           LLM_ACCOUNT_1_MODEL=gpt-4o
           LLM_ACCOUNT_1_PRIORITY=0

           LLM_ACCOUNT_2_NAME=codex-oauth
           LLM_ACCOUNT_2_AUTH_TYPE=oauth
           LLM_ACCOUNT_2_CLIENT_ID=...
           LLM_ACCOUNT_2_CLIENT_SECRET=...
           LLM_ACCOUNT_2_TOKEN_URL=https://auth.openai.com/oauth/token
           LLM_ACCOUNT_2_BASE_URL=https://api.openai.com/v1
           LLM_ACCOUNT_2_MODEL=gpt-4o
           LLM_ACCOUNT_2_PRIORITY=1

        Returns:
            AccountConfig 리스트 또는 None (설정이 없는 경우)
        """
        from .utils.account_manager import AccountConfig, AuthType

        accounts = []

        # 방법 1: JSON 환경변수
        json_accounts = os.environ.get('LLM_ACCOUNTS')
        if json_accounts:
            try:
                items = json.loads(json_accounts)
                for item in items:
                    accounts.append(AccountConfig(
                        name=item['name'],
                        auth_type=AuthType(item.get('auth_type', 'api_key')),
                        base_url=item.get('base_url', cls.LLM_BASE_URL),
                        model=item.get('model', cls.LLM_MODEL_NAME),
                        api_key=item.get('api_key'),
                        client_id=item.get('client_id'),
                        client_secret=item.get('client_secret'),
                        token_url=item.get('token_url'),
                        oauth_scope=item.get('oauth_scope'),
                        oauth_audience=item.get('oauth_audience'),
                        priority=item.get('priority', 0),
                        default_thinking=item.get('default_thinking'),
                        max_thinking_budget=item.get('max_thinking_budget'),
                    ))
                return accounts if accounts else None
            except (json.JSONDecodeError, KeyError) as e:
                import logging
                logging.getLogger('mirofish.config').warning(f"LLM_ACCOUNTS JSON 파싱 실패: {e}")

        # 방법 2: 번호 기반 환경변수 (LLM_ACCOUNT_1_*, LLM_ACCOUNT_2_*, ...)
        for i in range(1, 21):  # 최대 20개 계정
            prefix = f'LLM_ACCOUNT_{i}_'
            name = os.environ.get(f'{prefix}NAME')
            if not name:
                continue

            auth_type_str = os.environ.get(f'{prefix}AUTH_TYPE', 'api_key')
            auth_type = AuthType(auth_type_str)

            thinking_budget_raw = os.environ.get(f'{prefix}MAX_THINKING_BUDGET')
            thinking_budget = int(thinking_budget_raw) if thinking_budget_raw else None

            accounts.append(AccountConfig(
                name=name,
                auth_type=auth_type,
                base_url=os.environ.get(f'{prefix}BASE_URL', cls.LLM_BASE_URL),
                model=os.environ.get(f'{prefix}MODEL', cls.LLM_MODEL_NAME),
                api_key=os.environ.get(f'{prefix}API_KEY'),
                client_id=os.environ.get(f'{prefix}CLIENT_ID'),
                client_secret=os.environ.get(f'{prefix}CLIENT_SECRET'),
                token_url=os.environ.get(f'{prefix}TOKEN_URL'),
                oauth_scope=os.environ.get(f'{prefix}OAUTH_SCOPE'),
                oauth_audience=os.environ.get(f'{prefix}OAUTH_AUDIENCE'),
                priority=int(os.environ.get(f'{prefix}PRIORITY', str(i - 1))),
                default_thinking=os.environ.get(f'{prefix}DEFAULT_THINKING'),
                max_thinking_budget=thinking_budget,
            ))

        return accounts if accounts else None

    @classmethod
    def validate(cls):
        """验证必要配置"""
        errors = []
        # 멀티 계정이 설정되어 있으면 단일 API key는 필수가 아님
        has_multi_accounts = cls.get_llm_accounts() is not None
        if not cls.LLM_API_KEY and not has_multi_accounts:
            errors.append("LLM_API_KEY 未配置 (단일 API key 또는 LLM_ACCOUNTS 필요)")
        if not cls.ZEP_API_KEY:
            errors.append("ZEP_API_KEY 未配置")
        return errors


"""
계정 관리 API
- OAuth 로그인 (PKCE 브라우저 flow)
- 계정 hot-reload (돌아가는 도중 계정 추가/제거)
- 계정 상태 조회
"""

from flask import Blueprint, request, jsonify
from ..utils.logger import get_logger

logger = get_logger('mirofish.api.accounts')

accounts_bp = Blueprint('accounts', __name__)


def _get_account_manager():
    """현재 글로벌 AccountManager를 가져옵니다."""
    from ..utils.llm_client import _get_global_account_manager, _global_account_manager
    manager = _get_global_account_manager()
    if not manager:
        # 아직 초기화 안 됐으면 빈 매니저 생성
        from ..utils.account_manager import AccountManager
        from ..utils import llm_client as llm_mod
        llm_mod._global_account_manager = AccountManager()
        llm_mod._manager_initialized = True
        manager = llm_mod._global_account_manager
    return manager


# ── 계정 상태 조회 ──

@accounts_bp.route('/status', methods=['GET'])
def get_accounts_status():
    """모든 계정의 상태를 반환합니다."""
    manager = _get_account_manager()
    return jsonify({
        "accounts": manager.get_status(),
        "total": manager.account_count,
    })


# ── Hot-reload: 계정 추가 ──

@accounts_bp.route('/add', methods=['POST'])
def add_account():
    """
    돌아가는 도중 계정을 추가합니다 (서버 재시작 불필요).

    Request body:
    {
        "name": "codex-new",
        "auth_type": "oauth",           // "api_key" 또는 "oauth"
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-5.4",
        "priority": 5,
        "default_thinking": "high",

        // api_key 방식:
        "api_key": "sk-...",

        // oauth 방식:
        "client_id": "...",
        "client_secret": "...",          // 선택사항
        "token_url": "https://auth.openai.com/oauth/token",

        // 또는 이미 토큰이 있으면:
        "access_token": "...",
        "refresh_token": "..."
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "요청 데이터 없음"}), 400

    try:
        from ..utils.account_manager import AccountConfig, AuthType
        config = AccountConfig(
            name=data['name'],
            auth_type=AuthType(data.get('auth_type', 'api_key')),
            base_url=data.get('base_url', 'https://api.openai.com/v1'),
            model=data.get('model', 'gpt-5.4'),
            api_key=data.get('api_key'),
            client_id=data.get('client_id'),
            client_secret=data.get('client_secret'),
            token_url=data.get('token_url'),
            oauth_scope=data.get('oauth_scope'),
            oauth_audience=data.get('oauth_audience'),
            priority=data.get('priority', 99),
            default_thinking=data.get('default_thinking', 'high'),
            max_thinking_budget=data.get('max_thinking_budget'),
        )

        manager = _get_account_manager()
        manager.add_account(config)

        # OAuth 계정에 이미 토큰이 있으면 설정
        if config.auth_type == AuthType.OAUTH and data.get('access_token'):
            for acc in manager._accounts:
                if acc.config.name == config.name and acc.oauth_client:
                    acc.oauth_client.set_tokens(
                        access_token=data['access_token'],
                        refresh_token=data.get('refresh_token'),
                        expires_in=data.get('expires_in', 3600),
                    )

        return jsonify({
            "message": f"계정 '{config.name}' 추가 완료",
            "accounts": manager.get_status(),
        })

    except Exception as e:
        logger.error(f"계정 추가 실패: {e}")
        return jsonify({"error": str(e)}), 400


# ── Hot-reload: 계정 제거 ──

@accounts_bp.route('/remove/<name>', methods=['DELETE'])
def remove_account(name: str):
    """돌아가는 도중 계정을 제거합니다."""
    manager = _get_account_manager()
    with manager._lock:
        before = len(manager._accounts)
        manager._accounts = [a for a in manager._accounts if a.config.name != name]
        after = len(manager._accounts)

    if before == after:
        return jsonify({"error": f"계정 '{name}' 을 찾을 수 없음"}), 404

    logger.info(f"계정 제거: '{name}'")
    return jsonify({
        "message": f"계정 '{name}' 제거 완료",
        "accounts": manager.get_status(),
    })


# ── 계정 리셋 ──

@accounts_bp.route('/reset/<name>', methods=['POST'])
def reset_account(name: str):
    """특정 계정의 cooldown/error 상태를 초기화합니다."""
    manager = _get_account_manager()
    manager.reset_account(name)
    return jsonify({
        "message": f"계정 '{name}' 상태 초기화 완료",
        "accounts": manager.get_status(),
    })


@accounts_bp.route('/reset', methods=['POST'])
def reset_all_accounts():
    """모든 계정의 상태를 초기화합니다."""
    manager = _get_account_manager()
    manager.reset_all()
    return jsonify({
        "message": "모든 계정 상태 초기화 완료",
        "accounts": manager.get_status(),
    })


# ── OAuth 브라우저 로그인 ──

@accounts_bp.route('/oauth/login', methods=['POST'])
def oauth_login():
    """
    Codex OAuth PKCE 로그인을 시작합니다.
    브라우저에서 열 URL을 반환합니다.

    Request body:
    {
        "name": "codex-1",
        "client_id": "your_client_id",
        "client_secret": "...",          // 선택사항
        "authorize_url": "...",          // 선택사항, 기본: OpenAI
        "token_url": "...",              // 선택사항, 기본: OpenAI
        "scope": "...",                  // 선택사항
        "model": "gpt-5.4",             // 선택사항
        "callback_port": 14551           // 선택사항
    }
    """
    data = request.get_json()
    if not data or 'client_id' not in data:
        return jsonify({"error": "client_id 필요"}), 400

    from ..utils.codex_oauth import CodexOAuthClient

    name = data.get('name', f"codex-{data['client_id'][:8]}")
    client = CodexOAuthClient(
        client_id=data['client_id'],
        client_secret=data.get('client_secret'),
        token_url=data.get('token_url'),
        authorize_url=data.get('authorize_url'),
        scope=data.get('scope'),
        audience=data.get('audience'),
        account_name=name,
        callback_port=data.get('callback_port', 14551),
    )

    login_url = client.start_login()

    # callback 서버를 백그라운드에서 시작
    import threading

    def _wait_for_callback():
        success = client.start_callback_server(timeout=600)  # 10분 대기
        if success:
            # 계정 자동 추가
            from ..utils.account_manager import AccountConfig, AuthType
            config = AccountConfig(
                name=name,
                auth_type=AuthType.OAUTH,
                base_url=data.get('base_url', 'https://api.openai.com/v1'),
                model=data.get('model', 'gpt-5.4'),
                client_id=data['client_id'],
                client_secret=data.get('client_secret'),
                token_url=data.get('token_url'),
                priority=data.get('priority', 99),
                default_thinking=data.get('default_thinking', 'high'),
            )
            manager = _get_account_manager()

            # 이미 같은 이름 있으면 제거 후 추가
            with manager._lock:
                manager._accounts = [a for a in manager._accounts if a.config.name != name]

            manager.add_account(config)

            # OAuth 클라이언트 연결
            for acc in manager._accounts:
                if acc.config.name == name:
                    acc.oauth_client = client
                    break

            logger.info(f"OAuth 로그인 성공, 계정 '{name}' 자동 추가")

    thread = threading.Thread(target=_wait_for_callback, daemon=True)
    thread.start()

    return jsonify({
        "login_url": login_url,
        "message": f"브라우저에서 이 URL을 열어 로그인하세요. 로그인 후 계정 '{name}'이 자동 추가됩니다.",
        "callback_port": data.get('callback_port', 14551),
        "timeout_seconds": 600,
    })


# ── OAuth 수동 토큰 입력 ──

@accounts_bp.route('/oauth/token', methods=['POST'])
def oauth_set_token():
    """
    이미 가지고 있는 토큰을 직접 설정합니다.
    (브라우저 로그인 없이)

    Request body:
    {
        "name": "codex-1",
        "access_token": "...",
        "refresh_token": "...",
        "expires_in": 3600,
        "client_id": "...",
        "model": "gpt-5.4"
    }
    """
    data = request.get_json()
    if not data or 'access_token' not in data:
        return jsonify({"error": "access_token 필요"}), 400

    name = data.get('name', 'codex-manual')

    from ..utils.codex_oauth import CodexOAuthClient, save_token, OAuthToken
    from ..utils.account_manager import AccountConfig, AuthType

    # 토큰 저장
    token = OAuthToken(
        access_token=data['access_token'],
        refresh_token=data.get('refresh_token'),
        expires_in=data.get('expires_in', 3600),
    )
    save_token(name, token)

    # 계정 추가
    config = AccountConfig(
        name=name,
        auth_type=AuthType.OAUTH,
        base_url=data.get('base_url', 'https://api.openai.com/v1'),
        model=data.get('model', 'gpt-5.4'),
        client_id=data.get('client_id', ''),
        token_url=data.get('token_url'),
        priority=data.get('priority', 99),
        default_thinking=data.get('default_thinking', 'high'),
    )

    manager = _get_account_manager()
    with manager._lock:
        manager._accounts = [a for a in manager._accounts if a.config.name != name]

    manager.add_account(config)

    # 토큰 직접 설정
    for acc in manager._accounts:
        if acc.config.name == name:
            client = CodexOAuthClient(
                client_id=data.get('client_id', ''),
                account_name=name,
            )
            client._token = token
            acc.oauth_client = client
            break

    return jsonify({
        "message": f"계정 '{name}' 토큰 설정 완료",
        "accounts": manager.get_status(),
    })


# ── .env 리로드 ──

@accounts_bp.route('/reload', methods=['POST'])
def reload_accounts():
    """
    .env 파일에서 계정 설정을 다시 로드합니다 (서버 재시작 없이).
    기존 계정은 유지하고, 새 계정만 추가됩니다.
    """
    from ..config import Config
    from ..utils.account_manager import AccountConfig
    from dotenv import load_dotenv
    import os

    # .env 다시 로드
    project_root_env = os.path.join(os.path.dirname(__file__), '../../../.env')
    if os.path.exists(project_root_env):
        load_dotenv(project_root_env, override=True)

    # 계정 다시 파싱
    new_accounts = Config.get_llm_accounts()
    if not new_accounts:
        return jsonify({"message": "새 계정 설정 없음", "accounts": []})

    manager = _get_account_manager()
    existing_names = {a.config.name for a in manager._accounts}

    added = []
    for acc in new_accounts:
        if acc.name not in existing_names:
            manager.add_account(acc)
            added.append(acc.name)

    return jsonify({
        "message": f"{len(added)}개 계정 추가됨: {added}" if added else "새 계정 없음 (모두 이미 존재)",
        "accounts": manager.get_status(),
    })

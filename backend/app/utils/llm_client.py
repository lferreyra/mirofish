"""
LLM客户端封装
统一使用OpenAI格式调用，支持多账户和OAuth认证
"""

import json
import re
import time
from typing import Optional, Dict, Any, List
from openai import OpenAI, RateLimitError, APIStatusError

from ..config import Config
from ..utils.logger import get_logger

logger = get_logger('mirofish.llm_client')

# 글로벌 AccountManager 인스턴스 (lazy init)
_global_account_manager = None
_manager_initialized = False


def _get_global_account_manager():
    """글로벌 AccountManager를 lazy 초기화하여 반환합니다."""
    global _global_account_manager, _manager_initialized
    if not _manager_initialized:
        _manager_initialized = True
        accounts = Config.get_llm_accounts()
        if accounts:
            from .account_manager import AccountManager
            _global_account_manager = AccountManager(accounts)
            logger.info(f"멀티 계정 매니저 초기화 완료: {_global_account_manager.account_count}개 계정")
    return _global_account_manager


class LLMClient:
    """LLM客户端 - 支持API Key和OAuth认证，多账户自动切换"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        use_multi_account: Optional[bool] = None
    ):
        self.model = model or Config.LLM_MODEL_NAME
        self._use_multi_account = use_multi_account

        # 멀티 계정 사용 여부 결정
        # 직접 api_key를 넘긴 경우는 단일 계정 모드 사용
        self._account_manager = None
        if api_key is None and use_multi_account is not False:
            self._account_manager = _get_global_account_manager()

        # 멀티 계정이 없거나 비활성화된 경우 기존 방식 (단일 API key)
        if not self._account_manager:
            self.api_key = api_key or Config.LLM_API_KEY
            self.base_url = base_url or Config.LLM_BASE_URL
            if not self.api_key:
                raise ValueError("LLM_API_KEY 未配置")
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
        else:
            # 멀티 계정 모드에서는 클라이언트를 동적으로 가져옴
            self.client = None
            self.api_key = None
            self.base_url = None

    def _call_with_account_rotation(self, call_fn, model_override: Optional[str] = None):
        """
        멀티 계정 모드에서 rate limit 시 자동으로 다른 계정으로 전환하여 호출합니다.

        Args:
            call_fn: (client, model) -> result 를 받는 callable
            model_override: 특정 모델 지정 시 사용
        """
        if not self._account_manager:
            # 단일 계정 모드
            return call_fn(self.client, model_override or self.model)

        max_attempts = self._account_manager.account_count * 2
        last_error = None

        for attempt in range(max_attempts):
            account = self._account_manager.get_available_account()
            if account is None:
                # 모든 계정이 rate limited - 가장 빨리 풀리는 계정 대기
                statuses = self._account_manager.get_status()
                rate_limited = [s for s in statuses if s["status"] == "rate_limited"]
                if rate_limited:
                    min_wait = min(s.get("rate_limit_remaining_seconds", 60) for s in rate_limited)
                    wait_time = min(min_wait + 1, 120)
                    logger.info(f"모든 계정 rate limited, {wait_time:.0f}초 대기...")
                    time.sleep(wait_time)
                    continue
                else:
                    raise RuntimeError("사용 가능한 LLM 계정이 없습니다")

            try:
                client = account.get_openai_client()
                use_model = model_override or account.config.model or self.model
                result = call_fn(client, use_model)
                self._account_manager.on_success(account)
                return result

            except RateLimitError as e:
                retry_after = _extract_retry_after(e)
                self._account_manager.on_rate_limit(account, retry_after)
                logger.warning(
                    f"계정 '{account.config.name}' rate limited, "
                    f"다음 계정으로 전환 (attempt {attempt + 1}/{max_attempts})"
                )
                last_error = e
                continue

            except APIStatusError as e:
                if e.status_code == 429:
                    retry_after = _extract_retry_after(e)
                    self._account_manager.on_rate_limit(account, retry_after)
                    last_error = e
                    continue
                # 다른 API 오류
                self._account_manager.on_error(account)
                raise

            except Exception as e:
                self._account_manager.on_error(account)
                raise

        raise last_error or RuntimeError("모든 계정에서 요청 실패")

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None
    ) -> str:
        """
        发送聊天请求

        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            response_format: 响应格式（如JSON模式）

        Returns:
            模型响应文本
        """
        def _do_chat(client: OpenAI, model: str) -> str:
            kwargs = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if response_format:
                kwargs["response_format"] = response_format

            response = client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content
            # 部分模型（如MiniMax M2.5）会在content中包含<think>思考内容，需要移除
            content = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()
            return content

        return self._call_with_account_rotation(_do_chat)

    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096
    ) -> Dict[str, Any]:
        """
        发送聊天请求并返回JSON

        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数

        Returns:
            解析后的JSON对象
        """
        response = self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"}
        )
        # 清理markdown代码块标记
        cleaned_response = response.strip()
        cleaned_response = re.sub(r'^```(?:json)?\s*\n?', '', cleaned_response, flags=re.IGNORECASE)
        cleaned_response = re.sub(r'\n?```\s*$', '', cleaned_response)
        cleaned_response = cleaned_response.strip()

        try:
            return json.loads(cleaned_response)
        except json.JSONDecodeError:
            raise ValueError(f"LLM返回的JSON格式无效: {cleaned_response}")

    def get_account_status(self) -> Optional[List[Dict[str, Any]]]:
        """멀티 계정 상태를 반환합니다. 단일 계정 모드에서는 None."""
        if self._account_manager:
            return self._account_manager.get_status()
        return None


def _extract_retry_after(error: Exception) -> float:
    """API 오류에서 Retry-After 값을 추출합니다."""
    try:
        if hasattr(error, 'response') and error.response is not None:
            headers = getattr(error.response, 'headers', {})
            retry_after = headers.get('retry-after') or headers.get('Retry-After')
            if retry_after:
                return float(retry_after)

            # x-ratelimit-reset-requests 등에서도 추출 시도
            reset_requests = headers.get('x-ratelimit-reset-requests')
            if reset_requests:
                # "1s", "30s", "1m" 등의 형식
                if reset_requests.endswith('s'):
                    return float(reset_requests[:-1])
                elif reset_requests.endswith('m'):
                    return float(reset_requests[:-1]) * 60

        # 오류 메시지에서 시간 추출 시도
        error_msg = str(error)
        import re as _re
        match = _re.search(r'try again in (\d+\.?\d*)s', error_msg)
        if match:
            return float(match.group(1))
        match = _re.search(r'retry after (\d+)', error_msg, _re.IGNORECASE)
        if match:
            return float(match.group(1))
    except Exception:
        pass

    return 60.0  # 기본 60초 대기

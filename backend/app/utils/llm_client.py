"""
LLM客户端封装
统一使用OpenAI格式调用，支持多账户、OAuth认证和Extended Thinking
"""

import json
import re
import time
from typing import Optional, Dict, Any, List
from openai import OpenAI, RateLimitError, APIStatusError, APIConnectionError, APITimeoutError

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
    """LLM客户端 - 支持API Key和OAuth认证，多账户自动切换，Extended Thinking"""

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
            self.client = None
            self.api_key = None
            self.base_url = None

    def _call_with_account_rotation(self, call_fn, model_override: Optional[str] = None):
        """
        멀티 계정 모드에서 rate limit 시 자동으로 다른 계정으로 전환하여 호출합니다.

        Args:
            call_fn: (client, model, account_state_or_none) -> result 를 받는 callable
            model_override: 특정 모델 지정 시 사용
        """
        from .account_manager import FailureReason

        if not self._account_manager:
            return call_fn(self.client, model_override or self.model, None)

        max_attempts = self._account_manager.account_count * 2
        last_error = None

        for attempt in range(max_attempts):
            account = self._account_manager.get_available_account()
            if account is None:
                wait_time = self._account_manager.get_soonest_available_time()
                if wait_time is not None and wait_time > 0:
                    capped_wait = min(wait_time + 1, 120)
                    logger.info(f"모든 계정 cooldown, {capped_wait:.0f}초 대기...")
                    time.sleep(capped_wait)
                    continue
                else:
                    raise RuntimeError("사용 가능한 LLM 계정이 없습니다")

            try:
                client = account.get_openai_client()
                use_model = model_override or account.config.model or self.model
                result = call_fn(client, use_model, account)
                self._account_manager.on_success(account)
                return result

            except RateLimitError as e:
                retry_after = _extract_retry_after(e)
                self._account_manager.on_failure(account, FailureReason.RATE_LIMIT, retry_after)
                logger.warning(
                    f"계정 '{account.config.name}' rate limited → 다음 계정으로 전환 "
                    f"(attempt {attempt + 1}/{max_attempts})"
                )
                last_error = e
                continue

            except APIStatusError as e:
                reason = _classify_api_error(e)
                retry_after = _extract_retry_after(e) if reason == FailureReason.RATE_LIMIT else None
                self._account_manager.on_failure(account, reason, retry_after)

                if reason in (FailureReason.RATE_LIMIT, FailureReason.OVERLOADED):
                    logger.warning(
                        f"계정 '{account.config.name}' {reason.value} → 다음 계정 전환"
                    )
                    last_error = e
                    continue
                # auth, billing 등 복구 불가능한 오류는 다음 계정 시도
                if reason in (FailureReason.AUTH, FailureReason.BILLING, FailureReason.MODEL_NOT_FOUND):
                    last_error = e
                    continue
                raise

            except APITimeoutError as e:
                self._account_manager.on_failure(account, FailureReason.TIMEOUT)
                last_error = e
                continue

            except APIConnectionError as e:
                self._account_manager.on_failure(account, FailureReason.UNKNOWN, 15.0)
                last_error = e
                continue

            except Exception as e:
                self._account_manager.on_failure(account, FailureReason.UNKNOWN)
                raise

        raise last_error or RuntimeError("모든 계정에서 요청 실패")

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None,
        thinking: Optional[str] = None,
        thinking_budget: Optional[int] = None,
    ) -> str:
        """
        发送聊天请求

        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            response_format: 响应格式（如JSON模式）
            thinking: Thinking level ("off"/"low"/"medium"/"high"/"xhigh")
            thinking_budget: Max thinking budget tokens

        Returns:
            模型响应文本
        """
        from .account_manager import normalize_think_level, clamp_think_level, supports_thinking

        def _do_chat(client: OpenAI, model: str, account) -> str:
            # thinking level 결정: 파라미터 > 계정 기본값
            effective_thinking = normalize_think_level(thinking)
            if effective_thinking is None and account is not None:
                effective_thinking = account.effective_thinking
            if effective_thinking:
                effective_thinking = clamp_think_level(effective_thinking, model)

            is_thinking_model = supports_thinking(model)
            use_thinking = effective_thinking and effective_thinking != "off" and is_thinking_model

            kwargs = {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
            }

            if use_thinking:
                # Thinking 모델은 temperature를 지원하지 않거나 1만 허용하는 경우가 많음
                # OpenAI o-series: temperature 미지원
                # Anthropic: temperature 지원하되 thinking 시 제한
                if not _is_openai_reasoning_model(model):
                    kwargs["temperature"] = temperature

                # OpenAI o-series: reasoning_effort 파라미터
                if _is_openai_reasoning_model(model):
                    kwargs["reasoning_effort"] = effective_thinking
                    # max_completion_tokens 사용 (max_tokens 대신)
                    del kwargs["max_tokens"]
                    budget = thinking_budget
                    if budget is None and account is not None:
                        budget = account.config.max_thinking_budget
                    kwargs["max_completion_tokens"] = (budget or max_tokens) + max_tokens
                else:
                    # Anthropic, Gemini 등: thinking 파라미터
                    budget = thinking_budget
                    if budget is None and account is not None:
                        budget = account.config.max_thinking_budget
                    kwargs["thinking"] = {
                        "type": "enabled",
                        "budget_tokens": budget or 10000,
                    }
                    kwargs["temperature"] = 1  # Anthropic thinking은 temperature=1 필수
            else:
                kwargs["temperature"] = temperature

            if response_format:
                kwargs["response_format"] = response_format

            response = client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content
            # 部分模型会在content中包含<think>思考内容，需要移除
            content = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()
            return content

        return self._call_with_account_rotation(_do_chat)

    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
        thinking: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        发送聊天请求并返回JSON

        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            thinking: Thinking level

        Returns:
            解析后的JSON对象
        """
        response = self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            thinking=thinking,
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


def _is_openai_reasoning_model(model: str) -> bool:
    """OpenAI의 reasoning 모델(o-series)인지 확인합니다."""
    m = model.strip().lower()
    return bool(re.match(r'^o[1-9]', m))


def _classify_api_error(error: APIStatusError) -> 'FailureReason':
    """API 에러를 FailureReason으로 분류합니다 (openclaw 패턴)."""
    from .account_manager import FailureReason

    status = error.status_code
    if status == 429:
        return FailureReason.RATE_LIMIT
    if status in (401, 403):
        return FailureReason.AUTH
    if status == 402:
        return FailureReason.BILLING
    if status == 404:
        return FailureReason.MODEL_NOT_FOUND
    if status in (502, 503, 529):
        return FailureReason.OVERLOADED
    if status == 408:
        return FailureReason.TIMEOUT
    return FailureReason.UNKNOWN


def _extract_retry_after(error: Exception) -> float:
    """API 오류에서 Retry-After 값을 추출합니다."""
    try:
        if hasattr(error, 'response') and error.response is not None:
            headers = getattr(error.response, 'headers', {})
            retry_after = headers.get('retry-after') or headers.get('Retry-After')
            if retry_after:
                return float(retry_after)

            reset_requests = headers.get('x-ratelimit-reset-requests')
            if reset_requests:
                if reset_requests.endswith('s'):
                    return float(reset_requests[:-1])
                elif reset_requests.endswith('m'):
                    return float(reset_requests[:-1]) * 60

        error_msg = str(error)
        match = re.search(r'try again in (\d+\.?\d*)s', error_msg)
        if match:
            return float(match.group(1))
        match = re.search(r'retry after (\d+)', error_msg, re.IGNORECASE)
        if match:
            return float(match.group(1))
    except Exception:
        pass

    return 60.0

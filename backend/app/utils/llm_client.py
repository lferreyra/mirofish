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
        """
        from .account_manager import FailureReason

        if not self._account_manager:
            return call_fn(self.client, model_override or self.model, None)

        max_attempts = self._account_manager.account_count * 3
        last_error = None

        for attempt in range(max_attempts):
            account = self._account_manager.get_available_account()
            if account is None:
                wait_time = self._account_manager.get_soonest_available_time()
                if wait_time is not None and wait_time > 0:
                    # 대기 시간이 너무 길면 (5분 초과) 에러 반환
                    if wait_time > 300:
                        raise RuntimeError(
                            f"모든 계정 cooldown 중. 가장 빠른 복구까지 {wait_time:.0f}초 "
                            f"({wait_time / 60:.0f}분). 수동 대기 필요."
                        )
                    capped_wait = min(wait_time + 1, 300)
                    logger.info(f"모든 계정 cooldown, {capped_wait:.0f}초 대기...")
                    time.sleep(capped_wait)
                    continue
                else:
                    raise RuntimeError("사용 가능한 LLM 계정이 없습니다 (모든 계정 비활성화)")

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
                    f"계정 '{account.config.name}' rate limited → 다음 계정 전환 "
                    f"(attempt {attempt + 1}/{max_attempts})"
                )
                last_error = e
                continue

            except APIStatusError as e:
                reason = _classify_api_error(e)
                retry_after = _extract_retry_after(e) if reason == FailureReason.RATE_LIMIT else None
                self._account_manager.on_failure(account, reason, retry_after)

                if reason in (
                    FailureReason.RATE_LIMIT, FailureReason.OVERLOADED,
                    FailureReason.AUTH, FailureReason.BILLING,
                    FailureReason.MODEL_NOT_FOUND,
                ):
                    logger.warning(
                        f"계정 '{account.config.name}' {reason.value} → 다음 계정 전환"
                    )
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
        from .account_manager import (
            normalize_think_level, clamp_think_level, supports_thinking,
            is_openai_reasoning_model, map_to_openai_reasoning_effort,
        )

        def _do_chat(client: OpenAI, model: str, account) -> str:
            # thinking level 결정: 파라미터 > 계정 기본값
            effective_thinking = normalize_think_level(thinking)
            if effective_thinking is None and account is not None:
                effective_thinking = account.effective_thinking
            if effective_thinking:
                effective_thinking = clamp_think_level(effective_thinking, model)

            is_thinking = supports_thinking(model)
            is_o_series = is_openai_reasoning_model(model)
            use_thinking = effective_thinking and effective_thinking != "off" and is_thinking

            kwargs = {
                "model": model,
                "messages": messages,
            }

            # o-series는 항상 max_completion_tokens 사용 (max_tokens deprecated)
            if is_o_series:
                kwargs["max_completion_tokens"] = max_tokens
            else:
                kwargs["max_tokens"] = max_tokens

            if use_thinking:
                if is_o_series:
                    # OpenAI o-series: reasoning_effort ("low"/"medium"/"high" 만 허용)
                    kwargs["reasoning_effort"] = map_to_openai_reasoning_effort(effective_thinking)
                    # thinking budget이 있으면 max_completion_tokens에 합산
                    budget = thinking_budget
                    if budget is None and account is not None:
                        budget = account.config.max_thinking_budget
                    if budget:
                        kwargs["max_completion_tokens"] = budget + max_tokens
                    # o-series는 temperature 미지원 → 설정하지 않음
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
                # o-series는 thinking 안 쓸 때도 temperature 미지원
                if not is_o_series:
                    kwargs["temperature"] = temperature

            if response_format:
                kwargs["response_format"] = response_format

            response = client.chat.completions.create(**kwargs)

            # content가 None인 경우 처리 (thinking 모델은 thinking 필드에만 내용이 있을 수 있음)
            content = response.choices[0].message.content
            if content is None:
                # thinking 응답이 있으면 그걸 사용
                if hasattr(response.choices[0].message, 'thinking') and response.choices[0].message.thinking:
                    content = response.choices[0].message.thinking
                    logger.warning("LLM 응답의 content가 None, thinking 내용을 사용")
                elif hasattr(response.choices[0].message, 'refusal') and response.choices[0].message.refusal:
                    raise ValueError(f"LLM이 요청을 거부: {response.choices[0].message.refusal}")
                else:
                    raise ValueError("LLM 응답의 content가 비어있습니다")

            # <think> 태그 제거 (일부 모델이 content에 thinking을 포함)
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


def _classify_api_error(error: APIStatusError) -> 'FailureReason':
    """API 에러를 FailureReason으로 분류합니다."""
    from .account_manager import FailureReason

    status = error.status_code
    if status == 429:
        return FailureReason.RATE_LIMIT
    if status == 401:
        return FailureReason.AUTH
    if status == 403:
        # 403은 영구적 auth 문제일 수 있음 (권한 없음)
        return FailureReason.AUTH_PERMANENT
    if status == 402:
        return FailureReason.BILLING
    if status == 404:
        return FailureReason.MODEL_NOT_FOUND
    if status in (502, 503, 529):
        return FailureReason.OVERLOADED
    if status == 408:
        return FailureReason.TIMEOUT
    return FailureReason.UNKNOWN


def _extract_retry_after(error: Exception) -> Optional[float]:
    """API 오류에서 Retry-After 값을 추출합니다. 없으면 None 반환."""
    try:
        if hasattr(error, 'response') and error.response is not None:
            headers = getattr(error.response, 'headers', {})

            # Retry-After 헤더
            retry_after = headers.get('retry-after') or headers.get('Retry-After')
            if retry_after:
                return float(retry_after)

            # x-ratelimit-reset-requests 헤더 (OpenAI/Codex)
            reset_requests = headers.get('x-ratelimit-reset-requests')
            if reset_requests:
                return _parse_duration_string(reset_requests)

            # x-ratelimit-reset-tokens 헤더
            reset_tokens = headers.get('x-ratelimit-reset-tokens')
            if reset_tokens:
                return _parse_duration_string(reset_tokens)

        # 에러 메시지에서 시간 추출 시도
        error_msg = str(error)
        match = re.search(r'try again in (\d+\.?\d*)s', error_msg)
        if match:
            return float(match.group(1))
        match = re.search(r'try again in (\d+\.?\d*)m', error_msg)
        if match:
            return float(match.group(1)) * 60
        match = re.search(r'try again in (\d+\.?\d*)h', error_msg)
        if match:
            return float(match.group(1)) * 3600
        match = re.search(r'retry after (\d+)', error_msg, re.IGNORECASE)
        if match:
            return float(match.group(1))
    except Exception:
        pass

    return None  # 추출 실패 → calculate_cooldown()의 지수 백오프 사용


def _parse_duration_string(duration: str) -> Optional[float]:
    """'1s', '30s', '1m', '2m30s', '1h', '5h30m' 등의 형식을 초로 변환합니다."""
    duration = duration.strip()
    total = 0.0
    # 시간 파싱
    h_match = re.search(r'(\d+\.?\d*)h', duration)
    if h_match:
        total += float(h_match.group(1)) * 3600
    # 분 파싱
    m_match = re.search(r'(\d+\.?\d*)m(?!s)', duration)
    if m_match:
        total += float(m_match.group(1)) * 60
    # 초 파싱
    s_match = re.search(r'(\d+\.?\d*)(?:s|ms)', duration)
    if s_match:
        if 'ms' in duration:
            total += float(s_match.group(1)) / 1000
        else:
            total += float(s_match.group(1))
    # 순수 숫자만 있으면 초로 간주
    if total == 0 and re.match(r'^\d+\.?\d*$', duration):
        total = float(duration)
    return total if total > 0 else None

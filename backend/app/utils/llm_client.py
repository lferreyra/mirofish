"""
LLM客户端封装
统一使用OpenAI格式调用
"""

import base64
import json
import re
import time
from typing import Optional, Dict, Any, List
from openai import OpenAI

from ..config import Config
from .logger import get_logger
from .openrouter_runtime import classify_openrouter_error, is_openrouter_base_url

logger = get_logger('mirofish.llm_client')


class LLMResponseError(RuntimeError):
    """LLM返回了无法安全消费的响应结构。"""


class LLMEmptyResponseError(LLMResponseError):
    """LLM响应成功但内容为空。"""


class LLMJSONParseError(ValueError):
    """LLM返回了无法解析的JSON。"""


def describe_llm_failure(
    exc: Exception,
    *,
    request_label: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Return compact failure metadata for API responses/logs."""
    provider = "openrouter" if is_openrouter_base_url(base_url) else "generic-openai-compatible"
    failure_category = type(exc).__name__
    retryable = False

    if isinstance(exc, LLMEmptyResponseError):
        failure_category = "empty_response"
        retryable = True
    elif isinstance(exc, LLMJSONParseError):
        failure_category = "invalid_json"
        retryable = True
    elif isinstance(exc, LLMResponseError):
        failure_category = "llm_response_error"
    elif provider == "openrouter":
        failure_category = classify_openrouter_error(exc)
        retryable = failure_category in {
            "connection_error",
            "free_plan_rate_limit",
            "rate_limit",
            "quota_or_credit_exhausted",
            "provider_unavailable",
            "auth_error",
        }

    return {
        "request_label": request_label or "unknown",
        "model": model,
        "provider": provider,
        "failure_category": failure_category,
        "status_code": getattr(exc, "status_code", None),
        "retryable": retryable,
    }


class LLMClient:
    """LLM客户端"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ):
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        self.model = model or Config.LLM_MODEL_NAME
        self.timeout_seconds = timeout_seconds or Config.LLM_REQUEST_TIMEOUT_SECONDS
        
        if not self.api_key:
            raise ValueError("LLM_API_KEY 未配置")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout_seconds,
        )

    @staticmethod
    def _response_preview(response: Any, limit: int = 500) -> str:
        """生成紧凑响应预览，便于日志排查。"""
        try:
            if hasattr(response, "model_dump_json"):
                preview = response.model_dump_json(exclude_none=False)
            elif hasattr(response, "model_dump"):
                preview = json.dumps(response.model_dump(), ensure_ascii=False)
            else:
                preview = str(response)
        except Exception:
            preview = repr(response)
        return preview[:limit]

    def _extract_response_content(self, response: Any, request_label: Optional[str] = None) -> str:
        """验证并提取LLM文本响应。"""
        choices = getattr(response, "choices", None)
        choice_count = len(choices) if isinstance(choices, list) else None

        if not choices:
            message = (
                f"LLM returned no choices label={request_label or 'unknown'} "
                f"model={self.model} response_preview={self._response_preview(response)}"
            )
            logger.error(message)
            raise LLMResponseError(message)

        first_choice = choices[0]
        finish_reason = getattr(first_choice, "finish_reason", None)
        message = getattr(first_choice, "message", None)
        content = getattr(message, "content", None) if message is not None else None

        if content is None or not str(content).strip():
            error_cls = LLMEmptyResponseError if content is None or content == "" else LLMResponseError
            message_text = (
                f"LLM returned empty content label={request_label or 'unknown'} "
                f"model={self.model} finish_reason={finish_reason} "
                f"choices_present={choices is not None} choice_count={choice_count} "
                f"response_preview={self._response_preview(response)}"
            )
            logger.warning(message_text)
            raise error_cls(message_text)

        content = str(content)
        # 部分模型（如MiniMax M2.5）会在content中包含<think>思考内容，需要移除
        return re.sub(r'<think>[\s\S]*?</think>', '', content).strip()

    @staticmethod
    def _parse_json_response(cleaned_response: str) -> Dict[str, Any]:
        try:
            return json.loads(cleaned_response)
        except json.JSONDecodeError:
            match = re.search(r'\{[\s\S]*\}', cleaned_response)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            logger.error("JSON parsing failed, response prefix: %s", cleaned_response[:500])
            raise LLMJSONParseError(f"LLM返回的JSON格式无效: {cleaned_response[:200]}")
    
    def chat(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None,
        request_label: Optional[str] = None,
        retry_attempts: int = 1,
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
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if response_format:
            kwargs["response_format"] = response_format

        total_attempts = max(1, retry_attempts)
        last_error: Optional[Exception] = None

        for attempt in range(1, total_attempts + 1):
            if request_label:
                logger.info(
                    "LLM call start label=%s attempt=%s/%s model=%s provider=%s timeout_seconds=%s",
                    request_label,
                    attempt,
                    total_attempts,
                    self.model,
                    "openrouter" if is_openrouter_base_url(self.base_url) else "generic-openai-compatible",
                    self.timeout_seconds,
                )

            started_at = time.monotonic()
            try:
                response = self.client.chat.completions.create(**kwargs)
                elapsed_ms = round((time.monotonic() - started_at) * 1000)
                content = self._extract_response_content(response, request_label=request_label)
                if request_label:
                    logger.info(
                        "LLM call success label=%s attempt=%s/%s elapsed_ms=%s content_length=%s",
                        request_label,
                        attempt,
                        total_attempts,
                        elapsed_ms,
                        len(content),
                    )
                return content
            except Exception as e:
                last_error = e
                elapsed_ms = round((time.monotonic() - started_at) * 1000)
                retryable_error = isinstance(e, (LLMResponseError, LLMEmptyResponseError))
                if not retryable_error and is_openrouter_base_url(self.base_url):
                    retryable_error = classify_openrouter_error(e) in {
                        "connection_error",
                        "free_plan_rate_limit",
                        "rate_limit",
                        "quota_or_credit_exhausted",
                        "provider_unavailable",
                    }

                should_retry = retryable_error and attempt < total_attempts
                if request_label:
                    logger.warning(
                        "LLM call failed label=%s attempt=%s/%s elapsed_ms=%s retry=%s error_type=%s error=%s",
                        request_label,
                        attempt,
                        total_attempts,
                        elapsed_ms,
                        should_retry,
                        type(e).__name__,
                        str(e)[:240],
                    )

                if not should_retry:
                    raise

                time.sleep(min(attempt, 2))

        if isinstance(last_error, Exception):
            raise last_error
        raise LLMResponseError(f"LLM call failed without captured error label={request_label or 'unknown'}")
    
    def analyze_image(
        self,
        image_bytes: bytes,
        prompt: str,
        mime_type: str = "image/png",
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 1800,
        request_label: Optional[str] = None,
    ) -> str:
        """
        使用多模态模型分析图片。
        
        Args:
            image_bytes: 图片二进制内容
            prompt: 用户提示词
            mime_type: 图片 MIME 类型
            system_prompt: 系统提示词
            temperature: 温度参数
            max_tokens: 最大 token 数
            
        Returns:
            模型响应文本
        """
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        user_message = {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime_type};base64,{image_base64}"
                    }
                }
            ]
        }
        messages: List[Dict[str, Any]] = [user_message]
        
        if system_prompt:
            messages.insert(0, {"role": "system", "content": system_prompt})
        
        return self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            request_label=request_label,
        )
    
    def chat_json(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
        request_label: Optional[str] = None,
        retry_attempts: int = 1,
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
        total_attempts = max(1, retry_attempts)
        last_error: Optional[Exception] = None

        for attempt in range(1, total_attempts + 1):
            try:
                logger.info(
                    "LLM JSON call attempt label=%s attempt=%s/%s",
                    request_label or "unknown",
                    attempt,
                    total_attempts,
                )
                response = self.chat(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format={"type": "json_object"},
                    request_label=request_label,
                )

                cleaned_response = response.strip()
                cleaned_response = re.sub(r'^```(?:json)?\s*\n?', '', cleaned_response, flags=re.IGNORECASE)
                cleaned_response = re.sub(r'\n?```\s*$', '', cleaned_response)
                cleaned_response = cleaned_response.strip()

                if not cleaned_response:
                    raise LLMEmptyResponseError(
                        f"LLM returned blank JSON content label={request_label or 'unknown'} model={self.model}"
                    )

                return self._parse_json_response(cleaned_response)
            except (LLMResponseError, LLMJSONParseError, ValueError) as exc:
                last_error = exc
                should_retry = attempt < total_attempts
                logger.warning(
                    "LLM JSON call retryable failure label=%s attempt=%s/%s error_type=%s retry=%s error=%s",
                    request_label or "unknown",
                    attempt,
                    total_attempts,
                    type(exc).__name__,
                    should_retry,
                    str(exc)[:240],
                )
                if not should_retry:
                    break
                time.sleep(min(attempt, 2))

        if isinstance(last_error, Exception):
            raise last_error
        raise LLMResponseError(f"LLM JSON call failed without captured error label={request_label or 'unknown'}")

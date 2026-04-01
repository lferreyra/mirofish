"""
LLM客户端封装
统一使用OpenAI格式调用
"""

import json
import re
import time
from typing import Optional, Dict, Any, List
from openai import OpenAI, RateLimitError, APITimeoutError, APIConnectionError, APIStatusError

from ..config import Config
from .logger import get_logger

logger = get_logger('mirofish.llm_client')

# 可重试的错误类型（网络/限流类瞬时错误）
_RETRYABLE_ERRORS = (RateLimitError, APITimeoutError, APIConnectionError)


class LLMClient:
    """LLM客户端"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ):
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        self.model = model or Config.LLM_MODEL_NAME
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        if not self.api_key:
            raise ValueError("LLM_API_KEY 未配置")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None
    ) -> str:
        """
        发送聊天请求（含指数退避重试）

        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            response_format: 响应格式（如JSON模式）

        Returns:
            模型响应文本

        Raises:
            RateLimitError: 超过速率限制且重试耗尽
            APITimeoutError: 请求超时且重试耗尽
            APIConnectionError: 网络连接错误且重试耗尽
            APIStatusError: 4xx/5xx 不可重试的服务端错误
            ValueError: LLM_API_KEY 未配置
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if response_format:
            kwargs["response_format"] = response_format

        last_error: Exception = RuntimeError("未知错误")
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content
                # 部分模型（如MiniMax M2.5）会在content中包含<think>思考内容，需要移除
                content = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()
                return content

            except _RETRYABLE_ERRORS as e:
                last_error = e
                wait = self.retry_delay * (2 ** attempt)
                logger.warning(
                    f"LLM请求失败（可重试，第 {attempt + 1}/{self.max_retries} 次）: "
                    f"{type(e).__name__}: {e}. {wait:.1f}s 后重试..."
                )
                if attempt < self.max_retries - 1:
                    time.sleep(wait)

            except APIStatusError as e:
                # 4xx 客户端错误不重试（认证失败、参数错误等）
                logger.error(
                    f"LLM API 状态错误 [{e.status_code}]: {e.message}",
                    exc_info=True
                )
                raise

        logger.error(
            f"LLM请求在 {self.max_retries} 次重试后仍失败: {last_error}",
            exc_info=True
        )
        raise last_error

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

        Raises:
            ValueError: LLM返回的内容无法解析为合法JSON
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
        except json.JSONDecodeError as e:
            raise ValueError(f"LLM返回的JSON格式无效: {e}") from e

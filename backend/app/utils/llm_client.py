"""
LLM client wrapper.
Unified OpenAI-compatible API calls with timeout and retry.
"""

import os
import json
import re
from typing import Optional, Dict, Any, List
from openai import OpenAI, APIError, APIConnectionError, RateLimitError, APITimeoutError

from ..config import Config
from ..utils.logger import get_logger

logger = get_logger('mirofish.llm')


class LLMClient:
    """LLM client with timeout and retry."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        self.model = model or Config.LLM_MODEL_NAME

        if not self.api_key:
            raise ValueError("LLM_API_KEY is not configured")

        timeout = float(os.environ.get('LLM_TIMEOUT', '120'))
        self.max_retries = int(os.environ.get('LLM_MAX_RETRIES', '3'))

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=timeout,
        )
    
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
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if response_format:
            kwargs["response_format"] = response_format
        
        retryable_exceptions = (APIError, APIConnectionError, RateLimitError, APITimeoutError)
        last_exception = None
        import time as _time

        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content
                # Some models (e.g. MiniMax M2.5) include <think> tags that need removal
                content = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()
                return content
            except retryable_exceptions as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = min(2 ** attempt, 30)
                    logger.warning(f"LLM call attempt {attempt + 1} failed: {e}, retrying in {delay}s...")
                    _time.sleep(delay)
                else:
                    logger.error(f"LLM call failed after {self.max_retries + 1} attempts: {e}")
                    raise
    
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


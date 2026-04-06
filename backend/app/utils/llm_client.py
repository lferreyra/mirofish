"""
LLM客户端封装
统一使用OpenAI格式调用
"""

import base64
import json
import re
from typing import Optional, Dict, Any, List
from openai import OpenAI

from ..config import Config
from .logger import get_logger
from .openrouter_runtime import classify_openrouter_error, is_openrouter_base_url

logger = get_logger('mirofish.llm_client')


class LLMClient:
    """LLM客户端"""
    
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
            raise ValueError("LLM_API_KEY 未配置")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    def chat(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None,
        request_label: Optional[str] = None,
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

        if request_label:
            logger.info(
                "LLM call start label=%s model=%s provider=%s",
                request_label,
                self.model,
                "openrouter" if is_openrouter_base_url(self.base_url) else "generic-openai-compatible",
            )

        try:
            response = self.client.chat.completions.create(**kwargs)
        except Exception as e:
            if request_label:
                logger.warning(
                    "LLM call failed label=%s category=%s error=%s",
                    request_label,
                    classify_openrouter_error(e) if is_openrouter_base_url(self.base_url) else "non_openrouter_error",
                    str(e)[:200],
                )
            raise

        content = response.choices[0].message.content
        if content is None:
            finish_reason = None
            if getattr(response, "choices", None):
                finish_reason = getattr(response.choices[0], "finish_reason", None)
            logger.warning(
                "LLM returned empty content label=%s model=%s finish_reason=%s",
                request_label or "unknown",
                self.model,
                finish_reason,
            )
            return ""

        # 部分模型（如MiniMax M2.5）会在content中包含<think>思考内容，需要移除
        content = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()
        return content
    
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
            response_format={"type": "json_object"},
            request_label=request_label,
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

"""
LLM客户端封装
统一使用OpenAI格式调用
支持 GitHub Copilot 作为 LLM 后端（自动token交换）
"""

import json
import re
from typing import Optional, Dict, Any, List
from openai import OpenAI

from ..config import Config
from .copilot_auth import is_copilot_provider, get_copilot_token_manager, COPILOT_REQUEST_HEADERS


class LLMClient:
    """LLM客户端（支持标准 OpenAI API 和 GitHub Copilot）"""
    
    _copilot_mode: bool = False
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        # 检测是否使用 GitHub Copilot 作为 LLM 后端
        if not api_key and is_copilot_provider():
            self._copilot_mode = True
            mgr = get_copilot_token_manager()
            self.api_key = mgr.get_api_key()
            self.base_url = base_url or mgr.get_base_url()
            self.model = model or Config.LLM_MODEL_NAME
        else:
            self._copilot_mode = False
            self.api_key = api_key or Config.LLM_API_KEY
            self.base_url = base_url or Config.LLM_BASE_URL
            self.model = model or Config.LLM_MODEL_NAME
        
        if not self.api_key:
            raise ValueError(
                "LLM_API_KEY 未配置。请设置 LLM_API_KEY，"
                "或设置 LLM_PROVIDER=github-copilot 并配置 GITHUB_TOKEN 以使用 Copilot。"
            )
        
        self.client = self._create_openai_client()
    
    def _create_openai_client(self) -> OpenAI:
        """创建 OpenAI 客户端（Copilot 模式下附加必需的请求头）"""
        kwargs = {
            "api_key": self.api_key,
            "base_url": self.base_url,
        }
        if self._copilot_mode:
            kwargs["default_headers"] = {
                "Editor-Version": COPILOT_REQUEST_HEADERS["Editor-Version"],
                "User-Agent": COPILOT_REQUEST_HEADERS["User-Agent"],
                "X-Github-Api-Version": COPILOT_REQUEST_HEADERS["X-Github-Api-Version"],
            }
        return OpenAI(**kwargs)
    
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
        # 如果使用 Copilot，自动刷新可能过期的 token
        if self._copilot_mode:
            self._refresh_copilot_client()
        
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if response_format:
            kwargs["response_format"] = response_format
        
        response = self.client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        # 部分模型（如MiniMax M2.5）会在content中包含<think>思考内容，需要移除
        content = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()
        return content
    
    def _refresh_copilot_client(self):
        """刷新 Copilot token（如果已过期），并重建 OpenAI 客户端"""
        mgr = get_copilot_token_manager()
        new_key = mgr.get_api_key()
        if new_key != self.api_key:
            self.api_key = new_key
            self.base_url = mgr.get_base_url()
            self.client = self._create_openai_client()
    
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


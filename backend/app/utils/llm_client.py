"""
LLM客户端封装
统一使用OpenAI格式调用
"""

import json
import re
from typing import Optional, Dict, Any, List, Tuple
from openai import OpenAI

from ..config import Config


def estimate_tokens(text: str) -> int:
    """
    粗略估算文本的 token 数量（无需依赖 tiktoken）。

    规则：
    - 中文字符按每字 ~1.5 token 估算（UTF-8 汉字实际约 1-2 tokens）
    - ASCII 单词按每词 ~1.3 token 估算
    - 额外添加 10% buffer

    Args:
        text: 待估算的文本

    Returns:
        估算的 token 数
    """
    if not text:
        return 0
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    # 剩余字符按空格分词估算
    rest = ''.join(c if c < '\u4e00' or c > '\u9fff' else ' ' for c in text)
    ascii_words = len(rest.split())
    estimated = int(chinese_chars * 1.5 + ascii_words * 1.3)
    return int(estimated * 1.1)  # 10% buffer


def estimate_messages_tokens(messages: List[Dict]) -> int:
    """估算消息列表的总 token 数"""
    total = 0
    for msg in messages:
        content = msg.get("content") or ""
        if isinstance(content, list):
            content = " ".join(
                c.get("text", "") for c in content if isinstance(c, dict)
            )
        total += estimate_tokens(content) + 4  # role + overhead per message
    return total + 2  # conversation overhead


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
        
        response = self.client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        # 部分模型（如MiniMax M2.5）会在content中包含<think>思考内容，需要移除
        content = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()
        return content
    
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

    def chat_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> Tuple[Optional[str], Optional[List[Dict[str, Any]]]]:
        """
        使用 OpenAI native function calling 发送请求。

        Args:
            messages: 消息列表（支持 tool role 消息）
            tools: OpenAI tools 格式的工具定义列表
            temperature: 温度参数
            max_tokens: 最大 token 数

        Returns:
            (content, tool_calls)
            - content: 文本内容（无工具调用时为完整回复，有工具调用时可能为 None 或思考文字）
            - tool_calls: 工具调用列表，每项为
              {"id": str, "name": str, "parameters": dict}
              若没有工具调用则为 None
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=temperature,
            max_tokens=max_tokens,
        )

        message = response.choices[0].message
        content = message.content or ""
        content = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()

        if not message.tool_calls:
            return content, None

        parsed_calls = []
        for tc in message.tool_calls:
            try:
                params = json.loads(tc.function.arguments)
            except (json.JSONDecodeError, AttributeError):
                params = {}
            parsed_calls.append({
                "id": tc.id,
                "name": tc.function.name,
                "parameters": params,
            })

        return content, parsed_calls


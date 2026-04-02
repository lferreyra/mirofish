"""
LLM客户端封装
统一使用OpenAI格式调用
"""

import json
import re
from typing import Optional, Dict, Any, List
from openai import OpenAI

from ..config import Config


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
    ) -> Optional[str]:
        """
        发送聊天请求
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            response_format: 响应格式（如JSON模式）
            
        Returns:
            模型响应文本，若模型返回空内容则返回 None
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
        message = response.choices[0].message
        content = message.content

        # 部分推理模型（如 Qwen3-thinking、DeepSeek-R1）在思维链模式下
        # 会把思考过程放入 reasoning_content，content 字段可能为 None 或空字符串。
        # 此时尝试从 reasoning_content 兜底提取实际回答。
        if not content:
            reasoning = getattr(message, 'reasoning_content', None)
            if reasoning:
                # reasoning_content 是思考过程，不是最终答案；
                # 说明模型在思考阶段被截断，无有效 content，返回 None
                pass
            return None

        # 移除部分模型在 content 中内联的 <think>...</think> 思考块
        # （如 MiniMax M2.5 / 部分 Qwen3 非流式模式）
        content = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()
        return content if content else None
    
    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096
    ) -> Dict[str, Any]:
        """
        发送聊天请求并返回JSON
        
        不使用 response_format=json_object，以兼容思维链推理模型
        （Qwen3-thinking、DeepSeek-R1 等不支持该参数）。
        改为从模型的文本输出中手动提取 JSON。
        
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
            # 不传 response_format，避免思维链模型返回 content=None
        )
        if response is None:
            raise ValueError(
                "LLM 返回内容为空（content=None）。"
                "可能原因：模型为推理/思维链模型且内容被截断，或 max_tokens 不足。"
                f"当前模型: {self.model}"
            )

        # 从文本中提取 JSON（兼容 markdown 代码块和裸 JSON 两种格式）
        cleaned = response.strip()

        # 优先尝试提取 ```json ... ``` 代码块
        json_block = re.search(r'```(?:json)?\s*\n?([\s\S]*?)\n?```', cleaned, re.IGNORECASE)
        if json_block:
            cleaned = json_block.group(1).strip()
        else:
            # 去除首尾的 markdown 围栏（无语言标记的情况）
            cleaned = re.sub(r'^```\s*\n?', '', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r'\n?```\s*$', '', cleaned)
            cleaned = cleaned.strip()

        # 尝试从文本中定位第一个 { 到最后一个 }，提取 JSON 主体
        start = cleaned.find('{')
        end = cleaned.rfind('}')
        if start != -1 and end != -1 and end > start:
            cleaned = cleaned[start:end + 1]

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            raise ValueError(f"LLM返回的JSON格式无效: {cleaned[:500]}")

"""
LLM客户端封装
统一使用OpenAI格式调用
支持多Key自动轮换 - Groq 3 keys + Gemini 3 keys
当一个Key达到限制时自动切换到下一个Key
"""

import json
import re
from typing import Optional, Dict, Any, List
from openai import OpenAI

from ..config import Config


class LLMClient:
    """LLM客户端 - 支持多Key自动轮换"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.base_url = base_url or Config.LLM_BASE_URL
        self.model = model or Config.LLM_MODEL_NAME

        # Build key pool: if specific key provided use it, else load all from config
        if api_key:
            self.key_pool = [api_key]
        else:
            self.key_pool = Config.get_primary_keys()

        if not self.key_pool:
            raise ValueError("LLM_API_KEY_1 未配置")

        self.current_key_index = 0
        self.client = self._make_client(self.key_pool[0])

    def _make_client(self, api_key: str) -> OpenAI:
        return OpenAI(api_key=api_key, base_url=self.base_url)

    def _rotate_key(self) -> bool:
        """Rotate to next available key. Returns False if all exhausted."""
        next_index = self.current_key_index + 1
        if next_index < len(self.key_pool):
            self.current_key_index = next_index
            self.client = self._make_client(self.key_pool[next_index])
            print(f"🔄 [LLMClient] Rotated to primary key {next_index + 1}/{len(self.key_pool)}")
            return True
        print("❌ [LLMClient] All primary keys exhausted")
        return False

    def _is_rate_limit_error(self, error: Exception) -> bool:
        err = str(error)
        return any(x in err for x in ["429", "rate_limit", "rate limit", "quota", "tokens per day", "TPD"])
    
    def _is_too_large_error(self, error: Exception) -> bool:
        err = str(error)
        return "413" in err or "Request too large" in err or "reduce your message size" in err

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 8096,
        response_format: Optional[Dict] = None
    ) -> str:
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format

        last_error = None

        for attempt in range(len(self.key_pool)):
            try:
                response = self.client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content
                # Remove <think> blocks (some models include reasoning)
                content = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()
                return content

            except Exception as e:
                last_error = e
                if self._is_rate_limit_error(e):
                    print(f"⚠️ Key {self.current_key_index + 1} rate limited, rotating...")
                    if not self._rotate_key():
                        break
                elif self._is_too_large_error(e):
                    # No point rotating keys — request itself is too big
                    # Truncate and retry on same key
                    print(f"⚠️ Request too large ({str(e)[:80]}), truncating messages...")
                    messages = self._truncate_messages(messages, target_tokens=8000)
                    kwargs["messages"] = messages
                    continue
                else:
                    raise

        raise Exception(f"❌ All primary LLM keys exhausted. Last error: {last_error}")

    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 8096
    ) -> Dict[str, Any]:
        """Send chat request and return parsed JSON"""
        try:
            response = self.chat(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"}
            )
        except Exception:
            # Model doesn't support response_format, call without it
            response = self.chat(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        # Clean markdown fences
        cleaned_response = response.strip()
        cleaned_response = re.sub(r'^```(?:json)?\s*\n?', '', cleaned_response, flags=re.IGNORECASE)
        cleaned_response = re.sub(r'\n?```\s*$', '', cleaned_response)
        cleaned_response = cleaned_response.strip()

        try:
            return json.loads(cleaned_response)
        except json.JSONDecodeError:
            repaired = self._repair_truncated_json(cleaned_response)
            if repaired:
                return repaired
            raise ValueError(f"LLM返回的JSON格式无效: {cleaned_response[:500]}")
        
    def _truncate_messages(
    self, 
    messages: List[Dict[str, str]], 
    target_tokens: int = 8000
) -> List[Dict[str, str]]:
        """
        Truncate message content to fit within token limit.
        Keeps system message intact, truncates user message content.
        Rough estimate: 1 token ≈ 4 characters
        """
        char_limit = target_tokens * 4  # rough chars-to-tokens ratio
        
        truncated = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            
            if role == "system":
                # Always keep system message as-is
                truncated.append(msg)
            elif role == "user":
                if len(content) > char_limit:
                    # Truncate content and add notice
                    content = content[:char_limit] + "\n\n[Content truncated to fit token limit]"
                    print(f"✂️ Truncated user message from {len(msg['content'])} to {len(content)} chars")
                truncated.append({"role": role, "content": content})
            else:
                truncated.append(msg)
        
        return truncated

    @staticmethod
    def _repair_truncated_json(text: str) -> dict | None:
        """Try to fix truncated JSON by closing open brackets"""
        try:
            open_braces = text.count('{') - text.count('}')
            open_brackets = text.count('[') - text.count(']')
            repaired = text
            if repaired.count('"') % 2 != 0:
                repaired += '"'
            repaired += ']' * open_brackets
            repaired += '}' * open_braces
            return json.loads(repaired)
        except Exception:
            return None


class BoostLLMClient(LLMClient):
    """
    Gemini LLM客户端 - 使用Boost key pool自动轮换
    当一个Gemini Key达到限制时自动切换到下一个
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.base_url = base_url or Config.LLM_BOOST_BASE_URL
        self.model = model or Config.LLM_BOOST_MODEL_NAME

        if api_key:
            self.key_pool = [api_key]
        else:
            self.key_pool = Config.get_boost_keys()

        if not self.key_pool:
            raise ValueError("LLM_BOOST_API_KEY_1 未配置")

        self.current_key_index = 0
        self.client = self._make_client(self.key_pool[0])

    def _rotate_key(self) -> bool:
        next_index = self.current_key_index + 1
        if next_index < len(self.key_pool):
            self.current_key_index = next_index
            self.client = self._make_client(self.key_pool[next_index])
            print(f"🔄 [BoostLLMClient] Rotated to Gemini key {next_index + 1}/{len(self.key_pool)}")
            return True
        print("❌ [BoostLLMClient] All Gemini keys exhausted")
        return False
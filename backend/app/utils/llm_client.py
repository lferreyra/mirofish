"""
LLM client wrapper
Supports claude CLI, OpenAI SDK, and Ollama HTTP providers
"""

import json
import re
import subprocess
from typing import Optional, Dict, Any, List

from ..config import Config
from ..utils.logger import get_logger

logger = get_logger('mirofish.llm_client')


class LLMError(ValueError):
    """Exception raised for LLM-related errors.

    Extends ValueError for backward compatibility with existing callers
    that catch ValueError from the old LLMClient API.
    """
    pass


class LLMClient:
    """Unified LLM client supporting multiple providers."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None
    ):
        self.provider = provider or Config.LLM_PROVIDER
        self.model = model or Config.LLM_MODEL_NAME
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        self._openai_client = None

        if self.provider == "openai":
            if not self.api_key:
                raise LLMError("LLM_API_KEY is not configured (required for openai provider)")
            self._init_openai_client()
        elif self.provider == "ollama":
            self._init_openai_client()

    def _init_openai_client(self):
        """Initialize the OpenAI SDK client (used by openai and ollama providers)."""
        from openai import OpenAI
        self._openai_client = OpenAI(
            api_key=self.api_key or "ollama",
            base_url=self.base_url
        )

    def _flatten_messages(self, messages: List[Dict[str, str]]) -> tuple[str, str]:
        """
        Convert multi-turn messages into a single system prompt and user prompt.

        Extracts system messages as the system prompt.
        Remaining messages are formatted as:
            [User]
            content

            [Assistant]
            content

        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        system_parts = []
        conversation_parts = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                system_parts.append(content)
            elif role == "assistant":
                conversation_parts.append(f"[Assistant]\n{content}")
            else:
                conversation_parts.append(f"[User]\n{content}")

        system_prompt = "\n\n".join(system_parts)
        user_prompt = "\n\n".join(conversation_parts)
        return system_prompt, user_prompt

    @staticmethod
    def _clean_response(content: str) -> str:
        """Remove <think> tags and strip the response."""
        content = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()
        return content

    @staticmethod
    def _clean_json_response(content: str) -> str:
        """Remove markdown code fences from JSON responses."""
        cleaned = content.strip()
        cleaned = re.sub(r'^```(?:json)?\s*\n?', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\n?```\s*$', '', cleaned)
        return cleaned.strip()

    # ── Claude CLI provider ──────────────────────────────────────────

    def _claude_chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 4096,
        **kwargs
    ) -> str:
        """Send a chat request via the claude CLI."""
        system_prompt, user_prompt = self._flatten_messages(messages)

        cmd = [
            Config.CLAUDE_CLI_PATH,
            "-p",
            "--bare",
            "--output-format", "json",
        ]

        if system_prompt:
            cmd.extend(["--system-prompt", system_prompt])

        if self.model:
            cmd.extend(["--model", self.model])

        logger.debug("Claude CLI command: %s", " ".join(cmd))

        try:
            result = subprocess.run(
                cmd,
                input=user_prompt,
                capture_output=True,
                text=True,
                timeout=300,
            )
        except subprocess.TimeoutExpired:
            raise LLMError("Claude CLI timed out after 300 seconds")
        except FileNotFoundError:
            raise LLMError(
                f"Claude CLI not found at '{Config.CLAUDE_CLI_PATH}'. "
                "Install it or set CLAUDE_CLI_PATH."
            )

        if result.returncode != 0:
            stderr = result.stderr.strip() if result.stderr else "(no stderr)"
            raise LLMError(f"Claude CLI returned exit code {result.returncode}: {stderr}")

        stdout = result.stdout.strip()
        if not stdout:
            raise LLMError("Claude CLI returned empty output")

        # Parse JSON envelope
        try:
            envelope = json.loads(stdout)
        except json.JSONDecodeError:
            # If not valid JSON, treat raw stdout as the response text
            logger.warning("Claude CLI output is not JSON, using raw text")
            return self._clean_response(stdout)

        if isinstance(envelope, dict):
            if envelope.get("is_error"):
                raise LLMError(f"Claude CLI error: {envelope.get('result', 'unknown error')}")
            text = envelope.get("result", stdout)
        else:
            text = stdout

        return self._clean_response(str(text))

    # ── OpenAI SDK provider ──────────────────────────────────────────

    def _openai_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None
    ) -> str:
        """Send a chat request via the OpenAI SDK."""
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format

        response = self._openai_client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        return self._clean_response(content)

    # ── Ollama provider (uses OpenAI-compatible endpoint) ────────────

    def _ollama_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None
    ) -> str:
        """Send a chat request to Ollama via the OpenAI-compatible API."""
        return self._openai_chat(messages, temperature, max_tokens, response_format)

    # ── Public API ───────────────────────────────────────────────────

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None
    ) -> str:
        """
        Send a chat request.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            temperature: Temperature parameter (ignored for claude provider).
            max_tokens: Maximum tokens for the response.
            response_format: Response format hint (e.g. {"type": "json_object"}).

        Returns:
            Model response text.
        """
        if self.provider == "claude":
            return self._claude_chat(messages, max_tokens=max_tokens)
        elif self.provider == "ollama":
            return self._ollama_chat(messages, temperature, max_tokens, response_format)
        else:
            return self._openai_chat(messages, temperature, max_tokens, response_format)

    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096
    ) -> Dict[str, Any]:
        """
        Send a chat request and return parsed JSON.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            temperature: Temperature parameter (ignored for claude provider).
            max_tokens: Maximum tokens for the response.

        Returns:
            Parsed JSON object.
        """
        if self.provider == "claude":
            # For claude, append JSON instruction to the last user message
            messages = [m.copy() for m in messages]
            for i in range(len(messages) - 1, -1, -1):
                if messages[i].get("role") != "system":
                    messages[i]["content"] += (
                        "\n\nRespond with valid JSON only, no markdown code fences."
                    )
                    break
            response = self._claude_chat(messages, max_tokens=max_tokens)
        else:
            response = self.chat(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"}
            )

        cleaned = self._clean_json_response(response)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            raise LLMError(f"Invalid JSON returned by LLM: {cleaned[:500]}")

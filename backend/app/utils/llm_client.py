"""
LLM client wrapper.
Supports five providers: openai, anthropic, github-copilot, ollama, claude (CLI).
"""

import json
import re
import subprocess
from typing import Optional, Dict, Any, List, Tuple

from ..config import Config
from .logger import get_logger

logger = get_logger('mirofish.llm_client')


# ── Token estimation (no tiktoken dependency) ────────────────────────────────

def estimate_tokens(text: str) -> int:
    """
    Estimate token count without tiktoken.

    Rules:
    - CJK characters: ~1.5 tokens each (UTF-8 Han chars are typically 1-2 tokens)
    - ASCII words: ~1.3 tokens each
    - +10% safety buffer
    """
    if not text:
        return 0
    cjk_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    rest = ''.join(c if c < '\u4e00' or c > '\u9fff' else ' ' for c in text)
    ascii_words = len(rest.split())
    return int((cjk_chars * 1.5 + ascii_words * 1.3) * 1.1)


def estimate_messages_tokens(messages: List[Dict]) -> int:
    """Estimate total token count for a message list."""
    total = 0
    for msg in messages:
        content = msg.get("content") or ""
        if isinstance(content, list):
            content = " ".join(
                c.get("text", "") for c in content if isinstance(c, dict)
            )
        total += estimate_tokens(content) + 4  # role + per-message overhead
    return total + 2  # conversation overhead


# ── Exceptions ───────────────────────────────────────────────────────────────

class LLMError(ValueError):
    """LLM call error. Extends ValueError for backward compatibility."""
    pass


# ── Main client ──────────────────────────────────────────────────────────────

class LLMClient:
    """
    Unified LLM client. Provider is resolved at construction time.

    Supported providers (set LLM_PROVIDER in .env):
      openai        — Any OpenAI-compatible API (OpenAI, Qwen, DeepSeek, etc.)
      anthropic     — Anthropic Claude SDK (direct API)
      github-copilot — GitHub Copilot subscription via token exchange
      ollama        — Local Ollama via OpenAI-compatible endpoint
      claude        — Claude CLI subprocess (claude -p)
      auto (default)— Auto-detect from model name and environment
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
    ):
        self.model = model or Config.LLM_MODEL_NAME
        self.provider = (provider or Config.get_resolved_provider()).lower()

        if self.provider == 'github-copilot':
            self._init_copilot(base_url)
        elif self.provider == 'anthropic':
            self._init_anthropic(api_key)
        elif self.provider == 'ollama':
            self._init_ollama(base_url)
        elif self.provider == 'claude':
            self._init_claude_cli()
        else:
            self._init_openai(api_key, base_url)

    # ── Initializers ─────────────────────────────────────────────────────────

    def _init_openai(self, api_key: Optional[str], base_url: Optional[str]):
        from openai import OpenAI
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        if not self.api_key:
            raise LLMError(
                "LLM_API_KEY is not configured. "
                "Set it in .env or choose a different LLM_PROVIDER."
            )
        self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def _init_anthropic(self, api_key: Optional[str]):
        from anthropic import Anthropic
        self.api_key = api_key or Config.LLM_API_KEY
        if not self.api_key:
            raise LLMError(
                "LLM_API_KEY is not configured for Anthropic provider. "
                "Get a key at https://console.anthropic.com/settings/keys"
            )
        self._client = Anthropic(api_key=self.api_key)

    def _init_copilot(self, base_url: Optional[str]):
        from openai import OpenAI
        from .copilot_auth import (
            get_copilot_token_manager,
            COPILOT_REQUEST_HEADERS,
        )
        self._copilot_mgr = get_copilot_token_manager()
        self.api_key = self._copilot_mgr.get_api_key()
        self.base_url = base_url or self._copilot_mgr.get_base_url()
        self._copilot_headers = {
            "Editor-Version": COPILOT_REQUEST_HEADERS["Editor-Version"],
            "User-Agent": COPILOT_REQUEST_HEADERS["User-Agent"],
            "X-Github-Api-Version": COPILOT_REQUEST_HEADERS["X-Github-Api-Version"],
        }
        self._client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            default_headers=self._copilot_headers,
        )

    def _init_ollama(self, base_url: Optional[str]):
        from openai import OpenAI
        self.api_key = "ollama"  # Ollama doesn't require auth
        self.base_url = base_url or Config.LLM_BASE_URL or "http://localhost:11434/v1"
        self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def _init_claude_cli(self):
        self.api_key = None
        self.base_url = None
        self._client = None  # no SDK client needed

    # ── Internal helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _clean(content: str) -> str:
        """Remove <think> tags and strip whitespace."""
        return re.sub(r'<think>[\s\S]*?</think>', '', content).strip()

    @staticmethod
    def _clean_json(content: str) -> str:
        """Strip markdown code fences from a JSON response."""
        s = content.strip()
        s = re.sub(r'^```(?:json)?\s*\n?', '', s, flags=re.IGNORECASE)
        s = re.sub(r'\n?```\s*$', '', s)
        return s.strip()

    def _extract_system(
        self, messages: List[Dict[str, str]]
    ) -> Tuple[Optional[str], List[Dict[str, str]]]:
        """Split system messages from the rest (needed for Anthropic API)."""
        system_parts, rest = [], []
        for m in messages:
            if m.get("role") == "system":
                system_parts.append(m["content"])
            else:
                rest.append(m)
        return ("\n\n".join(system_parts) if system_parts else None), rest

    def _flatten_messages(
        self, messages: List[Dict[str, str]]
    ) -> Tuple[str, str]:
        """Flatten multi-turn messages into (system_prompt, user_prompt) strings for Claude CLI."""
        system_parts, convo_parts = [], []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "system":
                system_parts.append(content)
            elif role == "assistant":
                convo_parts.append(f"[Assistant]\n{content}")
            else:
                convo_parts.append(f"[User]\n{content}")
        return "\n\n".join(system_parts), "\n\n".join(convo_parts)

    def _refresh_copilot_client(self):
        """Refresh the Copilot token if expired and rebuild the OpenAI client."""
        from openai import OpenAI
        new_key = self._copilot_mgr.get_api_key()
        if new_key != self.api_key:
            self.api_key = new_key
            self.base_url = self._copilot_mgr.get_base_url()
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                default_headers=self._copilot_headers,
            )

    # ── Provider-specific call implementations ───────────────────────────────

    def _call_openai_sdk(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: Optional[int],
        response_format: Optional[Dict] = None,
    ) -> str:
        """Shared call path for openai / ollama / github-copilot."""
        if self.provider == 'github-copilot':
            self._refresh_copilot_client()

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        if response_format:
            kwargs["response_format"] = response_format

        response = self._client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    def _call_openai_sdk_with_finish(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: Optional[int],
        response_format: Optional[Dict] = None,
    ) -> Tuple[str, str]:
        if self.provider == 'github-copilot':
            self._refresh_copilot_client()

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        if response_format:
            kwargs["response_format"] = response_format

        response = self._client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        return choice.message.content, (choice.finish_reason or 'stop')

    def _call_anthropic_sdk(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        json_mode: bool = False,
    ) -> str:
        system_text, user_messages = self._extract_system(messages)
        if json_mode:
            suffix = "\n\nIMPORTANT: Respond with valid JSON only — no markdown, no explanation."
            system_text = (system_text + suffix) if system_text else suffix.strip()

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": user_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system_text:
            kwargs["system"] = system_text

        response = self._client.messages.create(**kwargs)
        return response.content[0].text

    def _call_anthropic_sdk_with_finish(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        json_mode: bool = False,
    ) -> Tuple[str, str]:
        content = self._call_anthropic_sdk(messages, temperature, max_tokens, json_mode)
        # Anthropic stop_reason: 'end_turn' → 'stop', 'max_tokens' → 'length'
        return content, 'stop'  # finish reason from _call_anthropic_sdk always ends normally

    def _call_claude_cli(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 4096,
    ) -> str:
        system_prompt, user_prompt = self._flatten_messages(messages)

        cmd = [
            Config.CLAUDE_CLI_PATH,
            "-p", "--bare",
            "--output-format", "json",
        ]
        if system_prompt:
            cmd.extend(["--system-prompt", system_prompt])
        if self.model:
            cmd.extend(["--model", self.model])

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
                "Install claude CLI or set CLAUDE_CLI_PATH in .env."
            )

        if result.returncode != 0:
            stderr = (result.stderr or "").strip() or "(no stderr)"
            raise LLMError(f"Claude CLI exit code {result.returncode}: {stderr}")

        stdout = result.stdout.strip()
        if not stdout:
            raise LLMError("Claude CLI returned empty output")

        try:
            envelope = json.loads(stdout)
            if isinstance(envelope, dict):
                if envelope.get("is_error"):
                    raise LLMError(f"Claude CLI error: {envelope.get('result', 'unknown')}")
                return str(envelope.get("result", stdout))
        except json.JSONDecodeError:
            pass

        return stdout

    # ── Public API ────────────────────────────────────────────────────────────

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None,
    ) -> str:
        """
        Send a chat request and return the response text.

        Args:
            messages: Message list (OpenAI format — system/user/assistant roles)
            temperature: Sampling temperature
            max_tokens: Maximum output tokens
            response_format: {"type": "json_object"} for JSON mode (OpenAI providers).
                             Anthropic and Claude CLI adapt automatically.

        Returns:
            Model response as a string.
        """
        json_mode = bool(response_format and response_format.get("type") == "json_object")

        if self.provider == 'anthropic':
            content = self._call_anthropic_sdk(messages, temperature, max_tokens, json_mode)
        elif self.provider == 'claude':
            content = self._call_claude_cli(messages, max_tokens)
        else:
            content = self._call_openai_sdk(messages, temperature, max_tokens, response_format)

        return self._clean(content)

    def chat_with_finish_reason(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict] = None,
    ) -> Tuple[str, str]:
        """
        Like chat(), but also returns the finish reason.

        finish_reason values (normalised to OpenAI format):
          'stop'   — completed normally
          'length' — truncated at max_tokens

        Returns:
            (response_text, finish_reason)
        """
        json_mode = bool(response_format and response_format.get("type") == "json_object")
        effective_max = max_tokens or 4096

        if self.provider == 'anthropic':
            system_text, user_messages = self._extract_system(messages)
            if json_mode:
                suffix = "\n\nIMPORTANT: Respond with valid JSON only — no markdown, no explanation."
                system_text = (system_text + suffix) if system_text else suffix.strip()

            kwargs: Dict[str, Any] = {
                "model": self.model,
                "messages": user_messages,
                "temperature": temperature,
                "max_tokens": effective_max,
            }
            if system_text:
                kwargs["system"] = system_text

            response = self._client.messages.create(**kwargs)
            content = response.content[0].text
            stop_reason = getattr(response, 'stop_reason', 'end_turn')
            finish_reason = 'length' if stop_reason == 'max_tokens' else 'stop'
        elif self.provider == 'claude':
            content = self._call_claude_cli(messages, effective_max)
            finish_reason = 'stop'
        else:
            if self.provider == 'github-copilot':
                self._refresh_copilot_client()
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
            }
            if max_tokens is not None:
                kwargs["max_tokens"] = max_tokens
            if response_format:
                kwargs["response_format"] = response_format
            response = self._client.chat.completions.create(**kwargs)
            choice = response.choices[0]
            content = choice.message.content
            finish_reason = choice.finish_reason or 'stop'

        return self._clean(content), finish_reason

    def chat_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> Tuple[Optional[str], Optional[List[Dict[str, Any]]]]:
        """
        Send a chat request with native function/tool calling.

        Args:
            messages: Message list (supports role=tool messages for tool results)
            tools: Tool definitions in OpenAI format:
                   [{"type": "function", "function": {"name", "description", "parameters"}}]
            temperature: Sampling temperature
            max_tokens: Maximum output tokens

        Returns:
            (content, tool_calls)
            - content: Text content (None or thinking text when tool calls are present)
            - tool_calls: List of {"id", "name", "parameters"} dicts, or None if no calls
        """
        if self.provider == 'anthropic':
            return self._chat_with_tools_anthropic(messages, tools, temperature, max_tokens)
        elif self.provider == 'claude':
            # Claude CLI doesn't support native tool calling — fall back to text
            logger.warning("chat_with_tools not supported for claude CLI provider; falling back to text")
            content = self._call_claude_cli(messages, max_tokens)
            return self._clean(content), None
        else:
            return self._chat_with_tools_openai(messages, tools, temperature, max_tokens)

    def _chat_with_tools_openai(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        temperature: float,
        max_tokens: int,
    ) -> Tuple[Optional[str], Optional[List[Dict[str, Any]]]]:
        if self.provider == 'github-copilot':
            self._refresh_copilot_client()

        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=temperature,
            max_tokens=max_tokens,
        )
        message = response.choices[0].message
        content = self._clean(message.content or "")

        if not message.tool_calls:
            return content, None

        parsed = []
        for tc in message.tool_calls:
            try:
                params = json.loads(tc.function.arguments)
            except (json.JSONDecodeError, AttributeError):
                params = {}
            parsed.append({"id": tc.id, "name": tc.function.name, "parameters": params})
        return content, parsed

    def _chat_with_tools_anthropic(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        temperature: float,
        max_tokens: int,
    ) -> Tuple[Optional[str], Optional[List[Dict[str, Any]]]]:
        """Translate OpenAI tool format to Anthropic tool_use format."""
        system_text, user_messages = self._extract_system(messages)

        # Convert OpenAI tools → Anthropic tools
        anthropic_tools = []
        for t in tools:
            fn = t.get("function", {})
            anthropic_tools.append({
                "name": fn.get("name", ""),
                "description": fn.get("description", ""),
                "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
            })

        # Convert tool result messages (role=tool → role=user with tool_result content)
        converted = []
        for m in user_messages:
            if m.get("role") == "tool":
                converted.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": m.get("tool_call_id", ""),
                        "content": m.get("content", ""),
                    }],
                })
            else:
                converted.append(m)

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": converted,
            "tools": anthropic_tools,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system_text:
            kwargs["system"] = system_text

        response = self._client.messages.create(**kwargs)

        text_parts, tool_calls = [], []
        for block in response.content:
            if getattr(block, "type", None) == "text":
                text_parts.append(block.text)
            elif getattr(block, "type", None) == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "parameters": block.input or {},
                })

        content = self._clean(" ".join(text_parts)) or None
        return content, (tool_calls if tool_calls else None)

    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        """
        Send a chat request and parse the response as JSON.

        Returns:
            Parsed JSON dict.

        Raises:
            LLMError: If the response cannot be parsed as valid JSON.
        """
        if self.provider == 'claude':
            # Inject JSON instruction into the last non-system message
            msgs = [m.copy() for m in messages]
            for i in range(len(msgs) - 1, -1, -1):
                if msgs[i].get("role") != "system":
                    msgs[i]["content"] += "\n\nRespond with valid JSON only, no markdown code fences."
                    break
            raw = self._call_claude_cli(msgs, max_tokens)
        else:
            raw = self.chat(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )

        cleaned = self._clean_json(raw)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            raise LLMError(f"LLM returned invalid JSON: {cleaned[:500]}")

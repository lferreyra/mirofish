"""
LLM Client Wrapper
Supports OpenAI API, Anthropic API, Claude CLI, and Codex CLI
"""

import json
import re
import subprocess
import time
import threading
from datetime import datetime
from typing import Optional, Dict, Any, List

from ..config import Config
from .logger import get_logger

logger = get_logger('mirofish.llm_client')

try:
    from openai import RateLimitError as _OpenAIRateLimitError
except ImportError:
    _OpenAIRateLimitError = None

try:
    from anthropic import RateLimitError as _AnthropicRateLimitError
except ImportError:
    _AnthropicRateLimitError = None


class _TokenBucket:
    """Fixed-window per-minute rate limiter for RPM and TPM."""

    def __init__(self):
        self._lock = threading.Lock()
        self._rpm_count = 0
        self._tpm_count = 0
        self._window_start = time.time()

    def check_and_consume(self, token_count: int, rpm_limit: int, tpm_limit: int) -> float:
        """Check limits and consume quota. Returns seconds to sleep (0.0 if under limit)."""
        with self._lock:
            now = time.time()
            if now - self._window_start >= 60.0:
                self._rpm_count = 0
                self._tpm_count = 0
                self._window_start = now

            if rpm_limit > 0 and self._rpm_count >= rpm_limit:
                return max(0.0, 60.0 - (now - self._window_start))
            if tpm_limit > 0 and self._tpm_count + token_count > tpm_limit:
                return max(0.0, 60.0 - (now - self._window_start))

            self._rpm_count += 1
            self._tpm_count += token_count
            return 0.0


class LLMClient:
    """LLM Client - supports OpenAI, Anthropic, Claude CLI, and Codex CLI"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None
    ):
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        self.model = model or Config.LLM_MODEL_NAME
        self.provider = (provider or Config.LLM_PROVIDER or "").lower()

        # CLI providers don't need an API key
        if self.provider in ("claude-cli", "codex-cli"):
            self.client = None
        elif not self.api_key:
            raise ValueError("LLM_API_KEY not configured")

        # Auto-detect provider if not specified
        if not self.provider:
            self.provider = self._detect_provider()

        # Initialize the appropriate client
        if self.provider == "anthropic":
            try:
                from anthropic import Anthropic
            except ImportError:
                raise ImportError(
                    "anthropic package required for Claude support. "
                    "Install with: pip install anthropic"
                )
            self.client = Anthropic(api_key=self.api_key)
        elif self.provider in ("claude-cli", "codex-cli"):
            self.client = None  # CLI-based, no SDK client needed
        else:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )

        self._token_bucket = _TokenBucket()

    def _is_rate_limit_error(self, exc) -> bool:
        """Detect 429 / rate limit errors across all providers."""
        if _OpenAIRateLimitError and isinstance(exc, _OpenAIRateLimitError):
            return True
        if _AnthropicRateLimitError and isinstance(exc, _AnthropicRateLimitError):
            return True
        msg = str(exc).lower()
        return "429" in msg or "rate limit" in msg or "too many requests" in msg

    def _check_token_bucket(self, rate_limit_config: dict, max_tokens: int):
        """Proactive RPM/TPM enforcement. Sleeps if over limit."""
        rpm_limit = rate_limit_config.get("rpm_limit", 0)
        tpm_limit = rate_limit_config.get("tpm_limit", 0)
        if rpm_limit <= 0 and tpm_limit <= 0:
            return
        while True:
            sleep_for = self._token_bucket.check_and_consume(max_tokens, rpm_limit, tpm_limit)
            if sleep_for <= 0:
                return
            logger.warning(
                f"[{datetime.now().isoformat()}] TPM/RPM limit reached. "
                f"Sleeping {sleep_for:.1f}s until window resets."
            )
            time.sleep(sleep_for)

    def _detect_provider(self) -> str:
        """Auto-detect provider from base_url or model name"""
        model_lower = (self.model or "").lower()
        base_lower = (self.base_url or "").lower()

        if any(k in model_lower for k in ["claude", "anthropic"]):
            return "anthropic"
        if "anthropic" in base_lower:
            return "anthropic"

        return "openai"

    def _split_system_message(self, messages: List[Dict[str, str]]):
        """
        Split system message from conversation messages.
        Returns (system_text, conversation_messages)
        """
        system_text = None
        conversation = []

        for msg in messages:
            if msg.get("role") == "system":
                if system_text is None:
                    system_text = msg["content"]
                else:
                    system_text += "\n\n" + msg["content"]
            else:
                conversation.append(msg)

        return system_text, conversation

    def _clean_content(self, content: str) -> str:
        """Remove <think> tags from reasoning models"""
        content = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()
        return content

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None,
        rate_limit_config: Optional[Dict] = None
    ) -> str:
        """
        Send a chat request with optional rate limit control.

        Args:
            messages: Message list
            temperature: Temperature parameter
            max_tokens: Maximum tokens
            response_format: Response format (e.g., JSON mode)
            rate_limit_config: Optional dict with keys: max_retries, retry_base_delay_s,
                               rpm_limit, tpm_limit

        Returns:
            Model response text
        """
        cfg = rate_limit_config or {}
        max_retries = cfg.get("max_retries", 3)
        base_delay = cfg.get("retry_base_delay_s", 30)

        for attempt in range(max_retries + 1):
            try:
                self._check_token_bucket(cfg, max_tokens)
                if self.provider == "claude-cli":
                    return self._chat_claude_cli(messages, temperature, max_tokens, response_format)
                elif self.provider == "codex-cli":
                    return self._chat_codex_cli(messages, temperature, max_tokens, response_format)
                elif self.provider == "anthropic":
                    return self._chat_anthropic(messages, temperature, max_tokens, response_format)
                else:
                    return self._chat_openai(messages, temperature, max_tokens, response_format)
            except Exception as e:
                if attempt >= max_retries or not self._is_rate_limit_error(e):
                    raise
                wait = min(base_delay * (2 ** attempt), 300)
                logger.warning(
                    f"[{datetime.now().isoformat()}] Rate limit hit "
                    f"(attempt {attempt + 1}/{max_retries}). "
                    f"Retrying in {wait}s. Error: {e}"
                )
                time.sleep(wait)

    def _chat_openai(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        response_format: Optional[Dict]
    ) -> str:
        """Chat via OpenAI-compatible API"""
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
        return self._clean_content(content)

    def _chat_anthropic(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        response_format: Optional[Dict] = None
    ) -> str:
        """Chat via Anthropic API"""
        system_text, conversation = self._split_system_message(messages)

        if response_format and response_format.get("type") == "json_object":
            json_instruction = "\n\nIMPORTANT: You must respond with valid JSON only. No markdown, no explanation, just pure JSON."
            if system_text:
                system_text += json_instruction
            else:
                system_text = json_instruction.strip()

        kwargs = {
            "model": self.model,
            "messages": conversation,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if system_text:
            kwargs["system"] = system_text

        response = self.client.messages.create(**kwargs)
        content = response.content[0].text
        return self._clean_content(content)

    def _chat_claude_cli(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        response_format: Optional[Dict] = None
    ) -> str:
        """Chat via Claude Code CLI (uses your Claude subscription)"""
        system_text, conversation = self._split_system_message(messages)

        # Build the prompt from messages
        prompt_parts = []
        if system_text:
            prompt_parts.append(f"SYSTEM INSTRUCTIONS:\n{system_text}\n")

        if response_format and response_format.get("type") == "json_object":
            prompt_parts.append("IMPORTANT: Respond with valid JSON only. No markdown, no explanation, just pure JSON.\n")

        for msg in conversation:
            role = msg.get("role", "user").upper()
            prompt_parts.append(f"{role}: {msg['content']}")

        prompt = "\n\n".join(prompt_parts)

        try:
            result = subprocess.run(
                ["claude", "-p", "--output-format", "json", prompt],
                capture_output=True, text=True, timeout=120,
                cwd="/tmp"
            )

            if result.returncode != 0:
                logger.error(f"Claude CLI error: {result.stderr[:200]}")
                raise RuntimeError(f"Claude CLI failed: {result.stderr[:200]}")

            # Parse JSON output to extract the result text
            try:
                output = json.loads(result.stdout)
                content = output.get("result", result.stdout)
            except json.JSONDecodeError:
                content = result.stdout.strip()

            return self._clean_content(content)

        except subprocess.TimeoutExpired:
            raise RuntimeError("Claude CLI timed out after 120s")

    def _chat_codex_cli(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        response_format: Optional[Dict] = None
    ) -> str:
        """Chat via Codex CLI (uses your OpenAI subscription)"""
        system_text, conversation = self._split_system_message(messages)

        # Build the prompt
        prompt_parts = []
        if system_text:
            prompt_parts.append(f"SYSTEM INSTRUCTIONS:\n{system_text}\n")

        if response_format and response_format.get("type") == "json_object":
            prompt_parts.append("IMPORTANT: Respond with valid JSON only. No markdown, no explanation, just pure JSON.\n")

        for msg in conversation:
            role = msg.get("role", "user").upper()
            prompt_parts.append(f"{role}: {msg['content']}")

        prompt = "\n\n".join(prompt_parts)

        try:
            result = subprocess.run(
                ["codex", "exec", "--skip-git-repo-check", prompt],
                capture_output=True, text=True, timeout=180,
                cwd="/tmp"
            )

            if result.returncode != 0:
                logger.error(f"Codex CLI error: {result.stderr[:200]}")
                raise RuntimeError(f"Codex CLI failed: {result.stderr[:200]}")

            # Codex exec outputs headers + conversation. Extract the last assistant response.
            raw = result.stdout.strip()
            # Find content after the last "codex\n" marker (the assistant response)
            parts = raw.split("\ncodex\n")
            if len(parts) > 1:
                # Get the response, strip trailing token counts
                content = parts[-1].strip()
                # Remove trailing "tokens used\nN\n..." lines
                lines = content.split("\n")
                clean_lines = []
                for line in lines:
                    if line.strip() == "tokens used":
                        break
                    clean_lines.append(line)
                content = "\n".join(clean_lines).strip()
            else:
                content = raw
            return self._clean_content(content)

        except subprocess.TimeoutExpired:
            raise RuntimeError("Codex CLI timed out after 180s")

    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
        rate_limit_config: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Send a chat request and return JSON.

        Args:
            messages: Message list
            temperature: Temperature parameter
            max_tokens: Maximum tokens
            rate_limit_config: Optional dict with rate limit settings (passed to chat())

        Returns:
            Parsed JSON object
        """
        response = self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            rate_limit_config=rate_limit_config
        )
        # Clean markdown code block markers
        cleaned_response = response.strip()
        cleaned_response = re.sub(r'^```(?:json)?\s*\n?', '', cleaned_response, flags=re.IGNORECASE)
        cleaned_response = re.sub(r'\n?```\s*$', '', cleaned_response)
        cleaned_response = cleaned_response.strip()

        try:
            return json.loads(cleaned_response)
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON returned by LLM: {cleaned_response[:500]}")

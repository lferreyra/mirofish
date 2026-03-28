"""
LLM model wrapper that uses `claude -p` CLI for inference.

Replaces the CAMEL ModelFactory with a subprocess-based approach
using the Claude CLI tool.
"""

import asyncio
import json
import logging
import subprocess
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# Shared thread pool for running subprocess calls in async context
_executor = ThreadPoolExecutor(max_workers=32)


class ClaudeLLMModel:
    """
    LLM model that invokes `claude -p --output-format json` via subprocess.

    This replaces the CAMEL ModelFactory.create() pattern used by OASIS.
    """

    def __init__(self, model: str = "sonnet", timeout: int = 300):
        """
        Initialize the Claude CLI LLM model.

        Args:
            model: The Claude model to use (e.g. "sonnet", "haiku", "opus").
            timeout: Maximum seconds to wait for a response.
        """
        self.model = model
        self.timeout = timeout

    def _call_claude_sync(self, system_prompt: str, user_prompt: str) -> str:
        """
        Synchronous call to the claude CLI.

        Args:
            system_prompt: The system prompt (agent persona).
            user_prompt: The user prompt (observation + action request).

        Returns:
            The text response from Claude.
        """
        cmd = [
            "claude",
            "-p",
            "--output-format", "json",
            "--model", self.model,
            "--max-turns", "1",
        ]

        if system_prompt:
            cmd.extend(["--system", system_prompt])

        try:
            result = subprocess.run(
                cmd,
                input=user_prompt,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )

            if result.returncode != 0:
                stderr = result.stderr.strip()
                logger.error("claude CLI error (rc=%d): %s", result.returncode, stderr)
                return ""

            stdout = result.stdout.strip()
            if not stdout:
                return ""

            # The --output-format json returns a JSON object with a "result" field
            try:
                parsed = json.loads(stdout)
                # Handle the JSON output format from claude CLI
                if isinstance(parsed, dict):
                    # Try common fields
                    if "result" in parsed:
                        return str(parsed["result"])
                    if "content" in parsed:
                        return str(parsed["content"])
                    if "text" in parsed:
                        return str(parsed["text"])
                    # Fall back to the full JSON string
                    return stdout
                return stdout
            except json.JSONDecodeError:
                # If not JSON, return raw output
                return stdout

        except subprocess.TimeoutExpired:
            logger.error("claude CLI timed out after %ds", self.timeout)
            return ""
        except FileNotFoundError:
            logger.error(
                "claude CLI not found. Install it with: npm install -g @anthropic-ai/claude-code"
            )
            return ""
        except Exception as e:
            logger.error("claude CLI unexpected error: %s", e)
            return ""

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        """
        Async wrapper around the synchronous claude CLI call.

        Uses a thread pool executor so the event loop is not blocked.

        Args:
            system_prompt: The system prompt (agent persona).
            user_prompt: The user prompt (observation + action request).

        Returns:
            The text response from Claude.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor,
            self._call_claude_sync,
            system_prompt,
            user_prompt,
        )

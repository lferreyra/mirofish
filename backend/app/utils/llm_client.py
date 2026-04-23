"""
LLM client — thin shim over `app.llm.ModelRouter`.

This used to wrap `openai.OpenAI` directly. It now delegates to the router so
every call flows through role-based routing, retry, fallback, and accounting.
The public surface (`chat`, `chat_json`) is unchanged so existing callers
continue to work without modification.

New method:
    chat_raw(...) -> LLMResponse   # exposes token counts / finish_reason

Role selection:
    The default role is `balanced`, matching the original single-endpoint
    behavior. Callers that want a different role (e.g. `fast` for NER,
    `heavy` for report synthesis) pass it explicitly.
"""

import json
import re
from typing import Any, Dict, List, Optional

from ..llm import ModelRouter, Role
from ..llm.base import LLMResponse


class LLMClient:
    """Backwards-compatible client façade. Delegates to ModelRouter."""

    def __init__(
        self,
        api_key: Optional[str] = None,        # accepted for back-compat; ignored
        base_url: Optional[str] = None,       # same
        model: Optional[str] = None,          # same
        *,
        role: Role | str = Role.BALANCED,
        router: Optional[ModelRouter] = None,
    ):
        self._role = Role(role) if isinstance(role, str) else role
        self._router = router or ModelRouter.default()
        # Expose legacy attrs for callers that read them (report_agent reads `.model`)
        backend = self._router.get(self._role)
        self.api_key = api_key or backend.config.api_key
        self.base_url = base_url or backend.config.base_url
        self.model = model or backend.model

    # ------------------------------------------------------------------ API
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None,
        *,
        role: Role | str | None = None,
        cache_key: Optional[str] = None,
    ) -> str:
        """Send chat request; return the stripped text content.

        Behavior preserved from the original: strips `<think>...</think>`
        reasoning blocks (the openai_compat backend already does this,
        we keep the call here for safety).
        """
        response = self.chat_raw(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
            role=role,
            cache_key=cache_key,
        )
        return re.sub(r"<think>[\s\S]*?</think>", "", response.text).strip()

    def chat_raw(
        self,
        messages: List[Dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None,
        role: Role | str | None = None,
        cache_key: Optional[str] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Return the full LLMResponse — use when you need token counts or
        `finish_reason` (e.g. to detect truncation)."""
        resolved_role = self._role if role is None else (Role(role) if isinstance(role, str) else role)
        return self._router.chat(
            resolved_role,
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
            cache_key=cache_key,
            **kwargs,
        )

    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
        *,
        role: Role | str | None = None,
        cache_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Request JSON mode; parse the response as JSON."""
        response = self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            role=role,
            cache_key=cache_key,
        )
        # Strip markdown code fences that some models still emit even in JSON mode.
        cleaned = response.strip()
        cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            raise ValueError(f"LLM返回的JSON格式无效: {cleaned}")

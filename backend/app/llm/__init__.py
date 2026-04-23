"""
Pluggable LLM backends and role-based routing.

Public surface:
    from app.llm import ModelRouter, LLMBackend, LLMResponse
    router = ModelRouter.default()
    response = router.chat(role="fast", messages=[...])
"""

from .base import LLMBackend, LLMResponse, EmbeddingResponse, Role, BackendError
from .router import ModelRouter

__all__ = [
    "LLMBackend",
    "LLMResponse",
    "EmbeddingResponse",
    "Role",
    "BackendError",
    "ModelRouter",
]

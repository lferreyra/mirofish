"""
Deterministic mock LLM router + embedder for the eval harness.

In live runs, the MemoryManager, PersonaGenerator, reflection scheduler, and
contradiction detector all talk to `ModelRouter.default()`. For CI we want:

  * NO network
  * bit-identical output given the same seed + inputs

`MockRouter` satisfies both. It hashes each prompt (system + user + cache_key)
into a stable reply drawn from a small table, and emits deterministic
embeddings from the same hash. Importance scoring returns a hash-derived
integer 1-10; persona-generation JSON is synthesized from the entity name.

The returned texts are obviously not real — that's the point. The eval
harness doesn't grade on language quality; it grades on whether the Phase-2
/ Phase-4 pipeline produces a reproducible verdict.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, List

from app.llm.base import EmbeddingResponse, LLMResponse


def _h(text: str, *, salt: str = "") -> int:
    """Stable 32-bit hash of text + salt. Used for all deterministic picks."""
    digest = hashlib.sha256((salt + "::" + text).encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big")


class MockRouter:
    """Drop-in replacement for `app.llm.ModelRouter`. Deterministic given
    the seed passed at construction time."""

    def __init__(self, *, seed: int = 0):
        self._seed = seed
        self.calls: List[Dict[str, Any]] = []

    # ---- chat --------------------------------------------------------------
    def chat(self, role, messages, **kwargs):
        cache_key = kwargs.get("cache_key") or ""
        response_format = kwargs.get("response_format") or {}
        joined = "\n".join(m.get("content", "") for m in messages)
        text = self._dispatch(str(getattr(role, "value", role)), cache_key, joined, response_format)
        self.calls.append({
            "role": str(getattr(role, "value", role)),
            "cache_key": cache_key,
            "len": len(joined),
        })
        return LLMResponse(text=text, model="mock", backend="mock", latency_ms=0.0)

    def stream_chat(self, role, messages, **kwargs):
        response = self.chat(role, messages, **kwargs)
        # Stream by whitespace so callers can still exercise the streaming path
        for chunk in re.split(r"(\s+)", response.text):
            if chunk:
                yield chunk

    def embed(self, texts, **kwargs):
        vectors: List[List[float]] = []
        for t in texts:
            # 8-dim deterministic embedding from the sha256 digest.
            digest = hashlib.sha256((str(self._seed) + "::emb::" + t).encode("utf-8")).digest()
            vec = [((digest[i] / 255.0) * 2.0 - 1.0) for i in range(8)]
            vectors.append(vec)
        return EmbeddingResponse(vectors=vectors, model="mock-emb", backend="mock")

    # ---- dispatch ----------------------------------------------------------
    def _dispatch(self, role: str, cache_key: str, text: str, response_format: dict) -> str:
        wants_json = response_format.get("type") == "json_object"

        # Importance scoring -> integer 1..10
        if cache_key == "memory.importance":
            return str(1 + (_h(text, salt=str(self._seed)) % 10))

        # Contradiction -> binary JSON
        if cache_key == "memory.contradiction":
            # Return contradicts=True ~25% of the time, deterministically.
            hit = (_h(text, salt=str(self._seed)) % 4) == 0
            return json.dumps({"contradicts": hit, "reason": "mock"})

        # Reflection -> 3 canned beliefs with source refs
        if cache_key == "memory.reflection":
            beliefs = [
                "I now believe the topic is more divisive than I thought.",
                "I've noticed a shift in community sentiment.",
                "I remain cautious about strong conclusions.",
            ]
            return json.dumps({"beliefs": beliefs})

        # Persona generation -> structured JSON
        if cache_key == "personas.generate":
            return self._persona_json(text)

        # Interview-like / everything else -> short canned reply
        if wants_json:
            return json.dumps({"direction": "neutral", "magnitude": 0.0, "confidence": 0.0})
        return "mock reply"

    def _persona_json(self, prompt_text: str) -> str:
        """Derive a persona from the prompt text deterministically."""
        h = _h(prompt_text, salt=str(self._seed))
        # Spread traits across [0.2, 0.9] using different byte slices.
        def _f(bucket: int) -> float:
            return 0.2 + ((h >> (bucket * 4)) & 0xF) / 15.0 * 0.7
        # Valence: +1/0/-1 depending on whether the entity name is in the
        # "supportive" or "opposing" bucket — gives a realistic mix.
        sign_choice = h % 3
        valence = [0.6, 0.0, -0.6][sign_choice]
        label = ["supportive", "neutral", "opposing"][sign_choice]
        # Credibility mildly correlated with archetype hint in the prompt.
        if "expert" in prompt_text.lower() or "media" in prompt_text.lower():
            credibility = 0.8
        else:
            credibility = 0.35 + _f(0) * 0.2
        return json.dumps({
            "big_five": {
                "openness": _f(1), "conscientiousness": _f(2),
                "extraversion": _f(3), "agreeableness": _f(4),
                "neuroticism": _f(5),
            },
            "conviction": 0.3 + _f(6) * 0.6,
            "credibility": credibility,
            "background": f"Mock persona seeded with hash {h:08x}"[:200],
            "initial_stance": {"label": label, "valence": valence},
        })

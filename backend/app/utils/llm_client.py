"""
LLM客户端封装
统一使用OpenAI格式调用
支持多Key智能轮换 - Groq 4 keys + Gemini 3 keys

Key rotation strategy:
- TPD (tokens per day) error  → mark key exhausted 24h, rotate to next
- TPM (tokens per minute) error → wait 61s, retry SAME key (don't waste other keys)
- 413 / too large              → truncate messages, retry same key
- Unknown error                → raise immediately
"""

import json
import re
import time
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from openai import OpenAI

from ..config import Config

logger = logging.getLogger(__name__)


class LLMClient:
    """
    LLM客户端 - 支持多Key智能轮换

    Rotation logic:
        - TPD exhausted  → skip key for 24 h, move to next available
        - TPM exceeded   → sleep 61 s, retry same key
        - Request too large → truncate, retry same key
        - Other errors   → re-raise immediately
    """

    # ------------------------------------------------------------------ #
    #  Construction                                                        #
    # ------------------------------------------------------------------ #

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.base_url = base_url or Config.LLM_BASE_URL
        self.model    = model    or Config.LLM_MODEL_NAME

        self.key_pool: List[str] = [api_key] if api_key else Config.get_primary_keys()
        if not self.key_pool:
            raise ValueError("No primary LLM API key configured (LLM_API_KEY_1 missing).")

        self.current_key_index: int = 0
        # Maps key index → datetime when the TPD ban expires
        self.exhausted_until: Dict[int, datetime] = {}

        self.client = self._make_client(self.key_pool[0])
        logger.info("LLMClient initialised with %d key(s), model=%s", len(self.key_pool), self.model)

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                    #
    # ------------------------------------------------------------------ #

    def _make_client(self, api_key: str) -> OpenAI:
        return OpenAI(api_key=api_key, base_url=self.base_url)

    # ---------- error classification ----------

    @staticmethod
    def _is_tpd_error(error: Exception) -> bool:
        """Tokens-per-DAY limit → key is done for 24 h."""
        msg = str(error).lower()
        return "tokens per day" in msg or "tpd" in msg

    @staticmethod
    def _is_tpm_error(error: Exception) -> bool:
        """Tokens-per-MINUTE limit → wait ~60 s on the SAME key."""
        msg = str(error).lower()
        return (
            "tokens per minute" in msg
            or "tpm" in msg
            or (("429" in msg or "rate_limit" in msg or "rate limit" in msg)
                and "tokens per day" not in msg)
        )

    @staticmethod
    def _is_too_large_error(error: Exception) -> bool:
        msg = str(error)
        return (
            "413" in msg
            or "Request too large" in msg
            or "reduce your message size" in msg
            or "context_length_exceeded" in msg
        )

    # ---------- key rotation ----------

    def _available_key_index(self) -> Optional[int]:
        """
        Return the index of the next key that is NOT TPD-exhausted,
        cycling through the whole pool starting after current_key_index.
        Cleans up expired bans along the way.
        Returns None if every key is still banned.
        """
        now = datetime.now()
        # Expire old bans
        self.exhausted_until = {k: v for k, v in self.exhausted_until.items() if now < v}

        total = len(self.key_pool)
        for offset in range(1, total + 1):
            idx = (self.current_key_index + offset) % total
            if idx not in self.exhausted_until:
                return idx
        return None

    def _rotate_key(self, *, tpd_exhausted: bool = False) -> bool:
        """
        Switch to the next usable key.
        If tpd_exhausted=True, marks the current key for 24 h first.
        Returns True if a new key is available, False if all are exhausted.
        """
        if tpd_exhausted:
            self.exhausted_until[self.current_key_index] = datetime.now() + timedelta(hours=24)
            logger.warning(
                "🚫 Primary key %d/%d marked TPD-exhausted for 24 h",
                self.current_key_index + 1, len(self.key_pool),
            )

        next_idx = self._available_key_index()
        if next_idx is None:
            logger.error("❌ All primary LLM keys are exhausted.")
            return False

        self.current_key_index = next_idx
        self.client = self._make_client(self.key_pool[next_idx])
        logger.info(
            "🔄 Rotated to primary key %d/%d",
            next_idx + 1, len(self.key_pool),
        )
        return True

    # ---------- message truncation ----------

    @staticmethod
    def _truncate_messages(
        messages: List[Dict[str, str]],
        target_tokens: int = 8_000,
    ) -> List[Dict[str, str]]:
        """
        Naively truncate user-role message content so the request fits.
        System messages are always kept intact.
        Rough heuristic: 1 token ≈ 4 chars.
        """
        char_limit = target_tokens * 4
        truncated = []
        for msg in messages:
            role    = msg.get("role", "")
            content = msg.get("content", "")
            if role == "system":
                truncated.append(msg)
            elif role == "user" and len(content) > char_limit:
                new_content = content[:char_limit] + "\n\n[Content truncated to fit token limit]"
                logger.warning(
                    "✂️  Truncated user message %d → %d chars", len(content), len(new_content)
                )
                truncated.append({"role": role, "content": new_content})
            else:
                truncated.append(msg)
        return truncated

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 8_096,
        response_format: Optional[Dict] = None,
    ) -> str:
        """
        Send a chat completion request.
        Automatically handles key rotation on rate-limit errors.
        Returns the assistant message as a plain string.
        """
        kwargs: Dict[str, Any] = {
            "model":       self.model,
            "messages":    messages,
            "temperature": temperature,
            "max_tokens":  max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format

        last_error: Optional[Exception] = None
        # Upper bound: try each key at most once for TPD; TPM retries don't
        # consume a "slot" because we wait on the same key.
        max_key_switches = len(self.key_pool)
        key_switches = 0

        while key_switches <= max_key_switches:
            try:
                response = self.client.chat.completions.create(**kwargs)
                content  = response.choices[0].message.content or ""
                # Strip chain-of-thought blocks some models return
                content  = re.sub(r"<think>[\s\S]*?</think>", "", content).strip()
                # Log which key succeeded
                logger.debug("✅ Request succeeded on key %d", self.current_key_index + 1)
                return content

            except Exception as e:
                last_error = e
                err_str    = str(e)

                if self._is_tpd_error(e):
                    logger.warning(
                        "⚠️  Key %d/%d hit TPD limit. Rotating… (%s)",
                        self.current_key_index + 1, len(self.key_pool), err_str[:120],
                    )
                    if not self._rotate_key(tpd_exhausted=True):
                        break          # all keys dead → exit loop
                    key_switches += 1

                elif self._is_too_large_error(e):
                    logger.warning(
                        "📦 Request too large (%s). Truncating messages…", err_str[:80]
                    )
                    messages          = self._truncate_messages(messages, target_tokens=8_000)
                    kwargs["messages"] = messages
                    # Do NOT rotate or increment counter

                elif self._is_tpm_error(e):
                    logger.warning(
                        "⏳ Key %d/%d hit TPM limit. Sleeping 61 s then retrying same key… (%s)",
                        self.current_key_index + 1, len(self.key_pool), err_str[:120],
                    )
                    time.sleep(61)
                    # Do NOT increment key_switches — we're retrying the same key

                else:
                    # Unexpected error — surface it immediately
                    raise

        raise RuntimeError(
            f"❌ All primary LLM keys exhausted. Last error: {last_error}"
        )

    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 8_096,
    ) -> Dict[str, Any]:
        """
        Like chat(), but parses the response as JSON.
        Falls back to plain chat if the model doesn't support response_format.
        """
        try:
            raw = self.chat(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
        except Exception:
            # Model may not support response_format → retry without it
            raw = self.chat(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        # Strip markdown fences if present
        cleaned = raw.strip()
        cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\n?```\s*$",          "", cleaned)
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            repaired = self._repair_truncated_json(cleaned)
            if repaired is not None:
                return repaired
            raise ValueError(f"LLM returned invalid JSON: {cleaned[:500]}")

    # ------------------------------------------------------------------ #
    #  Status / diagnostics                                                #
    # ------------------------------------------------------------------ #

    def status(self) -> Dict[str, Any]:
        """Return a human-readable snapshot of the key pool state."""
        now = datetime.now()
        keys_info = []
        for i, key in enumerate(self.key_pool):
            ban_until = self.exhausted_until.get(i)
            if ban_until and now < ban_until:
                remaining = int((ban_until - now).total_seconds() / 60)
                state = f"TPD-exhausted (~{remaining} min remaining)"
            else:
                state = "available"
            keys_info.append({
                "index":    i + 1,
                "key_tail": f"…{key[-6:]}",
                "state":    state,
                "active":   i == self.current_key_index,
            })
        return {
            "model":         self.model,
            "total_keys":    len(self.key_pool),
            "current_index": self.current_key_index + 1,
            "keys":          keys_info,
        }

    # ------------------------------------------------------------------ #
    #  JSON repair                                                         #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _repair_truncated_json(text: str) -> Optional[dict]:
        """Best-effort repair of truncated JSON by closing open brackets."""
        try:
            open_braces   = text.count("{") - text.count("}")
            open_brackets = text.count("[") - text.count("]")
            repaired = text
            if repaired.count('"') % 2 != 0:
                repaired += '"'
            repaired += "]" * open_brackets
            repaired += "}" * open_braces
            return json.loads(repaired)
        except Exception:
            return None


# ======================================================================= #
#  Boost (Gemini) client                                                   #
# ======================================================================= #

class BoostLLMClient(LLMClient):
    """
    Gemini LLM client with identical rotation logic.
    Uses the boost key pool from Config.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        # Bypass parent __init__ entirely and set attributes directly
        self.base_url = base_url or Config.LLM_BOOST_BASE_URL
        self.model    = model    or Config.LLM_BOOST_MODEL_NAME

        self.key_pool: List[str] = [api_key] if api_key else Config.get_boost_keys()
        if not self.key_pool:
            raise ValueError("No boost LLM API key configured (LLM_BOOST_API_KEY_1 missing).")

        self.current_key_index: int = 0
        self.exhausted_until:   Dict[int, datetime] = {}

        self.client = self._make_client(self.key_pool[0])
        logger.info(
            "BoostLLMClient initialised with %d key(s), model=%s",
            len(self.key_pool), self.model,
        )

    def _rotate_key(self, *, tpd_exhausted: bool = False) -> bool:
        if tpd_exhausted:
            self.exhausted_until[self.current_key_index] = datetime.now() + timedelta(hours=24)
            logger.warning(
                "🚫 Boost key %d/%d marked TPD-exhausted for 24 h",
                self.current_key_index + 1, len(self.key_pool),
            )

        next_idx = self._available_key_index()
        if next_idx is None:
            logger.error("❌ All boost (Gemini) LLM keys are exhausted.")
            return False

        self.current_key_index = next_idx
        self.client = self._make_client(self.key_pool[next_idx])
        logger.info(
            "🔄 Rotated to boost key %d/%d",
            next_idx + 1, len(self.key_pool),
        )
        return True
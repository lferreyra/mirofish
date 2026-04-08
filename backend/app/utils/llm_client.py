"""
LLM
OpenAI

AUGUR Enhancement: Rate limit handling com backoff exponencial,
sleep inteligente e abort após timeout configurável.
"""

import json
import re
import time
import logging
from typing import Optional, Dict, Any, List
from openai import OpenAI, RateLimitError, APIStatusError

from ..config import Config

logger = logging.getLogger(__name__)

# ─── Configuração de retry ─────────────────────────────────────
RATE_LIMIT_MAX_RETRIES    = 8       # tentativas máximas por chamada
RATE_LIMIT_BASE_SLEEP     = 5.0     # sleep inicial em segundos
RATE_LIMIT_MAX_SLEEP      = 120.0   # sleep máximo (2 minutos)
RATE_LIMIT_BACKOFF_FACTOR = 2.0     # fator exponencial
CONTEXT_MAX_RETRIES       = 2       # tentativas para context_length_exceeded


class LLMClient:
    """LLM com rate limit handling robusto"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.api_key  = api_key  or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        self.model    = model    or Config.LLM_MODEL_NAME

        if not self.api_key:
            raise ValueError("LLM_API_KEY Configuração")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

    # ─── Método principal com retry ───────────────────────────
    def _call_with_retry(self, kwargs: dict) -> str:
        """
        Executa a chamada à OpenAI com:
        - Retry automático em rate limit (429) com backoff exponencial
        - Sleep progressivo para não agravar o rate limit
        - Abort após RATE_LIMIT_MAX_RETRIES tentativas
        - Handling de context_length_exceeded (trunca e retenta)
        """
        sleep_time = RATE_LIMIT_BASE_SLEEP
        messages   = kwargs.get("messages", [])

        for attempt in range(1, RATE_LIMIT_MAX_RETRIES + 1):
            try:
                response = self.client.chat.completions.create(**kwargs)
                content  = response.choices[0].message.content
                # Remove thinking tags de alguns modelos
                content  = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()

                # Sleep mínimo entre chamadas para evitar burst
                time.sleep(0.3)
                return content

            except RateLimitError as e:
                if attempt >= RATE_LIMIT_MAX_RETRIES:
                    logger.error(
                        f"[LLMClient] Rate limit esgotado após {RATE_LIMIT_MAX_RETRIES} tentativas. "
                        f"Abortando chamada. Erro: {e}"
                    )
                    raise RuntimeError(
                        f"Rate limit da OpenAI esgotado após {RATE_LIMIT_MAX_RETRIES} tentativas. "
                        f"Aguarde alguns minutos e tente novamente."
                    ) from e

                actual_sleep = min(sleep_time, RATE_LIMIT_MAX_SLEEP)
                logger.warning(
                    f"[LLMClient] Rate limit (429) — tentativa {attempt}/{RATE_LIMIT_MAX_RETRIES}. "
                    f"Aguardando {actual_sleep:.1f}s antes de retomar..."
                )
                time.sleep(actual_sleep)
                sleep_time *= RATE_LIMIT_BACKOFF_FACTOR

            except APIStatusError as e:
                # Context length exceeded — tentar truncar e retentar
                if e.status_code == 400 and 'context_length_exceeded' in str(e):
                    messages = kwargs.get("messages", [])
                    truncated = self._truncate_messages(messages)
                    if truncated and attempt <= CONTEXT_MAX_RETRIES:
                        logger.warning(
                            f"[LLMClient] Context length exceeded — truncando mensagens "
                            f"e retentando (tentativa {attempt}/{CONTEXT_MAX_RETRIES})..."
                        )
                        kwargs = {**kwargs, "messages": truncated}
                        time.sleep(2)
                        continue
                    else:
                        logger.error(f"[LLMClient] Context length exceeded e não foi possível truncar. Abortando.")
                        raise RuntimeError(
                            "Contexto da conversa excedeu o limite do modelo. "
                            "Reduza o número de rodadas ou use menos agentes."
                        ) from e

                # Outros erros 4xx/5xx — não retenta
                logger.error(f"[LLMClient] Erro da API (status {e.status_code}): {e}")
                raise

            except Exception as e:
                # Erros de rede/timeout — retenta com backoff menor
                if attempt >= RATE_LIMIT_MAX_RETRIES:
                    logger.error(f"[LLMClient] Erro persistente após {attempt} tentativas: {e}")
                    raise

                actual_sleep = min(sleep_time / 2, 30.0)
                logger.warning(
                    f"[LLMClient] Erro de rede (tentativa {attempt}/{RATE_LIMIT_MAX_RETRIES}): {e}. "
                    f"Retentando em {actual_sleep:.1f}s..."
                )
                time.sleep(actual_sleep)

        raise RuntimeError(f"Falha após {RATE_LIMIT_MAX_RETRIES} tentativas.")

    def _truncate_messages(self, messages: list) -> Optional[list]:
        """
        Trunca o histórico de mensagens para caber no contexto.
        Mantém sempre: system prompt + última mensagem do usuário.
        Remove mensagens do meio (mais antigas) progressivamente.
        """
        if len(messages) <= 2:
            return None  # Não dá para truncar mais

        system_msgs = [m for m in messages if m.get("role") == "system"]
        user_msgs   = [m for m in messages if m.get("role") != "system"]

        # Manter sistema + 50% das mensagens mais recentes
        keep = max(1, len(user_msgs) // 2)
        truncated = system_msgs + user_msgs[-keep:]

        logger.info(
            f"[LLMClient] Mensagens truncadas: {len(messages)} → {len(truncated)}"
        )
        return truncated

    # ─── API pública ──────────────────────────────────────────
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None
    ) -> str:
        """
        Envia request para o LLM com rate limit handling automático.
        """
        kwargs: dict = {
            "model":       self.model,
            "messages":    messages,
            "temperature": temperature,
            "max_tokens":  max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format

        return self._call_with_retry(kwargs)

    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096
    ) -> Dict[str, Any]:
        """
        Envia request e retorna JSON parseado, com rate limit handling.
        """
        response = self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"}
        )
        # Limpar markdown code blocks
        cleaned = response.strip()
        cleaned = re.sub(r'^```(?:json)?\s*\n?', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\n?```\s*$', '', cleaned)
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            raise ValueError(f"LLM retornou JSON inválido: {cleaned[:200]}")

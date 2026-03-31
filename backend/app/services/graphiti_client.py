"""Shared Graphiti client factory -- singleton, async, Gemini-powered."""

import asyncio
from graphiti_core import Graphiti
from graphiti_core.llm_client.gemini_client import GeminiClient
from graphiti_core.llm_client.config import LLMConfig
from graphiti_core.embedder.gemini import GeminiEmbedder, GeminiEmbedderConfig
from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient
from openai import AsyncOpenAI

from ..config import Config
from ..utils.logger import get_logger

logger = get_logger('mirofish.graphiti_client')

_client: Graphiti | None = None
_lock = asyncio.Lock()


async def get_graphiti() -> Graphiti:
    global _client
    if _client is not None:
        return _client
    async with _lock:
        if _client is not None:
            return _client
        api_key = Config.LLM_API_KEY
        oai_client = AsyncOpenAI(
            api_key=api_key,
            base_url='https://generativelanguage.googleapis.com/v1beta/openai/',
        )
        reranker_config = LLMConfig(
            api_key=api_key,
            model='gemini-3-flash-preview',
            base_url='https://generativelanguage.googleapis.com/v1beta/openai/',
        )
        client = Graphiti(
            Config.NEO4J_URI,
            Config.NEO4J_USER,
            Config.NEO4J_PASSWORD,
            llm_client=GeminiClient(
                config=LLMConfig(api_key=api_key, model='gemini-3-flash-preview')
            ),
            embedder=GeminiEmbedder(
                config=GeminiEmbedderConfig(
                    api_key=api_key, embedding_model='gemini-embedding-001'
                )
            ),
            cross_encoder=OpenAIRerankerClient(
                client=oai_client, config=reranker_config
            ),
        )
        await client.build_indices_and_constraints()
        _client = client
        logger.info(f"Graphiti client initialized: {Config.NEO4J_URI}")
        return _client


async def close_graphiti():
    global _client
    if _client:
        await _client.close()
        _client = None

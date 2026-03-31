"""
Graphiti client factory -- creates fresh clients for thread safety.

Graphiti's Neo4j async driver is bound to the event loop it's created on.
Since Flask uses background threads for long-running tasks, we cannot use
a singleton client across threads. Instead, create_graphiti() returns a
fresh client each time, and callers must close() it when done.
"""

from graphiti_core import Graphiti
from graphiti_core.llm_client.gemini_client import GeminiClient
from graphiti_core.llm_client.config import LLMConfig
from graphiti_core.embedder.gemini import GeminiEmbedder, GeminiEmbedderConfig
from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient
from openai import AsyncOpenAI

from ..config import Config
from ..utils.logger import get_logger

logger = get_logger('mirofish.graphiti_client')


async def create_graphiti() -> Graphiti:
    """
    Create a new Graphiti client bound to the current event loop.
    Caller is responsible for calling await client.close() when done.
    """
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
                api_key=api_key, embedding_model='gemini-embedding-2-preview'
            )
        ),
        cross_encoder=OpenAIRerankerClient(
            client=oai_client, config=reranker_config
        ),
    )
    await client.build_indices_and_constraints()
    logger.info(f"Graphiti client created: {Config.NEO4J_URI}")
    return client


# Convenience alias for backward compat (some files import get_graphiti)
async def get_graphiti() -> Graphiti:
    """Create a fresh Graphiti client. Caller must close() when done."""
    return await create_graphiti()


async def close_graphiti():
    """No-op — clients are now per-use, closed by caller."""
    pass

import pytest
from unittest.mock import AsyncMock, patch
from src.orchestrator.source_router import SourceRouter
from src.models.source_data import (
    CollectedSources, WebSearchResult, GdeltEvent,
    NewsHeadline, RedditPost, WikipediaData, GeminiGroundingData,
)


def _make_router():
    return SourceRouter(gemini_api_key="test-gemini", serper_api_key="test-serper")


@pytest.mark.asyncio
async def test_shallow_collection_uses_correct_sources():
    router = _make_router()
    with patch.object(router._serper, "search", new_callable=AsyncMock, return_value=[
        WebSearchResult(title="Result 1", url="https://example.com/1", snippet="test"),
    ]):
        with patch.object(router._news_trends, "search_news", new_callable=AsyncMock, return_value=[
            NewsHeadline(title="Headline 1", url="https://example.com/h1"),
        ]):
            with patch.object(router._news_trends, "get_trends", new_callable=AsyncMock, return_value=None):
                with patch.object(router._reddit, "search", new_callable=AsyncMock, return_value=[
                    RedditPost(title="Post 1", subreddit="test"),
                ]):
                    sources = await router.collect("test topic", depth="shallow")
                    assert isinstance(sources, CollectedSources)
                    assert len(sources.web_search) == 1
                    assert len(sources.news_headlines) == 1
                    assert len(sources.reddit_posts) == 1
                    assert len(sources.gdelt_events) == 0
                    assert sources.wikipedia is None


@pytest.mark.asyncio
async def test_deep_collection_includes_all_sources():
    router = _make_router()
    with patch.object(router._serper, "search", new_callable=AsyncMock, return_value=[
        WebSearchResult(title="R1", url="https://example.com/1", snippet="t"),
    ]):
        with patch.object(router._news_trends, "search_news", new_callable=AsyncMock, return_value=[]):
            with patch.object(router._news_trends, "get_trends", new_callable=AsyncMock, return_value=None):
                with patch.object(router._reddit, "search", new_callable=AsyncMock, return_value=[]):
                    with patch.object(router._gdelt, "search", new_callable=AsyncMock, return_value=[
                        GdeltEvent(title="Event 1", url="https://example.com/e1"),
                    ]):
                        with patch.object(router._wikipedia, "get_summary", new_callable=AsyncMock, return_value=WikipediaData(summary="Test", url="https://wiki.org")):
                            with patch.object(router._gemini, "grounding_search", new_callable=AsyncMock, return_value=GeminiGroundingData(text="Grounded text")):
                                with patch.object(router._article_extractor, "extract_from_search_results", new_callable=AsyncMock, return_value=[]):
                                    sources = await router.collect("test topic", depth="deep")
                                    assert len(sources.gdelt_events) == 1
                                    assert sources.wikipedia is not None
                                    assert sources.gemini_grounding is not None


@pytest.mark.asyncio
async def test_collection_handles_source_failures():
    router = _make_router()
    with patch.object(router._serper, "search", new_callable=AsyncMock, side_effect=Exception("fail")):
        with patch.object(router._news_trends, "search_news", new_callable=AsyncMock, return_value=[
            NewsHeadline(title="H1", url="https://example.com"),
        ]):
            with patch.object(router._news_trends, "get_trends", new_callable=AsyncMock, return_value=None):
                with patch.object(router._reddit, "search", new_callable=AsyncMock, return_value=[]):
                    sources = await router.collect("test topic", depth="shallow")
                    assert len(sources.news_headlines) == 1
                    assert len(sources.web_search) == 0

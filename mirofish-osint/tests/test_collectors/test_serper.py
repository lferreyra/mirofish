import pytest
import httpx
import respx
from src.collectors.serper import SerperCollector
from src.models.source_data import WebSearchResult


@respx.mock
@pytest.mark.asyncio
async def test_serper_search_returns_results():
    respx.post("https://google.serper.dev/search").mock(
        return_value=httpx.Response(200, json={
            "organic": [
                {"title": "Test Result", "link": "https://example.com/test", "snippet": "A test snippet", "date": "2 days ago"},
                {"title": "Another Result", "link": "https://example.com/another", "snippet": "Another snippet"},
            ]
        })
    )
    collector = SerperCollector(api_key="test-key")
    results = await collector.search("test topic")
    assert len(results) == 2
    assert isinstance(results[0], WebSearchResult)
    assert results[0].title == "Test Result"


@respx.mock
@pytest.mark.asyncio
async def test_serper_search_handles_api_error():
    respx.post("https://google.serper.dev/search").mock(
        return_value=httpx.Response(500, json={"error": "Internal Server Error"})
    )
    collector = SerperCollector(api_key="test-key")
    results = await collector.search("test topic")
    assert results == []


@respx.mock
@pytest.mark.asyncio
async def test_serper_search_with_num_results():
    respx.post("https://google.serper.dev/search").mock(
        return_value=httpx.Response(200, json={"organic": [
            {"title": f"Result {i}", "link": f"https://example.com/{i}", "snippet": f"Snippet {i}"}
            for i in range(5)
        ]})
    )
    collector = SerperCollector(api_key="test-key")
    results = await collector.search("test topic", num_results=5)
    assert len(results) == 5

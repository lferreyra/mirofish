import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from src.mcp_clients.gdelt import GdeltClient
from src.mcp_clients.news_trends import NewsTrendsClient
from src.mcp_clients.reddit import RedditClient
from src.models.source_data import GdeltEvent, NewsHeadline, GoogleTrendsData, RedditPost


@pytest.mark.asyncio
async def test_gdelt_client_search_returns_events():
    mock_data = [
        {"title": "Trade War Escalates", "url": "https://example.com/1", "tone": -3.5, "seendate": "20260330", "sourcecountry": "US"},
        {"title": "New Tariffs Announced", "url": "https://example.com/2", "tone": -1.2, "seendate": "20260329", "sourcecountry": "CN"},
    ]
    gdelt = GdeltClient()
    with patch.object(gdelt, "_call_tool", new_callable=AsyncMock, return_value=mock_data):
        events = await gdelt.search("US tariffs")
        assert len(events) == 2
        assert isinstance(events[0], GdeltEvent)
        assert events[0].title == "Trade War Escalates"
        assert events[0].tone == -3.5


@pytest.mark.asyncio
async def test_gdelt_client_handles_error():
    gdelt = GdeltClient()
    with patch.object(gdelt, "_call_tool", new_callable=AsyncMock, side_effect=Exception("Connection failed")):
        events = await gdelt.search("test")
        assert events == []


@pytest.mark.asyncio
async def test_news_trends_search_news():
    mock_data = [
        {"title": "Breaking: New Policy", "link": "https://example.com/1", "source": {"title": "Reuters"}, "published": "2026-03-30"},
    ]
    client = NewsTrendsClient()
    with patch.object(client, "_call_tool", new_callable=AsyncMock, return_value=mock_data):
        headlines = await client.search_news("new policy")
        assert len(headlines) == 1
        assert isinstance(headlines[0], NewsHeadline)
        assert headlines[0].title == "Breaking: New Policy"


@pytest.mark.asyncio
async def test_news_trends_get_trends():
    mock_data = {"trending": [{"keyword": "AI regulation", "traffic": "500K+"}, {"keyword": "chip tariffs", "traffic": "200K+"}]}
    client = NewsTrendsClient()
    with patch.object(client, "_call_tool", new_callable=AsyncMock, return_value=mock_data):
        trends = await client.get_trends("US")
        assert isinstance(trends, GoogleTrendsData)
        assert len(trends.related_queries) > 0


@pytest.mark.asyncio
async def test_news_trends_handles_error():
    client = NewsTrendsClient()
    with patch.object(client, "_call_tool", new_callable=AsyncMock, side_effect=Exception("fail")):
        headlines = await client.search_news("test")
        assert headlines == []


@pytest.mark.asyncio
async def test_reddit_search_posts():
    mock_data = [
        {"title": "Discussion about tariffs", "subreddit": "economics", "score": 1500, "num_comments": 234, "created_utc": "2026-03-29", "url": "https://reddit.com/r/economics/123"},
    ]
    client = RedditClient()
    with patch.object(client, "_call_tool", new_callable=AsyncMock, return_value=mock_data):
        posts = await client.search("US tariffs")
        assert len(posts) == 1
        assert isinstance(posts[0], RedditPost)
        assert posts[0].subreddit == "economics"
        assert posts[0].score == 1500


@pytest.mark.asyncio
async def test_reddit_handles_error():
    client = RedditClient()
    with patch.object(client, "_call_tool", new_callable=AsyncMock, side_effect=Exception("fail")):
        posts = await client.search("test")
        assert posts == []

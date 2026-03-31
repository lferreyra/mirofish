import pytest
from unittest.mock import patch, MagicMock
from src.collectors.wikipedia import WikipediaCollector
from src.models.source_data import WikipediaData


@pytest.mark.asyncio
async def test_wikipedia_get_summary():
    mock_page = MagicMock()
    mock_page.exists.return_value = True
    mock_page.summary = "TSMC is a semiconductor company based in Taiwan."
    mock_page.fullurl = "https://en.wikipedia.org/wiki/TSMC"
    mock_page.links = {"Taiwan": MagicMock(), "Semiconductor": MagicMock(), "Intel": MagicMock()}

    mock_wiki = MagicMock()
    mock_wiki.page.return_value = mock_page

    with patch("src.collectors.wikipedia.wikipediaapi.Wikipedia", return_value=mock_wiki):
        collector = WikipediaCollector()
        result = await collector.get_summary("TSMC")
        assert isinstance(result, WikipediaData)
        assert "TSMC" in result.summary
        assert result.url == "https://en.wikipedia.org/wiki/TSMC"
        assert len(result.key_entities) > 0


@pytest.mark.asyncio
async def test_wikipedia_returns_none_for_missing_page():
    mock_page = MagicMock()
    mock_page.exists.return_value = False

    mock_wiki = MagicMock()
    mock_wiki.page.return_value = mock_page

    with patch("src.collectors.wikipedia.wikipediaapi.Wikipedia", return_value=mock_wiki):
        collector = WikipediaCollector()
        result = await collector.get_summary("xyznonexistentpage123")
        assert result is None

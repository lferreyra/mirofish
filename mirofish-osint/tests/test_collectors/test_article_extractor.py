import pytest
from unittest.mock import patch, MagicMock
from src.collectors.article_extractor import ArticleExtractorCollector
from src.models.source_data import ArticleData, WebSearchResult


@pytest.mark.asyncio
async def test_extract_articles_from_urls():
    mock_article = MagicMock()
    mock_article.title = "Test Article Title"
    mock_article.text = "This is the full article text content for testing."
    mock_article.publish_date = None
    mock_article.source_url = "https://example.com"

    with patch("src.collectors.article_extractor.newspaper.Article") as MockArticle:
        instance = MockArticle.return_value
        instance.title = mock_article.title
        instance.text = mock_article.text
        instance.publish_date = mock_article.publish_date
        instance.source_url = mock_article.source_url

        collector = ArticleExtractorCollector()
        search_results = [
            WebSearchResult(title="Test", url="https://example.com/article1", snippet="test"),
        ]
        articles = await collector.extract_from_search_results(search_results, max_articles=1)

        assert len(articles) == 1
        assert isinstance(articles[0], ArticleData)
        assert articles[0].title == "Test Article Title"


@pytest.mark.asyncio
async def test_extract_handles_failure_gracefully():
    with patch("src.collectors.article_extractor.newspaper.Article", side_effect=Exception("Network error")):
        collector = ArticleExtractorCollector()
        search_results = [
            WebSearchResult(title="Test", url="https://example.com/bad", snippet="test"),
        ]
        articles = await collector.extract_from_search_results(search_results, max_articles=1)
        assert articles == []

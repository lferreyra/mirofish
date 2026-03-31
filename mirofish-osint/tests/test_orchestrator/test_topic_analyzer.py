import pytest
from unittest.mock import patch, MagicMock
from src.orchestrator.topic_analyzer import TopicAnalyzer


@pytest.mark.asyncio
async def test_analyze_topic_returns_classification():
    mock_response = MagicMock()
    mock_response.text = '{"categories": ["geopolitical", "financial"], "source_weights": {"serper": 1.0, "gdelt": 0.9, "news_trends": 0.8, "reddit": 0.5, "wikipedia": 0.7, "gemini_grounding": 0.8}}'
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    with patch("src.orchestrator.topic_analyzer.genai.Client", return_value=mock_client):
        analyzer = TopicAnalyzer(api_key="test-key")
        result = await analyzer.analyze("US chip tariffs on TSMC")
        assert "geopolitical" in result["categories"]
        assert result["source_weights"]["gdelt"] == 0.9


@pytest.mark.asyncio
async def test_analyze_topic_returns_defaults_on_error():
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("API error")
    with patch("src.orchestrator.topic_analyzer.genai.Client", return_value=mock_client):
        analyzer = TopicAnalyzer(api_key="test-key")
        result = await analyzer.analyze("test topic")
        assert "general" in result["categories"]
        assert "source_weights" in result

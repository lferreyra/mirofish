import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from src.collectors.gemini_research import GeminiResearchCollector
from src.models.source_data import GeminiGroundingData, GeminiDeepResearchData


@pytest.mark.asyncio
async def test_grounding_search():
    mock_response = MagicMock()
    mock_response.text = "Spain won Euro 2024."
    mock_metadata = MagicMock()
    mock_metadata.grounding_chunks = []
    mock_metadata.grounding_supports = []
    mock_response.candidates = [MagicMock(grounding_metadata=mock_metadata)]

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    with patch("src.collectors.gemini_research.genai.Client", return_value=mock_client):
        collector = GeminiResearchCollector(api_key="test-key")
        result = await collector.grounding_search("Who won Euro 2024?")
        assert isinstance(result, GeminiGroundingData)
        assert "Spain" in result.text


@pytest.mark.asyncio
async def test_grounding_search_handles_error():
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("API error")

    with patch("src.collectors.gemini_research.genai.Client", return_value=mock_client):
        collector = GeminiResearchCollector(api_key="test-key")
        result = await collector.grounding_search("test query")
        assert result is None


@pytest.mark.asyncio
async def test_deep_research_returns_report():
    mock_interaction_start = MagicMock()
    mock_interaction_start.id = "interaction-123"

    mock_interaction_done = MagicMock()
    mock_interaction_done.status = "completed"
    mock_interaction_done.outputs = [MagicMock(text="Full research report about TPUs.")]

    mock_client = MagicMock()
    mock_client.interactions.create.return_value = mock_interaction_start
    mock_client.interactions.get.return_value = mock_interaction_done

    with patch("src.collectors.gemini_research.genai.Client", return_value=mock_client):
        with patch("asyncio.to_thread", side_effect=[mock_interaction_start, mock_interaction_done]):
            collector = GeminiResearchCollector(api_key="test-key")
            result = await collector.deep_research("Google TPU history", timeout=5)
            assert isinstance(result, GeminiDeepResearchData)
            assert "TPUs" in result.report
            assert result.status == "completed"


@pytest.mark.asyncio
async def test_deep_research_handles_failure():
    mock_interaction_start = MagicMock()
    mock_interaction_start.id = "interaction-456"

    mock_interaction_done = MagicMock()
    mock_interaction_done.status = "failed"

    with patch("src.collectors.gemini_research.genai.Client") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        with patch("asyncio.to_thread", side_effect=[mock_interaction_start, mock_interaction_done]):
            collector = GeminiResearchCollector(api_key="test-key")
            result = await collector.deep_research("test topic", timeout=5)
            assert result is None

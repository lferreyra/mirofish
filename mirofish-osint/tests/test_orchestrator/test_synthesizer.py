import pytest
from unittest.mock import patch, MagicMock
from src.orchestrator.synthesizer import Synthesizer
from src.models.source_data import CollectedSources, WebSearchResult, GdeltEvent
from src.models.research_result import Entity, TimelineEvent


@pytest.mark.asyncio
async def test_synthesize_mirofish_format():
    mock_response = MagicMock()
    mock_response.text = "# OSINT Intelligence Report: Test Topic\n\n## Key Entities\n\n## Relationships\n"
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    with patch("src.orchestrator.synthesizer.genai.Client", return_value=mock_client):
        synthesizer = Synthesizer(api_key="test-key")
        sources = CollectedSources(
            web_search=[WebSearchResult(title="Test", url="https://example.com", snippet="test")],
            gdelt_events=[GdeltEvent(title="Event A", url="https://example.com/e", date="20260328")],
        )
        entities = [Entity(name="TestCorp", type="organization", mention_count=2, sources=["serper"])]
        timeline = [TimelineEvent(date="2026-03-28", event="Event A", source="gdelt")]

        report = await synthesizer.synthesize(
            topic="Test Topic", depth="deep", sources=sources,
            entities=entities, timeline=timeline, output_format="mirofish",
        )
        assert "OSINT Intelligence Report: Test Topic" in report
        assert "Key Entities" in report


@pytest.mark.asyncio
async def test_synthesize_returns_error_report_on_failure():
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("API error")
    with patch("src.orchestrator.synthesizer.genai.Client", return_value=mock_client):
        synthesizer = Synthesizer(api_key="test-key")
        report = await synthesizer.synthesize(
            topic="Test", depth="shallow", sources=CollectedSources(),
            entities=[], timeline=[], output_format="general",
        )
        assert "Error" in report or "error" in report

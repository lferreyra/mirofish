from src.models.source_data import (
    WebSearchResult, CollectedSources, SourceStatus,
)
from src.models.research_result import (
    Entity, TimelineEvent, ResearchResult,
)


def test_web_search_result_creation():
    result = WebSearchResult(
        title="Test Article",
        url="https://example.com",
        snippet="A test snippet",
        date="2026-03-30",
        relevance_score=0.95,
    )
    assert result.title == "Test Article"
    assert result.relevance_score == 0.95


def test_collected_sources_defaults_to_empty():
    sources = CollectedSources()
    assert sources.web_search == []
    assert sources.articles == []
    assert sources.gdelt_events == []
    assert sources.reddit_posts == []
    assert sources.wikipedia is None
    assert sources.gemini_grounding is None
    assert sources.gemini_deep_research is None


def test_research_result_serialization():
    result = ResearchResult(
        topic="Test topic",
        topic_classification=["tech"],
        collected_at="2026-03-30T12:00:00Z",
        sources=CollectedSources(),
        entities=[Entity(name="OpenAI", type="organization", mention_count=3, sources=["serper", "gdelt"])],
        timeline=[TimelineEvent(date="2026-03-30", event="Test event", source="serper", confidence="high")],
    )
    data = result.model_dump()
    assert data["topic"] == "Test topic"
    assert len(data["entities"]) == 1
    assert data["entities"][0]["name"] == "OpenAI"


def test_source_status():
    status = SourceStatus(name="serper", status="active", description="Web search")
    assert status.status == "active"

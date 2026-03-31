import pytest
from src.orchestrator.normalizer import Normalizer
from src.models.source_data import CollectedSources, WebSearchResult, GdeltEvent, NewsHeadline
from src.models.research_result import Entity, TimelineEvent


def test_extract_entities_from_sources():
    sources = CollectedSources(
        web_search=[
            WebSearchResult(title="TSMC Plans New Factory in Arizona", url="https://example.com/1", snippet="TSMC is building a new semiconductor fab in Arizona, USA."),
            WebSearchResult(title="Intel Responds to TSMC Expansion", url="https://example.com/2", snippet="Intel CEO comments on TSMC plans."),
        ],
        gdelt_events=[
            GdeltEvent(title="TSMC Arizona Investment Confirmed", url="https://example.com/3", tone=2.5, date="20260325"),
        ],
    )
    normalizer = Normalizer()
    entities = normalizer.extract_entities(sources)
    names = [e.name for e in entities]
    assert len(entities) > 0


def test_build_timeline():
    sources = CollectedSources(
        gdelt_events=[
            GdeltEvent(title="Event A", url="https://example.com/a", date="20260328", tone=-1.0),
            GdeltEvent(title="Event B", url="https://example.com/b", date="20260330", tone=2.0),
        ],
        news_headlines=[
            NewsHeadline(title="Breaking: Event C", url="https://example.com/c", date="2026-03-29"),
        ],
    )
    normalizer = Normalizer()
    timeline = normalizer.build_timeline(sources)
    assert len(timeline) == 3
    assert isinstance(timeline[0], TimelineEvent)
    dates = [t.date for t in timeline]
    assert dates == sorted(dates)


def test_deduplicate_removes_similar_urls():
    sources = CollectedSources(
        web_search=[
            WebSearchResult(title="Same Article", url="https://example.com/article", snippet="test"),
            WebSearchResult(title="Same Article Copy", url="https://example.com/article", snippet="test copy"),
            WebSearchResult(title="Different Article", url="https://example.com/other", snippet="other"),
        ],
    )
    normalizer = Normalizer()
    deduped = normalizer.deduplicate(sources)
    assert len(deduped.web_search) == 2

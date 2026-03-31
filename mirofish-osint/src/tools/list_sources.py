from src.models.source_data import SourceStatus

SOURCES = [
    SourceStatus(name="serper", status="active", description="Web search via Serper API"),
    SourceStatus(name="gdelt", status="active", description="GDELT DOC 2.0 global news events (3-month rolling)"),
    SourceStatus(name="google_news_trends", status="active", description="Google News headlines + Google Trends"),
    SourceStatus(name="reddit", status="active", description="Reddit posts and discussions (zero auth)"),
    SourceStatus(name="wikipedia", status="active", description="Wikipedia background context"),
    SourceStatus(name="newspaper4k", status="active", description="Full article text extraction"),
    SourceStatus(name="gemini_grounding", status="active", description="Gemini Search Grounding"),
    SourceStatus(name="gemini_deep_research", status="active", description="Gemini Deep Research Agent"),
]


def get_sources() -> list[dict]:
    return [s.model_dump() for s in SOURCES]

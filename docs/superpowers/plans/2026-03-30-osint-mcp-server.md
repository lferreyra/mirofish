# OSINT MCP Server Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone MCP server that gathers OSINT data from multiple sources and synthesizes reports via Gemini, packaged in a single Docker container.

**Architecture:** MCP gateway pattern — one exposed FastMCP server orchestrates 3 internal MCP servers (GDELT, Google News/Trends, Reddit) via stdio subprocess plus 4 native Python collectors (Serper, newspaper4k, Wikipedia, Gemini research). Parallel async collection, Pydantic models, Gemini synthesis.

**Tech Stack:** Python 3.12, FastMCP, google-genai, httpx, newspaper4k, wikipedia-api, Pydantic, Docker, Node.js 20 (for mcp-gdelt)

**Spec:** `docs/superpowers/specs/2026-03-30-osint-mcp-server-design.md`

---

### Task 1: Project Scaffold & Dependencies

**Files:**
- Create: `mirofish-osint/pyproject.toml`
- Create: `mirofish-osint/.env.example`
- Create: `mirofish-osint/src/__init__.py`
- Create: `mirofish-osint/src/server.py`
- Create: `mirofish-osint/tests/__init__.py`

- [ ] **Step 1: Create project directory structure**

```bash
mkdir -p mirofish-osint/src/{tools,orchestrator,collectors,mcp_clients,models}
mkdir -p mirofish-osint/tests/{test_collectors,test_orchestrator,test_integration}
mkdir -p mirofish-osint/internal_servers
touch mirofish-osint/src/__init__.py
touch mirofish-osint/src/tools/__init__.py
touch mirofish-osint/src/orchestrator/__init__.py
touch mirofish-osint/src/collectors/__init__.py
touch mirofish-osint/src/mcp_clients/__init__.py
touch mirofish-osint/src/models/__init__.py
touch mirofish-osint/tests/__init__.py
touch mirofish-osint/tests/test_collectors/__init__.py
touch mirofish-osint/tests/test_orchestrator/__init__.py
touch mirofish-osint/tests/test_integration/__init__.py
```

- [ ] **Step 2: Create pyproject.toml**

```toml
[project]
name = "mirofish-osint"
version = "0.1.0"
description = "OSINT Research Agent MCP Server for MiroFish"
requires-python = ">=3.12"
dependencies = [
    "fastmcp>=2.0.0",
    "google-genai>=1.0.0",
    "httpx>=0.28.0",
    "newspaper4k>=0.9.0",
    "wikipedia-api>=0.7.0",
    "pydantic>=2.0.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "respx>=0.22.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 3: Create .env.example**

```env
# Required
GEMINI_API_KEY=your_gemini_key
SERPER_API_KEY=your_serper_key

# Optional (for future MiroFish auto-feed)
# MIROFISH_API_URL=http://localhost:5001
```

- [ ] **Step 4: Create .env with actual keys**

```env
GEMINI_API_KEY=AIzaSyAbPCs48URCPCRGfz04OiyR-iUXAcoHdZ0
SERPER_API_KEY=18220f8ce61791863b6bf5ace710f8eeb4a61fe6
```

- [ ] **Step 5: Create minimal server.py that starts**

```python
from fastmcp import FastMCP

mcp = FastMCP("MiroFish OSINT")


@mcp.tool
def list_sources() -> list[dict]:
    """List available OSINT data sources and their current status."""
    return [
        {"name": "serper", "status": "active", "description": "Web search via Serper API"},
        {"name": "gdelt", "status": "active", "description": "GDELT DOC 2.0 global news events"},
        {"name": "google_news_trends", "status": "active", "description": "Google News + Trends"},
        {"name": "reddit", "status": "active", "description": "Reddit posts, zero auth"},
        {"name": "wikipedia", "status": "active", "description": "Wikipedia summaries"},
        {"name": "newspaper4k", "status": "active", "description": "Full article text extraction"},
        {"name": "gemini_grounding", "status": "active", "description": "Gemini Search Grounding"},
        {"name": "gemini_deep_research", "status": "active", "description": "Gemini Deep Research Agent"},
    ]


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8080)
```

- [ ] **Step 6: Install dependencies and verify server starts**

```bash
cd mirofish-osint && uv sync && uv run python src/server.py
```

Expected: Server starts on port 8080 with no errors.

- [ ] **Step 7: Commit**

```bash
git add mirofish-osint/
git commit -m "feat(osint): scaffold project with FastMCP server entry point"
```

---

### Task 2: Pydantic Data Models

**Files:**
- Create: `mirofish-osint/src/models/source_data.py`
- Create: `mirofish-osint/src/models/research_result.py`
- Create: `mirofish-osint/tests/test_models.py`

- [ ] **Step 1: Write tests for data models**

```python
# tests/test_models.py
from src.models.source_data import (
    WebSearchResult,
    ArticleData,
    GdeltEvent,
    NewsHeadline,
    GoogleTrendsData,
    RedditPost,
    WikipediaData,
    GeminiGroundingData,
    GeminiDeepResearchData,
    CollectedSources,
    SourceStatus,
)
from src.models.research_result import (
    Entity,
    TimelineEvent,
    ResearchResult,
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

    degraded = SourceStatus(name="reddit", status="degraded", description="Reddit down")
    assert degraded.status == "degraded"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd mirofish-osint && uv run pytest tests/test_models.py -v
```

Expected: FAIL — modules don't exist yet.

- [ ] **Step 3: Implement source_data.py**

```python
# src/models/source_data.py
from pydantic import BaseModel


class WebSearchResult(BaseModel):
    title: str
    url: str
    snippet: str
    date: str = ""
    relevance_score: float = 0.0


class ArticleData(BaseModel):
    title: str
    url: str
    full_text: str
    date: str = ""
    source_name: str = ""


class GdeltEvent(BaseModel):
    title: str
    url: str
    tone: float = 0.0
    date: str = ""
    source_country: str = ""


class NewsHeadline(BaseModel):
    title: str
    url: str
    source: str = ""
    date: str = ""
    category: str = ""


class GoogleTrendsData(BaseModel):
    interest_over_time: dict = {}
    related_queries: list[str] = []
    geographic: dict = {}


class RedditPost(BaseModel):
    title: str
    subreddit: str = ""
    score: int = 0
    num_comments: int = 0
    date: str = ""
    url: str = ""


class WikipediaData(BaseModel):
    summary: str
    key_entities: list[str] = []
    url: str = ""


class GeminiGroundingData(BaseModel):
    text: str
    citations: list[dict] = []
    search_queries: list[str] = []


class GeminiDeepResearchData(BaseModel):
    report: str
    status: str = "completed"


class CollectedSources(BaseModel):
    web_search: list[WebSearchResult] = []
    articles: list[ArticleData] = []
    gdelt_events: list[GdeltEvent] = []
    news_headlines: list[NewsHeadline] = []
    google_trends: GoogleTrendsData | None = None
    reddit_posts: list[RedditPost] = []
    wikipedia: WikipediaData | None = None
    gemini_grounding: GeminiGroundingData | None = None
    gemini_deep_research: GeminiDeepResearchData | None = None


class SourceStatus(BaseModel):
    name: str
    status: str  # "active" | "degraded" | "down"
    description: str
```

- [ ] **Step 4: Implement research_result.py**

```python
# src/models/research_result.py
from pydantic import BaseModel
from src.models.source_data import CollectedSources


class Entity(BaseModel):
    name: str
    type: str  # "person" | "organization" | "location"
    mention_count: int = 0
    sources: list[str] = []


class TimelineEvent(BaseModel):
    date: str
    event: str
    source: str
    confidence: str = "medium"  # "high" | "medium" | "low"


class ResearchResult(BaseModel):
    topic: str
    topic_classification: list[str]
    collected_at: str
    sources: CollectedSources
    entities: list[Entity] = []
    timeline: list[TimelineEvent] = []
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd mirofish-osint && uv run pytest tests/test_models.py -v
```

Expected: All 4 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add mirofish-osint/src/models/ mirofish-osint/tests/test_models.py
git commit -m "feat(osint): add Pydantic data models for sources and research results"
```

---

### Task 3: Serper Collector

**Files:**
- Create: `mirofish-osint/src/collectors/serper.py`
- Create: `mirofish-osint/tests/test_collectors/test_serper.py`

- [ ] **Step 1: Write tests for Serper collector**

```python
# tests/test_collectors/test_serper.py
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
                {
                    "title": "Test Result",
                    "link": "https://example.com/test",
                    "snippet": "A test snippet about the topic",
                    "date": "2 days ago",
                },
                {
                    "title": "Another Result",
                    "link": "https://example.com/another",
                    "snippet": "Another snippet",
                },
            ]
        })
    )

    collector = SerperCollector(api_key="test-key")
    results = await collector.search("test topic")

    assert len(results) == 2
    assert isinstance(results[0], WebSearchResult)
    assert results[0].title == "Test Result"
    assert results[0].url == "https://example.com/test"


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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd mirofish-osint && uv run pytest tests/test_collectors/test_serper.py -v
```

Expected: FAIL — module doesn't exist.

- [ ] **Step 3: Implement Serper collector**

```python
# src/collectors/serper.py
import httpx
from src.models.source_data import WebSearchResult


class SerperCollector:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://google.serper.dev/search"

    async def search(self, query: str, num_results: int = 10) -> list[WebSearchResult]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.base_url,
                    headers={"X-API-KEY": self.api_key, "Content-Type": "application/json"},
                    json={"q": query, "num": num_results},
                    timeout=15.0,
                )
                response.raise_for_status()
                data = response.json()

            results = []
            for item in data.get("organic", []):
                results.append(WebSearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    date=item.get("date", ""),
                ))
            return results
        except Exception:
            return []
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd mirofish-osint && uv run pytest tests/test_collectors/test_serper.py -v
```

Expected: All 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add mirofish-osint/src/collectors/serper.py mirofish-osint/tests/test_collectors/test_serper.py
git commit -m "feat(osint): add Serper web search collector"
```

---

### Task 4: Article Extractor Collector

**Files:**
- Create: `mirofish-osint/src/collectors/article_extractor.py`
- Create: `mirofish-osint/tests/test_collectors/test_article_extractor.py`

- [ ] **Step 1: Write tests for article extractor**

```python
# tests/test_collectors/test_article_extractor.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd mirofish-osint && uv run pytest tests/test_collectors/test_article_extractor.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement article extractor**

```python
# src/collectors/article_extractor.py
import asyncio
from concurrent.futures import ThreadPoolExecutor
import newspaper
from src.models.source_data import ArticleData, WebSearchResult


class ArticleExtractorCollector:
    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=5)

    def _extract_single(self, url: str) -> ArticleData | None:
        try:
            article = newspaper.Article(url)
            article.download()
            article.parse()
            date_str = ""
            if article.publish_date:
                date_str = article.publish_date.isoformat()
            return ArticleData(
                title=article.title or "",
                url=url,
                full_text=article.text or "",
                date=date_str,
                source_name=article.source_url or "",
            )
        except Exception:
            return None

    async def extract_from_search_results(
        self, search_results: list[WebSearchResult], max_articles: int = 5
    ) -> list[ArticleData]:
        urls = [r.url for r in search_results[:max_articles]]
        loop = asyncio.get_event_loop()
        tasks = [loop.run_in_executor(self._executor, self._extract_single, url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if isinstance(r, ArticleData)]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd mirofish-osint && uv run pytest tests/test_collectors/test_article_extractor.py -v
```

Expected: All 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add mirofish-osint/src/collectors/article_extractor.py mirofish-osint/tests/test_collectors/test_article_extractor.py
git commit -m "feat(osint): add newspaper4k article extractor collector"
```

---

### Task 5: Wikipedia Collector

**Files:**
- Create: `mirofish-osint/src/collectors/wikipedia.py`
- Create: `mirofish-osint/tests/test_collectors/test_wikipedia.py`

- [ ] **Step 1: Write tests for Wikipedia collector**

```python
# tests/test_collectors/test_wikipedia.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd mirofish-osint && uv run pytest tests/test_collectors/test_wikipedia.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement Wikipedia collector**

```python
# src/collectors/wikipedia.py
import asyncio
from concurrent.futures import ThreadPoolExecutor
import wikipediaapi
from src.models.source_data import WikipediaData


class WikipediaCollector:
    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=2)

    def _fetch(self, topic: str) -> WikipediaData | None:
        wiki = wikipediaapi.Wikipedia(
            user_agent="MiroFishOSINT/0.1 (https://github.com/666ghj/MiroFish)",
            language="en",
        )
        page = wiki.page(topic)
        if not page.exists():
            return None
        key_entities = list(page.links.keys())[:20]
        return WikipediaData(
            summary=page.summary,
            key_entities=key_entities,
            url=page.fullurl,
        )

    async def get_summary(self, topic: str) -> WikipediaData | None:
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(self._executor, self._fetch, topic)
        except Exception:
            return None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd mirofish-osint && uv run pytest tests/test_collectors/test_wikipedia.py -v
```

Expected: All 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add mirofish-osint/src/collectors/wikipedia.py mirofish-osint/tests/test_collectors/test_wikipedia.py
git commit -m "feat(osint): add Wikipedia collector"
```

---

### Task 6: Gemini Research Collector (Grounding + Deep Research)

**Files:**
- Create: `mirofish-osint/src/collectors/gemini_research.py`
- Create: `mirofish-osint/tests/test_collectors/test_gemini_research.py`

- [ ] **Step 1: Write tests for Gemini research collector**

```python
# tests/test_collectors/test_gemini_research.py
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from src.collectors.gemini_research import GeminiResearchCollector
from src.models.source_data import GeminiGroundingData, GeminiDeepResearchData


@pytest.mark.asyncio
async def test_grounding_search():
    mock_response = MagicMock()
    mock_response.text = "Spain won Euro 2024."
    mock_metadata = MagicMock()
    mock_metadata.search_entry_point = None
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
    mock_client.interactions.create = AsyncMock(return_value=mock_interaction_start)
    mock_client.interactions.get = AsyncMock(return_value=mock_interaction_done)

    with patch("src.collectors.gemini_research.genai.Client", return_value=mock_client):
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

    mock_client = MagicMock()
    mock_client.interactions.create = AsyncMock(return_value=mock_interaction_start)
    mock_client.interactions.get = AsyncMock(return_value=mock_interaction_done)

    with patch("src.collectors.gemini_research.genai.Client", return_value=mock_client):
        collector = GeminiResearchCollector(api_key="test-key")
        result = await collector.deep_research("test topic", timeout=5)

        assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd mirofish-osint && uv run pytest tests/test_collectors/test_gemini_research.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement Gemini research collector**

```python
# src/collectors/gemini_research.py
import asyncio
from concurrent.futures import ThreadPoolExecutor
from google import genai
from google.genai import types
from src.models.source_data import GeminiGroundingData, GeminiDeepResearchData


class GeminiResearchCollector:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self._executor = ThreadPoolExecutor(max_workers=2)

    def _get_client(self) -> genai.Client:
        return genai.Client(api_key=self.api_key)

    def _grounding_sync(self, query: str) -> GeminiGroundingData | None:
        client = self._get_client()
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=f"Provide a comprehensive overview of the current situation regarding: {query}",
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            ),
        )
        citations = []
        search_queries = []
        if response.candidates:
            metadata = response.candidates[0].grounding_metadata
            if metadata:
                if metadata.grounding_chunks:
                    for chunk in metadata.grounding_chunks:
                        if hasattr(chunk, "web") and chunk.web:
                            citations.append({"title": chunk.web.title or "", "url": chunk.web.uri or ""})
                if metadata.grounding_supports:
                    for support in metadata.grounding_supports:
                        if hasattr(support, "segment") and support.segment:
                            search_queries.append(support.segment.text or "")
        return GeminiGroundingData(
            text=response.text or "",
            citations=citations,
            search_queries=search_queries,
        )

    async def grounding_search(self, query: str) -> GeminiGroundingData | None:
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(self._executor, self._grounding_sync, query)
        except Exception:
            return None

    async def deep_research(self, topic: str, timeout: int = 600) -> GeminiDeepResearchData | None:
        try:
            client = self._get_client()
            interaction = await asyncio.to_thread(
                client.interactions.create,
                input=f"Research comprehensively: {topic}. Cover history, current state, "
                      f"key players, recent developments, and future outlook.",
                agent="deep-research-pro-preview-12-2025",
                background=True,
            )

            elapsed = 0
            poll_interval = 10
            while elapsed < timeout:
                result = await asyncio.to_thread(client.interactions.get, interaction.id)
                if result.status == "completed":
                    report_text = result.outputs[-1].text if result.outputs else ""
                    return GeminiDeepResearchData(report=report_text, status="completed")
                if result.status in ("failed", "cancelled"):
                    return None
                await asyncio.sleep(poll_interval)
                elapsed += poll_interval

            return None  # timeout
        except Exception:
            return None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd mirofish-osint && uv run pytest tests/test_collectors/test_gemini_research.py -v
```

Expected: All 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add mirofish-osint/src/collectors/gemini_research.py mirofish-osint/tests/test_collectors/test_gemini_research.py
git commit -m "feat(osint): add Gemini research collector (grounding + deep research)"
```

---

### Task 7: Internal MCP Client Base + GDELT Client

**Files:**
- Create: `mirofish-osint/src/mcp_clients/base.py`
- Create: `mirofish-osint/src/mcp_clients/gdelt.py`
- Create: `mirofish-osint/tests/test_collectors/test_mcp_clients.py`

- [ ] **Step 1: Write tests for MCP client base and GDELT wrapper**

```python
# tests/test_collectors/test_mcp_clients.py
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from src.mcp_clients.base import InternalMCPClient
from src.mcp_clients.gdelt import GdeltClient
from src.models.source_data import GdeltEvent


@pytest.mark.asyncio
async def test_internal_mcp_client_call_tool():
    mock_result = MagicMock()
    mock_result.content = [MagicMock(text='[{"title":"Test Event","url":"https://example.com","tone":2.5}]')]

    mock_session = AsyncMock()
    mock_session.call_tool.return_value = mock_result
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with patch("src.mcp_clients.base.stdio_client") as mock_stdio:
        mock_read = AsyncMock()
        mock_write = AsyncMock()
        mock_stdio.return_value.__aenter__ = AsyncMock(return_value=(mock_read, mock_write))
        mock_stdio.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("src.mcp_clients.base.ClientSession", return_value=mock_session):
            client = InternalMCPClient(command="node", args=["server.js"])
            result = await client.call_tool("search_articles", {"query": "test"})
            assert result is not None


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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd mirofish-osint && uv run pytest tests/test_collectors/test_mcp_clients.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement base MCP client**

```python
# src/mcp_clients/base.py
import json
from mcp import StdioServerParameters, stdio_client, ClientSession


class InternalMCPClient:
    def __init__(self, command: str, args: list[str] | None = None, env: dict[str, str] | None = None):
        self.server_params = StdioServerParameters(
            command=command,
            args=args or [],
            env=env,
        )

    async def call_tool(self, tool_name: str, arguments: dict) -> any:
        async with stdio_client(self.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                if result.content and len(result.content) > 0:
                    text = result.content[0].text
                    try:
                        return json.loads(text)
                    except (json.JSONDecodeError, AttributeError):
                        return text
                return None
```

- [ ] **Step 4: Implement GDELT MCP client**

```python
# src/mcp_clients/gdelt.py
from src.mcp_clients.base import InternalMCPClient
from src.models.source_data import GdeltEvent


class GdeltClient:
    def __init__(self):
        self._client = InternalMCPClient(
            command="npx",
            args=["-y", "@missionsquad/mcp-gdelt"],
        )

    async def _call_tool(self, tool_name: str, arguments: dict) -> any:
        return await self._client.call_tool(tool_name, arguments)

    async def search(self, query: str) -> list[GdeltEvent]:
        try:
            data = await self._call_tool("search_articles", {"query": query})
            if not isinstance(data, list):
                return []
            events = []
            for item in data:
                events.append(GdeltEvent(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    tone=float(item.get("tone", 0.0)),
                    date=item.get("seendate", ""),
                    source_country=item.get("sourcecountry", ""),
                ))
            return events
        except Exception:
            return []
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd mirofish-osint && uv run pytest tests/test_collectors/test_mcp_clients.py -v
```

Expected: All 3 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add mirofish-osint/src/mcp_clients/
git commit -m "feat(osint): add internal MCP client base + GDELT wrapper"
```

---

### Task 8: Google News/Trends MCP Client + Reddit MCP Client

**Files:**
- Create: `mirofish-osint/src/mcp_clients/news_trends.py`
- Create: `mirofish-osint/src/mcp_clients/reddit.py`
- Create: `mirofish-osint/tests/test_collectors/test_news_reddit_clients.py`

- [ ] **Step 1: Write tests**

```python
# tests/test_collectors/test_news_reddit_clients.py
import pytest
from unittest.mock import patch, AsyncMock
from src.mcp_clients.news_trends import NewsTrendsClient
from src.mcp_clients.reddit import RedditClient
from src.models.source_data import NewsHeadline, GoogleTrendsData, RedditPost


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
    mock_data = {
        "trending": [
            {"keyword": "AI regulation", "traffic": "500K+"},
            {"keyword": "chip tariffs", "traffic": "200K+"},
        ]
    }

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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd mirofish-osint && uv run pytest tests/test_collectors/test_news_reddit_clients.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement Google News/Trends client**

```python
# src/mcp_clients/news_trends.py
from src.mcp_clients.base import InternalMCPClient
from src.models.source_data import NewsHeadline, GoogleTrendsData


class NewsTrendsClient:
    def __init__(self):
        self._client = InternalMCPClient(
            command="uvx",
            args=["google-news-trends-mcp@latest"],
        )

    async def _call_tool(self, tool_name: str, arguments: dict) -> any:
        return await self._client.call_tool(tool_name, arguments)

    async def search_news(self, query: str) -> list[NewsHeadline]:
        try:
            data = await self._call_tool("get_news_by_keyword", {"keyword": query})
            if not isinstance(data, list):
                return []
            headlines = []
            for item in data:
                source_name = ""
                if isinstance(item.get("source"), dict):
                    source_name = item["source"].get("title", "")
                elif isinstance(item.get("source"), str):
                    source_name = item["source"]
                headlines.append(NewsHeadline(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    source=source_name,
                    date=item.get("published", ""),
                ))
            return headlines
        except Exception:
            return []

    async def get_trends(self, geo: str = "US") -> GoogleTrendsData | None:
        try:
            data = await self._call_tool("get_trending_keywords", {"geo": geo})
            if not isinstance(data, dict):
                return GoogleTrendsData()
            trending = data.get("trending", [])
            related = [item.get("keyword", "") for item in trending if isinstance(item, dict)]
            return GoogleTrendsData(related_queries=related)
        except Exception:
            return None
```

- [ ] **Step 4: Implement Reddit client**

```python
# src/mcp_clients/reddit.py
from src.mcp_clients.base import InternalMCPClient
from src.models.source_data import RedditPost


class RedditClient:
    def __init__(self):
        self._client = InternalMCPClient(
            command="uvx",
            args=["reddit-no-auth-mcp-server"],
        )

    async def _call_tool(self, tool_name: str, arguments: dict) -> any:
        return await self._client.call_tool(tool_name, arguments)

    async def search(self, query: str, limit: int = 10) -> list[RedditPost]:
        try:
            data = await self._call_tool("search_posts", {"query": query, "limit": limit, "sort": "relevance"})
            if not isinstance(data, list):
                return []
            posts = []
            for item in data:
                posts.append(RedditPost(
                    title=item.get("title", ""),
                    subreddit=item.get("subreddit", ""),
                    score=int(item.get("score", 0)),
                    num_comments=int(item.get("num_comments", 0)),
                    date=item.get("created_utc", ""),
                    url=item.get("url", ""),
                ))
            return posts
        except Exception:
            return []
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd mirofish-osint && uv run pytest tests/test_collectors/test_news_reddit_clients.py -v
```

Expected: All 5 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add mirofish-osint/src/mcp_clients/news_trends.py mirofish-osint/src/mcp_clients/reddit.py mirofish-osint/tests/test_collectors/test_news_reddit_clients.py
git commit -m "feat(osint): add Google News/Trends + Reddit MCP client wrappers"
```

---

### Task 9: Topic Analyzer (Orchestrator)

**Files:**
- Create: `mirofish-osint/src/orchestrator/topic_analyzer.py`
- Create: `mirofish-osint/tests/test_orchestrator/test_topic_analyzer.py`

- [ ] **Step 1: Write tests**

```python
# tests/test_orchestrator/test_topic_analyzer.py
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
        assert "financial" in result["categories"]
        assert result["source_weights"]["gdelt"] == 0.9


@pytest.mark.asyncio
async def test_analyze_topic_returns_defaults_on_error():
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("API error")

    with patch("src.orchestrator.topic_analyzer.genai.Client", return_value=mock_client):
        analyzer = TopicAnalyzer(api_key="test-key")
        result = await analyzer.analyze("test topic")

        assert "categories" in result
        assert "general" in result["categories"]
        assert "source_weights" in result
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd mirofish-osint && uv run pytest tests/test_orchestrator/test_topic_analyzer.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement topic analyzer**

```python
# src/orchestrator/topic_analyzer.py
import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from google import genai


DEFAULT_WEIGHTS = {
    "serper": 0.8,
    "gdelt": 0.7,
    "news_trends": 0.7,
    "reddit": 0.5,
    "wikipedia": 0.6,
    "gemini_grounding": 0.8,
}

PROMPT = """Classify this research topic and assign source weights for OSINT collection.

Topic: "{topic}"

Return JSON only, no markdown:
{{
  "categories": ["geopolitical", "financial", "tech", "social", "cultural"],  // pick relevant ones
  "source_weights": {{
    "serper": 0.0-1.0,
    "gdelt": 0.0-1.0,
    "news_trends": 0.0-1.0,
    "reddit": 0.0-1.0,
    "wikipedia": 0.0-1.0,
    "gemini_grounding": 0.0-1.0
  }}
}}

Guidelines:
- geopolitical/policy topics: weight gdelt and news_trends higher
- financial/company topics: weight serper higher (for SEC, earnings)
- tech topics: weight reddit and wikipedia higher
- social/cultural: weight reddit and news_trends higher
- Always keep serper and gemini_grounding >= 0.7"""


class TopicAnalyzer:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self._executor = ThreadPoolExecutor(max_workers=1)

    def _analyze_sync(self, topic: str) -> dict:
        client = genai.Client(api_key=self.api_key)
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=PROMPT.format(topic=topic),
        )
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(text)

    async def analyze(self, topic: str) -> dict:
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(self._executor, self._analyze_sync, topic)
        except Exception:
            return {"categories": ["general"], "source_weights": DEFAULT_WEIGHTS}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd mirofish-osint && uv run pytest tests/test_orchestrator/test_topic_analyzer.py -v
```

Expected: All 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add mirofish-osint/src/orchestrator/topic_analyzer.py mirofish-osint/tests/test_orchestrator/test_topic_analyzer.py
git commit -m "feat(osint): add Gemini-powered topic analyzer"
```

---

### Task 10: Source Router (Parallel Orchestrator)

**Files:**
- Create: `mirofish-osint/src/orchestrator/source_router.py`
- Create: `mirofish-osint/tests/test_orchestrator/test_source_router.py`

- [ ] **Step 1: Write tests**

```python
# tests/test_orchestrator/test_source_router.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.orchestrator.source_router import SourceRouter
from src.models.source_data import (
    CollectedSources, WebSearchResult, GdeltEvent,
    NewsHeadline, RedditPost, WikipediaData,
    GeminiGroundingData, GeminiDeepResearchData, ArticleData,
)


def _make_router():
    return SourceRouter(gemini_api_key="test-gemini", serper_api_key="test-serper")


@pytest.mark.asyncio
async def test_shallow_collection_uses_correct_sources():
    router = _make_router()

    with patch.object(router._serper, "search", new_callable=AsyncMock, return_value=[
        WebSearchResult(title="Result 1", url="https://example.com/1", snippet="test"),
    ]):
        with patch.object(router._news_trends, "search_news", new_callable=AsyncMock, return_value=[
            NewsHeadline(title="Headline 1", url="https://example.com/h1"),
        ]):
            with patch.object(router._news_trends, "get_trends", new_callable=AsyncMock, return_value=None):
                with patch.object(router._reddit, "search", new_callable=AsyncMock, return_value=[
                    RedditPost(title="Post 1", subreddit="test"),
                ]):
                    sources = await router.collect("test topic", depth="shallow")

                    assert isinstance(sources, CollectedSources)
                    assert len(sources.web_search) == 1
                    assert len(sources.news_headlines) == 1
                    assert len(sources.reddit_posts) == 1
                    # deep-only sources should be empty
                    assert len(sources.gdelt_events) == 0
                    assert sources.wikipedia is None
                    assert sources.gemini_grounding is None


@pytest.mark.asyncio
async def test_deep_collection_includes_all_sources():
    router = _make_router()

    with patch.object(router._serper, "search", new_callable=AsyncMock, return_value=[
        WebSearchResult(title="R1", url="https://example.com/1", snippet="t"),
    ]):
        with patch.object(router._news_trends, "search_news", new_callable=AsyncMock, return_value=[]):
            with patch.object(router._news_trends, "get_trends", new_callable=AsyncMock, return_value=None):
                with patch.object(router._reddit, "search", new_callable=AsyncMock, return_value=[]):
                    with patch.object(router._gdelt, "search", new_callable=AsyncMock, return_value=[
                        GdeltEvent(title="Event 1", url="https://example.com/e1"),
                    ]):
                        with patch.object(router._wikipedia, "get_summary", new_callable=AsyncMock, return_value=WikipediaData(summary="Test", url="https://wiki.org")):
                            with patch.object(router._gemini, "grounding_search", new_callable=AsyncMock, return_value=GeminiGroundingData(text="Grounded text")):
                                with patch.object(router._article_extractor, "extract_from_search_results", new_callable=AsyncMock, return_value=[]):
                                    sources = await router.collect("test topic", depth="deep")

                                    assert len(sources.gdelt_events) == 1
                                    assert sources.wikipedia is not None
                                    assert sources.gemini_grounding is not None


@pytest.mark.asyncio
async def test_collection_handles_source_failures():
    router = _make_router()

    with patch.object(router._serper, "search", new_callable=AsyncMock, side_effect=Exception("fail")):
        with patch.object(router._news_trends, "search_news", new_callable=AsyncMock, return_value=[
            NewsHeadline(title="H1", url="https://example.com"),
        ]):
            with patch.object(router._news_trends, "get_trends", new_callable=AsyncMock, return_value=None):
                with patch.object(router._reddit, "search", new_callable=AsyncMock, return_value=[]):
                    sources = await router.collect("test topic", depth="shallow")

                    # Should still have news results even though serper failed
                    assert len(sources.news_headlines) == 1
                    assert len(sources.web_search) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd mirofish-osint && uv run pytest tests/test_orchestrator/test_source_router.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement source router**

```python
# src/orchestrator/source_router.py
import asyncio
from src.collectors.serper import SerperCollector
from src.collectors.article_extractor import ArticleExtractorCollector
from src.collectors.wikipedia import WikipediaCollector
from src.collectors.gemini_research import GeminiResearchCollector
from src.mcp_clients.gdelt import GdeltClient
from src.mcp_clients.news_trends import NewsTrendsClient
from src.mcp_clients.reddit import RedditClient
from src.models.source_data import CollectedSources


class SourceRouter:
    def __init__(self, gemini_api_key: str, serper_api_key: str):
        self._serper = SerperCollector(api_key=serper_api_key)
        self._article_extractor = ArticleExtractorCollector()
        self._wikipedia = WikipediaCollector()
        self._gemini = GeminiResearchCollector(api_key=gemini_api_key)
        self._gdelt = GdeltClient()
        self._news_trends = NewsTrendsClient()
        self._reddit = RedditClient()

    async def _safe(self, coro, default=None):
        try:
            return await coro
        except Exception:
            return default

    async def collect(self, topic: str, depth: str = "shallow") -> CollectedSources:
        sources = CollectedSources()

        # Phase 1: parallel collection
        phase1_tasks = {
            "serper": self._safe(self._serper.search(topic), []),
            "news": self._safe(self._news_trends.search_news(topic), []),
            "trends": self._safe(self._news_trends.get_trends(), None),
            "reddit": self._safe(self._reddit.search(topic), []),
        }

        if depth in ("deep", "research"):
            phase1_tasks["gdelt"] = self._safe(self._gdelt.search(topic), [])
            phase1_tasks["wikipedia"] = self._safe(self._wikipedia.get_summary(topic), None)
            phase1_tasks["grounding"] = self._safe(self._gemini.grounding_search(topic), None)

        if depth == "research":
            phase1_tasks["deep_research"] = self._safe(
                self._gemini.deep_research(topic), None
            )

        keys = list(phase1_tasks.keys())
        results = await asyncio.gather(*phase1_tasks.values(), return_exceptions=True)
        phase1 = {}
        for key, result in zip(keys, results):
            phase1[key] = result if not isinstance(result, Exception) else None

        sources.web_search = phase1.get("serper") or []
        sources.news_headlines = phase1.get("news") or []
        sources.google_trends = phase1.get("trends")
        sources.reddit_posts = phase1.get("reddit") or []
        sources.gdelt_events = phase1.get("gdelt") or []
        sources.wikipedia = phase1.get("wikipedia")
        sources.gemini_grounding = phase1.get("grounding")
        sources.gemini_deep_research = phase1.get("deep_research")

        # Phase 2: article extraction (depends on serper results)
        if depth in ("deep", "research") and sources.web_search:
            articles = await self._safe(
                self._article_extractor.extract_from_search_results(sources.web_search), []
            )
            sources.articles = articles or []

        return sources
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd mirofish-osint && uv run pytest tests/test_orchestrator/test_source_router.py -v
```

Expected: All 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add mirofish-osint/src/orchestrator/source_router.py mirofish-osint/tests/test_orchestrator/test_source_router.py
git commit -m "feat(osint): add parallel source router with depth-based dispatch"
```

---

### Task 11: Normalizer

**Files:**
- Create: `mirofish-osint/src/orchestrator/normalizer.py`
- Create: `mirofish-osint/tests/test_orchestrator/test_normalizer.py`

- [ ] **Step 1: Write tests**

```python
# tests/test_orchestrator/test_normalizer.py
import pytest
from src.orchestrator.normalizer import Normalizer
from src.models.source_data import (
    CollectedSources, WebSearchResult, GdeltEvent,
    NewsHeadline, RedditPost, WikipediaData,
)
from src.models.research_result import Entity, TimelineEvent


def test_extract_entities_from_sources():
    sources = CollectedSources(
        web_search=[
            WebSearchResult(title="TSMC Plans New Factory in Arizona", url="https://example.com/1", snippet="TSMC is building a new semiconductor fab in Arizona, USA."),
            WebSearchResult(title="Intel Responds to TSMC Expansion", url="https://example.com/2", snippet="Intel CEO Pat Gelsinger comments on TSMC's Arizona plans."),
        ],
        gdelt_events=[
            GdeltEvent(title="TSMC Arizona Investment Confirmed", url="https://example.com/3", tone=2.5, date="20260325"),
        ],
    )

    normalizer = Normalizer()
    entities = normalizer.extract_entities(sources)

    # Should find TSMC mentioned across multiple sources
    names = [e.name for e in entities]
    assert len(entities) > 0
    # Entities are extracted by the synthesizer via Gemini; normalizer does basic frequency counting
    # from titles and snippets


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
    # Should be sorted chronologically
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd mirofish-osint && uv run pytest tests/test_orchestrator/test_normalizer.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement normalizer**

```python
# src/orchestrator/normalizer.py
import re
from src.models.source_data import CollectedSources
from src.models.research_result import Entity, TimelineEvent


class Normalizer:
    def extract_entities(self, sources: CollectedSources) -> list[Entity]:
        """Basic entity extraction by counting proper nouns across titles and snippets."""
        text_chunks = []
        source_map: dict[str, set[str]] = {}

        for item in sources.web_search:
            text_chunks.append((item.title + " " + item.snippet, "serper"))
        for item in sources.gdelt_events:
            text_chunks.append((item.title, "gdelt"))
        for item in sources.news_headlines:
            text_chunks.append((item.title, "news_trends"))
        for item in sources.reddit_posts:
            text_chunks.append((item.title, "reddit"))
        if sources.wikipedia:
            text_chunks.append((sources.wikipedia.summary[:500], "wikipedia"))

        # Simple capitalized word extraction (proper nouns)
        word_counts: dict[str, int] = {}
        for text, source_name in text_chunks:
            words = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", text)
            for word in words:
                if len(word) < 3:
                    continue
                word_counts[word] = word_counts.get(word, 0) + 1
                if word not in source_map:
                    source_map[word] = set()
                source_map[word].add(source_name)

        entities = []
        for name, count in sorted(word_counts.items(), key=lambda x: -x[1]):
            if count >= 2:  # mentioned at least twice
                entities.append(Entity(
                    name=name,
                    type="unknown",
                    mention_count=count,
                    sources=list(source_map.get(name, [])),
                ))
        return entities[:30]

    def build_timeline(self, sources: CollectedSources) -> list[TimelineEvent]:
        """Build chronological timeline from dated sources."""
        events = []

        for item in sources.gdelt_events:
            if item.date:
                normalized_date = item.date
                if len(normalized_date) == 8:  # YYYYMMDD format
                    normalized_date = f"{normalized_date[:4]}-{normalized_date[4:6]}-{normalized_date[6:8]}"
                events.append(TimelineEvent(
                    date=normalized_date,
                    event=item.title,
                    source="gdelt",
                    confidence="high" if abs(item.tone) > 2 else "medium",
                ))

        for item in sources.news_headlines:
            if item.date:
                events.append(TimelineEvent(
                    date=item.date,
                    event=item.title,
                    source="news_trends",
                    confidence="medium",
                ))

        events.sort(key=lambda e: e.date)
        return events

    def deduplicate(self, sources: CollectedSources) -> CollectedSources:
        """Remove duplicate entries based on URL."""
        seen_urls = set()

        deduped_web = []
        for item in sources.web_search:
            if item.url not in seen_urls:
                seen_urls.add(item.url)
                deduped_web.append(item)

        deduped_gdelt = []
        for item in sources.gdelt_events:
            if item.url not in seen_urls:
                seen_urls.add(item.url)
                deduped_gdelt.append(item)

        deduped_news = []
        for item in sources.news_headlines:
            if item.url not in seen_urls:
                seen_urls.add(item.url)
                deduped_news.append(item)

        sources.web_search = deduped_web
        sources.gdelt_events = deduped_gdelt
        sources.news_headlines = deduped_news
        return sources
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd mirofish-osint && uv run pytest tests/test_orchestrator/test_normalizer.py -v
```

Expected: All 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add mirofish-osint/src/orchestrator/normalizer.py mirofish-osint/tests/test_orchestrator/test_normalizer.py
git commit -m "feat(osint): add normalizer for dedup, entity extraction, timeline"
```

---

### Task 12: Synthesizer (Gemini Report Generation)

**Files:**
- Create: `mirofish-osint/src/orchestrator/synthesizer.py`
- Create: `mirofish-osint/tests/test_orchestrator/test_synthesizer.py`

- [ ] **Step 1: Write tests**

```python
# tests/test_orchestrator/test_synthesizer.py
import pytest
from unittest.mock import patch, MagicMock
from src.orchestrator.synthesizer import Synthesizer
from src.models.source_data import CollectedSources, WebSearchResult, GdeltEvent
from src.models.research_result import ResearchResult, Entity, TimelineEvent


@pytest.mark.asyncio
async def test_synthesize_mirofish_format():
    mock_response = MagicMock()
    mock_response.text = """# OSINT Intelligence Report: Test Topic

**Generated:** 2026-03-30T12:00:00Z
**Depth:** deep
**Sources:** 3/7 active
**Confidence:** Medium

## Executive Summary
Test summary about the topic.

## Key Entities

### People
- **John Doe** - CEO of TestCorp. Sources: [serper, gdelt]. Stance: neutral

### Organizations
- **TestCorp** - Tech company. Sources: [serper]

## Relationships
- John Doe **leads** TestCorp - as CEO (serper, confidence: high)

## Timeline
| Date | Event | Source | Confidence |
|------|-------|--------|------------|
| 2026-03-28 | Event A | gdelt | High |

## Current Situation (Last 7 Days)
Current developments.

## Public Sentiment Analysis
- Overall tone: neutral

## Emerging Signals & Weak Indicators
- Signal 1

## Source Confidence Matrix
| Source | Items | Status | Reliability |
|--------|-------|--------|-------------|
| serper | 2 | Active | High |

## Raw Sources
- [Test](https://example.com) - 2026-03-30, serper"""

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
            topic="Test Topic",
            depth="deep",
            sources=sources,
            entities=entities,
            timeline=timeline,
            output_format="mirofish",
        )

        assert "# OSINT Intelligence Report: Test Topic" in report
        assert "Key Entities" in report
        assert "Relationships" in report


@pytest.mark.asyncio
async def test_synthesize_returns_error_report_on_failure():
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("API error")

    with patch("src.orchestrator.synthesizer.genai.Client", return_value=mock_client):
        synthesizer = Synthesizer(api_key="test-key")
        sources = CollectedSources()

        report = await synthesizer.synthesize(
            topic="Test", depth="shallow", sources=sources,
            entities=[], timeline=[], output_format="general",
        )

        assert "Error" in report or "error" in report
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd mirofish-osint && uv run pytest tests/test_orchestrator/test_synthesizer.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement synthesizer**

```python
# src/orchestrator/synthesizer.py
import asyncio
from concurrent.futures import ThreadPoolExecutor
from google import genai
from google.genai import types
from src.models.source_data import CollectedSources
from src.models.research_result import Entity, TimelineEvent

MIROFISH_PROMPT = """You are an OSINT analyst producing a structured intelligence report optimized for entity and relationship extraction.

Topic: {topic}
Depth: {depth}

COLLECTED DATA:
{sources_json}

EXTRACTED ENTITIES (preliminary):
{entities_json}

TIMELINE (preliminary):
{timeline_json}

{deep_research_section}

Produce a report in this EXACT format:

# OSINT Intelligence Report: {topic}

**Generated:** {timestamp}
**Depth:** {depth}
**Sources:** {{active_count}}/{{total_count}} active
**Confidence:** {{overall_confidence}}

## Executive Summary
2-3 paragraphs summarizing the topic, current state, and significance.

## Key Entities

### People
- **Name** — Role/title, affiliation. Sources: [...]. Stance: supportive/opposed/neutral

### Organizations
- **Name** — Type, relevance. Sources: [...]

### Locations
- **Name** — Significance. Sources: [...]

## Relationships
- Entity A **relationship_type** Entity B — context (source, confidence: high/medium/low)

## Timeline
| Date | Event | Source | Confidence |
|------|-------|--------|------------|
(fill from collected data, chronological order)

## Current Situation (Last 7 Days)
What is happening right now, sourced and cited.

## Public Sentiment Analysis
- Overall tone, media narrative, public reaction, trend direction

## Emerging Signals & Weak Indicators
- Weak signals with source and confidence

## Source Confidence Matrix
| Source | Items | Status | Reliability |
|--------|-------|--------|-------------|
(fill from actual collected data)

## Raw Sources
- [Title](URL) — date, source

RULES:
- Cross-reference facts across sources. Higher confidence = more sources agree.
- Extract ALL entities (people, orgs, locations) with their roles and relationships.
- Flag contradictions between sources.
- Be specific and factual. Cite sources for every claim.
- Maximize entity and relationship density — this report feeds into an agent simulation engine."""

GENERAL_PROMPT = """You are an OSINT analyst producing a comprehensive research report.

Topic: {topic}
Depth: {depth}

COLLECTED DATA:
{sources_json}

{deep_research_section}

Write a well-structured, narrative research report covering:
1. Executive summary
2. Background context
3. Current situation
4. Key players and stakeholders
5. Public sentiment
6. Outlook and emerging trends
7. Sources

Be factual, cite sources, and highlight areas of uncertainty."""


class Synthesizer:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self._executor = ThreadPoolExecutor(max_workers=1)

    def _synthesize_sync(
        self,
        topic: str,
        depth: str,
        sources: CollectedSources,
        entities: list[Entity],
        timeline: list[TimelineEvent],
        output_format: str,
    ) -> str:
        from datetime import datetime, timezone

        sources_json = sources.model_dump_json(indent=2)
        entities_json = "[" + ", ".join(e.model_dump_json() for e in entities) + "]"
        timeline_json = "[" + ", ".join(t.model_dump_json() for t in timeline) + "]"
        timestamp = datetime.now(timezone.utc).isoformat()

        deep_research_section = ""
        if sources.gemini_deep_research:
            deep_research_section = f"DEEP RESEARCH REPORT:\n{sources.gemini_deep_research.report}"

        if output_format == "mirofish":
            prompt = MIROFISH_PROMPT.format(
                topic=topic,
                depth=depth,
                sources_json=sources_json[:15000],
                entities_json=entities_json[:3000],
                timeline_json=timeline_json[:3000],
                timestamp=timestamp,
                deep_research_section=deep_research_section[:5000],
            )
        else:
            prompt = GENERAL_PROMPT.format(
                topic=topic,
                depth=depth,
                sources_json=sources_json[:15000],
                deep_research_section=deep_research_section[:5000],
            )

        client = genai.Client(api_key=self.api_key)
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            ),
        )
        return response.text

    async def synthesize(
        self,
        topic: str,
        depth: str,
        sources: CollectedSources,
        entities: list[Entity],
        timeline: list[TimelineEvent],
        output_format: str = "mirofish",
    ) -> str:
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self._executor,
                self._synthesize_sync,
                topic, depth, sources, entities, timeline, output_format,
            )
        except Exception as e:
            return f"# Error Generating Report\n\nSynthesis failed: {e}\n\nRaw data was collected but could not be synthesized."
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd mirofish-osint && uv run pytest tests/test_orchestrator/test_synthesizer.py -v
```

Expected: All 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add mirofish-osint/src/orchestrator/synthesizer.py mirofish-osint/tests/test_orchestrator/test_synthesizer.py
git commit -m "feat(osint): add Gemini synthesizer with MiroFish report template"
```

---

### Task 13: Wire Up MCP Tools (research_raw, research_and_synthesize, list_sources)

**Files:**
- Create: `mirofish-osint/src/tools/research_raw.py`
- Create: `mirofish-osint/src/tools/research_synthesize.py`
- Create: `mirofish-osint/src/tools/list_sources.py`
- Modify: `mirofish-osint/src/server.py`

- [ ] **Step 1: Implement list_sources tool**

```python
# src/tools/list_sources.py
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
```

- [ ] **Step 2: Implement research_raw tool**

```python
# src/tools/research_raw.py
import os
from datetime import datetime, timezone
from src.orchestrator.topic_analyzer import TopicAnalyzer
from src.orchestrator.source_router import SourceRouter
from src.orchestrator.normalizer import Normalizer
from src.models.research_result import ResearchResult


async def research_raw(topic: str, depth: str = "shallow") -> dict:
    gemini_key = os.environ["GEMINI_API_KEY"]
    serper_key = os.environ["SERPER_API_KEY"]

    analyzer = TopicAnalyzer(api_key=gemini_key)
    router = SourceRouter(gemini_api_key=gemini_key, serper_api_key=serper_key)
    normalizer = Normalizer()

    classification = await analyzer.analyze(topic)
    sources = await router.collect(topic, depth=depth)
    sources = normalizer.deduplicate(sources)
    entities = normalizer.extract_entities(sources)
    timeline = normalizer.build_timeline(sources)

    result = ResearchResult(
        topic=topic,
        topic_classification=classification.get("categories", ["general"]),
        collected_at=datetime.now(timezone.utc).isoformat(),
        sources=sources,
        entities=entities,
        timeline=timeline,
    )
    return result.model_dump()
```

- [ ] **Step 3: Implement research_and_synthesize tool**

```python
# src/tools/research_synthesize.py
import os
from datetime import datetime, timezone
from src.orchestrator.topic_analyzer import TopicAnalyzer
from src.orchestrator.source_router import SourceRouter
from src.orchestrator.normalizer import Normalizer
from src.orchestrator.synthesizer import Synthesizer


async def research_and_synthesize(
    topic: str,
    depth: str = "shallow",
    output_format: str = "mirofish",
) -> str:
    gemini_key = os.environ["GEMINI_API_KEY"]
    serper_key = os.environ["SERPER_API_KEY"]

    analyzer = TopicAnalyzer(api_key=gemini_key)
    router = SourceRouter(gemini_api_key=gemini_key, serper_api_key=serper_key)
    normalizer = Normalizer()
    synthesizer = Synthesizer(api_key=gemini_key)

    classification = await analyzer.analyze(topic)
    sources = await router.collect(topic, depth=depth)
    sources = normalizer.deduplicate(sources)
    entities = normalizer.extract_entities(sources)
    timeline = normalizer.build_timeline(sources)

    report = await synthesizer.synthesize(
        topic=topic,
        depth=depth,
        sources=sources,
        entities=entities,
        timeline=timeline,
        output_format=output_format,
    )
    return report
```

- [ ] **Step 4: Update server.py to wire everything together**

```python
# src/server.py
import os
from typing import Literal
from dotenv import load_dotenv
from fastmcp import FastMCP

# Load .env from project root
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

mcp = FastMCP("MiroFish OSINT")


@mcp.tool
async def research_raw(
    topic: str,
    depth: Literal["shallow", "deep", "research"] = "shallow",
) -> dict:
    """Gather OSINT data on any topic from multiple sources. Returns structured JSON with all collected data.

    Args:
        topic: The research subject (e.g., "US chip tariff impact on TSMC")
        depth: shallow (latest, fast), deep (all sources + grounding), research (everything + Gemini Deep Research)
    """
    from src.tools.research_raw import research_raw as _research_raw
    return await _research_raw(topic, depth)


@mcp.tool
async def research_and_synthesize(
    topic: str,
    depth: Literal["shallow", "deep", "research"] = "shallow",
    output_format: Literal["mirofish", "general"] = "mirofish",
) -> str:
    """Research any topic and synthesize a structured OSINT report via Gemini.

    Args:
        topic: The research subject (e.g., "US chip tariff impact on TSMC")
        depth: shallow (latest, fast), deep (all sources + grounding), research (everything + Gemini Deep Research)
        output_format: mirofish (entity-dense, for MiroFish ingestion) or general (narrative, for human reading)
    """
    from src.tools.research_synthesize import research_and_synthesize as _synthesize
    return await _synthesize(topic, depth, output_format)


@mcp.tool
def list_sources() -> list[dict]:
    """List available OSINT data sources and their current status."""
    from src.tools.list_sources import get_sources
    return get_sources()


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8080)
```

- [ ] **Step 5: Verify server starts and tools are registered**

```bash
cd mirofish-osint && uv run python src/server.py
```

Expected: Server starts on port 8080 with 3 tools registered.

- [ ] **Step 6: Commit**

```bash
git add mirofish-osint/src/tools/ mirofish-osint/src/server.py
git commit -m "feat(osint): wire up all MCP tools (research_raw, research_and_synthesize, list_sources)"
```

---

### Task 14: Docker Container

**Files:**
- Create: `mirofish-osint/Dockerfile`
- Create: `mirofish-osint/docker-compose.yml`

- [ ] **Step 1: Create Dockerfile**

```dockerfile
# mirofish-osint/Dockerfile
FROM python:3.12-slim

# Install Node.js 20 (for mcp-gdelt)
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy project files
COPY pyproject.toml .
COPY src/ src/

# Install Python dependencies
RUN uv sync --no-dev

# Pre-install internal MCP servers
RUN uv tool install google-news-trends-mcp
RUN uv tool install reddit-no-auth-mcp-server
RUN npx -y @missionsquad/mcp-gdelt --help || true

EXPOSE 8080

CMD ["uv", "run", "python", "src/server.py"]
```

- [ ] **Step 2: Create docker-compose.yml**

```yaml
# mirofish-osint/docker-compose.yml
services:
  mirofish-osint:
    build: .
    ports:
      - "8080:8080"
    env_file: .env
    restart: unless-stopped
```

- [ ] **Step 3: Create .dockerignore**

```
# mirofish-osint/.dockerignore
.env
.venv
__pycache__
*.pyc
tests/
internal_servers/
.git
```

- [ ] **Step 4: Build and test Docker image**

```bash
cd mirofish-osint && docker compose build
```

Expected: Image builds successfully.

- [ ] **Step 5: Commit**

```bash
git add mirofish-osint/Dockerfile mirofish-osint/docker-compose.yml mirofish-osint/.dockerignore
git commit -m "feat(osint): add Docker container with all internal MCP servers"
```

---

### Task 15: Integration Test (End-to-End)

**Files:**
- Create: `mirofish-osint/tests/test_integration/test_e2e.py`

- [ ] **Step 1: Write integration test**

```python
# tests/test_integration/test_e2e.py
"""
End-to-end integration tests.
These tests call real APIs and require GEMINI_API_KEY and SERPER_API_KEY in .env.
Run with: uv run pytest tests/test_integration/ -v -s
"""
import os
import pytest

# Skip if no API keys
pytestmark = pytest.mark.skipif(
    not os.environ.get("GEMINI_API_KEY") or not os.environ.get("SERPER_API_KEY"),
    reason="API keys not set",
)


@pytest.fixture(autouse=True)
def load_env():
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))


@pytest.mark.asyncio
async def test_research_raw_shallow():
    from src.tools.research_raw import research_raw

    result = await research_raw("Bitcoin price 2026", depth="shallow")

    assert result["topic"] == "Bitcoin price 2026"
    assert len(result["topic_classification"]) > 0
    assert result["collected_at"] != ""
    # Should have at least some web search results
    assert len(result["sources"]["web_search"]) > 0


@pytest.mark.asyncio
async def test_research_and_synthesize_shallow():
    from src.tools.research_synthesize import research_and_synthesize

    report = await research_and_synthesize(
        "Bitcoin price 2026", depth="shallow", output_format="mirofish"
    )

    assert isinstance(report, str)
    assert len(report) > 100
    assert "Bitcoin" in report


@pytest.mark.asyncio
async def test_list_sources():
    from src.tools.list_sources import get_sources

    sources = get_sources()

    assert len(sources) == 8
    assert sources[0]["name"] == "serper"
    assert sources[0]["status"] == "active"
```

- [ ] **Step 2: Run unit tests (all should pass)**

```bash
cd mirofish-osint && uv run pytest tests/ --ignore=tests/test_integration -v
```

Expected: All unit tests PASS.

- [ ] **Step 3: Run integration tests (requires API keys)**

```bash
cd mirofish-osint && uv run pytest tests/test_integration/ -v -s
```

Expected: All 3 integration tests PASS (calls real Serper + Gemini APIs).

- [ ] **Step 4: Commit**

```bash
git add mirofish-osint/tests/test_integration/
git commit -m "test(osint): add end-to-end integration tests"
```

---

### Task 16: Final Polish & README

**Files:**
- Create: `mirofish-osint/README.md`

- [ ] **Step 1: Create README**

```markdown
# MiroFish OSINT

An OSINT (Open Source Intelligence) research agent MCP server that gathers data from multiple sources and synthesizes reports via Gemini. Designed to produce MiroFish-compatible seed material.

## Quick Start

1. Copy `.env.example` to `.env` and add your API keys:
   - `GEMINI_API_KEY` — from [Google AI Studio](https://aistudio.google.com/)
   - `SERPER_API_KEY` — from [serper.dev](https://serper.dev) (2,500 free/month)

2. Run with Docker:
   ```bash
   docker compose up
   ```

   Or run locally:
   ```bash
   uv sync
   uv run python src/server.py
   ```

3. Connect any MCP client to `http://localhost:8080/mcp`

## MCP Tools

### `research_raw`
Gather raw OSINT data. Returns structured JSON.
- `topic` (string) — research subject
- `depth` — `shallow` | `deep` | `research`

### `research_and_synthesize`
Research + Gemini synthesis. Returns markdown report.
- `topic` (string) — research subject
- `depth` — `shallow` | `deep` | `research`
- `output_format` — `mirofish` | `general`

### `list_sources`
List available data sources and their status.

## Depth Modes

| Mode | Sources | Latency |
|------|---------|---------|
| `shallow` | Serper + News/Trends + Reddit | ~10-15s |
| `deep` | All + Gemini Grounding + articles + Wikipedia | ~30-60s |
| `research` | Everything + Gemini Deep Research Agent | ~2-10 min |

## Data Sources

- **Serper** — Web search (2,500 free/month)
- **GDELT** — Global news events, 65 languages, 3-month rolling (free)
- **Google News/Trends** — Headlines + trending topics (free, RSS-based)
- **Reddit** — Posts and discussions (free, zero auth)
- **Wikipedia** — Background context (free)
- **newspaper4k** — Full article text extraction
- **Gemini Search Grounding** — Google Search via Gemini API
- **Gemini Deep Research** — Autonomous deep research agent
```

- [ ] **Step 2: Run full test suite**

```bash
cd mirofish-osint && uv run pytest tests/ -v
```

Expected: All tests PASS.

- [ ] **Step 3: Commit**

```bash
git add mirofish-osint/README.md
git commit -m "docs(osint): add README with quickstart and tool documentation"
```

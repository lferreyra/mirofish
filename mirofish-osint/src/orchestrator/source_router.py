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
            phase1_tasks["deep_research"] = self._safe(self._gemini.deep_research(topic), None)

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

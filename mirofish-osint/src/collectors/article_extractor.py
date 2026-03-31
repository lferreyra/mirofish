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

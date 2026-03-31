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

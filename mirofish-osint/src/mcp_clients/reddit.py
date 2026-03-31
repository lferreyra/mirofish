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

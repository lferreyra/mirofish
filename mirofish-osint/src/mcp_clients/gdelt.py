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

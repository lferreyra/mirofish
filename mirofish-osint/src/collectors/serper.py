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

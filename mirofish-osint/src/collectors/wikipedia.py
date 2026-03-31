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

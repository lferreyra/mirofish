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

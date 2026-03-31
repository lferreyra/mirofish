import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from google import genai


DEFAULT_WEIGHTS = {
    "serper": 0.8, "gdelt": 0.7, "news_trends": 0.7,
    "reddit": 0.5, "wikipedia": 0.6, "gemini_grounding": 0.8,
}

PROMPT = """Classify this research topic and assign source weights for OSINT collection.

Topic: "{topic}"

Return JSON only, no markdown:
{{
  "categories": ["geopolitical", "financial", "tech", "social", "cultural"],
  "source_weights": {{
    "serper": 0.0-1.0, "gdelt": 0.0-1.0, "news_trends": 0.0-1.0,
    "reddit": 0.0-1.0, "wikipedia": 0.0-1.0, "gemini_grounding": 0.0-1.0
  }}
}}

Guidelines:
- geopolitical/policy: weight gdelt and news_trends higher
- financial/company: weight serper higher
- tech: weight reddit and wikipedia higher
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

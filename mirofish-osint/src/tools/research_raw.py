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

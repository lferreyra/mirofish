import os
from src.orchestrator.topic_analyzer import TopicAnalyzer
from src.orchestrator.source_router import SourceRouter
from src.orchestrator.normalizer import Normalizer
from src.orchestrator.synthesizer import Synthesizer


async def research_and_synthesize(
    topic: str, depth: str = "shallow", output_format: str = "mirofish",
) -> str:
    gemini_key = os.environ["GEMINI_API_KEY"]
    serper_key = os.environ["SERPER_API_KEY"]

    analyzer = TopicAnalyzer(api_key=gemini_key)
    router = SourceRouter(gemini_api_key=gemini_key, serper_api_key=serper_key)
    normalizer = Normalizer()
    synthesizer = Synthesizer(api_key=gemini_key)

    classification = await analyzer.analyze(topic)
    sources = await router.collect(topic, depth=depth)
    sources = normalizer.deduplicate(sources)
    entities = normalizer.extract_entities(sources)
    timeline = normalizer.build_timeline(sources)

    report = await synthesizer.synthesize(
        topic=topic, depth=depth, sources=sources,
        entities=entities, timeline=timeline, output_format=output_format,
    )
    return report

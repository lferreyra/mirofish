import asyncio
from concurrent.futures import ThreadPoolExecutor
from google import genai
from google.genai import types
from src.models.source_data import CollectedSources
from src.models.research_result import Entity, TimelineEvent

MIROFISH_PROMPT = """You are an OSINT analyst producing a structured intelligence report optimized for entity and relationship extraction.

Topic: {topic}
Depth: {depth}

COLLECTED DATA:
{sources_json}

EXTRACTED ENTITIES (preliminary):
{entities_json}

TIMELINE (preliminary):
{timeline_json}

{deep_research_section}

Produce a report in this EXACT format:

# OSINT Intelligence Report: {topic}

**Generated:** {timestamp}
**Depth:** {depth}
**Sources:** (count active sources)/(total) active
**Confidence:** (overall assessment)

## Executive Summary
2-3 paragraphs summarizing the topic, current state, and significance.

## Key Entities

### People
- **Name** — Role/title, affiliation. Sources: [...]. Stance: supportive/opposed/neutral

### Organizations
- **Name** — Type, relevance. Sources: [...]

### Locations
- **Name** — Significance. Sources: [...]

## Relationships
- Entity A **relationship_type** Entity B — context (source, confidence: high/medium/low)

## Timeline
| Date | Event | Source | Confidence |
|------|-------|--------|------------|

## Current Situation (Last 7 Days)
What is happening right now, sourced and cited.

## Public Sentiment Analysis
- Overall tone, media narrative, public reaction, trend direction

## Emerging Signals & Weak Indicators
- Weak signals with source and confidence

## Source Confidence Matrix
| Source | Items | Status | Reliability |
|--------|-------|--------|-------------|

## Raw Sources
- [Title](URL) — date, source

RULES:
- Cross-reference facts across sources. Higher confidence = more sources agree.
- Extract ALL entities (people, orgs, locations) with their roles and relationships.
- Flag contradictions between sources.
- Be specific and factual. Cite sources for every claim.
- Maximize entity and relationship density."""

GENERAL_PROMPT = """You are an OSINT analyst producing a comprehensive research report.

Topic: {topic}
Depth: {depth}

COLLECTED DATA:
{sources_json}

{deep_research_section}

Write a well-structured, narrative research report covering:
1. Executive summary
2. Background context
3. Current situation
4. Key players and stakeholders
5. Public sentiment
6. Outlook and emerging trends
7. Sources

Be factual, cite sources, and highlight areas of uncertainty."""


class Synthesizer:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self._executor = ThreadPoolExecutor(max_workers=1)

    def _synthesize_sync(self, topic, depth, sources, entities, timeline, output_format):
        from datetime import datetime, timezone
        sources_json = sources.model_dump_json(indent=2)
        entities_json = "[" + ", ".join(e.model_dump_json() for e in entities) + "]"
        timeline_json = "[" + ", ".join(t.model_dump_json() for t in timeline) + "]"
        timestamp = datetime.now(timezone.utc).isoformat()

        deep_research_section = ""
        if sources.gemini_deep_research:
            deep_research_section = f"DEEP RESEARCH REPORT:\n{sources.gemini_deep_research.report}"

        if output_format == "mirofish":
            prompt = MIROFISH_PROMPT.format(
                topic=topic, depth=depth,
                sources_json=sources_json[:15000],
                entities_json=entities_json[:3000],
                timeline_json=timeline_json[:3000],
                timestamp=timestamp,
                deep_research_section=deep_research_section[:5000],
            )
        else:
            prompt = GENERAL_PROMPT.format(
                topic=topic, depth=depth,
                sources_json=sources_json[:15000],
                deep_research_section=deep_research_section[:5000],
            )

        client = genai.Client(api_key=self.api_key)
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            ),
        )
        return response.text

    async def synthesize(self, topic, depth, sources, entities, timeline, output_format="mirofish"):
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self._executor, self._synthesize_sync,
                topic, depth, sources, entities, timeline, output_format,
            )
        except Exception as e:
            return f"# Error Generating Report\n\nSynthesis failed: {e}\n\nRaw data was collected but could not be synthesized."

# OSINT Research Agent MCP Server — Design Spec

**Date:** 2026-03-30
**Status:** Approved
**Author:** Remon + Claude

## 1. Overview

A standalone MCP server that gathers OSINT (Open Source Intelligence) data on any topic from multiple sources, normalizes and cross-references the data, and synthesizes it into a structured report via Gemini. Designed to produce MiroFish-compatible seed material, but usable standalone by any MCP client.

### Goals

- **General-purpose topic research** — works for geopolitical, financial, tech, social, cultural topics
- **Latest + historical** — not just headlines, but event timelines and background context
- **MiroFish-optimized output** — entity-dense, relationship-explicit reports that maximize entity/relationship extraction quality
- **Zero-config for users** — single `docker compose up`, two API keys (Gemini + Serper)
- **Graceful degradation** — no single source failure breaks the pipeline

## 2. Architecture

### MCP Gateway Pattern

A single Docker container exposes one MCP server (our gateway) on port 8080. Internally, it orchestrates 3 bundled MCP servers (via stdio subprocess) plus 4 native Python collectors.

```
Docker Container: mirofish-osint (:8080)
├── OSINT Gateway MCP Server (Python, FastMCP, exposed)
│   ├── Topic Analyzer (Gemini)
│   ├── Source Orchestrator (parallel async dispatch)
│   ├── Normalizer (dedup, entity extraction, timeline)
│   └── Synthesizer (Gemini + grounding)
│
├── Internal MCP Servers (stdio subprocesses, not exposed)
│   ├── mcp-gdelt (Node.js) — GDELT DOC 2.0 API, 65 languages, 3-month rolling
│   ├── google-news-trends-mcp (Python) — Google News RSS + Google Trends
│   └── reddit-no-auth-mcp (Python) — Reddit search, zero auth
│
└── Built-in Collectors (native Python, no MCP)
    ├── Serper — web search (2,500 free/month)
    ├── newspaper4k — full article text extraction from URLs
    ├── wikipedia-api — background context & key entities
    └── gemini_research — Search Grounding + Deep Research Agent
```

### Key Decisions

- Internal MCP servers communicate via **stdio** (fast, no network overhead)
- Serper, newspaper4k, wikipedia are **direct Python calls** — too simple to warrant MCP wrappers
- Internal servers start **lazily** on first request, stay alive for connection pooling
- If an internal server crashes, it restarts on next request
- Single container, single `docker compose up`, single `.env` file

## 3. Exposed MCP Tools

### Tool 1: `research_raw`

Returns structured JSON with all collected data, no synthesis.

**Input:**
- `topic` (string, required) — the research subject
- `depth` ("shallow" | "deep" | "research") — controls which sources are used

**Output (JSON):**
```json
{
  "topic": "US chip tariff impact on TSMC",
  "topic_classification": ["geopolitical", "financial", "tech"],
  "collected_at": "2026-03-30T12:00:00Z",
  "sources": {
    "web_search": [{ "title": "", "url": "", "snippet": "", "date": "", "relevance_score": 0.0 }],
    "articles": [{ "title": "", "url": "", "full_text": "", "date": "", "source_name": "" }],
    "gdelt_events": [{ "title": "", "url": "", "tone": 0.0, "date": "", "source_country": "" }],
    "news_headlines": [{ "title": "", "url": "", "source": "", "date": "", "category": "" }],
    "google_trends": { "interest_over_time": {}, "related_queries": [], "geographic": {} },
    "reddit_posts": [{ "title": "", "subreddit": "", "score": 0, "num_comments": 0, "date": "", "url": "" }],
    "wikipedia": { "summary": "", "key_entities": [], "url": "" },
    "gemini_grounding": { "text": "", "citations": [], "search_queries": [] },
    "gemini_deep_research": { "report": "", "status": "" }
  },
  "entities": [{ "name": "", "type": "", "mention_count": 0, "sources": [] }],
  "timeline": [{ "date": "", "event": "", "source": "", "confidence": "" }]
}
```

### Tool 2: `research_and_synthesize`

Returns a Gemini-synthesized markdown report.

**Input:**
- `topic` (string, required)
- `depth` ("shallow" | "deep" | "research")
- `output_format` ("mirofish" | "general") — mirofish optimizes for entity extraction

**Output:** Markdown string (see Section 6 for template).

### Tool 3: `list_sources`

**Input:** none
**Output:** Array of `{ name, status: "active"|"degraded"|"down", description }`

## 4. Depth Modes

| Mode | Sources Used | Latency | Cost |
|------|-------------|---------|------|
| `shallow` | Serper + News/Trends + Reddit | ~10-15s | ~$0.01 |
| `deep` | All OSINT collectors + Gemini Search Grounding + article extraction + Wikipedia | ~30-60s | ~$0.03 |
| `research` | Everything + Gemini Deep Research Agent (async, polled) | ~2-10 min | ~$0.10-0.30 |

### Source Matrix by Depth

| Source | shallow | deep | research |
|--------|---------|------|----------|
| Serper web search | Y | Y | Y |
| Google News/Trends MCP | Y | Y | Y |
| Reddit MCP | Y | Y | Y |
| GDELT MCP | - | Y | Y |
| Wikipedia | - | Y | Y |
| newspaper4k (article extraction) | - | Y | Y |
| Gemini Search Grounding | - | Y | Y |
| Gemini Deep Research Agent | - | - | Y |

## 5. Data Flow

```
research_and_synthesize(topic, depth, output_format)
    │
    ├─ 1. Topic Analyzer (Gemini, ~1-2s)
    │     Classifies topic → assigns source weights
    │
    ├─ 2a. Parallel Collection — Phase 1 (asyncio.gather)
    │     ├─ Serper → top 10 results (needed by Phase 2)
    │     ├─ mcp-gdelt (stdio) → events matching topic
    │     ├─ google-news-trends-mcp (stdio) → headlines + trend curve
    │     ├─ reddit-no-auth-mcp (stdio) → top posts
    │     ├─ wikipedia-api → background summary
    │     ├─ Gemini Search Grounding → grounded summary + citations
    │     └─ Gemini Deep Research Agent → started in background (research mode only)
    │     All run in parallel. Failures return gracefully.
    │
    ├─ 2b. Phase 2 (depends on Serper results)
    │     ├─ newspaper4k → full text from top 5 Serper URLs
    │     └─ Gemini Deep Research Agent → continue polling (research mode)
    │
    ├─ 3. Normalizer
    │     ├─ Deduplicate across sources
    │     ├─ Extract entities (people, orgs, locations)
    │     ├─ Build chronological timeline
    │     └─ Assign confidence scores (more sources = higher confidence)
    │
    └─ 4. Synthesizer (Gemini + Search Grounding)
          ├─ Cross-reference all sources
          ├─ Produce structured markdown report
          └─ Optimize entity/relationship density for MiroFish
```

### Error Handling

- Each collector runs independently inside `asyncio.gather(return_exceptions=True)`
- Failed sources return `None`, are flagged as `"degraded"` in output
- Pipeline continues with remaining sources — never blocks
- `list_sources` tool reflects current health status

## 6. Gemini Integration

Gemini serves 4 distinct roles:

### Role 1: Topic Analyzer (all depths)
- Quick classification call, no grounding
- Input: topic string
- Output: categories + source weights JSON
- Model: `gemini-3-flash-preview`, ~1-2s

### Role 2: Search Grounding (deep + research)
- Uses `google_search` tool in Gemini API
- Returns grounded summary + citations + web results
- Complements Serper — different search index, different results
- Model: `gemini-3-flash-preview`

### Role 3: Deep Research Agent (research only)
- Agent: `deep-research-pro-preview-12-2025`
- Async: starts in background, polled every 10s
- Runs in parallel with all other collectors
- Returns full research report or `None` on failure/timeout
- Timeout: 10 minutes max

### Role 4: Synthesizer (all depths, final step)
- Takes all normalized data + optional deep research report
- Produces structured markdown per output_format template
- Search Grounding enabled during synthesis for additional fact-checking
- Model: `gemini-3-flash-preview`

## 7. MiroFish Report Template

```markdown
# OSINT Intelligence Report: {topic}

**Generated:** {timestamp}
**Depth:** {depth}
**Sources:** {active_count}/{total_count} active
**Confidence:** {overall_confidence}

## Executive Summary
2-3 paragraph overview.

## Key Entities

### People
- **Name** — Role/title, affiliation. Sources: [...]. Stance: supportive/opposed/neutral

### Organizations
- **Name** — Type, relevance. Sources: [...]

### Locations
- **Name** — Significance. Sources: [...]

## Relationships
- Entity A **relationship_type** Entity B — context (source, confidence)

## Timeline
| Date | Event | Source | Confidence |
|------|-------|--------|------------|

## Current Situation (Last 7 Days)
Sourced and cited current developments.

## Public Sentiment Analysis
- Overall tone, media narrative, public reaction, trend direction

## Emerging Signals & Weak Indicators
- Weak signals with source and confidence

## Source Confidence Matrix
| Source | Items | Status | Reliability |
|--------|-------|--------|-------------|

## Raw Sources
- [Title](URL) — date, source
```

This template maximizes MiroFish entity/relationship extraction:
- Explicit entity sections with types → maps to `entity_types`
- Explicit relationships with named edges → maps to `edge_types`
- Stance/sentiment per entity → richer agent persona generation
- Timeline → better `event_config` in simulation

`output_format="general"` uses the same structure but more narrative, less rigid.

## 8. Project Structure

```
mirofish-osint/
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── pyproject.toml
│
├── src/
│   ├── server.py                     # MCP server entry (FastMCP, streamable HTTP)
│   │
│   ├── tools/                        # Exposed MCP tools
│   │   ├── research_raw.py
│   │   ├── research_synthesize.py
│   │   └── list_sources.py
│   │
│   ├── orchestrator/
│   │   ├── topic_analyzer.py         # Gemini topic classification
│   │   ├── source_router.py          # Parallel async dispatch
│   │   ├── normalizer.py             # Dedup, entity extraction, timeline
│   │   └── synthesizer.py            # Gemini synthesis → report
│   │
│   ├── collectors/                   # Native Python collectors
│   │   ├── serper.py                 # Serper web search API
│   │   ├── article_extractor.py      # newspaper4k full-text
│   │   ├── wikipedia.py              # wikipedia-api
│   │   └── gemini_research.py        # Grounding + Deep Research Agent
│   │
│   ├── mcp_clients/                  # Internal MCP server wrappers
│   │   ├── base.py                   # Shared stdio MCP client
│   │   ├── gdelt.py                  # mcp-gdelt wrapper
│   │   ├── news_trends.py            # google-news-trends-mcp wrapper
│   │   └── reddit.py                 # reddit-no-auth-mcp wrapper
│   │
│   └── models/                       # Pydantic data types
│       ├── research_result.py        # Tool output models
│       └── source_data.py            # Normalized source data
│
├── internal_servers/                 # Vendored or git submodules
│   ├── mcp-gdelt/
│   ├── google-news-trends-mcp/
│   └── reddit-no-auth-mcp/
│
└── tests/
    ├── test_collectors/
    ├── test_orchestrator/
    └── test_integration/
```

## 9. Configuration

### .env.example

```env
# Required
GEMINI_API_KEY=your_gemini_key
SERPER_API_KEY=your_serper_key

# Optional (for future MiroFish auto-feed)
# MIROFISH_API_URL=http://localhost:5001
```

### Docker Compose

```yaml
services:
  mirofish-osint:
    build: .
    ports:
      - "8080:8080"
    env_file: .env
```

Internal MCP servers run as stdio subprocesses inside the container — no separate services needed.

## 10. Internal MCP Server Communication

- Servers spawn lazily on first request via `asyncio.create_subprocess_exec`
- Communicate over stdin/stdout using MCP SDK client
- Stay alive for connection pooling across requests
- Health-checked via `list_sources` tool
- Auto-restart on crash (next request triggers respawn)

## 11. Dependencies

### Python (our gateway)
- `fastmcp` — MCP server framework
- `mcp` — MCP SDK client (for internal server communication)
- `google-genai` — Gemini API (grounding + deep research + synthesis)
- `httpx` — async HTTP for Serper API
- `newspaper4k` — article text extraction
- `wikipedia-api` — Wikipedia summaries
- `pydantic` — data validation

### Internal MCP Servers
- `mcp-gdelt` (Node.js) — requires `node` + `npm` in container
- `google-news-trends-mcp` (Python) — runs via `uvx`
- `reddit-no-auth-mcp` (Python) — runs via `uvx`

### Dockerfile Requirements
- Python 3.12
- Node.js 20+ (for mcp-gdelt)
- uv (Python package manager)

## 12. Future: MiroFish Integration

Not in scope for v1, but designed for:

- Add `MIROFISH_API_URL` to `.env`
- New tool: `research_and_simulate(topic, depth)` that:
  1. Runs `research_and_synthesize`
  2. Saves report as temp markdown file
  3. Calls MiroFish `POST /api/graph/ontology/generate` with the file
  4. Returns project_id for user to continue in MiroFish UI

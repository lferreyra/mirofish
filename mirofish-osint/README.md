# MiroFish OSINT

An OSINT (Open Source Intelligence) research agent MCP server that gathers data from multiple sources and synthesizes reports via Gemini. Designed to produce MiroFish-compatible seed material.

## Quick Start

1. Copy `.env.example` to `.env` and add your API keys:
   - `GEMINI_API_KEY` — from [Google AI Studio](https://aistudio.google.com/)
   - `SERPER_API_KEY` — from [serper.dev](https://serper.dev) (2,500 free/month)

2. Run with Docker:
   ```bash
   docker compose up
   ```

   Or run locally:
   ```bash
   uv sync
   uv run python src/server.py
   ```

3. Connect any MCP client to `http://localhost:8080/mcp`

## MCP Tools

### `research_raw`
Gather raw OSINT data. Returns structured JSON.
- `topic` (string) — research subject
- `depth` — `shallow` | `deep` | `research`

### `research_and_synthesize`
Research + Gemini synthesis. Returns markdown report.
- `topic` (string) — research subject
- `depth` — `shallow` | `deep` | `research`
- `output_format` — `mirofish` | `general`

### `list_sources`
List available data sources and their status.

## Depth Modes

| Mode | Sources | Latency |
|------|---------|---------|
| `shallow` | Serper + News/Trends + Reddit | ~10-15s |
| `deep` | All + Gemini Grounding + articles + Wikipedia | ~30-60s |
| `research` | Everything + Gemini Deep Research Agent | ~2-10 min |

## Data Sources

- **Serper** — Web search (2,500 free/month)
- **GDELT** — Global news events, 65 languages, 3-month rolling (free)
- **Google News/Trends** — Headlines + trending topics (free, RSS-based)
- **Reddit** — Posts and discussions (free, zero auth)
- **Wikipedia** — Background context (free)
- **newspaper4k** — Full article text extraction
- **Gemini Search Grounding** — Google Search via Gemini API
- **Gemini Deep Research** — Autonomous deep research agent

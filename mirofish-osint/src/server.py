from fastmcp import FastMCP

mcp = FastMCP("MiroFish OSINT")


@mcp.tool
def list_sources() -> list[dict]:
    """List available OSINT data sources and their current status."""
    return [
        {"name": "serper", "status": "active", "description": "Web search via Serper API"},
        {"name": "gdelt", "status": "active", "description": "GDELT DOC 2.0 global news events"},
        {"name": "google_news_trends", "status": "active", "description": "Google News + Trends"},
        {"name": "reddit", "status": "active", "description": "Reddit posts, zero auth"},
        {"name": "wikipedia", "status": "active", "description": "Wikipedia summaries"},
        {"name": "newspaper4k", "status": "active", "description": "Full article text extraction"},
        {"name": "gemini_grounding", "status": "active", "description": "Gemini Search Grounding"},
        {"name": "gemini_deep_research", "status": "active", "description": "Gemini Deep Research Agent"},
    ]


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8080)

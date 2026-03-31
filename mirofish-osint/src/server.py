import os
from typing import Literal
from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

mcp = FastMCP("MiroFish OSINT")


@mcp.tool
async def research_raw(
    topic: str,
    depth: Literal["shallow", "deep", "research"] = "shallow",
) -> dict:
    """Gather OSINT data on any topic from multiple sources. Returns structured JSON with all collected data.

    Args:
        topic: The research subject (e.g., "US chip tariff impact on TSMC")
        depth: shallow (latest, fast), deep (all sources + grounding), research (everything + Gemini Deep Research)
    """
    from src.tools.research_raw import research_raw as _research_raw
    return await _research_raw(topic, depth)


@mcp.tool
async def research_and_synthesize(
    topic: str,
    depth: Literal["shallow", "deep", "research"] = "shallow",
    output_format: Literal["mirofish", "general"] = "mirofish",
) -> str:
    """Research any topic and synthesize a structured OSINT report via Gemini.

    Args:
        topic: The research subject (e.g., "US chip tariff impact on TSMC")
        depth: shallow (latest, fast), deep (all sources + grounding), research (everything + Gemini Deep Research)
        output_format: mirofish (entity-dense, for MiroFish ingestion) or general (narrative, for human reading)
    """
    from src.tools.research_synthesize import research_and_synthesize as _synthesize
    return await _synthesize(topic, depth, output_format)


@mcp.tool
def list_sources() -> list[dict]:
    """List available OSINT data sources and their current status."""
    from src.tools.list_sources import get_sources
    return get_sources()


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8080)

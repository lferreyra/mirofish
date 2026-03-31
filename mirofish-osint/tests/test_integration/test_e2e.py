"""
End-to-end integration tests.
Run with: uv run pytest tests/test_integration/ -v -s
Requires GEMINI_API_KEY and SERPER_API_KEY in .env
"""
import os
import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("GEMINI_API_KEY") or not os.environ.get("SERPER_API_KEY"),
    reason="API keys not set",
)


@pytest.fixture(autouse=True)
def load_env():
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))


@pytest.mark.asyncio
async def test_research_raw_shallow():
    from src.tools.research_raw import research_raw
    result = await research_raw("Bitcoin price 2026", depth="shallow")
    assert result["topic"] == "Bitcoin price 2026"
    assert len(result["topic_classification"]) > 0
    assert result["collected_at"] != ""
    assert len(result["sources"]["web_search"]) > 0


@pytest.mark.asyncio
async def test_research_and_synthesize_shallow():
    from src.tools.research_synthesize import research_and_synthesize
    report = await research_and_synthesize("Bitcoin price 2026", depth="shallow", output_format="mirofish")
    assert isinstance(report, str)
    assert len(report) > 100


@pytest.mark.asyncio
async def test_list_sources():
    from src.tools.list_sources import get_sources
    sources = get_sources()
    assert len(sources) == 8
    assert sources[0]["name"] == "serper"
    assert sources[0]["status"] == "active"

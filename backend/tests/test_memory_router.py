"""Tests for MemoryRouter backend selection from env."""

import pytest

from app.memory.router import MemoryRouter


@pytest.fixture(autouse=True)
def _reset_router(monkeypatch):
    MemoryRouter.reset_default()
    # Scrub env so tests don't cross-contaminate.
    for k in ("MEMORY_BACKEND", "NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD", "ZEP_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    yield
    MemoryRouter.reset_default()


def test_explicit_in_memory_selection(monkeypatch):
    monkeypatch.setenv("MEMORY_BACKEND", "in_memory")
    router = MemoryRouter()
    backend = router.for_simulation("sim")
    assert backend.name == "in_memory"


def test_auto_picks_in_memory_without_any_config(monkeypatch):
    """Zero external creds -> in_memory. Enables zero-dep local runs."""
    router = MemoryRouter()
    assert router.kind == "in_memory"


def test_auto_prefers_neo4j_when_uri_set(monkeypatch):
    """A bolt:// URI indicates self-hosted; a neo4j+s:// URI is managed."""
    monkeypatch.setenv("NEO4J_URI", "bolt://localhost:7687")
    monkeypatch.setenv("NEO4J_PASSWORD", "pw")
    router = MemoryRouter()
    assert router.kind == "neo4j_local"

    # Now switch to Aura-style URI
    MemoryRouter.reset_default()
    monkeypatch.setenv("NEO4J_URI", "neo4j+s://xxx.databases.neo4j.io")
    router = MemoryRouter()
    assert router.kind == "neo4j_aura"


def test_auto_falls_back_to_zep_when_api_key_set(monkeypatch):
    """No Neo4j URI but a Zep API key set -> zep_cloud."""
    monkeypatch.setenv("ZEP_API_KEY", "zk-xxx")
    router = MemoryRouter()
    assert router.kind == "zep_cloud"


def test_unknown_backend_raises(monkeypatch):
    monkeypatch.setenv("MEMORY_BACKEND", "not_a_real_backend")
    router = MemoryRouter()
    from app.memory.base import MemoryBackendError
    with pytest.raises(MemoryBackendError) as exc_info:
        router.for_simulation("sim")
    assert exc_info.value.code == "unknown_backend_kind"

"""Shared pytest fixtures for the llm/ suite.

Most tests swap in a fake backend so no real HTTP is made. The tracker is
redirected to a tmp SQLite DB per test to keep runs hermetic.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Ensure `import app.*` works regardless of cwd.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


@pytest.fixture(autouse=True)
def _tmp_tracker_db(tmp_path, monkeypatch):
    """Redirect the global LLM call tracker to a per-test SQLite file."""
    db = tmp_path / "llm_calls.db"
    monkeypatch.setenv("LLM_CALLS_DB", str(db))
    from app.llm import accounting
    accounting.reset_tracker_for_tests(str(db))
    yield
    accounting._GLOBAL = None


@pytest.fixture(autouse=True)
def _reset_router_default():
    """Make sure env changes in one test don't leak into ModelRouter.default()."""
    from app.llm.router import ModelRouter
    ModelRouter.reset_default()
    yield
    ModelRouter.reset_default()


@pytest.fixture
def clean_llm_env(monkeypatch):
    """Strip LLM_* env vars before a test that wants a known-empty environment."""
    for key in list(os.environ.keys()):
        if key.startswith(("LLM_", "BACKEND_MODE", "VLLM_", "OLLAMA_")):
            monkeypatch.delenv(key, raising=False)

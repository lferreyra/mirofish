"""Shared pytest configuration and fixtures"""

import os
import sys
import tempfile
import pytest
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import Config


@pytest.fixture
def temp_file():
    """Create a temporary file for testing"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("Test content for MiroFish")
        temp_path = f.name

    yield temp_path

    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def temp_pdf_file():
    """Create a temporary PDF file for testing"""
    import fitz  # PyMuPDF

    # Create a simple PDF
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "MiroFish Test Document\n\nThis is a test PDF for file parsing.")

    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as f:
        doc.save(f.name)
        temp_path = f.name

    yield temp_path

    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def sample_json_data():
    """Sample JSON data for testing"""
    return {
        "graph_id": "test_graph_123",
        "entities": [
            {
                "uuid": "entity_1",
                "label": "Person",
                "name": "John Doe",
                "description": "Test person"
            },
            {
                "uuid": "entity_2",
                "label": "Organization",
                "name": "MiroFish Inc",
                "description": "Test organization"
            }
        ],
        "relationships": [
            {
                "source": "entity_1",
                "target": "entity_2",
                "relationship_type": "works_for"
            }
        ]
    }


@pytest.fixture
def mock_config(monkeypatch):
    """Mock configuration for testing"""
    monkeypatch.setenv("LLM_API_KEY", "test_key_123")
    monkeypatch.setenv("LLM_MODEL_NAME", "test-model")
    monkeypatch.setenv("LLM_BASE_URL", "https://test.api.com/v1")
    monkeypatch.setenv("ZEP_API_KEY", "test_zep_key")

    # Reload config to pick up environment variables
    Config.LLM_API_KEY = "test_key_123"
    Config.LLM_MODEL_NAME = "test-model"
    Config.LLM_BASE_URL = "https://test.api.com/v1"
    Config.ZEP_API_KEY = "test_zep_key"

    return Config

"""Tests for file parsing utilities"""

import pytest
import tempfile
import os
from pathlib import Path

from app.utils.file_parser import FileParser, _read_text_with_fallback


class TestFileParser:
    """Test cases for FileParser class"""

    def test_supported_extensions(self):
        """Test that correct file extensions are supported"""
        assert '.pdf' in FileParser.SUPPORTED_EXTENSIONS
        assert '.md' in FileParser.SUPPORTED_EXTENSIONS
        assert '.txt' in FileParser.SUPPORTED_EXTENSIONS
        assert '.markdown' in FileParser.SUPPORTED_EXTENSIONS

    def test_extract_text_from_txt_file(self, temp_file):
        """Test text extraction from plain text file"""
        content = FileParser.extract_text(temp_file)

        assert isinstance(content, str)
        assert len(content) > 0
        assert "Test content for MiroFish" in content

    def test_extract_text_from_nonexistent_file(self):
        """Test that FileNotFoundError is raised for nonexistent files"""
        with pytest.raises(FileNotFoundError):
            FileParser.extract_text("/nonexistent/file.txt")

    def test_extract_text_unsupported_format(self):
        """Test that unsupported file formats raise ValueError"""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            temp_path = f.name

        try:
            with pytest.raises(ValueError):
                FileParser.extract_text(temp_path)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_read_text_with_fallback_utf8(self, temp_file):
        """Test reading UTF-8 encoded text file"""
        content = _read_text_with_fallback(temp_file)

        assert isinstance(content, str)
        assert len(content) > 0

    def test_read_text_with_fallback_empty_file(self):
        """Test reading empty text file"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            temp_path = f.name

        try:
            content = _read_text_with_fallback(temp_path)
            assert content == ""
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_read_text_with_fallback_special_characters(self):
        """Test reading file with special characters"""
        with tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.txt', encoding='utf-8'
        ) as f:
            f.write("Special chars: 你好世界 🚀 こんにちは")
            temp_path = f.name

        try:
            content = _read_text_with_fallback(temp_path)
            assert "你好世界" in content or "🚀" in content
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_extract_text_from_markdown_file(self):
        """Test text extraction from markdown file"""
        markdown_content = """# MiroFish Test

This is a test markdown document.

## Features
- Feature 1
- Feature 2
"""
        with tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.md', encoding='utf-8'
        ) as f:
            f.write(markdown_content)
            temp_path = f.name

        try:
            content = FileParser.extract_text(temp_path)
            assert "MiroFish Test" in content
            assert "Features" in content
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_extract_text_from_pdf_file(self, temp_pdf_file):
        """Test text extraction from PDF file"""
        content = FileParser.extract_text(temp_pdf_file)

        assert isinstance(content, str)
        assert len(content) > 0
        # The content should contain text from the PDF
        assert "MiroFish" in content or "Test" in content

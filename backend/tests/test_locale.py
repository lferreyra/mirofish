"""Unit tests for locale module."""

import json
from pathlib import Path

import pytest


def _load_locale_files():
    """Load locale files for testing."""
    # Construct absolute path to source/locales from this test file's location
    # This test file is at: source/backend/tests/test_locale.py
    # We need: source/locales/
    this_file = Path(__file__).resolve()
    # tests/test_locale.py -> tests/ -> backend/ -> source/
    source_root = this_file.parent.parent.parent
    locales_dir = source_root / "locales"

    # Load languages.json
    with open(locales_dir / "languages.json", "r", encoding="utf-8") as f:
        languages = json.load(f)

    # Load translations
    translations = {}
    for filename in Path(locales_dir).iterdir():
        if filename.suffix == ".json" and filename.name != "languages.json":
            locale_name = filename.stem
            with open(filename, "r", encoding="utf-8") as f:
                translations[locale_name] = json.load(f)

    return languages, translations


# Load locale data at module level for structure tests
_languages, _translations = _load_locale_files()


class TestLocaleStructure:
    """Tests for locale file structure and completeness."""

    def test_languages_has_required_fields(self):
        """Should have required fields in languages.json."""
        assert "zh" in _languages
        assert "en" in _languages
        assert _languages["zh"]["label"] == "中文"
        assert _languages["en"]["label"] == "English"

    def test_languages_have_llm_instruction(self):
        """Should have llmInstruction field for each language."""
        for lang, config in _languages.items():
            assert "llmInstruction" in config
            assert len(config["llmInstruction"]) > 0

    def test_zh_translation_has_common_keys(self):
        """zh translation should have common keys."""
        zh = _translations.get("zh", {})
        assert "common" in zh
        assert "confirm" in zh["common"]
        assert "cancel" in zh["common"]
        assert "loading" in zh["common"]

    def test_en_translation_has_common_keys(self):
        """en translation should have common keys."""
        en = _translations.get("en", {})
        assert "common" in en
        assert "confirm" in en["common"]
        assert "cancel" in en["common"]
        assert "loading" in en["common"]

    def test_zh_and_en_have_same_top_level_keys(self):
        """zh and en should have same top-level keys."""
        zh_keys = set(_translations.get("zh", {}).keys())
        en_keys = set(_translations.get("en", {}).keys())
        # All en keys should be in zh, and vice versa
        assert zh_keys == en_keys, "zh and en should have same top-level keys"

    def test_translation_interpolation_format(self):
        """Translations with variables should use {var} format."""
        zh = _translations.get("zh", {})
        # Check a known key with interpolation
        if "home" in zh and "heroDesc" in zh["home"]:
            hero_desc = zh["home"]["heroDesc"]
            # Should contain {brand}, {agentScale}, {optimalSolution} placeholders
            assert "{" in hero_desc, "heroDesc should have interpolation placeholders"


class TestLanguagesCompleteness:
    """Tests for language completeness."""

    def test_translation_files_have_same_keys(self):
        """All existing translation files should have the same structure."""
        # Get keys from zh as reference
        zh_keys = set(_translations.get("zh", {}).keys())
        for lang, trans in _translations.items():
            if lang != "zh":
                trans_keys = set(trans.keys())
                missing_in_trans = zh_keys - trans_keys
                assert not missing_in_trans, f"{lang} missing keys: {missing_in_trans}"

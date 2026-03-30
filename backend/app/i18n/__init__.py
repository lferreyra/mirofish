"""
MiroFish i18n - Internationalisierung
Unterstützt mehrere Sprachen über die LANGUAGE Umgebungsvariable.
Verfügbare Sprachen: zh (Standard), en, de
"""
import os
import importlib
from typing import Dict, Any

LANGUAGE = os.getenv('LANGUAGE', 'zh')
_cache = {}

def _get_module():
    if LANGUAGE not in _cache:
        try:
            _cache[LANGUAGE] = importlib.import_module(f'.{LANGUAGE}', package='app.i18n')
        except ModuleNotFoundError:
            _cache[LANGUAGE] = importlib.import_module('.zh', package='app.i18n')
    return _cache[LANGUAGE]

def get_prompt(key: str) -> str:
    """Get a prompt template by key."""
    return _get_module().PROMPTS[key]

def get_format(key: str) -> str:
    """Get a format string by key."""
    return _get_module().FORMATS[key]

def get_string(key: str, **kwargs) -> str:
    """Get a UI/status string, optionally with format args."""
    s = _get_module().STRINGS[key]
    return s.format(**kwargs) if kwargs else s

def get_pattern(key: str) -> str:
    """Get a regex pattern by key (for frontend)."""
    return _get_module().PATTERNS[key]

def get_all_formats() -> Dict[str, str]:
    return dict(_get_module().FORMATS)

def get_all_patterns() -> Dict[str, str]:
    return dict(_get_module().PATTERNS)

def get_language() -> str:
    return LANGUAGE

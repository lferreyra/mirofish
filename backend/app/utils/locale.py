import json
import os
import threading
from flask import request, has_request_context

_thread_local = threading.local()

_locales_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'locales')

# Load language registry
with open(os.path.join(_locales_dir, 'languages.json'), 'r', encoding='utf-8') as f:
    _languages = json.load(f)

# Load translation files
_translations = {}
for filename in os.listdir(_locales_dir):
    if filename.endswith('.json') and filename != 'languages.json':
        locale_name = filename[:-5]
        with open(os.path.join(_locales_dir, filename), 'r', encoding='utf-8') as f:
            _translations[locale_name] = json.load(f)

# AUGUR: idioma padrão = português do Brasil
DEFAULT_LOCALE = 'pt'


def _normalize(raw: str) -> str:
    """Normaliza variantes de locale para o código canônico registrado em _translations."""
    if not raw:
        return DEFAULT_LOCALE
    lower = raw.lower().strip()
    # Variantes de português → 'pt'
    if lower in ('pt-br', 'pt-pt', 'pt_br', 'pt_pt', 'pt'):
        return 'pt'
    # Retorna exatamente como veio se já existe em _translations
    if raw in _translations:
        return raw
    # Tenta prefixo de 2 chars (ex: 'en-US' → 'en')
    prefix = lower[:2]
    if prefix in _translations:
        return prefix
    return DEFAULT_LOCALE


def set_locale(locale: str):
    """Set locale for current thread. Call at the start of background threads."""
    _thread_local.locale = _normalize(locale)


def get_locale() -> str:
    if has_request_context():
        raw = request.headers.get('Accept-Language', DEFAULT_LOCALE)
        return _normalize(raw)
    return getattr(_thread_local, 'locale', DEFAULT_LOCALE)


def t(key: str, **kwargs) -> str:
    locale = get_locale()
    # Fallback chain: locale → pt → en → zh
    value = None
    for fallback in [locale, DEFAULT_LOCALE, 'en', 'zh']:
        messages = _translations.get(fallback, {})
        v = messages
        for part in key.split('.'):
            if isinstance(v, dict):
                v = v.get(part)
            else:
                v = None
                break
        if v is not None:
            value = v
            break

    if value is None:
        return key

    if kwargs:
        for k, v in kwargs.items():
            value = value.replace(f'{{{k}}}', str(v))

    return value


def get_language_instruction() -> str:
    locale = get_locale()
    # Fallback chain: locale → pt → en
    for fallback in [locale, DEFAULT_LOCALE, 'en']:
        lang_config = _languages.get(fallback)
        if lang_config:
            return lang_config.get('llmInstruction', 'Please respond in Brazilian Portuguese.')
    return 'Please respond in Brazilian Portuguese.'

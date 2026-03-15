import importlib.util
from pathlib import Path


def load_module(module_name: str, relative_path: str):
    module_path = Path(__file__).resolve().parents[1] / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


config_module = load_module('mirofish_config_for_test', 'app/config.py')
get_debug_mode = config_module.get_debug_mode
get_secret_key = config_module.get_secret_key


def test_get_secret_key_prefers_explicit_env():
    assert get_secret_key({'SECRET_KEY': 'configured-secret'}) == 'configured-secret'


def test_get_secret_key_generates_secure_fallback():
    secret_key = get_secret_key({})

    assert secret_key
    assert secret_key != 'mirofish-secret-key'
    assert len(secret_key) >= 32


def test_get_debug_mode_defaults_to_false():
    assert get_debug_mode({}) is False


def test_get_debug_mode_accepts_truthy_values():
    assert get_debug_mode({'FLASK_DEBUG': 'true'}) is True
    assert get_debug_mode({'FLASK_DEBUG': 'On'}) is True

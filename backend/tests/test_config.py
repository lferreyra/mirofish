from test_utils import load_module

config_module = load_module('config_test', 'app/config.py')
get_debug_mode = config_module.get_debug_mode
get_secret_key = config_module.get_secret_key


def test_get_secret_key_prefers_explicit_env():
    assert get_secret_key({'SECRET_KEY': 'configured-secret'}) == 'configured-secret'


def test_get_secret_key_generates_secure_fallback():
    secret_key = get_secret_key({})
    next_secret_key = get_secret_key({})

    assert secret_key
    assert secret_key != 'mirofish-secret-key'
    assert len(secret_key) >= 32
    assert secret_key != next_secret_key


def test_get_debug_mode_defaults_to_false():
    assert get_debug_mode({}) is False


def test_get_debug_mode_accepts_truthy_values():
    assert get_debug_mode({'FLASK_DEBUG': 'true'}) is True
    assert get_debug_mode({'FLASK_DEBUG': 'On'}) is True
    assert get_debug_mode({'FLASK_DEBUG': 'yes'}) is True

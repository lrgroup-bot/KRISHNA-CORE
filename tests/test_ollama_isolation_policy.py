from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "core" / "krishna_core" / "config.py").read_text(encoding="utf-8")


def test_config_has_explicit_owner_ollama_switch():
    assert 'KRISHNA_OLLAMA_ENABLED' in CONFIG
    assert 'ollama_enabled: bool' in CONFIG


def test_disabled_ollama_never_routes_to_shared_11434():
    assert 'if _OLLAMA_ENABLED' in CONFIG
    assert 'else "disabled://krishna-ollama"' in CONFIG
    assert 'http://127.0.0.1:11434' in CONFIG


def test_disabled_ollama_is_zero_socket_fail_fast():
    assert 'unsupported URL scheme' in CONFIG
    assert 'without opening any socket' in CONFIG
    assert 'http://127.0.0.1:1' not in CONFIG

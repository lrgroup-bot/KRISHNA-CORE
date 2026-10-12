from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "core" / "krishna_core" / "config.py").read_text(encoding="utf-8")


def test_config_has_explicit_owner_ollama_switch():
    assert 'KRISHNA_OLLAMA_ENABLED' in CONFIG
    assert 'ollama_enabled: bool' in CONFIG


def test_disabled_ollama_never_routes_to_shared_11434():
    assert 'if _OLLAMA_ENABLED' in CONFIG
    assert 'else "http://127.0.0.1:1"' in CONFIG
    assert 'http://127.0.0.1:11434' in CONFIG

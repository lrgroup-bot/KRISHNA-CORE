from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "scripts" / "START_KRISHNA_SAFE.ps1").read_text(encoding="utf-8")


def test_launcher_uses_verified_worktree_and_npm_cmd():
    assert 'E:\\KRISHNA-UI-NEW' in SCRIPT
    assert 'E:\\Node.JS' in SCRIPT
    assert 'npm.cmd' in SCRIPT
    assert 'feature/krishna-universe-ui' in SCRIPT
    assert 'git merge --ff-only' in SCRIPT


def test_launcher_starts_core_low_load_without_ollama():
    assert "KRISHNA_BACKGROUND_SERVICES_ENABLED='0'" in SCRIPT
    assert 'krishna_core.server' in SCRIPT
    assert '11434' in SCRIPT
    assert 'Get-Process llama-server,ollama' in SCRIPT
    assert 'start-ollama-krishna.cmd' in SCRIPT


def test_launcher_does_not_use_broad_tree_kills_or_touch_kuber():
    assert 'taskkill' not in SCRIPT.lower()
    assert '/T /F' not in SCRIPT
    assert 'KUBER' in SCRIPT
    assert 'KUBER is untouched' in SCRIPT


def test_launcher_checks_both_core_and_frontend_health():
    assert 'http://127.0.0.1:$CorePort/health' in SCRIPT
    assert 'http://127.0.0.1:$FrontendPort/spatial/' in SCRIPT
    assert 'Wait-Http' in SCRIPT
    assert 'core.log' in SCRIPT
    assert 'frontend.log' in SCRIPT

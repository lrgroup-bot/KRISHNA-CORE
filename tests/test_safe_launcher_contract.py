from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "scripts" / "START_KRISHNA_SAFE.ps1").read_text(encoding="utf-8")


def test_launcher_uses_verified_worktree_and_npm_cmd():
    assert 'E:\\KRISHNA-UI-NEW' in SCRIPT
    assert 'E:\\Node.JS' in SCRIPT
    assert 'npm.cmd' in SCRIPT
    assert 'feature/krishna-universe-ui' in SCRIPT
    assert 'git merge --ff-only' in SCRIPT
    assert 'git rev-parse HEAD' in SCRIPT


def test_launcher_starts_core_low_load_without_starting_shared_ollama():
    assert "KRISHNA_BACKGROUND_SERVICES_ENABLED='0'" in SCRIPT
    assert 'krishna_core.server' in SCRIPT
    assert 'start-ollama-krishna.cmd' in SCRIPT
    assert 'A shared Ollama service is already listening on 11434' in SCRIPT
    assert 'KRISHNA did not start or stop it' in SCRIPT
    assert 'Get-Process llama-server,ollama' not in SCRIPT


def test_launcher_does_not_use_broad_tree_kills_or_touch_kuber():
    assert 'taskkill' not in SCRIPT.lower()
    assert '/T /F' not in SCRIPT
    assert 'KUBER' in SCRIPT
    assert 'KUBER and shared Ollama are untouched' in SCRIPT
    assert 'Refusing to kill an unrelated process' in SCRIPT


def test_launcher_checks_both_core_and_frontend_health_and_ports():
    assert 'http://127.0.0.1:$CorePort/health' in SCRIPT
    assert 'http://127.0.0.1:$FrontendPort/spatial/' in SCRIPT
    assert 'Wait-Http' in SCRIPT
    assert 'Assert-PortFree -Port $CorePort' in SCRIPT
    assert 'Assert-PortFree -Port $FrontendPort' in SCRIPT
    assert 'core.log' in SCRIPT
    assert 'frontend.log' in SCRIPT


def test_launcher_uses_encoded_child_commands_and_cleans_up_on_failure():
    assert 'Start-EncodedPowerShell' in SCRIPT
    assert '-EncodedCommand' in SCRIPT
    assert 'Startup/acceptance failed. Cleaning only KRISHNA processes' in SCRIPT
    assert 'npm install --no-package-lock --no-audit --no-fund' in SCRIPT


def test_launcher_runs_live_acceptance_after_startup():
    for endpoint in (
        '/health',
        '/api/status',
        '/api/tasks?limit=500',
        '/api/garudanetra/fabric',
        '/api/projects',
        '/api/chats',
        '/api/dashboard',
        '/api/plugins',
    ):
        assert endpoint in SCRIPT
    assert "-Name 'tasks'" in SCRIPT
    assert "-Name 'garudanetra'" in SCRIPT
    assert 'Running live acceptance sweep' in SCRIPT
    assert 'no retired KRISHNA worker is running' in SCRIPT
    assert 'no KRISHNA connection to 11434 while idle' in SCRIPT
    assert 'KRISHNA is running and the live acceptance sweep passed.' in SCRIPT
    assert 'nvidia-smi' in SCRIPT

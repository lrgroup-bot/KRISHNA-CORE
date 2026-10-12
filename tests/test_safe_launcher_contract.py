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


def test_launcher_runs_background_fabric_but_isolates_shared_ollama():
    assert "KRISHNA_BACKGROUND_SERVICES_ENABLED='1'" in SCRIPT
    assert "KRISHNA_OLLAMA_ENABLED='0'" in SCRIPT
    assert "KRISHNA_STRICT_ZERO_CREDIT='1'" in SCRIPT
    assert "KRISHNA_ALLOW_PAID_CLOUD='0'" in SCRIPT
    assert 'krishna_core.server' in SCRIPT
    assert 'start-ollama-krishna.cmd' in SCRIPT
    assert 'shared Ollama service is listening on 11434' in SCRIPT
    assert 'KRISHNA is isolated from it' in SCRIPT
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
        '/api/models/roles',
        '/api/resilience/status',
    ):
        assert endpoint in SCRIPT
    assert "-Name 'tasks'" in SCRIPT
    assert "-Name 'garudanetra'" in SCRIPT
    assert "-Name 'resilience'" in SCRIPT
    assert 'worker supervisor is running' in SCRIPT
    assert 'KRISHNA router cannot reach shared Ollama' in SCRIPT
    assert 'Running live acceptance sweep' in SCRIPT
    assert 'no retired KRISHNA worker is running' in SCRIPT
    assert 'no KRISHNA connection to 11434' in SCRIPT
    assert 'KRISHNA is running with background services ON and KRISHNA Ollama routing OFF.' in SCRIPT
    assert 'nvidia-smi' in SCRIPT


def test_launcher_reuses_expensive_acceptance_payloads_instead_of_double_fetching():
    assert SCRIPT.count('/api/models/roles') == 1
    assert SCRIPT.count('/api/resilience/status') == 1
    assert "$modelRoles = Assert-JsonEndpoint -Name 'models'" in SCRIPT
    assert "$resilience = Assert-JsonEndpoint -Name 'resilience'" in SCRIPT
    assert '[switch]$PassThru' in SCRIPT

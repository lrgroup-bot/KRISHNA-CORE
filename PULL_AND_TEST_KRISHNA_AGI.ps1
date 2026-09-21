$ErrorActionPreference='Stop'
$Source='E:\KRISHNA-SOURCE'
$RuntimePython='E:\Krishna-The GOD\.venv\Scripts\python.exe'
Set-Location $Source
Write-Host '=== KRISHNA AGI: PULL + VERIFY ===' -ForegroundColor Cyan
git status --short
git pull --ff-only
if (!(Test-Path $RuntimePython)) { throw "Runtime Python not found: $RuntimePython" }
& $RuntimePython -m compileall -q core
$env:PYTHONPATH=(Join-Path $Source 'core')
& $RuntimePython -m pytest -q core\tests
if ($LASTEXITCODE -ne 0) { throw 'KRISHNA tests failed. EXE build is blocked.' }
Write-Host 'Core tests PASS. Starting KRISHNA for browser verification...' -ForegroundColor Green
$env:KRISHNA_RUNTIME_ROOT='E:\Krishna-The GOD'
Start-Process $RuntimePython -ArgumentList '-m','core.krishna_core.server' -WorkingDirectory $Source
Start-Sleep -Seconds 2
Start-Process 'http://127.0.0.1:8766/dashboard'
Write-Host 'Dashboard opened. Run Garudanetra/UI Guardian verification before EXE packaging.' -ForegroundColor Yellow

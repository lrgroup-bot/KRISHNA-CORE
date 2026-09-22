$ErrorActionPreference="Stop"
$Source=Split-Path -Parent $MyInvocation.MyCommand.Path
$Py="E:\Krishna-The GOD\.venv\Scripts\python.exe"
if(!(Test-Path $Py)){throw "KRISHNA runtime Python not found: $Py"}
Set-Location $Source
$env:PYTHONPATH=Join-Path $Source "core"

& $Py -m compileall -q core\krishna_core
if($LASTEXITCODE -ne 0){throw "compileall failed"}
& $Py -m unittest discover -v -s core\tests -p "test_*.py"
if($LASTEXITCODE -ne 0){throw "Core tests failed"}
& $Py -m unittest discover -v -s tests -p "test_*.py"
if($LASTEXITCODE -ne 0){throw "Repository contracts failed"}
& $Py -c "from krishna_core.orchestrator import Orchestrator; o=Orchestrator(); print('ORCHESTRATOR_IMPORT_OK'); o.close()"
if($LASTEXITCODE -ne 0){throw "Orchestrator smoke test failed"}
$ui=Get-Content -Raw (Join-Path $Source "core\web_validation.html")
if($ui -notmatch 'data-krishna-ui="2026\.09-current"'){throw "Current KRISHNA UI marker missing"}
Write-Host "KRISHNA AGI SOURCE TESTS PASSED" -ForegroundColor Green

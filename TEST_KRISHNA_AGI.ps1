$ErrorActionPreference="Stop"
$Source=Split-Path -Parent $MyInvocation.MyCommand.Path
$Py="E:\Krishna-The GOD\.venv\Scripts\python.exe"
Set-Location $Source
& $Py -m compileall -q core
if ($LASTEXITCODE -ne 0) { throw "compileall failed" }
& $Py -c "from core.krishna_core.orchestrator import Orchestrator; o=Orchestrator(); print(o.agi_status()); o.close()"
if ($LASTEXITCODE -ne 0) { throw "AGI smoke test failed" }
Write-Host "KRISHNA AGI SOURCE TESTS PASSED" -ForegroundColor Green

$ErrorActionPreference="Stop"
$Source="E:\KRISHNA-SOURCE"
$RuntimePython="E:\Krishna-The GOD\.venv\Scripts\python.exe"
Set-Location $Source
Write-Host "=== KRISHNA: PULL + FULL VERIFY ===" -ForegroundColor Cyan
if(git status --porcelain){throw "Local source changes detected; refusing pull over uncommitted work."}
git pull --ff-only
if($LASTEXITCODE -ne 0){throw "Git fast-forward pull failed."}
if(!(Test-Path $RuntimePython)){throw "Runtime Python not found: $RuntimePython"}

& powershell -NoProfile -ExecutionPolicy Bypass -File ".\TEST_KRISHNA_AGI.ps1"
if($LASTEXITCODE -ne 0){throw "KRISHNA tests failed. EXE build is blocked."}

Write-Host "Source tests PASS. Running verified deployment/runtime acceptance..." -ForegroundColor Green
& powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\DEPLOY_KRISHNA_ONCE.ps1" -SkipStart
if($LASTEXITCODE -ne 0){throw "Verified deployment failed."}

Write-Host "Verified runtime ready. Starting KRISHNA current UI..." -ForegroundColor Green
& powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\START_KRISHNA.ps1"

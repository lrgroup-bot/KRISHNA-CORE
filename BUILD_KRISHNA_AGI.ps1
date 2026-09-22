$ErrorActionPreference = "Stop"
$Source = Split-Path -Parent $MyInvocation.MyCommand.Path
$Runtime = "E:\Krishna-The GOD"
$Py = Join-Path $Runtime ".venv\Scripts\python.exe"
if (!(Test-Path $Py)) { throw "KRISHNA runtime Python not found: $Py" }
Set-Location $Source

$env:PIP_CACHE_DIR=Join-Path $Runtime "cache\pip"
$env:TEMP=Join-Path $Runtime "cache\build-temp"
$env:TMP=$env:TEMP
New-Item -ItemType Directory -Force $env:PIP_CACHE_DIR,$env:TEMP | Out-Null

& powershell -NoProfile -ExecutionPolicy Bypass -File ".\TEST_KRISHNA_AGI.ps1"
if($LASTEXITCODE -ne 0){throw "KRISHNA source verification failed; EXE build blocked"}

& $Py -m pip install --disable-pip-version-check --upgrade pyinstaller pywebview playwright
if($LASTEXITCODE -ne 0){throw "KRISHNA build dependencies failed"}

$ui=Join-Path $Source "core\web_validation.html"
if(!(Test-Path $ui)){throw "Current KRISHNA UI missing: $ui"}
if((Get-Content -Raw $ui) -notmatch 'data-krishna-ui="2026\.09-current"'){throw "Stale KRISHNA UI; build blocked"}

& $Py -m PyInstaller --noconfirm --clean --onefile --windowed `
  --name Krishna_AGI `
  --paths "$Source\core" `
  --collect-submodules krishna_core `
  --collect-all playwright `
  --collect-all webview `
  --add-data "$Source\core\web_validation.html;." `
  --add-data "$Source\avatar\krishna_child_360.webp.b64;avatar" `
  "$Source\core\krishna_desktop.py"
if($LASTEXITCODE -ne 0){throw "KRISHNA desktop build failed"}

$artifact=Join-Path $Source "dist\Krishna_AGI.exe"
if(!(Test-Path $artifact)){throw "KRISHNA build artifact missing: $artifact"}
Write-Host "Build candidate: $artifact" -ForegroundColor Cyan
Write-Host "Private avatar/state/models remain under E:\Krishna-The GOD and are not bundled." -ForegroundColor DarkCyan
Write-Host "Run verified deployment/runtime acceptance before treating this candidate as released." -ForegroundColor Yellow

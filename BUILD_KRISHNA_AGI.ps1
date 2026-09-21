$ErrorActionPreference = "Stop"
$Source = Split-Path -Parent $MyInvocation.MyCommand.Path
$Runtime = "E:\Krishna-The GOD"
$Py = Join-Path $Runtime ".venv\Scripts\python.exe"
if (!(Test-Path $Py)) { throw "KRISHNA runtime Python not found: $Py" }
Set-Location $Source
& $Py -m pip install --upgrade pyinstaller
& $Py -m PyInstaller --noconfirm --clean --name Krishna_AGI --onefile --console --paths "$Source" "core\run_core.py"
Write-Host "Build candidate: $Source\dist\Krishna_AGI.exe" -ForegroundColor Cyan
Write-Host "Do not promote until TEST_KRISHNA_AGI.ps1 passes on Windows." -ForegroundColor Yellow

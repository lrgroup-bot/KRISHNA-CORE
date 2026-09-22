param(
  [string]$KrishnaRoot = "E:\Krishna-The GOD",
  [switch]$InstallChromium
)
$ErrorActionPreference="Stop"
$python=Join-Path $KrishnaRoot ".venv\Scripts\python.exe"
if(-not (Test-Path -LiteralPath $python)){ throw "KRISHNA venv python not found: $python" }
& $python -m pip install --upgrade pip
& $python -m pip install playwright pillow schemathesis
if($InstallChromium){ & $python -m playwright install chromium }
Write-Host "KRISHNA Project Perfection dependencies ready." -ForegroundColor Green
& $python -c "import PIL,playwright,schemathesis; print('PROJECT_PERFECTION_DEPS_OK')"

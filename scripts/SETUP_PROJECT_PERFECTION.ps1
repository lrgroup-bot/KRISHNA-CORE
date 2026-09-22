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

$axeRoot=Join-Path $KrishnaRoot "tools\project-perfection"
$npmCache=Join-Path $KrishnaRoot "npm-cache"
New-Item -ItemType Directory -Force -Path $axeRoot,$npmCache | Out-Null
$npm=(Get-Command npm -ErrorAction SilentlyContinue)
if(-not $npm){ throw "npm is required to install local axe-core accessibility verifier" }
$env:npm_config_cache=$npmCache
if(-not (Test-Path -LiteralPath (Join-Path $axeRoot "package.json"))){
  & $npm.Source --prefix $axeRoot init -y | Out-Null
}
& $npm.Source --prefix $axeRoot install axe-core@4 --no-audit --no-fund
$axePath=Join-Path $axeRoot "node_modules\axe-core\axe.min.js"
if(-not (Test-Path -LiteralPath $axePath)){ throw "axe-core install failed: $axePath" }
$env:KRISHNA_AXE_CORE_JS=$axePath
[Environment]::SetEnvironmentVariable("KRISHNA_AXE_CORE_JS",$axePath,"User")

Write-Host "KRISHNA Project Perfection dependencies ready." -ForegroundColor Green
Write-Host "axe-core: $axePath" -ForegroundColor DarkGray
& $python -c "import PIL,playwright,schemathesis; print('PROJECT_PERFECTION_DEPS_OK')"

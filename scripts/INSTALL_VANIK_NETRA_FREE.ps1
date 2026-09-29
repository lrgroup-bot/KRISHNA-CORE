param(
  [string]$Python = $env:KRISHNA_PYTHON
)

$ErrorActionPreference = "Stop"
$runtimeRoot = if ($env:KRISHNA_RUNTIME_ROOT) { $env:KRISHNA_RUNTIME_ROOT } else { "E:\Krishna-The GOD" }

$candidates = @(
  $Python,
  (Join-Path $runtimeRoot ".venv\Scripts\python.exe"),
  "E:\KRISHNA-SOURCE\.venv\Scripts\python.exe"
) | Where-Object { $_ -and (Test-Path $_) }

if (-not $candidates) {
  throw "No KRISHNA E-drive Python environment found. Set KRISHNA_PYTHON explicitly."
}

$pythonExe = $candidates[0]
$cacheRoot = Join-Path $runtimeRoot "tools\vanik-netra"
New-Item -ItemType Directory -Force -Path $cacheRoot | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $cacheRoot "pip-cache") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $cacheRoot "tmp") | Out-Null

$env:PIP_CACHE_DIR = Join-Path $cacheRoot "pip-cache"
$env:TEMP = Join-Path $cacheRoot "tmp"
$env:TMP = $env:TEMP
$env:PYTHONDONTWRITEBYTECODE = "1"

Write-Host "VANIK-NETRA free dependency install"
Write-Host "Python : $pythonExe"
Write-Host "Cache  : $env:PIP_CACHE_DIR"
Write-Host "Runtime: $runtimeRoot"

& $pythonExe -m pip install --upgrade duckdb h3
if ($LASTEXITCODE -ne 0) { throw "Free VANIK-NETRA dependency installation failed." }

& $pythonExe -c "import duckdb,h3; print('duckdb',duckdb.__version__); print('h3',h3.__version__)"
if ($LASTEXITCODE -ne 0) { throw "VANIK-NETRA dependency verification failed." }

Write-Host "VANIK-NETRA free dependencies are ready. No paid API or subscription was enabled."

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$krishnaRoot = if ($env:KRISHNA_ROOT) { $env:KRISHNA_ROOT } else { "E:\Krishna-The GOD" }
$cacheRoot = Join-Path $krishnaRoot "pip-cache"
New-Item -ItemType Directory -Force -Path $cacheRoot | Out-Null
$env:PIP_CACHE_DIR = $cacheRoot

$candidates = @()
if ($env:KRISHNA_PYTHON) { $candidates += $env:KRISHNA_PYTHON }
$candidates += @(
    (Join-Path $repoRoot ".venv\Scripts\python.exe"),
    (Join-Path $krishnaRoot ".venv\Scripts\python.exe")
)

$python = $null
foreach ($candidate in $candidates) {
    if ($candidate -and (Test-Path $candidate)) { $python = $candidate; break }
}
if (-not $python) {
    throw "KRISHNA virtual-environment Python not found. Refusing a global/C-drive install."
}

& $python -m pip install --disable-pip-version-check --no-input --upgrade opencv-python-headless
if ($LASTEXITCODE -ne 0) { throw "OpenCV installation failed" }

& $python -c "import cv2; print('CHANDRADEV OpenCV READY', cv2.__version__)"
if ($LASTEXITCODE -ne 0) { throw "OpenCV verification failed" }

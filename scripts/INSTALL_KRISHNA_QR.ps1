$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$cacheRoot = Join-Path $repoRoot ".cache\pip"
New-Item -ItemType Directory -Force -Path $cacheRoot | Out-Null
$env:PIP_CACHE_DIR = $cacheRoot

$candidates = @()
if ($env:KRISHNA_PYTHON) { $candidates += $env:KRISHNA_PYTHON }
$candidates += @(
    (Join-Path $repoRoot ".venv\Scripts\python.exe"),
    "E:\Krishna-The GOD\.venv\Scripts\python.exe"
)

$python = $null
foreach ($candidate in $candidates) {
    if ($candidate -and (Test-Path $candidate)) {
        $python = $candidate
        break
    }
}

if (-not $python) {
    throw "KRISHNA venv Python not found. Set KRISHNA_PYTHON or create the project/E-drive venv first. Refusing a global install."
}

& $python -m pip install --disable-pip-version-check --no-input "qrcode==8.2"
if ($LASTEXITCODE -ne 0) { throw "qrcode installation failed" }

& $python -c "import qrcode; from qrcode.image.svg import SvgPathImage; print('KRISHNA QR renderer READY')"
if ($LASTEXITCODE -ne 0) { throw "qrcode verification failed" }

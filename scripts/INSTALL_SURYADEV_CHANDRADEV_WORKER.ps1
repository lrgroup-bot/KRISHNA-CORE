param(
    [Parameter(Mandatory=$false)]
    [string]$Root = "E:\KRISHNA-EXTERNAL-OBSERVERS",
    [switch]$SkipBrowser
)

$ErrorActionPreference = "Stop"
$Root = [System.IO.Path]::GetFullPath($Root)
$Venv = Join-Path $Root ".venv"
$Cache = Join-Path $Root "cache"
$Models = Join-Path $Root "models"
$Browsers = Join-Path $Root "playwright-browsers"
$Workspace = Join-Path $Root "workspace"

New-Item -ItemType Directory -Force -Path $Root,$Cache,$Models,$Browsers,$Workspace | Out-Null

$env:TEMP = Join-Path $Root "tmp"
$env:TMP = $env:TEMP
$env:PIP_CACHE_DIR = Join-Path $Cache "pip"
$env:HF_HOME = Join-Path $Models "huggingface"
$env:TRANSFORMERS_CACHE = Join-Path $Models "transformers"
$env:PLAYWRIGHT_BROWSERS_PATH = $Browsers
New-Item -ItemType Directory -Force -Path $env:TEMP,$env:PIP_CACHE_DIR,$env:HF_HOME,$env:TRANSFORMERS_CACHE,$env:PLAYWRIGHT_BROWSERS_PATH | Out-Null

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python is required on the external Suryadev/Chandradev workstation."
}

if (-not (Test-Path (Join-Path $Venv "Scripts\python.exe"))) {
    python -m venv $Venv
}
$Python = Join-Path $Venv "Scripts\python.exe"

& $Python -m pip install --upgrade pip wheel setuptools

$Packages = @(
    "mss>=10,<11",
    "Pillow>=10,<12",
    "opencv-python-headless>=4.10,<5",
    "PyAudioWPatch>=0.2,<1",
    "faster-whisper>=1.1,<2",
    "scenedetect[opencv]>=0.6.6,<0.8",
    "playwright>=1.50,<2",
    "openadapt-capture>=1.3,<1.4"
)
& $Python -m pip install $Packages

if (-not $SkipBrowser) {
    & $Python -m playwright install chromium
}

$Config = @{
    schema = "krishna.external-observers.config.v1"
    root = $Root
    workspace = $Workspace
    models = $Models
    browser_path = $Browsers
    raw_media_policy = "local-only"
    transfer_policy = "distilled-findings-only"
    authentication_handoff = $true
    captcha_liveness = "human-handoff-only"
    free_only = $true
}
$Config | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 (Join-Path $Root "external-observers.json")

Write-Host ""
Write-Host "SURYDEV/CHANDRADEV external workspace prepared:"
Write-Host "  Root      : $Root"
Write-Host "  Python    : $Python"
Write-Host "  Workspace : $Workspace"
Write-Host "  Models    : $Models"
Write-Host ""
Write-Host "FFmpeg is optional but recommended and must be installed separately if not already present."
Write-Host "No paid API or paid service is configured by this installer."

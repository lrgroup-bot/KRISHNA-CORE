param(
    [string]$Output = ".\\dist-suryadev-learner",
    [switch]$SkipResetSmoke
)
$ErrorActionPreference = "Stop"
$Repo = Split-Path -Parent $PSScriptRoot
$Source = Join-Path $Repo "standalone\\suryadev"
$Output = [System.IO.Path]::GetFullPath($Output)
$Scratch = Join-Path $Output "_stage"
$StageApp = Join-Path $Scratch "app"
$Browsers = Join-Path $Scratch "playwright-browsers"
$Build = Join-Path $Scratch "build"
$Specs = Join-Path $Scratch "specs"
New-Item -ItemType Directory -Force $Output,$Scratch,$Build,$Specs | Out-Null

python -m pip install pyinstaller psutil playwright pypdf yt-dlp pypdfium2 pytesseract pillow
if ($LASTEXITCODE -ne 0) { throw "Python build dependencies failed" }
if (Test-Path $StageApp) {
    $ResolvedStage = [IO.Path]::GetFullPath($StageApp)
    if (-not $ResolvedStage.StartsWith($Output + [IO.Path]::DirectorySeparatorChar,
            [StringComparison]::OrdinalIgnoreCase)) { throw "Unsafe staging directory" }
    Remove-Item -Recurse -Force -LiteralPath $ResolvedStage
}
python (Join-Path $Source "install-node.py") --install-dir $StageApp
if ($LASTEXITCODE -ne 0) { throw "SURYADEV test gate or packaging stage failed" }

# GARUDANETRA's Playwright-managed Chromium is bundled explicitly. Never
# fall back to installed Google Chrome or Edge on customer PCs.
$env:PLAYWRIGHT_BROWSERS_PATH = $Browsers
python -m playwright install chromium
if ($LASTEXITCODE -ne 0) { throw "GARUDANETRA Chromium download failed" }
if (-not (Test-Path -LiteralPath $Browsers -PathType Container)) {
    throw "GARUDANETRA Chromium payload missing"
}

$PyInstallerArgs = @(
    "-m","PyInstaller",
    "--noconfirm","--clean","--onedir","--console",
    "--name","Suryadev-Learner",
    "--distpath",$Output,
    "--workpath",$Build,
    "--specpath",$Specs,
    "--paths",$StageApp,
    "--collect-all","playwright",
    "--collect-all","psutil",
    "--collect-all","yt_dlp",
    "--hidden-import","pypdf",
    "--add-data",($StageApp + [IO.Path]::PathSeparator + "app"),
    "--add-data",($Browsers + [IO.Path]::PathSeparator + "playwright-browsers"),
    (Join-Path $Source "suryadev_windows_exe.py")
)
# The entrypoint uses runpy on source assets. Data files alone do not make
# PyInstaller analyze their imports (sqlite3/ssl and lazy worker dependencies).
# Analyze every runtime module so the EXE works without system Python.
foreach ($Module in (Get-ChildItem -LiteralPath $StageApp -Filter 'suryadev*.py')) {
    if ($Module.BaseName -ne 'suryadev_windows_exe') {
        $PyInstallerArgs = $PyInstallerArgs[0..($PyInstallerArgs.Count - 2)] +
            @('--hidden-import', $Module.BaseName, $PyInstallerArgs[-1])
    }
}
python @PyInstallerArgs
if ($LASTEXITCODE -ne 0) { throw "Suryadev-Learner.exe build failed" }

$Package = Join-Path $Output "Suryadev-Learner"
$Exe = Join-Path $Package "Suryadev-Learner.exe"
if (-not (Test-Path $Exe -PathType Leaf)) { throw "Full learner EXE not generated" }

& $Exe --self-test
if ($LASTEXITCODE -ne 0) { throw "Bundled EXE self-test failed" }

# Real frozen startup, without starting a dashboard or contacting sources.
$ProbeRoot = Join-Path $Scratch "probe-data"
& $Exe --model collector --data $ProbeRoot --prepare-only --port 8872
if ($LASTEXITCODE -ne 0) { throw "Frozen launcher prepare-only smoke failed" }
if (-not $SkipResetSmoke) {
    & $Exe --reset-learning --data $ProbeRoot --confirm CLEAR-ALL-SURYADEV-LEARNING
    if ($LASTEXITCODE -ne 0) { throw "Frozen archive/reset smoke failed" }
}

$Hash = (Get-FileHash -Algorithm SHA256 -Path $Exe).Hash
@{
    schema = "suryadev.windows-learner-release.v1"
    main_executable = "Suryadev-Learner.exe"
    sha256 = $Hash
    full_ai_learner_dashboard = $true
    default_data_dir = "data (beside the executable)"
    portable_one_directory = $true
    chromium_managed_by = "GARUDANETRA Playwright"
    reset_requires_explicit_confirmation = $true
    frozen_reset_smoke_passed = (-not $SkipResetSmoke.IsPresent)
    local_ollama_required_for_model_inference = $true
    automatic_component_setup = $true
    automatic_model = 'hardware-admitted qwen3.5:2b; collector on insufficient headroom'
} | ConvertTo-Json | Set-Content -Encoding UTF8 (Join-Path $Package "RELEASE.json")

@'
SURYADEV AI Learner for Windows

1. Extract the entire Suryadev-Learner directory from the ZIP.
2. Run Suryadev-Learner.exe. Local dashboard: http://127.0.0.1:8872
3. This is a full portable app, not the legacy Core Suryadev controller.
4. First launch provisions missing local Ollama + qwen3.5:2b when hardware is safe.
   Downloads need internet and at least 10 GiB free disk; low-resource PCs collect evidence.
   Runtime downloads require a valid Ollama publisher signature. See KRISHNA Server for status.
   Models run locally; no paid or cloud model fallback.
5. Exact source approvals remain required. YouTube playback is not guaranteed.
6. RESET WITH ARCHIVE (ONLY AFTER CLOSING APP AND WORKERS):
   .\\Suryadev-Learner.exe --reset-learning --data .\\data --confirm CLEAR-ALL-SURYADEV-LEARNING
   All existing learning files AND approvals are archived to a sibling folder.
   Then run .\\Suryadev-Learner.exe to start a clean workspace.
7. Do NOT run reset against a live worker or with your data directory unmarked.
8. Existing Python-based SURYADEV data is NOT automatically imported.
   If migrating, use --data with an explicitly chosen existing directory.
9. On each new PC, open KRISHNA Server, enter the owner's HTTPS server address,
   certificate SHA-256 and a unique suryadev- device ID. Request pairing,
   approve on the KRISHNA PC, then activate and restart the learning worker.
   LAN reachability alone is not authenticated pairing. Credentials stay local.
10. Five videos and ten PDFs are queue targets, not guaranteed simultaneous work.
    The current PC's measured hardware and source/provider limits always apply.
'@ | Set-Content -Encoding UTF8 (Join-Path $Package "README-FIRST.txt")

@'
@echo off
cd /d "%~dp0"
if not exist "data\fresh-workspace.json" (
    echo No initialized SURYADEV learning workspace found beside this EXE.
    echo Start Suryadev-Learner.exe once to create it.
    pause
    exit /b 2
)
echo WARNING: This will archive ALL study data, approvals and history.
echo Close SURYADEV before continuing.
set /p CHOICE=Type RESET to archive learning and start fresh:
if /I not "%CHOICE%"=="RESET" (
    echo Cancelled. No learning files changed.
    pause
    exit /b 1
)
"%~dp0Suryadev-Learner.exe" --reset-learning --data "%~dp0data" --confirm CLEAR-ALL-SURYADEV-LEARNING
if errorlevel 1 (
    echo Reset failed or was blocked; check the messages above.
) else (
    echo Reset completed. Run Suryadev-Learner.exe again for the new clean workspace.
)
pause
'@ | Set-Content -Encoding ASCII (Join-Path $Package "RESET-LEARNING.cmd")

Write-Host "FULL SURYADEV AI Learner packaged: $Exe"

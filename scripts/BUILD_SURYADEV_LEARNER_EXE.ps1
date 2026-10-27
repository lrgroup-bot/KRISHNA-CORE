param(
    [string]$Output = ".\\dist-suryadev-learner"
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

python -m pip install pyinstaller psutil playwright pypdf yt-dlp
if ($LASTEXITCODE -ne 0) { throw "Python build dependencies failed" }
if (Test-Path $StageApp) { Remove-Item -Recurse -Force -LiteralPath $StageApp }
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
& $Exe --reset-learning --data $ProbeRoot --confirm CLEAR-ALL-SURYADEV-LEARNING
if ($LASTEXITCODE -ne 0) { throw "Frozen archive/reset smoke failed" }

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
    external_ollama_required_for_model_inference = $true
} | ConvertTo-Json | Set-Content -Encoding UTF8 (Join-Path $Package "RELEASE.json")

@'
SURYADEV AI Learner for Windows

1. Extract the entire Suryadev-Learner directory from the ZIP.
2. Run Suryadev-Learner.exe. Local dashboard: http://127.0.0.1:8872
3. This is a full portable app, not the legacy Core Suryadev controller.
4. Models are not bundled. Install Ollama + qwen3.5:2b for local AI inference.
5. Exact source approvals remain required. YouTube playback is not guaranteed.
6. RESET WITH ARCHIVE (ONLY AFTER CLOSING APP AND WORKERS):
   .\\Suryadev-Learner.exe --reset-learning --data .\\data --confirm CLEAR-ALL-SURYADEV-LEARNING
   All existing learning files AND approvals are archived to a sibling folder.
   Then run .\\Suryadev-Learner.exe to start a clean workspace.
7. Do NOT run reset against a live worker or with your data directory unmarked.
8. Existing Python-based SURYADEV data is NOT automatically imported.
   If migrating, use --data with an explicitly chosen existing directory.
'@ | Set-Content -Encoding UTF8 (Join-Path $Package "README-FIRST.txt")

Write-Host "FULL SURYADEV AI Learner packaged: $Exe"

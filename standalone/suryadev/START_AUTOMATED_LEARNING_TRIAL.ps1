param(
  [string]$InstallDir = "D:\Work\SURYADEV-UNIFIED-TEST",
  [string]$DataDir = "D:\Work\SURYADEV-UNIFIED-TEST-DATA",
  [string]$Python = "python",
  [string]$Model = "qwen3.5:9b"
)
$ErrorActionPreference = "Stop"
# This is an explicit one-time opt-in to two fixed public learning sources.
# Stop the existing SURYADEV worker AND dashboard before updating code.
$active = @(Get-CimInstance Win32_Process | Where-Object {
   $_.Name -match '^python(w)?\.exe$' -and
   $_.CommandLine -match 'suryadev_extras\.py' -and
   $_.CommandLine -match 'SURYADEV-UNIFIED-TEST-DATA'
})
if ($active.Count -ne 0) {
    $active | Select-Object ProcessId,CommandLine | Format-List
    throw "Stop the existing SURYADEV worker/dashboard gracefully before updating installed source. No process was killed."
}
if (-not (Test-Path -LiteralPath (Join-Path $DataDir "suryadev.sqlite3"))) {
    throw "Existing SURYADEV data root not found. Refusing to create a replacement data root."
}
if (-not (Test-Path -LiteralPath (Join-Path $DataDir "learning-plan.json"))) {
    throw "Approved learning plan missing. Refusing to bypass the source allowlist."
}
$git = Get-Command git -ErrorAction Stop
$checkout = Join-Path $env:TEMP ("suryadev-trial-src-" + [guid]::NewGuid().ToString("N"))
$repo = "https://github.com/lrgroup-bot/KRISHNA-CORE.git"
$branch = "feature/suryadev-r39-unified-repo-ui-20261023"
Write-Host "Fetching approved SURYADEV development branch (read-only checkout)..."
& $git.Source clone --quiet --filter=blob:none --no-checkout --depth=1 --single-branch --branch $branch $repo $checkout
if ($LASTEXITCODE -ne 0) {throw "Git checkout failed; installed SURYADEV not changed."}
& $git.Source -C $checkout sparse-checkout set --no-cone "/standalone/suryadev/" "/core/suryadev_worker.py" "/scripts/SURYDEV_VIDEO_LEARNING_ADAPTER.py"
if ($LASTEXITCODE -ne 0) {throw "Git sparse checkout failed; installed SURYADEV not changed."}
& $git.Source -C $checkout checkout --quiet $branch
if ($LASTEXITCODE -ne 0) {throw "Git branch checkout failed; installed SURYADEV not changed."}
$source = Join-Path $checkout "standalone\suryadev"
foreach ($name in @("suryadev_trial.py","suryadev_trial_exam.py","install-windows.ps1")) {
  if (-not (Test-Path -LiteralPath (Join-Path $source $name))) {
    throw "Trial module missing in verified checkout: $name"
  }
}
# Keep the durable data root untouched. Installer runs all tests before copying.
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $source "install-windows.ps1") -InstallDir $InstallDir -DataDir $DataDir -Python $Python
if ($LASTEXITCODE -ne 0) {throw "SURYADEV installation/tests failed. Learning not started."}
# The PDF book reader requires free local pypdf. Never use paid services.
& $Python -m pip show pypdf *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing free Python PDF parser for the approved textbook..."
    & $Python -m pip install --user pypdf
    if ($LASTEXITCODE -ne 0) {
        throw "Could not install free pypdf. Book acquisition/reading cannot be claimed."
    }
}
$env:SURYADEV_LEARNING_TRIAL = "1"
Write-Host "Starting ONE SURYADEV worker with automated YouTube/book trial."
Write-Host "Approved video: https://www.youtube.com/watch?v=VZ5LU8vHT0s"
Write-Host "Approved textbook: https://greenteapress.com/thinkpython2/thinkpython2.pdf"
Write-Host "No manual frontend source inputs. Local Ollama only. Ctrl+C for graceful stop."
& $Python (Join-Path $InstallDir "suryadev_extras.py") --data $DataDir worker --plan (Join-Path $DataDir "learning-plan.json") --model $Model --interval 30
if ($LASTEXITCODE -ne 0) {
    throw "Worker stopped with an error. See the worker console and learning-trial-runtime.json."
}

param(
    [string]$InstallDir = "$env:LOCALAPPDATA\SURYADEV",
    [string]$DataDir = "$env:USERPROFILE\SURYADEV-DATA",
    [string]$Python = "python"
)
$ErrorActionPreference = "Stop"
$source = (Resolve-Path $PSScriptRoot).Path
$destination = [System.IO.Path]::GetFullPath($InstallDir)
if ($destination.TrimEnd('\') -eq $source.TrimEnd('\')) {
    throw "Install destination must differ from source checkout"
}
Set-Location -LiteralPath $source
Write-Host "Validating SURYADEV before copying"
& $Python -c "import sys; assert sys.version_info >= (3,10), 'Python 3.10+ required'"
if ($LASTEXITCODE -ne 0) { throw "Python 3.10+ required" }
& $Python --version
if ($LASTEXITCODE -ne 0) { throw "Python 3.10+ is required" }
# Keep exact Windows failures visible and saved locally; never skip or
# automatically rerun a failed test. The active install remains untouched.
$testLog = Join-Path ([System.IO.Path]::GetTempPath()) "suryadev-install-tests.log"
& $Python (Join-Path $source 'install_test_gate.py') --source $source --log $testLog
if ($LASTEXITCODE -ne 0) {
    throw "Tests failed; no files installed. Full test names and tracebacks: $testLog"
}
# Reuse canonical repository worker and adapter; do not deploy the R39 ZIP binaries/UI.
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $source '..\..'))
$observerWorker = Join-Path $repoRoot 'core\suryadev_worker.py'
$observerAdapter = Join-Path $repoRoot 'scripts\SURYDEV_VIDEO_LEARNING_ADAPTER.py'
if (-not (Test-Path -LiteralPath $observerWorker -PathType Leaf)) { throw 'Canonical SURYADEV worker missing from GitHub checkout' }
if (-not (Test-Path -LiteralPath $observerAdapter -PathType Leaf)) { throw 'Canonical SURYADEV video adapter missing from GitHub checkout' }
New-Item -ItemType Directory -Force -Path $destination | Out-Null
$files = @('suryadev.py','suryadev_extras.py','suryadev_evidence.py',
           'suryadev_lock.py','suryadev_resources.py','suryadev_sources.py','suryadev_task_details.py','suryadev_liveops.py','suryadev_settings.py','suryadev_storage.py','suryadev_cleanup.py','suryadev_operator_api.py','suryadev_ingest.py','suryadev_deep_pdf.py','suryadev_deep_web.py','suryadev_video_lab.py','suryadev_youtube_audit.py','suryadev_book_reader.py','suryadev_book_visuals.py','suryadev_book_dashboard.py','suryadev_book_continuity.py','suryadev_book_handoff.py','suryadev_summary.py','suryadev_feeder.py','suryadev_continuity.py','suryadev_publisher.py','suryadev_mission_renewal.py','suryadev_krishna_mission.py','suryadev_fleet_client.py','suryadev_mission.py','suryadev_parallel.py','suryadev_parallel_books.py','suryadev_parallel_videos.py','suryadev_garudanetra.py','suryadev_youtube_preflight.py','install_test_gate.py','live_smoke.py','parallel_smoke.py','dashboard_ui_smoke.py','learning-plan.example.json','krishna-mission-connection.example.json','suryadev_bridge.py','suryadev_core_reader.py','suryadev_media.py','suryadev_discovery.py',
           'suryadev_core_identity.py','suryadev_enroll.py','dashboard.html','dashboard.css','dashboard-api.js','dashboard-learning.js','dashboard.js','dashboard-settings.css','dashboard-settings.js','dashboard-garudanetra.css','dashboard-garudanetra.js','dashboard-books.css','dashboard-books.js','laptop-preflight.ps1','start-continuous-learning.ps1','start-fresh-workspace.ps1','start-node.py','install-node.py','README.md','verify_runtime_package.py','suryadev_video_review.py','suryadev_dashboard_worker.py','suryadev_trial.py','suryadev_trial_exam.py','dashboard-video.css','dashboard-video.js')
foreach ($name in $files) {
    $from = Join-Path $source $name
    if (-not (Test-Path $from)) { throw "Missing release file: $name" }
    Copy-Item -LiteralPath $from -Destination (Join-Path $destination $name) -Force
}
Copy-Item -LiteralPath $observerWorker -Destination (Join-Path $destination 'suryadev_r39_worker.py') -Force
Copy-Item -LiteralPath $observerAdapter -Destination (Join-Path $destination 'suryadev_r39_adapter.py') -Force
# Verify from the actual installed directory using Python isolated mode (-I).
# Without -I, the source checkout can mask omitted modules such as suryadev_fleet_client.
& $Python -I (Join-Path $destination 'verify_runtime_package.py') --root $destination
if ($LASTEXITCODE -ne 0) { throw "Installed SURYADEV import validation failed" }
New-Item -ItemType Directory -Force -Path $DataDir | Out-Null
Write-Host "Installed SURYADEV to $destination"
Write-Host "Persistent data directory: $DataDir"
Write-Host "No services, startup tasks, firewall changes or Core pairing were created."
Write-Host "Next: cd '$destination'; & $Python suryadev.py --data '$DataDir' status"

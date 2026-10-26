<#
Read-only SURYADEV 1 acceptance preflight. Run AFTER pulling the feature branch
and installing the app. No job creation, network source fetch, browser launch,
startup task, Core pairing, provider login, or data mutation.
#>
param(
    [string]$Root = 'D:\Work\SURYADEV-FLEET-CANARY-20261025',
    [switch]$RequireDashboard
)
$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath($Root)
$Checkout = Join-Path $Root 'KRISHNA-CORE'
$App = Join-Path $Root 'app'
$Data = Join-Path $Root 'data'
$Base = 'http://127.0.0.1:8872'
$results = New-Object 'System.Collections.Generic.List[object]'

function Record([string]$Check, [string]$Status, [string]$Detail) {
    $script:results.Add([pscustomobject]@{
        check = $Check; status = $Status; detail = $Detail
    })
    Write-Host "$Status | $Check | $Detail"
}

Write-Host 'SURYADEV AI Learner | read-only Windows acceptance preflight'
Write-Host "Root: $Root"
Write-Host 'No sources, jobs, databases, credentials or worker state will be changed.'
if (-not (Test-Path -LiteralPath $Checkout -PathType Container)) {
    throw 'Expected existing KRISHNA-CORE checkout missing; no directory was created.'
}
try {
    $head = (& git -C $Checkout rev-parse HEAD 2>$null | Select-Object -First 1)
    $branch = (& git -C $Checkout symbolic-ref --quiet --short HEAD 2>$null | Select-Object -First 1)
    if ($LASTEXITCODE -ne 0 -or !$head) { throw 'git ref query failed' }
    if ($branch -eq 'feature/suryadev-universal-fleet-foundation-20261025') {
        Record 'Feature branch' 'PASS' $branch
    } else {
        Record 'Feature branch' 'FAIL' ("Expected SURYADEV feature; current: " + $branch)
    }
    Record 'Checkout HEAD' 'INFO' ([string]$head)
} catch {
    Record 'Git checkout' 'FAIL' 'Cannot read existing Git feature branch'
}
$source = Join-Path $Checkout 'standalone\suryadev'
$filenames = @('dashboard-ai-learner.js', 'dashboard-ai-learner.css',
               'dashboard.html', 'suryadev_video_review.py')
foreach ($file in $filenames) {
    $from = Join-Path $source $file
    $installed = Join-Path $App $file
    if (!(Test-Path -LiteralPath $from -PathType Leaf)) {
        Record "Source $file" 'FAIL' 'Missing in checked-out feature branch'
        continue
    }
    if (!(Test-Path -LiteralPath $installed -PathType Leaf)) {
        Record "Installed $file" 'FAIL' 'Missing: install from the feature branch after graceful stop'
        continue
    }
    $sourceHash = (Get-FileHash -LiteralPath $from -Algorithm SHA256).Hash
    $installedHash = (Get-FileHash -LiteralPath $installed -Algorithm SHA256).Hash
    Record "Installed $file" $(if ($sourceHash -eq $installedHash) { 'PASS' } else { 'FAIL' }) $(if ($sourceHash -eq $installedHash) { 'Matches checkout bytes' } else { 'Stale or modified installation; avoid testing the old UI' })
}
$htmlFile = Join-Path $App 'dashboard.html'
if (Test-Path -LiteralPath $htmlFile -PathType Leaf) {
    $html = Get-Content -LiteralPath $htmlFile -Raw
    $ids = @('ai-learner', 'ai-tab-youtube', 'ai-tab-pdf', 'ai-tab-website', 'ai-tab-book')
    $missing = @($ids | Where-Object { !$html.Contains('id="' + $_ + '"') })
    if ($missing.Count -eq 0) {
        Record 'Four integrated learning actions' 'PASS' 'All four workspace buttons are installed'
    } else {
        Record 'Four integrated learning actions' 'FAIL' ('Missing IDs: ' + ($missing -join ', '))
    }
}
Record 'Persistent data root' $(if (Test-Path -LiteralPath $Data -PathType Container) { 'PASS' } else { 'FAIL' }) 'Only presence checked; no writes'
Record 'Research SQLite ledger' $(if (Test-Path -LiteralPath (Join-Path $Data 'suryadev.sqlite3') -PathType Leaf) { 'PASS' } else { 'FAIL' }) 'Database not opened by this script'
Record 'Approved learning plan' $(if (Test-Path -LiteralPath (Join-Path $Data 'learning-plan.json') -PathType Leaf) { 'PASS' } else { 'WARN' }) 'Contents and credential values not printed'

$online = $false
try {
    $ui = Invoke-RestMethod -Uri "$Base/api/ui-version" -TimeoutSec 8
    $control = Invoke-RestMethod -Uri "$Base/api/learning/control" -TimeoutSec 8
    $video = Invoke-RestMethod -Uri "$Base/api/video/review" -TimeoutSec 8
    $online = $true
    Record 'Loopback dashboard' 'PASS' 'Existing local dashboard answered; no process started'
    Record 'AI Learner server contract' $(if ($ui.has_ai_learner_four_source_page -eq $true) { 'PASS' } else { 'FAIL' }) 'Expected unified source dashboard API'
    if ($control.managed_running -and $control.external_worker_active) {
        Record 'Single worker authority' 'FAIL' 'Both managed and external worker reported active'
    } else {
        Record 'Single worker authority' 'PASS' ('Managed: ' + [bool]$control.managed_running + '; external lock: ' + [bool]$control.external_worker_active)
    }
    $revoked = @($video.jobs | Where-Object { $_.source_currently_approved -ne $true -and $_.can_run -eq $true })
    Record 'Current YouTube approval enforced' $(if ($revoked.Count -eq 0) { 'PASS' } else { 'FAIL' }) ("Invalid runnable jobs: " + $revoked.Count)
    Record 'YouTube observation automation' 'INFO' $(if ($video.auto_enabled) { 'Enabled; video learning still unverified' } else { 'Not enabled; no playback claim' })
    if ($video.media_health) {
        Record 'Live browser media channel' $(if ($video.media_health.browser_channel -eq 'chromium') { 'PASS' } else { 'WARN' }) ('Observed channel: ' + [string]$video.media_health.browser_channel + '; position: ' + [string]$video.media_health.source_position_seconds + ' seconds; comprehension unverified')
    } else {
        Record 'Live browser media channel' 'PENDING' 'No fresh media-health observation; physical GARUDANETRA playback still required'
    }
    Record 'KRISHNA dispatch' 'INFO' $(if ($control.core_dispatch.ready) { 'Paired configuration validates locally; live Core ACK unverified' } else { 'Not locally paired; do not infer Core access' })
} catch {
    Record 'Loopback dashboard' $(if ($RequireDashboard) { 'FAIL' } else { 'PENDING' }) 'No verified response from existing port 8872; no dashboard started'
}

Record 'Full audiovisual coverage' 'PENDING' 'Must be verified on the laptop using genuine media observations, captions and frame evidence'
Record 'BRAHMAGYAN / Rishi examination' 'PENDING' 'Do not promote extracted text or preview playback to verified learning'
$failures = @($results | Where-Object { $_.status -eq 'FAIL' }).Count
Write-Host ''
Write-Host ("Acceptance preflight: " + $(if ($failures -eq 0) { 'PASS (with explicit pending physical gates)' } else { 'FAIL' }) + "; failed checks: " + $failures)
Write-Host 'This audit does not launch workers, import sources or modify the learning data directory.'
if ($failures -gt 0) { exit 2 }
exit 0

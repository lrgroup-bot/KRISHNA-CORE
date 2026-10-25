param(
  [string]$Root = 'D:\Work\SURYADEV-FLEET-CANARY-20261025',
  [string]$Model = 'auto',
  [int]$Minutes = 45,
  [switch]$DashboardOnly,
  [string]$Manifest = ''
)
$ErrorActionPreference = 'Stop'
if ($Model -notin @('auto','collector','qwen3.5:2b','qwen3.5:4b','qwen3.5:9b','gemma3:4b')) {
  throw 'Unsupported model. Auto safely chooses only an installed local model or collector.'
}
if ($Minutes -lt 1 -or $Minutes -gt 720) { throw 'Minutes must be between 1 and 720.' }
$Root = [System.IO.Path]::GetFullPath($Root)
$App = Join-Path $Root 'app'
$Data = Join-Path $Root 'data'
$Python = Join-Path $Root '.venv\Scripts\python.exe'
$Start = Join-Path $App 'start-node.py'
$Benchmark = Join-Path $App 'suryadev_workload_benchmark.py'
$Base = 'http://127.0.0.1:8872'
if (!(Test-Path -LiteralPath $Python -PathType Leaf) -or !(Test-Path -LiteralPath $Start -PathType Leaf)) {
  throw 'Existing Python/app not found. No new learning data root was created.'
}
if (!(Test-Path -LiteralPath (Join-Path $Data 'fresh-workspace.json'))) {
  throw 'Existing canary data root not found. Refusing to create a new workspace.'
}
$Listening = @(Get-NetTCPConnection -LocalPort 8872 -State Listen -ErrorAction SilentlyContinue)
if ($Listening.Count -gt 0) {
  try {
    $Control = Invoke-RestMethod "$Base/api/learning/control" -TimeoutSec 8
    if ($null -eq $Control.can_start) { throw 'This service does not look like SURYADEV.' }
    Write-Host 'Existing SURYADEV dashboard is already online; no duplicate process started.' -ForegroundColor Green
  } catch { throw 'Port 8872 is occupied by an unknown/unresponsive process. Nothing was stopped.' }
} else {
  Write-Host 'Starting one SURYADEV dashboard using the EXISTING data directory...' -ForegroundColor Cyan
  $launchArgs = @($Start,'--data',$Data,'--model',$Model,'--adaptive-fleet',
            '--continuous','--auto-approved-videos','--port','8872')
  $Started = Start-Process -FilePath $Python -ArgumentList $launchArgs -WorkingDirectory $App -PassThru
  $Control = $null
  for ($i=0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    try {
      $Control = Invoke-RestMethod "$Base/api/learning/control" -TimeoutSec 2
      break
    } catch {
      if ($Started.HasExited) { throw "Dashboard exited with code $($Started.ExitCode). Do not start another instance." }
    }
  }
  if ($null -eq $Control) { throw 'Dashboard not responding on 8872. Inspect its console before retrying.' }
}
Write-Host "Dashboard: $Base/advanced#video-review" -ForegroundColor Green
if ($DashboardOnly) { return }
if (!(Test-Path -LiteralPath $Benchmark -PathType Leaf)) {
  throw 'Install the tested feature-branch package after a GRACEFUL dashboard/worker stop. Existing app does not contain the benchmark.'
}
$Before = @('--data',$Data,'--preflight')
if ($Manifest) { $Before += @('--manifest',[System.IO.Path]::GetFullPath($Manifest)) }
& $Python $Benchmark @Before
if ($LASTEXITCODE -ne 0) {
  throw '13-source preflight refused: approve exactly 3 PDFs, 2 websites, 3 videos and 5 local SHA-pinned books. Dashboard remains online; no benchmark started.'
}
$Control = Invoke-RestMethod "$Base/api/learning/control" -TimeoutSec 8
if ($Control.external_worker_active) { throw 'External worker owns lock; no duplicate startup.' }
if (!$Control.managed_running) {
  $settings = Invoke-RestMethod "$Base/api/operator/settings" -TimeoutSec 8
  if (!$settings.csrf_token) { throw 'Missing local dashboard CSRF authorization.' }
  $Headers = @{ 'Origin'=$Base; 'X-SURYADEV-CSRF'=$settings.csrf_token }
  $Result = Invoke-RestMethod "$Base/api/operator/learning/start" `
    -Method Post -ContentType 'application/json' -Headers $Headers `
    -Body (ConvertTo-Json @{ model=$Model } -Compress) -TimeoutSec 20
  $Result | Select-Object status,pid,model,learning_role,approved_books_loaded,book_mode |
    Format-List
}
$Control = Invoke-RestMethod "$Base/api/learning/control" -TimeoutSec 8
if (!$Control.managed_running) { throw 'Worker did not start. Check dashboard-worker.log; benchmark refused.' }
$Video = Invoke-RestMethod "$Base/api/video/review" -TimeoutSec 8
if (!$Video.auto_enabled) {
  Write-Warning 'YouTube visual-observation automation is disabled. Caption jobs may still run, but full video testing is NOT active. Do not infer that watching happened.'
}
Write-Host 'Starting read-only timed audit of approved work. Ctrl+C stops the AUDIT, not the learning worker.' -ForegroundColor Cyan
$Cmd = @('--data',$Data,'--dashboard',$Base,'--minutes',"$Minutes",
         '--sample-seconds','15','--report-dir',(Join-Path $Root 'benchmark-reports'))
if ($Manifest) { $Cmd += @('--manifest',[System.IO.Path]::GetFullPath($Manifest)) }
& $Python $Benchmark @Cmd
if ($LASTEXITCODE -ne 0) {
  Write-Warning 'Some lanes were incomplete, blocked, rate-limited or the audit reached its time limit. Read the JSON receipt; existing learning data was not cleared.'
}

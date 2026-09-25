param(
  [string]$SourceRoot="E:\KRISHNA-SOURCE",
  [string]$RuntimeRoot="E:\Krishna-The GOD",
  [int]$AcceptancePort=8876,
  [switch]$SkipLiveAcceptance
)
$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

$SourceRoot=[IO.Path]::GetFullPath($SourceRoot)
$RuntimeRoot=[IO.Path]::GetFullPath($RuntimeRoot)
$py=Join-Path $RuntimeRoot ".venv\Scripts\python.exe"
if(!(Test-Path $py)){throw "KRISHNA runtime Python not found: $py"}
if(!(Test-Path (Join-Path $SourceRoot ".git"))){throw "Authoritative KRISHNA source is not a Git working tree: $SourceRoot"}

$reportDir=Join-Path $RuntimeRoot "reports"
New-Item -ItemType Directory -Force $reportDir|Out-Null
$stamp=Get-Date -Format "yyyyMMdd-HHmmss"
$staticReport=Join-Path $reportDir ("full-project-static-audit-"+$stamp+".json")
$summaryReport=Join-Path $reportDir ("full-project-audit-"+$stamp+".json")
$steps=New-Object System.Collections.Generic.List[object]

function Step([string]$Name,[scriptblock]$Run){
  Write-Host ""
  Write-Host ("=== AUDIT BOT: "+$Name+" ===") -ForegroundColor Cyan
  $started=Get-Date
  try{
    # Reset native-command state so a previous failed tool cannot poison a later
    # PowerShell-only audit phase.
    $global:LASTEXITCODE=0
    & $Run
    $code=$global:LASTEXITCODE
    if($null -eq $code){$code=0}
    if($code -ne 0){throw "$Name returned exit code $code"}
    $steps.Add([ordered]@{name=$Name;status="PASS";seconds=[math]::Round(((Get-Date)-$started).TotalSeconds,2)})
  }catch{
    $steps.Add([ordered]@{name=$Name;status="FAIL";seconds=[math]::Round(((Get-Date)-$started).TotalSeconds,2);error=$_.Exception.Message})
    # A full-project audit must continue after an individual phase fails so the
    # final report exposes every defect in one pass. The script still exits 2
    # after the summary when any phase failed.
    Write-Warning ("AUDIT STEP FAILED: {0}: {1}" -f $Name,$_.Exception.Message)
    return
  }
}

$env:PYTHONPATH=Join-Path $SourceRoot "core"

Step "SOURCE + UI + CORE + AVATAR + VOICE + MOBILE + SECURITY + DEPLOYMENT + REQUIREMENTS" {
  & $py -m krishna_core.project_audit --source-root $SourceRoot --runtime-root $RuntimeRoot --output $staticReport
}

Step "PYTHON COMPILE" {
  & $py -m compileall -q (Join-Path $SourceRoot "core") (Join-Path $SourceRoot "tests")
}

Step "CORE UNIT + HTTP INTEGRATION" {
  Push-Location (Join-Path $SourceRoot "core")
  try{& $py -m unittest discover -s tests -v}finally{Pop-Location}
}

Step "REPOSITORY CONTRACTS" {
  Push-Location $SourceRoot
  try{& $py -m unittest discover -s tests -v}finally{Pop-Location}
}

Step "SPATIAL FRONTEND BUILD" {
  $ui=Join-Path $SourceRoot "app\spatial-ui"
  if(!(Test-Path (Join-Path $ui "package.json"))){throw "spatial UI package.json missing"}
  $npm=(Get-Command npm -ErrorAction SilentlyContinue)
  if(!$npm){throw "npm is required for the spatial frontend build audit"}
  Push-Location $ui
  try{
    & npm install --ignore-scripts --no-audit --no-fund --package-lock=false
    if($LASTEXITCODE -ne 0){throw "npm install failed"}
    & npm run build
    if($LASTEXITCODE -ne 0){throw "spatial frontend build failed"}
  }finally{Pop-Location}
}

Step "SELF-HEAL CONTRACT PREFLIGHT" {
  Push-Location (Join-Path $SourceRoot "core")
  try{
    & $py -m unittest -v tests.test_self_heal tests.test_shared_action_bus tests.test_promotion_runtime
  }finally{Pop-Location}
}

Step "POWERSHELL PARSE" {
  $failed=@()
  Get-ChildItem (Join-Path $SourceRoot "scripts") -Filter "*.ps1" -File -Recurse | ForEach-Object {
    $tokens=$null;$errors=$null
    [void][System.Management.Automation.Language.Parser]::ParseFile($_.FullName,[ref]$tokens,[ref]$errors)
    if($errors){$failed += ($_.FullName+": "+(($errors|ForEach-Object Message)-join " | "))}
  }
  if($failed.Count){throw ($failed -join " || ")}
}

if(!$SkipLiveAcceptance){
  Step "REAL RUNTIME ACCEPTANCE" {
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $SourceRoot "scripts\ACCEPT_KRISHNA_RUNTIME.ps1") -SourceRoot $SourceRoot -RuntimeRoot $RuntimeRoot -Port $AcceptancePort
  }
}

Step "E DRIVE RECONCILIATION" {
  & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $SourceRoot "scripts\AUDIT_KRISHNA_E_DRIVE.ps1") -SourceRoot $SourceRoot -RuntimeRoot $RuntimeRoot | Out-Host
}

$rows=@($steps|ForEach-Object{$_})
$summary=[ordered]@{
  schema=1
  generated_at=(Get-Date).ToUniversalTime().ToString("o")
  source_root=$SourceRoot
  runtime_root=$RuntimeRoot
  source_commit=(git -C $SourceRoot rev-parse HEAD).Trim()
  static_report=$staticReport
  pass=@($rows|Where-Object{$_.status -eq "PASS"}).Count
  fail=@($rows|Where-Object{$_.status -eq "FAIL"}).Count
  steps=$rows
}
$summary|ConvertTo-Json -Depth 8|Set-Content -Encoding UTF8 $summaryReport
Write-Host ""
Write-Host ("FULL KRISHNA AUDIT COMPLETE: PASS={0} FAIL={1}" -f $summary.pass,$summary.fail) -ForegroundColor $(if($summary.fail){"Red"}else{"Green"})
Write-Host "Static report: $staticReport"
Write-Host "Summary report: $summaryReport"
if($summary.fail){exit 2}else{exit 0}

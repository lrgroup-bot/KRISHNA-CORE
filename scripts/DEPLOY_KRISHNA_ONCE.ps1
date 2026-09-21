param(
  [switch]$SkipStart,
  [switch]$SkipAcceptance,
  [string]$Branch = ""
)
$ErrorActionPreference="Stop"
$Source="E:\KRISHNA-SOURCE"
$Runtime="E:\Krishna-The GOD"
$Py="$Runtime\.venv\Scripts\python.exe"

function Invoke-KrishnaTests([string]$CoreRoot,[string]$ContractRoot){
  $env:PYTHONPATH="$CoreRoot\core"
  & $Py -m compileall -q "$CoreRoot\core\krishna_core"
  if($LASTEXITCODE -ne 0){throw "CORE COMPILE FAILED: $CoreRoot"}
  & $Py -m unittest discover -v -s "$CoreRoot\core\tests" -p "test_*.py"
  if($LASTEXITCODE -ne 0){throw "CORE TESTS FAILED: $CoreRoot"}
  if(Test-Path "$ContractRoot\tests"){
    & $Py -m unittest discover -v -s "$ContractRoot\tests" -p "test_*.py"
    if($LASTEXITCODE -ne 0){throw "REPOSITORY CONTRACTS FAILED: $ContractRoot"}
  }
}

Write-Host "=== KRISHNA VERIFIED DEPLOY ===" -ForegroundColor Cyan
if(!(Test-Path "$Source\.git")){throw "Source repo missing: $Source"}
if(!(Test-Path $Py)){throw "KRISHNA venv missing: $Py"}
Set-Location $Source
if((git status --porcelain)){throw "E:\KRISHNA-SOURCE has local changes. Refusing destructive update."}

git fetch --prune origin
if(!$Branch){
  $remoteHead=(git symbolic-ref --short refs/remotes/origin/HEAD 2>$null)
  if($LASTEXITCODE -eq 0 -and $remoteHead){$Branch=($remoteHead.Trim() -replace '^origin/','')}
  else{$Branch=(git branch --show-current).Trim()}
}
if(!$Branch){throw "Could not resolve deployment branch"}
git checkout $Branch
if($LASTEXITCODE -ne 0){throw "Cannot checkout $Branch"}
git pull --ff-only origin $Branch
if($LASTEXITCODE -ne 0){throw "Cannot fast-forward $Branch"}
$Head=(git rev-parse HEAD).Trim()
Write-Host "SOURCE $Branch @ $Head" -ForegroundColor Cyan

# Test authoritative source before runtime mutation.
Invoke-KrishnaTests $Source $Source

# Runtime state/assets are owned by the runtime and never mirrored/deleted by deploy.
$excludeDirs=@("__pycache__",".krishna_state","state","logs","backups",".venv","ollama-models","dashboard\assets\avatar")
$xd=@();foreach($d in $excludeDirs){$xd+=@("/XD",(Join-Path $Runtime $d))}
& robocopy "$Source\core" "$Runtime\core" /E /R:1 /W:1 /XF "*.pyc" @xd
if($LASTEXITCODE -ge 8){throw "CORE COPY FAILED: robocopy=$LASTEXITCODE"}

New-Item -ItemType Directory -Force "$Runtime\scripts"|Out-Null
& robocopy "$Source\scripts" "$Runtime\scripts" /E /R:1 /W:1 /XF "*.pyc"
if($LASTEXITCODE -ge 8){throw "SCRIPT COPY FAILED: robocopy=$LASTEXITCODE"}

# Test the deployed runtime code, then repository-level contracts against runtime PYTHONPATH.
$env:PYTHONPATH="$Runtime\core"
& $Py -m compileall -q "$Runtime\core\krishna_core"
if($LASTEXITCODE -ne 0){throw "DEPLOYED CORE COMPILE FAILED"}
& $Py -m unittest discover -v -s "$Runtime\core\tests" -p "test_*.py"
if($LASTEXITCODE -ne 0){throw "DEPLOYED CORE TESTS FAILED"}
& $Py -m unittest discover -v -s "$Source\tests" -p "test_*.py"
if($LASTEXITCODE -ne 0){throw "POST-DEPLOY CONTRACTS FAILED"}
& $Py -c "from krishna_core.orchestrator import Orchestrator; print('ORCHESTRATOR_IMPORT_OK')"
if($LASTEXITCODE -ne 0){throw "ORCHESTRATOR IMPORT FAILED"}

# Write an atomic deployment manifest so KRISHNA can prove exactly what code is running.
$deployDir=Join-Path $Runtime "state\deployment"
New-Item -ItemType Directory -Force $deployDir|Out-Null
$hashes=[ordered]@{}
$tracked=@()
$tracked+=Get-ChildItem "$Runtime\core\krishna_core" -File -Recurse -Filter "*.py" -ErrorAction SilentlyContinue
foreach($p in @("$Runtime\core\web_validation.html","$Runtime\core\dashboard.html")){
  if(Test-Path $p){$tracked+=Get-Item $p}
}
foreach($file in ($tracked|Sort-Object FullName -Unique)){
  $rel=$file.FullName.Substring($Runtime.Length+1).Replace("\","/")
  $hashes[$rel]=(Get-FileHash -Algorithm SHA256 $file.FullName).Hash.ToLowerInvariant()
}
$manifest=[ordered]@{
  schema=1
  commit=$Head
  branch=$Branch
  deployed_at=(Get-Date).ToUniversalTime().ToString("o")
  release_ready=$false
  acceptance_status="pending"
  acceptance_completed_at=$null
  source_root=$Source
  runtime_root=$Runtime
  files=$hashes
}
$tmp=Join-Path $deployDir "DEPLOYED_COMMIT.json.tmp"
$dest=Join-Path $deployDir "DEPLOYED_COMMIT.json"
$manifest|ConvertTo-Json -Depth 8|Set-Content -Encoding UTF8 $tmp
Move-Item -Force $tmp $dest

Write-Host "DEPLOY FILES SYNCED AT $Head" -ForegroundColor Cyan
Write-Host "MANIFEST $dest ($($hashes.Count) files; acceptance pending)" -ForegroundColor Cyan

# Real runtime acceptance is part of deployment by default. It starts an isolated
# localhost Core on a separate port, exercises the release gates, then shuts it down.
if(!$SkipAcceptance){
  $accept=Join-Path $Runtime "scripts\ACCEPT_KRISHNA_RUNTIME.ps1"
  if(!(Test-Path $accept)){throw "Runtime acceptance harness missing: $accept"}
  & powershell -NoProfile -ExecutionPolicy Bypass -File $accept -RuntimeRoot $Runtime -SourceRoot $Source
  if($LASTEXITCODE -ne 0){
    $failed=Get-Content -Raw $dest|ConvertFrom-Json
    $failed.release_ready=$false
    $failed.acceptance_status="failed"
    $failed.acceptance_completed_at=(Get-Date).ToUniversalTime().ToString("o")
    $failed|ConvertTo-Json -Depth 8|Set-Content -Encoding UTF8 $tmp
    Move-Item -Force $tmp $dest
    throw "KRISHNA runtime acceptance failed; release_ready remains false and final start is refused"
  }
  $passed=Get-Content -Raw $dest|ConvertFrom-Json
  $passed.release_ready=$true
  $passed.acceptance_status="passed"
  $passed.acceptance_completed_at=(Get-Date).ToUniversalTime().ToString("o")
  $passed|ConvertTo-Json -Depth 8|Set-Content -Encoding UTF8 $tmp
  Move-Item -Force $tmp $dest
  Write-Host "DEPLOY VERIFIED + ACCEPTED AT $Head" -ForegroundColor Green
}else{
  Write-Host "Acceptance skipped; runtime is NOT release-ready." -ForegroundColor Yellow
}

if(!$SkipStart -and $SkipAcceptance){
  throw "Cannot start KRISHNA from a deployment whose runtime acceptance was skipped"
}

# Non-destructive E: audit after every verified deployment.
$audit=Join-Path $Runtime "scripts\AUDIT_KRISHNA_E_DRIVE.ps1"
if(Test-Path $audit){
  & powershell -NoProfile -ExecutionPolicy Bypass -File $audit | Out-Host
}

if(!$SkipStart){
  $env:KRISHNA_ALLOW_ACTIONS="1"
  & "$Runtime\scripts\START_KRISHNA.ps1"
}

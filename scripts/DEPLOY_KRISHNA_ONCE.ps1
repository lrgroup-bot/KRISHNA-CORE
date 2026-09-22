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
  $currentBranch=(git branch --show-current).Trim()
  if($currentBranch){$Branch=$currentBranch}
  else{
    $remoteHead=(git symbolic-ref --short refs/remotes/origin/HEAD 2>$null)
    if($LASTEXITCODE -eq 0 -and $remoteHead){$Branch=($remoteHead.Trim() -replace '^origin/','')}
  }
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

# Parse every PowerShell entrypoint before touching runtime.
$parseFailures=@()
Get-ChildItem (Join-Path $Source "scripts") -Filter "*.ps1" -File -Recurse | ForEach-Object {
  $tokens=$null;$errors=$null
  [void][System.Management.Automation.Language.Parser]::ParseFile($_.FullName,[ref]$tokens,[ref]$errors)
  if($errors){$parseFailures += ($_.FullName + ": " + (($errors | ForEach-Object Message) -join " | "))}
}
if($parseFailures.Count){throw ("POWERSHELL PARSE FAILED: " + ($parseFailures -join " || "))}

# Runtime state/assets are owned by the runtime and never mirrored/deleted by deploy.
$excludeDirs=@("__pycache__",".krishna_state","state","logs","backups",".venv","ollama-models","dashboard\assets\avatar")
$xd=@();foreach($d in $excludeDirs){$xd+=@("/XD",(Join-Path $Runtime $d))}
& robocopy "$Source\core" "$Runtime\core" /E /R:1 /W:1 /XF "*.pyc" @xd
if($LASTEXITCODE -ge 8){throw "CORE COPY FAILED: robocopy=$LASTEXITCODE"}

New-Item -ItemType Directory -Force "$Runtime\scripts"|Out-Null
& robocopy "$Source\scripts" "$Runtime\scripts" /E /R:1 /W:1 /XF "*.pyc"
if($LASTEXITCODE -ge 8){throw "SCRIPT COPY FAILED: robocopy=$LASTEXITCODE"}

# Deploy only the repository-owned 360 preview asset required by /api/avatar360.
# Private runtime avatar assets (for example dashboard\assets\avatar\krishna.glb)
# remain runtime-owned and are never overwritten by this deploy.
$avatarPreviewSource=Join-Path $Source "avatar\krishna_child_360.webp.b64"
$avatarPreviewDir=Join-Path $Runtime "avatar"
$avatarPreviewRuntime=Join-Path $avatarPreviewDir "krishna_child_360.webp.b64"
if(!(Test-Path $avatarPreviewSource)){throw "AVATAR PREVIEW SOURCE MISSING: $avatarPreviewSource"}
New-Item -ItemType Directory -Force $avatarPreviewDir|Out-Null
Copy-Item -Force $avatarPreviewSource $avatarPreviewRuntime
if(!(Test-Path $avatarPreviewRuntime)){throw "AVATAR PREVIEW COPY FAILED: $avatarPreviewRuntime"}

# Install the browser-side 3D avatar engines locally on E: when missing.
# TalkingHead is cloned from GitHub at a pinned commit; model-viewer is pinned from npm.
$avatarEngineInstaller=Join-Path $Runtime "scripts\INSTALL_AVATAR_ENGINE.ps1"
$talkingHeadAsset=Join-Path $Runtime "dashboard\assets\avatar-engine\talkinghead\talkinghead.mjs"
$modelViewerAsset=Join-Path $Runtime "dashboard\assets\avatar-engine\model-viewer\model-viewer.min.js"
$headAudioAsset=Join-Path $Runtime "dashboard\assets\avatar-engine\headaudio\dist\headaudio.min.mjs"
$headAudioModel=Join-Path $Runtime "dashboard\assets\avatar-engine\headaudio\dist\model-en-mixed.bin"
$motionEngineAsset=Join-Path $Runtime "dashboard\assets\avatar-engine\motion-engine\src\MotionEngine.js"
if(!(Test-Path $talkingHeadAsset) -or !(Test-Path $modelViewerAsset) -or !(Test-Path $headAudioAsset) -or !(Test-Path $headAudioModel) -or !(Test-Path $motionEngineAsset)){
  if(!(Test-Path $avatarEngineInstaller)){throw "AVATAR ENGINE INSTALLER MISSING: $avatarEngineInstaller"}
  & powershell -NoProfile -ExecutionPolicy Bypass -File $avatarEngineInstaller -RuntimeRoot $Runtime
  if($LASTEXITCODE -ne 0){throw "AVATAR ENGINE INSTALL FAILED"}
}
if(!(Test-Path $talkingHeadAsset)){throw "TALKINGHEAD ASSET MISSING AFTER INSTALL: $talkingHeadAsset"}
if(!(Test-Path $modelViewerAsset)){throw "MODEL-VIEWER ASSET MISSING AFTER INSTALL: $modelViewerAsset"}
if(!(Test-Path $headAudioAsset)){throw "HEADAUDIO ASSET MISSING AFTER INSTALL: $headAudioAsset"}
if(!(Test-Path $headAudioModel)){throw "HEADAUDIO VISEME MODEL MISSING AFTER INSTALL: $headAudioModel"}
if(!(Test-Path $motionEngineAsset)){throw "MOTION ENGINE ASSET MISSING AFTER INSTALL: $motionEngineAsset"}

# Inspect the private runtime avatar and prepare an isolated local candidate when
# body rigging is required. This never overwrites dashboard\assets\avatar\krishna.glb.
# Missing Blender/face-rig capability is reported, not disguised as a successful avatar.
$avatarPrepare=Join-Path $Runtime "scripts\PREPARE_KRISHNA_AVATAR.ps1"
if(Test-Path $avatarPrepare){
  & powershell -NoProfile -ExecutionPolicy Bypass -File $avatarPrepare -RuntimeRoot $Runtime -SourceRoot $Source -TryBodyRig $true -InstallRigTools $true
  if($LASTEXITCODE -ne 0){throw "KRISHNA AVATAR PREPARATION FAILED"}
}

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
foreach($p in @(
  "$Runtime\core\web_validation.html",
  "$Runtime\core\dashboard.html",
  "$Runtime\avatar\krishna_child_360.webp.b64"
)){
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
  source_root=$Source
  runtime_root=$Runtime
  files=$hashes
}
$tmp=Join-Path $deployDir "DEPLOYED_COMMIT.json.tmp"
$dest=Join-Path $deployDir "DEPLOYED_COMMIT.json"
$previousManifest=$null
if(Test-Path $dest){$previousManifest=Get-Content -Raw $dest}
$manifest|ConvertTo-Json -Depth 8|Set-Content -Encoding UTF8 $tmp
Move-Item -Force $tmp $dest

Write-Host "DEPLOY STAGED AT $Head" -ForegroundColor Yellow
Write-Host "PROVISIONAL MANIFEST $dest ($($hashes.Count) files)" -ForegroundColor Yellow

# Real runtime acceptance is part of deployment by default. The manifest is provisional
# until acceptance succeeds. On failure, restore the prior manifest (or remove the new
# one) so START_KRISHNA will detect drift and refuse to advertise this release as verified.
if(!$SkipAcceptance){
  $accept=Join-Path $Runtime "scripts\ACCEPT_KRISHNA_RUNTIME.ps1"
  if(!(Test-Path $accept)){throw "Runtime acceptance harness missing: $accept"}
  & powershell -NoProfile -ExecutionPolicy Bypass -File $accept -RuntimeRoot $Runtime -SourceRoot $Source
  if($LASTEXITCODE -ne 0){
    if($null -ne $previousManifest){$previousManifest|Set-Content -Encoding UTF8 $dest}
    elseif(Test-Path $dest){Remove-Item -Force $dest}
    throw "KRISHNA runtime acceptance failed; provisional manifest rolled back; refusing final start"
  }
}

Write-Host "DEPLOY VERIFIED AT $Head" -ForegroundColor Green
Write-Host "MANIFEST $dest ($($hashes.Count) files)" -ForegroundColor Green

# Non-destructive E: audit after every verified deployment.
$audit=Join-Path $Runtime "scripts\AUDIT_KRISHNA_E_DRIVE.ps1"
if(Test-Path $audit){
  & powershell -NoProfile -ExecutionPolicy Bypass -File $audit | Out-Host
}

if(!$SkipStart){
  $env:KRISHNA_ALLOW_ACTIONS="1"
  & "$Runtime\scripts\START_KRISHNA.ps1"
}

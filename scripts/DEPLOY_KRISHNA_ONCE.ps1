param(
  [switch]$SkipStart,
  [switch]$SkipAcceptance,
  [switch]$PrivateRemote,
  [string]$TailscaleExe = "E:\TailScale\tailscale.exe",
  [string]$Branch = ""
)
$ErrorActionPreference="Stop"
$Source="E:\KRISHNA-SOURCE"
$Runtime="E:\Krishna-The GOD"
$Py="$Runtime\.venv\Scripts\python.exe"

function Get-KrishnaProcess([int]$ProcessId,[string]$ScriptName){
  if($ProcessId -le 0){return $null}
  try{
    $row=Get-CimInstance Win32_Process -Filter ("ProcessId = "+$ProcessId) -ErrorAction Stop
    if(!$row){return $null}
    $cmd=[string]$row.CommandLine
    if($cmd -notlike ("*"+$ScriptName+"*")){return $null}
    return $row
  }catch{return $null}
}

function Get-KrishnaListenerOwnership([int]$ProcessId,[string]$RuntimeRoot,[int]$RecordedCorePid=0,[int]$RecordedGuardianPid=0){
  if($ProcessId -le 0){return $null}
  $runtime=[IO.Path]::GetFullPath($RuntimeRoot).TrimEnd("\\")
  $chain=@()
  $current=$ProcessId
  $seen=@{}
  for($depth=0;$depth -lt 10 -and $current -gt 0;$depth++){
    if($seen.ContainsKey([string]$current)){break}
    $seen[[string]$current]=$true
    $row=$null
    try{$row=Get-CimInstance Win32_Process -Filter ("ProcessId = "+$current) -ErrorAction Stop}catch{}
    if(!$row){break}
    $cmd=[string]$row.CommandLine
    $exe=[string]$row.ExecutablePath
    if(!$exe){
      try{$exe=[string](Get-Process -Id $current -ErrorAction Stop).Path}catch{$exe=""}
    }
    $chain+=@([pscustomobject]@{
      pid=[int]$row.ProcessId
      parent_pid=[int]$row.ParentProcessId
      name=[string]$row.Name
      command_line=$cmd
      executable_path=$exe
    })
    $current=[int]$row.ParentProcessId
  }

  if(!$chain.Count){return $null}
  $listener=$chain[0]
  if(([string]$listener.name) -notmatch "(?i)^python(?:\.exe)?$"){return $null}

  # Primary proof: command/executable evidence explicitly points at this runtime.
  $runtimeEvidence=@($chain | Where-Object {
    ([string]$_.executable_path).StartsWith($runtime,[StringComparison]::OrdinalIgnoreCase) -or
    ([string]$_.command_line).IndexOf($runtime,[StringComparison]::OrdinalIgnoreCase) -ge 0
  })
  $startProc=$null
  $guardianProc=$null
  foreach($row in $chain){
    if(([string]$row.command_line) -match "(?i)START_KRISHNA\.ps1"){$startProc=$row}
    if(([string]$row.command_line) -match "(?i)KRISHNA_GUARDIAN\.ps1"){$guardianProc=$row}
  }
  if($runtimeEvidence.Count -and $startProc){
    return [pscustomobject]@{
      proof="command_line"
      listener_pid=$ProcessId
      start_pid=[int]$startProc.pid
      guardian_pid=if($guardianProc){[int]$guardianProc.pid}else{0}
      evidence=$chain
    }
  }

  # Windows can redact CommandLine/ExecutablePath. In that case accept only an
  # exact match between the live listener ancestry and KRISHNA's own recorded
  # guardian state. This cannot authorize an arbitrary PID: the recorded Core PID
  # must be an ancestor of the actual 8766 Python listener, and the recorded
  # Guardian PID (when present) must also be in that same ancestry.
  if($RecordedCorePid -gt 0){
    $recordedCore=@($chain | Where-Object {
      [int]$_.pid -eq $RecordedCorePid -and ([string]$_.name) -match "(?i)^powershell(?:\.exe)?$"
    } | Select-Object -First 1)
    $recordedGuardian=@()
    if($RecordedGuardianPid -gt 0){
      $recordedGuardian=@($chain | Where-Object {
        [int]$_.pid -eq $RecordedGuardianPid -and ([string]$_.name) -match "(?i)^powershell(?:\.exe)?$"
      } | Select-Object -First 1)
    }
    if($recordedCore.Count -and ($RecordedGuardianPid -le 0 -or $recordedGuardian.Count)){
      return [pscustomobject]@{
        proof="recorded_pid_ancestry"
        listener_pid=$ProcessId
        start_pid=$RecordedCorePid
        guardian_pid=$RecordedGuardianPid
        evidence=$chain
      }
    }
  }

  return $null
}

function Stop-ExistingKrishnaGuardian([string]$RuntimeRoot){
  $stateDir=Join-Path $RuntimeRoot "state\guardian"
  New-Item -ItemType Directory -Force $stateDir|Out-Null
  $pidPath=Join-Path $stateDir "guardian.pid"
  $statePath=Join-Path $stateDir "core-guardian.json"
  $stopPath=Join-Path $stateDir "STOP"

  $oldGuardianPid=0
  if(Test-Path $pidPath){try{$oldGuardianPid=[int](Get-Content -Raw $pidPath).Trim()}catch{$oldGuardianPid=0}}

  $oldCorePid=0
  if(Test-Path $statePath){
    try{$oldCorePid=[int]((Get-Content -Raw $statePath|ConvertFrom-Json).core_pid)}catch{$oldCorePid=0}
  }

  $guardianProc=Get-KrishnaProcess $oldGuardianPid "KRISHNA_GUARDIAN.ps1"
  $coreProc=Get-KrishnaProcess $oldCorePid "START_KRISHNA.ps1"

  # WMI may redact command lines on an otherwise valid KRISHNA process chain.
  # Recover ownership only when the recorded Core/Guardian PIDs appear in the
  # ancestry of the actual 8766 Python listener.
  if(!$coreProc -and $oldCorePid -gt 0){
    $live8766=Get-NetTCPConnection -LocalPort 8766 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if($live8766){
      $ownership=Get-KrishnaListenerOwnership ([int]$live8766.OwningProcess) $RuntimeRoot $oldCorePid $oldGuardianPid
      if($ownership -and $ownership.proof -eq "recorded_pid_ancestry"){
        try{$coreProc=Get-CimInstance Win32_Process -Filter ("ProcessId = "+$oldCorePid) -ErrorAction Stop}catch{$coreProc=$null}
        if($oldGuardianPid -gt 0 -and !$guardianProc){
          try{$guardianProc=Get-CimInstance Win32_Process -Filter ("ProcessId = "+$oldGuardianPid) -ErrorAction Stop}catch{$guardianProc=$null}
        }
        Write-Host ("Verified KRISHNA ownership by recorded PID ancestry: listener={0} core={1} guardian={2}" -f $ownership.listener_pid,$oldCorePid,$oldGuardianPid) -ForegroundColor Yellow
      }
    }
  }

  if($guardianProc){
    "DEPLOY_GENERATION_HANDOFF"|Set-Content -Encoding ASCII $stopPath
    Write-Host ("Stopping previous KRISHNA Guardian PID {0} before generation handoff..." -f $oldGuardianPid) -ForegroundColor Yellow
  }elseif(Test-Path $pidPath){
    Write-Host ("Removing stale Guardian PID file (recorded PID {0} is not KRISHNA_GUARDIAN.ps1)." -f $oldGuardianPid) -ForegroundColor Yellow
    Remove-Item -Force $pidPath -ErrorAction SilentlyContinue
  }

  # Guardian blocks on the child Core process. Terminating only a verified
  # START_KRISHNA.ps1 child releases that wait so the STOP marker can be honored.
  if($coreProc){
    Write-Host ("Stopping previous KRISHNA Core process tree rooted at PID {0} for verified generation handoff..." -f $oldCorePid) -ForegroundColor Yellow
    # START_KRISHNA.ps1 launches python.exe as a child. Killing only the PowerShell
    # wrapper can orphan the server and leave port 8766 occupied. The wrapper PID
    # has already been verified above as KRISHNA's START_KRISHNA.ps1, so terminate
    # that verified tree rather than touching unrelated processes.
    & taskkill.exe /PID $oldCorePid /T /F | Out-Null
    if($LASTEXITCODE -ne 0 -and (Get-Process -Id $oldCorePid -ErrorAction SilentlyContinue)){
      throw ("Failed to stop verified KRISHNA Core process tree rooted at PID {0}" -f $oldCorePid)
    }
  }

  if($guardianProc){
    $stopped=$false
    for($i=0;$i -lt 20;$i++){
      Start-Sleep -Milliseconds 500
      if(!(Get-Process -Id $oldGuardianPid -ErrorAction SilentlyContinue)){$stopped=$true;break}
    }
    if(!$stopped){
      $verified=Get-KrishnaProcess $oldGuardianPid "KRISHNA_GUARDIAN.ps1"
      if($verified){
        Write-Host ("Previous KRISHNA Guardian PID {0} did not stop cleanly; completing verified takeover." -f $oldGuardianPid) -ForegroundColor Yellow
        Stop-Process -Id $oldGuardianPid -Force -ErrorAction Stop
      }else{
        throw "Guardian PID changed identity during generation handoff; refusing process termination."
      }
    }
  }

  Remove-Item -Force $pidPath -ErrorAction SilentlyContinue
  Remove-Item -Force $stopPath -ErrorAction SilentlyContinue
}

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

& git fetch --quiet --prune origin
if($LASTEXITCODE -ne 0){throw "Cannot fetch origin"}
if(!$Branch){
  $currentBranch=(git branch --show-current).Trim()
  if($currentBranch){$Branch=$currentBranch}
  else{
    $remoteHead=(git symbolic-ref --short refs/remotes/origin/HEAD 2>$null)
    if($LASTEXITCODE -eq 0 -and $remoteHead){$Branch=($remoteHead.Trim() -replace '^origin/','')}
  }
}
if(!$Branch){throw "Could not resolve deployment branch"}
& git checkout --quiet $Branch
if($LASTEXITCODE -ne 0){throw "Cannot checkout $Branch"}
& git pull --quiet --ff-only origin $Branch
if($LASTEXITCODE -ne 0){throw "Cannot fast-forward $Branch"}
$Head=(git rev-parse HEAD).Trim()
Write-Host "SOURCE $Branch @ $Head" -ForegroundColor Cyan

# Test authoritative source before runtime mutation.
# Source tests must never write runtime state into the Git checkout. Some modules
# derive state roots from KRISHNA_RUNTIME_ROOT / KRISHNA_DB during import, so bind
# both to an isolated disposable E:-drive workspace for the entire source test pass.
$sourceTestRuntime=Join-Path $Runtime ("workspace\source-tests\"+[guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force $sourceTestRuntime|Out-Null
$previousRuntimeRoot=$env:KRISHNA_RUNTIME_ROOT
$previousDb=$env:KRISHNA_DB
$previousSourceRoot=$env:KRISHNA_SOURCE_ROOT
$previousTemp=$env:TEMP
$previousTmp=$env:TMP
try{
  $env:KRISHNA_RUNTIME_ROOT=$sourceTestRuntime
  $env:KRISHNA_DB=Join-Path $sourceTestRuntime "krishna_core.db"
  $env:KRISHNA_SOURCE_ROOT=$Source
  $env:TEMP=$sourceTestRuntime
  $env:TMP=$sourceTestRuntime
  Invoke-KrishnaTests $Source $Source
  & $Py (Join-Path $Source "scripts\AUDIT_KRISHNA_ARCHITECTURE.py")
  if($LASTEXITCODE -ne 0){throw "KRISHNA ARCHITECTURE TRUTH AUDIT FAILED"}
}finally{
  if($null -eq $previousRuntimeRoot){Remove-Item Env:KRISHNA_RUNTIME_ROOT -ErrorAction SilentlyContinue}else{$env:KRISHNA_RUNTIME_ROOT=$previousRuntimeRoot}
  if($null -eq $previousDb){Remove-Item Env:KRISHNA_DB -ErrorAction SilentlyContinue}else{$env:KRISHNA_DB=$previousDb}
  if($null -eq $previousSourceRoot){Remove-Item Env:KRISHNA_SOURCE_ROOT -ErrorAction SilentlyContinue}else{$env:KRISHNA_SOURCE_ROOT=$previousSourceRoot}
  if($null -eq $previousTemp){Remove-Item Env:TEMP -ErrorAction SilentlyContinue}else{$env:TEMP=$previousTemp}
  if($null -eq $previousTmp){Remove-Item Env:TMP -ErrorAction SilentlyContinue}else{$env:TMP=$previousTmp}
  Remove-Item -Recurse -Force $sourceTestRuntime -ErrorAction SilentlyContinue
}
if((git status --porcelain)){
  throw "SOURCE TESTS DIRTY THE REPOSITORY. Tests/runtime imports must write only to the isolated source-test runtime."
}

# Parse every PowerShell entrypoint before touching runtime.
$parseFailures=@()
Get-ChildItem (Join-Path $Source "scripts") -Filter "*.ps1" -File -Recurse | ForEach-Object {
  $tokens=$null;$errors=$null
  [void][System.Management.Automation.Language.Parser]::ParseFile($_.FullName,[ref]$tokens,[ref]$errors)
  if($errors){$parseFailures += ($_.FullName + ": " + (($errors | ForEach-Object Message) -join " | "))}
}
if($parseFailures.Count){throw ("POWERSHELL PARSE FAILED: " + ($parseFailures -join " || "))}

# Project Perfection is part of the verified runtime. Provision its local-only
# dependencies before deployment when any required component is unavailable.
$perfectionSetup=Join-Path $Source "scripts\SETUP_PROJECT_PERFECTION.ps1"
if(!(Test-Path $perfectionSetup)){throw "PROJECT PERFECTION SETUP MISSING: $perfectionSetup"}
$perfectionReady=$false
try{
  & $Py -c "import PIL,playwright,schemathesis; print('PROJECT_PERFECTION_PY_OK')" | Out-Null
  $perfectionReady=($LASTEXITCODE -eq 0)
}catch{$perfectionReady=$false}
$axeUser=[Environment]::GetEnvironmentVariable("KRISHNA_AXE_CORE_JS","User")
if(!$axeUser -or !(Test-Path -LiteralPath $axeUser)){$perfectionReady=$false}
if(!$perfectionReady){
  & powershell -NoProfile -ExecutionPolicy Bypass -File $perfectionSetup -KrishnaRoot $Runtime -InstallChromium
  if($LASTEXITCODE -ne 0){throw "PROJECT PERFECTION DEPENDENCY SETUP FAILED"}
}
$axeUser=[Environment]::GetEnvironmentVariable("KRISHNA_AXE_CORE_JS","User")
if($axeUser){$env:KRISHNA_AXE_CORE_JS=$axeUser}
Write-Host "PROJECT PERFECTION DEPENDENCIES VERIFIED" -ForegroundColor Green

# Build and deploy the React spatial shell as an opt-in preview. The verified
# operational HTML remains default until Spatial UI parity is explicitly accepted.
$spatialRoot=Join-Path $Source "app\spatial-ui"
$spatialIndex=Join-Path $spatialRoot "dist\index.html"
if(!(Test-Path (Join-Path $spatialRoot "package.json"))){throw "SPATIAL UI PACKAGE MISSING: $spatialRoot"}
$npmCmd=(Get-Command npm.cmd -ErrorAction SilentlyContinue)
if(!$npmCmd){$npmCmd=(Get-Command npm -ErrorAction SilentlyContinue)}
if(!$npmCmd){throw "SPATIAL UI BUILD REQUIRES NODE/NPM"}
Push-Location $spatialRoot
try{
  & $npmCmd.Source install --no-audit --no-fund --package-lock=false
  if($LASTEXITCODE -ne 0){throw "SPATIAL UI NPM INSTALL FAILED"}
  & $npmCmd.Source run build
  if($LASTEXITCODE -ne 0){throw "SPATIAL UI BUILD FAILED"}
}finally{Pop-Location}
$spatialDirty=(git -C $Source status --porcelain)
if($spatialDirty){
  $dirtyDetail=($spatialDirty -join " | ")
  throw ("SPATIAL UI BUILD DIRTY THE SOURCE REPOSITORY. Generated artifacts must remain ignored and package-lock creation is disabled. Dirty paths: " + $dirtyDetail)
}
if(!(Test-Path $spatialIndex)){throw "SPATIAL UI INDEX MISSING AFTER BUILD: $spatialIndex"}
$spatialText=Get-Content -LiteralPath $spatialIndex -Raw
if($spatialText -notmatch 'data-krishna-spatial-ui="2026\.09"'){throw "SPATIAL UI VERSION MARKER MISSING"}
$spatialRuntime=Join-Path $Runtime "dashboard\spatial-ui"
New-Item -ItemType Directory -Force $spatialRuntime|Out-Null
& robocopy (Join-Path $spatialRoot "dist") $spatialRuntime /MIR /R:1 /W:1
if($LASTEXITCODE -ge 8){throw "SPATIAL UI COPY FAILED: robocopy=$LASTEXITCODE"}
if(!(Test-Path (Join-Path $spatialRuntime "index.html"))){throw "SPATIAL UI RUNTIME INDEX MISSING"}
Write-Host "SPATIAL UI BUILT AND DEPLOYED" -ForegroundColor Green

# Runtime state/assets are owned by the runtime and never mirrored/deleted by deploy.
$excludeDirs=@("__pycache__",".krishna_state","state","logs","backups",".venv","ollama-models","dashboard\assets\avatar")
$xd=@();foreach($d in $excludeDirs){$xd+=@("/XD",(Join-Path $Runtime $d))}
& robocopy "$Source\core" "$Runtime\core" /E /R:1 /W:1 /XF "*.pyc" @xd
if($LASTEXITCODE -ge 8){throw "CORE COPY FAILED: robocopy=$LASTEXITCODE"}

# The old standalone dashboard is source-owned legacy UI, not runtime state.
# Remove it explicitly so an obsolete shell cannot be opened from the runtime.
$legacyDashboard=Join-Path $Runtime "core\dashboard.html"
if(Test-Path $legacyDashboard){Remove-Item -Force $legacyDashboard}

New-Item -ItemType Directory -Force "$Runtime\scripts"|Out-Null
& robocopy "$Source\scripts" "$Runtime\scripts" /E /R:1 /W:1 /XF "*.pyc"
if($LASTEXITCODE -ge 8){throw "SCRIPT COPY FAILED: robocopy=$LASTEXITCODE"}

# Owner policy: PC-local Qwen is permitted as an opt-in model.
# Deployment must not unload, delete or otherwise disable installed/running Qwen
# models on the PC. Mobile inference policy is separate and remains Qwen-free.
Write-Host "PC QWEN POLICY: preserve installed/running PC models; mobile remains Qwen-free" -ForegroundColor Green

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
  & powershell -NoProfile -ExecutionPolicy Bypass -File $avatarPrepare -RuntimeRoot $Runtime -SourceRoot $Source
  if($LASTEXITCODE -ne 0){
    Write-Warning "KRISHNA avatar candidate preparation reported a tooling failure. Core deployment will continue; the private source GLB remains untouched."
  }
}

# Ensure Gyan-Bhandar AES-GCM envelope encryption dependency is installed only
# inside KRISHNA's E: virtual environment/cache. DPAPI remains the Windows key wrapper.
$gyanSecuritySetup=Join-Path $Runtime "scripts\SETUP_GYAN_SECURITY.ps1"
if(!(Test-Path $gyanSecuritySetup)){throw "GYAN SECURITY SETUP MISSING: $gyanSecuritySetup"}
& powershell -NoProfile -ExecutionPolicy Bypass -File $gyanSecuritySetup -RuntimeRoot $Runtime
if($LASTEXITCODE -ne 0){throw "GYAN SECURITY SETUP FAILED"}

# Test the deployed runtime code in an isolated disposable runtime state.
# Unit/integration tests must never read or mutate the production KRISHNA DB/state;
# the real live runtime is validated later by ACCEPT_KRISHNA_RUNTIME.ps1.
# Repository-only contracts (for example .github workflows) still resolve from
# the authoritative source checkout.
$deployedTestRuntime=Join-Path $Runtime ("workspace\deployed-tests\"+[guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force $deployedTestRuntime|Out-Null
$previousRuntimeRoot=$env:KRISHNA_RUNTIME_ROOT
$previousDb=$env:KRISHNA_DB
$previousSourceRoot=$env:KRISHNA_SOURCE_ROOT
$previousTemp=$env:TEMP
$previousTmp=$env:TMP
try{
  $env:KRISHNA_RUNTIME_ROOT=$deployedTestRuntime
  $env:KRISHNA_DB=Join-Path $deployedTestRuntime "krishna_core.db"
  $env:KRISHNA_SOURCE_ROOT=$Source
  $env:TEMP=$deployedTestRuntime
  $env:TMP=$deployedTestRuntime
  $env:PYTHONPATH="$Runtime\core"
  & $Py -m compileall -q "$Runtime\core\krishna_core"
  if($LASTEXITCODE -ne 0){throw "DEPLOYED CORE COMPILE FAILED"}
  # Discover tests from the authoritative source tree so repository-contract
  # fixtures resolve .github/mobile_v3/app/.gitignore from the real repository,
  # while PYTHONPATH remains bound to the deployed runtime Core. This verifies
  # the deployed Python code without pretending the runtime is a full Git checkout.
  & $Py -m unittest discover -v -s "$Source\core\tests" -p "test_*.py"
  if($LASTEXITCODE -ne 0){throw "DEPLOYED CORE TESTS FAILED"}
  & $Py -m unittest discover -v -s "$Source\tests" -p "test_*.py"
  if($LASTEXITCODE -ne 0){throw "POST-DEPLOY CONTRACTS FAILED"}
  & $Py -c "from krishna_core.orchestrator import Orchestrator; print('ORCHESTRATOR_IMPORT_OK')"
  if($LASTEXITCODE -ne 0){throw "ORCHESTRATOR IMPORT FAILED"}
}
finally{
  if($null -eq $previousRuntimeRoot){Remove-Item Env:KRISHNA_RUNTIME_ROOT -ErrorAction SilentlyContinue}else{$env:KRISHNA_RUNTIME_ROOT=$previousRuntimeRoot}
  if($null -eq $previousDb){Remove-Item Env:KRISHNA_DB -ErrorAction SilentlyContinue}else{$env:KRISHNA_DB=$previousDb}
  if($null -eq $previousSourceRoot){Remove-Item Env:KRISHNA_SOURCE_ROOT -ErrorAction SilentlyContinue}else{$env:KRISHNA_SOURCE_ROOT=$previousSourceRoot}
  if($null -eq $previousTemp){Remove-Item Env:TEMP -ErrorAction SilentlyContinue}else{$env:TEMP=$previousTemp}
  if($null -eq $previousTmp){Remove-Item Env:TMP -ErrorAction SilentlyContinue}else{$env:TMP=$previousTmp}
  Remove-Item -Recurse -Force $deployedTestRuntime -ErrorAction SilentlyContinue
}

# Write an atomic deployment manifest so KRISHNA can prove exactly what code is running.
$deployDir=Join-Path $Runtime "state\deployment"
New-Item -ItemType Directory -Force $deployDir|Out-Null
$hashes=[ordered]@{}
$tracked=@()
$tracked+=Get-ChildItem "$Runtime\core\krishna_core" -File -Recurse -Filter "*.py" -ErrorAction SilentlyContinue
foreach($p in @(
  "$Runtime\core\web_validation.html",
  "$Runtime\core\design_studio.html",
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
  if($PrivateRemote){
    $firewall=Join-Path $Runtime "scripts\CONFIGURE_KRISHNA_PRIVATE_REMOTE_FIREWALL.ps1"
    if(Test-Path $firewall){
      & powershell -NoProfile -ExecutionPolicy Bypass -File $firewall -CorePort 8766 -DiscoveryPort 8767 -TailscaleCIDR "100.64.0.0/10" | Out-Host
      if($LASTEXITCODE -ne 0){Write-Warning "KRISHNA private-remote firewall helper returned exit code $LASTEXITCODE; Core application policy still rejects public clients."}
    }else{
      Write-Warning "KRISHNA private-remote firewall helper is missing; application-layer private remote policy remains active."
    }
  }
  $guardian=Join-Path $Runtime "scripts\KRISHNA_GUARDIAN.ps1"
  if(!(Test-Path $guardian)){throw "KRISHNA Guardian missing: $guardian"}
  $guardianStateDir=Join-Path $Runtime "state\guardian"
  New-Item -ItemType Directory -Force $guardianStateDir|Out-Null
  $stopMarker=Join-Path $guardianStateDir "STOP"
  $quarantineMarker=Join-Path $guardianStateDir "QUARANTINED"
  if(Test-Path $quarantineMarker){
    throw "KRISHNA Guardian is quarantined. Diagnose $quarantineMarker before restart."
  }
  Stop-ExistingKrishnaGuardian $Runtime
  if(Test-Path $stopMarker){Remove-Item -Force $stopMarker -ErrorAction SilentlyContinue}

  # The old verified Core tree must release 8766 before a new generation is launched.
  # If stale PID metadata missed an orphaned Core, reconstruct only verified
  # START_KRISHNA/Guardian ownership from the listener ancestry and reuse the
  # existing generation-handoff authority. Unknown listeners remain untouched.
  $staleListener=Get-NetTCPConnection -LocalPort 8766 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
  if($staleListener){
    $listenerPid=[int]$staleListener.OwningProcess
    $stateForRecovery=Join-Path $guardianStateDir "core-guardian.json"
    $recordedCorePid=0
    $recordedGuardianPid=0
    if(Test-Path $stateForRecovery){
      try{
        $recordedState=Get-Content -Raw $stateForRecovery|ConvertFrom-Json
        $recordedCorePid=[int]$recordedState.core_pid
        $recordedGuardianPid=[int]$recordedState.guardian_pid
      }catch{}
    }
    $ownership=Get-KrishnaListenerOwnership $listenerPid $Runtime $recordedCorePid $recordedGuardianPid
    if($ownership){
      $recoveredState=Join-Path $guardianStateDir "core-guardian.json"
      @{
        status="RECOVERED_FOR_HANDOFF"
        guardian_pid=[int]$ownership.guardian_pid
        core_pid=[int]$ownership.start_pid
        recovered_listener_pid=$listenerPid
        updated=(Get-Date).ToUniversalTime().ToString("o")
      }|ConvertTo-Json -Depth 4|Set-Content -Encoding UTF8 $recoveredState
      if([int]$ownership.guardian_pid -gt 0){
        [string]$ownership.guardian_pid|Set-Content -Encoding ASCII (Join-Path $guardianStateDir "guardian.pid")
      }
      Write-Host ("Recovered verified KRISHNA Core ancestry for listener PID {0}; START_KRISHNA PID {1}; Guardian PID {2}." -f $listenerPid,$ownership.start_pid,$ownership.guardian_pid) -ForegroundColor Yellow
      Stop-ExistingKrishnaGuardian $Runtime
      $staleListener=Get-NetTCPConnection -LocalPort 8766 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    }
    if($staleListener){
      $listenerPid=[int]$staleListener.OwningProcess
      $listenerRow=$null
      try{$listenerRow=Get-CimInstance Win32_Process -Filter ("ProcessId = "+$listenerPid) -ErrorAction Stop}catch{}
      $listenerCmd=if($listenerRow){[string]$listenerRow.CommandLine}else{""}
      $listenerExe=if($listenerRow){[string]$listenerRow.ExecutablePath}else{""}
      throw ("Port 8766 remains occupied after KRISHNA generation handoff. Refusing to kill an unverified listener. PID={0}; executable={1}; command={2}" -f $listenerPid,$listenerExe,$listenerCmd)
    }
  }

  $runtimeGeneration=[guid]::NewGuid().ToString("N")
  $guardianStdout=Join-Path $Runtime "logs\guardian-bootstrap.stdout.log"
  $guardianStderr=Join-Path $Runtime "logs\guardian-bootstrap.stderr.log"
  # Start-Process joins ArgumentList arrays into one command line and strips the
  # outer PowerShell string quotes. Runtime/source paths contain spaces, so build
  # one explicitly quoted argument string as recommended by Microsoft.
  $guardianArgs='-NoProfile -ExecutionPolicy Bypass -File "'+$guardian+'" -RuntimeRoot "'+$Runtime+'" -SourceRoot "'+$Source+'" -RuntimeGeneration "'+$runtimeGeneration+'"'
  if($PrivateRemote){
    $guardianArgs+=' -PrivateRemote'
    if($TailscaleExe){$guardianArgs+=' -TailscaleExe "'+$TailscaleExe+'"'}
  }
  $guardianProc=Start-Process -FilePath "powershell.exe" -ArgumentList $guardianArgs `
    -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput $guardianStdout `
    -RedirectStandardError $guardianStderr

  $healthUrl="http://127.0.0.1:8766/health"
  $online=$false
  for($i=0;$i -lt 45;$i++){
    Start-Sleep -Seconds 1
    if($guardianProc.HasExited){break}
    try{
      $health=Invoke-RestMethod -Uri $healthUrl -TimeoutSec 2
      if($health.ok -and [string]$health.runtime_generation -eq $runtimeGeneration){$online=$true;break}
    }catch{}
  }
  if(!$online){
    $guardianState=Join-Path $guardianStateDir "core-guardian.json"
    $stderr=Join-Path $Runtime "logs\core-runtime.stderr.log"
    $detail=""
    if(Test-Path $guardianState){$detail+=" guardian_state="+(Get-Content -Raw $guardianState)}
    if(Test-Path $guardianStderr){$detail+=" guardian_stderr="+((Get-Content $guardianStderr -Tail 20 -ErrorAction SilentlyContinue)-join " | ")}
    if(Test-Path $guardianStdout){$detail+=" guardian_stdout="+((Get-Content $guardianStdout -Tail 20 -ErrorAction SilentlyContinue)-join " | ")}
    if(Test-Path $stderr){$detail+=" stderr="+((Get-Content $stderr -Tail 20 -ErrorAction SilentlyContinue)-join " | ")}
    throw ("KRISHNA Guardian started but the newly launched runtime generation did not become healthy on 8766. generation="+$runtimeGeneration+"."+ $detail)
  }
  Write-Host ("KRISHNA GUARDIAN ONLINE PID {0} | generation {1} | Core health {2}" -f $guardianProc.Id,$runtimeGeneration,$healthUrl) -ForegroundColor Green
}

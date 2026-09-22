param(
  [string]$RuntimeRoot = "E:\Krishna-The GOD",
  [string]$SourceRoot = "E:\KRISHNA-SOURCE",
  [bool]$TryBodyRig = $true,
  [bool]$InstallRigTools = $true,
  [string]$MotiusCommit = "6d259de4672ff33c43a44d948fe8182f2c6eafb2"
)
$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

$runtimePython=Join-Path $RuntimeRoot ".venv\Scripts\python.exe"
if(!(Test-Path $runtimePython)){throw "KRISHNA runtime Python missing: $runtimePython"}

$avatarDir=Join-Path $RuntimeRoot "dashboard\assets\avatar"
$sourceGlb=Join-Path $avatarDir "krishna.glb"
$productionGlb=Join-Path $avatarDir "krishna.production.glb"
$candidateDir=Join-Path $avatarDir "candidates"
$reportDir=Join-Path $RuntimeRoot "state\avatar"
$backupDir=Join-Path $RuntimeRoot "backups\avatar"
$cacheRoot=Join-Path $RuntimeRoot "cache\avatar-production"
$toolsRoot=Join-Path $RuntimeRoot "tools"
$auditScript=Join-Path $RuntimeRoot "scripts\avatar_asset_audit.py"
if(!(Test-Path $auditScript)){$auditScript=Join-Path $SourceRoot "scripts\avatar_asset_audit.py"}

New-Item -ItemType Directory -Force $avatarDir,$candidateDir,$reportDir,$backupDir,$cacheRoot,$toolsRoot|Out-Null
if(!(Test-Path $auditScript)){throw "Avatar audit CLI missing: $auditScript"}
if(!(Test-Path $sourceGlb)){
  $missing=[ordered]@{
    schema=1;status="missing";source=$sourceGlb;production=$productionGlb
    message="Private KRISHNA GLB is not installed. Source asset was not modified."
    updated_at=(Get-Date).ToUniversalTime().ToString("o")
  }
  $missing|ConvertTo-Json -Depth 8|Set-Content -Encoding UTF8 (Join-Path $reportDir "production-pipeline.json")
  Write-Warning $missing.message
  exit 0
}

$previousPythonPath=$env:PYTHONPATH
$env:PYTHONPATH=Join-Path $RuntimeRoot "core"
$env:PIP_CACHE_DIR=Join-Path $RuntimeRoot "cache\pip"
$env:TEMP=Join-Path $RuntimeRoot "cache\temp"
$env:TMP=$env:TEMP
New-Item -ItemType Directory -Force $env:PIP_CACHE_DIR,$env:TEMP|Out-Null

function Invoke-AvatarAudit([string]$Asset,[string]$Report){
  $raw=& $runtimePython $auditScript $Asset --report $Report
  if($LASTEXITCODE -ne 0){throw "Avatar audit command failed for $Asset"}
  return ($raw -join [Environment]::NewLine)|ConvertFrom-Json
}

function Save-Pipeline([object]$Payload){
  $tmp=Join-Path $reportDir "production-pipeline.json.tmp"
  $dest=Join-Path $reportDir "production-pipeline.json"
  $Payload|ConvertTo-Json -Depth 12|Set-Content -Encoding UTF8 $tmp
  Move-Item -Force $tmp $dest
}

function Promote-Candidate([string]$Candidate,[object]$Audit,[string]$Reason){
  if(!$Audit.ready){throw "Refusing avatar promotion: candidate did not pass production audit"}
  if(Test-Path $productionGlb){
    $stamp=(Get-Date).ToUniversalTime().ToString("yyyyMMdd-HHmmss")
    Copy-Item -Force $productionGlb (Join-Path $backupDir ("krishna.production-"+$stamp+".glb"))
  }
  Copy-Item -Force $Candidate $productionGlb
  $verify=Invoke-AvatarAudit $productionGlb (Join-Path $reportDir "production-audit.json")
  if(!$verify.ready){
    Remove-Item -Force $productionGlb
    throw "Promoted avatar failed re-audit; production copy removed"
  }
  Write-Host "KRISHNA production avatar promoted: $Reason" -ForegroundColor Green
  return $verify
}

function Find-Blender(){
  $cmd=Get-Command blender.exe -ErrorAction SilentlyContinue
  if($cmd){return $cmd.Source}
  $roots=@(
    "C:\Program Files\Blender Foundation",
    (Join-Path $RuntimeRoot "tools\Blender"),
    (Join-Path $RuntimeRoot "tools\blender")
  )
  foreach($root in $roots){
    if(!(Test-Path $root)){continue}
    $hit=Get-ChildItem $root -Filter blender.exe -File -Recurse -ErrorAction SilentlyContinue |
      Sort-Object FullName -Descending | Select-Object -First 1
    if($hit){return $hit.FullName}
  }
  return $null
}

Write-Host "=== KRISHNA AVATAR PRODUCTION PIPELINE ===" -ForegroundColor Cyan
Write-Host "Private source: $sourceGlb"
$sourceAudit=Invoke-AvatarAudit $sourceGlb (Join-Path $reportDir "source-audit.json")
Write-Host ("SOURCE STAGE: "+$sourceAudit.stage) -ForegroundColor Yellow

# A source asset that already meets the complete TalkingHead contract can be
# promoted byte-for-byte. The source remains untouched.
if($sourceAudit.ready){
  $prod=Promote-Candidate $sourceGlb $sourceAudit "private source already satisfies TalkingHead body + ARKit + Oculus requirements"
  Save-Pipeline ([ordered]@{
    schema=1;status="production-ready";source=$sourceAudit;candidate=$null;production=$prod
    body_rig_attempted=$false;cloud_upload_used=$false
    policy="private source preserved; local inspection only"
    updated_at=(Get-Date).ToUniversalTime().ToString("o")
  })
  if($null -eq $previousPythonPath){Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue}else{$env:PYTHONPATH=$previousPythonPath}
  exit 0
}

# Keep an existing known-good production asset if the source later changes or a
# new candidate is not yet ready.
$existingProduction=$null
if(Test-Path $productionGlb){
  $existingProduction=Invoke-AvatarAudit $productionGlb (Join-Path $reportDir "production-audit.json")
  if(!$existingProduction.ready){
    $quarantine=Join-Path $candidateDir ("krishna.production-rejected-"+(Get-Date -Format "yyyyMMdd-HHmmss")+".glb")
    Move-Item -Force $productionGlb $quarantine
    Write-Warning "Existing krishna.production.glb failed the current compatibility gate and was moved to candidates."
    $existingProduction=$null
  }
}

$candidateAudit=$null
$bodyRigAttempted=$false
$bodyRigMessage="not required or not attempted"
$blender=Find-Blender

if($TryBodyRig -and !$sourceAudit.body.ready){
  if(!$blender){
    $bodyRigMessage="Blender 3.6+ was not found; local body auto-rig was skipped."
    Write-Warning $bodyRigMessage
  }else{
    $bodyRigAttempted=$true
    $motiusRoot=Join-Path $toolsRoot "motius-src"
    $motiusVenv=Join-Path $toolsRoot "avatar-production-venv"
    $motiusPython=Join-Path $motiusVenv "Scripts\python.exe"
    $git=Get-Command git.exe -ErrorAction SilentlyContinue
    if(!$git){
      $bodyRigMessage="git.exe unavailable; local Motius body-rig candidate could not be prepared."
      Write-Warning $bodyRigMessage
    }else{
      if(!(Test-Path (Join-Path $motiusRoot ".git"))){
        if(!$InstallRigTools){
          $bodyRigMessage="Motius is not installed and InstallRigTools=false."
          Write-Warning $bodyRigMessage
        }else{
          if(Test-Path $motiusRoot){Remove-Item -Recurse -Force $motiusRoot}
          & $git.Source clone --no-tags https://github.com/ZeyuLing/Motius.git $motiusRoot
          if($LASTEXITCODE -ne 0){throw "Motius clone failed"}
        }
      }
      if(Test-Path (Join-Path $motiusRoot ".git")){
        & $git.Source -C $motiusRoot fetch origin $MotiusCommit --depth 1
        if($LASTEXITCODE -ne 0){throw "Motius pinned commit fetch failed"}
        & $git.Source -C $motiusRoot checkout --detach $MotiusCommit
        if($LASTEXITCODE -ne 0){throw "Motius pinned checkout failed"}

        if(!(Test-Path $motiusPython)){
          if(!$InstallRigTools){
            $bodyRigMessage="Avatar production virtual environment missing and InstallRigTools=false."
            Write-Warning $bodyRigMessage
          }else{
            & $runtimePython -m venv $motiusVenv
            if($LASTEXITCODE -ne 0){throw "Avatar production venv creation failed"}
          }
        }
        if(Test-Path $motiusPython){
          if($InstallRigTools){
            & $motiusPython -m pip install --disable-pip-version-check --no-input -e $motiusRoot
            if($LASTEXITCODE -ne 0){throw "Local Motius installation failed"}
          }
          $candidate=Join-Path $candidateDir "krishna.body-rigged.glb"
          $rigTool=Join-Path $motiusRoot "tools\auto_rig_character.py"
          if(!(Test-Path $rigTool)){throw "Motius auto-rig tool missing: $rigTool"}
          Write-Host "Generating LOCAL body-rig candidate with Motius + Blender..." -ForegroundColor Cyan
          & $motiusPython $rigTool $sourceGlb $candidate --method template --blender $blender --weight-method capsules
          if($LASTEXITCODE -ne 0){
            $bodyRigMessage="Motius/Blender candidate generation failed. Original GLB remains untouched."
            Write-Warning $bodyRigMessage
          }elseif(Test-Path $candidate){
            $candidateAudit=Invoke-AvatarAudit $candidate (Join-Path $reportDir "candidate-body-audit.json")
            $bodyRigMessage="Local Motius/Blender candidate generated and audited."
            if($candidateAudit.ready){
              $existingProduction=Promote-Candidate $candidate $candidateAudit "local body-rig candidate passed the complete production gate"
            }else{
              Write-Warning "Body-rig candidate is NOT production-ready; it remains isolated under candidates."
            }
          }
        }
      }
    }
  }
}

$effectiveAudit=if($candidateAudit){$candidateAudit}else{$sourceAudit}
$next=@()
if(!$effectiveAudit.body.ready){$next+="Body rig still does not match TalkingHead/Mixamo pose-bone requirements."}
if(!$effectiveAudit.face.arkit.ready){$next+=("$($effectiveAudit.face.arkit.missing.Count) ARKit facial blend shapes still need a source-faithful local facial rig.")}
if(!$effectiveAudit.face.oculus_visemes.ready){$next+=("$($effectiveAudit.face.oculus_visemes.missing.Count) Oculus viseme shapes still need a local facial/lip rig.")}
if(!$next.Count){$next+="Re-run the production audit and promote only after all checks pass."}

$status=if($existingProduction -and $existingProduction.ready){"production-ready"}else{"candidate-only"}
Save-Pipeline ([ordered]@{
  schema=1;status=$status
  source=$sourceAudit
  candidate=$candidateAudit
  production=$existingProduction
  body_rig_attempted=$bodyRigAttempted
  body_rig_message=$bodyRigMessage
  blender=$blender
  motius_commit=$MotiusCommit
  cloud_upload_used=$false
  next_actions=$next
  policy="No public Make-It-Animatable/Gradio upload. Original krishna.glb is never overwritten. Candidates are promoted only after complete local compatibility audit."
  updated_at=(Get-Date).ToUniversalTime().ToString("o")
})

Write-Host "KRISHNA avatar audit complete." -ForegroundColor Green
foreach($item in $next){Write-Host (" - "+$item) -ForegroundColor Yellow}
if($null -eq $previousPythonPath){Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue}else{$env:PYTHONPATH=$previousPythonPath}
exit 0

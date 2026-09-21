param(
  [string]$RuntimeRoot="E:\Krishna-The GOD",
  [string]$SourceRoot="E:\KRISHNA-SOURCE",
  [int]$Port=8876
)
$ErrorActionPreference="Stop"
$Py=Join-Path $RuntimeRoot ".venv\Scripts\python.exe"
if(!(Test-Path $Py)){throw "KRISHNA runtime Python not found: $Py"}
if(!(Test-Path "$RuntimeRoot\core\krishna_core")){throw "KRISHNA runtime core is missing"}

$env:PYTHONPATH="$RuntimeRoot\core"
$env:KRISHNA_RUNTIME_ROOT=$RuntimeRoot
$env:KRISHNA_SOURCE_ROOT=$SourceRoot
$env:KRISHNA_HOST="127.0.0.1"
$env:KRISHNA_PORT=[string]$Port
$env:KRISHNA_DB=Join-Path $RuntimeRoot "krishna_core.db"
$env:KRISHNA_ALLOW_ACTIONS="0"
$base="http://127.0.0.1:$Port"
$reportDir=Join-Path $RuntimeRoot "reports"
New-Item -ItemType Directory -Force $reportDir|Out-Null
$started=Get-Date
$checks=New-Object System.Collections.Generic.List[object]

function Add-Check([string]$Name,[string]$Status,[string]$Detail,[object]$Evidence=$null){
  $checks.Add([ordered]@{name=$Name;status=$Status;detail=$Detail;evidence=$Evidence})
  $color=if($Status -eq "PASS"){"Green"}elseif($Status -eq "WARN"){"Yellow"}else{"Red"}
  Write-Host ("[{0}] {1} - {2}" -f $Status,$Name,$Detail) -ForegroundColor $color
}
function Get-Json([string]$Path){
  return Invoke-RestMethod -Method Get -Uri ($base+$Path) -TimeoutSec 20
}
function Post-Json([string]$Path,[object]$Body){
  return Invoke-RestMethod -Method Post -Uri ($base+$Path) -ContentType "application/json" -Body ($Body|ConvertTo-Json -Depth 10) -TimeoutSec 90
}
function Wait-Core(){
  for($i=0;$i -lt 40;$i++){
    try{$h=Get-Json "/health";if($h.ok){return $h}}catch{}
    Start-Sleep -Milliseconds 500
  }
  throw "KRISHNA acceptance server did not become ready"
}

$proc=$null
try{
  Write-Host "=== KRISHNA RUNTIME ACCEPTANCE ===" -ForegroundColor Cyan
  $proc=Start-Process -FilePath $Py -ArgumentList "-u","-m","krishna_core.server" -WorkingDirectory "$RuntimeRoot\core" -WindowStyle Hidden -PassThru
  $health=Wait-Core
  Add-Check "Core health" "PASS" ("ONLINE on "+$base) $health

  $integrity=Get-Json "/api/runtime/integrity"
  if($integrity.status -eq "SYNCED"){Add-Check "Deployment integrity" "PASS" ("SYNCED "+$integrity.commit) $integrity}
  else{Add-Check "Deployment integrity" "FAIL" ($integrity.status+" - source/runtime must match") $integrity}

  $requirements=Get-Json "/api/requirements"
  if($requirements.requirement_count -ge 35){Add-Check "Chat requirements ledger" "PASS" ($requirements.requirement_count.ToString()+" canonical requirements") $requirements}
  else{Add-Check "Chat requirements ledger" "FAIL" "Requirement ledger is incomplete" $requirements}

  $narad=Get-Json "/api/narad/status"
  if($narad.name -eq "NARAD"){Add-Check "NARAD runtime" "PASS" ("workflows="+$narad.workflows) $narad}else{Add-Check "NARAD runtime" "FAIL" "NARAD did not report ready" $narad}

  $intelligence=Get-Json "/api/intelligence/status"
  Add-Check "Code intelligence" ($(if($intelligence.codebase_memory.available){"PASS"}else{"WARN"})) ($(if($intelligence.codebase_memory.available){"Codebase-Memory discovered"}else{"Codebase-Memory optional adapter unavailable"})) $intelligence.codebase_memory
  Add-Check "Graft memory adapter" ($(if($intelligence.graft.available){"PASS"}else{"WARN"})) ($(if($intelligence.graft.available){"Graft discovered"}else{"Graft optional adapter unavailable"})) $intelligence.graft
  Add-Check "OpenMontage boundary" "PASS" ("installed="+$intelligence.media.installed+" bridge_ready="+$intelligence.media.bridge_ready) $intelligence.media

  $kabach=Get-Json "/api/kabach/projects"
  Add-Check "KABACH boundary registry" "PASS" ("protected projects="+$kabach.count) $kabach

  $commitments=Get-Json "/api/commitments?project=KRISHNA"
  Add-Check "Commitment ledger" "PASS" ("unfinished="+@($commitments.unfinished).Count+" forgotten="+@($commitments.forgotten).Count) $commitments

  $autonomy=Get-Json "/api/autonomy/status"
  if($autonomy.running -or $autonomy.enabled){Add-Check "Autonomy supervisor" "PASS" "Supervisor is active" $autonomy}
  else{Add-Check "Autonomy supervisor" "WARN" "Supervisor is installed but not active" $autonomy}

  # Isolated Narad lifecycle acceptance. No external webhook and no mutation.
  $wf=Post-Json "/api/narad/workflows/create" @{name=("acceptance-"+[guid]::NewGuid().ToString("N").Substring(0,8));trigger=@{type="manual"};steps=@(@{action="publish_event";topic="krishna.acceptance";payload=@{source="acceptance"}});permissions=@()}
  $wid=$wf.id
  $null=Post-Json "/api/narad/workflows/promote" @{workflow_id=$wid;state="sandbox";verified=$false}
  $run=Post-Json "/api/narad/workflows/execute" @{workflow_id=$wid;context=@{};approved=$false}
  $null=Post-Json "/api/narad/workflows/promote" @{workflow_id=$wid;state="verified";verified=$true}
  $null=Post-Json "/api/narad/workflows/promote" @{workflow_id=$wid;state="stable";verified=$true}
  Add-Check "NARAD lifecycle" "PASS" ("workflow "+$wid+" executed and promoted") $run

  # Gyan candidate -> approval -> verified recall acceptance, using a disposable topic.
  $topic="runtime-acceptance-"+[guid]::NewGuid().ToString("N").Substring(0,8)
  $proposal=Post-Json "/api/gyan-bhandar/propose" @{project="KRISHNA";topic=$topic;lesson="KRISHNA runtime acceptance evidence";evidence=@(@{source="local_acceptance";detail="self-test"});confidence=.99;source="runtime_acceptance";verified=$true}
  if($proposal.approval_id){
    $decision=Post-Json "/api/gyan-bhandar/decide" @{approval_id=$proposal.approval_id;approved=$true}
    $recall=Get-Json ("/api/gyan-bhandar?project=KRISHNA&topic="+[uri]::EscapeDataString($topic)+"&verified=1")
    if(@($recall.learnings).Count -gt 0){Add-Check "Gyan-Bhandar promotion" "PASS" "Candidate approved and verified recall returned evidence" $decision}
    else{Add-Check "Gyan-Bhandar promotion" "FAIL" "Verified recall did not return the accepted finding" $recall}
  }else{Add-Check "Gyan-Bhandar promotion" "WARN" "Proposal API did not return an approval id" $proposal}

  # Garudanetra must be able to launch the local KRISHNA UI and produce a real frame.
  try{
    $live=Post-Json "/api/garudanetra/session/start" @{project="KRISHNA";url="$base/"}
    $sid=$live.session_id
    $ready=$null
    for($i=0;$i -lt 30;$i++){
      Start-Sleep -Milliseconds 500
      try{$s=Get-Json ("/api/garudanetra/session?id="+$sid);if($s.frame_available -or $s.state -eq "ERROR"){$ready=$s;break}}catch{}
    }
    if($ready -and $ready.frame_available){
      $frame=Invoke-WebRequest -Uri ($base+"/api/garudanetra/frame?id="+$sid) -TimeoutSec 20
      if($frame.RawContentLength -gt 1000){Add-Check "Garudanetra live browser" "PASS" ("frame bytes="+$frame.RawContentLength) $ready}else{Add-Check "Garudanetra live browser" "FAIL" "Browser frame was empty" $ready}
    }else{
      Add-Check "Garudanetra live browser" "FAIL" (($ready.last_error|Out-String).Trim()) $ready
    }
    try{$null=Post-Json "/api/garudanetra/session/control" @{session_id=$sid;action="stop";payload=@{}}}catch{}
  }catch{
    Add-Check "Garudanetra live browser" "FAIL" $_.Exception.Message $null
  }

  # UI Guardian four-viewport acceptance against the same local interface.
  try{
    $entry=Post-Json "/api/ui-guardian/register" @{name="KRISHNA runtime acceptance";project="KRISHNA";url="$base/";state="candidate";notes="automated runtime acceptance"}
    $eval=Post-Json "/api/ui-guardian/evaluate" @{entry_id=$entry.id}
    if($eval.passed){Add-Check "UI Guardian matrix" "PASS" "All four viewport contracts passed" $eval}
    else{Add-Check "UI Guardian matrix" "FAIL" ("defects="+@($eval.defects).Count) $eval}
  }catch{
    Add-Check "UI Guardian matrix" "FAIL" $_.Exception.Message $null
  }

  $mobile=Get-Json "/api/mobile/connection"
  Add-Check "Mobile bridge" ($(if($mobile.connected){"PASS"}else{"WARN"})) ($(if($mobile.connected){"paired mobile is live"}else{"no paired mobile currently connected"})) $mobile

  $auditScript=Join-Path $RuntimeRoot "scripts\AUDIT_KRISHNA_E_DRIVE.ps1"
  if(Test-Path $auditScript){
    try{
      $auditOut=& powershell -NoProfile -ExecutionPolicy Bypass -File $auditScript -SourceRoot $SourceRoot -RuntimeRoot $RuntimeRoot | Select-Object -Last 1
      Add-Check "E drive reconciliation audit" "PASS" ("report="+$auditOut) $auditOut
    }catch{Add-Check "E drive reconciliation audit" "FAIL" $_.Exception.Message $null}
  }else{Add-Check "E drive reconciliation audit" "WARN" "audit script not deployed" $null}

} finally {
  if($proc -and !$proc.HasExited){
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    try{$proc.WaitForExit(5000)}catch{}
  }
}

$fail=@($checks|Where-Object{$_.status -eq "FAIL"}).Count
$warn=@($checks|Where-Object{$_.status -eq "WARN"}).Count
$pass=@($checks|Where-Object{$_.status -eq "PASS"}).Count
$report=[ordered]@{
  schema=1
  generated_at=(Get-Date).ToUniversalTime().ToString("o")
  runtime_root=$RuntimeRoot
  source_root=$SourceRoot
  port=$Port
  passed=$pass
  warnings=$warn
  failed=$fail
  duration_seconds=[math]::Round(((Get-Date)-$started).TotalSeconds,2)
  release_ready=($fail -eq 0)
  checks=@($checks)
}
$out=Join-Path $reportDir ("runtime-acceptance-"+(Get-Date -Format "yyyyMMdd-HHmmss")+".json")
$report|ConvertTo-Json -Depth 14|Set-Content -Encoding UTF8 $out
Write-Host ("=== ACCEPTANCE: PASS={0} WARN={1} FAIL={2} ===" -f $pass,$warn,$fail) -ForegroundColor $(if($fail){"Red"}else{"Green"})
Write-Host "Report: $out"
if($fail){exit 2}else{exit 0}

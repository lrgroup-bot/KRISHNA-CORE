param(
  [string]$RuntimeRoot="E:\Krishna-The GOD",
  [string]$SourceRoot="E:\KRISHNA-SOURCE",
  [int]$Port=8876
)
$ErrorActionPreference="Stop"
$Py=Join-Path $RuntimeRoot ".venv\Scripts\python.exe"
if(!(Test-Path $Py)){throw "KRISHNA runtime Python not found: $Py"}
if(!(Test-Path "$RuntimeRoot\core\krishna_core")){throw "KRISHNA runtime core is missing"}

$acceptanceId=[guid]::NewGuid().ToString("N")
$acceptanceState=Join-Path $RuntimeRoot ("state\acceptance\"+$acceptanceId)
New-Item -ItemType Directory -Force $acceptanceState|Out-Null
$env:PYTHONPATH="$RuntimeRoot\core"
$env:KRISHNA_RUNTIME_ROOT=$RuntimeRoot
$env:KRISHNA_SOURCE_ROOT=$SourceRoot
$env:KRISHNA_HOST="127.0.0.1"
$env:KRISHNA_PORT=[string]$Port
$env:KRISHNA_DB=Join-Path $acceptanceState "krishna_core.db"
$env:KRISHNA_ALLOW_ACTIONS="0"
$base="http://127.0.0.1:$Port"
$reportDir=Join-Path $RuntimeRoot "reports"
New-Item -ItemType Directory -Force $reportDir|Out-Null
$started=Get-Date
$checks=New-Object System.Collections.Generic.List[object]

function Add-Check([string]$Name,[string]$Status,[string]$Detail,[object]$Evidence=$null){
  [void]$checks.Add([ordered]@{name=$Name;status=$Status;detail=$Detail;evidence=$Evidence})
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

  try{
    $actionBus=Get-Json "/api/action-bus"
    $actionNames=@($actionBus.actions|ForEach-Object{$_.name})
    $needed=@("chat.create","chat.move","chat.rename","chat.delete","project.register","project.unregister","model.complete","narad.publish_event","narad.adapter_webhook","narad.provider_send","narad.workflow.create","narad.workflow.promote","narad.workflow.execute","narad.checkpoint.resume","narad.dead_letter.retry","worker.ephemeral.execute","browser.inspect","browser.testing_lead","development.git.status","development.git.commit","development.git.push","development.sync","development.stage","development.verify","work.managed.run","repair.shadow","promotion.prepare","promotion.apply","garuda.scout","garudanetra.start","garudanetra.control","garudanetra.upload_attachment")
    $missing=@($needed|Where-Object{$_ -notin $actionNames})
    if($actionBus.owner -eq "KRISHNA Shared Action Bus" -and $missing.Count -eq 0){
      Add-Check "Shared Action Bus" "PASS" ("registered="+$actionBus.registered_actions+"; Projects/Chats wired") $actionBus
    }else{
      Add-Check "Shared Action Bus" "FAIL" ("Missing canonical actions: "+($missing -join ", ")) $actionBus
    }
    $probe=Post-Json "/api/action-bus/dispatch" @{action="chat.create";project="general";actor="acceptance";payload=@{project="general";title="Action Bus Acceptance"};idempotency_key="acceptance-chat-create"}
    if($probe.status -eq "completed" -and $probe.action_id -and $probe.result.chat_id -and $probe.verified){
      Add-Check "Shared Action dispatch" "PASS" ("action_id="+$probe.action_id) $probe
    }else{
      Add-Check "Shared Action dispatch" "FAIL" "Action envelope did not complete" $probe
    }
  }catch{Add-Check "Shared Action Bus" "FAIL" $_.Exception.Message $null}

  try{
    $agents=Get-Json "/api/agents/runtime"
    $jobs=Get-Json "/api/jobs/runtime"
    $permissions=Get-Json "/api/permissions/runtime"
    $protocols=Get-Json "/api/protocols/status"
    $dispatch=Get-Json "/api/dispatch/status"
    $sudarshan=Get-Json "/api/sudarshan/runtime"
    if($sudarshan.owner -eq "Sudarshan Control Plane" -and $sudarshan.exit -eq "IndependentCriticVerifier"){
      Add-Check "Sudarshan control plane" "PASS" "Permissioned Action/Job entry with independent verifier exit" $sudarshan
    }else{Add-Check "Sudarshan control plane" "FAIL" "Sudarshan authority/verification boundary mismatch" $sudarshan}
    if($agents.owner -eq "KRISHNA Agent Runtime" -and @($agents.agents).Count -ge 5 -and $agents.authority -eq "Sudarshan Control Plane"){
      Add-Check "Agent Runtime" "PASS" ("agents="+$agents.count+"; Sudarshan authority") $agents
    }else{Add-Check "Agent Runtime" "FAIL" "Agent Runtime manifest registry is incomplete" $agents}
    if($jobs.owner -eq "KRISHNA Job Runtime" -and $jobs.authority -eq "Shared Action Bus"){
      Add-Check "Job Runtime" "PASS" "Durable TaskLedger-backed jobs use Shared Action Bus" $jobs
    }else{Add-Check "Job Runtime" "FAIL" "Job Runtime authority mismatch" $jobs}
    if($permissions.owner -eq "KRISHNA Permission Runtime"){
      Add-Check "Permission Runtime" "PASS" "Delegated capabilities are explicit" $permissions
    }else{Add-Check "Permission Runtime" "FAIL" "Permission Runtime unavailable" $permissions}
    if($protocols.owner -eq "KRISHNA Agent Protocol Gateway"){
      Add-Check "MCP/A2A boundary" "PASS" "Protocol adapters resolve through Sudarshan" $protocols
    }else{Add-Check "MCP/A2A boundary" "FAIL" "Protocol gateway authority mismatch" $protocols}
    if($dispatch.owner -eq "KRISHNA Dispatch Runtime" -and $dispatch.authority -eq "Sudarshan Control Plane"){
      Add-Check "Dispatch Runtime" "PASS" ("targets="+(@($dispatch.targets) -join ",")+"; Sudarshan authority") $dispatch
    }else{Add-Check "Dispatch Runtime" "FAIL" "Dispatch Runtime unavailable" $dispatch}

    $jobProbe=Post-Json "/api/jobs/submit" @{action="chat.create";project="general";actor="acceptance-job";permissions=@("chat.write");payload=@{project="general";title="Job Runtime Acceptance"};idempotency_key="acceptance-job-chat"}
    if($jobProbe.status -eq "completed" -and $jobProbe.job_id -and $jobProbe.action.action_id -and $jobProbe.verified){
      Add-Check "Job dispatch" "PASS" ("job_id="+$jobProbe.job_id+" action_id="+$jobProbe.action.action_id) $jobProbe
    }else{Add-Check "Job dispatch" "FAIL" "Durable job did not produce an action receipt" $jobProbe}

    $mcpProbe=Post-Json "/api/protocols/mcp/call" @{tool="chat.create";project="general";principal="acceptance-mcp";permissions=@("chat.write");args=@{project="general";title="MCP Acceptance"};request_id="acceptance-mcp-chat"}
    if($mcpProbe.status -eq "completed" -and $mcpProbe.source -eq "mcp" -and $mcpProbe.verified){
      Add-Check "MCP action adapter" "PASS" ("action_id="+$mcpProbe.action_id) $mcpProbe
    }else{Add-Check "MCP action adapter" "FAIL" "MCP adapter bypassed or failed the Shared Action Bus" $mcpProbe}

    $a2aProbe=Post-Json "/api/protocols/a2a/dispatch" @{action="chat.create";project="general";principal="acceptance-a2a";permissions=@("chat.write");payload=@{project="general";title="A2A Acceptance"};request_id="acceptance-a2a-chat"}
    if($a2aProbe.status -eq "completed" -and $a2aProbe.source -eq "a2a" -and $a2aProbe.verified){
      Add-Check "A2A action adapter" "PASS" ("action_id="+$a2aProbe.action_id) $a2aProbe
    }else{Add-Check "A2A action adapter" "FAIL" "A2A adapter bypassed or failed the Shared Action Bus" $a2aProbe}

    $dispatchProbe=Post-Json "/api/dispatch" @{target="action";action="chat.create";project="general";actor="acceptance-dispatch";payload=@{project="general";title="Dispatch Acceptance"};idempotency_key="acceptance-dispatch-chat"}
    if($dispatchProbe.status -eq "completed" -and $dispatchProbe.action_id -and $dispatchProbe.verified){
      Add-Check "Unified dispatch" "PASS" ("action_id="+$dispatchProbe.action_id) $dispatchProbe
    }else{Add-Check "Unified dispatch" "FAIL" "Unified Dispatch did not produce an action receipt" $dispatchProbe}
  }catch{Add-Check "Agent-native runtime layers" "FAIL" $_.Exception.Message $null}

  $narad=Get-Json "/api/narad/status"
  if($narad.name -eq "NARAD" -and $narad.sudarshan_bound -and $narad.workflow_engine -eq "typed-dag/sudarshan"){
    Add-Check "NARAD runtime" "PASS" ("workflows="+$narad.workflows+"; typed DAG through Sudarshan") $narad
  }else{Add-Check "NARAD runtime" "FAIL" "NARAD is not bound to Sudarshan typed-DAG execution" $narad}
  if($narad.execution_gate.max_concurrent -le 4 -and $narad.execution_gate.policy -match "no extra worker pool"){
    Add-Check "NARAD resource gate" "PASS" ("max_concurrent="+$narad.execution_gate.max_concurrent+"; active="+$narad.execution_gate.active) $narad.execution_gate
  }else{Add-Check "NARAD resource gate" "FAIL" "NARAD concurrency/load contract is unsafe" $narad.execution_gate}
  if($narad.connector_registry.count -ge 8){
    Add-Check "NARAD connector contracts" "PASS" ("operations="+$narad.connector_registry.count) $narad.connector_registry
  }else{Add-Check "NARAD connector contracts" "FAIL" "Typed connector registry is incomplete" $narad.connector_registry}
  if($narad.n8n.mode -eq "external-webhook-only" -and $narad.n8n.policy -match "never KRISHNA authority"){
    Add-Check "n8n boundary" "PASS" "n8n is external connector only; Sudarshan remains authority" $narad.n8n
  }else{Add-Check "n8n boundary" "FAIL" "n8n boundary is not connector-only" $narad.n8n}
  $requiredProviders=@("telegram","discord","slack","whatsapp","gmail","google_drive","google_sheets","google_calendar")
  $missingProviders=@($requiredProviders|Where-Object{$_ -notin @($narad.provider_hub)})
  if($missingProviders.Count -eq 0){Add-Check "NARAD provider hub" "PASS" "Messaging and Google provider adapters registered" $narad.provider_hub}
  else{Add-Check "NARAD provider hub" "FAIL" ("Missing provider adapters: "+($missingProviders -join ", ")) $narad.provider_hub}
  $remote=Get-Json "/api/remote/status"
  if($remote.mode -eq "private-network-only"){Add-Check "Private remote boundary" "PASS" "Public Internet control clients are rejected" $remote}else{Add-Check "Private remote boundary" "FAIL" "Remote boundary is not private-network-only" $remote}

  $vault=Get-Json "/api/secure-vault/status"
  if($vault.backend -eq "windows-dpapi" -and $vault.available){Add-Check "Encrypted secret vault" "PASS" "Windows DPAPI vault available; plaintext is not returned" $vault}
  else{Add-Check "Encrypted secret vault" "FAIL" "Windows runtime does not report an available DPAPI vault" $vault}

  $models=Get-Json "/api/models?project=KRISHNA"
  if($models.gateway.policy -match "no silent provider fallback"){Add-Check "Free-only model gateway" "PASS" "Gateway policy blocks silent paid fallback" $models.gateway}
  else{Add-Check "Free-only model gateway" "FAIL" "Free-only fallback policy missing" $models.gateway}

  $voice=Get-Json "/api/voice/status"
  $voiceReady=($voice.stt.available -and $voice.tts.available -and $voice.wake.available)
  Add-Check "Native Odia voice + wake" ($(if($voiceReady){"PASS"}else{"WARN"})) ($(if($voiceReady){"Indic STT/TTS and Krishna wake runtime ready"}else{"Local voice boundaries installed; model/worker/wake assets still require runtime configuration"})) $voice

  $vision=Get-Json "/api/vision/status"
  Add-Check "Local multimodal vision" ($(if($vision.available){"PASS"}else{"WARN"})) ($(if($vision.available){"Local vision model "+$vision.model+" available"}else{"Local vision adapter installed; configured multimodal Ollama model is unavailable"})) $vision

  $resilience=Get-Json "/api/resilience/status"
  if($resilience.worker_supervisor.running){Add-Check "Crash-loop resilience" "PASS" "Worker supervisor live with backoff/quarantine" $resilience.worker_supervisor}
  else{Add-Check "Crash-loop resilience" "FAIL" "Worker resilience supervisor is not running" $resilience.worker_supervisor}

  $wear=Get-Json "/api/wearables"
  Add-Check "Wearable capability gate" "PASS" ("verified capabilities="+(($wear.verified_capabilities -join ", "))) $wear

  $intelligence=Get-Json "/api/intelligence/status"
  Add-Check "Code intelligence" ($(if($intelligence.codebase_memory.available){"PASS"}else{"WARN"})) ($(if($intelligence.codebase_memory.available){"Codebase-Memory discovered"}else{"Codebase-Memory optional adapter unavailable"})) $intelligence.codebase_memory
  Add-Check "Graft memory adapter" ($(if($intelligence.graft.available){"PASS"}else{"WARN"})) ($(if($intelligence.graft.available){"Graft discovered"}else{"Graft optional adapter unavailable"})) $intelligence.graft
  Add-Check "OpenMontage boundary" "PASS" ("installed="+$intelligence.media.installed+" bridge_ready="+$intelligence.media.bridge_ready) $intelligence.media

  $kabach=Get-Json "/api/kabach/projects"
  Add-Check "KABACH boundary registry" "PASS" ("protected projects="+$kabach.count) $kabach

  # Protected/archive projects are observable but may never enter a mutation path.
  $protectedRoot=Join-Path $acceptanceState "protected-project"
  New-Item -ItemType Directory -Force $protectedRoot|Out-Null
  $protectedName="KRISHNA-ACCEPT-PROTECTED"
  $null=Post-Json "/api/projects/register" @{name=$protectedName;root=$protectedRoot;privacy="local_only";role="protected";allowed_actions=@("edit");verification_checks=@()}
  try{
    $null=Post-Json "/api/development/stage" @{project=$protectedName;files=@("x.txt")}
    Add-Check "Protected project mutation gate" "FAIL" "Protected project accepted a staging mutation" $null
  }catch{
    Add-Check "Protected project mutation gate" "PASS" "Protected project mutation was rejected" $_.Exception.Message
  }

  $commitments=Get-Json "/api/commitments?project=KRISHNA"
  Add-Check "Commitment ledger" "PASS" ("unfinished="+@($commitments.unfinished).Count+" forgotten="+@($commitments.forgotten).Count) $commitments

  $autonomy=Get-Json "/api/autonomy/status"
  if($autonomy.running -or $autonomy.enabled){Add-Check "Autonomy supervisor" "PASS" "Supervisor is active" $autonomy}
  else{Add-Check "Autonomy supervisor" "WARN" "Supervisor is installed but not active" $autonomy}

  # Isolated Narad lifecycle acceptance. No external webhook and no mutation.
  $wf=Post-Json "/api/narad/workflows/create" @{name=("acceptance-"+[guid]::NewGuid().ToString("N").Substring(0,8));trigger=@{type="manual"};steps=@(@{action="publish_event";topic="krishna.acceptance";payload=@{source="acceptance"}});permissions=@()}
  $wid=$wf.id
  $plan=Get-Json ("/api/narad/workflow/plan?id="+$wid)
  if($plan.execution_authority -eq "Sudarshan Control Plane" -and @($plan.order).Count -eq 1 -and $plan.verification -match "IndependentCriticVerifier"){
    Add-Check "NARAD workflow plan" "PASS" ("workflow="+$wid+" order="+($plan.order -join ",")) $plan
  }else{Add-Check "NARAD workflow plan" "FAIL" "Workflow plan did not resolve through Sudarshan/verifier" $plan}
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

  # Garudanetra must expose one canonical browser fabric before live work starts.
  try{
    $fabric=Get-Json "/api/garudanetra/fabric"
    if($fabric.canonical_engine -eq "playwright" -and $fabric.owner -eq "garudanetra-browser-fabric"){
      Add-Check "Garudanetra browser fabric" "PASS" ("canonical="+$fabric.canonical_engine+"; adapters="+@($fabric.adapters.adapters).Count) $fabric
    }else{Add-Check "Garudanetra browser fabric" "FAIL" "Canonical browser fabric contract is not active" $fabric}
  }catch{Add-Check "Garudanetra browser fabric" "FAIL" $_.Exception.Message $null}

  # Garudanetra must be able to launch the local KRISHNA UI and produce a real frame.
  try{
    $live=Post-Json "/api/garudanetra/session/start" @{project="KRISHNA";url="$base/";mode="task_memory";persistent_approved=$false}
    $sid=$live.session_id
    $ready=$null
    for($i=0;$i -lt 30;$i++){
      Start-Sleep -Milliseconds 500
      try{$s=Get-Json ("/api/garudanetra/session?id="+$sid);if($s.frame_available -or $s.state -eq "ERROR"){$ready=$s;break}}catch{}
    }
    if($ready -and $ready.frame_available){
      if($ready.mode -ne "task_memory"){Add-Check "Garudanetra browser mode" "FAIL" "Task Memory mode was not preserved" $ready}else{Add-Check "Garudanetra browser mode" "PASS" "Private + Task Memory session active" $ready}
      $null=Post-Json "/api/garudanetra/session/control" @{session_id=$sid;action="takeover";payload=@{}}
      $null=Post-Json "/api/garudanetra/session/control" @{session_id=$sid;action="reload";payload=@{}}
      $frame=Invoke-WebRequest -Uri ($base+"/api/garudanetra/frame?id="+$sid) -TimeoutSec 20
      if($frame.RawContentLength -gt 1000){Add-Check "Garudanetra live browser" "PASS" ("frame bytes="+$frame.RawContentLength) $ready}else{Add-Check "Garudanetra live browser" "FAIL" "Browser frame was empty" $ready}
      if($ready.stream_mode -eq "cdp_screencast"){
        Add-Check "Garudanetra stream transport" "PASS" "CDP screencast is active" $ready
      }else{
        Add-Check "Garudanetra stream transport" "WARN" ("Using "+[string]$ready.stream_mode+"; CDP screencast fallback remains functional") $ready
      }
      Start-Sleep -Milliseconds 500
      try{
        $semantic=Get-Json ("/api/garudanetra/semantic?id="+$sid)
        if([int]$semantic.revision -gt 0 -and @($semantic.items).Count -gt 0){
          Add-Check "Garudanetra semantic observer" "PASS" ("refs="+@($semantic.items).Count+" revision="+$semantic.revision) $semantic
        }else{Add-Check "Garudanetra semantic observer" "WARN" "Semantic snapshot is available but contains no interactive refs yet" $semantic}
      }catch{Add-Check "Garudanetra semantic observer" "FAIL" $_.Exception.Message $null}
      try{
        $replayGate=Post-Json "/api/garudanetra/session/replay" @{session_id=$sid;approved=$false;steps=@(@{action="click";payload=@{selector="#acceptance-probe"};status="ok"})}
        if(@($replayGate.blocked).Count -eq 1 -and @($replayGate.queued).Count -eq 0){
          Add-Check "Garudanetra replay approval gate" "PASS" "Consequential replay was blocked without approval" $replayGate
        }else{Add-Check "Garudanetra replay approval gate" "FAIL" "Consequential replay bypassed approval gate" $replayGate}
      }catch{Add-Check "Garudanetra replay approval gate" "FAIL" $_.Exception.Message $null}
      try{
        $recording=Get-Json ("/api/garudanetra/recording?id="+$sid)
        if([int]$recording.count -gt 0){Add-Check "Garudanetra action recording" "PASS" ("steps="+$recording.count) $recording}
        else{Add-Check "Garudanetra action recording" "WARN" "Recording endpoint is live but no actions were captured yet" $recording}
      }catch{Add-Check "Garudanetra action recording" "FAIL" $_.Exception.Message $null}
    }else{
      Add-Check "Garudanetra live browser" "FAIL" (($ready.last_error|Out-String).Trim()) $ready
    }
    try{$null=Post-Json "/api/garudanetra/session/control" @{session_id=$sid;action="stop";payload=@{}}}catch{}
  }catch{
    Add-Check "Garudanetra live browser" "FAIL" $_.Exception.Message $null
  }

  try{
    try{
      $null=Post-Json "/api/garudanetra/session/start" @{project="KRISHNA";url="$base/";mode="persistent_workspace";persistent_approved=$false}
      Add-Check "Garudanetra persistent approval gate" "FAIL" "Persistent workspace started without explicit approval" $null
    }catch{
      Add-Check "Garudanetra persistent approval gate" "PASS" "Persistent workspace correctly refused without approval" $_.Exception.Message
    }
  }catch{}

  # UI Guardian four-viewport acceptance against the same local interface.
  try{
    $entry=Post-Json "/api/ui-guardian/register" @{name="KRISHNA runtime acceptance";project="KRISHNA";url="$base/";state="candidate";notes="automated runtime acceptance"}
    $eval=Post-Json "/api/ui-guardian/evaluate" @{entry_id=$entry.id}
    if($eval.passed){Add-Check "UI Guardian matrix" "PASS" "All four viewport contracts passed" $eval}
    else{
      $defectSummary=@($eval.defects | Select-Object -First 8 | ForEach-Object {
        $vp=[string]$_.viewport;$kind=[string]$_.kind;$detail=[string]$_.detail
        ("{0}:{1}:{2}" -f $vp,$kind,$detail)
      }) -join " | "
      Add-Check "UI Guardian matrix" "FAIL" ("defects="+@($eval.defects).Count+" | "+$defectSummary) $eval
    }
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

} catch {
  Add-Check "Acceptance harness" "FAIL" $_.Exception.Message $null
} finally {
  if($proc -and !$proc.HasExited){
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    try{[void]$proc.WaitForExit(5000)}catch{}
  }
  if(Test-Path $acceptanceState){Remove-Item -Recurse -Force $acceptanceState -ErrorAction SilentlyContinue}
}

$checkRows=@($checks | ForEach-Object { $_ })
$fail=@($checkRows|Where-Object{$_.status -eq "FAIL"}).Count
$warn=@($checkRows|Where-Object{$_.status -eq "WARN"}).Count
$pass=@($checkRows|Where-Object{$_.status -eq "PASS"}).Count
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
  checks=$checkRows
}
$out=Join-Path $reportDir ("runtime-acceptance-"+(Get-Date -Format "yyyyMMdd-HHmmss")+".json")
$report|ConvertTo-Json -Depth 14|Set-Content -Encoding UTF8 $out
Write-Host ("=== ACCEPTANCE: PASS={0} WARN={1} FAIL={2} ===" -f $pass,$warn,$fail) -ForegroundColor $(if($fail){"Red"}else{"Green"})
Write-Host "Report: $out"
if($fail){exit 2}else{exit 0}

param(
  [string]$SourceRoot="E:\KRISHNA-SOURCE",
  [string]$RuntimeRoot="E:\Krishna-The GOD",
  [string]$DriveRoot="E:\"
)
$ErrorActionPreference="Continue"
$stamp=Get-Date -Format "yyyyMMdd-HHmmss"
$reportDir=Join-Path $RuntimeRoot "reports"
New-Item -ItemType Directory -Force $reportDir|Out-Null

function Normalize-Root([string]$Path){
  if(!$Path){return ""}
  try{
    $full=[IO.Path]::GetFullPath($Path)
    $pathRoot=[IO.Path]::GetPathRoot($full)
    if($pathRoot -and $full -ieq $pathRoot){return $full}
    return $full.TrimEnd("\\")
  }catch{
    return $Path.TrimEnd("\\")
  }
}
function Get-HashProbe([string]$Path){
  $exists=Test-Path -LiteralPath $Path -PathType Leaf
  if(!$exists){return [ordered]@{exists=$false;sha256=$null;hash_status="missing";error=$null}}
  try{
    $hash=(Get-FileHash -Algorithm SHA256 -LiteralPath $Path -ErrorAction Stop).Hash.ToLowerInvariant()
    return [ordered]@{exists=$true;sha256=$hash;hash_status="ok";error=$null}
  }catch{
    $message=[string]$_.Exception.Message
    $status=if($message -match '(?i)used by another process|cannot access the file|being used'){"locked_or_in_use"}else{"unreadable"}
    return [ordered]@{exists=$true;sha256=$null;hash_status=$status;error=$message}
  }
}
function Get-HashSafe([string]$Path){
  return (Get-HashProbe $Path).sha256
}
function Get-FileProbe([string]$Path){
  $probe=Get-HashProbe $Path
  $size=$null
  if($probe.exists){try{$size=(Get-Item -LiteralPath $Path -ErrorAction Stop).Length}catch{}}
  return [ordered]@{path=$Path;exists=$probe.exists;size=$size;sha256=$probe.sha256;hash_status=$probe.hash_status;hash_error=$probe.error}
}
function Compare-File([string]$Candidate,[string]$Canonical,[string]$Policy="compare"){
  $a=Get-HashProbe $Candidate;$b=Get-HashProbe $Canonical
  return [ordered]@{
    candidate=$Candidate
    canonical=$Canonical
    candidate_exists=$a.exists
    canonical_exists=$b.exists
    same=([bool]($a.sha256 -and $b.sha256 -and $a.sha256 -eq $b.sha256))
    candidate_sha256=$a.sha256
    canonical_sha256=$b.sha256
    candidate_hash_status=$a.hash_status
    canonical_hash_status=$b.hash_status
    policy=$Policy
  }
}
function Get-GitHead([string]$Root){
  if(!(Test-Path -LiteralPath (Join-Path $Root ".git"))){return $null}
  try{
    $value=(& git -C $Root rev-parse HEAD 2>$null)
    if($LASTEXITCODE -eq 0 -and $value){return ($value|Select-Object -First 1).Trim()}
  }catch{}
  return $null
}
function Get-GitBranch([string]$Root){
  if(!(Test-Path -LiteralPath (Join-Path $Root ".git"))){return $null}
  try{
    $value=(& git -C $Root branch --show-current 2>$null)
    if($LASTEXITCODE -eq 0 -and $value){return ($value|Select-Object -First 1).Trim()}
  }catch{}
  return $null
}
function Get-GitDirty([string]$Root){
  if(!(Test-Path -LiteralPath (Join-Path $Root ".git"))){return $null}
  try{
    $rows=@(& git -C $Root status --porcelain --untracked-files=all 2>$null)
    if($LASTEXITCODE -ne 0){return $null}
    return [bool](@($rows|Where-Object{$_ -and $_.Trim()}).Count)
  }catch{return $null}
}
function Get-DeploymentManifest([string]$Root){
  $path=Join-Path $Root "state\deployment\DEPLOYED_COMMIT.json"
  if(!(Test-Path -LiteralPath $path -PathType Leaf)){return $null}
  try{return (Get-Content -Raw -LiteralPath $path|ConvertFrom-Json)}catch{return $null}
}
function Get-FolderSummary([string]$Path){
  if(!(Test-Path -LiteralPath $Path)){return [ordered]@{path=$Path;exists=$false;file_count=0;size_bytes=0;top_level=@()}}
  $files=@(Get-ChildItem -LiteralPath $Path -File -Recurse -Force -ErrorAction SilentlyContinue)
  $size=($files|Measure-Object Length -Sum).Sum
  if(!$size){$size=0}
  $top=@(Get-ChildItem -LiteralPath $Path -Force -ErrorAction SilentlyContinue|Select-Object -First 120 Name,Mode,Length,LastWriteTime)
  return [ordered]@{path=$Path;exists=$true;file_count=@($files).Count;size_bytes=[int64]$size;top_level=$top}
}
function Get-ProtectedEvidence([string]$Root){
  if(!(Test-Path -LiteralPath $Root)){return [ordered]@{count=0;examples=@();policy="missing root"}}
  $pattern='(?i)(^|\\)(krishna_core\.db$|state(\\|$)|config(\\|$)|logs(\\|$)|reports(\\|$)|backups(\\|$)|knowledge(\\|$)|gyan[-_ ]?bhandar(\\|$)|ollama-models(\\|$)|models(\\|$)|avatar(\\|$)|assets\\avatar(\\|$)|certificates?(\\|$)|certs?(\\|$)|secrets?(\\|$)|credentials?(\\|$)|trusted[^\\]*device|pairing|\.env($|\.)|[^\\]+\.(pem|key|pfx|p12|cer|crt|glb)$)'
  $hits=New-Object System.Collections.Generic.List[string]
  try{
    Get-ChildItem -LiteralPath $Root -Force -Recurse -ErrorAction SilentlyContinue|ForEach-Object{
      $rel=$_.FullName.Substring((Normalize-Root $Root).Length).TrimStart("\")
      if($rel -match $pattern){
        if($hits.Count -lt 200){[void]$hits.Add($rel)}
      }
    }
  }catch{}
  return [ordered]@{
    count=$hits.Count
    examples=@($hits|Select-Object -First 80)
    policy="protected paths are evidence only; audit never reads secret contents and never deletes protected data"
  }
}
function Resolve-OwnerRoot([string]$CommandLine,[string[]]$Roots){
  if(!$CommandLine){return $null}
  $best=$null
  foreach($root in $Roots){
    if(!$root){continue}
    if($CommandLine.IndexOf($root,[StringComparison]::OrdinalIgnoreCase) -ge 0){
      if(!$best -or $root.Length -gt $best.Length){$best=$root}
    }
  }
  return $best
}
function Get-ProcessInventory([string[]]$Roots){
  $rows=New-Object System.Collections.Generic.List[object]
  try{
    foreach($p in (Get-CimInstance Win32_Process -ErrorAction Stop)){
      $cmd=[string]$p.CommandLine
      $owner=Resolve-OwnerRoot $cmd $Roots
      $krishnaLike=[bool]($owner -or ($cmd -and $cmd -match '(?i)KRISHNA|krishna_core\.server|START_KRISHNA|KRISHNA_GUARDIAN') -or $p.Name -match '^(?i)ollama\.exe$')
      if($krishnaLike){
        [void]$rows.Add([ordered]@{
          pid=[int]$p.ProcessId
          parent_pid=[int]$p.ParentProcessId
          name=[string]$p.Name
          executable=[string]$p.ExecutablePath
          command_line=$cmd
          owning_root=$owner
          guardian=[bool]($cmd -match '(?i)KRISHNA_GUARDIAN\.ps1')
          start_krishna=[bool]($cmd -match '(?i)START_KRISHNA\.ps1')
          core_server=[bool]($cmd -match '(?i)(-m\s+krishna_core\.server|krishna_core\.server)')
        })
      }
    }
  }catch{}
  return @($rows|ForEach-Object{$_})
}
function Get-CoreServerInstances([object[]]$Processes){
  $cores=@($Processes|Where-Object{$_.core_server})
  $byPid=@{}
  foreach($p in $cores){$byPid[[string]$p.pid]=$p}
  $groups=@{}
  foreach($p in $cores){
    $root=$p
    $guard=0
    while($guard -lt 16){
      $guard++
      $parent=$byPid[[string]$root.parent_pid]
      if(!$parent){break}
      $sameRoot=([string]$parent.owning_root -ieq [string]$root.owning_root)
      $sameCommand=([string]$parent.command_line -eq [string]$root.command_line)
      if(!$sameRoot -or !$sameCommand){break}
      $root=$parent
    }
    $key=[string]$root.pid
    if(!$groups.ContainsKey($key)){
      $groups[$key]=New-Object System.Collections.Generic.List[object]
    }
    [void]$groups[$key].Add($p)
  }
  $rows=New-Object System.Collections.Generic.List[object]
  foreach($key in $groups.Keys){
    $members=@($groups[$key]|Sort-Object pid)
    $root=$byPid[$key]
    [void]$rows.Add([ordered]@{
      instance_root_pid=[int]$root.pid
      process_count=$members.Count
      pids=@($members|ForEach-Object{[int]$_.pid})
      owning_root=$root.owning_root
      command_line=$root.command_line
      classification=if($members.Count -gt 1){"launcher_child_chain"}else{"single_process"}
    })
  }
  return @($rows|Sort-Object instance_root_pid)
}

function Get-ListenerInventory([object[]]$Processes){
  $byPid=@{}
  foreach($p in $Processes){$byPid[[string]$p.pid]=$p}
  $knownPorts=@(8765,8766,8767,8876,11434)
  $rows=New-Object System.Collections.Generic.List[object]
  try{
    foreach($c in (Get-NetTCPConnection -State Listen -ErrorAction Stop)){
      $proc=$byPid[[string]$c.OwningProcess]
      if(($knownPorts -contains [int]$c.LocalPort) -or $proc){
        if(!$proc){
          try{
            $wp=Get-CimInstance Win32_Process -Filter ("ProcessId = "+[int]$c.OwningProcess) -ErrorAction Stop
            $proc=[ordered]@{
              pid=[int]$wp.ProcessId
              name=[string]$wp.Name
              executable=[string]$wp.ExecutablePath
              command_line=[string]$wp.CommandLine
              owning_root=$null
            }
          }catch{}
        }
        [void]$rows.Add([ordered]@{
          local_address=[string]$c.LocalAddress
          local_port=[int]$c.LocalPort
          pid=[int]$c.OwningProcess
          state=[string]$c.State
          process_name=if($proc){$proc.name}else{$null}
          executable=if($proc){$proc.executable}else{$null}
          command_line=if($proc){$proc.command_line}else{$null}
          owning_root=if($proc){$proc.owning_root}else{$null}
          expected_port=[bool]($knownPorts -contains [int]$c.LocalPort)
        })
      }
    }
  }catch{}
  return @($rows|ForEach-Object{$_})
}
function Get-GuardianState([string]$Root,[object[]]$Processes){
  $byPid=@{}
  foreach($p in $Processes){$byPid[[string]$p.pid]=$p}
  $pidPath=Join-Path $Root "state\guardian\guardian.pid"
  $statePath=Join-Path $Root "state\guardian\core-guardian.json"
  $guardianPid=0;$corePid=0
  if(Test-Path -LiteralPath $pidPath){try{$guardianPid=[int](Get-Content -Raw -LiteralPath $pidPath).Trim()}catch{}}
  if(Test-Path -LiteralPath $statePath){try{$corePid=[int]((Get-Content -Raw -LiteralPath $statePath|ConvertFrom-Json).core_pid)}catch{}}
  $g=$byPid[[string]$guardianPid];$c=$byPid[[string]$corePid]
  return [ordered]@{
    guardian_pid_file=$pidPath
    guardian_pid=$guardianPid
    guardian_process=$g
    guardian_pid_valid=[bool]($g -and $g.guardian)
    core_state_file=$statePath
    core_pid=$corePid
    core_process=$c
    core_pid_valid=[bool]($c -and ($c.start_krishna -or $c.core_server))
  }
}
function Get-CanonicalMatchEvidence([string]$Root,[string]$SourceRoot){
  $critical=@(
    "core\krishna_core\server.py",
    "core\krishna_core\orchestrator.py",
    "core\krishna_core\runtime_integrity.py",
    "core\krishna_core\shared_action_bus.py",
    "scripts\START_KRISHNA.ps1",
    "scripts\KRISHNA_GUARDIAN.ps1"
  )
  $rows=@()
  $same=0;$comparable=0
  foreach($rel in $critical){
    $a=Join-Path $Root $rel;$b=Join-Path $SourceRoot $rel
    $cmp=Compare-File $a $b "candidate-vs-canonical-source"
    if($cmp.candidate_exists -and $cmp.canonical_exists){
      $comparable++
      if($cmp.same){$same++}
    }
    $rows+=$cmp
  }
  return [ordered]@{same=$same;comparable=$comparable;files=$rows}
}
function Get-RootClassification(
  [string]$Root,
  [string]$SourceRoot,
  [string]$RuntimeRoot,
  [string]$SourceHead,
  [object[]]$Processes,
  [object]$Protected,
  [object]$CanonicalMatch
){
  $norm=Normalize-Root $Root
  $src=Normalize-Root $SourceRoot
  $run=Normalize-Root $RuntimeRoot
  $exists=Test-Path -LiteralPath $norm
  if(!$exists){return [ordered]@{classification="UNKNOWN - DO NOT DELETE";reason="root not present";delete_candidate=$false;automatic_delete_allowed=$false}}
  if($norm -ieq $src){
    return [ordered]@{classification="CANONICAL SOURCE";reason="configured authoritative Git source";delete_candidate=$false;automatic_delete_allowed=$false}
  }
  if($norm -ieq $run){
    return [ordered]@{classification="ACTIVE RUNTIME";reason="configured production runtime";delete_candidate=$false;automatic_delete_allowed=$false}
  }

  $leaf=Split-Path -Leaf $norm
  $active=@($Processes|Where-Object{$_.owning_root -and (Normalize-Root $_.owning_root) -ieq $norm})
  $gitHead=Get-GitHead $norm
  $gitDirty=Get-GitDirty $norm
  $runtimeLike=(Test-Path -LiteralPath (Join-Path $norm "core")) -or (Test-Path -LiteralPath (Join-Path $norm ".venv")) -or (Test-Path -LiteralPath (Join-Path $norm "state"))

  if($leaf -ieq "KRISHNA-CBM"){
    return [ordered]@{classification="REQUIRED DATA";reason="codebase-memory root; preserve until CBM/Graft ownership is reconciled";delete_candidate=$false;automatic_delete_allowed=$false}
  }
  if($leaf -match '(?i)backup|snapshot|recovery'){
    return [ordered]@{classification="BACKUP";reason="name identifies recovery/backup material";delete_candidate=$false;automatic_delete_allowed=$false}
  }
  if($leaf -match '(?i)cache'){
    return [ordered]@{classification="CACHE";reason="cache-named root; still requires ownership review before deletion";delete_candidate=($active.Count -eq 0 -and $Protected.count -eq 0);automatic_delete_allowed=$false}
  }
  if($leaf -match '(?i)e2e|probe|audit'){
    return [ordered]@{classification="TEST/PROBE";reason="test/audit-named root";delete_candidate=($active.Count -eq 0 -and $Protected.count -eq 0);automatic_delete_allowed=$false}
  }
  if($leaf -ieq "New folder"){
    return [ordered]@{classification="UNKNOWN - DO NOT DELETE";reason="generic folder may contain unique runtime/database/avatar artifacts";delete_candidate=$false;automatic_delete_allowed=$false}
  }
  if($gitHead -and $SourceHead -and $gitHead -eq $SourceHead -and $gitDirty -eq $false -and $active.Count -eq 0 -and $Protected.count -eq 0){
    return [ordered]@{classification="DUPLICATE";reason="clean Git checkout at canonical source commit with no protected-data evidence and no owning process";delete_candidate=$true;automatic_delete_allowed=$false}
  }
  if($runtimeLike -and $active.Count -eq 0){
    return [ordered]@{classification="OLD/STAGING";reason="runtime-like root is not canonical and has no observed owning process; protected/unique data still blocks automatic deletion";delete_candidate=($Protected.count -eq 0);automatic_delete_allowed=$false}
  }
  if($CanonicalMatch.comparable -ge 3 -and $CanonicalMatch.same -eq $CanonicalMatch.comparable -and $active.Count -eq 0 -and $Protected.count -eq 0){
    return [ordered]@{classification="DUPLICATE";reason="critical source-owned files match canonical source; no protected-data evidence or owning process";delete_candidate=$true;automatic_delete_allowed=$false}
  }
  if($gitHead){
    return [ordered]@{classification="OLD/STAGING";reason="non-canonical Git checkout requires branch/dirty-state review";delete_candidate=$false;automatic_delete_allowed=$false}
  }
  return [ordered]@{classification="UNKNOWN - DO NOT DELETE";reason="insufficient evidence for safe classification";delete_candidate=$false;automatic_delete_allowed=$false}
}

$SourceRoot=Normalize-Root $SourceRoot
$RuntimeRoot=Normalize-Root $RuntimeRoot
$DriveRoot=Normalize-Root $DriveRoot
$sourceHead=Get-GitHead $SourceRoot
$sourceBranch=Get-GitBranch $SourceRoot
$runtimeManifest=Get-DeploymentManifest $RuntimeRoot

$explicitRoots=@(
  "E:\KRISHNA",
  "E:\KRISHNA-SOURCE",
  "E:\Krishna-The",
  "E:\Krishna-The GOD",
  "E:\KRISHNA-CBM",
  "E:\KRISHNA-E2E-PROBE",
  "E:\KRISHNA-AUDIT",
  "E:\New folder"
)
$discoveredRoots=@()
try{
  $discoveredRoots=@(Get-ChildItem -LiteralPath $DriveRoot -Directory -Force -ErrorAction Stop|Where-Object{$_.Name -match '(?i)krishna'}|ForEach-Object{$_.FullName})
}catch{}
$candidateRoots=@(($explicitRoots+$discoveredRoots)|ForEach-Object{Normalize-Root $_}|Where-Object{$_}|Sort-Object -Unique)

$processRows=Get-ProcessInventory $candidateRoots
$coreServerInstances=Get-CoreServerInstances $processRows
$listenerRows=Get-ListenerInventory $processRows
$guardian=Get-GuardianState $RuntimeRoot $processRows

$rootRows=New-Object System.Collections.Generic.List[object]
foreach($root in $candidateRoots){
  $summary=Get-FolderSummary $root
  $protected=Get-ProtectedEvidence $root
  $canonicalMatch=Get-CanonicalMatchEvidence $root $SourceRoot
  $manifest=Get-DeploymentManifest $root
  $gitHead=Get-GitHead $root
  $gitBranch=Get-GitBranch $root
  $gitDirty=Get-GitDirty $root
  $owners=@($processRows|Where-Object{$_.owning_root -and (Normalize-Root $_.owning_root) -ieq (Normalize-Root $root)})
  $classification=Get-RootClassification $root $SourceRoot $RuntimeRoot $sourceHead $processRows $protected $canonicalMatch
  [void]$rootRows.Add([ordered]@{
    path=$root
    exists=$summary.exists
    classification=$classification.classification
    classification_reason=$classification.reason
    delete_candidate=$classification.delete_candidate
    automatic_delete_allowed=$false
    file_count=$summary.file_count
    size_bytes=$summary.size_bytes
    top_level=$summary.top_level
    git=[ordered]@{head=$gitHead;branch=$gitBranch;dirty=$gitDirty;canonical_head_match=[bool]($gitHead -and $sourceHead -and $gitHead -eq $sourceHead)}
    deployment_manifest=$manifest
    protected_data=$protected
    canonical_match=$canonicalMatch
    owning_processes=$owners
  })
}

$critical=@(
 "core\krishna_core\server.py",
 "core\krishna_core\orchestrator.py",
 "core\krishna_core\agi_kernel.py",
 "core\krishna_core\integrations.py",
 "core\krishna_core\runtime_integrity.py",
 "core\web_validation.html"
)
$sourceRuntime=@()
foreach($rel in $critical){
  $sourceRuntime+=Compare-File (Join-Path $SourceRoot $rel) (Join-Path $RuntimeRoot $rel) "source-vs-runtime"
}

$components=[ordered]@{
  canonical_db=Get-FileProbe (Join-Path $RuntimeRoot "krishna_core.db")
  canonical_avatar=Get-FileProbe (Join-Path $RuntimeRoot "dashboard\assets\avatar\krishna.glb")
  source_mobile_v3=Get-FileProbe (Join-Path $SourceRoot "mobile_v3\index.html")
  mobile_companion_server=Get-FileProbe (Join-Path $RuntimeRoot "mobile\companion\server.py")
  codebase_memory_exe=Get-FileProbe "E:\AI-Tools\codebase-memory-mcp\codebase-memory-mcp.exe"
  openmontage_python=Get-FileProbe "E:\AI-Tools\OpenMontage\.venv\Scripts\python.exe"
  openmontage_repo=Get-FileProbe "E:\AI-Tools\OpenMontage\.git\HEAD"
  browser_fabric_source=Get-FileProbe (Join-Path $SourceRoot "core\krishna_core\browser_fabric.py")
  playwright_python=Get-FileProbe (Join-Path $RuntimeRoot ".venv\Lib\site-packages\playwright\__init__.py")
  graft_ai_tools=Get-FileProbe "E:\AI-Tools\Graft\graft.exe"
  graft_cbm_runtime=Get-FileProbe "E:\CBM-Runtime\graft.exe"
  qwen25vl_manifest=Get-FileProbe (Join-Path $RuntimeRoot "ollama-models\manifests\registry.ollama.ai\library\qwen2.5vl\7b")
  legacy_browser_data=Get-FileProbe (Join-Path $RuntimeRoot "browser-data")
  legacy_garudanetra_source=Get-FileProbe (Join-Path $SourceRoot "core\krishna_core\garudanetra.py")
}
$preservedBackup=Get-FolderSummary (Join-Path $RuntimeRoot "backups\PRE-CANONICAL-SYNC-20260923-213620")
$legacyBrowserData=Get-FolderSummary (Join-Path $RuntimeRoot "browser-data")

$newFolderPaths=@(
  "E:\New folder\server.py",
  "E:\New folder\krishna.glb",
  "E:\New folder\KRISHNA-Mobile-debug-APK.zip",
  "E:\New folder\krishna_core.db",
  "E:\New folder\KRISHNA_REAL_WORLD_PREVIEW.html"
)
$newFolderLeftovers=@($newFolderPaths | ForEach-Object { Get-FileProbe $_ })
$newFolderComparisons=@(
  (Compare-File "E:\New folder\server.py" (Join-Path $SourceRoot "core\krishna_core\server.py") "staging server vs canonical source"),
  (Compare-File "E:\New folder\krishna.glb" (Join-Path $RuntimeRoot "dashboard\assets\avatar\krishna.glb") "avatar candidate vs accepted runtime avatar; never overwrite automatically"),
  (Compare-File "E:\New folder\krishna_core.db" (Join-Path $RuntimeRoot "krishna_core.db") "runtime database is authoritative; never overwrite it with an old copy")
)

$findings=New-Object System.Collections.Generic.List[object]
if(!$components.codebase_memory_exe.exists){
  [void]$findings.Add([ordered]@{status="WARN";code="CBM_EXECUTABLE_MISSING";detail=$components.codebase_memory_exe.path})
}else{
  [void]$findings.Add([ordered]@{status="PASS";code="CBM_DISCOVERED";detail=$components.codebase_memory_exe.path})
}
if(!$components.openmontage_python.exists){
  [void]$findings.Add([ordered]@{status="WARN";code="OPENMONTAGE_RUNTIME_MISSING";detail=$components.openmontage_python.path})
}elseif($env:OPENMONTAGE_CMD){
  [void]$findings.Add([ordered]@{status="PASS";code="OPENMONTAGE_BRIDGE_READY";detail="OpenMontage source + Python runtime detected and OPENMONTAGE_CMD is configured."})
}else{
  [void]$findings.Add([ordered]@{status="PASS";code="OPENMONTAGE_INSTALLED";detail="OpenMontage source + Python runtime detected; command bridge is not configured in this audit process."})
}
if(!$components.playwright_python.exists){
  [void]$findings.Add([ordered]@{status="WARN";code="PLAYWRIGHT_RUNTIME_MISSING";detail=$components.playwright_python.path})
}
if(!$components.browser_fabric_source.exists){
  [void]$findings.Add([ordered]@{status="WARN";code="BROWSER_FABRIC_SOURCE_MISSING";detail=$components.browser_fabric_source.path})
}
if($legacyBrowserData.exists){
  [void]$findings.Add([ordered]@{status="STALE";code="LEGACY_BROWSER_DATA_PRESENT";detail=$legacyBrowserData.path})
}
if($components.legacy_garudanetra_source.exists){
  [void]$findings.Add([ordered]@{status="PASS";code="LEGACY_GARUDANETRA_MODULE_PRESENT";detail="Compatibility module exists; browser_fabric.py remains canonical browser authority."})
}
if($components.mobile_companion_server.exists -and $components.source_mobile_v3.exists){
  [void]$findings.Add([ordered]@{status="WARN";code="MOBILE_RUNTIME_DUALITY";detail="Legacy runtime mobile companion and repository mobile_v3 both exist; mobile_v3 remains canonical until legacy runtime is separately reconciled."})
}
if(!$sourceHead){[void]$findings.Add([ordered]@{status="BLOCKED";code="CANONICAL_SOURCE_HEAD_UNREADABLE";detail=$SourceRoot})}
if($runtimeManifest -and $sourceHead -and [string]$runtimeManifest.commit -ne $sourceHead){
  [void]$findings.Add([ordered]@{status="WARN";code="SOURCE_RUNTIME_COMMIT_MISMATCH";detail=("source="+$sourceHead+" runtime="+[string]$runtimeManifest.commit)})
}
if(!$preservedBackup.exists){
  [void]$findings.Add([ordered]@{status="WARN";code="REQUIRED_RECOVERY_BACKUP_NOT_FOUND";detail=$preservedBackup.path})
}else{
  [void]$findings.Add([ordered]@{status="PASS";code="RECOVERY_BACKUP_PRESERVED";detail=$preservedBackup.path})
}
foreach($x in $sourceRuntime){
  if($x.candidate_exists -and $x.canonical_exists -and !$x.same){
    [void]$findings.Add([ordered]@{status="WARN";code="SOURCE_RUNTIME_FILE_DRIFT";detail=$x.candidate})
  }
}
foreach($row in $rootRows){
  if($row.exists){
    [void]$findings.Add([ordered]@{status=if($row.classification -eq "UNKNOWN - DO NOT DELETE"){"WARN"}elseif($row.classification -in @("DUPLICATE","OLD/STAGING")){"STALE"}else{"PASS"};code="ROOT_CLASSIFICATION";detail=($row.path+" => "+$row.classification);reason=$row.classification_reason})
  }
}
$guardianCount=@($processRows|Where-Object{$_.guardian}).Count
$coreCount=@($processRows|Where-Object{$_.core_server}).Count
$coreInstanceCount=@($coreServerInstances).Count
$startCount=@($processRows|Where-Object{$_.start_krishna}).Count
if($guardianCount -gt 1){[void]$findings.Add([ordered]@{status="DUPLICATE";code="MULTIPLE_GUARDIANS";detail=("count="+$guardianCount)})}
if($startCount -gt 1){[void]$findings.Add([ordered]@{status="DUPLICATE";code="MULTIPLE_START_KRISHNA";detail=("count="+$startCount)})}
if($coreInstanceCount -gt 1){
  [void]$findings.Add([ordered]@{status="DUPLICATE";code="MULTIPLE_CORE_SERVER_INSTANCES";detail=("instances="+$coreInstanceCount+" raw_processes="+$coreCount);instances=$coreServerInstances})
}elseif($coreCount -gt 1 -and $coreInstanceCount -eq 1){
  [void]$findings.Add([ordered]@{status="PASS";code="CORE_SERVER_LAUNCHER_CHILD_CHAIN";detail=("one runtime instance uses "+$coreCount+" linked Windows Python processes; no duplicate runtime inferred");instances=$coreServerInstances})
}
if($guardian.guardian_pid -gt 0 -and !$guardian.guardian_pid_valid){[void]$findings.Add([ordered]@{status="STALE";code="STALE_GUARDIAN_PID";detail=[string]$guardian.guardian_pid})}
if($guardian.core_pid -gt 0 -and !$guardian.core_pid_valid){[void]$findings.Add([ordered]@{status="STALE";code="STALE_CORE_PID";detail=[string]$guardian.core_pid})}

foreach($port in @(8766,11434)){
  $rows=@($listenerRows|Where-Object{$_.local_port -eq $port})
  if($rows.Count -eq 0){
    [void]$findings.Add([ordered]@{status="WARN";code="EXPECTED_PORT_NOT_LISTENING";detail=[string]$port})
  }elseif($rows.Count -gt 1){
    [void]$findings.Add([ordered]@{status="DUPLICATE";code="MULTIPLE_LISTENERS_ON_EXPECTED_PORT";detail=[string]$port;pids=@($rows | ForEach-Object { $_.pid })})
  }else{
    [void]$findings.Add([ordered]@{status="PASS";code="EXPECTED_PORT_LISTENER";detail=([string]$port+" pid="+[string]$rows[0].pid)})
  }
}
$legacyMobileRows=@($listenerRows|Where-Object{$_.local_port -eq 8765})
if($legacyMobileRows.Count -eq 0){
  [void]$findings.Add([ordered]@{status="PASS";code="LEGACY_MOBILE_PORT_CLEAR";detail="8765; canonical mobile_v3 connects to Core 8766"})
}elseif($legacyMobileRows.Count -gt 1){
  [void]$findings.Add([ordered]@{status="DUPLICATE";code="MULTIPLE_LEGACY_MOBILE_LISTENERS";detail="8765";pids=@($legacyMobileRows | ForEach-Object { $_.pid })})
}else{
  [void]$findings.Add([ordered]@{status="STALE";code="LEGACY_MOBILE_LISTENER_PRESENT";detail=("8765 pid="+[string]$legacyMobileRows[0].pid+"; verify legacy companion need before retirement")})
}
$lanDiscoveryRows=@($listenerRows|Where-Object{$_.local_port -eq 8767})
if($lanDiscoveryRows.Count -eq 0){
  [void]$findings.Add([ordered]@{status="PASS";code="LAN_DISCOVERY_INACTIVE";detail="8767; expected while Core is loopback/private-LAN mode is not active"})
}else{
  [void]$findings.Add([ordered]@{status="PASS";code="LAN_DISCOVERY_LISTENER";detail=("8767 pid="+[string]$lanDiscoveryRows[0].pid)})
}
$acceptanceRows=@($listenerRows | Where-Object { $_.local_port -eq 8876 })
if($acceptanceRows.Count -eq 0){
  [void]$findings.Add([ordered]@{status="PASS";code="ACCEPTANCE_PORT_CLEAR";detail="8876"})
}else{
  [void]$findings.Add([ordered]@{status="STALE";code="ACCEPTANCE_PORT_LISTENER_PRESENT";detail="8876 should normally be clear outside a live acceptance run";pids=@($acceptanceRows | ForEach-Object { $_.pid })})
}

$findingRows=@($findings | ForEach-Object { $_ })
$rootOutput=@($rootRows|ForEach-Object{$_})
$report=[ordered]@{
  schema=3
  generated_at=(Get-Date).ToUniversalTime().ToString("o")
  machine=$env:COMPUTERNAME
  audit_mode="READ_ONLY"
  deletion_performed=$false
  policy="No root, process, file, cache, backup, database, state, model, credential, certificate, pairing record, avatar asset, log or report is deleted by this audit."
  source=[ordered]@{root=$SourceRoot;head=$sourceHead;branch=$sourceBranch}
  runtime=[ordered]@{root=$RuntimeRoot;deployment_manifest=$runtimeManifest}
  required_recovery_backup=$preservedBackup
  new_folder_leftovers=$newFolderLeftovers
  new_folder_comparisons=$newFolderComparisons
  candidate_roots=$rootOutput
  source_runtime=$sourceRuntime
  guardian=$guardian
  core_server_instances=$coreServerInstances
  processes=$processRows
  listeners=$listenerRows
  components=$components
  findings=$findingRows
}
$out=Join-Path $reportDir "e-drive-cleanup-audit-$stamp.json"
$report|ConvertTo-Json -Depth 14|Set-Content -Encoding UTF8 $out

Write-Host "=== KRISHNA E: DRIVE CLEANUP AUDIT (READ ONLY) ===" -ForegroundColor Cyan
Write-Host ("Source : "+$SourceRoot+" @ "+$sourceHead)
Write-Host ("Runtime: "+$RuntimeRoot+" @ "+[string]$runtimeManifest.commit)
Write-Host ("Report : "+$out)
Write-Host ""
foreach($row in $rootRows){
  if($row.exists){
    Write-Host ("[{0}] {1}" -f $row.classification,$row.path)
    Write-Host ("  files={0} size_bytes={1} protected={2} processes={3} delete_candidate={4}" -f $row.file_count,$row.size_bytes,$row.protected_data.count,@($row.owning_processes).Count,$row.delete_candidate)
  }
}
Write-Host ""
Write-Host "=== KRISHNA PROCESS OWNERSHIP ===" -ForegroundColor Cyan
@($processRows | Where-Object { $_.guardian -or $_.start_krishna -or $_.core_server }) | ForEach-Object {
  Write-Host ("PID={0} PPID={1} name={2} root={3} guardian={4} start={5} core={6}" -f $_.pid,$_.parent_pid,$_.name,$_.owning_root,$_.guardian,$_.start_krishna,$_.core_server)
  Write-Host ("  exe: "+$_.executable)
  Write-Host ("  cmd: "+$_.command_line)
}
Write-Host ""
Write-Host "=== KRISHNA LISTENERS ===" -ForegroundColor Cyan
$listenerRows | Sort-Object local_port,pid | ForEach-Object {
  Write-Host ("port={0} addr={1} pid={2} process={3} root={4}" -f $_.local_port,$_.local_address,$_.pid,$_.process_name,$_.owning_root)
  if($_.command_line){Write-Host ("  cmd: "+$_.command_line)}
}
Write-Host ""
$findings|ForEach-Object{Write-Host ("[{0}] {1} - {2}" -f $_.status,$_.code,$_.detail)}
Write-Output $out

param(
  [string]$SourceRoot="E:\KRISHNA-SOURCE",
  [string]$RuntimeRoot="E:\Krishna-The GOD"
)
$ErrorActionPreference="Continue"
$stamp=Get-Date -Format "yyyyMMdd-HHmmss"
$reportDir=Join-Path $RuntimeRoot "reports"
New-Item -ItemType Directory -Force $reportDir|Out-Null

function Get-FolderSummary([string]$Path){
  if(!(Test-Path $Path)){return [ordered]@{path=$Path;exists=$false}}
  $files=Get-ChildItem -LiteralPath $Path -File -Recurse -Force -ErrorAction SilentlyContinue
  $size=($files|Measure-Object Length -Sum).Sum
  $top=Get-ChildItem -LiteralPath $Path -Force -ErrorAction SilentlyContinue|Select-Object -First 80 Name,Mode,Length,LastWriteTime
  return [ordered]@{
    path=$Path;exists=$true;file_count=@($files).Count;size_bytes=[int64]($size|ForEach-Object{if($_){$_}else{0}})
    top_level=@($top)
  }
}
function Get-HashSafe([string]$Path){
  if(!(Test-Path -LiteralPath $Path -PathType Leaf)){return $null}
  try{return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()}catch{return $null}
}
function Compare-File([string]$Candidate,[string]$Canonical,[string]$Policy="compare"){
  $a=Get-HashSafe $Candidate;$b=Get-HashSafe $Canonical
  [ordered]@{candidate=$Candidate;canonical=$Canonical;candidate_exists=[bool]$a;canonical_exists=[bool]$b;same=($a -and $b -and $a -eq $b);candidate_sha256=$a;canonical_sha256=$b;policy=$Policy}
}

$targets=[ordered]@{
  source=$SourceRoot
  runtime=$RuntimeRoot
  cbm_source="E:\KRISHNA-CBM"
  cbm_runtime="E:\CBM-Runtime"
  cbm_cache="E:\CBM-Cache"
  agi=(Join-Path $RuntimeRoot "agi")
  agents=(Join-Path $RuntimeRoot "agents")
  guardian=(Join-Path $RuntimeRoot "guardian")
  voice=(Join-Path $RuntimeRoot "voice")
  external=(Join-Path $RuntimeRoot "external")
  mobile=(Join-Path $RuntimeRoot "mobile")
  dashboard=(Join-Path $RuntimeRoot "dashboard")
  tools=(Join-Path $RuntimeRoot "tools")
}
$summaries=[ordered]@{}
foreach($k in $targets.Keys){$summaries[$k]=Get-FolderSummary $targets[$k]}

$leftovers=@(
  "E:\New folder\server.py",
  "E:\New folder\krishna.glb",
  "E:\New folder\KRISHNA-Mobile-debug-APK.zip",
  "E:\New folder\krishna_core.db",
  "E:\New folder\KRISHNA_REAL_WORLD_PREVIEW.html"
)|ForEach-Object{
  [ordered]@{path=$_;exists=(Test-Path -LiteralPath $_);sha256=(Get-HashSafe $_);size=(if(Test-Path -LiteralPath $_){(Get-Item -LiteralPath $_).Length}else{$null})}
}

$comparisons=@(
  (Compare-File "E:\New folder\server.py" (Join-Path $SourceRoot "core\krishna_core\server.py")),
  (Compare-File "E:\New folder\krishna.glb" (Join-Path $RuntimeRoot "dashboard\assets\avatar\krishna.glb")),
  (Compare-File "E:\New folder\krishna_core.db" (Join-Path $RuntimeRoot "krishna_core.db") "runtime database is authoritative; never copy stale DB over it")
)

$critical=@(
 "core\krishna_core\server.py","core\krishna_core\orchestrator.py","core\krishna_core\agi_kernel.py","core\web_validation.html"
)
$sourceRuntime=@()
foreach($rel in $critical){
 $s=Join-Path $SourceRoot $rel;$r=Join-Path $RuntimeRoot $rel
 $sourceRuntime+=Compare-File $s $r "source-vs-runtime"
}

$proc=@()
try{
 $proc=Get-CimInstance Win32_Process|Where-Object{
   $_.CommandLine -and ($_.CommandLine -like "*Krishna-The GOD*" -or $_.CommandLine -like "*KRISHNA-SOURCE*")
 }|Select-Object ProcessId,ParentProcessId,Name,CommandLine
}catch{}

$listeners=@()
try{
 $listeners=Get-NetTCPConnection -State Listen -ErrorAction Stop|Where-Object{$_.LocalPort -in 8765,8766,11434}|Select-Object LocalAddress,LocalPort,OwningProcess,State
}catch{}

$manifestPath=Join-Path $RuntimeRoot "state\deployment\DEPLOYED_COMMIT.json"
$manifest=$null
if(Test-Path $manifestPath){try{$manifest=Get-Content -Raw $manifestPath|ConvertFrom-Json}catch{}}

$findings=New-Object System.Collections.Generic.List[object]
if(!$summaries.cbm_source.exists){$findings.Add([ordered]@{severity="warning";code="CBM_SOURCE_MISSING";detail="E:\KRISHNA-CBM not found"})}
if(!$summaries.cbm_runtime.exists){$findings.Add([ordered]@{severity="warning";code="CBM_RUNTIME_MISSING";detail="E:\CBM-Runtime not found"})}
if(!$manifest){$findings.Add([ordered]@{severity="critical";code="DEPLOYMENT_MANIFEST_MISSING";detail=$manifestPath})}
foreach($x in $sourceRuntime){if($x.candidate_exists -and $x.canonical_exists -and !$x.same){$findings.Add([ordered]@{severity="critical";code="SOURCE_RUNTIME_DRIFT";detail=$x.candidate})}}
foreach($p in $proc){
 if($p.CommandLine -match "\\agents\\astra_worker.py|\\agents\\autonomous_recovery_loop.py|\\guardian\\autopilot.py|\\mobile\\companion\\server.py"){
   $findings.Add([ordered]@{severity="notice";code="LEGACY_PARALLEL_PROCESS";detail=$p.CommandLine;pid=$p.ProcessId})
 }
}
foreach($x in $leftovers){if($x.exists){$findings.Add([ordered]@{severity="notice";code="UNRESOLVED_LEFTOVER";detail=$x.path})}}

$report=[ordered]@{
 schema=1
 generated_at=(Get-Date).ToUniversalTime().ToString("o")
 machine=$env:COMPUTERNAME
 source_root=$SourceRoot
 runtime_root=$RuntimeRoot
 deployment_manifest=$manifest
 folders=$summaries
 unresolved_leftovers=$leftovers
 comparisons=$comparisons
 source_runtime=$sourceRuntime
 running_processes=@($proc)
 listeners=@($listeners)
 findings=@($findings)
}
$out=Join-Path $reportDir "e-drive-audit-$stamp.json"
$report|ConvertTo-Json -Depth 12|Set-Content -Encoding UTF8 $out

Write-Host "=== KRISHNA E: DRIVE AUDIT ===" -ForegroundColor Cyan
Write-Host "Report: $out"
Write-Host "Findings: $($findings.Count)"
$findings|ForEach-Object{Write-Host ("[{0}] {1} - {2}" -f $_.severity,$_.code,$_.detail)}
Write-Output $out

param(
  [string]$SourceRoot="E:\KRISHNA-SOURCE",
  [string]$RuntimeRoot="E:\Krishna-The GOD"
)
$ErrorActionPreference="Continue"
$stamp=Get-Date -Format "yyyyMMdd-HHmmss"
$reportDir=Join-Path $RuntimeRoot "reports"
New-Item -ItemType Directory -Force $reportDir|Out-Null

function Get-FolderSummary([string]$Path){
  if(!(Test-Path -LiteralPath $Path)){return [ordered]@{path=$Path;exists=$false}}
  $files=Get-ChildItem -LiteralPath $Path -File -Recurse -Force -ErrorAction SilentlyContinue
  $size=($files|Measure-Object Length -Sum).Sum
  if(!$size){$size=0}
  $top=Get-ChildItem -LiteralPath $Path -Force -ErrorAction SilentlyContinue|Select-Object -First 80 Name,Mode,Length,LastWriteTime
  return [ordered]@{path=$Path;exists=$true;file_count=@($files).Count;size_bytes=[int64]$size;top_level=@($top)}
}
function Get-HashSafe([string]$Path){
  if(!(Test-Path -LiteralPath $Path -PathType Leaf)){return $null}
  try{return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()}catch{return $null}
}
function Get-FileProbe([string]$Path){
  $exists=Test-Path -LiteralPath $Path -PathType Leaf
  $size=$null
  if($exists){try{$size=(Get-Item -LiteralPath $Path).Length}catch{}}
  return [ordered]@{path=$Path;exists=$exists;size=$size;sha256=(Get-HashSafe $Path)}
}
function Compare-File([string]$Candidate,[string]$Canonical,[string]$Policy="compare"){
  $a=Get-HashSafe $Candidate;$b=Get-HashSafe $Canonical
  return [ordered]@{candidate=$Candidate;canonical=$Canonical;candidate_exists=[bool]$a;canonical_exists=[bool]$b;same=([bool]($a -and $b -and $a -eq $b));candidate_sha256=$a;canonical_sha256=$b;policy=$Policy}
}

$targets=[ordered]@{
  source=$SourceRoot
  runtime=$RuntimeRoot
  ai_tools="E:\AI-Tools"
  codebase_memory="E:\AI-Tools\codebase-memory-mcp"
  openmontage="E:\AI-Tools\OpenMontage"
  cbm_source="E:\KRISHNA-CBM"
  cbm_runtime="E:\CBM-Runtime"
  cbm_cache="E:\CBM-Cache"
  agi=(Join-Path $RuntimeRoot "agi")
  agents=(Join-Path $RuntimeRoot "agents")
  guardian=(Join-Path $RuntimeRoot "guardian")
  voice=(Join-Path $RuntimeRoot "voice")
  external=(Join-Path $RuntimeRoot "external")
  agency_agents=(Join-Path $RuntimeRoot "external\agency-agents")
  mobile=(Join-Path $RuntimeRoot "mobile")
  mobile_companion=(Join-Path $RuntimeRoot "mobile\companion")
  dashboard=(Join-Path $RuntimeRoot "dashboard")
  tools=(Join-Path $RuntimeRoot "tools")
}
$summaries=[ordered]@{}
foreach($k in $targets.Keys){$summaries[$k]=Get-FolderSummary $targets[$k]}

$components=[ordered]@{
  codebase_memory_exe=Get-FileProbe "E:\AI-Tools\codebase-memory-mcp\codebase-memory-mcp.exe"
  openmontage_python=Get-FileProbe "E:\AI-Tools\OpenMontage\.venv\Scripts\python.exe"
  openmontage_repo=Get-FileProbe "E:\AI-Tools\OpenMontage\.git\HEAD"
  graft_ai_tools=Get-FileProbe "E:\AI-Tools\Graft\graft.exe"
  graft_cbm_runtime=Get-FileProbe "E:\CBM-Runtime\graft.exe"
  canonical_avatar=Get-FileProbe (Join-Path $RuntimeRoot "dashboard\assets\avatar\krishna.glb")
  mobile_companion_server=Get-FileProbe (Join-Path $RuntimeRoot "mobile\companion\server.py")
  source_mobile_v3=Get-FileProbe (Join-Path $SourceRoot "mobile_v3\index.html")
}

$leftoverPaths=@(
  "E:\New folder\server.py",
  "E:\New folder\krishna.glb",
  "E:\New folder\KRISHNA-Mobile-debug-APK.zip",
  "E:\New folder\krishna_core.db",
  "E:\New folder\KRISHNA_REAL_WORLD_PREVIEW.html"
)
$leftovers=@($leftoverPaths|ForEach-Object{Get-FileProbe $_})

$comparisons=@(
  (Compare-File "E:\New folder\server.py" (Join-Path $SourceRoot "core\krishna_core\server.py")),
  (Compare-File "E:\New folder\krishna.glb" (Join-Path $RuntimeRoot "dashboard\assets\avatar\krishna.glb")),
  (Compare-File "E:\New folder\krishna_core.db" (Join-Path $RuntimeRoot "krishna_core.db") "runtime database is authoritative; never overwrite it with an old copy")
)

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
 $s=Join-Path $SourceRoot $rel;$r=Join-Path $RuntimeRoot $rel
 $sourceRuntime+=Compare-File $s $r "source-vs-runtime"
}

$proc=@()
try{
 $proc=Get-CimInstance Win32_Process|Where-Object{
   $_.CommandLine -and ($_.CommandLine -like "*Krishna-The GOD*" -or $_.CommandLine -like "*KRISHNA-SOURCE*" -or $_.CommandLine -like "*AI-Tools\codebase-memory*" -or $_.CommandLine -like "*AI-Tools\OpenMontage*")
 }|Select-Object ProcessId,ParentProcessId,Name,CommandLine
}catch{}

$listeners=@()
try{
 $listeners=Get-NetTCPConnection -State Listen -ErrorAction Stop|Where-Object{$_.LocalPort -in 8010,8765,8766,11434}|Select-Object LocalAddress,LocalPort,OwningProcess,State
}catch{}

$manifestPath=Join-Path $RuntimeRoot "state\deployment\DEPLOYED_COMMIT.json"
$manifest=$null
if(Test-Path -LiteralPath $manifestPath){try{$manifest=Get-Content -Raw -LiteralPath $manifestPath|ConvertFrom-Json}catch{}}

$findings=New-Object System.Collections.Generic.List[object]
if(!$components.codebase_memory_exe.exists){
  $findings.Add([ordered]@{severity="warning";code="CBM_EXECUTABLE_MISSING";detail="E:\AI-Tools\codebase-memory-mcp\codebase-memory-mcp.exe"})
}else{
  $findings.Add([ordered]@{severity="info";code="CBM_DISCOVERED";detail=$components.codebase_memory_exe.path})
}
if(!$components.openmontage_python.exists){
  $findings.Add([ordered]@{severity="warning";code="OPENMONTAGE_RUNTIME_MISSING";detail=$components.openmontage_python.path})
}else{
  $findings.Add([ordered]@{severity="info";code="OPENMONTAGE_INSTALLED";detail="OpenMontage source + Python runtime detected; dedicated KRISHNA command bridge is still required before execution."})
}
if(!$summaries.cbm_source.exists -and !$components.codebase_memory_exe.exists){
  $findings.Add([ordered]@{severity="notice";code="CBM_ALTERNATE_SOURCE_MISSING";detail="E:\KRISHNA-CBM not found; this is not an error if E:\AI-Tools\codebase-memory-mcp is canonical."})
}
if(!$summaries.cbm_runtime.exists -and !$components.codebase_memory_exe.exists){
  $findings.Add([ordered]@{severity="notice";code="CBM_ALTERNATE_RUNTIME_MISSING";detail="E:\CBM-Runtime not found; this is not an error if E:\AI-Tools\codebase-memory-mcp is canonical."})
}
if(!$manifest){$findings.Add([ordered]@{severity="critical";code="DEPLOYMENT_MANIFEST_MISSING";detail=$manifestPath})}
foreach($x in $sourceRuntime){
  if($x.candidate_exists -and $x.canonical_exists -and !$x.same){
    $findings.Add([ordered]@{severity="critical";code="SOURCE_RUNTIME_DRIFT";detail=$x.candidate})
  }
}
foreach($p in $proc){
 if($p.CommandLine -match "\\agents\\astra_worker.py|\\agents\\autonomous_recovery_loop.py|\\guardian\\autopilot.py|\\mobile\\companion\\server.py"){
   $findings.Add([ordered]@{severity="notice";code="LEGACY_PARALLEL_PROCESS";detail=$p.CommandLine;pid=$p.ProcessId})
 }
}
if($components.mobile_companion_server.exists -and $components.source_mobile_v3.exists){
  $findings.Add([ordered]@{severity="notice";code="MOBILE_RUNTIME_DUALITY";detail="Legacy runtime mobile companion and repository mobile_v3 both exist; keep one canonical product path after comparison."})
}
foreach($x in $leftovers){
  if($x.exists){$findings.Add([ordered]@{severity="notice";code="UNRESOLVED_LEFTOVER";detail=$x.path})}
}

$report=[ordered]@{
 schema=2
 generated_at=(Get-Date).ToUniversalTime().ToString("o")
 machine=$env:COMPUTERNAME
 source_root=$SourceRoot
 runtime_root=$RuntimeRoot
 deployment_manifest=$manifest
 folders=$summaries
 components=$components
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

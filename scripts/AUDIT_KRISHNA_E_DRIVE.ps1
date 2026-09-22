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
  browser_data_legacy=(Join-Path $RuntimeRoot "browser-data")
  playwright_browsers=(Join-Path $RuntimeRoot "playwright-browsers")
  garudanetra_state=(Join-Path $RuntimeRoot "state\garudanetra")
  garudanetra_profiles=(Join-Path $RuntimeRoot "garudanetra\profiles")
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
  canonical_mobile_main=Get-FileProbe (Join-Path $RuntimeRoot "mobile\app-source\MainActivity.java")
  mobile_runtime_manifest=Get-FileProbe (Join-Path $RuntimeRoot "state\deployment\MOBILE_RUNTIME.json")
  playwright_python=Get-FileProbe (Join-Path $RuntimeRoot ".venv\Lib\site-packages\playwright\__init__.py")
  browser_fabric_source=Get-FileProbe (Join-Path $SourceRoot "core\krishna_core\browser_fabric.py")
  garudanetra_session_source=Get-FileProbe (Join-Path $SourceRoot "core\krishna_core\garudanetra_session.py")
  legacy_garudanetra_source=Get-FileProbe (Join-Path $SourceRoot "core\krishna_core\garudanetra.py")
}
$browserEnv=[ordered]@{
  PLAYWRIGHT_BROWSERS_PATH=$env:PLAYWRIGHT_BROWSERS_PATH
  KRISHNA_BROWSER_DATA_ROOT=$env:KRISHNA_BROWSER_DATA_ROOT
  KRISHNA_BROWSER_HARNESS_CMD=$env:KRISHNA_BROWSER_HARNESS_CMD
  KRISHNA_BROWSER_VISION_RECOVERY_CMD=$env:KRISHNA_BROWSER_VISION_RECOVERY_CMD
  KRISHNA_AGENT_BROWSER_CMD=$env:KRISHNA_AGENT_BROWSER_CMD
  KRISHNA_BROWSERCODE_CMD=$env:KRISHNA_BROWSERCODE_CMD
  KRISHNA_OPENDEVBROWSER_CMD=$env:KRISHNA_OPENDEVBROWSER_CMD
  KRISHNA_RUSTWRIGHT_CMD=$env:KRISHNA_RUSTWRIGHT_CMD
  KRISHNA_LUCARNE_CMD=$env:KRISHNA_LUCARNE_CMD
  KRISHNA_PROMPTWRIGHT_CMD=$env:KRISHNA_PROMPTWRIGHT_CMD
  KRISHNA_SKYVERN_CMD=$env:KRISHNA_SKYVERN_CMD
  KRISHNA_RRWEB_CMD=$env:KRISHNA_RRWEB_CMD
  KRISHNA_CEREON_BROWSER_ENDPOINT=$env:KRISHNA_CEREON_BROWSER_ENDPOINT
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
   $_.CommandLine -and ($_.CommandLine -like "*Krishna-The GOD*" -or $_.CommandLine -like "*KRISHNA-SOURCE*" -or $_.CommandLine -like "*AI-Tools\codebase-memory*" -or $_.CommandLine -like "*AI-Tools\OpenMontage*" -or ($_.Name -match "chrome|chromium|msedge" -and $_.CommandLine -match "garudanetra|playwright|Krishna-The GOD"))
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
  [void]$findings.Add([ordered]@{severity="warning";code="CBM_EXECUTABLE_MISSING";detail="E:\AI-Tools\codebase-memory-mcp\codebase-memory-mcp.exe"})
}else{
  [void]$findings.Add([ordered]@{severity="info";code="CBM_DISCOVERED";detail=$components.codebase_memory_exe.path})
}
if(!$components.openmontage_python.exists){
  [void]$findings.Add([ordered]@{severity="warning";code="OPENMONTAGE_RUNTIME_MISSING";detail=$components.openmontage_python.path})
}elseif($env:OPENMONTAGE_CMD){
  [void]$findings.Add([ordered]@{severity="info";code="OPENMONTAGE_BRIDGE_READY";detail="OpenMontage source + Python runtime detected and OPENMONTAGE_CMD is configured."})
}else{
  [void]$findings.Add([ordered]@{severity="info";code="OPENMONTAGE_INSTALLED";detail="OpenMontage source + Python runtime detected; command bridge is not configured in this audit process."})
}
if(!$summaries.cbm_source.exists -and !$components.codebase_memory_exe.exists){
  [void]$findings.Add([ordered]@{severity="notice";code="CBM_ALTERNATE_SOURCE_MISSING";detail="E:\KRISHNA-CBM not found; this is not an error if E:\AI-Tools\codebase-memory-mcp is canonical."})
}
if(!$summaries.cbm_runtime.exists -and !$components.codebase_memory_exe.exists){
  [void]$findings.Add([ordered]@{severity="notice";code="CBM_ALTERNATE_RUNTIME_MISSING";detail="E:\CBM-Runtime not found; this is not an error if E:\AI-Tools\codebase-memory-mcp is canonical."})
}
if(!$components.playwright_python.exists){
  [void]$findings.Add([ordered]@{severity="critical";code="PLAYWRIGHT_RUNTIME_MISSING";detail=$components.playwright_python.path})
}else{
  [void]$findings.Add([ordered]@{severity="info";code="GARUDANETRA_CANONICAL_ENGINE";detail="Playwright runtime detected inside KRISHNA venv."})
}
if(!$components.browser_fabric_source.exists){
  [void]$findings.Add([ordered]@{severity="critical";code="BROWSER_FABRIC_SOURCE_MISSING";detail=$components.browser_fabric_source.path})
}
if($summaries.browser_data_legacy.exists){
  [void]$findings.Add([ordered]@{severity="notice";code="LEGACY_BROWSER_DATA_PRESENT";detail=$targets.browser_data_legacy})
}
if($summaries.playwright_browsers.exists){
  [void]$findings.Add([ordered]@{severity="info";code="PLAYWRIGHT_BROWSER_ASSETS_PRESENT";detail=$targets.playwright_browsers})
}
if($env:KRISHNA_BROWSER_HARNESS_CMD){
  [void]$findings.Add([ordered]@{severity="info";code="BROWSER_HARNESS_CONFIGURED";detail="KRISHNA_BROWSER_HARNESS_CMD is configured."})
}
if($env:KRISHNA_BROWSER_VISION_RECOVERY_CMD){
  [void]$findings.Add([ordered]@{severity="info";code="BROWSER_VISION_RECOVERY_CONFIGURED";detail="KRISHNA_BROWSER_VISION_RECOVERY_CMD is configured."})
}
if($components.legacy_garudanetra_source.exists){
  [void]$findings.Add([ordered]@{severity="notice";code="LEGACY_GARUDANETRA_MODULE_PRESENT";detail="garudanetra.py remains only for compatibility; server authority must remain browser_fabric.py + garudanetra_session.py."})
}
if(!$manifest){[void]$findings.Add([ordered]@{severity="critical";code="DEPLOYMENT_MANIFEST_MISSING";detail=$manifestPath})}
foreach($x in $sourceRuntime){
  if($x.candidate_exists -and $x.canonical_exists -and !$x.same){
    [void]$findings.Add([ordered]@{severity="critical";code="SOURCE_RUNTIME_DRIFT";detail=$x.candidate})
  }
}
foreach($p in $proc){
 if($p.CommandLine -match "\\agents\\astra_worker.py|\\agents\\autonomous_recovery_loop.py|\\guardian\\autopilot.py|\\mobile\\companion\\server.py"){
   [void]$findings.Add([ordered]@{severity="notice";code="LEGACY_PARALLEL_PROCESS";detail=$p.CommandLine;pid=$p.ProcessId})
 }
}
if($components.source_mobile_v3.exists -and !$components.canonical_mobile_main.exists){
  [void]$findings.Add([ordered]@{severity="critical";code="CANONICAL_MOBILE_RUNTIME_MISSING";detail="Repository mobile_v3 exists but deployed mobile\app-source is missing."})
}
if($components.canonical_mobile_main.exists -and $components.mobile_runtime_manifest.exists){
  [void]$findings.Add([ordered]@{severity="info";code="MOBILE_V3_CANONICAL";detail="mobile_v3 is deployed under mobile\app-source with a deployment manifest."})
}
if($components.mobile_companion_server.exists){
  [void]$findings.Add([ordered]@{severity="notice";code="LEGACY_MOBILE_COMPANION_PRESENT";detail="mobile\companion is preserved for compatibility only; mobile_v3/mobile\app-source is the product authority after deployment."})
}
foreach($x in $leftovers){
  if($x.exists){[void]$findings.Add([ordered]@{severity="notice";code="UNRESOLVED_LEFTOVER";detail=$x.path})}
}

$findingRows=@($findings | ForEach-Object { $_ })
$processRows=@($proc | ForEach-Object { $_ })
$listenerRows=@($listeners | ForEach-Object { $_ })
$report=[ordered]@{
 schema=2
 generated_at=(Get-Date).ToUniversalTime().ToString("o")
 machine=$env:COMPUTERNAME
 source_root=$SourceRoot
 runtime_root=$RuntimeRoot
 deployment_manifest=$manifest
 folders=$summaries
 components=$components
 browser_environment=$browserEnv
 unresolved_leftovers=$leftovers
 comparisons=$comparisons
 source_runtime=$sourceRuntime
 running_processes=$processRows
 listeners=$listenerRows
 findings=$findingRows
}
$out=Join-Path $reportDir "e-drive-audit-$stamp.json"
$report|ConvertTo-Json -Depth 12|Set-Content -Encoding UTF8 $out

Write-Host "=== KRISHNA E: DRIVE AUDIT ===" -ForegroundColor Cyan
Write-Host "Report: $out"
Write-Host "Findings: $($findings.Count)"
$findings|ForEach-Object{Write-Host ("[{0}] {1} - {2}" -f $_.severity,$_.code,$_.detail)}
Write-Output $out

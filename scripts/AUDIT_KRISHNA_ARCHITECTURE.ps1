param(
  [string]$SourceRoot="E:\KRISHNA-SOURCE",
  [string]$OutFile=""
)

$ErrorActionPreference="Stop"
$SourceRoot=(Resolve-Path $SourceRoot).Path
$core=Join-Path $SourceRoot "core"
if(!(Test-Path $core)){throw "KRISHNA core not found: $core"}

$candidates=@(
  (Join-Path $SourceRoot ".venv\Scripts\python.exe"),
  "E:\Krishna-The GOD\.venv\Scripts\python.exe"
)
$Python=$null
foreach($candidate in $candidates){
  if(Test-Path $candidate){$Python=$candidate;break}
}
if(!$Python){
  $cmd=Get-Command python -ErrorAction SilentlyContinue
  if($cmd){$Python=$cmd.Source}
}
if(!$Python){throw "Python runtime not found"}

if(!$OutFile){
  $reportDir=Join-Path $SourceRoot "reports"
  New-Item -ItemType Directory -Force $reportDir|Out-Null
  $OutFile=Join-Path $reportDir ("architecture-truth-"+(Get-Date -Format "yyyyMMdd-HHmmss")+".json")
}

$previousPythonPath=$env:PYTHONPATH
$previousRoot=$env:KRISHNA_ARCHITECTURE_ROOT
try{
  $env:PYTHONPATH=$core
  $env:KRISHNA_ARCHITECTURE_ROOT=$SourceRoot
  $json=& $Python -c "import json,os; from krishna_core.architecture_truth import ArchitectureTruthAudit; print(json.dumps(ArchitectureTruthAudit(os.environ['KRISHNA_ARCHITECTURE_ROOT']).scan(),ensure_ascii=False,indent=2))"
  if($LASTEXITCODE -ne 0){throw "Architecture truth audit failed"}
  $report=$json|ConvertFrom-Json
  $json|Set-Content -Encoding UTF8 $OutFile
  Write-Host "=== KRISHNA ARCHITECTURE TRUTH ===" -ForegroundColor Cyan
  Write-Host ("Ledger                 : "+$report.requirements.version)
  Write-Host ("Requirements indexed   : "+$report.summary.requirements_indexed)
  Write-Host ("Missing evidence paths  : "+$report.summary.requirements_missing_evidence)
  Write-Host ("Legacy roots present    : "+$report.summary.legacy_roots_present)
  Write-Host ("Duplicate basenames     : "+$report.summary.duplicate_basenames)
  Write-Host ("Identical content groups: "+$report.summary.identical_content_groups)
  Write-Host ("Orphan review candidates: "+$report.summary.orphan_candidates)
  Write-Host ("Stale source-tree gaps  : "+$report.summary.source_tree_missing_current_modules)
  Write-Host ("Report                  : "+$OutFile) -ForegroundColor Green
  $report
}
finally{
  if($null -eq $previousPythonPath){Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue}else{$env:PYTHONPATH=$previousPythonPath}
  if($null -eq $previousRoot){Remove-Item Env:KRISHNA_ARCHITECTURE_ROOT -ErrorAction SilentlyContinue}else{$env:KRISHNA_ARCHITECTURE_ROOT=$previousRoot}
}

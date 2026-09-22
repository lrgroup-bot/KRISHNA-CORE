param(
  [Parameter(Mandatory=$true)][string]$Project,
  [Parameter(Mandatory=$true)][string]$Url,
  [int]$DeadlineMinutes=60,
  [string]$SchemaUrl="",
  [string]$ApiBaseUrl="",
  [string[]]$Checks=@(),
  [string]$BuildHash="",
  [switch]$NoBackend,
  [switch]$NoRestartGate,
  [switch]$NoPerformanceGate,
  [switch]$NoAxeGate,
  [switch]$ApproveVisualBaselines,
  [string]$CoreBase="http://127.0.0.1:8766",
  [string]$RuntimeRoot="E:\Krishna-The GOD"
)
$ErrorActionPreference="Stop"

$uri=$CoreBase.TrimEnd("/")+"/api/project-perfection/finish"
$reports=Join-Path $RuntimeRoot "reports\project-perfection"
New-Item -ItemType Directory -Force -Path $reports | Out-Null

$body=[ordered]@{
  project=$Project
  url=$Url
  deadline_minutes=$DeadlineMinutes
  requirements_ok=$true
  backend_required=(-not $NoBackend)
  restart_recovery_required=(-not $NoRestartGate)
  performance_required=(-not $NoPerformanceGate)
  axe_required=(-not $NoAxeGate)
  hawkeye_ui_required=$true
  approve_visual_baselines=[bool]$ApproveVisualBaselines
  auto_repair=$true
  max_repair_rounds=3
  run_qa_workers=$true
  max_mutants=8
  apply_verified=$true
}
if($SchemaUrl){$body.schema_url=$SchemaUrl}
if($ApiBaseUrl){$body.api_base_url=$ApiBaseUrl}
if($Checks.Count){$body.checks=$Checks}
if($BuildHash){$body.build_hash=$BuildHash}

Write-Host "=== KRISHNA FINISH PROJECT ===" -ForegroundColor Cyan
Write-Host ("Project : "+$Project)
Write-Host ("URL     : "+$Url)
Write-Host ("Deadline: "+$DeadlineMinutes+" min")
Write-Host "Running governed Project Perfection pipeline..." -ForegroundColor Cyan

try{
  $result=Invoke-RestMethod -Method Post -Uri $uri -ContentType "application/json" -Body ($body|ConvertTo-Json -Depth 12) -TimeoutSec 3600
}catch{
  $detail=$_.Exception.Message
  if($_.ErrorDetails.Message){$detail+=[Environment]::NewLine+$_.ErrorDetails.Message}
  throw "Project Perfection request failed: $detail"
}

$stamp=Get-Date -Format "yyyyMMdd-HHmmss"
$out=Join-Path $reports ($Project.Replace(" ","_")+"-"+$stamp+".json")
$result|ConvertTo-Json -Depth 30|Set-Content -LiteralPath $out -Encoding UTF8

$cert=$result.certificate
Write-Host ""
Write-Host ("VERDICT : "+$result.verdict) -ForegroundColor $(if($result.passed){"Green"}else{"Red"})
Write-Host ("CERT ID : "+$cert.certificate_id)
Write-Host ("REPORT  : "+$out)
Write-Host ""
foreach($gate in @($result.gates)){
  $status=if($gate.passed){"PASS"}else{"FAIL"}
  $color=if($gate.passed){"Green"}else{"Red"}
  Write-Host ("[{0}] {1}" -f $status,$gate.gate) -ForegroundColor $color
}
if($result.repair_history){
  Write-Host ""
  Write-Host ("Auto-repair rounds: "+@($result.repair_history).Count) -ForegroundColor Yellow
}
if($result.live_apply){
  Write-Host ("LIVE APPLY: "+$result.live_apply.status) -ForegroundColor $(if($result.live_apply.promoted){"Green"}elseif($result.live_apply.rolled_back){"Red"}else{"Yellow"})
}elseif($result.promotion -and $result.promotion.promotion_token){
  Write-Host ("Verified promotion candidate: "+$result.promotion.promotion_token) -ForegroundColor Cyan
}
if(-not $result.passed){ exit 2 }
exit 0

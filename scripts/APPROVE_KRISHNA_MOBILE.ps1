param(
  [string]$CoreUrl="http://127.0.0.1:8766",
  [string]$DeviceId=""
)
$ErrorActionPreference="Stop"
$base=$CoreUrl.TrimEnd("/")

$pending=Invoke-RestMethod -Method Get -Uri ($base+"/api/mobile/pair/pending") -TimeoutSec 10
$rows=@($pending.pending)

if($DeviceId){
  $rows=@($rows | Where-Object { [string]$_.device_id -eq $DeviceId })
}
if($rows.Count -eq 0){
  Write-Host "No matching KRISHNA Mobile pairing request is pending." -ForegroundColor Yellow
  exit 2
}
if($rows.Count -ne 1){
  Write-Host "More than one KRISHNA Mobile pairing request is pending. Refusing to guess." -ForegroundColor Red
  $rows | Select-Object device_id,name,created_at,expires_at,credential_proposed | Format-Table -AutoSize
  exit 3
}

$row=$rows[0]
if(-not [bool]$row.credential_proposed){
  throw "Pending device did not propose a client-held credential; refusing zero-code approval."
}

$body=@{request_id=[string]$row.request_id}|ConvertTo-Json
$approved=Invoke-RestMethod -Method Post -Uri ($base+"/api/mobile/pair/approve") -ContentType "application/json" -Body $body -TimeoutSec 10

if(-not $approved.approved){throw "KRISHNA Mobile approval did not complete"}
if([string]$approved.mode -ne "client-hash-zero-code"){throw "KRISHNA Mobile did not use zero-code client-hash pairing"}

Write-Host ("[PASS] KRISHNA Mobile approved: {0} | mode={1}" -f $approved.device_id,$approved.mode) -ForegroundColor Green
Write-Host "No pairing code or plaintext device credential was returned by the PC." -ForegroundColor Green

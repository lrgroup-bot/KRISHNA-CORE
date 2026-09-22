param(
  [string]$CoreUrl = "http://127.0.0.1:8766",
  [string]$RuntimeRoot = "E:\Krishna-The GOD",
  [string]$ApkPath = "",
  [switch]$SaveBaseline
)

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

function Assert-EPath([string]$Path,[string]$Label){
  $full=[System.IO.Path]::GetFullPath($Path)
  if($full -notmatch '^[Ee]:\\'){ throw "$Label must remain on E:. Refusing: $full" }
  return $full
}
$RuntimeRoot=Assert-EPath $RuntimeRoot "KRISHNA runtime"
$reportRoot=Assert-EPath (Join-Path $RuntimeRoot "state\privacy") "Privacy acceptance evidence"
New-Item -ItemType Directory -Force -Path $reportRoot | Out-Null

function Invoke-KrishnaJson([string]$Path,[object]$Body=$null){
  $uri=$CoreUrl.TrimEnd("/")+$Path
  if($null -eq $Body){
    return Invoke-RestMethod -Uri $uri -Method Get -TimeoutSec 60
  }
  return Invoke-RestMethod -Uri $uri -Method Post -ContentType "application/json" -Body ($Body|ConvertTo-Json -Depth 20) -TimeoutSec 120
}

Write-Host "=== KABACH PRIVACY GUARDIAN ACCEPTANCE ===" -ForegroundColor Cyan
Write-Host ("Core: "+$CoreUrl)
Write-Host ("Evidence: "+$reportRoot)

$status=Invoke-KrishnaJson "/api/kabach/privacy/status"
if($status.owner -ne "KABACH Privacy Guardian"){throw "Privacy Guardian runtime is not active"}
if(!$status.internal_only -or $status.main_menu){throw "Privacy Guardian UI boundary is incorrect"}
Write-Host "Runtime status: READY (internal KABACH capability)" -ForegroundColor Green

$clean=Invoke-KrishnaJson "/api/kabach/privacy/clean-url" @{
  url="https://example.com/path?id=7&utm_source=kabach&fbclid=test&custom=preserve"
}
if($clean.after -match "utm_source|fbclid"){throw "Tracking URL cleaner failed"}
if($clean.after -notmatch "id=7" -or $clean.after -notmatch "custom=preserve"){throw "Tracking URL cleaner removed a functional/unknown parameter"}
Write-Host "Tracking link cleaner: PASS" -ForegroundColor Green

$webUrl=$CoreUrl.TrimEnd("/")+"/dashboard"
$web=Invoke-KrishnaJson "/api/kabach/privacy/audit" @{
  target_type="web";url=$webUrl;owned=$true;profile="WEB_ENDPOINT";policy="WEB_RELEASE"
}
if($web.target_type -ne "web"){throw "Owned web audit did not execute"}
Write-Host ("KRISHNA web audit: PASS ("+$web.findings.Count+" findings captured)") -ForegroundColor Green

$browser=Invoke-KrishnaJson "/api/kabach/privacy/audit" @{
  target_type="browser";url=$webUrl;profile="FRESH_PROFILE";policy="STRICT"
}
if($browser.target_type -ne "browser"){throw "Browser privacy audit did not execute"}
if(!$browser.metadata.temporary_profile){throw "Browser privacy audit was not isolated"}
if(!$browser.metadata.fingerprint.identifier){throw "Local fingerprint identifier was not produced"}
if($browser.metadata.fingerprint.uploaded){throw "Local fingerprint must not be uploaded"}
Write-Host ("Browser privacy audit: PASS ("+$browser.findings.Count+" findings captured)") -ForegroundColor Green

$network=Invoke-KrishnaJson "/api/kabach/privacy/audit" @{
  target_type="network";profile="BASELINE";policy="STANDARD"
}
if($network.target_type -ne "network"){throw "Network privacy lane did not execute"}
$networkConfigured=[bool]$status.network_probe.configured
if($networkConfigured){
  Write-Host "External network probe: CONFIGURED / RESULT CAPTURED" -ForegroundColor Green
}else{
  Write-Host "External network probe: NOT CONFIGURED (public IP/DNS/TLS claims remain unsupported)" -ForegroundColor Yellow
}

$mobile=$null
if($ApkPath){
  $apk=[System.IO.Path]::GetFullPath($ApkPath)
  if(!(Test-Path $apk)){throw "APK not found: $apk"}
  $mobile=Invoke-KrishnaJson "/api/kabach/privacy/audit" @{
    target_type="mobile";apk_path=$apk;profile="KRISHNA_MOBILE";policy="MOBILE_RELEASE"
  }
  if($mobile.target_type -ne "mobile"){throw "Mobile privacy audit did not execute"}
  Write-Host ("KRISHNA Mobile static audit: PASS ("+$mobile.findings.Count+" findings captured)") -ForegroundColor Green
}else{
  Write-Host "KRISHNA Mobile static audit: SKIPPED (pass -ApkPath to test a real APK)" -ForegroundColor Yellow
}

$baselineName="kabach-acceptance-dashboard"
if($SaveBaseline){
  $saved=Invoke-KrishnaJson "/api/kabach/privacy/baseline" @{name=$baselineName;report=$browser}
  if(!$saved.stored){throw "Privacy baseline was not stored"}
  $comparison=Invoke-KrishnaJson "/api/kabach/privacy/compare" @{name=$baselineName;report=$browser;configuration_change="acceptance rerun"}
  if($comparison.regression_count -ne 0){throw "New baseline unexpectedly regressed against itself"}
  Write-Host "Baseline/regression round-trip: PASS" -ForegroundColor Green
}

$full=Invoke-KrishnaJson "/api/kabach/privacy/audit" @{
  target_type="full";url=$webUrl;web_url=$webUrl;apk_path=$(if($ApkPath){[System.IO.Path]::GetFullPath($ApkPath)}else{""});profile="FRESH_PROFILE";policy="STRICT"
}

$bundle=[ordered]@{
  generated_at=(Get-Date).ToUniversalTime().ToString("o")
  core_url=$CoreUrl
  status=$status
  tracking_url_cleaner=$clean
  web=$web
  browser=$browser
  network=$network
  mobile=$mobile
  full=$full
}
$path=Join-Path $reportRoot ("kabach-privacy-acceptance-"+(Get-Date -Format "yyyyMMdd-HHmmss")+".json")
$bundle|ConvertTo-Json -Depth 30|Set-Content -Encoding UTF8 $path

Write-Host ""
Write-Host "=== KABACH PRIVACY ACCEPTANCE RESULT ===" -ForegroundColor Cyan
Write-Host ("Browser runtime     : "+$(if($full.definition_of_done.browser_real_runtime){"VERIFIED"}else{"NOT VERIFIED"}))
Write-Host ("KRISHNA web endpoint: "+$(if($full.definition_of_done.web_real_endpoint){"VERIFIED"}else{"NOT VERIFIED"}))
Write-Host ("External network    : "+$(if($full.definition_of_done.network_external_runtime){"VERIFIED"}else{"NOT VERIFIED"}))
Write-Host ("Real APK static     : "+$(if($full.definition_of_done.mobile_real_apk_static){"VERIFIED"}else{"NOT VERIFIED"}))
Write-Host ("Mobile dynamic      : NOT VERIFIED (requires real-device dynamic test)")
Write-Host ("Evidence bundle     : "+$path)

if(!$full.definition_of_done.browser_real_runtime -or !$full.definition_of_done.web_real_endpoint){
  throw "Required local browser/web privacy acceptance did not complete"
}

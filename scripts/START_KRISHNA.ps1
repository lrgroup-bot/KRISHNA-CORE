param(
    [Parameter(Mandatory=$false)][string]$KrishnaRoot = "E:\Krishna-The GOD",
    [Parameter(Mandatory=$false)][int]$Port = 8766,
    [Parameter(Mandatory=$false)][string]$SourceRoot = "",
    [Parameter(Mandatory=$false)][switch]$PrivateRemote,
    [Parameter(Mandatory=$false)][switch]$MobileLan,
    [Parameter(Mandatory=$false)][string]$PrivateRemoteCIDRs = "",
    [Parameter(Mandatory=$false)][string]$TailscaleExe = ""
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$KrishnaRoot=[IO.Path]::GetFullPath($KrishnaRoot)
$authoritative = if($SourceRoot){[IO.Path]::GetFullPath($SourceRoot)}elseif(Test-Path "E:\KRISHNA-SOURCE\.git"){"E:\KRISHNA-SOURCE"}else{""}
$coreDir=Join-Path $KrishnaRoot "core"
$py=Join-Path $KrishnaRoot ".venv\Scripts\python.exe"
$logDir=Join-Path $KrishnaRoot "logs"
if(!(Test-Path $py)){throw "KRISHNA venv Python not found: $py"}
if(!(Test-Path $logDir)){New-Item -ItemType Directory -Force $logDir|Out-Null}

# Keep runtime automatically synchronized to the authoritative Git source.
if($authoritative -and (Test-Path "$authoritative\.git")){
    $env:KRISHNA_SOURCE_ROOT=$authoritative
    $sourceHead=(git -C $authoritative rev-parse HEAD).Trim()
    $manifestPath=Join-Path $KrishnaRoot "state\deployment\DEPLOYED_COMMIT.json"
    $deployed=""
    if(Test-Path $manifestPath){
        try{$deployed=(Get-Content -Raw $manifestPath|ConvertFrom-Json).commit}catch{$deployed=""}
    }
    if(!$deployed -or $deployed -ne $sourceHead){
        Write-Host "KRISHNA runtime is not synchronized. Running verified deploy..." -ForegroundColor Yellow
        $deploy=Join-Path $authoritative "scripts\DEPLOY_KRISHNA_ONCE.ps1"
        if(!(Test-Path $deploy)){throw "Verified deploy script missing: $deploy"}
        & powershell -NoProfile -ExecutionPolicy Bypass -File $deploy -SkipStart -SourceRoot $authoritative
        if($LASTEXITCODE -ne 0){throw "Automatic verified deployment failed"}
    }
}

if(!(Test-Path $coreDir)){throw "KRISHNA core directory not found: $coreDir"}
$env:PYTHONPATH=$coreDir
$voiceConfig=Join-Path $KrishnaRoot "config\voice-runtime.ps1"
if(Test-Path $voiceConfig){. $voiceConfig}
$browserConfig=Join-Path $KrishnaRoot "config\browser-runtime.ps1"
if(Test-Path $browserConfig){
    . $browserConfig
    Write-Host "Browser adapter config loaded: $browserConfig" -ForegroundColor DarkCyan
}
$naradConfig=Join-Path $KrishnaRoot "config\narad-runtime.ps1"
if(Test-Path $naradConfig){
    . $naradConfig
    Write-Host "NARAD adapter config loaded: $naradConfig" -ForegroundColor DarkCyan
}
$bindHost="127.0.0.1"
$lanIp=""
$remoteIp=""
$env:KRISHNA_LAN_DISCOVERY="0"
$env:KRISHNA_PRIVATE_REMOTE_URL=""
if($PrivateRemote -and $MobileLan){throw "Choose either -PrivateRemote or -MobileLan, not both"}
if($MobileLan){
    $bindHost="0.0.0.0"
    $env:KRISHNA_LAN_DISCOVERY="1"
    try{
        $lanIp=(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction Stop | Where-Object {$_.IPAddress -notmatch '^(127\.|169\.254\.)' -and $_.PrefixOrigin -ne 'WellKnown'} | Sort-Object InterfaceMetric | Select-Object -First 1 -ExpandProperty IPAddress)
    }catch{$lanIp=""}
}
if($PrivateRemote){
    $tailscalePath=""
    if($TailscaleExe -and (Test-Path $TailscaleExe)){
        $tailscalePath=[IO.Path]::GetFullPath($TailscaleExe)
    }else{
        $tailscale=(Get-Command tailscale.exe -ErrorAction SilentlyContinue)
        if($tailscale){$tailscalePath=$tailscale.Source}
        elseif(Test-Path "E:\TailScale\tailscale.exe"){$tailscalePath="E:\TailScale\tailscale.exe"}
    }
    if(!$tailscalePath){throw "PrivateRemote requested but tailscale.exe is not installed/found"}
    $tsIp=(& $tailscalePath ip -4 2>$null | Select-Object -First 1).Trim()
    if(!$tsIp){throw "PrivateRemote requested but no Tailscale IPv4 address is available"}
    $parsed=$null
    if(![System.Net.IPAddress]::TryParse($tsIp,[ref]$parsed)){throw "Tailscale returned an invalid IP: $tsIp"}
    $remoteIp=$tsIp
    # Bind loopback + private interfaces through one listener; Core itself rejects public clients.
    $bindHost="0.0.0.0"
    # Keep UDP discovery available on the trusted local network for first-time
    # zero-code mobile enrollment. Authenticated control remains pairing-gated.
    $env:KRISHNA_LAN_DISCOVERY="1"
    $env:KRISHNA_PRIVATE_REMOTE_CIDRS=if($PrivateRemoteCIDRs){$PrivateRemoteCIDRs}else{"100.64.0.0/10"}
    $env:KRISHNA_PRIVATE_REMOTE_URL=("http://{0}:{1}" -f $remoteIp,$Port)
}
$env:KRISHNA_HOST=$bindHost
$env:KRISHNA_PORT=[string]$Port
$env:KRISHNA_RUNTIME_ROOT=$KrishnaRoot
$env:KRISHNA_BROWSER_DATA_ROOT=Join-Path $KrishnaRoot "state\garudanetra"
$playwrightRoot=Join-Path $KrishnaRoot "playwright-browsers"
if(Test-Path $playwrightRoot){$env:PLAYWRIGHT_BROWSERS_PATH=$playwrightRoot}
if($authoritative){$env:KRISHNA_SOURCE_ROOT=$authoritative}
if (!$env:KRISHNA_DB) { $env:KRISHNA_DB=Join-Path $KrishnaRoot "krishna_core.db" }
if (!$env:KRISHNA_ALLOW_ACTIONS) { $env:KRISHNA_ALLOW_ACTIONS="0" }

# Never advertise CORE ONLINE when deployed files no longer match the verified manifest.
$integrityJson=& $py -c "import json; from krishna_core.runtime_integrity import RuntimeIntegrity; print(json.dumps(RuntimeIntegrity().status()))"
if($LASTEXITCODE -ne 0){throw "Runtime integrity check could not run"}
$integrity=$integrityJson|ConvertFrom-Json
if($integrity.status -eq "DRIFT"){
    if($authoritative -and (Test-Path "$authoritative\.git")){
        Write-Host "KRISHNA runtime drift detected. Re-running verified deployment..." -ForegroundColor Yellow
        $deploy=Join-Path $authoritative "scripts\DEPLOY_KRISHNA_ONCE.ps1"
        & powershell -NoProfile -ExecutionPolicy Bypass -File $deploy -SkipStart
        if($LASTEXITCODE -ne 0){throw "Automatic drift reconciliation deployment failed"}
        $integrityJson=& $py -c "import json; from krishna_core.runtime_integrity import RuntimeIntegrity; print(json.dumps(RuntimeIntegrity().status()))"
        if($LASTEXITCODE -ne 0){throw "Post-reconciliation integrity check could not run"}
        $integrity=$integrityJson|ConvertFrom-Json
    }
    if($integrity.status -eq "DRIFT"){
        throw ("KRISHNA runtime drift remains after reconciliation. Missing={0}; mismatches={1}; source_drift={2}" -f (($integrity.missing -join ',')),(($integrity.mismatches -join ',')),$integrity.source_drift)
    }
}
if($integrity.status -eq "UNVERIFIED"){Write-Host "KRISHNA runtime has no verified deployment manifest." -ForegroundColor Yellow}

Write-Host ""
Write-Host "KRISHNA MODERN CORE START" -ForegroundColor Cyan
Write-Host "Root      : $KrishnaRoot"
Write-Host "Source    : $authoritative"
Write-Host "Integrity : $($integrity.status)"
Write-Host "Commit    : $($integrity.commit)"
Write-Host "UI        : http://127.0.0.1`:$Port/"
Write-Host "Browser   : Garudanetra Fabric | Playwright canonical | adapters explicit"
if($MobileLan){
    $mobileAddress=if($lanIp){"http://$lanIp`:$Port/"}else{"LAN address will be discovered by phone"}
    Write-Host "Mobile    : $mobileAddress | discovery ON | pairing required" -ForegroundColor Green
}
if($PrivateRemote){
    Write-Host "Remote    : http://$remoteIp`:$Port/ | PRIVATE OVERLAY | pairing required" -ForegroundColor Green
}
Write-Host ""

& $py -u -m krishna_core.server
exit $LASTEXITCODE

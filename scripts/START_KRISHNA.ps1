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

$mrityunjayHandoffPath=Join-Path $KrishnaRoot ".krishna_state\mrityunjay\deploy-handoff.json"
$mrityunjayLastHandoffPath=Join-Path $KrishnaRoot ".krishna_state\mrityunjay\last-deploy-handoff.json"

function Get-MrityunjayHandoff {
    if(!(Test-Path $mrityunjayHandoffPath)){return $null}
    try{
        $row=Get-Content -Raw $mrityunjayHandoffPath|ConvertFrom-Json
        if([string]$row.owner -ne "MRITYUNJAY"){return $null}
        if([string]$row.status -ne "restart_requested"){return $null}
        return $row
    }catch{
        Write-Warning ("MRITYUNJAY handoff is unreadable: "+$_.Exception.Message)
        return $null
    }
}

function Save-MrityunjayHandoffResult($Handoff,[string]$Status,[string]$Detail){
    $row=[ordered]@{}
    foreach($p in $Handoff.PSObject.Properties){$row[$p.Name]=$p.Value}
    $row.status=$Status
    $row.completed_at=(Get-Date).ToUniversalTime().ToString("o")
    $row.detail=$Detail
    $dir=Split-Path -Parent $mrityunjayLastHandoffPath
    New-Item -ItemType Directory -Force $dir|Out-Null
    $row|ConvertTo-Json -Depth 8|Set-Content -Encoding UTF8 $mrityunjayLastHandoffPath
    Remove-Item -Force $mrityunjayHandoffPath -ErrorAction SilentlyContinue
}

function Restore-MrityunjayPreviousSource($Handoff,[string]$Reason){
    if(!$authoritative -or !(Test-Path "$authoritative\.git")){throw "MRITYUNJAY rollback requires authoritative Git source"}
    $current=(git -C $authoritative rev-parse HEAD).Trim()
    $expected=[string]$Handoff.new_commit
    if($current -ne $expected){
        throw ("MRITYUNJAY rollback refused because current HEAD changed. expected="+$expected+" current="+$current)
    }
    $previous=[string]$Handoff.previous_commit
    if(!$previous){throw "MRITYUNJAY rollback has no previous commit"}
    & git -C $authoritative reset --hard $previous
    if($LASTEXITCODE -ne 0){throw "MRITYUNJAY could not reset source to previous commit"}
    $deploy=Join-Path $authoritative "scripts\DEPLOY_KRISHNA_ONCE.ps1"
    $branch=[string]$Handoff.branch
    & powershell -NoProfile -ExecutionPolicy Bypass -File $deploy -Branch $branch -SkipStart
    if($LASTEXITCODE -ne 0){throw "MRITYUNJAY rollback deployment failed"}
    Save-MrityunjayHandoffResult $Handoff "rolled_back" $Reason
    Write-Warning ("MRITYUNJAY autonomous upgrade rolled back: "+$Reason)
}

function Complete-MrityunjayHandoff($Handoff){
    if(!$authoritative -or !(Test-Path "$authoritative\.git")){throw "MRITYUNJAY handoff requires authoritative Git source"}
    $head=(git -C $authoritative rev-parse HEAD).Trim()
    $newCommit=[string]$Handoff.new_commit
    if($head -ne $newCommit){return $false}
    $manifestPath=Join-Path $KrishnaRoot "state\deployment\DEPLOYED_COMMIT.json"
    if(!(Test-Path $manifestPath)){throw "MRITYUNJAY handoff cannot find verified deployment manifest"}
    $manifest=Get-Content -Raw $manifestPath|ConvertFrom-Json
    if([string]$manifest.commit -ne $newCommit){
        throw "MRITYUNJAY refuses remote push before verified runtime deployment matches the new commit"
    }
    $branch=(git -C $authoritative branch --show-current).Trim()
    if(!$branch -or $branch -ne [string]$Handoff.branch){
        Restore-MrityunjayPreviousSource $Handoff "canonical branch changed before remote push"
        return $true
    }
    & git -C $authoritative push origin $branch
    $pushExit=$LASTEXITCODE

    # A network disconnect can make push return non-zero even after the remote
    # accepted the commit. Check the actual remote head before deciding rollback.
    $remoteProbe=& git -C $authoritative ls-remote origin ("refs/heads/"+$branch) 2>$null
    $remoteProbeExit=$LASTEXITCODE
    $remoteActual=""
    if($remoteProbeExit -eq 0 -and $remoteProbe){
        $remoteActual=([string]($remoteProbe|Select-Object -First 1)).Split([char]9)[0].Trim()
    }
    if($remoteActual -eq $newCommit){
        # Push is verified, regardless of the client's original exit code.
    }elseif($pushExit -ne 0 -and $remoteActual -eq [string]$Handoff.previous_commit){
        Restore-MrityunjayPreviousSource $Handoff "remote push was rejected and remote remained on the previous commit"
        return $true
    }elseif(!$remoteActual){
        throw "MRITYUNJAY cannot determine remote state after push; retaining handoff for retry rather than guessing rollback"
    }else{
        throw ("MRITYUNJAY remote branch changed unexpectedly. remote="+$remoteActual+" expected="+$newCommit)
    }

    & git -C $authoritative fetch --quiet origin
    if($LASTEXITCODE -ne 0){
        throw "MRITYUNJAY remote push is verified but tracking-ref refresh failed; retaining handoff for retry"
    }
    $remote=(git -C $authoritative rev-parse ("origin/"+$branch)).Trim()
    if($remote -ne $newCommit){
        throw "MRITYUNJAY remote tracking ref does not match the verified autonomous commit"
    }
    Save-MrityunjayHandoffResult $Handoff "completed" "verified deployment accepted and canonical remote push verified"
    Write-Host ("MRITYUNJAY AUTONOMOUS UPGRADE VERIFIED: "+$newCommit) -ForegroundColor Green
    return $true
}

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
        & powershell -NoProfile -ExecutionPolicy Bypass -File $deploy -SkipStart
        if($LASTEXITCODE -ne 0){
            $handoff=Get-MrityunjayHandoff
            if($handoff -and [string]$handoff.new_commit -eq $sourceHead){
                Restore-MrityunjayPreviousSource $handoff "verified deployment/acceptance failed"
                $sourceHead=(git -C $authoritative rev-parse HEAD).Trim()
            }else{
                throw "Automatic verified deployment failed"
            }
        }else{
            $handoff=Get-MrityunjayHandoff
            if($handoff -and [string]$handoff.new_commit -eq $sourceHead){
                [void](Complete-MrityunjayHandoff $handoff)
                $sourceHead=(git -C $authoritative rev-parse HEAD).Trim()
            }
        }
    }

    # A previous restart may already have deployed the local autonomous commit
    # but still be waiting to verify/push the remote branch. Complete that durable
    # handoff before runtime-integrity checks.
    $handoff=Get-MrityunjayHandoff
    if($handoff){
        $currentHead=(git -C $authoritative rev-parse HEAD).Trim()
        if([string]$handoff.new_commit -eq $currentHead){
            [void](Complete-MrityunjayHandoff $handoff)
        }
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

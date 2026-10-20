Set-StrictMode -Version Latest

function Get-KrishnaNetworkConstants {
    $repoRoot = Split-Path -Parent $PSScriptRoot
    $manifest = Join-Path $repoRoot "core\krishna_core\server_ports.json"
    if(!(Test-Path -LiteralPath $manifest)){
        throw "KRISHNA network constants manifest missing: $manifest"
    }
    try{
        $cfg = Get-Content -LiteralPath $manifest -Raw | ConvertFrom-Json
    }catch{
        throw "KRISHNA network constants manifest is invalid JSON: $manifest"
    }

    $core = [int]$cfg.krishna_core
    $mobile = [int]$cfg.mobile_companion
    $discovery = [int]$cfg.lan_discovery
    foreach($item in @(
        @{Name="krishna_core";Value=$core},
        @{Name="mobile_companion";Value=$mobile},
        @{Name="lan_discovery";Value=$discovery}
    )){
        if($item.Value -lt 1 -or $item.Value -gt 65535){
            throw ("Invalid KRISHNA port {0}={1}" -f $item.Name,$item.Value)
        }
    }
    if(@($core,$mobile,$discovery | Select-Object -Unique).Count -ne 3){
        throw "KRISHNA canonical ports must be distinct"
    }

    return [pscustomobject]@{
        Core = $core
        MobileCompanion = $mobile
        LanDiscovery = $discovery
        Manifest = $manifest
    }
}

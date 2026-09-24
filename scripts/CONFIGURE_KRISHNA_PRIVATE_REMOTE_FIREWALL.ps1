param(
  [int]$CorePort=8766,
  [int]$DiscoveryPort=8767,
  [string]$TailscaleCIDR="100.64.0.0/10"
)
$ErrorActionPreference="Stop"

$identity=[Security.Principal.WindowsIdentity]::GetCurrent()
$principal=New-Object Security.Principal.WindowsPrincipal($identity)
$isAdmin=$principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if(!$isAdmin){
  Write-Warning "KRISHNA firewall configuration requires an elevated PowerShell. Existing rules were not changed."
  exit 0
}

$rules=@(
  @{
    Name="KRISHNA Core Private Remote TCP"
    Protocol="TCP"
    Port=$CorePort
    Remote=@("LocalSubnet",$TailscaleCIDR)
    Description="KRISHNA Core control: trusted LAN plus Tailscale private overlay only."
  },
  @{
    Name="KRISHNA Mobile LAN Discovery UDP"
    Protocol="UDP"
    Port=$DiscoveryPort
    Remote=@("LocalSubnet")
    Description="KRISHNA zero-code mobile discovery on the local subnet only."
  }
)

foreach($spec in $rules){
  Get-NetFirewallRule -DisplayName $spec.Name -ErrorAction SilentlyContinue | Remove-NetFirewallRule -ErrorAction SilentlyContinue
  New-NetFirewallRule -DisplayName $spec.Name -Direction Inbound -Action Allow -Protocol $spec.Protocol -LocalPort $spec.Port -RemoteAddress $spec.Remote -Profile Any -EdgeTraversalPolicy Block -Description $spec.Description | Out-Null
  Write-Host ("[PASS] {0} | {1}/{2} | remote={3}" -f $spec.Name,$spec.Protocol,$spec.Port,($spec.Remote -join ","))
}

Write-Host "KRISHNA private-remote firewall policy installed. No public router/NAT port forwarding is configured." -ForegroundColor Green

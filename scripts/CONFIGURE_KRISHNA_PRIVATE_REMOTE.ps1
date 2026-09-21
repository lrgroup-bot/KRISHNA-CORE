param(
  [string]$RuntimeRoot="E:\Krishna-The GOD",
  [string]$OverlayCIDRs="100.64.0.0/10"
)
$ErrorActionPreference="Stop"
$ts=Get-Command tailscale.exe -ErrorAction SilentlyContinue
if(!$ts){throw "tailscale.exe is not installed. KRISHNA will not expose Core directly to the public Internet."}
$ip=(& $ts.Source ip -4 2>$null | Select-Object -First 1).Trim()
if(!$ip){throw "Tailscale is installed but not connected."}
$status=& $ts.Source status --json 2>$null | ConvertFrom-Json
if(!$status.Self.Online){throw "Tailscale reports this KRISHNA PC offline."}
$config=Join-Path $RuntimeRoot "config\private-remote.ps1"
New-Item -ItemType Directory -Force (Split-Path $config)|Out-Null
@(
  '# Generated KRISHNA private remote configuration',
  '$env:KRISHNA_PRIVATE_REMOTE_CIDRS='+("'" + $OverlayCIDRs.Replace("'","''") + "'"),
  '$env:KRISHNA_HOST='+("'" + $ip + "'")
)|Set-Content -Encoding UTF8 $config
Write-Host "KRISHNA private overlay ready: $ip" -ForegroundColor Green
Write-Host "Start with: .\scripts\START_KRISHNA.ps1 -PrivateRemote" -ForegroundColor Cyan
Write-Host "Public Internet exposure remains blocked by Core network policy." -ForegroundColor Yellow

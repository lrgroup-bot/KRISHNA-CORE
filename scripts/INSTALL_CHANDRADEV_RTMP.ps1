$ErrorActionPreference = "Stop"

$root = if ($env:KRISHNA_ROOT) { $env:KRISHNA_ROOT } else { "E:\Krishna-The GOD" }
$toolRoot = Join-Path $root "tools\mediamtx"
$cacheRoot = Join-Path $root "tools\downloads"
New-Item -ItemType Directory -Force -Path $toolRoot,$cacheRoot | Out-Null

$release = Invoke-RestMethod -Headers @{"User-Agent"="KRISHNA-Chandradev"} -Uri "https://api.github.com/repos/bluenviron/mediamtx/releases/latest"
$asset = $release.assets | Where-Object { $_.name -match "windows_amd64\.zip$" } | Select-Object -First 1
if (-not $asset) { throw "MediaMTX Windows amd64 release asset not found." }

$zip = Join-Path $cacheRoot $asset.name
Invoke-WebRequest -UseBasicParsing -Uri $asset.browser_download_url -OutFile $zip

$extract = Join-Path $cacheRoot "mediamtx-extract"
if (Test-Path $extract) { Remove-Item -Recurse -Force $extract }
Expand-Archive -Force -Path $zip -DestinationPath $extract
Copy-Item -Force (Join-Path $extract "mediamtx.exe") (Join-Path $toolRoot "mediamtx.exe")

$exe = Join-Path $toolRoot "mediamtx.exe"
if (-not (Test-Path $exe)) { throw "MediaMTX install failed." }
Write-Host "MediaMTX installed: $exe"

$ruleName = "KRISHNA Chandradev RTMP 1935"
try {
    $existing = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
    if ($existing) { Remove-NetFirewallRule -DisplayName $ruleName | Out-Null }
    New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow -Protocol TCP -LocalPort 1935 -Profile Private -RemoteAddress LocalSubnet | Out-Null
    Write-Host "Firewall rule ready: Private profile + LocalSubnet only"
} catch {
    Write-Warning "Could not create firewall rule automatically. Run PowerShell as Administrator, or allow TCP 1935 only on Private/LocalSubnet manually."
}

& $exe --version

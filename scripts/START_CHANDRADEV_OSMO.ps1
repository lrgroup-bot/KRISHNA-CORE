$ErrorActionPreference = "Stop"

$root = if ($env:KRISHNA_ROOT) { $env:KRISHNA_ROOT } else { "E:\Krishna-The GOD" }
$exe = Join-Path $root "tools\mediamtx\mediamtx.exe"
if (-not (Test-Path $exe)) {
    throw "MediaMTX not found. Run scripts\INSTALL_CHANDRADEV_RTMP.ps1 first."
}

$state = Join-Path $root "state\chandradev"
New-Item -ItemType Directory -Force -Path $state | Out-Null

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

$streamFile = Join-Path $state "stream-name.txt"
if (Test-Path $streamFile) {
    $stream = (Get-Content $streamFile -Raw).Trim().TrimStart([char]0xFEFF)
} else {
    $stream = "osmo-" + ([guid]::NewGuid().ToString("N").Substring(0,12))
}
# Windows PowerShell 5.1 writes a BOM for -Encoding UTF8. MediaMTX stream/config
# consumers do not need it, so normalize the shared stream name as UTF-8 no BOM.
[System.IO.File]::WriteAllText($streamFile, $stream + [Environment]::NewLine, $utf8NoBom)

# Prefer a real Ethernet/Wi-Fi RFC1918 address with a default gateway. This keeps
# Tailscale/CGNAT (100.64.0.0/10), Hyper-V and other tunnel adapters out of the
# DJI Mimo URL when the phone and KRISHNA PC are on the same LAN.
$ip = Get-NetIPConfiguration |
    Where-Object { $_.IPv4DefaultGateway -and $_.IPv4Address } |
    ForEach-Object { $_.IPv4Address.IPAddress } |
    Where-Object {
        $_ -match '^10\.' -or
        $_ -match '^192\.168\.' -or
        $_ -match '^172\.(1[6-9]|2[0-9]|3[0-1])\.'
    } |
    Select-Object -First 1

if (-not $ip) {
    $ip = Get-NetIPAddress -AddressFamily IPv4 |
        Where-Object {
            $_.IPAddress -notlike "127.*" -and
            $_.IPAddress -notlike "169.254.*" -and
            $_.IPAddress -notmatch '^100\.(6[4-9]|[7-9][0-9]|1[01][0-9]|12[0-7])\.' -and
            $_.PrefixOrigin -ne "WellKnown"
        } |
        Select-Object -First 1 -ExpandProperty IPAddress
}
if (-not $ip) { throw "No usable LAN IPv4 address found. Connect the KRISHNA PC to the same Wi-Fi/LAN as the DJI Mimo phone." }

$config = Join-Path $state "mediamtx.yml"
$yaml = @(
    "logLevel: info",
    "rtsp: false",
    "rtmp: true",
    'rtmpEncryption: "no"',
    "rtmpAddress: :1935",
    "hls: true",
    "hlsAddress: 127.0.0.1:8888",
    "webrtc: true",
    "webrtcAddress: 127.0.0.1:8889",
    "srt: false",
    "api: false",
    "metrics: false",
    "pprof: false",
    "paths:",
    ("  {0}:" -f $stream),
    "    source: publisher",
    "    overridePublisher: false",
    "    maxReaders: 4"
)
$yamlText = ($yaml -join [Environment]::NewLine) + [Environment]::NewLine
# MediaMTX v1.21+ rejects a UTF-8 BOM as part of the first YAML key
# (reported as unknown field "\ufefflogLevel"), so write UTF-8 without BOM.
[System.IO.File]::WriteAllText($config, $yamlText, $utf8NoBom)

$pushUrl = "rtmp://{0}:1935/{1}" -f $ip,$stream
$readUrl = "rtmp://127.0.0.1:1935/{0}" -f $stream
$hlsUrl = "http://127.0.0.1:8888/{0}/index.m3u8" -f $stream
Write-Host ""
Write-Host "CHANDRADEV RTMP RECEIVER"
Write-Host "========================"
Write-Host "DJI Mimo RTMP URL:"
Write-Host $pushUrl
Write-Host ""
Write-Host "Original Osmo Action: choose 720p / 30fps / 4 Mbps for maximum live quality; use 2 Mbps only if unstable."
Write-Host "Local read: $readUrl"
Write-Host "Local HLS : $hlsUrl"
Write-Host ""
Write-Host "Keep this PowerShell window open while streaming."
Write-Host ""

Push-Location $state
try { & $exe $config } finally { Pop-Location }

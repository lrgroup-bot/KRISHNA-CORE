$ErrorActionPreference = "Stop"

$root = if ($env:KRISHNA_ROOT) { $env:KRISHNA_ROOT } else { "E:\Krishna-The GOD" }
$exe = Join-Path $root "tools\mediamtx\mediamtx.exe"
if (-not (Test-Path $exe)) {
    throw "MediaMTX not found. Run scripts\INSTALL_CHANDRADEV_RTMP.ps1 first."
}

$state = Join-Path $root "state\chandradev"
New-Item -ItemType Directory -Force -Path $state | Out-Null

$streamFile = Join-Path $state "stream-name.txt"
if (Test-Path $streamFile) {
    $stream = (Get-Content $streamFile -Raw).Trim()
} else {
    $stream = "osmo-" + ([guid]::NewGuid().ToString("N").Substring(0,12))
    Set-Content -Encoding UTF8 -Path $streamFile -Value $stream
}

$ip = Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.IPAddress -notlike "127.*" -and $_.PrefixOrigin -ne "WellKnown" } |
    Sort-Object InterfaceMetric |
    Select-Object -First 1 -ExpandProperty IPAddress
if (-not $ip) { throw "No LAN IPv4 address found." }

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
$yaml | Set-Content -Encoding UTF8 -Path $config

$pushUrl = "rtmp://{0}:1935/{1}" -f $ip,$stream
$readUrl = "rtmp://127.0.0.1:1935/{0}" -f $stream
$hlsUrl = "http://127.0.0.1:8888/{0}/index.m3u8" -f $stream
Write-Host ""
Write-Host "CHANDRADEV RTMP RECEIVER"
Write-Host "========================"
Write-Host "DJI Mimo RTMP URL:"
Write-Host $pushUrl
Write-Host ""
Write-Host "Original Osmo Action: choose 720p / 30fps / 2 Mbps first."
Write-Host "Local read: $readUrl"
Write-Host "Local HLS : $hlsUrl"
Write-Host ""
Write-Host "Keep this PowerShell window open while streaming."
Write-Host ""

Push-Location $state
try { & $exe $config } finally { Pop-Location }

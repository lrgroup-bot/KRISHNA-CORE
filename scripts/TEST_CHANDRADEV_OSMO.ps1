$ErrorActionPreference = "Stop"

$root = if ($env:KRISHNA_ROOT) { $env:KRISHNA_ROOT } else { "E:\Krishna-The GOD" }
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$state = Join-Path $root "state\chandradev"
$streamFile = Join-Path $state "stream-name.txt"
$exe = Join-Path $root "tools\mediamtx\mediamtx.exe"

Write-Host ""
Write-Host "CHANDRADEV + DJI OSMO TEST"
Write-Host "=========================="

Write-Host ""
Write-Host "[1] DJI USB presence"
$devices = Get-PnpDevice -PresentOnly | Where-Object {
    $_.FriendlyName -match "DJI|OSMO" -or $_.InstanceId -match "VEN_DJI|PROD_OSMO"
} | Select-Object Status,Class,FriendlyName,InstanceId

if ($devices) {
    $devices | Format-Table -AutoSize
    $storage = $devices | Where-Object { $_.Class -eq "DiskDrive" -or $_.InstanceId -like "USBSTOR*" }
    if ($storage) {
        Write-Host "PASS: DJI Osmo is connected as USB storage/file-transfer."
        Write-Host "INFO: This is not the live-video lane. Live CHANDRADEV uses DJI Mimo -> RTMP."
    }
} else {
    Write-Warning "No DJI/OSMO USB device is currently detected. USB is optional for RTMP live test."
}

Write-Host ""
Write-Host "[2] MediaMTX"
if (-not (Test-Path $exe)) {
    Write-Host "NOT INSTALLED: $exe"
    Write-Host "Run: .\scripts\INSTALL_CHANDRADEV_RTMP.ps1"
    exit 2
}
Write-Host "PASS: $exe"

Write-Host ""
Write-Host "[3] RTMP receiver"
$listen = Get-NetTCPConnection -State Listen -LocalPort 1935 -ErrorAction SilentlyContinue
if (-not $listen) {
    Write-Host "NOT RUNNING: TCP 1935 is not listening."
    Write-Host "Open another PowerShell and run:"
    Write-Host "  .\scripts\START_CHANDRADEV_OSMO.ps1"
    exit 3
}
Write-Host "PASS: TCP 1935 is listening."

if (-not (Test-Path $streamFile)) {
    Write-Host "Stream name file not found: $streamFile"
    Write-Host "Restart .\scripts\START_CHANDRADEV_OSMO.ps1 once."
    exit 4
}
$stream = (Get-Content $streamFile -Raw).Trim()
if (-not $stream) { throw "CHANDRADEV stream name is empty." }

$rtmp = "rtmp://127.0.0.1:1935/$stream"
Write-Host "Local RTMP: $rtmp"

Write-Host ""
Write-Host "[4] KRISHNA Python + OpenCV"
$candidates = @()
if ($env:KRISHNA_PYTHON) { $candidates += $env:KRISHNA_PYTHON }
$candidates += @(
    (Join-Path $repoRoot ".venv\Scripts\python.exe"),
    (Join-Path $root ".venv\Scripts\python.exe")
)
$python = $null
foreach ($candidate in $candidates) {
    if ($candidate -and (Test-Path $candidate)) { $python = $candidate; break }
}
if (-not $python) {
    Write-Host "KRISHNA Python venv not found."
    exit 5
}

& $python -c "import cv2; print('PASS: OpenCV', cv2.__version__)"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Run: .\scripts\INSTALL_CHANDRADEV_VISION.ps1"
    exit 6
}

Write-Host ""
Write-Host "[5] Capture one real DJI frame"
$outDir = Join-Path $state "test"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$outFile = Join-Path $outDir ("osmo-test-" + (Get-Date -Format "yyyyMMdd-HHmmss") + ".jpg")
$py = @"
import cv2,sys,time
url=r'''$rtmp'''
out=r'''$outFile'''
cap=cv2.VideoCapture()
try:
    if hasattr(cv2,'CAP_PROP_OPEN_TIMEOUT_MSEC'):
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC,6000)
    if hasattr(cv2,'CAP_PROP_READ_TIMEOUT_MSEC'):
        cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC,6000)
    if not cap.open(url):
        print('NO_STREAM: receiver is running but DJI Mimo is not publishing to the expected RTMP URL')
        sys.exit(7)
    ok,frame=cap.read()
    if not ok or frame is None:
        print('NO_FRAME: RTMP connected but no decodable frame arrived')
        sys.exit(8)
    if not cv2.imwrite(out,frame):
        print('WRITE_FAILED')
        sys.exit(9)
    print('PASS: REAL_FRAME',frame.shape[1],frame.shape[0],out)
finally:
    cap.release()
"@
& $python -c $py
$code = $LASTEXITCODE

if ($code -eq 7) {
    Write-Host ""
    Write-Host "Receiver is ready, but DJI Mimo is not streaming yet."
    Write-Host "Use the RTMP URL printed by START_CHANDRADEV_OSMO.ps1 in DJI Mimo -> Live Stream -> RTMP."
    exit 7
}
if ($code -ne 0) { exit $code }

Write-Host ""
Write-Host "CHANDRADEV DJI TEST PASSED"
Write-Host "Captured frame: $outFile"

param(
    [int]$CameraIndex = 0
)

$ErrorActionPreference = "Stop"

$root = if ($env:KRISHNA_ROOT) { $env:KRISHNA_ROOT } else { "E:\Krishna-The GOD" }
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$shared = Join-Path $root "state\chandradev"

Write-Host ""
Write-Host "CHANDRADEV DIRECT USB WEBCAM TEST"
Write-Host "================================"

Write-Host ""
Write-Host "[1] Windows camera devices"
$devices = Get-PnpDevice -PresentOnly | Where-Object {
    $_.Class -in @("Camera","Image")
} | Select-Object Status,Class,FriendlyName,InstanceId

if ($devices) {
    $devices | Format-Table -AutoSize
} else {
    Write-Warning "Windows currently reports no Camera/Image device."
}

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

$env:CHANDRADEV_SHARED_STATE = $shared
$env:CHANDRADEV_WEBCAM_INDEX = "$CameraIndex"

Write-Host ""
Write-Host "[2] OpenCV"
& $python -c "import cv2; print('PASS: OpenCV', cv2.__version__)"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Run: .\scripts\INSTALL_CHANDRADEV_VISION.ps1"
    exit 6
}

Write-Host ""
Write-Host "[3] Direct UVC capture from camera index $CameraIndex"
$py = @"
import json,sys
from pathlib import Path
repo=Path(r'''$repoRoot''')
sys.path.insert(0,str(repo/'core'))
from krishna_core.chandradev_camera import ChandradevOsmoCameraAdapter

adapter=ChandradevOsmoCameraAdapter(
    Path(r'''$root''')/'state'/'chandradev'/'webcam-runtime'
)
selection=adapter.select_camera_source('usb_uvc_webcam',webcam_index=int(r'''$CameraIndex'''))
print('SELECTION',json.dumps(selection,ensure_ascii=False))
print('UVC_PROBE',json.dumps(adapter.probe_uvc_devices(),ensure_ascii=False))
try:
    result=adapter.capture_frame(quality=94,timeout_seconds=8)
except RuntimeError as exc:
    print('NO_USB_WEBCAM:',str(exc))
    raise SystemExit(7)
print(json.dumps(result,ensure_ascii=False,indent=2))
print('')
print('CHANDRADEV USB WEBCAM TEST PASSED')
print('Captured frame:',result['path'])
print('Actual mode:',result.get('actual_mode'))
"@

& $python -c $py
$code = $LASTEXITCODE

if ($code -eq 7) {
    Write-Host ""
    Write-Host "CHANDRADEV COULD NOT OPEN CAMERA INDEX $CameraIndex"
    Write-Host "Close Windows Camera, Teams, Zoom, browsers, or other apps that may be holding the webcam."
    Write-Host "If more than one camera is installed, retry:"
    Write-Host "  .\scripts\TEST_CHANDRADEV_WEBCAM.ps1 -CameraIndex 1"
    Write-Host "  .\scripts\TEST_CHANDRADEV_WEBCAM.ps1 -CameraIndex 2"
    exit 7
}
if ($code -ne 0) { exit $code }

Write-Host ""
Write-Host "Next:"
Write-Host "  .\scripts\TEST_CHANDRADEV_SCREEN.ps1 -CameraIndex $CameraIndex"

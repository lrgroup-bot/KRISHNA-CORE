param(
    [int]$CameraIndex = 0
)

$ErrorActionPreference = "Stop"

$root = if ($env:KRISHNA_ROOT) { $env:KRISHNA_ROOT } else { "E:\Krishna-The GOD" }
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$shared = Join-Path $root "state\chandradev"

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
if (-not $python) { throw "KRISHNA Python venv not found." }

$env:CHANDRADEV_SHARED_STATE = $shared
$env:CHANDRADEV_WEBCAM_INDEX = "$CameraIndex"

$py = @"
import json,sys
from pathlib import Path
repo=Path(r'''$repoRoot''')
sys.path.insert(0,str(repo/'core'))
from krishna_core.chandradev_camera import ChandradevOsmoCameraAdapter

adapter=ChandradevOsmoCameraAdapter(
    Path(r'''$root''')/'state'/'chandradev'/'screen-focus-runtime'
)
adapter.select_camera_source('usb_uvc_webcam',webcam_index=int(r'''$CameraIndex'''))
try:
    result=adapter.focus_screen(burst_frames=15,target_width=1920,timeout_seconds=8)
except RuntimeError as exc:
    message=str(exc)
    if 'USB webcam index' in message:
        print('NO_USB_WEBCAM:',message)
        raise SystemExit(12)
    raise
print(json.dumps(result,ensure_ascii=False,indent=2))
if not result.get('found'):
    raise SystemExit(10)
print('')
print('CHANDRADEV SCREEN FOCUS PASSED')
print('Focused screen:',result['focused_screen_path'])
print('Sharpness:',result['sharpness'])
print('Screen area ratio:',result['screen_area_ratio'])
"@

& $python -c $py
$code = $LASTEXITCODE

if ($code -eq 12) {
    Write-Host ""
    Write-Host "CHANDRADEV USB WEBCAM IS NOT AVAILABLE"
    Write-Host "Connect the webcam directly to the KRISHNA PC and close Camera/Teams/Zoom or any app that may already be using it."
    Write-Host "If Windows has multiple cameras, rerun with -CameraIndex 1, then 2, etc."
    Write-Host "Example: .\scripts\TEST_CHANDRADEV_SCREEN.ps1 -CameraIndex 1"
}
if ($code -eq 10) {
    Write-Host ""
    Write-Host "CHANDRADEV SCREEN ALIGNMENT NEEDS OWNER HELP"
    Write-Host "KRISHNA should connect the owner for a manual camera adjustment."
    Write-Host "Point the USB webcam so the complete monitor and all four screen edges are visible."
    Write-Host "Stabilize the camera/mount, reduce glare, then run this test again."
    Write-Host "After adjustment CHANDRADEV will re-detect, refocus and lock the monitor."
}
exit $code

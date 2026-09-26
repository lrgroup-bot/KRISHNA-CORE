param(
    [Parameter(Mandatory=$false)]
    [string]$Output = ".\dist-external-observers"
)

$ErrorActionPreference = "Stop"
$Repo = Split-Path -Parent $PSScriptRoot
$Core = Join-Path $Repo "core"
$Output = [System.IO.Path]::GetFullPath($Output)
$Build = Join-Path $Output "_build"
$Spec = Join-Path $Output "_spec"

New-Item -ItemType Directory -Force -Path $Output,$Build,$Spec | Out-Null

python -m pip install --upgrade pyinstaller

$SuryaArgs = @(
    "-m","PyInstaller",
    "--noconfirm","--clean","--onefile",
    "--name","Suryadev",
    "--paths",$Core,
    "--distpath",$Output,
    "--workpath",(Join-Path $Build "suryadev"),
    "--specpath",$Spec,
    (Join-Path $Core "suryadev_worker.py")
)
python @SuryaArgs

$ChandraArgs = @(
    "-m","PyInstaller",
    "--noconfirm","--clean","--onefile",
    "--name","Chandradev",
    "--paths",$Core,
    "--distpath",$Output,
    "--workpath",(Join-Path $Build "chandradev"),
    "--specpath",$Spec,
    (Join-Path $Core "chandradev_worker.py")
)
python @ChandraArgs

$Surya = Join-Path $Output "Suryadev.exe"
$Chandra = Join-Path $Output "Chandradev.exe"
if (-not (Test-Path $Surya)) { throw "Suryadev.exe was not built" }
if (-not (Test-Path $Chandra)) { throw "Chandradev.exe was not built" }

& $Surya --probe | Out-File -Encoding UTF8 (Join-Path $Output "Suryadev-probe.json")
& $Chandra --probe | Out-File -Encoding UTF8 (Join-Path $Output "Chandradev-probe.json")

Get-FileHash -Algorithm SHA256 $Surya,$Chandra |
    Select-Object Path,Hash |
    ConvertTo-Json |
    Set-Content -Encoding UTF8 (Join-Path $Output "SHA256.json")

Write-Host "Built and probe-tested:"
Write-Host "  $Surya"
Write-Host "  $Chandra"

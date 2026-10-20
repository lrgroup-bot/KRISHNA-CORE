param(
    [string]$InstallDir = "$env:LOCALAPPDATA\SURYADEV",
    [string]$DataDir = "$env:USERPROFILE\SURYADEV-DATA",
    [string]$Python = "python"
)
$ErrorActionPreference = "Stop"
$source = (Resolve-Path $PSScriptRoot).Path
$destination = [System.IO.Path]::GetFullPath($InstallDir)
if ($destination.TrimEnd('\') -eq $source.TrimEnd('\')) {
    throw "Install destination must differ from source checkout"
}
Write-Host "Validating SURYADEV before copying"
& $Python --version
if ($LASTEXITCODE -ne 0) { throw "Python 3.10+ is required" }
& $Python -m unittest discover -s (Join-Path $source 'tests') -v
if ($LASTEXITCODE -ne 0) { throw "Tests failed; no files installed" }
New-Item -ItemType Directory -Force -Path $destination | Out-Null
$files = @('suryadev.py','suryadev_extras.py','suryadev_evidence.py',
           'suryadev_lock.py','suryadev_media.py','suryadev_discovery.py',
           'suryadev_core_identity.py','suryadev_enroll.py','laptop-preflight.ps1','README.md')
foreach ($name in $files) {
    $from = Join-Path $source $name
    if (-not (Test-Path $from)) { throw "Missing release file: $name" }
    Copy-Item -LiteralPath $from -Destination (Join-Path $destination $name) -Force
}
New-Item -ItemType Directory -Force -Path $DataDir | Out-Null
Write-Host "Installed SURYADEV to $destination"
Write-Host "Persistent data directory: $DataDir"
Write-Host "No services, startup tasks, firewall changes or Core pairing were created."
Write-Host "Next: cd '$destination'; & $Python suryadev.py --data '$DataDir' status"

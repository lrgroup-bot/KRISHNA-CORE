param(
  [string]$RuntimeRoot="E:\Krishna-The GOD"
)
$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

$RuntimeRoot=[IO.Path]::GetFullPath($RuntimeRoot)
if(!$RuntimeRoot.StartsWith("E:\",[StringComparison]::OrdinalIgnoreCase)){throw "KRISHNA runtime must remain on E:"}
$py=Join-Path $RuntimeRoot ".venv\Scripts\python.exe"
if(!(Test-Path $py)){throw "KRISHNA runtime Python not found: $py"}

$cache=Join-Path $RuntimeRoot "cache\pip"
$tmp=Join-Path $RuntimeRoot "cache\gyan-security\temp"
$userbase=Join-Path $RuntimeRoot "python-userbase"
New-Item -ItemType Directory -Force $cache,$tmp,$userbase|Out-Null
$env:PIP_CACHE_DIR=$cache
$env:TEMP=$tmp
$env:TMP=$tmp
$env:PYTHONUSERBASE=$userbase
$env:PYTHONNOUSERSITE="1"

& $py -c "from cryptography.hazmat.primitives.ciphers.aead import AESGCM; print('GYAN_AESGCM_OK')"
if($LASTEXITCODE -ne 0){
  Write-Host "Installing pinned cryptography 50.0.1 into KRISHNA E: virtual environment..." -ForegroundColor Cyan
  & $py -m pip install --disable-pip-version-check "cryptography==50.0.1"
  if($LASTEXITCODE -ne 0){throw "cryptography installation failed"}
}
& $py -c "from cryptography.hazmat.primitives.ciphers.aead import AESGCM; print('GYAN_AESGCM_READY')"
if($LASTEXITCODE -ne 0){throw "Gyan AES-GCM runtime verification failed"}

Write-Host "Gyan envelope encryption dependency is ready in $py" -ForegroundColor Green

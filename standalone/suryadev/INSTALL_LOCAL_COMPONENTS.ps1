param([Parameter(Mandatory=$true)][string]$ComponentDir, [switch]$OCR)
$ErrorActionPreference = 'Stop'
$ComponentDir = [IO.Path]::GetFullPath($ComponentDir)
New-Item -ItemType Directory -Force -Path $ComponentDir | Out-Null
if ($OCR) {
    $Winget = Get-Command winget.exe -ErrorAction SilentlyContinue
    if (-not $Winget) { throw 'Windows App Installer (winget) is needed for automatic Tesseract installation' }
    & $Winget.Source install --id UB-Mannheim.TesseractOCR --exact --source winget --silent --accept-source-agreements --accept-package-agreements --disable-interactivity
    if ($LASTEXITCODE -ne 0) { throw "Tesseract installation failed: $LASTEXITCODE" }
    exit 0
}
$Installer = Join-Path $ComponentDir 'OllamaSetup.exe'
# Fixed official source, HTTPS validation and Authenticode before execution.
# Never evaluate a downloaded PowerShell script or accept a caller URL.
Invoke-WebRequest -Uri 'https://ollama.com/download/OllamaSetup.exe' -OutFile $Installer
$Signature = Get-AuthenticodeSignature -LiteralPath $Installer
if ($Signature.Status -ne 'Valid' -or $Signature.SignerCertificate.Subject -notmatch 'Ollama') {
    throw 'Ollama installer publisher signature could not be verified; nothing executed'
}
$Install = Start-Process -FilePath $Installer -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-') -WindowStyle Hidden -Wait -PassThru
if ($Install.ExitCode -ne 0) { throw "Ollama installer failed: $($Install.ExitCode)" }

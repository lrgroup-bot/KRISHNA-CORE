param(
  [string]$RuntimeRoot="E:\Krishna-The GOD",
  [string]$WakeModel="",
  [string]$IndicSttCommand="",
  [string]$IndicTtsCommand="",
  [ValidateSet("hi,or","en,hi,or")][string]$IndicTtsLanguages="hi,or"
)
$ErrorActionPreference="Stop"
$py=Join-Path $RuntimeRoot ".venv\Scripts\python.exe"
if(!(Test-Path $py)){throw "KRISHNA runtime Python not found: $py"}
Write-Host "KRISHNA LOCAL VOICE SETUP" -ForegroundColor Cyan
Write-Host "Installing only wake-word runtime dependencies into the KRISHNA E: virtualenv." -ForegroundColor DarkGray
& $py -m pip install --disable-pip-version-check openwakeword sounddevice numpy
if($LASTEXITCODE -ne 0){throw "openWakeWord dependency installation failed"}
$envFile=Join-Path $RuntimeRoot "config\voice-runtime.ps1"
New-Item -ItemType Directory -Force (Split-Path $envFile)|Out-Null
$lines=@(
  '# Generated KRISHNA local voice configuration',
  '# Wake word is activation only; device/policy authentication remains authoritative.'
)
if($WakeModel){
  $resolved=(Resolve-Path $WakeModel).Path
  $lines += '$env:KRISHNA_WAKEWORD_MODEL='+("'" + $resolved.Replace("'","''") + "'")
}
if($IndicSttCommand){$lines += '$env:KRISHNA_INDIC_STT_CMD='+("'" + $IndicSttCommand.Replace("'","''") + "'")}
if($IndicTtsCommand){
  $lines += '$env:KRISHNA_INDIC_TTS_CMD='+("'" + $IndicTtsCommand.Replace("'","''") + "'")
  $lines += '$env:KRISHNA_INDIC_TTS_LANGUAGES='+("'" + $IndicTtsLanguages + "'")
}
$lines|Set-Content -Encoding UTF8 $envFile
Write-Host "Voice config: $envFile" -ForegroundColor Green
Write-Host "AI4Bharat workers are never claimed active unless local commands are configured. Default TTS languages are Hindi/Odia; use -IndicTtsLanguages 'en,hi,or' only when an English checkpoint is installed." -ForegroundColor Yellow

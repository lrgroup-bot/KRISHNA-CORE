param(
  [string]$RuntimeRoot="E:\Krishna-The GOD",
  [string]$WakeModel="",
  [string]$WakeCommand="",
  [switch]$InstallEmbeddedWakeDependencies,
  [string]$IndicSttCommand="",
  [string]$IndicTtsCommand="",
  [string]$SanskritTtsCommand="",
  [ValidateSet("hi,or","en,hi,or")][string]$IndicTtsLanguages="hi,or"
)
$ErrorActionPreference="Stop"
$py=Join-Path $RuntimeRoot ".venv\Scripts\python.exe"
if(!(Test-Path $py)){throw "KRISHNA runtime Python not found: $py"}
Write-Host "KRISHNA LOCAL VOICE SETUP" -ForegroundColor Cyan
if($InstallEmbeddedWakeDependencies){
  Write-Warning "Installing wake dependencies into the production KRISHNA venv was explicitly requested. Isolated wake workers are preferred."
  & $py -m pip install --disable-pip-version-check openwakeword sounddevice numpy
  if($LASTEXITCODE -ne 0){throw "openWakeWord dependency installation failed"}
}else{
  Write-Host "Production Core venv left unchanged; use an isolated local wake worker when possible." -ForegroundColor DarkGray
}
$envFile=Join-Path $RuntimeRoot "config\voice-runtime.ps1"
New-Item -ItemType Directory -Force (Split-Path $envFile)|Out-Null

# Merge with the existing generated voice config instead of replacing previously
# configured wake/STT/TTS providers. Parse only simple KRISHNA env assignments;
# never dot-source an existing file during configuration.
$values=[ordered]@{}
$assignmentPattern="^\s*`$env:(KRISHNA_[A-Z0-9_]+)='((?:''|[^'])*)'\s*$"
if(Test-Path -LiteralPath $envFile){
  foreach($line in (Get-Content -LiteralPath $envFile -ErrorAction Stop)){
    if($line -match $assignmentPattern){
      $values[$matches[1]]=$matches[2].Replace("''","'")
    }
  }
}

if($WakeCommand){$values["KRISHNA_WAKEWORD_CMD"]=$WakeCommand}
if($WakeModel){
  $resolved=(Resolve-Path -LiteralPath $WakeModel).Path
  $values["KRISHNA_WAKEWORD_MODEL"]=$resolved
}
if($IndicSttCommand){$values["KRISHNA_INDIC_STT_CMD"]=$IndicSttCommand}
if($IndicTtsCommand){$values["KRISHNA_INDIC_TTS_CMD"]=$IndicTtsCommand}
if($SanskritTtsCommand){$values["KRISHNA_SANSKRIT_TTS_CMD"]=$SanskritTtsCommand}
if($PSBoundParameters.ContainsKey("IndicTtsLanguages")){
  $values["KRISHNA_INDIC_TTS_LANGUAGES"]=$IndicTtsLanguages
}elseif($IndicTtsCommand -and !$values.Contains("KRISHNA_INDIC_TTS_LANGUAGES")){
  $values["KRISHNA_INDIC_TTS_LANGUAGES"]="hi,or"
}

$lines=@(
  '# Generated KRISHNA local voice configuration',
  '# Wake word is activation only; device/policy authentication remains authoritative.'
)
$preferred=@(
  "KRISHNA_WAKEWORD_CMD",
  "KRISHNA_WAKEWORD_MODEL",
  "KRISHNA_WAKEWORD_THRESHOLD",
  "KRISHNA_INDIC_STT_CMD",
  "KRISHNA_INDIC_TTS_CMD",
  "KRISHNA_INDIC_TTS_LANGUAGES",
  "KRISHNA_SANSKRIT_TTS_CMD"
)
$written=New-Object System.Collections.Generic.HashSet[string]
foreach($name in $preferred){
  if($values.Contains($name) -and [string]$values[$name]){
    $escaped=([string]$values[$name]).Replace("'","''")
    $lines += ('$env:'+$name+"='"+$escaped+"'")
    [void]$written.Add($name)
  }
}
foreach($name in ($values.Keys | Sort-Object)){
  if($written.Contains([string]$name)){continue}
  if([string]$values[$name]){
    $escaped=([string]$values[$name]).Replace("'","''")
    $lines += ('$env:'+[string]$name+"='"+$escaped+"'")
  }
}
$lines|Set-Content -Encoding UTF8 $envFile
Write-Host "Voice config: $envFile" -ForegroundColor Green
Write-Host "AI4Bharat workers are never claimed active unless local commands are configured. Default TTS languages are Hindi/Odia; use -IndicTtsLanguages 'en,hi,or' only when an English checkpoint is installed." -ForegroundColor Yellow

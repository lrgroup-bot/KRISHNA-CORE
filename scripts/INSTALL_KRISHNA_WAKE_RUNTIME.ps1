param(
  [string]$RuntimeRoot="E:\Krishna-The GOD",
  [string]$WakeModel="",
  [double]$Threshold=0.65,
  [string]$PythonExe=""
)
$ErrorActionPreference="Stop"

$voiceRoot=Join-Path $RuntimeRoot "voice"
$envRoot=Join-Path $voiceRoot "envs\wake"
$modelRoot=Join-Path $voiceRoot "models\wake"
$worker=Join-Path $RuntimeRoot "scripts\voice\krishna_wake_worker.py"
$setup=Join-Path $RuntimeRoot "scripts\SETUP_KRISHNA_VOICE.ps1"

if(!(Test-Path -LiteralPath $worker)){throw "Wake worker missing from deployed runtime: $worker"}
if(!(Test-Path -LiteralPath $setup)){throw "Voice setup script missing from deployed runtime: $setup"}

New-Item -ItemType Directory -Force $voiceRoot,$modelRoot|Out-Null

# Keep Python caches/downloads on E:.
$env:TEMP=Join-Path $RuntimeRoot "temp"
$env:TMP=$env:TEMP
$env:PIP_CACHE_DIR=Join-Path $RuntimeRoot "pip-cache"
New-Item -ItemType Directory -Force $env:TEMP,$env:PIP_CACHE_DIR|Out-Null

function Resolve-VoicePython {
  param([string]$Requested)
  if($Requested){
    if(!(Test-Path -LiteralPath $Requested)){throw "Requested Python not found: $Requested"}
    return (Resolve-Path -LiteralPath $Requested).Path
  }

  $launcher=Get-Command py.exe -ErrorAction SilentlyContinue
  if($launcher){
    foreach($version in @("3.12","3.11","3.13")){
      try{
        $candidate=(& $launcher.Source ("-"+$version) -c "import sys;print(sys.executable)" 2>$null | Select-Object -First 1)
        if($LASTEXITCODE -eq 0 -and $candidate -and (Test-Path -LiteralPath $candidate.Trim())){
          return $candidate.Trim()
        }
      }catch{}
    }
  }

  $python=Get-Command python.exe -ErrorAction SilentlyContinue
  if($python){return $python.Source}
  throw "No suitable Python was found. Install/use Python 3.11 or 3.12 and rerun with -PythonExe."
}

$basePython=Resolve-VoicePython $PythonExe
Write-Host "VOICE PYTHON: $basePython" -ForegroundColor Cyan

if(!(Test-Path -LiteralPath (Join-Path $envRoot "Scripts\python.exe"))){
  & $basePython -m venv $envRoot
  if($LASTEXITCODE -ne 0){throw "Failed to create isolated wake-word environment"}
}

$wakePy=Join-Path $envRoot "Scripts\python.exe"
if(!(Test-Path -LiteralPath $wakePy)){throw "Wake environment Python missing: $wakePy"}

& $wakePy -m pip install --disable-pip-version-check --upgrade pip
if($LASTEXITCODE -ne 0){throw "Wake environment pip bootstrap failed"}

& $wakePy -m pip install --disable-pip-version-check openwakeword sounddevice numpy
if($LASTEXITCODE -ne 0){throw "Wake environment dependency install failed"}

& $wakePy -c "import openwakeword,sounddevice,numpy;print('KRISHNA_WAKE_DEPS_OK')"
if($LASTEXITCODE -ne 0){throw "Wake dependency import verification failed"}

if(!$WakeModel){
  $candidate=Join-Path $modelRoot "krishna.onnx"
  if(Test-Path -LiteralPath $candidate){$WakeModel=$candidate}
}

if($WakeModel){
  $resolved=(Resolve-Path -LiteralPath $WakeModel).Path
  $cmd='"'+$wakePy+'" "'+$worker+'" --model "'+$resolved+'" --threshold '+$Threshold.ToString([Globalization.CultureInfo]::InvariantCulture)
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $setup -RuntimeRoot $RuntimeRoot -WakeModel $resolved -WakeCommand $cmd
  if($LASTEXITCODE -ne 0){throw "KRISHNA voice configuration failed"}
  Write-Host "ISOLATED WAKE WORKER CONFIGURED" -ForegroundColor Green
  Write-Host "Model: $resolved"
}else{
  Write-Warning "Wake dependencies are installed in isolation, but no custom Krishna model was provided. No wake command was activated."
  Write-Host "Expected model destination: $(Join-Path $modelRoot 'krishna.onnx')" -ForegroundColor Yellow
}

Write-Host "Core venv was not modified: $(Join-Path $RuntimeRoot '.venv')" -ForegroundColor Green

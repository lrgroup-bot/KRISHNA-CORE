param(
  [string]$RuntimeRoot="E:\Krishna-The GOD",
  [string]$ModelId="ai4bharat/indic-conformer-600m-multilingual",
  [switch]$InstallOnly
)
$ErrorActionPreference="Stop"

$voiceRoot=Join-Path $RuntimeRoot "voice"
$envRoot=Join-Path $voiceRoot "envs\indic-stt"
$modelRoot=Join-Path $voiceRoot "models\indicconformer-600m-multilingual"
$worker=Join-Path $RuntimeRoot "scripts\voice\indicconformer_worker.py"
$setup=Join-Path $RuntimeRoot "scripts\SETUP_KRISHNA_VOICE.ps1"

if(!(Test-Path -LiteralPath $worker)){throw "IndicConformer worker missing: $worker"}
if(!(Test-Path -LiteralPath $setup)){throw "Voice setup missing: $setup"}

$env:TEMP=Join-Path $RuntimeRoot "temp"
$env:TMP=$env:TEMP
$env:PIP_CACHE_DIR=Join-Path $RuntimeRoot "pip-cache"
$env:HF_HOME=Join-Path $RuntimeRoot "hf-cache"
$env:HUGGINGFACE_HUB_CACHE=Join-Path $env:HF_HOME "hub"
$env:TRANSFORMERS_CACHE=Join-Path $env:HF_HOME "transformers"
New-Item -ItemType Directory -Force $voiceRoot,$modelRoot,$env:TEMP,$env:PIP_CACHE_DIR,$env:HF_HOME|Out-Null

$pyPath=$null
$launcher=Get-Command py.exe -ErrorAction SilentlyContinue
if($launcher){
  try{
    $candidate=(& $launcher.Source -3.12 -c "import sys;print(sys.executable)" 2>$null | Select-Object -First 1)
    if($LASTEXITCODE -eq 0 -and $candidate -and (Test-Path -LiteralPath $candidate.Trim())){$pyPath=$candidate.Trim()}
  }catch{}
}
if(!$pyPath){throw "Python 3.12 is required for the isolated IndicConformer worker"}

if(!(Test-Path -LiteralPath (Join-Path $envRoot "Scripts\python.exe"))){
  & $pyPath -m venv $envRoot
  if($LASTEXITCODE -ne 0){throw "Failed to create isolated IndicConformer environment"}
}
$sttPy=Join-Path $envRoot "Scripts\python.exe"

& $sttPy -m pip install --disable-pip-version-check --upgrade pip wheel setuptools
if($LASTEXITCODE -ne 0){throw "IndicConformer pip bootstrap failed"}

& $sttPy -m pip install --disable-pip-version-check torch torchaudio transformers huggingface_hub "onnxruntime==1.20.1" "onnx==1.20.1"
if($LASTEXITCODE -ne 0){throw "IndicConformer dependency install failed"}

& $sttPy -c "import torch,torchaudio,transformers,huggingface_hub;print('KRISHNA_INDIC_STT_DEPS_OK')"
if($LASTEXITCODE -ne 0){throw "IndicConformer dependency import verification failed"}

if($InstallOnly){
  Write-Warning "IndicConformer dependencies installed only. Model access/configuration was intentionally skipped."
  exit 0
}

$downloadScript=@'
from huggingface_hub import snapshot_download
import os, sys
repo=sys.argv[1]
target=sys.argv[2]
try:
    snapshot_download(repo_id=repo, local_dir=target, token=os.getenv("HF_TOKEN") or True)
except Exception as exc:
    print(f"KRISHNA_HF_ACCESS_BLOCKED: {type(exc).__name__}: {exc}", file=sys.stderr)
    raise SystemExit(7)
'@
$tmp=Join-Path $RuntimeRoot "temp\krishna-download-indicconformer.py"
$downloadScript|Set-Content -LiteralPath $tmp -Encoding UTF8
& $sttPy $tmp $ModelId $modelRoot
$code=$LASTEXITCODE
Remove-Item -Force $tmp -ErrorAction SilentlyContinue
if($code -eq 7){
  Write-Warning "AI4Bharat IndicConformer is gated. Accept its Hugging Face access terms and authenticate locally, then rerun this installer."
  Write-Host "No STT command was activated; KRISHNA continues to report STT unavailable rather than a false-ready state." -ForegroundColor Yellow
  exit 7
}
if($code -ne 0){throw "IndicConformer model download failed"}

$cmd='"'+$sttPy+'" "'+$worker+'" --audio "{audio}" --language "{language}" --model "'+$modelRoot+'" --decoder ctc'
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $setup -RuntimeRoot $RuntimeRoot -IndicSttCommand $cmd
if($LASTEXITCODE -ne 0){throw "KRISHNA IndicConformer configuration failed"}

Write-Host "KRISHNA HINDI/ODIA STT CONFIGURED IN ISOLATED E: ENV" -ForegroundColor Green
Write-Host "Python: $sttPy"
Write-Host "Model: $modelRoot"
Write-Host "Production Core venv unchanged: $(Join-Path $RuntimeRoot '.venv')" -ForegroundColor Green

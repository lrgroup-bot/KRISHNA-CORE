param(
  [string]$RuntimeRoot="E:\Krishna-The GOD",
  [string]$ModelId="ai4bharat/indic-parler-tts-pretrained",
  [switch]$SkipModelDownload
)
$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

$voiceRoot=Join-Path $RuntimeRoot "voice"
$envRoot=Join-Path $voiceRoot "envs\sanskrit-tts"
$modelRoot=Join-Path $voiceRoot "models\sanskrit-parler"
$hfHome=Join-Path $RuntimeRoot "hf"
$worker=Join-Path $RuntimeRoot "scripts\voice\sanskrit_parler_worker.py"
$setup=Join-Path $RuntimeRoot "scripts\SETUP_KRISHNA_VOICE.ps1"

if(!(Test-Path -LiteralPath $worker)){throw "Sanskrit worker missing: $worker"}
if(!(Test-Path -LiteralPath $setup)){throw "Voice setup missing: $setup"}

$env:TEMP=Join-Path $RuntimeRoot "temp"
$env:TMP=$env:TEMP
$env:PIP_CACHE_DIR=Join-Path $RuntimeRoot "pip-cache"
$env:HF_HOME=$hfHome
$env:HUGGINGFACE_HUB_CACHE=Join-Path $hfHome "hub"
$env:TRANSFORMERS_CACHE=Join-Path $hfHome "transformers"
New-Item -ItemType Directory -Force $voiceRoot,$modelRoot,$hfHome,$env:TEMP,$env:PIP_CACHE_DIR|Out-Null

$pyCmd=$null
foreach($candidate in @(
  @{exe="py.exe";args=@("-3.12")},
  @{exe="py.exe";args=@("-3.11")},
  @{exe=(Join-Path $RuntimeRoot "python-managed\cpython-3.10.11-windows-x86_64-none\python.exe");args=@()}
)){
  try{
    $cmd=Get-Command $candidate.exe -ErrorAction Stop
    & $cmd.Source @($candidate.args) -c "import sys;print(sys.version_info[:2])" | Out-Null
    if($LASTEXITCODE -eq 0){$pyCmd=@($cmd.Source)+@($candidate.args);break}
  }catch{}
}
if(!$pyCmd){throw "No supported Python found for isolated Sanskrit TTS runtime"}

$ttsPy=Join-Path $envRoot "Scripts\python.exe"
if(!(Test-Path -LiteralPath $ttsPy)){
  & $pyCmd[0] @($pyCmd[1..($pyCmd.Count-1)]) -m venv $envRoot
  if($LASTEXITCODE -ne 0){throw "Failed to create Sanskrit TTS environment"}
}

& $ttsPy -m pip install --disable-pip-version-check --upgrade "pip<26" wheel setuptools
if($LASTEXITCODE -ne 0){throw "Sanskrit TTS pip bootstrap failed"}

# Keep the production Core venv untouched. Parler and model dependencies live
# exclusively under voice\envs\sanskrit-tts.
& $ttsPy -m pip install --disable-pip-version-check torch soundfile accelerate transformers huggingface_hub
if($LASTEXITCODE -ne 0){throw "Sanskrit TTS base dependency install failed"}
& $ttsPy -m pip install --disable-pip-version-check "git+https://github.com/huggingface/parler-tts.git"
if($LASTEXITCODE -ne 0){throw "Parler-TTS installation failed"}

if(!$SkipModelDownload){
  Write-Host "Checking/downloading gated AI4Bharat Sanskrit-capable model to E: ..." -ForegroundColor Cyan
  $probe=@'
from huggingface_hub import snapshot_download
import os,sys
model_id=sys.argv[1]
target=sys.argv[2]
try:
    snapshot_download(
        repo_id=model_id,
        local_dir=target,
        token=os.getenv("HF_TOKEN") or None,
    )
except Exception as exc:
    print("KRISHNA_SANSKRIT_MODEL_ACCESS_ERROR="+str(exc))
    raise
'@
  & $ttsPy -c $probe $ModelId $modelRoot
  if($LASTEXITCODE -ne 0){
    Write-Warning "AI4Bharat Indic Parler-TTS is free/Apache-2.0 but Hugging Face requires the account access agreement. Accept the model conditions and authenticate locally; no token should be pasted into chat."
    exit 7
  }
}

$required=@("config.json")
foreach($name in $required){
  if(!(Test-Path -LiteralPath (Join-Path $modelRoot $name))){
    throw "Sanskrit model installation incomplete: missing $name in $modelRoot"
  }
}

& $ttsPy -c "import torch, soundfile, transformers, parler_tts; print('KRISHNA_SANSKRIT_TTS_ENGINE_OK')"
if($LASTEXITCODE -ne 0){throw "Sanskrit TTS engine import failed"}

$cmd='"'+$ttsPy+'" "'+$worker+'" --text "{text}" --output "{output}" --model-root "'+$modelRoot+'"'
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $setup -RuntimeRoot $RuntimeRoot -SanskritTtsCommand $cmd
if($LASTEXITCODE -ne 0){throw "KRISHNA Sanskrit TTS configuration failed"}

Write-Host "KRISHNA SANSKRIT TTS CONFIGURED IN ISOLATED E: ENV" -ForegroundColor Green
Write-Host "Python: $ttsPy"
Write-Host "Model : $modelRoot"
Write-Host "Provider: $ModelId"
Write-Host "Speaker profile: Aryan / calm devotional measured delivery"
Write-Host "GPU policy: CUDA only when >=6GB VRAM; otherwise CPU fallback"
Write-Host "Production Core venv unchanged: $(Join-Path $RuntimeRoot '.venv')" -ForegroundColor Green

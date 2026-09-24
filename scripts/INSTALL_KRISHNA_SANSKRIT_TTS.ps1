param(
  [string]$RuntimeRoot="E:\Krishna-The GOD",
  [string]$BundleRevision="7d5b0b162477e1c2489c72da3ab2e3052c9a59bd",
  [int]$Nfe=12,
  [switch]$SkipBundleDownload
)
$ErrorActionPreference="Stop"

$voiceRoot=Join-Path $RuntimeRoot "voice"
$envRoot=Join-Path $voiceRoot "envs\sanskrit-tts"
$engineRoot=Join-Path $voiceRoot "engines\edge-sanskrit"
$cacheRoot=Join-Path $voiceRoot "cache\huggingface"
$worker=Join-Path $RuntimeRoot "scripts\voice\sanskrit_tts_worker.py"
$setup=Join-Path $RuntimeRoot "scripts\SETUP_KRISHNA_VOICE.ps1"
$managedPy=Join-Path $RuntimeRoot "python-managed\cpython-3.10.11-windows-x86_64-none\python.exe"

if(!(Test-Path -LiteralPath $managedPy)){throw "Managed Python 3.10.11 missing: $managedPy"}
if(!(Test-Path -LiteralPath $worker)){throw "Sanskrit TTS worker missing: $worker"}
if(!(Test-Path -LiteralPath $setup)){throw "Voice setup missing: $setup"}

$env:TEMP=Join-Path $RuntimeRoot "temp"
$env:TMP=$env:TEMP
$env:PIP_CACHE_DIR=Join-Path $RuntimeRoot "pip-cache"
$env:HF_HOME=$cacheRoot
$env:HUGGINGFACE_HUB_CACHE=Join-Path $cacheRoot "hub"
New-Item -ItemType Directory -Force $voiceRoot,$cacheRoot,$env:TEMP,$env:PIP_CACHE_DIR|Out-Null

if(!(Test-Path -LiteralPath (Join-Path $envRoot "Scripts\python.exe"))){
  & $managedPy -m venv $envRoot
  if($LASTEXITCODE -ne 0){throw "Failed to create isolated Sanskrit TTS environment"}
}
$saPy=Join-Path $envRoot "Scripts\python.exe"

& $saPy -m pip install --disable-pip-version-check --upgrade "pip<26" wheel setuptools
if($LASTEXITCODE -ne 0){throw "Sanskrit TTS pip bootstrap failed"}
& $saPy -m pip install --disable-pip-version-check "huggingface_hub[hf_xet]"
if($LASTEXITCODE -ne 0){throw "Hugging Face bundle client install failed"}

if(!$SkipBundleDownload){
  New-Item -ItemType Directory -Force $engineRoot|Out-Null
  $download="from huggingface_hub import snapshot_download; snapshot_download(repo_id='Hari7718/EdgeSanskrit-TTS', revision='$BundleRevision', local_dir=r'$engineRoot'); print('KRISHNA_EDGE_SANSKRIT_BUNDLE_OK')"
  & $saPy -c $download
  if($LASTEXITCODE -ne 0){throw "Pinned EdgeSanskrit offline bundle download failed"}
}

$generator=Join-Path $engineRoot "generate_sanskrit_v2.py"
if(!(Test-Path -LiteralPath $generator)){throw "EdgeSanskrit generator missing after install: $generator"}
foreach($required in @("models\IndicF5\model.safetensors","vagdhenu\src\reference_bank\bank.json","vagdhenu\src\reference_bank\vocab.txt")){
  $path=Join-Path $engineRoot $required
  if(!(Test-Path -LiteralPath $path)){throw "EdgeSanskrit offline bundle incomplete: $path"}
}

& $saPy -m pip install --disable-pip-version-check "torch==2.4.1" "torchaudio==2.4.1" --index-url "https://download.pytorch.org/whl/cpu"
if($LASTEXITCODE -ne 0){throw "CPU PyTorch install failed for Sanskrit TTS"}
& $saPy -m pip install --disable-pip-version-check "git+https://github.com/ai4bharat/IndicF5.git@13f7c4d627cc10111aea8fe9c0039462cacacdc7" "vocos>=0.1.0" "x-transformers>=2.19.7" indic-transliteration librosa soundfile safetensors python-dotenv
if($LASTEXITCODE -ne 0){throw "EdgeSanskrit dependency install failed"}

& $saPy -c "import torch,torchaudio,vocos,soundfile,safetensors; print('KRISHNA_SANSKRIT_TTS_ENGINE_OK')"
if($LASTEXITCODE -ne 0){throw "Sanskrit TTS isolated environment import check failed"}

$nfeBound=[Math]::Max(4,[Math]::Min(32,$Nfe))
$cmd='"'+$saPy+'" "'+$worker+'" --text "{text}" --output "{output}" --meter "{meter}" --engine-root "'+$engineRoot+'" --nfe '+$nfeBound
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $setup -RuntimeRoot $RuntimeRoot -SanskritTtsCommand $cmd
if($LASTEXITCODE -ne 0){throw "KRISHNA Sanskrit TTS configuration failed"}

Write-Host "KRISHNA SANSKRIT TTS CONFIGURED IN ISOLATED E: ENV" -ForegroundColor Green
Write-Host "Provider : EdgeSanskrit-TTS (MIT)"
Write-Host "Revision : $BundleRevision"
Write-Host "Python   : $saPy"
Write-Host "Engine   : $engineRoot"
Write-Host "HF cache : $cacheRoot"
Write-Host "Core venv unchanged: $(Join-Path $RuntimeRoot '.venv')" -ForegroundColor Green

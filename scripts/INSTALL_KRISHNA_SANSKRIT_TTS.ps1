param(
  [string]$RuntimeRoot="E:\Krishna-The GOD",
  [switch]$SkipBundleDownload,
  [switch]$VerifySample
)
$ErrorActionPreference="Stop"

$voiceRoot=Join-Path $RuntimeRoot "voice"
$envRoot=Join-Path $voiceRoot "envs\sanskrit-tts"
$bundleRoot=Join-Path $voiceRoot "models\edge-sanskrit-tts"
$worker=Join-Path $RuntimeRoot "scripts\voice\sanskrit_tts_worker.py"
$setup=Join-Path $RuntimeRoot "scripts\SETUP_KRISHNA_VOICE.ps1"
$managedPy=Join-Path $RuntimeRoot "python-managed\cpython-3.10.11-windows-x86_64-none\python.exe"
$pinnedBundleCommit="7d5b0b162477e1c2489c72da3ab2e3052c9a59bd"
$indicF5Commit="13f7c4d627cc10111aea8fe9c0039462cacacdc7"

if(!(Test-Path -LiteralPath $managedPy)){throw "Managed Python 3.10.11 missing: $managedPy"}
if(!(Test-Path -LiteralPath $worker)){throw "Sanskrit worker missing: $worker"}
if(!(Test-Path -LiteralPath $setup)){throw "Voice setup missing: $setup"}

$env:TEMP=Join-Path $RuntimeRoot "temp"
$env:TMP=$env:TEMP
$env:PIP_CACHE_DIR=Join-Path $RuntimeRoot "pip-cache"
$env:HF_HOME=Join-Path $RuntimeRoot "hf-home"
$env:TORCH_HOME=Join-Path $RuntimeRoot "torch-home"
New-Item -ItemType Directory -Force $voiceRoot,$env:TEMP,$env:PIP_CACHE_DIR,$env:HF_HOME,$env:TORCH_HOME|Out-Null

if(!(Test-Path -LiteralPath (Join-Path $envRoot "Scripts\python.exe"))){
  & $managedPy -m venv $envRoot
  if($LASTEXITCODE -ne 0){throw "Failed to create isolated Sanskrit TTS environment"}
}
$ttsPy=Join-Path $envRoot "Scripts\python.exe"

if(!(Test-Path -LiteralPath $bundleRoot)){
  if($SkipBundleDownload){throw "EdgeSanskrit offline bundle missing and -SkipBundleDownload was requested: $bundleRoot"}
  $git=(Get-Command git.exe -ErrorAction SilentlyContinue)
  if(!$git){throw "git.exe is required to install the free local Sanskrit bundle"}
  & git lfs version
  if($LASTEXITCODE -ne 0){throw "Git LFS is required for the EdgeSanskrit model bundle"}
  New-Item -ItemType Directory -Force (Split-Path $bundleRoot)|Out-Null
  & git clone https://huggingface.co/Hari7718/EdgeSanskrit-TTS $bundleRoot
  if($LASTEXITCODE -ne 0){throw "EdgeSanskrit bundle clone failed"}
}

Push-Location $bundleRoot
try{
  & git rev-parse --is-inside-work-tree
  if($LASTEXITCODE -ne 0){throw "EdgeSanskrit bundle is not a Git checkout"}
  # Pin source revision; model files remain local under E:. If this historical
  # revision is unavailable in a preexisting shallow clone, do not rewrite it.
  & git cat-file -e ($pinnedBundleCommit+"^{commit}") 2>$null
  if($LASTEXITCODE -eq 0){
    & git checkout --detach $pinnedBundleCommit
    if($LASTEXITCODE -ne 0){throw "Could not checkout pinned EdgeSanskrit source revision"}
  }else{
    Write-Warning "Pinned EdgeSanskrit bundle commit is unavailable in this local checkout; leaving the existing local bundle untouched."
  }
  & git lfs pull
  if($LASTEXITCODE -ne 0){throw "EdgeSanskrit LFS model materialization failed"}
}finally{Pop-Location}

$generator=Join-Path $bundleRoot "generate_sanskrit_v2.py"
$required=@(
  $generator,
  (Join-Path $bundleRoot "models\IndicF5\model.safetensors"),
  (Join-Path $bundleRoot "models\vocos"),
  (Join-Path $bundleRoot "vagdhenu\src\reference_bank\bank.json"),
  (Join-Path $bundleRoot "vagdhenu\src\reference_bank\vocab.txt")
)
$missing=@($required|Where-Object {!(Test-Path -LiteralPath $_)})
if($missing.Count){throw ("EdgeSanskrit offline bundle incomplete: "+($missing -join "; "))}

& $ttsPy -m pip install --disable-pip-version-check --upgrade "pip<26" wheel setuptools
if($LASTEXITCODE -ne 0){throw "Sanskrit TTS pip bootstrap failed"}
& $ttsPy -m pip install --disable-pip-version-check ("git+https://github.com/ai4bharat/IndicF5.git@"+$indicF5Commit)
if($LASTEXITCODE -ne 0){throw "Pinned IndicF5 installation failed"}
$requirements=Join-Path $bundleRoot "requirements.txt"
if(Test-Path -LiteralPath $requirements){
  & $ttsPy -m pip install --disable-pip-version-check -r $requirements
  if($LASTEXITCODE -ne 0){throw "EdgeSanskrit requirements installation failed"}
}

$cmd='"'+$ttsPy+'" "'+$worker+'" --text "{text}" --output "{output}" --bundle-root "'+$bundleRoot+'"'
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $setup -RuntimeRoot $RuntimeRoot -SanskritTtsCommand $cmd
if($LASTEXITCODE -ne 0){throw "KRISHNA Sanskrit TTS configuration failed"}

if($VerifySample){
  $sample=Join-Path $voiceRoot "verification\gita-2.47-sanskrit.wav"
  New-Item -ItemType Directory -Force (Split-Path $sample)|Out-Null
  & $ttsPy $worker --text "कर्मण्येवाधिकारस्ते मा फलेषु कदाचन । मा कर्मफलहेतुर्भूर्मा ते सङ्गोऽस्त्वकर्मणि ॥" --output $sample --bundle-root $bundleRoot --meter anushtubh
  if($LASTEXITCODE -ne 0 -or !(Test-Path -LiteralPath $sample)){throw "Sanskrit sample synthesis failed"}
  Write-Host "Generated Sanskrit acceptance sample (pronunciation still requires human/independent review): $sample" -ForegroundColor Yellow
}

Write-Host "KRISHNA SANSKRIT RECITATION WORKER CONFIGURED IN ISOLATED E: ENV" -ForegroundColor Green
Write-Host "Python: $ttsPy"
Write-Host "Bundle: $bundleRoot"
Write-Host "Production Core venv unchanged: $(Join-Path $RuntimeRoot '.venv')" -ForegroundColor Green
Write-Host "No paid fallback. Runtime generation is offline; generated audio is not labelled pronunciation-verified until acceptance testing passes." -ForegroundColor Yellow

param(
  [string]$RuntimeRoot="E:\Krishna-The GOD",
  [ValidateSet("hi","or","hi,or")][string]$Languages="hi,or",
  [switch]$SkipModelDownload
)
$ErrorActionPreference="Stop"

$voiceRoot=Join-Path $RuntimeRoot "voice"
$envRoot=Join-Path $voiceRoot "envs\indic-tts"
$modelRoot=Join-Path $voiceRoot "models\indic-tts"
$downloadRoot=Join-Path $voiceRoot "downloads\indic-tts"
$worker=Join-Path $RuntimeRoot "scripts\voice\indic_tts_worker.py"
$setup=Join-Path $RuntimeRoot "scripts\SETUP_KRISHNA_VOICE.ps1"
$managedPy=Join-Path $RuntimeRoot "python-managed\cpython-3.10.11-windows-x86_64-none\python.exe"

if(!(Test-Path -LiteralPath $managedPy)){throw "Managed Python 3.10.11 missing: $managedPy"}
if(!(Test-Path -LiteralPath $worker)){throw "Indic-TTS worker missing: $worker"}
if(!(Test-Path -LiteralPath $setup)){throw "Voice setup missing: $setup"}

$env:TEMP=Join-Path $RuntimeRoot "temp"
$env:TMP=$env:TEMP
$env:PIP_CACHE_DIR=Join-Path $RuntimeRoot "pip-cache"
New-Item -ItemType Directory -Force $voiceRoot,$modelRoot,$downloadRoot,$env:TEMP,$env:PIP_CACHE_DIR|Out-Null

if(!(Test-Path -LiteralPath (Join-Path $envRoot "Scripts\python.exe"))){
  & $managedPy -m venv $envRoot
  if($LASTEXITCODE -ne 0){throw "Failed to create isolated Indic-TTS environment"}
}
$ttsPy=Join-Path $envRoot "Scripts\python.exe"

& $ttsPy -m pip install --disable-pip-version-check --upgrade "pip<26" wheel setuptools
if($LASTEXITCODE -ne 0){throw "Indic-TTS pip bootstrap failed"}

$ttsCommit="8efcb8adaaf55563538c12e325d073eaf110065d"
$ttsPackage="git+https://github.com/gokulkarthik/TTS.git@$ttsCommit"
& $ttsPy -m pip install --disable-pip-version-check $ttsPackage
if($LASTEXITCODE -ne 0){throw "Pinned AI4Bharat-compatible TTS engine install failed"}

& $ttsPy -c "import TTS; print('KRISHNA_INDIC_TTS_ENGINE_OK')"
if($LASTEXITCODE -ne 0){throw "Indic-TTS engine import failed"}

$requested=@($Languages -split "," | ForEach-Object {$_.Trim()} | Where-Object {$_})
foreach($lang in $requested){
  $target=Join-Path $modelRoot $lang
  $fastpitch=Join-Path $target "fastpitch\best_model.pth"
  $hifigan=Join-Path $target "hifigan\best_model.pth"
  if((Test-Path -LiteralPath $fastpitch) -and (Test-Path -LiteralPath $hifigan)){continue}
  if($SkipModelDownload){continue}

  $zip=Join-Path $downloadRoot ($lang+".zip")
  $url="https://github.com/AI4Bharat/Indic-TTS/releases/download/v1-checkpoints-release/$lang.zip"
  if(!(Test-Path -LiteralPath $zip)){
    Write-Host "Downloading AI4Bharat Indic-TTS $lang checkpoint to E: ..." -ForegroundColor Cyan
    & curl.exe -L --fail --retry 3 --retry-delay 5 -o $zip $url
    if($LASTEXITCODE -ne 0){throw "Indic-TTS checkpoint download failed: $lang"}
  }

  $stage=Join-Path $downloadRoot ("extract-"+$lang)
  Remove-Item -Recurse -Force $stage -ErrorAction SilentlyContinue
  New-Item -ItemType Directory -Force $stage|Out-Null
  Expand-Archive -LiteralPath $zip -DestinationPath $stage -Force

  $candidate=Get-ChildItem -LiteralPath $stage -Directory -Recurse -ErrorAction SilentlyContinue |
    Where-Object {
      (Test-Path -LiteralPath (Join-Path $_.FullName "fastpitch\best_model.pth")) -and
      (Test-Path -LiteralPath (Join-Path $_.FullName "hifigan\best_model.pth"))
    } | Select-Object -First 1
  if(!$candidate){throw "Could not locate extracted Indic-TTS model root for $lang"}

  Remove-Item -Recurse -Force $target -ErrorAction SilentlyContinue
  New-Item -ItemType Directory -Force (Split-Path $target)|Out-Null
  Move-Item -LiteralPath $candidate.FullName -Destination $target
  Remove-Item -Recurse -Force $stage -ErrorAction SilentlyContinue
}

$missing=@()
foreach($lang in $requested){
  foreach($rel in @("fastpitch\best_model.pth","fastpitch\config.json","hifigan\best_model.pth","hifigan\config.json")){
    $p=Join-Path (Join-Path $modelRoot $lang) $rel
    if(!(Test-Path -LiteralPath $p)){$missing+=$p}
  }
}
if($missing.Count){throw ("Indic-TTS model installation incomplete: "+($missing -join "; "))}

$cmd='\"'+$ttsPy+'\" \"'+$worker+'\" --text \"{text}\" --output \"{output}\" --language \"{language}\" --model-root \"'+$modelRoot+'\"'
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $setup -RuntimeRoot $RuntimeRoot -IndicTtsCommand $cmd -IndicTtsLanguages "hi,or"
if($LASTEXITCODE -ne 0){throw "KRISHNA Indic-TTS configuration failed"}

Write-Host "KRISHNA HINDI/ODIA TTS CONFIGURED IN ISOLATED E: ENV" -ForegroundColor Green
Write-Host "Python: $ttsPy"
Write-Host "Models: $modelRoot"
Write-Host "Production Core venv unchanged: $(Join-Path $RuntimeRoot '.venv')" -ForegroundColor Green

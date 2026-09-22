param(
  [string]$RuntimeRoot = "E:\\Krishna-The GOD",
  [string]$TalkingHeadCommit = "eed58d198076a7e1e825f804802921c4d3804d46",
  [string]$HeadAudioCommit = "d3af5f9ff86ab6b2b1913d411a4e1922ec101953",
  [string]$MotionEngineCommit = "bd780a19e10d1cc5736a77946b04e08d658d5bf8",
  [string]$ModelViewerVersion = "4.3.1"
)
$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

$git=(Get-Command git.exe -ErrorAction SilentlyContinue)
$npm=(Get-Command npm.cmd -ErrorAction SilentlyContinue)
if(!$git){throw "git.exe is required to install the KRISHNA avatar engine"}
if(!$npm){throw "npm.cmd is required to install the KRISHNA avatar engine"}

$toolsRoot=Join-Path $RuntimeRoot "tools\avatar-engine-src"
$talkRoot=Join-Path $toolsRoot "TalkingHead"
$headAudioRoot=Join-Path $toolsRoot "HeadAudio"
$motionRoot=Join-Path $toolsRoot "motion-engine"
$mvRoot=Join-Path $toolsRoot "model-viewer-package"
$assetRoot=Join-Path $RuntimeRoot "dashboard\assets\avatar-engine"
$talkAssets=Join-Path $assetRoot "talkinghead"
$headAudioAssets=Join-Path $assetRoot "headaudio"
$motionAssets=Join-Path $assetRoot "motion-engine"
$threeAssets=Join-Path $assetRoot "three"
$mvAssets=Join-Path $assetRoot "model-viewer"
$cacheRoot=Join-Path $RuntimeRoot "cache\npm"
New-Item -ItemType Directory -Force $toolsRoot,$assetRoot,$cacheRoot|Out-Null
$env:npm_config_cache=$cacheRoot

Write-Host "Installing KRISHNA local avatar engine..." -ForegroundColor Cyan
Write-Host "TalkingHead: met4citizen/TalkingHead @ $TalkingHeadCommit"
Write-Host "HeadAudio: met4citizen/HeadAudio @ $HeadAudioCommit"
Write-Host "MotionEngine: lhupyn/motion-engine @ $MotionEngineCommit"
Write-Host "model-viewer: @google/model-viewer@$ModelViewerVersion"

if(!(Test-Path (Join-Path $talkRoot ".git"))){
  if(Test-Path $talkRoot){Remove-Item -Recurse -Force $talkRoot}
  & $git.Source clone --no-tags https://github.com/met4citizen/TalkingHead.git $talkRoot
  if($LASTEXITCODE -ne 0){throw "TalkingHead clone failed"}
}
& $git.Source -C $talkRoot fetch origin $TalkingHeadCommit --depth 1
if($LASTEXITCODE -ne 0){throw "TalkingHead commit fetch failed"}
& $git.Source -C $talkRoot checkout --detach $TalkingHeadCommit
if($LASTEXITCODE -ne 0){throw "TalkingHead checkout failed"}

& $npm.Source --prefix $talkRoot install --ignore-scripts --no-audit --no-fund
if($LASTEXITCODE -ne 0){throw "TalkingHead dependencies install failed"}

function Sync-PinnedRepo([string]$Url,[string]$Target,[string]$Commit){
  if(!(Test-Path (Join-Path $Target ".git"))){
    if(Test-Path $Target){Remove-Item -Recurse -Force $Target}
    & $git.Source clone --no-tags $Url $Target
    if($LASTEXITCODE -ne 0){throw "Clone failed: $Url"}
  }
  & $git.Source -C $Target fetch origin $Commit --depth 1
  if($LASTEXITCODE -ne 0){throw "Pinned commit fetch failed: $Url @ $Commit"}
  & $git.Source -C $Target checkout --detach $Commit
  if($LASTEXITCODE -ne 0){throw "Pinned checkout failed: $Url @ $Commit"}
}

Sync-PinnedRepo "https://github.com/met4citizen/HeadAudio.git" $headAudioRoot $HeadAudioCommit
Sync-PinnedRepo "https://github.com/lhupyn/motion-engine.git" $motionRoot $MotionEngineCommit

if(Test-Path $mvRoot){Remove-Item -Recurse -Force $mvRoot}
New-Item -ItemType Directory -Force $mvRoot|Out-Null
& $npm.Source --prefix $mvRoot install --ignore-scripts --no-audit --no-fund --no-save "@google/model-viewer@$ModelViewerVersion"
if($LASTEXITCODE -ne 0){throw "model-viewer install failed"}

foreach($p in @($talkAssets,$headAudioAssets,$motionAssets,$threeAssets,$mvAssets)){
  if(Test-Path $p){Remove-Item -Recurse -Force $p}
  New-Item -ItemType Directory -Force $p|Out-Null
}

Copy-Item -Recurse -Force (Join-Path $talkRoot "modules\*") $talkAssets
Copy-Item -Recurse -Force (Join-Path $talkRoot "node_modules\three\*") $threeAssets
Copy-Item -Force (Join-Path $talkRoot "LICENSE") (Join-Path $talkAssets "LICENSE-TalkingHead.txt")

Copy-Item -Recurse -Force (Join-Path $headAudioRoot "modules") $headAudioAssets
Copy-Item -Recurse -Force (Join-Path $headAudioRoot "dist") $headAudioAssets
if(Test-Path (Join-Path $headAudioRoot "models")){Copy-Item -Recurse -Force (Join-Path $headAudioRoot "models") $headAudioAssets}
Copy-Item -Force (Join-Path $headAudioRoot "LICENSE") (Join-Path $headAudioAssets "LICENSE-HeadAudio.txt")

Copy-Item -Recurse -Force (Join-Path $motionRoot "src") $motionAssets
Copy-Item -Force (Join-Path $motionRoot "LICENSE") (Join-Path $motionAssets "LICENSE-MotionEngine.txt")

$mvPackage=Join-Path $mvRoot "node_modules\@google\model-viewer"
$mvBundle=Join-Path $mvPackage "dist\model-viewer.min.js"
if(!(Test-Path $mvBundle)){throw "model-viewer bundle missing after npm install"}
Copy-Item -Force $mvBundle (Join-Path $mvAssets "model-viewer.min.js")
if(Test-Path (Join-Path $mvPackage "LICENSE")){
  Copy-Item -Force (Join-Path $mvPackage "LICENSE") (Join-Path $mvAssets "LICENSE-model-viewer.txt")
}
$threeLicense=Join-Path $talkRoot "node_modules\three\LICENSE"
if(Test-Path $threeLicense){Copy-Item -Force $threeLicense (Join-Path $threeAssets "LICENSE-three.txt")}

$required=@(
  (Join-Path $talkAssets "talkinghead.mjs"),
  (Join-Path $talkAssets "dynamicbones.mjs"),
  (Join-Path $talkAssets "retargeter.mjs"),
  (Join-Path $headAudioAssets "dist\headaudio.min.mjs"),
  (Join-Path $headAudioAssets "modules\headworklet.mjs"),
  (Join-Path $motionAssets "src\MotionEngine.js"),
  (Join-Path $motionAssets "src\motions.json"),
  (Join-Path $threeAssets "build\three.module.js"),
  (Join-Path $threeAssets "examples\jsm\loaders\GLTFLoader.js"),
  (Join-Path $mvAssets "model-viewer.min.js")
)
$missing=@($required|Where-Object {!(Test-Path $_)})
if($missing.Count){throw ("Avatar engine install incomplete: "+($missing -join ", "))}

$marker=[ordered]@{
  schema=1
  installed_at=(Get-Date).ToUniversalTime().ToString("o")
  talkinghead_repository="https://github.com/met4citizen/TalkingHead"
  talkinghead_commit=$TalkingHeadCommit
  talkinghead_license="MIT"
  headaudio_repository="https://github.com/met4citizen/HeadAudio"
  headaudio_commit=$HeadAudioCommit
  headaudio_license="MIT"
  motion_engine_repository="https://github.com/lhupyn/motion-engine"
  motion_engine_commit=$MotionEngineCommit
  motion_engine_license="MIT"
  three_license="MIT"
  model_viewer_version=$ModelViewerVersion
  model_viewer_license="Apache-2.0"
  assets=$required
}
$marker|ConvertTo-Json -Depth 5|Set-Content -Encoding UTF8 (Join-Path $assetRoot "INSTALL.json")

Write-Host "KRISHNA avatar engine installed locally." -ForegroundColor Green
Write-Host "Assets: $assetRoot"

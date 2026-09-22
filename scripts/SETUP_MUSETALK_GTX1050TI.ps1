param(
  [string]$RuntimeRoot = "E:\Krishna-The GOD",
  [string]$PythonVersion = "3.10.11",
  [bool]$InstallWeights = $true
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

function Assert-EPath([string]$Path,[string]$Label){
  if([string]::IsNullOrWhiteSpace($Path)){throw "$Label path is empty"}
  $full=[System.IO.Path]::GetFullPath($Path)
  if($full -notmatch '^[Ee]:\\'){
    throw "$Label must stay on E:. Refusing path: $full"
  }
  return $full
}

$RuntimeRoot=Assert-EPath $RuntimeRoot "KRISHNA runtime"

function Assert-EPath([string]$Path,[string]$Label){
  if([string]::IsNullOrWhiteSpace($Path)){throw "$Label path is empty"}
  $full=[System.IO.Path]::GetFullPath($Path)
  if($full -notmatch '^[Ee]:\\'){
    throw "$Label must stay on E:. Refusing path: $full"
  }
  return $full
}
$RuntimeRoot=Assert-EPath $RuntimeRoot "KRISHNA runtime"

$toolRoot = Join-Path $RuntimeRoot "tools\avatar-video\musetalk"
$envRoot = Join-Path $RuntimeRoot "tools\avatar-video\envs\musetalk"
$cacheRoot = Join-Path $RuntimeRoot "cache\avatar-video"
$downloadRoot = Join-Path $cacheRoot "downloads"
$tempRoot = Join-Path $cacheRoot "temp"
$uvRoot = Join-Path $RuntimeRoot "tools\uv-runtime"
$uvBinRoot = Join-Path $uvRoot "bin"
$uvCache = Join-Path $RuntimeRoot "cache\uv-runtime"
$uvPythonRoot = Join-Path $RuntimeRoot "python-managed"
$uvPythonBin = Join-Path $RuntimeRoot "python-bin"
$pipCache = Join-Path $RuntimeRoot "cache\pip"
$hfHome = Join-Path $RuntimeRoot "cache\huggingface"
$torchHome = Join-Path $RuntimeRoot "cache\torch"
$cudaCache = Join-Path $RuntimeRoot "cache\cuda"
$mplCache = Join-Path $RuntimeRoot "cache\matplotlib"
$numbaCache = Join-Path $RuntimeRoot "cache\numba"
$pythonUserBase = Join-Path $RuntimeRoot "python-userbase"
$stateRoot = Join-Path $RuntimeRoot "state\avatar"

New-Item -ItemType Directory -Force -Path $downloadRoot,$tempRoot,$uvBinRoot,$uvCache,$uvPythonRoot,$uvPythonBin,$pipCache,$hfHome,$torchHome,$cudaCache,$mplCache,$numbaCache,$pythonUserBase,$stateRoot | Out-Null

$env:TEMP = $tempRoot
$env:TMP = $tempRoot
$env:UV_CACHE_DIR = $uvCache
$env:UV_PYTHON_INSTALL_DIR = $uvPythonRoot
$env:UV_PYTHON_BIN_DIR = $uvPythonBin
$env:UV_NO_MODIFY_PATH = "1"
$env:PIP_CACHE_DIR = $pipCache
$env:PYTHONUSERBASE = $pythonUserBase
$env:HF_HOME = $hfHome
$env:HF_HUB_CACHE = Join-Path $hfHome "hub"
$env:HUGGINGFACE_HUB_CACHE = $env:HF_HUB_CACHE
$env:HF_ASSETS_CACHE = Join-Path $hfHome "assets"
$env:HF_XET_CACHE = Join-Path $hfHome "xet"
$env:TORCH_HOME = $torchHome
$env:CUDA_CACHE_PATH = $cudaCache
$env:MPLCONFIGDIR = $mplCache
$env:NUMBA_CACHE_DIR = $numbaCache
$env:XDG_CACHE_HOME = Join-Path $RuntimeRoot "cache"
$env:TRANSFORMERS_CACHE = Join-Path $hfHome "transformers"
$env:PYTHONNOUSERSITE = "1"

if(!(Test-Path (Join-Path $toolRoot "scripts\realtime_inference.py"))){
  throw "MuseTalk source is missing. Run INSTALL_VIDEO_AVATAR_ENGINES.ps1 first."
}

function Invoke-Checked([string]$Exe,[string[]]$CommandArgs,[string]$Label){
  Write-Host ""
  Write-Host ("== "+$Label+" ==") -ForegroundColor Cyan
  Write-Host ("Command: "+$Exe+" "+($CommandArgs -join " ")) -ForegroundColor DarkGray
  & $Exe @CommandArgs
  if($LASTEXITCODE -ne 0){throw "$Label failed with exit code $LASTEXITCODE"}
}

function Get-NvidiaProbe {
  $smi=Get-Command nvidia-smi.exe -ErrorAction SilentlyContinue
  if(!$smi){$smi=Get-Command nvidia-smi -ErrorAction SilentlyContinue}
  if(!$smi){throw "nvidia-smi is unavailable"}
  $row=(& $smi.Source --query-gpu=name,memory.total,driver_version --format=csv,noheader,nounits | Select-Object -First 1)
  $parts=$row -split "," | ForEach-Object {$_.Trim()}
  if($parts.Count -lt 3){throw "Could not read NVIDIA GPU information"}
  return [ordered]@{
    name=$parts[0]
    memory_total_mb=[int]$parts[1]
    vram_gb=[math]::Round(([int]$parts[1])/1024,2)
    driver=$parts[2]
  }
}

$gpu=Get-NvidiaProbe
Write-Host ("GPU: "+$gpu.name+" | VRAM: "+$gpu.vram_gb+" GB | Driver: "+$gpu.driver) -ForegroundColor Green
if($gpu.vram_gb -lt 4){
  throw "MuseTalk setup stopped: upstream Windows testing floor is 4 GB VRAM."
}
if($gpu.name -notmatch "NVIDIA"){
  throw "MuseTalk CUDA setup requires an NVIDIA GPU."
}

$ffmpeg=(Get-Command ffmpeg.exe -ErrorAction SilentlyContinue)
if(!$ffmpeg){$ffmpeg=(Get-Command ffmpeg -ErrorAction SilentlyContinue)}
if(!$ffmpeg){throw "FFmpeg is required and was not found."}
$ffmpegBin=Split-Path $ffmpeg.Source -Parent

$uvVersion="0.12.17"
$uvSha256="a252121d5b59398fcb137c6ea448176459a44010f33f67e0072305a637119ca7"
$uvExe=Join-Path $uvBinRoot "uv.exe"
if(!(Test-Path $uvExe)){
  $uvZip=Join-Path $downloadRoot ("uv-"+$uvVersion+"-x86_64-pc-windows-msvc.zip")
  $uvUrl="https://github.com/astral-sh/uv/releases/download/$uvVersion/uv-x86_64-pc-windows-msvc.zip"
  if(!(Test-Path $uvZip)){
    Write-Host "Downloading pinned portable uv $uvVersion to E: ..." -ForegroundColor Cyan
    Invoke-WebRequest -Uri $uvUrl -OutFile $uvZip -UseBasicParsing
  }
  $actualUvHash=(Get-FileHash -Algorithm SHA256 $uvZip).Hash.ToLowerInvariant()
  if($actualUvHash -ne $uvSha256){
    throw "uv archive checksum mismatch. Expected $uvSha256, got $actualUvHash"
  }
  $extract=Join-Path $tempRoot "uv-extract"
  if(Test-Path $extract){Remove-Item -Recurse -Force $extract}
  New-Item -ItemType Directory -Force -Path $extract | Out-Null
  Expand-Archive -Path $uvZip -DestinationPath $extract -Force
  $found=Get-ChildItem $extract -Filter uv.exe -File -Recurse | Select-Object -First 1
  if(!$found){throw "uv.exe was not found after extraction"}
  Copy-Item -Force $found.FullName $uvExe
}
Invoke-Checked -Exe $uvExe -CommandArgs @("self","version") -Label "Verify portable uv"
Invoke-Checked -Exe $uvExe -CommandArgs @("python","install",$PythonVersion) -Label "Install managed Python $PythonVersion on E"

if(!(Test-Path (Join-Path $envRoot "Scripts\python.exe"))){
  Invoke-Checked -Exe $uvExe -CommandArgs @("venv",$envRoot,"--python",$PythonVersion,"--managed-python","--seed") -Label "Create E-drive MuseTalk Python environment"
}
$envPython=Assert-EPath (Join-Path $envRoot "Scripts\python.exe") "MuseTalk Python"
$envPip=Assert-EPath (Join-Path $envRoot "Scripts\pip.exe") "MuseTalk pip"
if(!(Test-Path $envPython)){throw "MuseTalk environment Python missing: $envPython"}
if(!(Test-Path $envPip)){throw "MuseTalk environment pip missing: $envPip"}
$actualVersion=(& $envPython -c "import sys;print(sys.version.split()[0])").Trim()
if($actualVersion -notlike "3.10*"){throw "Expected Python 3.10, found $actualVersion"}

Invoke-Checked $envPython @("-m","pip","install","--upgrade","pip","setuptools","wheel") "Upgrade MuseTalk environment tooling"

Invoke-Checked $envPip @(
  "install",
  "torch==2.0.1",
  "torchvision==0.15.2",
  "torchaudio==2.0.2",
  "--index-url","https://download.pytorch.org/whl/cu118"
) "Install PyTorch 2.0.1 CUDA 11.8"

$probeJson=& $envPython -c @"
import json, torch
d={
  "torch":torch.__version__,
  "cuda_available":torch.cuda.is_available(),
  "cuda_runtime":torch.version.cuda,
  "arch_list":torch.cuda.get_arch_list() if torch.cuda.is_available() else [],
}
if torch.cuda.is_available():
 d.update({
   "device":torch.cuda.get_device_name(0),
   "capability":"%d.%d"%torch.cuda.get_device_capability(0),
   "memory_gb":round(torch.cuda.get_device_properties(0).total_memory/1024**3,2),
 })
print(json.dumps(d))
"@
if($LASTEXITCODE -ne 0){throw "PyTorch CUDA probe failed"}
$torchProbe=($probeJson | Select-Object -Last 1 | ConvertFrom-Json)
if(!$torchProbe.cuda_available){
  throw "PyTorch installed, but CUDA is not available. Stopping before the large model downloads."
}
if($torchProbe.device -notmatch "1050 Ti"){
  Write-Warning ("Expected GTX 1050 Ti from preflight, PyTorch reports: "+$torchProbe.device)
}
Write-Host ("PyTorch CUDA READY: "+$torchProbe.device+" | capability "+$torchProbe.capability+" | CUDA "+$torchProbe.cuda_runtime) -ForegroundColor Green

$requirements=Join-Path $toolRoot "requirements.txt"
Invoke-Checked $envPip @("install","-r",$requirements) "Install MuseTalk Python dependencies"

Invoke-Checked $envPip @(
  "install","mmcv==2.0.1",
  "-f","https://download.openmmlab.com/mmcv/dist/cu118/torch2.0/index.html"
) "Install prebuilt MMCV 2.0.1 CUDA 11.8 wheel"
Invoke-Checked $envPip @("install","mmengine","mmdet==3.1.0","mmpose==1.1.0") "Install OpenMMLab MuseTalk dependencies"

$importProbe=& $envPython -c "import torch,cv2,diffusers,transformers,mmcv,mmengine,mmdet,mmpose; print('IMPORT_OK'); print(torch.cuda.get_device_name(0))"
if($LASTEXITCODE -ne 0 -or ($importProbe -notcontains "IMPORT_OK")){
  throw "MuseTalk dependency import verification failed"
}

$models=Assert-EPath (Join-Path $toolRoot "models") "MuseTalk models"
$weightsInstalled=$false
if($InstallWeights){
  Invoke-Checked $envPip @("install","--upgrade","huggingface_hub[hf_xet]") "Install Hugging Face downloader"
  $hf=Join-Path $envRoot "Scripts\hf.exe"
  if(!(Test-Path $hf)){$hf=Join-Path $envRoot "Scripts\huggingface-cli.exe"}
  if(!(Test-Path $hf)){throw "Hugging Face CLI was not installed in the MuseTalk environment"}

  New-Item -ItemType Directory -Force -Path $models | Out-Null
  Push-Location $toolRoot
  try{
    Invoke-Checked $hf @("download","TMElyralab/MuseTalk","--local-dir",$models) "Download MuseTalk 1.5 weights"
    Invoke-Checked $hf @("download","stabilityai/sd-vae-ft-mse","--local-dir",(Join-Path $models "sd-vae"),"--include","config.json","diffusion_pytorch_model.bin") "Download SD VAE"
    Invoke-Checked $hf @("download","openai/whisper-tiny","--local-dir",(Join-Path $models "whisper"),"--include","config.json","pytorch_model.bin","preprocessor_config.json") "Download Whisper Tiny"
    Invoke-Checked $hf @("download","yzd-v/DWPose","--local-dir",(Join-Path $models "dwpose"),"--include","dw-ll_ucoco_384.pth") "Download DWPose"
    Invoke-Checked $hf @("download","ByteDance/LatentSync","--local-dir",(Join-Path $models "syncnet"),"--include","latentsync_syncnet.pt") "Download SyncNet"
    Invoke-Checked $hf @("download","ManyOtherFunctions/face-parse-bisent","--local-dir",(Join-Path $models "face-parse-bisent"),"--include","79999_iter.pth","resnet18-5c106cde.pth") "Download face parsing weights"
  } finally { Pop-Location }

  $required=@(
    (Join-Path $models "musetalkV15\unet.pth"),
    (Join-Path $models "musetalkV15\musetalk.json"),
    (Join-Path $models "sd-vae\diffusion_pytorch_model.bin"),
    (Join-Path $models "whisper\pytorch_model.bin"),
    (Join-Path $models "dwpose\dw-ll_ucoco_384.pth"),
    (Join-Path $models "syncnet\latentsync_syncnet.pt"),
    (Join-Path $models "face-parse-bisent\79999_iter.pth"),
    (Join-Path $models "face-parse-bisent\resnet18-5c106cde.pth")
  )
  $missing=@($required | Where-Object {!(Test-Path $_)})
  if($missing.Count){
    throw ("MuseTalk model download incomplete. Missing: "+($missing -join "; "))
  }
  $weightsInstalled=$true
}

$env:FFMPEG_PATH=$ffmpegBin
Push-Location $toolRoot
try{
  $verify=& $envPython -c "import torch; assert torch.cuda.is_available(); import scripts.realtime_inference as r; print('MUSETALK_RUNTIME_OK')" 2>&1
} finally { Pop-Location }
if($LASTEXITCODE -ne 0 -or (($verify | Out-String) -notmatch "MUSETALK_RUNTIME_OK")){
  Write-Warning "Realtime module import needs follow-up; environment and CUDA install completed. Details follow:"
  $verify | Out-Host
  $runtimeImportOk=$false
}else{
  $runtimeImportOk=$true
}

$controlledPaths=[ordered]@{
  runtime=$RuntimeRoot
  source=$toolRoot
  environment=$envRoot
  uv=$uvRoot
  uv_cache=$uvCache
  managed_python=$uvPythonRoot
  python_bin=$uvPythonBin
  pip_cache=$pipCache
  huggingface=$hfHome
  torch_cache=$torchHome
  cuda_cache=$cudaCache
  matplotlib_cache=$mplCache
  numba_cache=$numbaCache
  python_userbase=$pythonUserBase
  temp=$tempRoot
  models=$models
}
$bad=@()
foreach($kv in $controlledPaths.GetEnumerator()){
  $full=[System.IO.Path]::GetFullPath([string]$kv.Value)
  if($full -notmatch '^[Ee]:\\'){$bad+=($kv.Key+"="+$full)}
}
if($bad.Count){throw ("KRISHNA E-drive storage guard failed: "+($bad -join "; "))}


$report=[ordered]@{
  schema=2
  generated_at=(Get-Date).ToUniversalTime().ToString("o")
  provider="musetalk"
  source_root=$toolRoot
  python_root=$uvPythonRoot
  environment_root=$envRoot
  ffmpeg_bin=$ffmpegBin
  gpu=$gpu
  torch=$torchProbe
  dependencies_import_ok=$true
  realtime_module_import_ok=$runtimeImportOk
  weights_installed=$weightsInstalled
  float16_recommended=$true
  c_drive_guard_passed=$true
  controlled_paths=$controlledPaths
  storage_policy="KRISHNA-controlled Python, environments, caches, models and temp files are E-drive-only"
  hardware_profile="GTX 1050 Ti 4GB - supported as low-memory/slow path; upstream 4GB Windows benchmark used RTX 3050 Ti"
  recommended_launch=("python app.py --use_float16 --ffmpeg_path "+$ffmpegBin)
}
$reportPath=Join-Path $stateRoot "musetalk-runtime.json"
$tmp=$reportPath+".tmp"
$report | ConvertTo-Json -Depth 10 | Set-Content -Encoding UTF8 $tmp
Move-Item -Force $tmp $reportPath

Write-Host ""
Write-Host "=== KRISHNA MUSETALK SETUP COMPLETE ===" -ForegroundColor Green
Write-Host ("Python       : "+$actualVersion+" @ "+$envPython)
Write-Host ("Environment  : "+$envRoot)
Write-Host ("Managed Python: "+$uvPythonRoot)
Write-Host ("Caches        : "+(Join-Path $RuntimeRoot "cache"))
Write-Host ("GPU          : "+$torchProbe.device+" ("+$torchProbe.memory_gb+" GB)")
Write-Host ("PyTorch CUDA : "+$torchProbe.cuda_runtime)
Write-Host ("FFmpeg       : "+$ffmpegBin)
Write-Host ("Weights      : "+$(if($weightsInstalled){"READY"}else{"NOT INSTALLED"}))
Write-Host ("Runtime import: "+$(if($runtimeImportOk){"READY"}else{"NEEDS FOLLOW-UP"}))
Write-Host ("C-drive guard : PASSED for KRISHNA-controlled paths")
Write-Host ("Report       : "+$reportPath)
Write-Host ""
Write-Host "GTX 1050 Ti mode: use fp16 and expect slower-than-real-time generation." -ForegroundColor Yellow

param(
  [string]$RuntimeRoot = "E:\Krishna-The GOD",
  [string]$PythonVersion = "3.10.11",
  [bool]$InstallWeights = $true
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$toolRoot = Join-Path $RuntimeRoot "tools\avatar-video\musetalk"
$envRoot = Join-Path $RuntimeRoot "tools\avatar-video\envs\musetalk"
$pythonRoot = Join-Path $RuntimeRoot "python310"
$cacheRoot = Join-Path $RuntimeRoot "cache\avatar-video"
$downloadRoot = Join-Path $cacheRoot "downloads"
$tempRoot = Join-Path $cacheRoot "temp"
$pipCache = Join-Path $RuntimeRoot "cache\pip"
$hfHome = Join-Path $RuntimeRoot "cache\huggingface"
$torchHome = Join-Path $RuntimeRoot "cache\torch"
$stateRoot = Join-Path $RuntimeRoot "state\avatar"

New-Item -ItemType Directory -Force -Path $downloadRoot,$tempRoot,$pipCache,$hfHome,$torchHome,$stateRoot | Out-Null

$env:TEMP = $tempRoot
$env:TMP = $tempRoot
$env:PIP_CACHE_DIR = $pipCache
$env:HF_HOME = $hfHome
$env:HUGGINGFACE_HUB_CACHE = Join-Path $hfHome "hub"
$env:TORCH_HOME = $torchHome
$env:XDG_CACHE_HOME = Join-Path $RuntimeRoot "cache"
$env:TRANSFORMERS_CACHE = Join-Path $hfHome "transformers"
$env:PYTHONNOUSERSITE = "1"

if(!(Test-Path (Join-Path $toolRoot "scripts\realtime_inference.py"))){
  throw "MuseTalk source is missing. Run INSTALL_VIDEO_AVATAR_ENGINES.ps1 first."
}

function Invoke-Checked([string]$Exe,[string[]]$Args,[string]$Label){
  Write-Host ""
  Write-Host ("== "+$Label+" ==") -ForegroundColor Cyan
  & $Exe @Args
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

$pythonExe=Join-Path $pythonRoot "python.exe"
if(!(Test-Path $pythonExe)){
  $installer=Join-Path $downloadRoot ("python-"+$PythonVersion+"-amd64.exe")
  $url="https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-amd64.exe"
  if(!(Test-Path $installer)){
    Write-Host "Downloading official Python $PythonVersion installer to E: ..." -ForegroundColor Cyan
    Invoke-WebRequest -Uri $url -OutFile $installer -UseBasicParsing
  }

  $sig=Get-AuthenticodeSignature $installer
  if($sig.Status -ne "Valid" -or $sig.SignerCertificate.Subject -notmatch "Python Software Foundation"){
    throw "Python installer signature validation failed. Status=$($sig.Status) Subject=$($sig.SignerCertificate.Subject)"
  }

  $installArgs=@(
    "/quiet",
    "InstallAllUsers=0",
    "TargetDir=$pythonRoot",
    "Include_pip=1",
    "Include_launcher=0",
    "Include_doc=0",
    "Include_test=0",
    "Include_tcltk=0",
    "Include_symbols=0",
    "Include_debug=0",
    "Shortcuts=0",
    "AssociateFiles=0",
    "PrependPath=0"
  )
  Write-Host "Installing Python $PythonVersion under $pythonRoot ..." -ForegroundColor Cyan
  $proc=Start-Process -FilePath $installer -ArgumentList $installArgs -Wait -PassThru
  if($proc.ExitCode -ne 0){throw "Python installer failed with exit code $($proc.ExitCode)"}
}
if(!(Test-Path $pythonExe)){throw "Python 3.10 installation did not create $pythonExe"}

$actualVersion=(& $pythonExe -c "import sys;print(sys.version.split()[0])").Trim()
if($actualVersion -notlike "3.10*"){throw "Expected Python 3.10, found $actualVersion at $pythonExe"}

if(!(Test-Path (Join-Path $envRoot "Scripts\python.exe"))){
  Invoke-Checked $pythonExe @("-m","venv",$envRoot) "Create isolated MuseTalk Python environment"
}
$envPython=Join-Path $envRoot "Scripts\python.exe"
$envPip=Join-Path $envRoot "Scripts\pip.exe"

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

$models=Join-Path $toolRoot "models"
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

$report=[ordered]@{
  schema=1
  generated_at=(Get-Date).ToUniversalTime().ToString("o")
  provider="musetalk"
  source_root=$toolRoot
  python_root=$pythonRoot
  environment_root=$envRoot
  ffmpeg_bin=$ffmpegBin
  gpu=$gpu
  torch=$torchProbe
  dependencies_import_ok=$true
  realtime_module_import_ok=$runtimeImportOk
  weights_installed=$weightsInstalled
  float16_recommended=$true
  hardware_profile="GTX 1050 Ti 4GB - supported as low-memory/slow path; upstream 4GB Windows benchmark used RTX 3050 Ti"
  recommended_launch=("python app.py --use_float16 --ffmpeg_path "+$ffmpegBin)
}
$reportPath=Join-Path $stateRoot "musetalk-runtime.json"
$tmp=$reportPath+".tmp"
$report | ConvertTo-Json -Depth 10 | Set-Content -Encoding UTF8 $tmp
Move-Item -Force $tmp $reportPath

Write-Host ""
Write-Host "=== KRISHNA MUSETALK SETUP COMPLETE ===" -ForegroundColor Green
Write-Host ("Python       : "+$actualVersion+" @ "+$pythonRoot)
Write-Host ("Environment  : "+$envRoot)
Write-Host ("GPU          : "+$torchProbe.device+" ("+$torchProbe.memory_gb+" GB)")
Write-Host ("PyTorch CUDA : "+$torchProbe.cuda_runtime)
Write-Host ("FFmpeg       : "+$ffmpegBin)
Write-Host ("Weights      : "+$(if($weightsInstalled){"READY"}else{"NOT INSTALLED"}))
Write-Host ("Runtime import: "+$(if($runtimeImportOk){"READY"}else{"NEEDS FOLLOW-UP"}))
Write-Host ("Report       : "+$reportPath)
Write-Host ""
Write-Host "GTX 1050 Ti mode: use fp16 and expect slower-than-real-time generation." -ForegroundColor Yellow

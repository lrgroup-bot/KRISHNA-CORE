param(
  [string]$RuntimeRoot = "E:\Krishna-The GOD"
)

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

$toolsRoot=Join-Path $RuntimeRoot "tools\avatar-video"
$stateRoot=Join-Path $RuntimeRoot "state\avatar"
New-Item -ItemType Directory -Force -Path $stateRoot | Out-Null

function Get-CommandPath([string]$Name){
  $cmd=Get-Command $Name -ErrorAction SilentlyContinue
  if($cmd){return $cmd.Source}
  return $null
}

function Test-Python310 {
  $result=[ordered]@{available=$false;launcher=$null;version=$null;path=$null}
  $py=Get-CommandPath "py.exe"
  if($py){
    try{
      $version=(& $py -3.10 -c "import sys;print(sys.version.split()[0]);print(sys.executable)" 2>$null)
      if($LASTEXITCODE -eq 0 -and $version.Count -ge 2){
        $result.available=$true;$result.launcher="$py -3.10";$result.version=$version[0];$result.path=$version[1]
        return $result
      }
    }catch{}
  }
  $managedRoot=Join-Path $RuntimeRoot "python-managed"
  $managed=@()
  if(Test-Path $managedRoot){
    $managed=Get-ChildItem $managedRoot -Filter python.exe -File -Recurse -ErrorAction SilentlyContinue |
      Select-Object -ExpandProperty FullName
  }
  foreach($candidate in @(
    (Join-Path $RuntimeRoot "tools\avatar-video\envs\musetalk\Scripts\python.exe"),
    (Join-Path $RuntimeRoot "python310\python.exe"),
    (Join-Path $RuntimeRoot "tools\python310\python.exe")
  ) + $managed){
    if(!(Test-Path $candidate)){continue}
    try{
      $v=(& $candidate -c "import sys;print(sys.version.split()[0])").Trim()
      if($v -like "3.10*"){
        $result.available=$true;$result.launcher=$candidate;$result.version=$v;$result.path=$candidate
        return $result
      }
    }catch{}
  }
  return $result
}

function Get-GpuAudit {
  $path=Get-CommandPath "nvidia-smi.exe"
  if(!$path){$path=Get-CommandPath "nvidia-smi"}
  $rows=@()
  $cudaVersion=$null
  if($path){
    try{
      $raw=& $path --query-gpu=name,memory.total,memory.free,driver_version --format=csv,noheader,nounits
      foreach($line in @($raw)){
        $parts=$line -split "," | ForEach-Object {$_.Trim()}
        if($parts.Count -ge 4){
          $rows += [ordered]@{
            name=$parts[0]
            memory_total_mb=[int]$parts[1]
            memory_free_mb=[int]$parts[2]
            driver_version=$parts[3]
          }
        }
      }
      $banner=(& $path 2>$null | Out-String)
      if($banner -match "CUDA Version:\s*([0-9\.]+)"){$cudaVersion=$Matches[1]}
    }catch{}
  }
  return [ordered]@{
    nvidia_smi=$path
    available=[bool]($rows.Count)
    cuda_runtime=$cudaVersion
    gpus=$rows
  }
}

$gpu=Get-GpuAudit
$nvcc=Get-CommandPath "nvcc.exe"
if(!$nvcc){$nvcc=Get-CommandPath "nvcc"}
$nvccVersion=$null
if($nvcc){
  try{
    $txt=(& $nvcc --version | Out-String)
    if($txt -match "release\s+([0-9\.]+)"){$nvccVersion=$Matches[1]}
  }catch{}
}

$ffmpeg=Get-CommandPath "ffmpeg.exe"
if(!$ffmpeg){$ffmpeg=Get-CommandPath "ffmpeg"}
$ffmpegVersion=$null
if($ffmpeg){
  try{
    $first=(& $ffmpeg -version 2>$null | Select-Object -First 1)
    $ffmpegVersion=[string]$first
  }catch{}
}

$conda=Get-CommandPath "conda.exe"
if(!$conda){$conda=Get-CommandPath "conda"}
$condaVersion=$null
if($conda){
  try{$condaVersion=((& $conda --version 2>$null) | Out-String).Trim()}catch{}
}

$python310=Test-Python310
$drive=Get-PSDrive -Name E -ErrorAction SilentlyContinue
$freeGb=if($drive){[math]::Round($drive.Free/1GB,2)}else{$null}

$museRoot=Join-Path $toolsRoot "musetalk"
$liveRoot=Join-Path $toolsRoot "liveportrait"
$museInstalled=Test-Path (Join-Path $museRoot "scripts\realtime_inference.py")
$liveInstalled=Test-Path (Join-Path $liveRoot "inference.py")

$museCommit=$null
if(Test-Path (Join-Path $museRoot ".git")){
  try{$museCommit=((& git -C $museRoot rev-parse HEAD) | Out-String).Trim()}catch{}
}
$liveCommit=$null
if(Test-Path (Join-Path $liveRoot ".git")){
  try{$liveCommit=((& git -C $liveRoot rev-parse HEAD) | Out-String).Trim()}catch{}
}

$primaryGpu=if($gpu.gpus.Count){$gpu.gpus[0]}else{$null}
$vramGb=if($primaryGpu){[math]::Round($primaryGpu.memory_total_mb/1024,2)}else{0}

$museReasons=@()
if(!$museInstalled){$museReasons+="MuseTalk source is not installed."}
if(!$gpu.available){$museReasons+="No NVIDIA GPU detected through nvidia-smi."}
elseif($vramGb -lt 4){$museReasons+="VRAM is below the 4 GB configuration explicitly tested upstream."}
if(!$ffmpeg){$museReasons+="FFmpeg is not available on PATH."}
# MuseTalk setup bootstraps a managed Python 3.10 with portable uv under E:, so a
# preinstalled Python/Conda is no longer a blocker.

$liveReasons=@()
if(!$liveInstalled){$liveReasons+="LivePortrait source is not installed."}
if(!$ffmpeg){$liveReasons+="FFmpeg is not available on PATH."}
if(!$python310.available -and !$conda){$liveReasons+="Python 3.10/Conda environment creator is not available."}
if(!$gpu.available){$liveReasons+="No NVIDIA GPU detected for the normal Windows CUDA path."}

$museReady=($museReasons.Count -eq 0)
$liveReady=($liveReasons.Count -eq 0)

$recommended="none"
if($museReady){$recommended="musetalk"}
elseif($liveReady){$recommended="liveportrait"}

$heavyEligibility=[ordered]@{
  echomimic_v3=($gpu.available -and $vramGb -ge 12)
  wan_animate_2=($gpu.available -and $vramGb -ge 24)
  note="Heavy-provider thresholds are KRISHNA routing guardrails, not guarantees of upstream performance."
}

$report=[ordered]@{
  schema=1
  generated_at=(Get-Date).ToUniversalTime().ToString("o")
  runtime_root=$RuntimeRoot
  tools_root=$toolsRoot
  system=[ordered]@{
    os=[System.Environment]::OSVersion.VersionString
    powershell=$PSVersionTable.PSVersion.ToString()
    e_drive_free_gb=$freeGb
  }
  gpu=$gpu
  cuda_toolkit=[ordered]@{nvcc=$nvcc;version=$nvccVersion}
  ffmpeg=[ordered]@{available=[bool]$ffmpeg;path=$ffmpeg;version=$ffmpegVersion}
  conda=[ordered]@{available=[bool]$conda;path=$conda;version=$condaVersion}
  python310=$python310
  providers=[ordered]@{
    musetalk=[ordered]@{
      source_installed=$museInstalled
      root=$museRoot
      commit=$museCommit
      upstream_tested_floor_vram_gb=4
      runtime_bootstrap="portable uv installs managed Python 3.10 under E:\Krishna-The GOD"
      ready_for_runtime_setup=$museReady
      blockers=$museReasons
    }
    liveportrait=[ordered]@{
      source_installed=$liveInstalled
      root=$liveRoot
      commit=$liveCommit
      ready_for_runtime_setup=$liveReady
      blockers=$liveReasons
    }
  }
  heavy_provider_eligibility=$heavyEligibility
  recommended_provider=$recommended
  next_action=if($recommended -eq "none"){"Resolve the listed blockers before downloading model weights."}else{"Run KRISHNA provider runtime setup for "+$recommended+"."}
}

$reportPath=Join-Path $stateRoot "video-avatar-hardware.json"
$tmp=$reportPath+".tmp"
$report | ConvertTo-Json -Depth 10 | Set-Content -Encoding UTF8 $tmp
Move-Item -Force $tmp $reportPath

Write-Host ""
Write-Host "=== KRISHNA VIDEO AVATAR HARDWARE PREFLIGHT ===" -ForegroundColor Cyan
Write-Host ("NVIDIA GPU     : "+$(if($gpu.available){$primaryGpu.name}else{"NOT DETECTED"}))
Write-Host ("VRAM           : "+$(if($gpu.available){$vramGb.ToString()+" GB"}else{"n/a"}))
Write-Host ("CUDA runtime   : "+$(if($gpu.cuda_runtime){$gpu.cuda_runtime}else{"not detected"}))
Write-Host ("CUDA toolkit   : "+$(if($nvccVersion){$nvccVersion}else{"not detected"}))
Write-Host ("FFmpeg         : "+$(if($ffmpeg){"READY"}else{"MISSING"}))
Write-Host ("Python 3.10    : "+$(if($python310.available){"READY "+$python310.version}else{"not installed yet - MuseTalk setup will create it on E:"}))
Write-Host ("Conda          : "+$(if($conda){"READY"}else{"not detected"}))
Write-Host ("E: free space  : "+$(if($null -ne $freeGb){$freeGb.ToString()+" GB"}else{"unknown"}))
Write-Host ("MuseTalk       : "+$(if($museReady){"READY FOR SETUP"}else{"BLOCKED"}))
Write-Host ("LivePortrait   : "+$(if($liveReady){"READY FOR SETUP"}else{"BLOCKED"}))
Write-Host ("Recommended    : "+$recommended.ToUpperInvariant())
Write-Host ("Report         : "+$reportPath)

if(!$museReady -and $museReasons.Count){
  Write-Host ""
  Write-Host "MuseTalk blockers:" -ForegroundColor Yellow
  $museReasons | ForEach-Object {Write-Host (" - "+$_)}
}
if(!$liveReady -and $liveReasons.Count){
  Write-Host ""
  Write-Host "LivePortrait blockers:" -ForegroundColor Yellow
  $liveReasons | ForEach-Object {Write-Host (" - "+$_)}
}

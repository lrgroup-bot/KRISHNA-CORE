param(
  [string]$RuntimeRoot = "E:\Krishna-The GOD",
  [ValidateSet("MuseTalk","LivePortrait","EchoMimicV3","WanAnimate2","All")]
  [string]$Provider = "MuseTalk",
  [switch]$IncludeHeavy,
  [switch]$WithWeights
)

$ErrorActionPreference="Stop"
$toolsRoot=Join-Path $RuntimeRoot "tools\avatar-video"
New-Item -ItemType Directory -Force -Path $toolsRoot | Out-Null

$catalog=@{
  MuseTalk=@{
    Folder="musetalk"
    Repo="https://github.com/TMElyralab/MuseTalk.git"
    Heavy=$false
    Note="MIT; real-time lip-sync path. Windows inference is documented upstream."
  }
  LivePortrait=@{
    Folder="liveportrait"
    Repo="https://github.com/KlingAIResearch/LivePortrait.git"
    Heavy=$false
    Note="MIT code. Bundled InsightFace models have separate non-commercial terms; replace them for fully commercial deployment."
  }
  EchoMimicV3=@{
    Folder="echomimic_v3"
    Repo="https://github.com/antgroup/echomimic_v3.git"
    Heavy=$true
    Note="Apache-2.0; Flash path is a 12 GB+ VRAM-class workload and upstream quick-start is Linux/CUDA focused."
  }
  WanAnimate2=@{
    Folder="wan_animate_2"
    Repo="https://github.com/Wan-Video/Wan-Animate-2.git"
    Heavy=$true
    Note="Apache-2.0; 14B-class cinematic character animation stack."
  }
}

$targets=@()
if($Provider -eq "All"){
  $targets=@("MuseTalk","LivePortrait")
  if($IncludeHeavy){$targets+=@("EchoMimicV3","WanAnimate2")}
}else{
  $targets=@($Provider)
}

if(-not (Get-Command git -ErrorAction SilentlyContinue)){
  throw "git is required to install KRISHNA video-avatar providers."
}

$report=@()
foreach($name in $targets){
  $meta=$catalog[$name]
  if($meta.Heavy -and -not $IncludeHeavy){
    $report+=[pscustomobject]@{provider=$name;status="skipped";path="";note="Heavy provider requires -IncludeHeavy"}
    continue
  }
  $dest=Join-Path $toolsRoot $meta.Folder
  if(Test-Path (Join-Path $dest ".git")){
    Push-Location $dest
    try{
      git fetch --depth 1 origin | Out-Host
      $branch=(git symbolic-ref --short refs/remotes/origin/HEAD 2>$null)
      if($branch){$branch=$branch -replace "^origin/",""}else{$branch="main"}
      git checkout $branch | Out-Host
      git pull --ff-only origin $branch | Out-Host
      $sha=(git rev-parse HEAD).Trim()
    } finally { Pop-Location }
    $status="updated"
  }else{
    if(Test-Path $dest){Remove-Item -Recurse -Force $dest}
    git clone --depth 1 $meta.Repo $dest | Out-Host
    Push-Location $dest
    try{$sha=(git rev-parse HEAD).Trim()}finally{Pop-Location}
    $status="installed-code"
  }
  $report+=[pscustomobject]@{provider=$name;status=$status;path=$dest;commit=$sha;note=$meta.Note}
}

if($WithWeights){
  Write-Warning "Model weights are intentionally NOT auto-downloaded by this script. They are large, provider-specific, and should be installed only after KRISHNA checks GPU VRAM, disk space, license terms, and the exact model variant."
}

$stateRoot=Join-Path $RuntimeRoot "state\avatar"
New-Item -ItemType Directory -Force -Path $stateRoot | Out-Null
$reportPath=Join-Path $stateRoot "video-avatar-install.json"
@{
  generated_at=(Get-Date).ToUniversalTime().ToString("o")
  runtime_root=$RuntimeRoot
  tools_root=$toolsRoot
  free_local_only=$true
  higgsfield_dependency=$false
  weights_auto_downloaded=$false
  providers=$report
} | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 $reportPath

Write-Host ""
Write-Host "KRISHNA VIDEO AVATAR PROVIDER INSTALL COMPLETE"
Write-Host "Root   : $toolsRoot"
Write-Host "Report : $reportPath"
$report | Format-Table -AutoSize

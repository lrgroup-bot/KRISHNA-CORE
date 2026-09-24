param(
  [string]$RuntimeRoot="E:\Krishna-The GOD",
  [string]$SourceRoot="E:\KRISHNA-SOURCE",
  [string]$RuntimeGeneration="",
  [int]$MaxCrashes=5,
  [int]$CrashWindowSeconds=600,
  [switch]$PrivateRemote,
  [string]$TailscaleExe="E:\TailScale\tailscale.exe"
)
$ErrorActionPreference="Stop"
$stateDir=Join-Path $RuntimeRoot "state\guardian"
$logDir=Join-Path $RuntimeRoot "logs"
New-Item -ItemType Directory -Force $stateDir,$logDir|Out-Null
$statePath=Join-Path $stateDir "core-guardian.json"
$pidPath=Join-Path $stateDir "guardian.pid"
$logPath=Join-Path $logDir "core-guardian.jsonl"
$stopPath=Join-Path $stateDir "STOP"
$quarantinePath=Join-Path $stateDir "QUARANTINED"
$coreStdout=Join-Path $logDir "core-runtime.stdout.log"
$coreStderr=Join-Path $logDir "core-runtime.stderr.log"

function Write-GuardianEvent([string]$event,[hashtable]$extra=@{}){
  $row=[ordered]@{time=(Get-Date).ToUniversalTime().ToString("o");event=$event}
  foreach($k in $extra.Keys){$row[$k]=$extra[$k]}
  ($row|ConvertTo-Json -Compress)|Add-Content -Encoding UTF8 $logPath
}
function Save-State([hashtable]$state){
  $tmp=$statePath+".tmp";$state|ConvertTo-Json -Depth 8|Set-Content -Encoding UTF8 $tmp;Move-Item -Force $tmp $statePath
}
function Load-State(){
  if(Test-Path $statePath){try{return (Get-Content -Raw $statePath|ConvertFrom-Json)}catch{}}
  return $null
}

Write-Host "KRISHNA GUARDIAN - crash-loop protected supervisor" -ForegroundColor Cyan
if(Test-Path $quarantinePath){
  Write-Host "Core is quarantined. Remove $quarantinePath after diagnosis to resume." -ForegroundColor Red
  exit 3
}
if(Test-Path $pidPath){
  $existingPid=0
  try{$existingPid=[int](Get-Content -Raw $pidPath).Trim()}catch{$existingPid=0}
  if($existingPid -gt 0 -and $existingPid -ne $PID){
    $existing=$null
    try{$existing=Get-CimInstance Win32_Process -Filter ("ProcessId = "+$existingPid) -ErrorAction Stop}catch{}
    $existingCmd=if($existing){[string]$existing.CommandLine}else{""}
    if($existing -and $existingCmd -like "*KRISHNA_GUARDIAN.ps1*"){
      Write-GuardianEvent "ALREADY_RUNNING" @{guardian_pid=$existingPid}
      Write-Host "KRISHNA Guardian is already running (PID $existingPid)." -ForegroundColor Yellow
      exit 0
    }
    Write-GuardianEvent "STALE_GUARDIAN_PID" @{recorded_pid=$existingPid}
  }
  Remove-Item -Force $pidPath -ErrorAction SilentlyContinue
}
if(!$RuntimeGeneration){$RuntimeGeneration=[guid]::NewGuid().ToString("N")}
$env:KRISHNA_RUNTIME_GENERATION=$RuntimeGeneration
[string]$PID|Set-Content -Encoding ASCII $pidPath
Write-GuardianEvent "GUARDIAN_START" @{guardian_pid=$PID;runtime_generation=$RuntimeGeneration;private_remote=[bool]$PrivateRemote;tailscale_exe=$TailscaleExe}
$crashes=New-Object System.Collections.Generic.List[double]
$restartCount=0

try{
while($true){
  if(Test-Path $stopPath){
    Write-GuardianEvent "STOP_REQUESTED"
    Write-Host "Guardian stop marker detected." -ForegroundColor Yellow
    break
  }
  if(Test-Path $quarantinePath){break}
  $start=[DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
  Write-GuardianEvent "CORE_START" @{restart_count=$restartCount;guardian_pid=$PID}
  $startScript=Join-Path $RuntimeRoot "scripts\START_KRISHNA.ps1"
  if(!(Test-Path $startScript)){throw "START_KRISHNA.ps1 missing: $startScript"}
  # START_KRISHNA.ps1 and RuntimeRoot live under "E:\Krishna-The GOD".
  # Quote every path-bearing argument explicitly; Start-Process otherwise flattens
  # ArgumentList and can split paths containing spaces before PowerShell sees them.
  $coreArgs='-NoProfile -ExecutionPolicy Bypass -File "'+$startScript+'" -KrishnaRoot "'+$RuntimeRoot+'" -SourceRoot "'+$SourceRoot+'"'
  if($PrivateRemote){
    $coreArgs+=' -PrivateRemote'
    if($TailscaleExe){$coreArgs+=' -TailscaleExe "'+$TailscaleExe+'"'}
  }
  $p=Start-Process -FilePath "powershell.exe" -ArgumentList $coreArgs -PassThru -WindowStyle Hidden -RedirectStandardOutput $coreStdout -RedirectStandardError $coreStderr
  Save-State @{status="RUNNING";guardian_pid=$PID;core_pid=$p.Id;runtime_generation=$RuntimeGeneration;restart_count=$restartCount;started=(Get-Date).ToUniversalTime().ToString("o");stdout=$coreStdout;stderr=$coreStderr}
  $p.WaitForExit()
  $end=[DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
  $duration=$end-$start;$code=$p.ExitCode
  Write-GuardianEvent "CORE_EXIT" @{exit_code=$code;duration_seconds=$duration}

  if(Test-Path $stopPath){continue}

  # A long healthy run followed by exit resets crash-loop history.
  if($duration -ge 300){$crashes.Clear();$restartCount=0}
  else{
    $now=[double]$end
    $crashes.Add($now)
    $fresh=@($crashes|Where-Object{($now-$_) -le $CrashWindowSeconds})
    $crashes.Clear();foreach($x in $fresh){$crashes.Add([double]$x)}
    if($crashes.Count -ge $MaxCrashes){
      "KRISHNA CORE QUARANTINED after $($crashes.Count) exits in $CrashWindowSeconds seconds at $((Get-Date).ToString('s'))"|Set-Content -Encoding UTF8 $quarantinePath
      Write-GuardianEvent "CORE_QUARANTINED" @{crashes=$crashes.Count;window_seconds=$CrashWindowSeconds;last_exit_code=$code}
      Save-State @{status="QUARANTINED";restart_count=$restartCount;crashes=@($crashes);last_exit_code=$code;updated=(Get-Date).ToUniversalTime().ToString("o")}
      Write-Host "KRISHNA Core quarantined after repeated crashes. Automatic restarts stopped." -ForegroundColor Red
      exit 3
    }
  }

  $restartCount++
  $delay=[Math]::Min(60,[Math]::Pow(2,[Math]::Min($restartCount-1,6)))
  Save-State @{status="RESTART_BACKOFF";restart_count=$restartCount;crashes=@($crashes);last_exit_code=$code;backoff_seconds=$delay;updated=(Get-Date).ToUniversalTime().ToString("o")}
  Write-GuardianEvent "RESTART_SCHEDULED" @{delay_seconds=$delay;restart_count=$restartCount}
  Start-Sleep -Seconds $delay
}
Save-State @{status="STOPPED";guardian_pid=$PID;restart_count=$restartCount;crashes=@($crashes);updated=(Get-Date).ToUniversalTime().ToString("o")}
}
finally{
  Write-GuardianEvent "GUARDIAN_EXIT" @{guardian_pid=$PID}
  Remove-Item -Force $pidPath -ErrorAction SilentlyContinue
}

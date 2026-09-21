param(
  [string]$RuntimeRoot="E:\Krishna-The GOD",
  [string]$SourceRoot="E:\KRISHNA-SOURCE",
  [int]$MaxCrashes=5,
  [int]$CrashWindowSeconds=600
)
$ErrorActionPreference="Stop"
$stateDir=Join-Path $RuntimeRoot "state\guardian"
$logDir=Join-Path $RuntimeRoot "logs"
New-Item -ItemType Directory -Force $stateDir,$logDir|Out-Null
$statePath=Join-Path $stateDir "core-guardian.json"
$logPath=Join-Path $logDir "core-guardian.jsonl"
$stopPath=Join-Path $stateDir "STOP"
$quarantinePath=Join-Path $stateDir "QUARANTINED"

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
$crashes=New-Object System.Collections.Generic.List[double]
$restartCount=0

while($true){
  if(Test-Path $stopPath){
    Write-GuardianEvent "STOP_REQUESTED"
    Write-Host "Guardian stop marker detected." -ForegroundColor Yellow
    break
  }
  if(Test-Path $quarantinePath){break}
  $start=[DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
  Write-GuardianEvent "CORE_START" @{restart_count=$restartCount}
  $startScript=Join-Path $RuntimeRoot "scripts\START_KRISHNA.ps1"
  if(!(Test-Path $startScript)){throw "START_KRISHNA.ps1 missing: $startScript"}
  $p=Start-Process powershell -ArgumentList @("-NoProfile","-ExecutionPolicy","Bypass","-File",$startScript,"-KrishnaRoot",$RuntimeRoot,"-SourceRoot",$SourceRoot) -PassThru -Wait
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
Save-State @{status="STOPPED";restart_count=$restartCount;crashes=@($crashes);updated=(Get-Date).ToUniversalTime().ToString("o")}

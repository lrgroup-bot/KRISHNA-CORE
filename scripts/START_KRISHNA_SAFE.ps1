param(
    [string]$SourceRoot = "E:\KRISHNA-UI-NEW",
    [string]$RuntimeRoot = "E:\Krishna-The GOD",
    [string]$NodeRoot = "E:\Node.JS",
    [int]$CorePort = 8766,
    [int]$FrontendPort = 5173,
    [switch]$SkipGitPull,
    [switch]$NoBrowser
)

$ErrorActionPreference = 'Stop'

function Write-Step([string]$Message) {
    Write-Host "[KRISHNA] $Message" -ForegroundColor Cyan
}

function Get-KrishnaProcesses {
    param([string[]]$Patterns)
    return @(Get-CimInstance Win32_Process | Where-Object {
        $cmd = [string]$_.CommandLine
        if (-not $cmd) { return $false }
        foreach ($pattern in $Patterns) {
            if ($cmd -like $pattern) { return $true }
        }
        return $false
    })
}

function Stop-KrishnaProcessByCommandLine {
    param([string[]]$Patterns)
    foreach ($proc in (Get-KrishnaProcesses -Patterns $Patterns)) {
        try {
            Write-Step "Stopping stale KRISHNA process $($proc.ProcessId): $($proc.Name)"
            Stop-Process -Id $proc.ProcessId -Force -ErrorAction Stop
        } catch {
            Write-Warning "Could not stop PID $($proc.ProcessId): $($_.Exception.Message)"
        }
    }
}

function Assert-PortFree {
    param([int]$Port, [string]$Purpose)
    $listeners = @(Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)
    if (-not $listeners.Count) { return }
    $details = foreach ($listener in $listeners) {
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$($listener.OwningProcess)" -ErrorAction SilentlyContinue
        "PID $($listener.OwningProcess) $($proc.Name) :: $($proc.CommandLine)"
    }
    throw "$Purpose port $Port is already occupied after KRISHNA cleanup. Refusing to kill an unrelated process. $($details -join ' | ')"
}

function Wait-Http {
    param([string]$Url, [int]$TimeoutSeconds = 25)
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        try {
            $r = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 2
            if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500) { return $true }
        } catch {}
        Start-Sleep -Milliseconds 500
    } while ((Get-Date) -lt $deadline)
    return $false
}

function Assert-JsonEndpoint {
    param([string]$Name, [string]$Url)
    try {
        $null = Invoke-RestMethod -Uri $Url -TimeoutSec 4 -Headers @{ Accept = 'application/json' }
        Write-Host ("PASS  {0,-12} {1}" -f $Name, $Url) -ForegroundColor Green
    } catch {
        Write-Host ("FAIL  {0,-12} {1} :: {2}" -f $Name, $Url, $_.Exception.Message) -ForegroundColor Red
        throw "$Name endpoint failed"
    }
}

function Start-EncodedPowerShell {
    param([string]$Command)
    $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($Command))
    Start-Process powershell.exe -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-EncodedCommand',$encoded -WindowStyle Minimized | Out-Null
}

Write-Step "Validating paths"
$python = Join-Path $RuntimeRoot '.venv\Scripts\python.exe'
$npm = Join-Path $NodeRoot 'npm.cmd'
$spatial = Join-Path $SourceRoot 'app\spatial-ui'
$core = Join-Path $SourceRoot 'core'

foreach ($required in @($SourceRoot, $RuntimeRoot, $python, $npm, $spatial, $core)) {
    if (-not (Test-Path $required)) { throw "Required path not found: $required" }
}

$runtimePattern = $RuntimeRoot.TrimEnd('\')
$sourcePattern = $SourceRoot.TrimEnd('\')
$legacyPatterns = @(
    "*$runtimePattern\guardian\autopilot.py*",
    "*$runtimePattern\agents\autonomous_recovery_loop.py*",
    "*$runtimePattern\agents\astra_worker.py*",
    "*$runtimePattern\mobile\companion\server.py*",
    "*$runtimePattern\scripts\start_free_router.py*",
    "*$runtimePattern\scripts\start-ollama-krishna.cmd*"
)
$activePatterns = @(
    "*$sourcePattern\core*krishna_core.server*",
    "*$sourcePattern\app\spatial-ui*vite*"
)

Write-Step "Stopping only stale KRISHNA UI/Core workers (KUBER and shared Ollama are untouched)"
Stop-KrishnaProcessByCommandLine -Patterns ($legacyPatterns + $activePatterns)
Start-Sleep -Milliseconds 500
Assert-PortFree -Port $CorePort -Purpose 'KRISHNA Core'
Assert-PortFree -Port $FrontendPort -Purpose 'KRISHNA frontend'

if (-not $SkipGitPull) {
    Write-Step "Updating verified UI branch"
    Push-Location $SourceRoot
    try {
        & git fetch origin feature/krishna-universe-ui
        if ($LASTEXITCODE -ne 0) { throw 'git fetch failed' }
        & git merge --ff-only origin/feature/krishna-universe-ui
        if ($LASTEXITCODE -ne 0) { throw 'git fast-forward failed; local changes may need review' }
    } finally {
        Pop-Location
    }
}

Push-Location $SourceRoot
try {
    $head = (& git rev-parse HEAD).Trim()
    Write-Step "Source HEAD $head"
} finally {
    Pop-Location
}

if (-not (Test-Path (Join-Path $spatial 'node_modules\.bin\vite.cmd'))) {
    Write-Step "Frontend dependencies are missing; installing them once"
    Push-Location $spatial
    try {
        & $npm install --no-package-lock --no-audit --no-fund
        if ($LASTEXITCODE -ne 0) { throw 'npm install failed' }
    } finally {
        Pop-Location
    }
}

$logs = Join-Path $RuntimeRoot 'logs\safe-start'
New-Item -ItemType Directory -Force -Path $logs | Out-Null
$coreLog = Join-Path $logs 'core.log'
$uiLog = Join-Path $logs 'frontend.log'

try {
    Write-Step "Starting KRISHNA Core on $CorePort with autonomous background services disabled"
    $coreCommand = @"
`$env:KRISHNA_BACKGROUND_SERVICES_ENABLED='0'
`$env:KRISHNA_RUNTIME_ROOT='$RuntimeRoot'
`$env:KRISHNA_DB='$RuntimeRoot\krishna_core.db'
`$env:PYTHONPATH='$core'
Set-Location '$core'
& '$python' -u -m krishna_core.server *>&1 | Tee-Object -FilePath '$coreLog'
"@
    Start-EncodedPowerShell -Command $coreCommand

    if (-not (Wait-Http -Url "http://127.0.0.1:$CorePort/health" -TimeoutSeconds 30)) {
        throw "KRISHNA Core did not become healthy on port $CorePort. Check $coreLog"
    }
    Write-Step "Core healthy"

    Write-Step "Starting verified spatial frontend on $FrontendPort"
    $uiCommand = @"
Set-Location '$spatial'
& '$npm' run dev -- --host 127.0.0.1 --port $FrontendPort *>&1 | Tee-Object -FilePath '$uiLog'
"@
    Start-EncodedPowerShell -Command $uiCommand

    if (-not (Wait-Http -Url "http://127.0.0.1:$FrontendPort/spatial/" -TimeoutSeconds 30)) {
        throw "KRISHNA frontend did not become reachable on port $FrontendPort. Check $uiLog"
    }
    Write-Step "Frontend reachable"

    Write-Step "Running live acceptance sweep"
    Assert-JsonEndpoint -Name 'health' -Url "http://127.0.0.1:$CorePort/health"
    Assert-JsonEndpoint -Name 'status' -Url "http://127.0.0.1:$CorePort/api/status"
    Assert-JsonEndpoint -Name 'tasks' -Url "http://127.0.0.1:$CorePort/api/tasks?limit=500"
    Assert-JsonEndpoint -Name 'garudanetra' -Url "http://127.0.0.1:$CorePort/api/garudanetra/fabric"
    Assert-JsonEndpoint -Name 'projects' -Url "http://127.0.0.1:$CorePort/api/projects"
    Assert-JsonEndpoint -Name 'chats' -Url "http://127.0.0.1:$CorePort/api/chats"
    Assert-JsonEndpoint -Name 'dashboard' -Url "http://127.0.0.1:$CorePort/api/dashboard"
    Assert-JsonEndpoint -Name 'plugins' -Url "http://127.0.0.1:$CorePort/api/plugins"

    if (-not (Wait-Http -Url "http://127.0.0.1:$FrontendPort/spatial/" -TimeoutSeconds 4)) {
        throw 'Spatial frontend acceptance check failed'
    }
    Write-Host ("PASS  {0,-12} {1}" -f 'frontend', "http://127.0.0.1:$FrontendPort/spatial/") -ForegroundColor Green

    $legacyAlive = @(Get-KrishnaProcesses -Patterns $legacyPatterns)
    if ($legacyAlive.Count) {
        $details = $legacyAlive | ForEach-Object { "PID $($_.ProcessId) $($_.Name)" }
        throw "Legacy KRISHNA workers reappeared: $($details -join ', ')"
    }
    Write-Host 'PASS  legacy       no retired KRISHNA worker is running' -ForegroundColor Green

    $krishnaOllamaLinks = foreach ($conn in @(Get-NetTCPConnection -RemotePort 11434 -State Established -ErrorAction SilentlyContinue)) {
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$($conn.OwningProcess)" -ErrorAction SilentlyContinue
        $cmd = [string]$proc.CommandLine
        if ($cmd -like "*$sourcePattern*" -or $cmd -like "*$runtimePattern*") { $proc }
    }
    if (@($krishnaOllamaLinks).Count) {
        $details = @($krishnaOllamaLinks) | ForEach-Object { "PID $($_.ProcessId) $($_.Name)" }
        throw "KRISHNA unexpectedly connected to Ollama 11434 during idle startup: $($details -join ', ')"
    }
    Write-Host 'PASS  ollama-link  no KRISHNA connection to 11434 while idle' -ForegroundColor Green
} catch {
    Write-Warning "Startup/acceptance failed. Cleaning only KRISHNA processes started from $SourceRoot."
    Stop-KrishnaProcessByCommandLine -Patterns $activePatterns
    throw
}

Write-Host ''
Write-Host '=== KRISHNA SAFE START STATUS ===' -ForegroundColor Green
Write-Host "HEAD:     $head"
Write-Host "Core:     http://127.0.0.1:$CorePort/health"
Write-Host "Frontend: http://127.0.0.1:$FrontendPort/spatial/"
Write-Host "Core log: $coreLog"
Write-Host "UI log:   $uiLog"
Write-Host ''
Write-Host 'Listeners:'
Get-NetTCPConnection -State Listen -LocalPort $CorePort,$FrontendPort -ErrorAction SilentlyContinue |
    Select-Object LocalAddress,LocalPort,OwningProcess

$ollamaListener = @(Get-NetTCPConnection -State Listen -LocalPort 11434 -ErrorAction SilentlyContinue)
if ($ollamaListener.Count) {
    Write-Warning 'A shared Ollama service is already listening on 11434. KRISHNA did not start or stop it.'
    $ollama = Get-Command ollama -ErrorAction SilentlyContinue
    if ($ollama) {
        Write-Host 'Current shared Ollama model state:'
        & $ollama.Source ps
    }
} else {
    Write-Host 'Ollama 11434: OFF (KRISHNA did not start it)' -ForegroundColor Green
}

$nvidia = Get-Command nvidia-smi -ErrorAction SilentlyContinue
if ($nvidia) {
    Write-Host 'GPU idle snapshot:'
    & $nvidia.Source --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader
}

if (-not $NoBrowser) {
    Start-Process "http://127.0.0.1:$FrontendPort/spatial/"
}

Write-Host ''
Write-Host 'KRISHNA is running and the live acceptance sweep passed.' -ForegroundColor Green
Write-Host 'If the browser cached an older UI, press Ctrl+Shift+R once.' -ForegroundColor Yellow

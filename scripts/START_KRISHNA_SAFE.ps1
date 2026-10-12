param(
    [string]$SourceRoot = "E:\KRISHNA-UI-NEW",
    [string]$RuntimeRoot = "E:\Krishna-The GOD",
    [string]$NodeRoot = "E:\Node.JS",
    [int]$CorePort = 8766,
    [int]$FrontendPort = 5173,
    [switch]$SkipGitPull
)

$ErrorActionPreference = 'Stop'

function Write-Step([string]$Message) {
    Write-Host "[KRISHNA] $Message" -ForegroundColor Cyan
}

function Test-TcpListen([int]$Port) {
    return @(Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue).Count -gt 0
}

function Stop-KrishnaProcessByCommandLine {
    param([string[]]$Patterns)
    $targets = Get-CimInstance Win32_Process | Where-Object {
        $cmd = [string]$_.CommandLine
        if (-not $cmd) { return $false }
        foreach ($pattern in $Patterns) {
            if ($cmd -like $pattern) { return $true }
        }
        return $false
    }
    foreach ($proc in $targets) {
        try {
            Write-Step "Stopping stale KRISHNA process $($proc.ProcessId): $($proc.Name)"
            Stop-Process -Id $proc.ProcessId -Force -ErrorAction Stop
        } catch {
            Write-Warning "Could not stop PID $($proc.ProcessId): $($_.Exception.Message)"
        }
    }
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

Write-Step "Validating paths"
$python = Join-Path $RuntimeRoot '.venv\Scripts\python.exe'
$npm = Join-Path $NodeRoot 'npm.cmd'
$spatial = Join-Path $SourceRoot 'app\spatial-ui'
$core = Join-Path $SourceRoot 'core'

foreach ($required in @($SourceRoot, $RuntimeRoot, $python, $npm, $spatial, $core)) {
    if (-not (Test-Path $required)) { throw "Required path not found: $required" }
}

Write-Step "Stopping only stale KRISHNA UI/Core workers (KUBER is untouched)"
Stop-KrishnaProcessByCommandLine -Patterns @(
    '*E:\Krishna-The GOD\guardian\autopilot.py*',
    '*E:\Krishna-The GOD\agents\autonomous_recovery_loop.py*',
    '*E:\Krishna-The GOD\agents\astra_worker.py*',
    '*E:\Krishna-The GOD\mobile\companion\server.py*',
    '*E:\Krishna-The GOD\scripts\start_free_router.py*',
    '*E:\Krishna-The GOD\scripts\start-ollama-krishna.cmd*',
    '*E:\KRISHNA-UI-NEW\core*krishna_core.server*',
    '*E:\KRISHNA-UI-NEW\app\spatial-ui*vite*'
)

Get-Process llama-server,ollama -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

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

$logs = Join-Path $RuntimeRoot 'logs\safe-start'
New-Item -ItemType Directory -Force -Path $logs | Out-Null
$coreLog = Join-Path $logs 'core.log'
$uiLog = Join-Path $logs 'frontend.log'

Write-Step "Starting KRISHNA Core on $CorePort with background services disabled"
$coreCommand = @"
`$env:KRISHNA_BACKGROUND_SERVICES_ENABLED='0'
`$env:KRISHNA_RUNTIME_ROOT='$RuntimeRoot'
`$env:KRISHNA_DB='$RuntimeRoot\krishna_core.db'
`$env:PYTHONPATH='$core'
Set-Location '$core'
& '$python' -u -m krishna_core.server *>&1 | Tee-Object -FilePath '$coreLog'
"@
Start-Process powershell.exe -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-Command',$coreCommand -WindowStyle Minimized | Out-Null

if (-not (Wait-Http -Url "http://127.0.0.1:$CorePort/health" -TimeoutSeconds 30)) {
    throw "KRISHNA Core did not become healthy on port $CorePort. Check $coreLog"
}
Write-Step "Core healthy"

Write-Step "Starting verified spatial frontend on $FrontendPort"
$uiCommand = @"
Set-Location '$spatial'
& '$npm' run dev -- --host 127.0.0.1 --port $FrontendPort *>&1 | Tee-Object -FilePath '$uiLog'
"@
Start-Process powershell.exe -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-Command',$uiCommand -WindowStyle Minimized | Out-Null

if (-not (Wait-Http -Url "http://127.0.0.1:$FrontendPort/spatial/" -TimeoutSeconds 30)) {
    throw "KRISHNA frontend did not become reachable on port $FrontendPort. Check $uiLog"
}

Write-Step "Frontend reachable"
Write-Host ''
Write-Host '=== KRISHNA SAFE START STATUS ===' -ForegroundColor Green
Write-Host "Core:     http://127.0.0.1:$CorePort/health"
Write-Host "Frontend: http://127.0.0.1:$FrontendPort/spatial/"
Write-Host "Core log: $coreLog"
Write-Host "UI log:   $uiLog"
Write-Host ''
Write-Host 'Listeners:'
Get-NetTCPConnection -State Listen -LocalPort $CorePort,$FrontendPort -ErrorAction SilentlyContinue |
    Select-Object LocalAddress,LocalPort,OwningProcess
Write-Host ''
Write-Host 'Ollama/Qwen should remain off:'
Get-NetTCPConnection -State Listen -LocalPort 11434 -ErrorAction SilentlyContinue |
    Select-Object LocalAddress,LocalPort,OwningProcess
Write-Host ''
Write-Host 'Open the frontend URL above and press Ctrl+Shift+R once after updates.' -ForegroundColor Yellow

param(
    [string]$OllamaExe = "ollama"
)

$ErrorActionPreference = "Stop"

$cmd = Get-Command $OllamaExe -ErrorAction SilentlyContinue
if (-not $cmd) {
    Write-Host "Ollama CLI not found; no local Qwen process can be verified."
    exit 0
}

$before = (& $cmd.Source ps | Out-String)
if ($LASTEXITCODE -ne 0) {
    throw "Unable to query Ollama running models."
}

$running = @()
foreach ($line in ($before -split "\r?\n")) {
    $trim = $line.Trim()
    if (-not $trim) { continue }
    $name = ($trim -split "\s+")[0]
    if ($name -match "(?i)^qwen") {
        $running += $name
    }
}
$running = @($running | Sort-Object -Unique)

foreach ($model in $running) {
    Write-Host "Stopping Qwen model: $model"
    & $cmd.Source stop $model
    if ($LASTEXITCODE -ne 0) {
        throw "ollama stop failed for $model"
    }
}

$after = (& $cmd.Source ps | Out-String)
if ($LASTEXITCODE -ne 0) {
    throw "Unable to verify Ollama after stopping Qwen."
}
if ($after -match "(?im)^\s*qwen") {
    throw "Qwen is still running after stop attempts."
}

Write-Host "QWEN STOPPED: no running Qwen model remains. Installed model files were not deleted."

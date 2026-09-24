param(
    [string]$Model = "qwen3.5:4b",
    [string]$OllamaExe = "ollama",
    [switch]$Pull
)

$ErrorActionPreference = "Stop"

# Owner policy:
# - Qwen is permitted on the KRISHNA PC as an explicit local opt-in model.
# - Qwen is not a KRISHNA Mobile inference dependency.
# - Canonical deployment never pulls, starts, stops or deletes Qwen automatically.
$cmd = Get-Command $OllamaExe -ErrorAction SilentlyContinue
if (-not $cmd) {
    throw "Ollama CLI not found. PC Qwen cannot be inspected or installed."
}

if (-not $Pull) {
    Write-Host "PC-only Qwen is permitted. No download was requested; leaving Ollama models unchanged."
    Write-Host "To explicitly install a PC model, rerun with -Pull [-Model <ollama-model>]."
    exit 0
}

if ([string]::IsNullOrWhiteSpace($Model) -or $Model -notmatch "(?i)^qwen") {
    throw "This helper accepts only an explicit Qwen model name."
}

Write-Host "Explicit PC-only Qwen install requested: $Model"
& $cmd.Source pull $Model
if ($LASTEXITCODE -ne 0) {
    throw "ollama pull failed for $Model"
}
Write-Host "PC Qwen installed: $Model. KRISHNA Mobile remains Qwen-free."

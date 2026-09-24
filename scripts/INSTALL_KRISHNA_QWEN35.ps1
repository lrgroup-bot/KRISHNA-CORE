param(
    [string]$Model = "qwen3.5:4b",
    [string]$OllamaExe = "ollama",
    [switch]$Pull
)

$ErrorActionPreference = "Stop"

# Owner policy:
# - Qwen is role-assigned on the KRISHNA PC by owner policy.
# - Qwen is not a KRISHNA Mobile inference dependency.
# - Canonical deployment never downloads or deletes models automatically; this helper pulls only when explicitly requested.
$cmd = Get-Command $OllamaExe -ErrorAction SilentlyContinue
if (-not $cmd) {
    throw "Ollama CLI not found. PC Qwen cannot be inspected or installed."
}

if (-not $Pull) {
    Write-Host "KRISHNA PC Qwen role policy is enabled. No download was requested; leaving Ollama models unchanged."
    Write-Host "To install a missing PC Qwen model, rerun with -Pull [-Model <ollama-model>]."
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

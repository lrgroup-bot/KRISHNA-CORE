param(
    [string]$ModelRoot = "E:\\Krishna-The GOD\\ollama-models",
    [string]$PrimaryModel = "qwen3.5:4b",
    [switch]$SkipPull
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    throw "Ollama is not installed or is not available in PATH."
}

New-Item -ItemType Directory -Force -Path $ModelRoot | Out-Null
$env:OLLAMA_MODELS = $ModelRoot
$env:KRISHNA_LOCAL_MODEL = $PrimaryModel
$env:KRISHNA_LOCAL_FALLBACK_MODELS = "qwen2.5:3b,qwen2.5vl:7b"
$env:KRISHNA_OLLAMA_MODEL = $PrimaryModel
$env:KRISHNA_OLLAMA_FALLBACK_MODELS = "qwen2.5:3b,qwen2.5vl:7b"
$env:KRISHNA_VISION_MODEL = "qwen2.5vl:7b"
$env:KRISHNA_VISION_FALLBACK_MODELS = $PrimaryModel
$env:KRISHNA_FAST_VISION_MODEL = $PrimaryModel
$env:KRISHNA_FAST_VISION_FALLBACK_MODELS = "qwen2.5vl:7b"

if (-not $SkipPull) {
    Write-Host "Pulling $PrimaryModel into $ModelRoot ..."
    & ollama pull $PrimaryModel
    if ($LASTEXITCODE -ne 0) {
        throw "ollama pull failed for $PrimaryModel"
    }
}

$list = (& ollama list | Out-String)
if ($LASTEXITCODE -ne 0) {
    throw "ollama list failed"
}
if ($list -notmatch [regex]::Escape($PrimaryModel)) {
    throw "$PrimaryModel is not visible in Ollama."
}

$payload = @{
    model  = $PrimaryModel
    prompt = "Reply with exactly KRISHNA_QWEN_OK"
    stream = $false
} | ConvertTo-Json

try {
    $result = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/generate" -Method Post -ContentType "application/json" -Body $payload
} catch {
    throw "Qwen verification request failed: $($_.Exception.Message)"
}

if ([string]::IsNullOrWhiteSpace([string]$result.response)) {
    throw "$PrimaryModel returned an empty verification response."
}

Write-Host ""
Write-Host "=== KRISHNA QWEN PRIMARY VERIFIED ==="
Write-Host "Primary: $PrimaryModel"
Write-Host "Model root: $ModelRoot"
Write-Host "Text fallback: qwen2.5:3b"
Write-Host "Detailed vision primary: qwen2.5vl:7b"
Write-Host "Detailed vision fallback: $PrimaryModel"
Write-Host "Fast/live vision primary: $PrimaryModel"
Write-Host "Fast/live vision fallback: qwen2.5vl:7b"
Write-Host "Old Qwen models were NOT deleted."
Write-Host "Response: $($result.response)"

# Start a new SURYADEV learning ledger without deleting earlier learning evidence.
# The original data root is NEVER modified: a sibling fresh data root is used.
param(
    [string]$PreviousDataDir = "D:\Work\SURYADEV-UNIFIED-TEST-DATA",
    [string]$FreshDataDir = "",
    [int]$Port = 8772,
    [string]$Python = "python",
    [string]$Model = "qwen3.5:2b",
    [switch]$NewSession
)
$ErrorActionPreference = "Stop"
if ($Model -notin @("qwen3.5:2b","qwen3.5:4b","qwen3.5:9b","gemma3:4b")) {
    throw "Use a supported locally installed Ollama model."
}
if ($Port -lt 1024 -or $Port -gt 65535) { throw "Choose a dashboard port from 1024 to 65535" }
$previous = [System.IO.Path]::GetFullPath($PreviousDataDir).TrimEnd('\')
if (-not $FreshDataDir) { $FreshDataDir = $previous + "-FRESH" }
if ($NewSession) { $FreshDataDir += "-" + (Get-Date -Format "yyyyMMdd-HHmmss") }
$fresh = [System.IO.Path]::GetFullPath($FreshDataDir).TrimEnd('\')
if ($fresh.Equals($previous, [System.StringComparison]::OrdinalIgnoreCase) -or
    $fresh.StartsWith($previous + "\", [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Fresh data must be a different folder outside the previous learning data root."
}
if (-not (Test-Path -LiteralPath $previous -PathType Container)) {
    throw "Existing learning directory not found: $previous. Check your earlier path."
}
# Never take over an already-running dashboard or an old worker.
$listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($listener) {
    throw "Dashboard port $Port is in use. Stop the old dashboard gracefully first."
}
if (-not (Test-Path -LiteralPath $fresh -PathType Container)) {
    New-Item -ItemType Directory -Path $fresh -Force | Out-Null
}
$marker = Join-Path $fresh "fresh-workspace.json"
if (Test-Path -LiteralPath $marker -PathType Leaf) {
    $existing = Get-Content -LiteralPath $marker -Raw | ConvertFrom-Json
    if ($existing.schema -ne "suryadev.fresh-workspace.v1") {
        throw "Existing workspace marker is invalid; refusing to alter its contents."
    }
    # Reopening the same study ledger must never restore the old 9B default.
    # Update only the model preference; retain every existing learning receipt.
    if ($existing.trial_model -ne $Model) {
        $existing | Add-Member -NotePropertyName trial_model -NotePropertyValue $Model -Force
        $stage = Join-Path $fresh (".fresh-workspace-model-" + [guid]::NewGuid().ToString("N") + ".tmp")
        try {
            $json = $existing | ConvertTo-Json -Depth 8
            [System.IO.File]::WriteAllText($stage, $json + [Environment]::NewLine,
                ([System.Text.UTF8Encoding]::new($false)))
            Move-Item -LiteralPath $stage -Destination $marker -Force
        } finally {
            if (Test-Path -LiteralPath $stage) { [System.IO.File]::Delete($stage) }
        }
        Write-Host "Updated existing fresh workspace model to $Model (study data retained)"
    }
    Write-Host "Reopening existing fresh workspace with its retained checkpoints: $fresh"
} else {
    $unexpected = @(Get-ChildItem -LiteralPath $fresh -Force -ErrorAction Stop)
    if ($unexpected.Count -ne 0) {
        throw "Fresh directory already contains unrecognized files. Use -NewSession or a different path."
    }
    $record = @{
        schema = "suryadev.fresh-workspace.v1"
        created_at = (Get-Date).ToUniversalTime().ToString("o")
        active_task_limit = 3
        auto_start = $true
        trial_model = $Model
        previous_learning_preserved_at = $previous
        note = "New independent databases; previous evidence was not deleted or copied."
    }
    # PowerShell 5.1 writes a BOM with -Encoding UTF8; Python's utf-8 JSON reader
    # will reject it. Always store the marker in UTF-8 without a BOM.
    $json = $record | ConvertTo-Json -Depth 3
    [System.IO.File]::WriteAllText($marker, $json + [Environment]::NewLine,
        ([System.Text.UTF8Encoding]::new($false)))
}
$env:SURYADEV_MAX_PARALLEL = "3"
$env:SURYADEV_LEARNING_TRIAL = "1"
Write-Host "SURYADEV CLEAN WORKSPACE: $fresh"
Write-Host "Previous learning safely retained: $previous"
Write-Host "Maximum three simultaneous tasks across websites, PDFs, YouTube and books; 85% guard takes priority."
Write-Host "The fixed owner-approved video/book trial is seeded only when the worker actually starts."
Write-Host "KRISHNA pairing is NOT copied or invented; a separately authenticated Core connection is required."
Set-Location -LiteralPath $PSScriptRoot
& $Python (Join-Path $PSScriptRoot "suryadev_extras.py") --data $fresh dashboard --port $Port
if ($LASTEXITCODE -ne 0) { throw "Fresh SURYADEV dashboard exited unsuccessfully." }

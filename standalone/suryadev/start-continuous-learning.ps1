param(
    [string]$DataDir = (Join-Path $env:USERPROFILE "SURYADEV-DATA"),
    [int]$RefillMinutes = 5,
    [int]$CheckSeconds = 10,
    [string]$Python = "python",
    [switch]$ActivateOfficialTech,
    [switch]$UseOllama,
    [switch]$DeepWeb,
    [switch]$DeepPDF,
    [switch]$AnalyzeYoutubeComments,
    [string]$VisionModel = "",
    [string]$CoreMissionConfig = "",
    [string]$Model = "qwen3.5:9b"
)
$ErrorActionPreference = "Stop"
if ($RefillMinutes -lt 1 -or $RefillMinutes -gt 360) {
    throw "RefillMinutes must be 1..360"
}
if ($CheckSeconds -lt 10 -or $CheckSeconds -gt 3600) {
    throw "CheckSeconds must be 10..3600"
}
$source = (Resolve-Path -LiteralPath $PSScriptRoot).Path
Set-Location -LiteralPath $source
$root = [System.IO.Path]::GetFullPath($DataDir)
$plan = Join-Path $root "learning-plan.json"
if ($ActivateOfficialTech) {
    Write-Host "Activating official public technology documentation and publisher feeds."
    Write-Host "Existing approved entries, quotas and SQLite assignments remain intact."
    & $Python (Join-Path $source "suryadev_continuity.py") --data $root activate-official-tech
    if ($LASTEXITCODE -ne 0) {
        throw "Could not activate the official learning source pack; no worker started"
    }
}
if (-not (Test-Path -LiteralPath $plan -PathType Leaf)) {
    throw "Missing approved research plan: $plan. Use -ActivateOfficialTech to opt in."
}
$workerArgs = @(
    (Join-Path $source "suryadev_extras.py"),
    "--data", $root,
    "worker", "--plan", $plan,
    "--refill-minutes", [string]$RefillMinutes,
    "--interval", [string]$CheckSeconds
)
if ($CoreMissionConfig) {
    if (-not (Test-Path -LiteralPath $CoreMissionConfig -PathType Leaf)) {
        throw "Core mission configuration does not exist: $CoreMissionConfig"
    }
    $workerArgs += @("--core-mission-config",$CoreMissionConfig)
}
if (($DeepWeb -or $DeepPDF) -and -not $VisionModel) {
    throw "DeepWeb/DeepPDF visual understanding requires -VisionModel and a locally installed image-capable Ollama model"
}
if ($DeepWeb) { $env:SURYADEV_DEEP_WEB = "1" }
if ($DeepPDF) { $env:SURYADEV_DEEP_PDF = "1" }
if ($DeepWeb -or $DeepPDF) { $env:SURYADEV_VISION_MODEL = $VisionModel }
if ($AnalyzeYoutubeComments) { $env:SURYADEV_YT_COMMENTS = "1" }
if ($UseOllama) {
    $workerArgs += @("--model",$Model)
} else {
    $workerArgs += "--no-ollama"
}
Write-Host "Starting ONE self-refilling SURYADEV worker from the approved plan."
Write-Host "YouTube rate limits remain respected; website/PDF work is independent."
Write-Host "Stop with Ctrl+C. Do not launch another worker or mission for this data root."
& $Python @workerArgs
if ($LASTEXITCODE -ne 0) {
    throw "SURYADEV worker returned a nonzero exit status. Check worker console."
}

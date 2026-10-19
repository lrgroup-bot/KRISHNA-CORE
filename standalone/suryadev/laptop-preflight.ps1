param(
  [string]$Data = "$env:USERPROFILE\SURYADEV-DATA",
  [string]$Python = "python",
  [switch]$SkipOllama
)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
Write-Host "SURYADEV standalone laptop preflight"
& $Python --version
if ($LASTEXITCODE -ne 0) { throw "Python unavailable" }
& $Python -m compileall -q .
if ($LASTEXITCODE -ne 0) { throw "Python syntax checks failed" }
& $Python -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw "Unit tests failed" }
& $Python suryadev.py --data $Data status
if ($LASTEXITCODE -ne 0) { throw "Local database failed" }
if (-not $SkipOllama) {
  try {
    $models = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 5
    if (-not ($models.models | Where-Object { $_.name -like "qwen3.5:9b*" })) {
      Write-Warning "Ollama reachable but qwen3.5:9b not found"
    } else { Write-Host "Ollama qwen3.5:9b available" }
  } catch { Write-Warning "Ollama not reachable on laptop loopback" }
}
Write-Host "Discovering possible KRISHNA Core nodes; no automatic pairing"
& $Python suryadev_discovery.py
if ($LASTEXITCODE -ne 0) { throw "Discovery failed" }
Write-Host "Preflight finished. Core joining requires verified authenticated enrollment."

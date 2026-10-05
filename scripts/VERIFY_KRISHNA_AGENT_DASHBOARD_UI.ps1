param(
    [string]$SourceRoot = "E:\KRISHNA-SOURCE",
    [string]$Python = "E:\Krishna-The GOD\.venv\Scripts\python.exe"
)

$ErrorActionPreference = "Stop"
$htmlPath = Join-Path $SourceRoot "core\web_validation.html"
if (-not (Test-Path -LiteralPath $htmlPath)) { throw "KRISHNA UI not found: $htmlPath" }
$html = Get-Content -LiteralPath $htmlPath -Raw -Encoding UTF8

$checks = [ordered]@{
    marker = $html.Contains("KRISHNA AGENT WORK DASHBOARD v1")
    dashboard_dialog = $html.Contains('class="godDetailDialog agentWorkDashboard"')
    readable_name_override = $html.Contains('position:static!important;width:auto!important;height:auto!important;clip:auto!important')
    three_d_logo = $html.Contains('transform:translateZ(12px)!important')
    semantic_work_state = $html.Contains("row.classList.add('workstate-'+String(g.state||'idle').toLowerCase())")
    completed_metric = $html.Contains('id="godMetricDone"')
    attention_metric = $html.Contains('id="godMetricAttention"')
    progress_truth = $html.Contains("'Not reported'") -and $html.Contains('id="godDetailProgressBar"')
    recent_activity = $html.Contains('id="godDetailRecent"')
}

$failed = @($checks.GetEnumerator() | Where-Object { -not $_.Value })
$checks.GetEnumerator() | ForEach-Object {
    $label = if ($_.Value) { "PASS" } else { "FAIL" }
    Write-Host ("[{0}] {1}" -f $label,$_.Key) -ForegroundColor $(if($_.Value){"Green"}else{"Red"})
}
if ($failed.Count) { throw "Agent dashboard contract failed: $($failed.Name -join ', ')" }

if (Test-Path -LiteralPath $Python) {
    Push-Location $SourceRoot
    try {
        & $Python -m unittest -v tests.test_current_krishna_ui_contract
        if ($LASTEXITCODE -ne 0) { throw "Current KRISHNA UI contract tests failed" }
    }
    finally { Pop-Location }
} else {
    Write-Host "[WARN] Python runtime not found at $Python; static dashboard checks passed but unittest was skipped." -ForegroundColor Yellow
}

Write-Host "KRISHNA Agent Work Dashboard source verification: PASS" -ForegroundColor Green

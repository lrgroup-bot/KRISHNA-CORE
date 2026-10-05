[CmdletBinding()]
param(
    [string]$Root = "E:\Krishna-The GOD",
    [switch]$DownloadOnly,
    [switch]$SkipJoern,
    [switch]$SkipSemgrep,
    [switch]$SkipStryker
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# KRISHNA free-only external-tool staging.
# This script intentionally:
# - installs/downloads only the pinned free/open-source instruments in config/free-gap-tools.lock.json;
# - keeps every tool under E:\Krishna-The GOD by default;
# - does NOT add anything to global PATH;
# - does NOT start Toxiproxy or any other service;
# - does NOT run scans/mutations against live source;
# - does NOT grant any tool Sudarshan/Shared Action Bus authority;
# - does NOT install Archify (optional presentation layer) by default.

function Write-Step([string]$Message) {
    Write-Host "`n=== $Message ===" -ForegroundColor Cyan
}

function Ensure-Dir([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Download-File([string]$Url, [string]$Destination) {
    Ensure-Dir (Split-Path -Parent $Destination)
    if (Test-Path -LiteralPath $Destination) {
        Write-Host "Already downloaded: $Destination"
        return
    }
    $partial = "$Destination.partial"
    Remove-Item -LiteralPath $partial -Force -ErrorAction SilentlyContinue
    $curl = Get-Command curl.exe -ErrorAction SilentlyContinue
    if ($curl) {
        & $curl.Source -L --fail --retry 3 --retry-delay 2 --output $partial $Url
        if ($LASTEXITCODE -ne 0) { throw "curl failed for $Url" }
    } else {
        Invoke-WebRequest -Uri $Url -OutFile $partial -UseBasicParsing
    }
    Move-Item -LiteralPath $partial -Destination $Destination -Force
}

function Assert-Sha256([string]$Path, [string]$Expected) {
    $actual = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
    $expectedNormalized = $Expected.Trim().ToLowerInvariant()
    if ($actual -ne $expectedNormalized) {
        throw "SHA256 mismatch for $Path. Expected $expectedNormalized, got $actual"
    }
    Write-Host "SHA256 OK: $(Split-Path -Leaf $Path)"
    return $actual
}

function Get-ChecksumFromFile([string]$ChecksumFile, [string]$FileName) {
    $escaped = [regex]::Escape($FileName)
    $line = Get-Content -LiteralPath $ChecksumFile | Where-Object { $_ -match "(?i)$escaped$" } | Select-Object -First 1
    if (-not $line) { throw "Checksum entry not found for $FileName" }
    $parts = ($line.Trim() -split '\s+')
    if ($parts.Count -lt 2 -or $parts[0] -notmatch '^[0-9a-fA-F]{64}$') {
        throw "Unrecognized checksum format for $FileName"
    }
    return $parts[0].ToLowerInvariant()
}

function Expand-ZipClean([string]$Archive, [string]$Destination) {
    if (Test-Path -LiteralPath $Destination) {
        Write-Host "Already staged: $Destination"
        return
    }
    $tmp = "$Destination.extracting"
    Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue
    Ensure-Dir $tmp
    Expand-Archive -LiteralPath $Archive -DestinationPath $tmp -Force
    Move-Item -LiteralPath $tmp -Destination $Destination
}

function Resolve-BootstrapPython {
    $preferred = Join-Path $Root "venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $preferred) { return $preferred }
    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($python) { return $python.Source }
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) { return $python.Source }
    return $null
}

function Install-PythonTool([string]$Id, [string]$PackageSpec, [string]$ToolRoot, [string]$BootstrapPython) {
    $venv = Join-Path $ToolRoot "venv"
    $venvPython = Join-Path $venv "Scripts\python.exe"
    Ensure-Dir $ToolRoot
    if (-not (Test-Path -LiteralPath $venvPython)) {
        & $BootstrapPython -m venv $venv
        if ($LASTEXITCODE -ne 0) { throw "Failed creating venv for $Id" }
    }
    & $venvPython -m pip install --disable-pip-version-check --no-input --no-warn-script-location $PackageSpec
    if ($LASTEXITCODE -ne 0) { throw "pip install failed for $PackageSpec" }
    & $venvPython -m pip freeze | Set-Content -LiteralPath (Join-Path $ToolRoot "installed-freeze.txt") -Encoding UTF8
    return $venvPython
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$manifestPath = Join-Path $repoRoot "config\free-gap-tools.lock.json"
if (-not (Test-Path -LiteralPath $manifestPath)) {
    throw "Missing tool lock manifest: $manifestPath"
}
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if ($manifest.policy -ne "FREE_ONLY_LOCAL_FIRST_SUDARSHAN_GOVERNED") {
    throw "Refusing unknown tool policy: $($manifest.policy)"
}

if (-not [System.IO.Path]::IsPathRooted($Root)) { throw "Root must be an absolute path" }
Ensure-Dir $Root
$toolsRoot = Join-Path $Root "tools"
$downloadsRoot = Join-Path $toolsRoot "downloads\free-gap-tools"
$stateRoot = Join-Path $Root "state\tool-install"
$cacheRoot = Join-Path $Root "state\tool-cache"
Ensure-Dir $toolsRoot
Ensure-Dir $downloadsRoot
Ensure-Dir $stateRoot
Ensure-Dir $cacheRoot

# Keep temporary/package-manager state on the KRISHNA drive for this process only.
$env:TEMP = Join-Path $Root "temp"
$env:TMP = $env:TEMP
$env:PIP_CACHE_DIR = Join-Path $cacheRoot "pip"
$env:npm_config_cache = Join-Path $cacheRoot "npm"
Ensure-Dir $env:TEMP
Ensure-Dir $env:PIP_CACHE_DIR
Ensure-Dir $env:npm_config_cache

$qualifier = Split-Path -Qualifier $Root
if ($qualifier) {
    $driveName = $qualifier.TrimEnd('\').TrimEnd(':')
    $drive = Get-PSDrive -Name $driveName -ErrorAction SilentlyContinue
    if ($drive) {
        $freeGB = [math]::Round($drive.Free / 1GB, 2)
        Write-Host "KRISHNA drive free space: $freeGB GB"
        $minimum = if ($SkipJoern) { 4 } else { 12 }
        if ($freeGB -lt $minimum) {
            throw "Need at least $minimum GB free for safe staging; found $freeGB GB"
        }
    }
}

$results = [System.Collections.Generic.List[object]]::new()
function Record-Result([string]$Tool, [string]$Status, [string]$Path, [string]$Detail = "") {
    $results.Add([pscustomobject]@{ tool=$Tool; status=$Status; path=$Path; detail=$Detail })
}

function Get-Tool([string]$Id) {
    $row = @($manifest.tools | Where-Object { $_.id -eq $Id })
    if ($row.Count -ne 1) { throw "Expected exactly one manifest entry for $Id" }
    return $row[0]
}

Write-Step "Pinned binary instruments"

if (-not $SkipJoern) {
    try {
        $t = Get-Tool "joern"
        $archive = Join-Path $downloadsRoot $t.filename
        Download-File $t.url $archive
        $hash = Assert-Sha256 $archive $t.sha256
        if (-not $DownloadOnly) {
            $dest = Join-Path $toolsRoot ("joern\" + $t.version)
            Expand-ZipClean $archive $dest
            $java = Get-Command java.exe -ErrorAction SilentlyContinue
            if (-not $java) { $java = Get-Command java -ErrorAction SilentlyContinue }
            $detail = "staged; upstream recommends JDK 21"
            if ($java) {
                $javaText = (& $java.Source -version 2>&1 | Out-String).Trim()
                $detail += "; java detected: " + ($javaText -replace "`r?`n", " ")
            } else {
                $detail += "; Java not detected, runtime acceptance pending"
            }
            Record-Result "joern" "STAGED_UNVERIFIED" $dest $detail
        } else {
            Record-Result "joern" "DOWNLOADED_VERIFIED_HASH" $archive $hash
        }
    } catch {
        Record-Result "joern" "FAILED" "" $_.Exception.Message
        Write-Warning "Joern staging failed: $($_.Exception.Message)"
    }
}

try {
    $t = Get-Tool "osv-scanner"
    $download = Join-Path $downloadsRoot $t.filename
    Download-File $t.url $download
    $hash = Assert-Sha256 $download $t.sha256
    if (-not $DownloadOnly) {
        $destDir = Join-Path $toolsRoot ("osv-scanner\" + $t.version)
        Ensure-Dir $destDir
        $dest = Join-Path $destDir "osv-scanner.exe"
        Copy-Item -LiteralPath $download -Destination $dest -Force
        Record-Result "osv-scanner" "STAGED_UNVERIFIED" $dest $hash
    } else { Record-Result "osv-scanner" "DOWNLOADED_VERIFIED_HASH" $download $hash }
} catch {
    Record-Result "osv-scanner" "FAILED" "" $_.Exception.Message
    Write-Warning "OSV-Scanner staging failed: $($_.Exception.Message)"
}

try {
    $t = Get-Tool "gitleaks"
    $archive = Join-Path $downloadsRoot $t.filename
    Download-File $t.url $archive
    $hash = Assert-Sha256 $archive $t.sha256
    if (-not $DownloadOnly) {
        $dest = Join-Path $toolsRoot ("gitleaks\" + $t.version)
        Expand-ZipClean $archive $dest
        Record-Result "gitleaks" "STAGED_UNVERIFIED" $dest $hash
    } else { Record-Result "gitleaks" "DOWNLOADED_VERIFIED_HASH" $archive $hash }
} catch {
    Record-Result "gitleaks" "FAILED" "" $_.Exception.Message
    Write-Warning "Gitleaks staging failed: $($_.Exception.Message)"
}

try {
    $cli = Get-Tool "toxiproxy-cli"
    $server = Get-Tool "toxiproxy-server"
    $checksumFile = Join-Path $downloadsRoot "toxiproxy-2.12.0-checksums.txt"
    Download-File $cli.checksums_url $checksumFile
    $destDir = Join-Path $toolsRoot ("toxiproxy\" + $cli.version)
    if (-not $DownloadOnly) { Ensure-Dir $destDir }
    foreach ($t in @($cli, $server)) {
        $download = Join-Path $downloadsRoot $t.filename
        Download-File $t.url $download
        $expected = Get-ChecksumFromFile $checksumFile $t.filename
        $hash = Assert-Sha256 $download $expected
        if (-not $DownloadOnly) {
            $name = if ($t.id -eq "toxiproxy-cli") { "toxiproxy-cli.exe" } else { "toxiproxy-server.exe" }
            $dest = Join-Path $destDir $name
            Copy-Item -LiteralPath $download -Destination $dest -Force
            Record-Result $t.id "STAGED_UNVERIFIED_NOT_STARTED" $dest $hash
        } else { Record-Result $t.id "DOWNLOADED_VERIFIED_HASH" $download $hash }
    }
} catch {
    Record-Result "toxiproxy" "FAILED" "" $_.Exception.Message
    Write-Warning "Toxiproxy staging failed: $($_.Exception.Message)"
}

if (-not $DownloadOnly) {
    Write-Step "Isolated Python instruments"
    $bootstrapPython = Resolve-BootstrapPython
    if (-not $bootstrapPython) {
        foreach ($id in @("hypothesis","mutmut","semgrep-ce")) {
            if ($id -eq "semgrep-ce" -and $SkipSemgrep) { continue }
            Record-Result $id "SKIPPED" "" "Python not found"
        }
        Write-Warning "Python not found; isolated Python tools were not installed."
    } else {
        Write-Host "Bootstrap Python: $bootstrapPython"
        foreach ($id in @("hypothesis", "mutmut", "semgrep-ce")) {
            if ($id -eq "semgrep-ce" -and $SkipSemgrep) {
                Record-Result $id "SKIPPED_BY_OWNER" "" "-SkipSemgrep"
                continue
            }
            try {
                $t = Get-Tool $id
                $dest = Join-Path $toolsRoot ($id + "\" + $t.version)
                $venvPython = Install-PythonTool $id $t.package $dest $bootstrapPython
                Record-Result $id "INSTALLED_UNVERIFIED" $dest ("venv python: " + $venvPython)
            } catch {
                Record-Result $id "FAILED" "" $_.Exception.Message
                Write-Warning "$id install failed: $($_.Exception.Message)"
            }
        }
    }

    Write-Step "Isolated JavaScript mutation instrument"
    if ($SkipStryker) {
        Record-Result "stryker-js" "SKIPPED_BY_OWNER" "" "-SkipStryker"
    } else {
        $npm = Get-Command npm.cmd -ErrorAction SilentlyContinue
        if (-not $npm) { $npm = Get-Command npm -ErrorAction SilentlyContinue }
        if (-not $npm) {
            Record-Result "stryker-js" "SKIPPED" "" "npm not found"
            Write-Warning "npm not found; StrykerJS not installed."
        } else {
            try {
                $t = Get-Tool "stryker-js"
                $dest = Join-Path $toolsRoot ("stryker-js\" + $t.version)
                Ensure-Dir $dest
                $packageJson = Join-Path $dest "package.json"
                if (-not (Test-Path -LiteralPath $packageJson)) {
                    $pkg = [ordered]@{
                        name = "krishna-stryker-instrument"
                        private = $true
                        version = "1.0.0"
                        description = "Isolated KRISHNA mutation-test instrument; no runtime authority"
                    } | ConvertTo-Json -Depth 4
                    Set-Content -LiteralPath $packageJson -Value $pkg -Encoding UTF8
                }
                Push-Location $dest
                try {
                    & $npm.Source install --save-exact --ignore-scripts $t.package
                    if ($LASTEXITCODE -ne 0) { throw "npm install failed for $($t.package)" }
                } finally { Pop-Location }
                Record-Result "stryker-js" "INSTALLED_UNVERIFIED" $dest "exact npm dependency; lifecycle scripts disabled during install"
            } catch {
                Record-Result "stryker-js" "FAILED" "" $_.Exception.Message
                Write-Warning "StrykerJS install failed: $($_.Exception.Message)"
            }
        }
    }
}

Write-Step "Write installation receipt"
$receipt = [ordered]@{
    schema_version = 1
    policy = $manifest.policy
    timestamp_utc = [DateTime]::UtcNow.ToString("o")
    root = $Root
    repo_commit = (& git -C $repoRoot rev-parse HEAD 2>$null | Select-Object -First 1)
    download_only = [bool]$DownloadOnly
    results = @($results)
    authority = "NONE: external tools are evidence instruments; Sudarshan/Policy Kernel/Shared Action Bus remain authoritative"
    automatic_scans_run = $false
    services_started = $false
    global_path_modified = $false
}
$receiptPath = Join-Path $stateRoot "free-gap-tools-install.json"
$receipt | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $receiptPath -Encoding UTF8

$results | Format-Table -AutoSize
Write-Host "`nReceipt: $receiptPath" -ForegroundColor Green
Write-Host "No scans, mutations, proxies, services, merges or deployments were started by this installer." -ForegroundColor Yellow
Write-Host "Next gate: run each tool's seeded KRISHNA acceptance benchmark before status can become VERIFIED." -ForegroundColor Yellow

if (@($results | Where-Object { $_.status -eq "FAILED" }).Count -gt 0) {
    exit 2
}
exit 0

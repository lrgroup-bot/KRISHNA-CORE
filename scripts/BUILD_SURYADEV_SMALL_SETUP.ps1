param(
    [Parameter(Mandatory=$true)][string]$PayloadDirectory,
    [Parameter(Mandatory=$true)][string]$DownloadUrl,
    [Parameter(Mandatory=$true)][string]$ReleaseVersion,
    [string]$Output = '.\dist-suryadev-setup'
)
$ErrorActionPreference='Stop'
$Repo=Split-Path -Parent $PSScriptRoot
$Source=Join-Path $Repo 'standalone\suryadev\setup'
$Output=[IO.Path]::GetFullPath($Output)
$PayloadDirectory=(Resolve-Path -LiteralPath $PayloadDirectory).Path
New-Item -ItemType Directory -Force -Path $Output | Out-Null
$Zip=Join-Path $Output 'SURYADEV-Learner-Payload.zip'
if (Test-Path -LiteralPath $Zip) { throw 'Choose a new setup output folder; existing payload will not be overwritten' }
Add-Type -AssemblyName System.IO.Compression.FileSystem
# Payload must have the expected root folder, even when a caller uses another parent.
if ((Split-Path -Leaf $PayloadDirectory) -ne 'Suryadev-Learner') { throw 'Expected the full Suryadev-Learner package directory' }
[IO.Compression.ZipFile]::CreateFromDirectory($PayloadDirectory,$Zip,[IO.Compression.CompressionLevel]::Optimal,$true)
$Hash=(Get-FileHash -LiteralPath $Zip -Algorithm SHA256).Hash.ToLowerInvariant()
$ExeHash=(Get-FileHash -LiteralPath (Join-Path $PayloadDirectory 'Suryadev-Learner.exe') -Algorithm SHA256).Hash.ToLowerInvariant()
$Bytes=(Get-Item -LiteralPath $Zip).Length
$UrlLiteral=ConvertTo-Json -InputObject $DownloadUrl -Compress
$VersionLiteral=ConvertTo-Json -InputObject $ReleaseVersion -Compress
$Config=Join-Path $Output 'ReleaseSpec.cs'
@"
namespace SuryadevSetup {
    public static class ReleaseSpec {
        public const string Url=$UrlLiteral;
        public static readonly Payload Payload=new Payload(Url,"$Hash","$ExeHash",${Bytes}L,$VersionLiteral);
    }
}
"@ | Set-Content -LiteralPath $Config -Encoding UTF8
$Compiler=Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if (-not (Test-Path -LiteralPath $Compiler)) {throw 'Windows .NET Framework C# compiler is required'}
$References=@('/r:System.Windows.Forms.dll','/r:System.Drawing.dll','/r:System.IO.Compression.dll','/r:System.IO.Compression.FileSystem.dll','/r:System.Web.Extensions.dll','/r:Microsoft.CSharp.dll')
$Main=Join-Path $Source 'SuryadevSetup.cs'
$SetupExe=Join-Path $Output 'SURYADEV-Setup.exe'
& $Compiler /nologo /optimize+ /target:winexe /platform:x64 "/out:$SetupExe" @References $Main $Config
if ($LASTEXITCODE -ne 0) {throw 'Small setup compilation failed'}
$Fixture=Join-Path $Output 'SetupFixture.exe'
& $Compiler /nologo /target:exe "/out:$Fixture" (Join-Path $Source 'TestFixture.cs')
if ($LASTEXITCODE -ne 0) {throw 'Test fixture compilation failed'}
$Tests=Join-Path $Output 'SetupTests.exe'
& $Compiler /nologo /target:exe /main:BootstrapTests "/out:$Tests" @References $Main $Config (Join-Path $Source 'SetupTests.cs')
if ($LASTEXITCODE -ne 0) {throw 'Bootstrap tests compilation failed'}
$TestRoot=Join-Path $Output '_tests'
& $Tests $TestRoot $Fixture
if ($LASTEXITCODE -ne 0) {throw 'Bootstrap safety/integration tests failed'}
@{
    schema='suryadev.small-setup-release.v1'; version=$ReleaseVersion
    setup='SURYADEV-Setup.exe'; setup_bytes=(Get-Item -LiteralPath $SetupExe).Length
    setup_sha256=(Get-FileHash -LiteralPath $SetupExe).Hash.ToLowerInvariant()
    payload_url=$DownloadUrl; payload_sha256=$Hash; payload_bytes=$Bytes; learner_exe_sha256=$ExeHash
    components_in_setup_exe=$false; github_login_required=$false
    source_commit=(& git -C $Repo rev-parse HEAD)
} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $Output 'SETUP-RELEASE.json') -Encoding UTF8
Write-Output "Small setup EXE: $SetupExe"

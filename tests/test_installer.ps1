param(
    [Parameter(Mandatory = $true)]
    [string]$Installer
)

$ErrorActionPreference = "Stop"
$repoDir = Split-Path $PSScriptRoot -Parent
$installerPath = (Resolve-Path -LiteralPath $Installer).Path
$sourceExe = Join-Path $repoDir "dist\ncdl.exe"
$registryPath = "HKCU:\Software\haruyq\ncdl"

if (Test-Path -LiteralPath $registryPath) {
    throw "ncdl is already installed for this user. Run this test with a separate Windows user."
}
if (-not (Test-Path -LiteralPath $sourceExe -PathType Leaf)) {
    throw "Missing $sourceExe. Run build.bat before this test."
}

$originalPath = [Environment]::GetEnvironmentVariable("Path", "User")
$testDir = Join-Path ([IO.Path]::GetTempPath()) ("ncdl-installer-" + [guid]::NewGuid())
$fixtureDir = Join-Path $testDir "fixture"
$installDir = Join-Path $testDir "installed"
$oldInstaller = Join-Path $testDir "ncdl-old.msi"
$installedProduct = $null
New-Item -ItemType Directory -Path $fixtureDir | Out-Null
[IO.File]::WriteAllBytes((Join-Path $fixtureDir "ncdl.exe"), [byte[]](77, 90, 0, 0))
Write-Host "Installer test files and logs: $testDir"

function Invoke-Msi {
    param(
        [string]$Package,
        [string]$Action,
        [string]$LogName,
        [int[]]$ExpectedCodes = @(0, 3010)
    )

    $logPath = Join-Path $testDir "$LogName.log"
    $arguments = @(
        $Action, "`"$Package`"", "/qn", "/norestart",
        "INSTALLFOLDER=`"$installDir`"", "/l*v", "`"$logPath`""
    )
    $process = Start-Process msiexec.exe -ArgumentList $arguments -WindowStyle Hidden -Wait -PassThru
    if ($process.ExitCode -notin $ExpectedCodes) {
        throw "Windows Installer failed with code $($process.ExitCode). See $logPath."
    }
    return $process.ExitCode
}

function Assert-UserPath {
    param([int]$ExpectedCount)

    $entries = [Environment]::GetEnvironmentVariable("Path", "User") -split ";"
    $installEntries = @($entries | Where-Object { $_.TrimEnd("\") -ieq $installDir })
    if ($installEntries.Count -ne $ExpectedCount) {
        throw "Expected $ExpectedCount entries for $installDir in user PATH; found $($installEntries.Count)."
    }
    foreach ($entry in ($originalPath -split ";")) {
        if ($entry -and $entry -notin $entries) {
            throw "An existing user PATH entry was removed: $entry"
        }
    }
}

Push-Location $repoDir
try {
    dotnet wix build installer/ncdl.wxs -arch x64 -d Version=0.0.0 -d "SourceDir=$fixtureDir" -o $oldInstaller
    if ($LASTEXITCODE -ne 0) {
        throw "Could not build the previous-version MSI fixture. Run dotnet tool restore and retry."
    }
} finally {
    Pop-Location
}

$installedExe = Join-Path $installDir "ncdl.exe"
$savedFiles = @{
    "config.toml" = '[download]'
    "cookies.txt" = "installer test cookie"
    "downloads\saved.txt" = "installer test download"
}

try {
    [void](Invoke-Msi $oldInstaller "/i" "install")
    $installedProduct = $oldInstaller
    if ((Get-FileHash -LiteralPath $installedExe).Hash -ne (Get-FileHash -LiteralPath (Join-Path $fixtureDir "ncdl.exe")).Hash) {
        throw "The previous-version executable was not installed in $installDir."
    }
    Assert-UserPath 1

    New-Item -ItemType Directory -Path (Join-Path $installDir "downloads") | Out-Null
    foreach ($name in $savedFiles.Keys) {
        Set-Content -LiteralPath (Join-Path $installDir $name) -Value $savedFiles[$name] -NoNewline -Encoding UTF8
    }

    [void](Invoke-Msi $installerPath "/i" "upgrade")
    $installedProduct = $installerPath
    if ((Get-FileHash -LiteralPath $installedExe).Hash -ne (Get-FileHash -LiteralPath $sourceExe).Hash) {
        throw "The upgraded executable does not match $sourceExe."
    }
    & $installedExe --help
    if ($LASTEXITCODE -ne 0) { throw "The installed CLI could not start." }
    Assert-UserPath 1
    foreach ($name in $savedFiles.Keys) {
        if ((Get-Content -LiteralPath (Join-Path $installDir $name) -Raw -Encoding UTF8) -cne $savedFiles[$name]) {
            throw "The upgrade changed user data: $name"
        }
    }

    $downgradeCode = Invoke-Msi $oldInstaller "/i" "downgrade" @(0, 3010, 1603)
    if ($downgradeCode -ne 1603) {
        $installedProduct = $oldInstaller
        throw "The installer allowed a downgrade to version 0.0.0."
    }
} finally {
    if ($installedProduct) {
        [void](Invoke-Msi $installedProduct "/x" "uninstall")
    }
}

if (Test-Path -LiteralPath $installedExe) {
    throw "The executable remains after uninstall: $installedExe"
}
if (Test-Path -LiteralPath $registryPath) {
    throw "The installation registry key remains after uninstall: $registryPath"
}
Assert-UserPath 0
foreach ($name in $savedFiles.Keys) {
    if ((Get-Content -LiteralPath (Join-Path $installDir $name) -Raw -Encoding UTF8) -cne $savedFiles[$name]) {
        throw "Uninstall changed user data: $name"
    }
}
Write-Host "Installer checks passed: install, upgrade, downgrade protection, PATH, user data, and uninstall."

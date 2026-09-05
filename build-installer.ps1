param([switch]$SkipBuild)

$ErrorActionPreference = "Stop"
Push-Location $PSScriptRoot

try {
    $version = uv run --locked python -c "import runpy; print(runpy.run_path('src/__version__.py')['__version__'])"
    if ($LASTEXITCODE -ne 0) { throw "Could not read src/__version__.py." }
    if ($version -notmatch '^\d+\.\d+\.\d+$') { throw "Use a major.minor.patch version in src/__version__.py." }

    if (-not $SkipBuild) {
        & .\build.bat
        if ($LASTEXITCODE -ne 0) { throw "The executable build failed." }
    }

    dotnet tool restore
    if ($LASTEXITCODE -ne 0) { throw "WiX restore failed. Install the .NET 8 SDK and retry." }

    dotnet wix build installer\ncdl.wxs -arch x64 `
        -d "Version=$version" -d "SourceDir=$PSScriptRoot\dist" `
        -o "dist\ncdl-$version-windows-x64.msi"
    if ($LASTEXITCODE -ne 0) { throw "The installer build failed." }
}
finally {
    Pop-Location
}

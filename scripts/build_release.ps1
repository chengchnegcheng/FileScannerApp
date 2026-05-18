param(
    [switch]$BuildInstaller
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

Write-Host "[1/3] Running tests..."
python -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[2/3] Building EXE..."
python -m PyInstaller --clean --noconfirm app.spec
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $BuildInstaller) {
    Write-Host "Done: dist/FileScanner_Win11.exe"
    exit 0
}

$iscc = Get-Command iscc -ErrorAction SilentlyContinue
if (-not $iscc) {
    Write-Warning "Inno Setup (iscc) not found. Installer script is ready at installer/FileScanner_Win11.iss"
    exit 0
}

Write-Host "[3/3] Building installer..."
iscc installer/FileScanner_Win11.iss
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Done: installer build completed."

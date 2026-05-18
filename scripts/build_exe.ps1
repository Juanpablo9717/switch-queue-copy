# build_exe.ps1
# One-click standalone Windows .exe build via `flet pack` (PyInstaller under the hood).
# Output: dist/Switch Queue Copy.exe

$ErrorActionPreference = "Stop"

# Repo root = parent of this script
$Root = Resolve-Path "$PSScriptRoot/.."
Push-Location $Root
try {
    Write-Host ""
    Write-Host "Switch Queue Copy — build" -ForegroundColor Cyan
    Write-Host "============================="
    Write-Host "Root: $Root"
    Write-Host ""

    # Sanity checks
    if (-not (Get-Command flet -ErrorAction SilentlyContinue)) {
        Write-Host "flet CLI not found. Install with:" -ForegroundColor Red
        Write-Host "    pip install flet" -ForegroundColor Yellow
        exit 1
    }

    # Clean previous outputs
    if (Test-Path "dist") {
        Write-Host "Cleaning dist/..." -ForegroundColor DarkGray
        Remove-Item "dist" -Recurse -Force
    }
    if (Test-Path "build") {
        Write-Host "Cleaning build/..." -ForegroundColor DarkGray
        Remove-Item "build" -Recurse -Force
    }

    # Pack
    $iconArg = @()
    if (Test-Path "assets/icon.ico") {
        $iconArg = @("--icon", "assets/icon.ico")
    }

    Write-Host "Running flet pack..." -ForegroundColor Cyan
    # NOTE: we point flet pack at the top-level launcher (main.py), not
    # the package's __main__.py. See main.py's docstring for the why.
    flet pack `
        "main.py" `
        --name "Switch Queue Copy" `
        --product-name "Switch Queue Copy" `
        --product-version "0.1.0" `
        --file-version "0.1.0" `
        @iconArg `
        --yes

    if ($LASTEXITCODE -ne 0) {
        Write-Host "flet pack failed (exit $LASTEXITCODE)" -ForegroundColor Red
        exit $LASTEXITCODE
    }

    Write-Host ""
    Write-Host "Build OK." -ForegroundColor Green
    $exe = Get-ChildItem -Path "dist" -Filter "*.exe" -Recurse | Select-Object -First 1
    if ($exe) {
        Write-Host "Output: $($exe.FullName)" -ForegroundColor Green
    }
}
finally {
    Pop-Location
}

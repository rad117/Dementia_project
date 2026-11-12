# PowerShell equivalent of scripts/check_all.sh for Windows
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Host "Creating virtual environment in .venv..."
    python -m venv .venv
}

Write-Host "Installing backend dev requirements..."
& $VenvPython -m pip install -q -r backend\requirements-dev.txt

Write-Host "== backend + ml + monitoring tests =="
& $VenvPython -m pytest -q

Write-Host "== frontend lint =="
if (-not (Test-Path "frontend\node_modules")) {
    npm --prefix frontend install
}
npm --prefix frontend run lint

Write-Host "== frontend tests =="
npm --prefix frontend run test

Write-Host "== frontend build =="
npm --prefix frontend run build

Write-Host "ALL CHECKS PASSED"

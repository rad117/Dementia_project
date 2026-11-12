# PowerShell equivalent of scripts/run_all.sh for Windows
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Host "Creating virtual environment in .venv..."
    python -m venv .venv
}

Write-Host "Installing backend requirements..."
& $VenvPython -m pip install -q -r backend\requirements.txt

if (-not (Test-Path "frontend\node_modules")) {
    Write-Host "Installing frontend dependencies..."
    npm --prefix frontend install
}

if (-not (Test-Path "frontend\.env.local")) {
    Copy-Item "frontend\.env.example" "frontend\.env.local"
}

Write-Host "Starting backend on http://127.0.0.1:8000..."
$BackendJob = Start-Process -FilePath $VenvPython -ArgumentList "-m", "uvicorn", "backend.main:app", "--port", "8000" -PassThru

try {
    Write-Host "Starting frontend on http://127.0.0.1:5173..."
    npm --prefix frontend run dev -- --host 127.0.0.1
} finally {
    if ($BackendJob -and -not $BackendJob.HasExited) {
        Write-Host "Stopping backend..."
        Stop-Process -Id $BackendJob.Id -Force
    }
}


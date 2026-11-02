<#
.SYNOPSIS
    Full local setup for Experience Intelligence on Windows 10/11.
.DESCRIPTION
    1. Checks dependencies
    2. Creates the backend Python virtual environment and installs requirements
    3. Copies backend/.env.example to backend/.env if missing
    4. Installs frontend npm dependencies
    5. Prints next steps to run the application
#>

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "=== Experience Intelligence - Windows Setup ===" -ForegroundColor Cyan

# 1. Dependency check
& (Join-Path $PSScriptRoot "check-dependencies.ps1")

# 2. Backend virtual environment
Write-Host ""
Write-Host "Setting up backend virtual environment..." -ForegroundColor Cyan
Set-Location (Join-Path $root "backend")

if (-not (Test-Path "venv")) {
    python -m venv venv
}

& ".\venv\Scripts\Activate.ps1"
python -m pip install --upgrade pip
pip install -r requirements.txt

# 3. Environment file
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created backend/.env from .env.example - review and adjust as needed." -ForegroundColor Yellow
}

New-Item -ItemType Directory -Force -Path "storage\uploads" | Out-Null
New-Item -ItemType Directory -Force -Path "storage\chroma" | Out-Null

# 4. Frontend dependencies
Write-Host ""
Write-Host "Installing frontend dependencies..." -ForegroundColor Cyan
Set-Location (Join-Path $root "frontend")
npm install

Set-Location $root

Write-Host ""
Write-Host "=== Setup complete ===" -ForegroundColor Green
Write-Host "Next steps:"
Write-Host "  1. Install and start Ollama, then run: scripts\setup-ollama.ps1"
Write-Host "  2. Start the backend:   cd backend; .\venv\Scripts\Activate.ps1; uvicorn app.main:app --reload --port 8001"
Write-Host "  3. Start the mock portal (for local testing): cd ..; python -m uvicorn mock_portal.main:app --port 9000"
Write-Host "  4. Start the frontend:  cd frontend; npm run dev"
Write-Host "  5. Open http://localhost:5173 and log in with the seeded default admin (see backend logs on first start)."

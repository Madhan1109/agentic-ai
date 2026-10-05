# Convenience launcher: seeds DB (if needed), starts API + Streamlit UI.
# Usage:  .\start.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path .\.venv\Scripts\Activate.ps1)) {
    Write-Host "Creating virtualenv..."
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt
} else {
    .\.venv\Scripts\Activate.ps1
}

if (-not (Test-Path .\.env)) {
    Copy-Item .env.example .env
    Write-Host "Created .env — optional free GROQ_API_KEY for natural-language replies." -ForegroundColor Yellow
}

python scripts\seed_db.py

Write-Host "Starting API on http://127.0.0.1:8000 ..." -ForegroundColor Cyan
Start-Process -FilePath ".\.venv\Scripts\python.exe" -ArgumentList "scripts\run_api.py" -WorkingDirectory $PSScriptRoot

Start-Sleep -Seconds 3
Write-Host "Starting UI on http://localhost:8501 ..." -ForegroundColor Cyan
python scripts\run_ui.py

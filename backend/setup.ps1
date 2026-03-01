# Market Intelligence Dashboard - Backend setup
# Python 3.11 or 3.12 required (3.14 has no pydantic-core wheel and would need Rust).
$ErrorActionPreference = "Stop"
$venvExists = Test-Path "venv"
# Prefer creating venv with Python 3.12 or 3.11
if (-not $venvExists) {
    foreach ($py in @("py -3.12", "py -3.11") ) {
        Write-Host "Trying $py -m venv venv ..." -ForegroundColor Cyan
        & cmd /c "$py -m venv venv" 2>$null
        if (Test-Path "venv\Scripts\python.exe") { break }
        if (Test-Path "venv") { Remove-Item -Recurse -Force venv }
    }
}
if (-not (Test-Path "venv\Scripts\python.exe")) {
    Write-Host "Python 3.11 or 3.12 is required." -ForegroundColor Red
    Write-Host "Install from https://www.python.org/downloads/ (e.g. Python 3.12)." -ForegroundColor Yellow
    Write-Host "Then run:  py -3.12 -m venv venv" -ForegroundColor Cyan
    Write-Host "Then:     .\venv\Scripts\Activate.ps1" -ForegroundColor Cyan
    Write-Host "Then:     pip install -r requirements.txt" -ForegroundColor Cyan
    exit 1
}
Write-Host "Activating venv and installing dependencies..." -ForegroundColor Cyan
& .\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip -q
pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { exit 1 }
if (-not (Test-Path ".env")) { Copy-Item .env.example .env; Write-Host "Created .env - add API keys if needed." -ForegroundColor Yellow }
Write-Host "Done. Start server: .\run.ps1" -ForegroundColor Green

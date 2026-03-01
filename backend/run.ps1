# Start the backend server (uses venv in this folder)
$ErrorActionPreference = "Stop"
$venvPython = "venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "Run setup first: .\setup.ps1" -ForegroundColor Red
    exit 1
}
# Python 3.14 is not supported (pydantic-core has no wheel). Require 3.11 or 3.12.
$pyvenvCfg = Join-Path $PSScriptRoot "venv\pyvenv.cfg"
if (Test-Path $pyvenvCfg) {
    $versionLine = Get-Content $pyvenvCfg | Where-Object { $_ -match "^version\s*=" }
    if ($versionLine -match "3\.14") {
        Write-Host "This venv uses Python 3.14, which is not supported (pydantic/fastapi need 3.11 or 3.12)." -ForegroundColor Red
        Write-Host "Recreate the venv with Python 3.11 or 3.12:" -ForegroundColor Yellow
        Write-Host "  Remove-Item -Recurse -Force .\venv" -ForegroundColor Cyan
        Write-Host "  .\setup.ps1" -ForegroundColor Cyan
        Write-Host "If you don't have 3.11/3.12, install from https://www.python.org/downloads/" -ForegroundColor Yellow
        exit 1
    }
}
# Free port 8000 if already in use (fixes "Errno 10048" / "address already in use")
$conn = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($conn) {
    $conn | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
    Write-Host "Freed port 8000." -ForegroundColor Yellow
    Start-Sleep -Seconds 1
}
# Use this folder's venv Python directly (no reliance on old paths from activation)
Write-Host "Starting server at http://127.0.0.1:8000 (docs: http://127.0.0.1:8000/docs)" -ForegroundColor Green
& (Join-Path $PSScriptRoot $venvPython) -m uvicorn main:app --host 0.0.0.0 --port 8000

# Recreate venv with Python 3.11 or 3.12 (required for pydantic/fastapi; 3.14 not supported)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Test-Path "venv") {
    Write-Host "Removing existing venv (Python 3.14 not supported)..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force venv
}

function Get-PythonVersion { param($pyExe)
    try {
        $v = & $pyExe -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        if ($v -match "3\.1[12]") { return $v }
    } catch {}
    return $null
}

$created = $false
# 1) Try py launcher
foreach ($py in @("py -3.12", "py -3.11") ) {
    try {
        Write-Host "Trying $py -m venv venv ..." -ForegroundColor Cyan
        $null = cmd /c "$py -m venv venv" 2>&1
        if (Test-Path "venv\Scripts\python.exe") {
            $ver = Get-PythonVersion ".\venv\Scripts\python.exe"
            if ($ver) { $created = $true; Write-Host "Created venv with Python $ver" -ForegroundColor Green; break }
            Remove-Item -Recurse -Force venv -ErrorAction SilentlyContinue
        }
    } catch {}
}
# 2) Try python in PATH (might be 3.11/3.12)
if (-not $created -and (Get-Command python -ErrorAction SilentlyContinue)) {
    $ver = Get-PythonVersion "python"
    if ($ver) {
        Write-Host "Trying python -m venv venv (Python $ver) ..." -ForegroundColor Cyan
        python -m venv venv
        if (Test-Path "venv\Scripts\python.exe") { $created = $true; Write-Host "Created venv with Python $ver" -ForegroundColor Green }
    }
}
# 3) Try common install paths
if (-not $created) {
    $base = $env:LOCALAPPDATA; if (-not $base) { $base = "C:\Users\$env:USERNAME\AppData\Local" }
    foreach ($dir in @("$base\Programs\Python\Python312", "$base\Programs\Python\Python311", "C:\Python312", "C:\Python311")) {
        $pyExe = Join-Path $dir "python.exe"
        if (Test-Path $pyExe) {
            $ver = Get-PythonVersion $pyExe
            if ($ver) {
                Write-Host "Trying $pyExe -m venv venv ..." -ForegroundColor Cyan
                & $pyExe -m venv venv
                if (Test-Path "venv\Scripts\python.exe") { $created = $true; Write-Host "Created venv with Python $ver" -ForegroundColor Green; break }
            }
        }
    }
}

if (-not $created) {
    Write-Host "Python 3.11 or 3.12 is required (you have 3.14; pydantic/fastapi do not support it yet)." -ForegroundColor Red
    Write-Host "1. Download Python 3.12: https://www.python.org/downloads/release/python-3120/" -ForegroundColor Yellow
    Write-Host "2. Run the installer and CHECK 'Add python.exe to PATH'" -ForegroundColor Yellow
    Write-Host "3. Close and reopen PowerShell, then run:  cd D:\abhishek\backend; .\fix.ps1" -ForegroundColor Cyan
    exit 1
}

Write-Host "Installing dependencies..." -ForegroundColor Cyan
& .\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip -q
pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { exit 1 }
if (-not (Test-Path ".env")) { Copy-Item .env.example .env; Write-Host "Created .env - add API keys if needed." -ForegroundColor Yellow }
Write-Host "Done. Start server: .\run.ps1" -ForegroundColor Green

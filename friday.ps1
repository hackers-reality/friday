Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONUTF8 = "1"

# ─── Auto-setup: create venv + install deps if missing ───
$venvPython = $null
if (Test-Path ".venv\Scripts\python.exe") {
    $venvPython = ".venv\Scripts\python.exe"
} elseif (Test-Path "venv\Scripts\python.exe") {
    $venvPython = "venv\Scripts\python.exe"
}

if (-not $venvPython) {
    Write-Host "[FRIDAY] No virtual environment found. Creating one..." -ForegroundColor Yellow
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[FRIDAY] Failed to create venv. Make sure Python 3.10+ is installed." -ForegroundColor Red
        Read-Host -Prompt "Press Enter to exit"
        exit 1
    }
    $venvPython = ".venv\Scripts\python.exe"
    Write-Host "[FRIDAY] Virtual environment created." -ForegroundColor Green
}

# Install dependencies if requirements.txt exists
if (Test-Path "requirements.txt") {
    # Check critical packages (core + screen + OSINT)
    $depsCheck = & $venvPython -c "import aiohttp, httpx, dnspython, requests, msgpack, reportlab, docx, chromadb, sherlock, holehe, pywinctl, PIL" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[FRIDAY] Installing dependencies..." -ForegroundColor Yellow
        & $venvPython -m pip install -r requirements.txt --quiet
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[FRIDAY] Dependencies installed." -ForegroundColor Green
        } else {
            Write-Host "[FRIDAY] Some deps failed to install. FRIDAY may not work correctly." -ForegroundColor Red
        }
    }
}

Write-Host "[STARK INDUSTRIES] Starting F.R.I.D.A.Y. Sovereign CLI Agent..." -ForegroundColor Yellow

# Add project to Python path
$env:PYTHONPATH = "$PSScriptRoot"

# Run python directly so all logs print to the active PowerShell terminal
& $venvPython friday.py

Write-Host "[STARK INDUSTRIES] Friday has exited." -ForegroundColor Red
Read-Host -Prompt "Press Enter to exit"

<#
.SYNOPSIS
  FRIDAY Unified Launcher — single script to install, activate & run.
.DESCRIPTION
  Run this to auto-create venv, install deps, create .env if missing,
  set up the friday.cmd PATH helper, then launch FRIDAY.
.EXAMPLE
  .\friday.ps1              # interactive mode (asks before each step)
  .\friday.ps1 -Auto        # unattended (yes to everything)
  .\friday.ps1 -SetupOnly   # only install, don't launch
  .\friday.ps1 -Dev         # skip install checks, launch fast
#>
param(
    [switch]$Auto,       # Unattended: yes to all prompts
    [switch]$SetupOnly,  # Install only, skip launch
    [switch]$Dev         # Skip install checks for rapid dev iterations
)

Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONUTF8 = "1"

# ─── Helper: ask or auto ───
function Confirm-Step {
    param([string]$Message)
    if ($Auto) { return $true }
    return (Read-Host "${Message} (y/n)") -eq "y"
}

# ─── ASCII banner ───
function Show-Banner {
    Write-Host "╔══════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║  FFFFF  RRRR   III  DDDD   AAA   Y   Y         ║" -ForegroundColor Yellow
    Write-Host "║  F      R   R   I   D   D  A   A   Y Y         ║" -ForegroundColor Yellow
    Write-Host "║  FFF    RRRR    I   D   D  AAAAA    Y          ║" -ForegroundColor Yellow
    Write-Host "║  F      R   R   I   D   D  A   A    Y          ║" -ForegroundColor Yellow
    Write-Host "║  F      R    R III  DDDD   A   A    Y          ║" -ForegroundColor Yellow
    Write-Host "║                                                ║" -ForegroundColor Yellow
    Write-Host "║  Ultimate AI Agent — Unified Launcher           ║" -ForegroundColor Green
    Write-Host "╚══════════════════════════════════════════════════╝" -ForegroundColor Cyan
}

# ─── Step 1: Detect / create venv ───
function Step-Venv {
    Write-Host "`n[1/5] Virtual environment..." -ForegroundColor Yellow

    # Which venvs exist?
    $venvPython = $null
    if (Test-Path ".venv\Scripts\python.exe") {
        $venvPython = ".venv\Scripts\python.exe"
    } elseif (Test-Path "venv\Scripts\python.exe") {
        $venvPython = "venv\Scripts\python.exe"
    }

    if ($venvPython) {
        Write-Host "  ✅ Found $venvPython" -ForegroundColor Green
        return $venvPython
    }

    # None found — create one
    if (-not (Confirm-Step "  No venv found. Create .venv?")) {
        Write-Host "  ⚠️  Skipping venv creation. Using system Python." -ForegroundColor Yellow
        return $null
    }

    Write-Host "  Creating .venv..." -ForegroundColor Cyan
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ❌ Failed to create venv. Install Python 3.10+ first." -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
    Write-Host "  ✅ .venv created" -ForegroundColor Green
    return ".venv\Scripts\python.exe"
}

# ─── Step 2: Install dependencies ───
function Step-Deps {
    param([string]$PythonExe)
    Write-Host "`n[2/5] Dependencies..." -ForegroundColor Yellow

    if (-not $PythonExe) { $PythonExe = "python" }

    # Quick check: are critical packages importable?
    $check = & $PythonExe -c "import aiohttp, httpx, requests, chromadb, reportlab, dnspython, docx, pywinctl, PIL, numpy, rich, fastapi, uvicorn" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ Core packages already installed" -ForegroundColor Green
        return
    }

    if (-not (Confirm-Step "  Install Python dependencies?")) {
        Write-Host "  ⚠️  Skipping dep install" -ForegroundColor Yellow
        return
    }

    Write-Host "  Installing core packages..." -ForegroundColor Cyan

    # Install from requirements.txt first
    if (Test-Path "requirements.txt") {
        & $PythonExe -m pip install -r requirements.txt --quiet --disable-pip-version-check
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✅ requirements.txt done" -ForegroundColor Green
        } else {
            Write-Host "  ⚠️  Some deps in requirements.txt failed" -ForegroundColor Yellow
        }
    }

    # Install critical packages that might be missing
    $critical = @(
        "aiohttp", "httpx", "requests", "python-dotenv",
        "chromadb>=0.4", "numpy", "Pillow",
        "reportlab", "python-docx", "openpyxl",
        "pywinctl>=0.0.52", "psutil",
        "rich", "colorama",
        "fastapi>=0.115.0", "uvicorn>=0.32.0", "websockets>=12.0",
        "python-multipart>=0.0.9", "flask>=3.0", "flask-socketio>=5.3",
        "pygame", "dnspython", "pyperclip"
    )
    foreach ($pkg in $critical) {
        $name = ($pkg -split '[<>=!~]')[0].Trim()
        $installed = & $PythonExe -c "import importlib.metadata as m; m.version('$name')" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  [SKIP] $name already installed" -ForegroundColor DarkGray
        } else {
            Write-Host "  [INSTALL] $pkg ..." -ForegroundColor Cyan
            & $PythonExe -m pip install $pkg --quiet --disable-pip-version-check
        }
    }

    Write-Host "  ✅ Dependency check complete" -ForegroundColor Green
}

# ─── Step 3: Setup .env if missing ───
function Step-Env {
    Write-Host "`n[3/5] Environment file..." -ForegroundColor Yellow
    if (Test-Path ".env") {
        Write-Host "  ✅ .env exists" -ForegroundColor Green
        return
    }

    if (-not (Confirm-Step "  Create .env file?")) {
        Write-Host "  ⚠️  Skipping .env creation" -ForegroundColor Yellow
        return
    }

    @"
# FRIDAY API Keys — Keep secret, never commit
GOOGLE_API_KEY=your_google_api_key_here
GROQ_API_KEY=your_groq_api_key_here
PICOVOICE_ACCESS_KEY=your_picovoice_access_key_here
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
DISCORD_BOT_TOKEN=your_discord_bot_token_here
DISCORD_WEBHOOK_URL=your_discord_webhook_url_here
NVIDIA_NIM_API_KEY=your_nvidia_nim_api_key_here
"@ | Out-File -FilePath ".env" -Encoding UTF8
    Write-Host "  ✅ .env created — edit it with your API keys" -ForegroundColor Green
}

# ─── Step 4: friday.cmd PATH helper ───
function Step-PathHelper {
    Write-Host "`n[4/5] Command helper..." -ForegroundColor Yellow
    if (Test-Path "friday.cmd") {
        Write-Host "  ✅ friday.cmd exists" -ForegroundColor Green
    } elseif (Confirm-Step "  Create friday.cmd wrapper?" -or $Auto) {
        @"
@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
set "FRIDAY_PY=python.exe"
if exist ".venv\Scripts\python.exe" (
    set "FRIDAY_PY=.venv\Scripts\python.exe"
) else if exist "venv\Scripts\python.exe" (
    set "FRIDAY_PY=venv\Scripts\python.exe"
)
if "%~1"=="" goto start_friday
if /I "%~1"=="start" goto start_friday
if /I "%~1"=="live" goto start_friday
%FRIDAY_PY% -m friday.cli %*
exit /b %ERRORLEVEL%
:start_friday
echo [STARK INDUSTRIES] Bootstrapping F.R.I.D.A.Y. Sovereign Agent...
%FRIDAY_PY% friday.py
"@ | Out-File -FilePath "friday.cmd" -Encoding ASCII
        Write-Host "  ✅ Created friday.cmd" -ForegroundColor Green
    }

    # Add to PATH if not already
    $currentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
    if ($currentPath -notlike "*$PSScriptRoot*") {
        [Environment]::SetEnvironmentVariable("PATH", "$currentPath;$PSScriptRoot", "User")
        Write-Host "  ✅ Added to PATH (restart terminal for new shells)" -ForegroundColor Green
    }
}

# ─── Step 5: Verify & launch ───
function Step-Launch {
    param([string]$PythonExe)
    Write-Host "`n[5/5] Launch..." -ForegroundColor Yellow

    # Verify key files
    $files = @("friday.py", "friday\live.py", "friday\cli.py")
    $missing = @()
    foreach ($f in $files) { if (-not (Test-Path $f)) { $missing += $f } }
    if ($missing.Count -gt 0) {
        Write-Host "  ❌ Missing files: $($missing -join ', ')" -ForegroundColor Red
        Write-Host "  Run from the FRIDAY root directory" -ForegroundColor Yellow
        Read-Host "Press Enter to exit"
        exit 1
    }

    Write-Host "  ✅ All files present" -ForegroundColor Green

    if ($SetupOnly) {
        Write-Host "`n  Setup complete (--SetupOnly, not launching)" -ForegroundColor Green
        return
    }

    if ($Dev) {
        Write-Host "`n  --Dev mode: launching without install checks" -ForegroundColor Yellow
    }

    if ($Auto -or (Confirm-Step "  Launch FRIDAY now?")) {
        Write-Host "`n[STARK INDUSTRIES] Starting F.R.I.D.A.Y. Sovereign CLI Agent..." -ForegroundColor Yellow
        $env:PYTHONPATH = $PSScriptRoot
        & $PythonExe friday.py
        Write-Host "`n[STARK INDUSTRIES] FRIDAY has exited." -ForegroundColor Red
    } else {
        Write-Host "`n  Setup complete. Run .\friday.ps1 again to launch." -ForegroundColor Green
    }
}

# ─── Main ───
Show-Banner
$py = Step-Venv
if (-not $Dev) {
    Step-Deps -PythonExe $py
    Step-Env
    Step-PathHelper
}
Step-Launch -PythonExe ($py -or "python")

Read-Host "`nPress Enter to exit"

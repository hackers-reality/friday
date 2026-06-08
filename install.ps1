# Friday Install Script (PowerShell)
# Run: powershell -ExecutionPolicy Bypass -File install.ps1

Write-Host "=============================================================" -ForegroundColor Cyan
Write-Host "  FFFFF  RRRR   III  DDDD   AAA   Y   Y                  " -ForegroundColor Yellow
Write-Host "  F      R   R   I   D   D  A   A   Y Y                    " -ForegroundColor Yellow
Write-Host "  FFF    RRRR    I   D   D  AAAAA    Y                     " -ForegroundColor Yellow
Write-Host "  F      R   R   I   D   D  A   A    Y                     " -ForegroundColor Yellow
Write-Host "  F      R    R III  DDDD   A   A    Y                     " -ForegroundColor Yellow
Write-Host "                                                             " -ForegroundColor Yellow
Write-Host "  Ultimate AI Agent - Installation Script                    " -ForegroundColor Green
Write-Host "=============================================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
Write-Host "[1/6] Checking Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ $pythonVersion" -ForegroundColor Green
    } else {
        throw "Python not found"
    }
} catch {
    Write-Host "  ❌ Python not found. Please install Python 3.10+" -ForegroundColor Red
    Write-Host "  Download from: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

# Check pip
Write-Host "`n[2/6] Checking pip..." -ForegroundColor Yellow
try {
    $pipVersion = python -m pip --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ $pipVersion" -ForegroundColor Green
    } else {
        throw "pip not found"
    }
} catch {
    Write-Host "  ❌ pip not found. Installing..." -ForegroundColor Red
    python -m ensurepip --upgrade
}

# Create virtual environment (optional)
Write-Host "`n[3/6] Setting up environment..." -ForegroundColor Yellow
$useVenv = Read-Host "  Create virtual environment? (y/n)"
if ($useVenv -eq "y") {
    if (-not (Test-Path "venv")) {
        python -m venv venv
        Write-Host "  ✅ Virtual environment created" -ForegroundColor Green
    }
    # Activate venv
    & .\venv\Scripts\Activate.ps1
    Write-Host "  ✅ Virtual environment activated" -ForegroundColor Green
}

# Install dependencies
Write-Host "`n[4/6] Installing Python packages..." -ForegroundColor Yellow
Write-Host "  Progress is printed package-by-package. Already installed packages are skipped." -ForegroundColor Yellow

$packages = @(
    "google-genai>=1.0",
    "requests>=2.31",
    "python-dotenv>=1.0",
    "pvporcupine>=3.0",
    "pvrecorder>=1.2",
    "PyAudio>=0.2.14",
    "pycaw>=1.5",
    "pygame>=2.5",
    "Pillow>=10.0",
    "opencv-python>=4.8",
    "pywinctl>=0.0.52",
    "google-auth-oauthlib>=1.2",
    "google-api-python-client>=2.125",
    "google-auth-httplib2>=0.2",
    "python-telegram-bot>=20.0",
    "discord.py>=2.3",
    "browser-history>=0.5",
    "psutil>=5.9",
    "schedule>=1.2",
    "chromadb>=0.4",
    "numpy>=1.24",
    "langchain-core>=0.2",
    "langchain-google-genai>=1.0",
    "langgraph>=1.0",
    "mcp>=1.0",
    "flask>=3.0",
    "flask-socketio>=5.3",
    "fastapi>=0.115.0",
    "uvicorn>=0.32.0",
    "python-multipart>=0.0.9",
    "websockets>=12.0",
    "rich>=13.0",
    "colorama>=0.4.6"
)

function Get-PackageNameFromRequirement {
    param([string]$Requirement)
    return (($Requirement -split '[<>=!~]')[0]).Trim()
}

function Test-PythonPackageInstalled {
    param([string]$DistributionName)
    python -c "import importlib.metadata as m, sys; m.version(sys.argv[1])" $DistributionName *> $null
    return ($LASTEXITCODE -eq 0)
}

function Install-PythonRequirement {
    param(
        [string]$Requirement,
        [bool]$Optional = $false
    )

    $name = Get-PackageNameFromRequirement $Requirement
    if (Test-PythonPackageInstalled $name) {
        Write-Host "  [SKIP] $Requirement already installed" -ForegroundColor DarkGray
        return
    }

    if ($Optional) {
        Write-Host "  [INSTALL] $Requirement (optional)..." -ForegroundColor Cyan
    } else {
        Write-Host "  [INSTALL] $Requirement..." -ForegroundColor Cyan
    }

    python -m pip install $Requirement --quiet --disable-pip-version-check
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] $Requirement installed" -ForegroundColor Green
    } elseif ($Optional) {
        Write-Host "  [WARN] Optional package failed: $Requirement" -ForegroundColor Yellow
    } else {
        Write-Host "  [WARN] Failed to install $Requirement (continuing)" -ForegroundColor Yellow
    }
}

$count = 0
foreach ($pkg in $packages) {
    $count += 1
    Write-Host "  [$count/$($packages.Count)] Checking $pkg" -ForegroundColor Gray
    Install-PythonRequirement $pkg $false
}

if ($false) {
foreach ($pkg in $packages) {
    Write-Host "  Installing $pkg..." -ForegroundColor Cyan
    python -m pip install $pkg --quiet
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    ✅ $pkg" -ForegroundColor Green
    } else {
        Write-Host "    ⚠️  Failed to install $pkg (will try to continue)" -ForegroundColor Yellow
    }
}

}

# Install all deps from requirements.txt
Write-Host "`n[5/6] Installing comprehensive dependencies from requirements.txt..." -ForegroundColor Yellow
if (Test-Path "requirements.txt") {
    python -m pip install -r requirements.txt --quiet --disable-pip-version-check
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ requirements.txt installed successfully" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  Some packages in requirements.txt failed. Check logs above." -ForegroundColor Yellow
    }
}

# Optional packages
Write-Host "`n[5b/6] Installing optional packages..." -ForegroundColor Yellow
$optional = @(
    "pvporcupine",  # Voice wake word (already installed if main)
    "selenium",  # Legacy browser automation
    "playwright"  # Modern browser automation
)

foreach ($pkg in $optional) {
    Install-PythonRequirement $pkg $true
}

if ($false) {
foreach ($pkg in $optional) {
    Write-Host "  Installing $pkg (optional)..." -ForegroundColor Cyan
    python -m pip install $pkg --quiet 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    ✅ $pkg" -ForegroundColor Green
    } else {
        Write-Host "    ⚠️  $pkg not installed (optional)" -ForegroundColor Yellow
    }
}

}

# Setup .env file
Write-Host "`n[6/6] Setting up environment..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Write-Host "  Creating .env file..." -ForegroundColor Cyan
    @"
# Friday API Keys
# Keep this file secret. Never commit it to git.

# Google Gemini (Brain & Vision)
GOOGLE_API_KEY=your_google_api_key_here

# Groq (Fast inference)
GROQ_API_KEY=your_groq_api_key_here

# Picovoice (Voice wake word)
PICOVOICE_ACCESS_KEY=your_picovoice_access_key_here

# Telegram Bot (optional)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Discord Bot (optional)
DISCORD_BOT_TOKEN=your_discord_bot_token_here
DISCORD_WEBHOOK_URL=your_discord_webhook_url_here

# Google Calendar (optional, for goal scheduling)
# Run setup_google_calendar.py to generate credentials.json
"@ | Out-File -FilePath ".env" -Encoding UTF8
    Write-Host "  ✅ .env file created. Please edit it with your API keys." -ForegroundColor Green
} else {
    Write-Host "  ✅ .env file already exists" -ForegroundColor Green
}

# Create memory directory
if (-not (Test-Path "friday_memory")) {
    New-Item -ItemType Directory -Path "friday_memory" -Force | Out-Null
    Write-Host "  ✅ Created friday_memory/ directory" -ForegroundColor Green
}

# Add friday command to PATH
Write-Host "`n[7/7] Adding friday command to PATH..." -ForegroundColor Yellow

# Create a friday.cmd wrapper script. With no args, `friday` starts the full
# assistant. With args, it routes to the management CLI (`friday status`, etc.).
$wrapperPath = Join-Path $PWD "friday.cmd"
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
echo [+] Starting dashboard server. This terminal shows logs only...
echo.
%FRIDAY_PY% friday.py
"@ | Out-File -FilePath $wrapperPath -Encoding ASCII
Write-Host "  ✅ Created friday.cmd wrapper" -ForegroundColor Green

# Add to user PATH
$currentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($currentPath -notlike "*$PWD*") {
    [Environment]::SetEnvironmentVariable("PATH", "$currentPath;$PWD", "User")
    $env:PATH += ";$PWD"
    Write-Host "  ✅ Added Friday to PATH (restart terminal to use 'friday' command)" -ForegroundColor Green
} else {
    Write-Host "  ✅ Friday already in PATH" -ForegroundColor Green
}

# Verify installation
Write-Host "`n=============================================================" -ForegroundColor Cyan
Write-Host "  Verifying installation..." -ForegroundColor Yellow
Write-Host "=============================================================" -ForegroundColor Cyan

$testFiles = @(
    "friday.py",
    "friday.cmd",
    "friday.ps1",
    "friday\live.py",
    "friday\tools.py",
    "friday\cli.py",
    "friday\dashboard.py",
    "friday\dashboard_api.py",
    "friday\memory_import.py",
    "friday\memory_context.py",
    "friday\sidecar.py",
    "friday\authority.py",
    "friday\snapshots.py",
    "friday\autonomy.py",
    "friday\ironman.py"
)

$allGood = $true
foreach ($file in $testFiles) {
    if (Test-Path $file) {
        Write-Host "  ✅ $file" -ForegroundColor Green
    } else {
        Write-Host "  ❌ $file missing!" -ForegroundColor Red
        $allGood = $false
    }
}

Write-Host "`n=============================================================" -ForegroundColor Cyan
if ($allGood) {
    Write-Host "  ✅ Installation complete!" -ForegroundColor Green
    Write-Host "`n  Next steps:" -ForegroundColor Yellow
    Write-Host "    1. Edit .env with your API keys" -ForegroundColor Yellow
    Write-Host "    2. Start everything: friday" -ForegroundColor Yellow
    Write-Host "    3. Management commands: friday status, friday doctor, friday dashboard start" -ForegroundColor Yellow
} else {
    Write-Host "  ⚠️  Some files are missing. Please check the errors above." -ForegroundColor Yellow
}
Write-Host "=============================================================" -ForegroundColor Cyan

# Ask to run Friday
Write-Host ""
$runNow = Read-Host "  Run Friday now? (y/n)"
if ($runNow -eq "y") {
    Write-Host "`n  Starting Friday..." -ForegroundColor Green
    & $wrapperPath
}

Write-Host ""
Read-Host "Press Enter to exit"

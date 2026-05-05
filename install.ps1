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
Write-Host "  This may take a few minutes..." -ForegroundColor Yellow

$packages = @(
    "langgraph>=1.0",
    "langchain>=0.2",
    "langchain-google-genai>=1.0",
    "langchain-community>=0.2",
    "mcp>=1.0",
    "pywinctl>=0.0.52",
    "pycaw>=1.5",
    "psutil>=5.9",
    "browser-history>=0.5",
    "google-auth>=2.28",
    "google-auth-oauthlib>=1.2",
    "google-auth-httplib2>=0.2",
    "google-api-python-client>=2.125",
    "requests>=2.31",
    "Pillow>=10.0",
    "pyautogui>=0.9",
    "pyscreeze>=0.1.29",
    "langgraph-checkpoint-sqlite>=3.0"
)

foreach ($pkg in $packages) {
    Write-Host "  Installing $pkg..." -ForegroundColor Cyan
    python -m pip install $pkg --quiet
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    ✅ $pkg" -ForegroundColor Green
    } else {
        Write-Host "    ⚠️  Failed to install $pkg (will try to continue)" -ForegroundColor Yellow
    }
}

# Optional packages
Write-Host "`n[5/6] Installing optional packages..." -ForegroundColor Yellow
$optional = @(
    "pvporcupine",  # Voice wake word
    "openwakeword",  # Alternative voice wake
    "python-telegram-bot",  # Telegram integration
    "discord.py",  # Discord integration
    "selenium",  # WhatsApp automation
    "playwright"  # Modern browser automation
)

foreach ($pkg in $optional) {
    Write-Host "  Installing $pkg (optional)..." -ForegroundColor Cyan
    python -m pip install $pkg --quiet 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    ✅ $pkg" -ForegroundColor Green
    } else {
        Write-Host "    ⚠️  $pkg not installed (optional)" -ForegroundColor Yellow
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

# Create a friday.cmd wrapper script
$wrapperPath = Join-Path $PWD "friday.cmd"
@"
@echo off
python "$PWD\friday_master.py" %*
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
    "friday_graph.py",
    "friday_mcp.py",
    "friday_live.py",
    "screen_watcher.py",
    "proactive_commentary.py",
    "browser_history_tools.py",
    "goal_memory.py",
    "file_generator.py",
    "multi_agent.py",
    "voice_wake.py",
    "message_channels.py",
    "coding_agent.py",
    "self_improvement.py",
    "friday_master.py"
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
    Write-Host "    2. Run: friday status" -ForegroundColor Yellow
    Write-Host "    3. Start Friday: friday multi-agent" -ForegroundColor Yellow
} else {
    Write-Host "  ⚠️  Some files are missing. Please check the errors above." -ForegroundColor Yellow
}
Write-Host "=============================================================" -ForegroundColor Cyan

# Ask to run Friday
Write-Host ""
$runNow = Read-Host "  Run Friday now? (y/n)"
if ($runNow -eq "y") {
    Write-Host "`n  Starting Friday..." -ForegroundColor Green
    python friday_master.py status
    Write-Host ""
    $startFriday = Read-Host "  Start Friday multi-agent? (y/n)"
    if ($startFriday -eq "y") {
        python friday_master.py multi-agent
    }
}

Write-Host ""
Read-Host "Press Enter to exit"

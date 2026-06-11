#Requires -Version 5.1
<#
.SYNOPSIS
    FRIDAY — Installation script with onboarding wizard.
.DESCRIPTION
    Checks prerequisites, creates .venv, installs dependencies,
    guides you through all API key configuration, and verifies
    the installation.
.PARAMETER Quick
    Skip the onboarding wizard and install with minimal prompts.
.PARAMETER NoVenv
    Skip virtual environment creation.
#>

param(
    [switch]$Quick,
    [switch]$NoVenv
)

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false

# ─── helpers ──────────────────────────────────────────────────────────
function Write-Step($Title) { Write-Host "`n━━━ $Title ━━━" -ForegroundColor Cyan }
function Write-Ok  ($Msg)   { Write-Host "  ✅ $Msg" -ForegroundColor Green }
function Write-Warn($Msg)   { Write-Host "  ⚠️  $Msg" -ForegroundColor Yellow }
function Write-Fail($Msg)   { Write-Host "  ❌ $Msg" -ForegroundColor Red }

function Test-Command($Name) {
    try   { $null = Get-Command $Name -ErrorAction Stop; return $true }
    catch { return $false }
}

function Add-ToEnvFile($Key, $Value, $Path = ".env") {
    if (Test-Path $Path) {
        $lines = Get-Content $Path
        $existing = $lines | Where-Object { $_ -match "^${Key}=" }
        if ($existing) {
            $lines = $lines -replace "^${Key}=.*", "${Key}=$Value"
        } else {
            $lines += "${Key}=$Value"
        }
        $lines | Set-Content $Path
    }
}

function Prompt-Key($Name, $Description) {
    Write-Host "`n$Name :" -ForegroundColor Yellow
    if ($Description) { Write-Host "  $Description" -ForegroundColor Gray }
    $val = Read-Host "  Enter $Name (or press Enter to skip)"
    return $val.Trim()
}

# ─── BANNER ───────────────────────────────────────────────────────────
Write-Host @"

  ███████╗██████╗ ██╗██████╗  █████╗ ██╗   ██╗
  ██╔════╝██╔══██╗██║██╔══██╗██╔══██╗╚██╗ ██╔╝
  █████╗  ██████╔╝██║██║  ██║███████║ ╚████╔╝
  ██╔══╝  ██╔══██╗██║██║  ██║██╔══██║  ╚██╔╝
  ██║     ██║  ██║██║██████╔╝██║  ██║   ██║
  ╚═╝     ╚═╝  ╚═╝╚═╝╚═════╝ ╚═╝  ╚═╝   ╚═╝
  Ultimate AI Agent — Installation & Onboarding
"@ -ForegroundColor Cyan
Write-Host "  PowerShell Edition | https://github.com/your-org/friday`n" -ForegroundColor Gray

# ─── 1. PREREQUISITES ─────────────────────────────────────────────────
Write-Step "PREREQUISITES"

$prereqsOk = $true

if (-not (Test-Command python)) {
    Write-Fail "Python not found. Install Python 3.10+ from https://www.python.org/downloads/"
    $prereqsOk = $false
} else {
    $pv = python --version 2>&1
    Write-Ok "$pv"
}

if (-not (Test-Command git)) {
    Write-Warn "git not found — version checks will be skipped"
} else {
    $gv = git --version 2>&1
    Write-Ok "$gv"
}

if (-not $prereqsOk) { Write-Host "`nFix above errors and re-run." -ForegroundColor Red; exit 1 }

# Optional: Node.js (for opencode serve)
if (Test-Command node) {
    $nv = node --version 2>&1
    Write-Ok "$nv (opencode serve available)"
} else {
    Write-Warn "Node.js not found — opencode serve sub-agent spawning requires it"
    Write-Host "  Install from https://nodejs.org/ (LTS recommended)" -ForegroundColor Gray
}

# ─── 2. VIRTUAL ENVIRONMENT ───────────────────────────────────────────
if (-not $NoVenv) {
    Write-Step "VIRTUAL ENVIRONMENT"

    if (Test-Path ".venv") {
        Write-Ok ".venv/ already exists"
    } else {
        Write-Host "  Creating .venv/..." -ForegroundColor Yellow
        python -m venv .venv
        if ($LASTEXITCODE -eq 0) {
            Write-Ok ".venv/ created"
        } else {
            Write-Fail "Failed to create .venv/"; exit 1
        }
    }

    $venvPython = Join-Path $PWD ".venv\Scripts\python.exe"
    $venvPip    = Join-Path $PWD ".venv\Scripts\pip.exe"
    if (-not (Test-Path $venvPython)) {
        Write-Fail "Virtual environment Python not found at $venvPython"
        exit 1
    }
    Write-Ok "Using $venvPython"
} else {
    $venvPython = "python"
    $venvPip    = "python -m pip"
}

function RunPip { param([string]$Args) & $venvPython -m pip $Args --quiet --disable-pip-version-check }

# ─── 3. DEPENDENCIES ──────────────────────────────────────────────────
Write-Step "DEPENDENCIES"

Write-Host "  Installing core packages..." -ForegroundColor Yellow

$packages = @(
    "google-genai>=1.0"
    "requests>=2.31"
    "python-dotenv>=1.0"
    "pillow>=10.0"
    "opencv-python>=4.8"
    "rich>=13.0"
    "colorama>=0.4.6"
    "psutil>=5.9"
    "numpy>=1.24"
    "chromadb>=1.5"
    "fastapi>=0.115.0"
    "uvicorn>=0.32.0"
    "python-multipart>=0.0.9"
    "websockets>=12.0"
    "httpx>=0.27.0"
    "pydantic>=2.0"
    "pyyaml>=6.0"
    "flask>=3.0"
    "flask-socketio>=5.3"
    "flask-cors>=4.0"
)

foreach ($pkg in $packages) {
    $name = ($pkg -split '[<>=!~]')[0].Trim()
    $installed = & $venvPython -c "import importlib.metadata as m; m.version('$name')" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [SKIP] $name $installed" -ForegroundColor DarkGray
    } else {
        Write-Host "  [INSTALL] $pkg" -ForegroundColor Cyan
        & $venvPython -m pip install $pkg --quiet --disable-pip-version-check 2>$null
    }
}

Write-Ok "Core packages installed"

# requirements.txt
if (Test-Path "requirements.txt") {
    Write-Host "  Installing from requirements.txt..." -ForegroundColor Yellow
    & $venvPython -m pip install -r requirements.txt --quiet --disable-pip-version-check
    if ($LASTEXITCODE -eq 0) {
        Write-Ok "requirements.txt installed"
    } else {
        Write-Warn "Some packages in requirements.txt failed (continuing)"
    }
}

# Optional: browser-use
Write-Host "  Installing optional browser-use..." -ForegroundColor Yellow
& $venvPython -m pip install browser-use==0.13.0 langchain-google-genai --quiet --disable-pip-version-check 2>$null

# ─── 4. ONBOARDING WIZARD ─────────────────────────────────────────────
if (-not $Quick) {
    Write-Step "ONBOARDING — API KEYS"
    Write-Host "  FRIDAY needs various API keys. You can fill them all now or"
    Write-Host "  skip any and configure later via the dashboard."
    Write-Host "  All keys are stored in .env (gitignored).`n" -ForegroundColor Gray

    # Create .env from .env.example if it doesn't exist
    if (-not (Test-Path ".env")) {
        if (Test-Path ".env.example") {
            Copy-Item ".env.example" ".env"
            Write-Ok "Created .env from .env.example"
        } else {
            New-Item -ItemType File -Path ".env" -Force | Out-Null
            Write-Ok "Created empty .env"
        }
    } else {
        Write-Ok ".env already exists (keys will be appended/updated)"
    }

    # ── Essential keys ──
    Write-Host "`n─── ESSENTIAL ───" -ForegroundColor Cyan

    $ocKey = Prompt-Key "OPENCODE_ZEN_API_KEY" @"
  Primary model provider. Get your free API key at:
  https://opencode.ai (unlimited tokens, big-pickle model)
  This is the default brain for FRIDAY.
"@
    if ($ocKey) { Add-ToEnvFile "OPENCODE_ZEN_API_KEY" $ocKey }

    $nvKey = Prompt-Key "NVIDIA_NIM_API_KEY" @"
  Fallback/research model provider. Get free API key at:
  https://build.nvidia.com/ (requires NVIDIA account)
  Provides access to Qwen, Llama, and vision models.
"@
    if ($nvKey) { Add-ToEnvFile "NVIDIA_NIM_API_KEY" $nvKey }

    $googleKey = Prompt-Key "GOOGLE_API_KEY" @"
  Google Gemini models (vision, document AI). Get key at:
  https://aistudio.google.com/apikey (free tier: 60 req/min)
"@
    if ($googleKey) { Add-ToEnvFile "GOOGLE_API_KEY" $googleKey }

    $groqKey = Prompt-Key "GROQ_API_KEY" @"
  Groq — ultra-fast Whisper speech-to-text. Get key at:
  https://console.groq.com/keys (free tier: 30 req/min)
"@
    if ($groqKey) { Add-ToEnvFile "GROQ_API_KEY" $groqKey }

    $githubToken = Prompt-Key "GITHUB_TOKEN" @"
  GitHub Personal Access Token for OSINT features.
  Create at: https://github.com/settings/tokens (no special scopes needed)
"@
    if ($githubToken) { Add-ToEnvFile "GITHUB_TOKEN" $githubToken }

    # ── Communication keys ──
    Write-Host "`n─── COMMUNICATION (optional) ───" -ForegroundColor Cyan

    $telegramToken = Prompt-Key "TELEGRAM_BOT_TOKEN" @"
  Telegram Bot token. Create a bot via @BotFather on Telegram.
  Used for remote commands and alerts.
"@
    if ($telegramToken) { Add-ToEnvFile "TELEGRAM_BOT_TOKEN" $telegramToken }

    $discordToken = Prompt-Key "DISCORD_BOT_TOKEN" @"
  Discord Bot token. Create a bot at https://discord.com/developers/applications
  Used for Discord integration.
"@
    if ($discordToken) { Add-ToEnvFile "DISCORD_BOT_TOKEN" $discordToken }

    $discordWebhook = Prompt-Key "DISCORD_WEBHOOK_URL" @"
  Discord Webhook URL (for sending messages without a bot).
  Create in Discord channel settings → Integrations → Webhooks.
"@
    if ($discordWebhook) { Add-ToEnvFile "DISCORD_WEBHOOK_URL" $discordWebhook }

    # ── Voice keys ──
    Write-Host "`n─── VOICE (optional) ───" -ForegroundColor Cyan

    $picovoice = Prompt-Key "PICOVOICE_ACCESS_KEY" @"
  Picovoice wake word engine. Get key at:
  https://console.picovoice.ai/ (free tier: unlimited)
"@
    if ($picovoice) { Add-ToEnvFile "PICOVOICE_ACCESS_KEY" $picovoice }

    $sarvam = Prompt-Key "SARVAM_API_KEY" @"
  Sarvam AI — Hindi/English Text-to-Speech. Get key at:
  https://docs.sarvam.ai/ (free tier available)
"@
    if ($sarvam) { Add-ToEnvFile "SARVAM_API_KEY" $sarvam }

    # ── OSINT keys ──
    Write-Host "`n─── OSINT (optional) ───" -ForegroundColor Cyan

    $shodan = Prompt-Key "SHODAN_API_KEY" "Shodan — device search (free: 100 queries/month)"
    if ($shodan) { Add-ToEnvFile "SHODAN_API_KEY" $shodan }

    $virustotal = Prompt-Key "VIRUSTOTAL_API_KEY" "VirusTotal — file/URL reputation (free: 500/day)"
    if ($virustotal) { Add-ToEnvFile "VIRUSTOTAL_API_KEY" $virustotal }

    $ipinfo = Prompt-Key "IPINFO_API_KEY" "IPinfo — geolocation/ASN (free: 50K requests/month)"
    if ($ipinfo) { Add-ToEnvFile "IPINFO_API_KEY" $ipinfo }

    $abuseipdb = Prompt-Key "ABUSEIPDB_API_KEY" "AbuseIPDB — IP blacklist check (free: 1000/day)"
    if ($abuseipdb) { Add-ToEnvFile "ABUSEIPDB_API_KEY" $abuseipdb }

    # ── Social Media keys ──
    Write-Host "`n─── SOCIAL MEDIA (optional) ───" -ForegroundColor Cyan

    $instaUser = Prompt-Key "INSTAGRAM_USER" "Instagram username for automation"
    if ($instaUser) { Add-ToEnvFile "INSTAGRAM_USER" $instaUser; $instaPass = Prompt-Key "INSTAGRAM_PASS" "Instagram password"; Add-ToEnvFile "INSTAGRAM_PASS" $instaPass }

    $redditId = Prompt-Key "REDDIT_CLIENT_ID" "Reddit API client ID (create at https://www.reddit.com/prefs/apps)"
    if ($redditId) { Add-ToEnvFile "REDDIT_CLIENT_ID" $redditId; $redditSecret = Prompt-Key "REDDIT_CLIENT_SECRET" "Reddit API client secret"; Add-ToEnvFile "REDDIT_CLIENT_SECRET" $redditSecret }

    # ── Google Cloud Setup Guide ──
    Write-Host "`n─── GOOGLE CLOUD SETUP ───" -ForegroundColor Cyan
    Write-Host "  FRIDAY can use Google Calendar and Gmail features."
    Write-Host "  Setting up Google Cloud is optional but recommended.`n" -ForegroundColor Gray

    $setupGcp = Read-Host "  Do you want to set up Google Cloud now? (y/n)"
    if ($setupGcp -eq "y") {
        # Project name
        $projectName = Read-Host "  Enter your Google Cloud Project ID (e.g., friday-agent)"
        if ($projectName) {
            Add-ToEnvFile "GCP_PROJECT" $projectName
        }

        Write-Host "`n  Steps to complete Google Cloud setup:" -ForegroundColor Yellow
        Write-Host "  1. Go to https://console.cloud.google.com/apis/credentials" -ForegroundColor White
        Write-Host "  2. Create a new OAuth 2.0 Client ID (Desktop application)" -ForegroundColor White
        Write-Host "  3. Download the JSON and save as credentials.json in the project root" -ForegroundColor White
        Write-Host "  4. Enable these APIs for your project:" -ForegroundColor White
        Write-Host "     - Google Calendar API" -ForegroundColor Gray
        Write-Host "     - Gmail API" -ForegroundColor Gray
        Write-Host "  5. Set the GCP_PROJECT in .env (done above)" -ForegroundColor Gray
        Write-Host "  6. Run: $venvPython setup_google_calendar.py" -ForegroundColor Cyan
        Write-Host "     (First-time auth will open a browser window)" -ForegroundColor Gray

        $confirm = Read-Host "`n  Press Enter after completing steps 1-4 (or 's' to skip)"
    }

    Write-Ok "API key onboarding complete!"
} else {
    Write-Host "  Skipping wizard (-Quick mode). Use 'friday config' to set keys later." -ForegroundColor Gray
    if (-not (Test-Path ".env")) {
        if (Test-Path ".env.example") {
            Copy-Item ".env.example" ".env"
            Write-Ok "Created .env from .env.example"
        }
    }
}

# ─── 5. MEMORY DIRECTORY ─────────────────────────────────────────────
Write-Step "MEMORY DIRECTORY"
if (-not (Test-Path "friday_memory")) {
    New-Item -ItemType Directory -Path "friday_memory" -Force | Out-Null
    Write-Ok "Created friday_memory/"
} else {
    Write-Ok "friday_memory/ already exists"
}

# Write .gitkeep
New-Item -ItemType File -Path "friday_memory\.gitkeep" -Force | Out-Null

# ─── 6. FRIDAY COMMAND (PATH) ───────────────────────────────────────
Write-Step "FRIDAY COMMAND (PATH)"

$wrapperPath = Join-Path $PWD "friday.cmd"
@"
@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
set "FRIDAY_PY=%cd%\.venv\Scripts\python.exe"
if not exist "%FRIDAY_PY%" set "FRIDAY_PY=python.exe"
if "%~1"=="" goto start_friday
if /I "%~1"=="start" goto start_friday
if /I "%~1"=="live" goto start_friday
%FRIDAY_PY% -m friday.cli %*
exit /b %ERRORLEVEL%
:start_friday
echo [STARK INDUSTRIES] Booting F.R.I.D.A.Y. Sovereign Agent...
echo.
%FRIDAY_PY% friday.py
"@ | Out-File -FilePath $wrapperPath -Encoding ASCII
Write-Ok "Created friday.cmd wrapper"

$currentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($currentPath -notlike "*$PWD*") {
    [Environment]::SetEnvironmentVariable("PATH", "$currentPath;$PWD", "User")
    $env:PATH += ";$PWD"
    Write-Ok "Added to user PATH (restart terminal to use 'friday' command)"
} else {
    Write-Ok "Already in PATH"
}

# ─── 7. VERIFICATION ─────────────────────────────────────────────────
Write-Step "VERIFICATION"

$coreFiles = @(
    "friday.py"
    "friday.cmd"
    "config.yaml"
    ".env"
    "friday\__init__.py"
    "friday\cli.py"
    "friday\live.py"
    "friday\tools.py"
    "friday\orchestrator.py"
    "friday\townhall_engine.py"
    "friday\nim_client.py"
    "friday\model_router.py"
    "friday\opencode_bridge.py"
    "friday\agent_terminal.py"
    "friday\paths.py"
    "friday\_paths.py"
)

$allGood = $true
foreach ($file in $coreFiles) {
    if (Test-Path $file) {
        Write-Ok $file
    } else {
        Write-Fail "$file missing!"
        $allGood = $false
    }
}

# Python import check
Write-Host "  Testing Python imports..." -ForegroundColor Yellow
$importTest = & $venvPython -c "
import sys
modules = ['friday.tools', 'friday.orchestrator', 'friday.nim_client', 'friday.model_router',
           'friday.opencode_bridge', 'friday.agent_terminal', 'friday.townhall_engine']
errors = []
for m in modules:
    try:
        __import__(m)
    except Exception as e:
        errors.append(f'{m}: {e}')
if errors:
    print('IMPORT_ERRORS:' + ';'.join(errors))
else:
    print('OK')
" 2>&1

if ($LASTEXITCODE -eq 0 -and $importTest -eq "OK") {
    Write-Ok "All imports successful"
} else {
    Write-Warn "Import check: $importTest"
    Write-Host "  (Some imports may need optional dependencies)" -ForegroundColor Gray
}

# ─── SUMMARY ─────────────────────────────────────────────────────────
Write-Step "SUMMARY"
if ($allGood) {
    Write-Host @"

  ╔══════════════════════════════════════════════════════════╗
  ║            INSTALLATION COMPLETE                        ║
  ╠══════════════════════════════════════════════════════════╣
  ║  Start FRIDAY:     friday                                 ║
  ║  Config:           friday config                           ║
  ║  Status:           friday status                           ║
  ║  Doctor:           friday doctor                           ║
  ║  Run tests:        $venvPython test_features_comp.py       ║
  ║                                                             ║
  ║  Dashboard:        friday dashboard start                   ║
  ║  Townhall:         friday townhall                          ║
  ║                                                             ║
  ║  Edit .env for more keys: notepad .env                      ║
  ╚══════════════════════════════════════════════════════════╝
"@ -ForegroundColor Cyan
} else {
    Write-Warn "Some files are missing. Check errors above."
}

$runNow = Read-Host "Run FRIDAY now? (y/n)"
if ($runNow -eq "y") {
    Write-Host "`n  Starting FRIDAY..." -ForegroundColor Green
    & $wrapperPath
}

Write-Host ""
Read-Host "Press Enter to exit"
